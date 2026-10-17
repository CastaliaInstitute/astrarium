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
    parser.add_argument("--throat-seconds", type=float, default=0.0, help="assumed signal transit time through throat")
    parser.add_argument("--beta-max", type=float, default=0.8)
    parser.add_argument("--endpoint-displacement-ly", type=float, default=0.0)
    parser.add_argument("--csv", type=Path, help="write sampled mouth worldline and clock history")
    args = parser.parse_args()

    if args.range_km < 0 or args.throat_seconds < 0:
        parser.error("range and throat transit must be nonnegative")
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
    if args.csv:
        from estimate_smooth_wormhole_clock_offset import write_csv

        write_csv(args.csv, result)
    output = {
        "scenario": "conditional Phoenix Lights pilot-account timing illustration",
        "control_event_utc": args.control_utc.isoformat(),
        "nominal_witness_event_utc": args.witness_utc.isoformat(),
        "target_emission_event_utc": datetime.fromtimestamp(emitter_epoch, timezone.utc).isoformat(),
        "assumed_emitter_to_witness_range_km": args.range_km,
        "ordinary_light_flight_time_seconds": light_time_s,
        "assumed_throat_transit_seconds": args.throat_seconds,
        "required_mouth_clock_offset_years": lag_years,
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
        ],
    }
    if args.csv:
        output["sampled_worldline_csv"] = str(args.csv)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
