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

AU_M = 149_597_870_700.0
LY_M = 9.4607304725808e15
KPC_M = 3.085677581491367e19
JULIAN_YEAR_S = 365.25 * 24.0 * 60.0 * 60.0


def calculate(
    frame_speed_fraction_c: float = 0.75,
    alpha: float = 10.0,
    duration_ratio: float = 0.95,
    lookback_years: float = 2031.0,
    solar_speed_km_s: float = 230.0,
    earth_orbital_speed_km_s: float = 29.78,
    earth_rotation_speed_bound_km_s: float = 0.465,
    galactocentric_radius_kpc: float = 8.2,
    earth_orbit_offset_bound_au: float = 2.0,
    target_displacement_ly: float | None = None,
) -> dict[str, float | str]:
    u = frame_speed_fraction_c
    omega = duration_ratio
    if not 0 < u < 1:
        raise ValueError("frame_speed_fraction_c must be between 0 and 1")
    if alpha <= 0 or not 0 < omega < 1:
        raise ValueError("alpha must be positive and duration_ratio must be in (0, 1)")
    if (lookback_years <= 0 or solar_speed_km_s < 0 or earth_orbital_speed_km_s < 0
            or earth_rotation_speed_bound_km_s < 0 or galactocentric_radius_kpc <= 0):
        raise ValueError("lookback and radius must be positive; speeds must be nonnegative")
    if earth_orbit_offset_bound_au < 0:
        raise ValueError("earth_orbit_offset_bound_au must be nonnegative")

    # Paper's symmetric smooth-profile example: vbar = u[1+omega(alpha-1)/4].
    v = u * (1.0 + omega * (alpha - 1.0) / 4.0)
    critical_u = 2.0 * v / (1.0 + v * v)
    finish_ratio = (2.0 * v - u * (1.0 + v * v)) / (v - u)
    lookback_per_leg_time = -finish_ratio
    distance_ratio = lookback_per_leg_time / v

    # Flat 1+1 endpoint extension, with c=1, t in years, z in light-years.
    # S is the departure-comoving inertial frame used by the published model.
    # In a one-axis Galactic frame, approximate the historical Earth event as
    # sharing the Sun's linear Galactic drift, while A.R.G.O.'s departure speed
    # also includes Earth's orbital speed. Lorentz-transform the event into S.
    # Orbital phase, site rotation, and Galactic curvature are retained as a
    # projected offset bound, not represented by a complete ephemeris.
    a = (2.0 * v - u * (1.0 + v * v)) / (v - u)
    b = (v * u - 1.0) / (v - u)
    elapsed_s = lookback_years * JULIAN_YEAR_S
    galactic_radius_m = galactocentric_radius_kpc * KPC_M
    galactic_acceleration_m_s2 = (solar_speed_km_s * 1000.0) ** 2 / galactic_radius_m
    galactic_tangent_offset_m = 0.5 * galactic_acceleration_m_s2 * elapsed_s**2
    galactic_curvature_bound_ly = galactic_tangent_offset_m / LY_M
    earth_orbit_phase_bound_ly = earth_orbit_offset_bound_au * AU_M / LY_M
    earth_rotation_drift_bound_ly = (earth_rotation_speed_bound_km_s / 299_792.458) * lookback_years
    beta_sun = solar_speed_km_s / 299_792.458
    beta_earth_orbit = earth_orbital_speed_km_s / 299_792.458
    beta_departure = (beta_sun + beta_earth_orbit) / (1.0 + beta_sun * beta_earth_orbit)
    gamma_departure = 1.0 / (1.0 - beta_departure**2) ** 0.5
    target_time_galactic_years = -lookback_years
    target_position_galactic_ly = -beta_sun * lookback_years
    target_time_departure_years = gamma_departure * (
        target_time_galactic_years - beta_departure * target_position_galactic_ly
    )
    target_position_departure_ly = gamma_departure * (
        target_position_galactic_ly - beta_departure * target_time_galactic_years
    )
    target_offset_bound_ly = (
        earth_orbit_phase_bound_ly + earth_rotation_drift_bound_ly + galactic_curvature_bound_ly
    )
    if target_displacement_ly is None:
        target_displacement_ly = target_position_departure_ly
    first_leg_time_years = (target_time_departure_years - b * target_displacement_ly) / a
    first_leg_distance_ly = v * first_leg_time_years
    target_min_ly = target_displacement_ly - target_offset_bound_ly
    target_max_ly = target_displacement_ly + target_offset_bound_ly
    first_leg_time_min_years = (target_time_departure_years - b * target_min_ly) / a
    first_leg_time_max_years = (target_time_departure_years - b * target_max_ly) / a
    closure_segment_speed_fraction_c = target_displacement_ly / target_time_departure_years
    closure_segment_is_timelike = (
        target_time_departure_years < 0
        and abs(target_displacement_ly) < abs(target_time_departure_years)
    )
    closure_segment_proper_time_years = (
        (target_time_departure_years**2 - target_displacement_ly**2) ** 0.5
        if closure_segment_is_timelike else float("nan")
    )

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
        "reference_frame": "departure-comoving inertial frame S, as in the published construction",
        "target_displacement_model": "one-axis Lorentz transform from a Galactic frame to the departure-comoving frame, with projected orbit, rotation, and Galactic-curvature bounds; illustrative, not an ephemeris reconstruction",
        "solar_galactic_speed_km_s_assumed": solar_speed_km_s,
        "earth_orbital_speed_km_s_assumed": earth_orbital_speed_km_s,
        "earth_rotation_speed_bound_km_s_assumed": earth_rotation_speed_bound_km_s,
        "galactocentric_radius_kpc_assumed": galactocentric_radius_kpc,
        "galactic_acceleration_m_s2_estimate": galactic_acceleration_m_s2,
        "galactic_curvature_offset_bound_ly": galactic_curvature_bound_ly,
        "departure_speed_in_galactic_frame_km_s_collinear_assumption": beta_departure * 299_792.458,
        "departure_gamma": gamma_departure,
        "target_event_time_departure_frame_years": target_time_departure_years,
        "target_event_position_departure_frame_ly_before_bounds": target_position_departure_ly,
        "earth_orbit_offset_bound_au_assumed": earth_orbit_offset_bound_au,
        "target_offset_bound_ly_from_orbit_rotation_curvature": target_offset_bound_ly,
        "target_displacement_ly_central_or_override": target_displacement_ly,
        "target_displacement_ly_min_under_projected_bounds": target_min_ly,
        "target_displacement_ly_max_under_projected_bounds": target_max_ly,
        "straight_target_to_departure_segment_is_timelike_in_flat_extension": float(closure_segment_is_timelike),
        "straight_target_to_departure_segment_speed_fraction_c": closure_segment_speed_fraction_c,
        "straight_target_to_departure_segment_proper_time_years": closure_segment_proper_time_years,
        "flat_endpoint_time_coefficient": a,
        "flat_endpoint_displacement_coefficient": b,
        "flat_endpoint_first_leg_time_years": first_leg_time_years,
        "flat_endpoint_first_leg_time_min_years": min(first_leg_time_min_years, first_leg_time_max_years),
        "flat_endpoint_first_leg_time_max_years": max(first_leg_time_min_years, first_leg_time_max_years),
        "flat_endpoint_first_leg_distance_ly": first_leg_distance_ly,
        "scope": "endpoint extension is kinematic only; it is not the published compact-support metric retargeted to a moving Earth/witness world-tube",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frame-speed-fraction-c", type=float, default=0.75)
    parser.add_argument("--alpha", type=float, default=10.0)
    parser.add_argument("--duration-ratio", type=float, default=0.95)
    parser.add_argument("--lookback-years", type=float, default=2031.0)
    parser.add_argument("--solar-speed-km-s", type=float, default=230.0, help="assumed projected Galactic speed in the one-axis illustration")
    parser.add_argument("--earth-orbital-speed-km-s", type=float, default=29.78)
    parser.add_argument("--earth-rotation-speed-bound-km-s", type=float, default=0.465)
    parser.add_argument("--galactocentric-radius-kpc", type=float, default=8.2)
    parser.add_argument("--earth-orbit-offset-bound-au", type=float, default=2.0, help="projected bound on Earth's orbital position difference between epochs")
    parser.add_argument("--target-displacement-ly", type=float, help="override target displacement in the departure-comoving inertial frame")
    args = parser.parse_args()
    result = calculate(
        frame_speed_fraction_c=args.frame_speed_fraction_c,
        alpha=args.alpha,
        duration_ratio=args.duration_ratio,
        lookback_years=args.lookback_years,
        solar_speed_km_s=args.solar_speed_km_s,
        galactocentric_radius_kpc=args.galactocentric_radius_kpc,
        earth_orbit_offset_bound_au=args.earth_orbit_offset_bound_au,
        target_displacement_ly=args.target_displacement_ly,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
