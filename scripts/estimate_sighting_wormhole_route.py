#!/usr/bin/env python3
"""Compute a conditional historical-emitter / moving-mouth sighting scenario.

This joins a dated witness event to a target-side light emission, then asks
what smooth flat-exterior twin-mouth kinematics would accumulate that clock
offset. It does not model an actual wormhole metric, Earth-fixed observer
worldline, historical emitter, or material vehicle arrival.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estimate_smooth_wormhole_clock_offset import estimate  # noqa: E402

C_M_S = 299_792_458.0
JULIAN_YEAR_S = 365.25 * 86400.0


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamps must include a UTC offset or Z")
    return parsed.astimezone(timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-utc", type=parse_utc, default=parse_utc("2026-10-18T03:15:00Z"))
    parser.add_argument("--witness-utc", type=parse_utc, default=parse_utc("1997-03-14T03:15:00Z"))
    parser.add_argument("--range-km", type=float, default=10.0, help="assumed emitter-to-witness distance")
    parser.add_argument("--mouth-gap-m", type=float, default=1000.0, help="small initial and final separation between mouths for the flat 1D closure screen")
    parser.add_argument("--throat-seconds", type=float, default=0.0, help="assumed signal transit time through throat")
    parser.add_argument("--beta-max", type=float, default=0.8)
    parser.add_argument("--view-span-years", type=float, default=5000.0, help="remote proper-time span requested for the crew viewpoint")
    parser.add_argument("--crew-minutes", type=float, default=5.0, help="A.R.G.O. proper-time duration for the requested viewpoint scan")
    parser.add_argument("--endpoint-displacement-ly", type=float, default=0.0)
    parser.add_argument("--csv", type=Path, help="write sampled mouth worldline and clock history")
    args = parser.parse_args()

    if args.range_km < 0 or args.mouth_gap_m <= 0 or args.throat_seconds < 0:
        parser.error("range and throat transit must be nonnegative; mouth gap must be positive")
    if args.view_span_years < 0 or args.crew_minutes <= 0:
        parser.error("view span must be nonnegative and crew duration must be positive")
    control = args.control_utc.timestamp()
    witness = args.witness_utc.timestamp()
    if control <= witness:
        parser.error("control event must be later than the witness event")
    range_m = args.range_km * 1000.0
    light_time_s = range_m / C_M_S
    emitter_epoch = witness - light_time_s
    required_offset_s = control - witness + args.throat_seconds + light_time_s
    lag_years = required_offset_s / JULIAN_YEAR_S
    result = estimate(lag_years, args.beta_max, args.endpoint_displacement_ly)
    crew_seconds = args.crew_minutes * 60.0
    crew_years = crew_seconds / JULIAN_YEAR_S
    requested_rate = args.view_span_years / crew_years if crew_years else float("inf")
    equal_clock_span_years = crew_years
    # Preliminary return-ray screen: at the target-mouth exit event, emit an
    # ordinary null signal toward the moving entry mouth and solve its first
    # intersection with that mouth worldline, extended at rest after reunion.
    profile_duration = float(result["exterior_duration_years"])
    mouth_gap_ly = args.mouth_gap_m / (C_M_S * JULIAN_YEAR_S)
    target_exit_year = float(result["moving_mouth_proper_time_years"]) + args.throat_seconds / JULIAN_YEAR_S
    beta_profile = args.beta_max
    endpoint_ly = args.endpoint_displacement_ly

    def mouth_x(time_years: float) -> float:
        if time_years >= profile_duration:
            return mouth_gap_ly + endpoint_ly
        u = max(0.0, time_years / profile_duration)
        profile_x = endpoint_ly * (3.0*u*u - 2.0*u**3) + beta_profile * profile_duration / (2.0*math.pi) * (1.0 - math.cos(2.0*math.pi*u))
        return mouth_gap_ly + profile_x

    def return_residual(time_years: float) -> float:
        return time_years - target_exit_year - abs(mouth_x(time_years))

    closure = {"model": "flat 1D ordinary-light return to prescribed moving-mouth worldline; not field-state closure"}
    residual_at_control = return_residual(profile_duration)
    if residual_at_control >= 0.0:
        lo, hi = target_exit_year, profile_duration
        for _ in range(90):
            mid = (lo + hi) / 2.0
            if return_residual(mid) >= 0.0:
                hi = mid
            else:
                lo = mid
        return_time = (lo + hi) / 2.0
        closure.update({
            "target_exit_coordinate_years_from_mouth_start": target_exit_year,
            "return_signal_intersects_entry_mouth_at_years_from_start": return_time,
            "return_light_travel_time_years": return_time - target_exit_year,
            "control_event_coordinate_years_from_mouth_start": profile_duration,
            "remaining_wait_on_entry_mouth_worldline_years": profile_duration - return_time,
            "preliminary_loop_margin_years": profile_duration - return_time,
            "status": "null return intersects before or at control event; requires full geometry and state matching",
        })
    else:
        closure.update({
            "target_exit_coordinate_years_from_mouth_start": target_exit_year,
            "control_event_coordinate_years_from_mouth_start": profile_duration,
            "status": "no ordinary null interception with the entry-mouth worldline by the control event in this 1D profile",
        })
    view_map = {
        "requested_remote_view_span_years": args.view_span_years,
        "crew_proper_time_minutes": args.crew_minutes,
        "required_mean_remote_to_crew_time_ratio": requested_rate,
        "equal_clock_wormhole_remote_span_years": equal_clock_span_years,
        "required_time_stretch_beyond_equal_clock_map": (
            args.view_span_years / equal_clock_span_years if equal_clock_span_years else float("inf")
        ),
        "status": "not supplied by standard equal-clock mouth identification",
    }
    if args.csv:
        from estimate_smooth_wormhole_clock_offset import write_csv

        write_csv(args.csv, result)
    output = {
        "scenario": "conditional Phoenix Lights pilot-account timing illustration",
        "control_event_utc": args.control_utc.isoformat(),
        "nominal_witness_event_utc": args.witness_utc.isoformat(),
        "target_emission_event_utc": datetime.fromtimestamp(emitter_epoch, timezone.utc).isoformat(),
        "assumed_emitter_to_witness_range_km": args.range_km,
        "assumed_initial_and_final_mouth_gap_m": args.mouth_gap_m,
        "ordinary_light_flight_time_seconds": light_time_s,
        "assumed_throat_transit_seconds": args.throat_seconds,
        "required_mouth_clock_offset_years": lag_years,
        "crew_viewpoint_map": view_map,
        "preliminary_chronology_closure": closure,
        "mouth_history_kinematics": result,
        "interpretation": (
            "The result is a conditional continuous mouth worldline plus target-side emission timing. "
            "It is not a reconstructed Phoenix Lights trajectory or a material A.R.G.O. arrival."
        ),
        "limits": [
            "NUFORC 8345 date/time is a retrospective single-witness report; 8:15 p.m. March 13 is approximate.",
            "The 10 km range is an illustrative input, not a measured sighting distance.",
            "Flat exterior, stationary/co-located endpoint approximation; no Earth rotation, orbit, or Galactic motion.",
            "No solved wormhole throat geometry, stress-energy, optical source, or collision analysis.",
            "The moving-mouth history only creates a clock offset; its equal-clock transfer map does not create the requested fast viewpoint scan.",
            "The reported closure margin is a flat one-dimensional null-interception screen with a fixed mouth gap; it does not establish a closed timelike curve or field-state matching.",
        ],
    }
    if args.csv:
        output["sampled_worldline_csv"] = str(args.csv)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
