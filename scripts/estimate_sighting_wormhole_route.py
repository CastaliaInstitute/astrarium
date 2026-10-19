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
from estimate_smooth_wormhole_clock_offset import beta_at, estimate, simpson_mean  # noqa: E402

C_M_S = 299_792_458.0
JULIAN_YEAR_S = 365.25 * 86400.0


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamps must include a UTC offset or Z")
    return parsed.astimezone(timezone.utc)


def planar_profile(
    lookback_years: float,
    beta_max: float,
    endpoint_distance_ly: float,
    transverse_excursion_ly: float,
) -> dict[str, float | str]:
    """Solve one smooth, planar mouth excursion with a fixed proper-clock lag.

    The x coordinate uses the existing smooth twin-mouth profile. The added
    y coordinate is y=b*sin(pi*u)^2, so it and its velocity vanish at both
    endpoints. Proper time is reintegrated from the total 2D speed.
    """
    if transverse_excursion_ly == 0.0:
        return estimate(lookback_years, beta_max, endpoint_distance_ly)

    intervals = 4000
    samples = intervals

    def state(duration: float, u: float) -> tuple[float, float, float, float, float]:
        vx = beta_at(u, duration, endpoint_distance_ly, beta_max)
        vy = transverse_excursion_ly * math.pi / duration * math.sin(2.0 * math.pi * u)
        x = endpoint_distance_ly * (3.0 * u * u - 2.0 * u**3) + beta_max * duration / (2.0 * math.pi) * (1.0 - math.cos(2.0 * math.pi * u))
        y = transverse_excursion_ly * math.sin(math.pi * u) ** 2
        return x, y, vx, vy, math.hypot(vx, vy)

    def lag_and_speed(duration: float) -> tuple[float | None, float]:
        max_speed = 0.0
        for i in range(samples + 1):
            *_, speed = state(duration, i / samples)
            max_speed = max(max_speed, speed)
        if max_speed >= 1.0:
            return None, max_speed

        def integrand(u: float) -> float:
            *_, speed = state(duration, u)
            return 1.0 - math.sqrt(1.0 - speed * speed)

        return duration * simpson_mean(integrand, intervals), max_speed

    # Find a subluminal lower edge. A tiny margin avoids roundoff at beta=1.
    lower = max(1.0, endpoint_distance_ly * 1.001, transverse_excursion_ly * math.pi / max(math.sqrt(1.0 - beta_max**2), 1e-12))
    for _ in range(200):
        low_lag, low_speed = lag_and_speed(lower)
        if low_lag is not None and low_speed < 1.0 - 1e-10:
            break
        lower *= 1.01
    else:
        raise ValueError("could not find a subluminal duration for the planar profile")

    target = lookback_years
    previous_t, previous_lag = lower, float(low_lag)
    bracket: tuple[float, float] | None = None
    best_lag = previous_lag
    t = lower
    baseline = estimate(lookback_years, beta_max, endpoint_distance_ly)
    baseline_duration = float(baseline["exterior_duration_years"])
    upper_limit = max(lower * 100.0, target * 100.0, baseline_duration * 100.0, 100.0)
    while t < upper_limit:
        t = min(t * 1.01, upper_limit)
        lag, speed = lag_and_speed(t)
        if lag is None:
            continue
        best_lag = min(best_lag, lag)
        if (previous_lag - target) * (lag - target) <= 0.0:
            bracket = (previous_t, t)
            break
        previous_t, previous_lag = t, lag

    if bracket is None:
        raise ValueError(
            f"no duration found for this smooth planar profile; smallest sampled lag was {best_lag:.6g} years "
            f"for a requested {target:.6g}-year offset; searched up to {upper_limit:.6g} years "
            "with 1% geometric duration steps"
        )

    lo, hi = bracket
    lo_lag, _ = lag_and_speed(lo)
    for _ in range(70):
        mid = (lo + hi) / 2.0
        mid_lag, _ = lag_and_speed(mid)
        if mid_lag is None:
            lo = mid
            continue
        if (float(lo_lag) - target) * (mid_lag - target) <= 0.0:
            hi = mid
        else:
            lo, lo_lag = mid, mid_lag
    duration = (lo + hi) / 2.0
    actual_lag, max_speed = lag_and_speed(duration)
    if actual_lag is None:
        raise ArithmeticError("planar profile root is not subluminal")

    max_radius = 0.0
    path_length = 0.0
    max_accel_beta_per_year = 0.0
    previous_xy: tuple[float, float] | None = None
    for i in range(samples + 1):
        u = i / samples
        x, y, _, _, _ = state(duration, u)
        max_radius = max(max_radius, math.hypot(x, y))
        if previous_xy is not None:
            path_length += math.hypot(x - previous_xy[0], y - previous_xy[1])
        previous_xy = (x, y)
        ax = endpoint_distance_ly / duration**2 * 6.0 * (1.0 - 2.0*u) + beta_max * 2.0*math.pi / duration * math.cos(2.0*math.pi*u)
        ay = transverse_excursion_ly * 2.0 * math.pi**2 / duration**2 * math.cos(2.0*math.pi*u)
        max_accel_beta_per_year = max(max_accel_beta_per_year, math.hypot(ax, ay))

    return {
        "model": "flat-exterior smooth planar twin-mouth kinematics",
        "lookback_clock_offset_years": lookback_years,
        "endpoint_displacement_light_years": endpoint_distance_ly,
        "transverse_excursion_amplitude_light_years": transverse_excursion_ly,
        "maximum_speed_fraction_of_c": max_speed,
        "sinusoidal_x_velocity_amplitude_fraction_of_c": beta_max,
        "clock_lag_fraction_of_exterior_duration": lookback_years / duration,
        "exterior_duration_years": duration,
        "moving_mouth_proper_time_years": duration - lookback_years,
        "stationary_mouth_proper_time_years": duration,
        "maximum_displacement_from_initial_site_light_years": max_radius,
        "total_path_length_light_years": path_length,
        "maximum_coordinate_acceleration_m_s2": max_accel_beta_per_year * C_M_S / JULIAN_YEAR_S,
        "profile": "x smoothstep + sinusoidal excursion; y=b*sin(pi*u)^2; total speed from both components",
        "duration_solver": "1% geometric scan, then bisection; 4,000-interval Simpson proper-time integration",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-utc", type=parse_utc, default=parse_utc("2026-10-18T03:15:00Z"))
    parser.add_argument("--witness-utc", type=parse_utc, default=parse_utc("1997-03-14T03:15:00Z"))
    parser.add_argument("--range-km", type=float, default=10.0, help="assumed emitter-to-witness distance")
    parser.add_argument("--mouth-gap-m", type=float, default=1000.0, help="small initial and final separation between mouths")
    parser.add_argument("--transverse-excursion-ly", type=float, default=0.0, help="peak sideways amplitude of a smooth mouth excursion that returns to the initial axis")
    parser.add_argument("--throat-seconds", type=float, default=0.0, help="assumed signal transit time through throat")
    parser.add_argument("--beta-max", type=float, default=0.8)
    parser.add_argument("--view-span-years", type=float, default=5000.0, help="remote proper-time span requested for the crew viewpoint")
    parser.add_argument("--crew-minutes", type=float, default=5.0, help="A.R.G.O. proper-time duration for the requested viewpoint scan")
    parser.add_argument("--endpoint-displacement-ly", type=float, default=0.0)
    parser.add_argument("--csv", type=Path, help="write sampled mouth worldline and clock history")
    args = parser.parse_args()

    if args.range_km < 0 or args.mouth_gap_m <= 0 or args.throat_seconds < 0 or args.transverse_excursion_ly < 0:
        parser.error("range, throat transit, and transverse excursion must be nonnegative; mouth gap must be positive")
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
    try:
        result = planar_profile(lag_years, args.beta_max, args.endpoint_displacement_ly, args.transverse_excursion_ly)
    except ValueError as exc:
        parser.error(str(exc))
    crew_seconds = args.crew_minutes * 60.0
    crew_years = crew_seconds / JULIAN_YEAR_S
    requested_rate = args.view_span_years / crew_years if crew_years else float("inf")
    equal_clock_span_years = crew_years
    # Preliminary return-ray screen in the same flat 2D spatial embedding: at
    # the target-mouth exit event, emit an ordinary null signal toward the
    # moving entry mouth along its solved planar worldline.
    profile_duration = float(result["exterior_duration_years"])
    mouth_gap_ly = args.mouth_gap_m / (C_M_S * JULIAN_YEAR_S)
    target_exit_year = float(result["moving_mouth_proper_time_years"]) + args.throat_seconds / JULIAN_YEAR_S
    beta_profile = args.beta_max
    endpoint_ly = args.endpoint_displacement_ly

    def mouth_xy(time_years: float) -> tuple[float, float]:
        if time_years >= profile_duration:
            return mouth_gap_ly + endpoint_ly, 0.0
        u = max(0.0, time_years / profile_duration)
        x = endpoint_ly * (3.0*u*u - 2.0*u**3) + beta_profile * profile_duration / (2.0*math.pi) * (1.0 - math.cos(2.0*math.pi*u))
        y = args.transverse_excursion_ly * math.sin(math.pi*u) ** 2
        return mouth_gap_ly + x, y

    def return_residual(time_years: float) -> float:
        x, y = mouth_xy(time_years)
        return time_years - target_exit_year - math.hypot(x, y)

    closure = {"model": "flat 2D spatial null return to the same smooth planar mouth worldline; not field-state closure"}
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
            "null_return_distance_at_control_light_years": math.hypot(*mouth_xy(profile_duration)),
            "available_future_time_years": profile_duration - target_exit_year,
            "status": "no ordinary null interception with the entry-mouth worldline by the control event",
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
    profile_start_epoch = control - profile_duration * JULIAN_YEAR_S
    target_exit_epoch = profile_start_epoch + target_exit_year * JULIAN_YEAR_S
    return_intercept_epoch = None
    if "return_signal_intersects_entry_mouth_at_years_from_start" in closure:
        return_intercept_epoch = profile_start_epoch + float(closure["return_signal_intersects_entry_mouth_at_years_from_start"]) * JULIAN_YEAR_S
    if args.csv:
        from estimate_smooth_wormhole_clock_offset import write_csv

        write_csv(args.csv, result)
    output = {
        "scenario": "conditional Phoenix Lights pilot-account timing illustration",
        "control_event_utc": args.control_utc.isoformat(),
        "nominal_witness_event_utc": args.witness_utc.isoformat(),
        "target_emission_event_utc": datetime.fromtimestamp(emitter_epoch, timezone.utc).isoformat(),
        "mouth_history_start_utc": datetime.fromtimestamp(profile_start_epoch, timezone.utc).isoformat(),
        "target_mouth_exit_utc": datetime.fromtimestamp(target_exit_epoch, timezone.utc).isoformat(),
        "flat_model_target_exit_vs_emitter_epoch_residual_seconds": target_exit_epoch - emitter_epoch,
        "elapsed_time_convention": "POSIX seconds derived from UTC labels; leap seconds are omitted; calendar consistency only, not TAI/TDB propagation",
        "return_signal_mouth_intercept_utc": (
            datetime.fromtimestamp(return_intercept_epoch, timezone.utc).isoformat() if return_intercept_epoch is not None else None
        ),
        "assumed_emitter_to_witness_range_km": args.range_km,
        "assumed_initial_and_final_mouth_gap_m": args.mouth_gap_m,
        "assumed_peak_transverse_mouth_excursion_light_years": args.transverse_excursion_ly,
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
            "The reported closure margin uses a flat-space smooth planar mouth worldline and a null return ray; it does not establish a closed timelike curve or field-state matching.",
            "UTC dates are differenced as POSIX timestamps, so leap seconds are omitted; high-precision event matching requires explicit UTC-to-TAI/TT/TDB conversions.",
            "The target-side mouth is assumed co-located with the optical emitter; neither the true historical witness geometry nor the actual three-dimensional Phoenix sightline is known.",
        ],
    }
    if args.csv:
        output["sampled_worldline_csv"] = str(args.csv)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
