#!/usr/bin/env python3
"""Reproduce the symmetric two-bubble CTC kinematic benchmark.

This evaluates the flat-background closure equations associated with the
Shoshany-Snodgrass prescribed two-bubble geometry. It is not a geodesic
integrator, Einstein-tensor/source calculation, finite-hull model, or a
retargeted solution through a real sighting event.
"""
from __future__ import annotations

import argparse
import json


def calculate(
    frame_speed_fraction_c: float = 0.75,
    alpha: float = 10.0,
    duration_ratio: float = 0.95,
    lookback_years: float = 2031.0,
    solar_speed_km_s: float = 230.0,
    target_displacement_ly: float | None = None,
) -> dict[str, float | str]:
    u = frame_speed_fraction_c
    omega = duration_ratio
    if not 0 < u < 1:
        raise ValueError("frame_speed_fraction_c must be between 0 and 1")
    if alpha <= 0 or not 0 < omega < 1:
        raise ValueError("alpha must be positive and duration_ratio must be in (0, 1)")
    if lookback_years <= 0 or solar_speed_km_s < 0:
        raise ValueError("lookback_years must be positive and solar_speed_km_s nonnegative")

    # Paper's symmetric smooth-profile example: vbar = u[1+omega(alpha-1)/4].
    v = u * (1.0 + omega * (alpha - 1.0) / 4.0)
    critical_u = 2.0 * v / (1.0 + v * v)
    finish_ratio = (2.0 * v - u * (1.0 + v * v)) / (v - u)
    lookback_per_leg_time = -finish_ratio
    distance_ratio = lookback_per_leg_time / v

    # Flat 1+1 endpoint extension, with c=1, t in years, z in light-years.
    # By default, project constant solar_speed_km_s along +z for the full
    # lookback. The sign is a scenario choice; this is not Earth's reconstructed
    # displacement. t_C = A*T + B*z_C. Solve for T at t_C=-lookback.
    # This is a kinematic scale diagnostic, not the published metric.
    a = (2.0 * v - u * (1.0 + v * v)) / (v - u)
    b = (v * u - 1.0) / (v - u)
    if target_displacement_ly is None:
        target_displacement_ly = (solar_speed_km_s / 299_792.458) * lookback_years
    first_leg_time_years = (-lookback_years - b * target_displacement_ly) / a
    first_leg_distance_ly = v * first_leg_time_years

    return {
        "model": "symmetric two-bubble flat-background CTC kinematics",
        "source": "Shoshany and Snodgrass (2024), equations for symmetric average-speed closure",
        "frame_speed_fraction_c_U": u,
        "profile_parameter_alpha": alpha,
        "duration_ratio_omega": omega,
        "average_bubble_separation_speed_fraction_c_V": v,
        "ctc_threshold_Ucrit": critical_u,
        "ctc_condition_satisfied": float(u > critical_u),
        "same_spatial_point_finish_time_over_first_leg_time": finish_ratio,
        "lookback_fraction_of_first_leg_time": lookback_per_leg_time,
        "lookback_over_first_leg_distance_over_c": distance_ratio,
        "lookback_years_input": lookback_years,
        "solar_motion_projection_speed_km_s": solar_speed_km_s,
        "target_displacement_ly_input": target_displacement_ly,
        "flat_endpoint_time_coefficient": a,
        "flat_endpoint_displacement_coefficient": b,
        "flat_endpoint_first_leg_time_years": first_leg_time_years,
        "flat_endpoint_first_leg_distance_ly": first_leg_distance_ly,
        "scope": "endpoint extension is kinematic only; it is not the published compact-support metric retargeted to a moving Earth/witness world-tube",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frame-speed-fraction-c", type=float, default=0.75)
    parser.add_argument("--alpha", type=float, default=10.0)
    parser.add_argument("--duration-ratio", type=float, default=0.95)
    parser.add_argument("--lookback-years", type=float, default=2031.0)
    parser.add_argument("--solar-speed-km-s", type=float, default=230.0)
    parser.add_argument("--target-displacement-ly", type=float, help="override the one-axis solar-motion projection")
    args = parser.parse_args()
    result = calculate(
        frame_speed_fraction_c=args.frame_speed_fraction_c,
        alpha=args.alpha,
        duration_ratio=args.duration_ratio,
        lookback_years=args.lookback_years,
        solar_speed_km_s=args.solar_speed_km_s,
        target_displacement_ly=args.target_displacement_ly,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
