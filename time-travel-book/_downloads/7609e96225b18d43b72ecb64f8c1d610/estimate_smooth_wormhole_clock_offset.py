#!/usr/bin/env python3
"""Estimate a smooth twin-mouth clock offset for a conditional wormhole model.

This is special-relativistic kinematics in a prescribed flat exterior. It is
not a traversable-wormhole metric, stress-energy solution, source model, or
navigation solution. The moving mouth follows a smooth 1D history that starts
and ends at rest; an optional smoothstep term allows distinct endpoint sites:

    v/c = (D/T)*6u*(1-u) + beta_max*sin(2*pi*u),  u=t/T.

The other mouth is stationary. D is the moving mouth's net endpoint
displacement in light-years (a small positive initial gap is omitted), and T
is in Julian years, so the numerical calculation uses c=1 light-year/year.
The caller chooses the required proper-clock lag; the script solves for T. A
real throat's transit time, gravity, acceleration support, mouth matching, and
hazard environment must be added before using this as a signal route.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

C_M_S = 299_792_458.0
JULIAN_YEAR_S = 365.25 * 24.0 * 60.0 * 60.0


def simpson_mean(function, intervals: int) -> float:
    """Simpson integral over [0, 1], returned as the interval mean."""
    if intervals < 2 or intervals % 2:
        raise ValueError("intervals must be a positive even integer >= 2")
    step = 1.0 / intervals
    weighted = function(0.0) + function(1.0)
    for index in range(1, intervals):
        weighted += (4.0 if index % 2 else 2.0) * function(index * step)
    return weighted * step / 3.0


def beta_at(u: float, duration_years: float, endpoint_distance_ly: float, beta_max: float) -> float:
    return (
        endpoint_distance_ly / duration_years * 6.0 * u * (1.0 - u)
        + beta_max * math.sin(2.0 * math.pi * u)
    )


def clock_lag_years(
    duration_years: float, endpoint_distance_ly: float, beta_max: float, intervals: int
) -> float | None:
    def integrand(u: float) -> float:
        beta = beta_at(u, duration_years, endpoint_distance_ly, beta_max)
        if abs(beta) >= 1.0:
            return math.inf
        return 1.0 - math.sqrt(1.0 - beta * beta)

    mean_lag_rate = simpson_mean(integrand, intervals)
    if not math.isfinite(mean_lag_rate):
        return None
    return duration_years * mean_lag_rate


def estimate(
    lookback_years: float,
    beta_max: float,
    endpoint_distance_ly: float = 0.0,
    intervals: int = 20_000,
) -> dict[str, float | str]:
    if lookback_years <= 0:
        raise ValueError("lookback_years must be positive")
    if not 0 < beta_max < 1:
        raise ValueError("beta_max must be strictly between 0 and 1")
    if endpoint_distance_ly < 0:
        raise ValueError("endpoint_distance_ly must be nonnegative; use the opposite axis for a negative displacement")

    lower = max(1.0, endpoint_distance_ly * 1.001)
    lower_lag = clock_lag_years(lower, endpoint_distance_ly, beta_max, intervals)
    while lower_lag is None:
        lower *= 1.2
        lower_lag = clock_lag_years(lower, endpoint_distance_ly, beta_max, intervals)
    if lower_lag >= lookback_years:
        raise ValueError("no subluminal solution for this profile, endpoint distance, and requested clock lag")

    upper = lower * 2.0
    upper_lag = clock_lag_years(upper, endpoint_distance_ly, beta_max, intervals)
    while upper_lag is None or upper_lag < lookback_years:
        upper *= 2.0
        upper_lag = clock_lag_years(upper, endpoint_distance_ly, beta_max, intervals)

    for _ in range(70):
        midpoint = (lower + upper) / 2.0
        midpoint_lag = clock_lag_years(midpoint, endpoint_distance_ly, beta_max, intervals)
        if midpoint_lag is None or midpoint_lag >= lookback_years:
            upper = midpoint
        else:
            lower = midpoint
    exterior_years = (lower + upper) / 2.0
    lag_fraction = lookback_years / exterior_years
    moving_mouth_proper_years = exterior_years - lookback_years
    maximum_displacement_ly = 0.0
    total_path_length_ly = 0.0
    maximum_speed = 0.0
    maximum_acceleration_beta_per_year = 0.0
    previous_position = 0.0
    samples = 20_000
    for index in range(samples + 1):
        u = index / samples
        beta = beta_at(u, exterior_years, endpoint_distance_ly, beta_max)
        position = (
            endpoint_distance_ly * (3.0 * u * u - 2.0 * u**3)
            + beta_max * exterior_years / (2.0 * math.pi) * (1.0 - math.cos(2.0 * math.pi * u))
        )
        acceleration_beta = abs(
            endpoint_distance_ly / exterior_years**2 * 6.0 * (1.0 - 2.0 * u)
            + beta_max * 2.0 * math.pi / exterior_years * math.cos(2.0 * math.pi * u)
        )
        maximum_speed = max(maximum_speed, abs(beta))
        maximum_acceleration_beta_per_year = max(maximum_acceleration_beta_per_year, acceleration_beta)
        maximum_displacement_ly = max(maximum_displacement_ly, abs(position))
        if index:
            total_path_length_ly += abs(position - previous_position)
        previous_position = position
    peak_acceleration_m_s2 = maximum_acceleration_beta_per_year * C_M_S / JULIAN_YEAR_S

    return {
        "model": "flat-exterior smooth twin-mouth kinematics with smoothstep endpoint displacement",
        "lookback_clock_offset_years": lookback_years,
        "endpoint_displacement_light_years": endpoint_distance_ly,
        "maximum_speed_fraction_of_c": maximum_speed,
        "sinusoidal_velocity_amplitude_fraction_of_c": beta_max,
        "clock_lag_fraction_of_exterior_duration": lag_fraction,
        "exterior_duration_years": exterior_years,
        "moving_mouth_proper_time_years": moving_mouth_proper_years,
        "stationary_mouth_proper_time_years": exterior_years,
        "maximum_displacement_from_initial_site_light_years": maximum_displacement_ly,
        "total_path_length_light_years": total_path_length_ly,
        "maximum_coordinate_acceleration_m_s2": peak_acceleration_m_s2,
        "profile": "v/c = (D/T)*6u*(1-u) + beta_max*sin(2*pi*u); x(0)=0, x(T)=D",
    }


def write_csv(path: Path, summary: dict[str, float | str], rows: int = 2001) -> None:
    duration = float(summary["exterior_duration_years"])
    beta_max = float(summary["sinusoidal_velocity_amplitude_fraction_of_c"])
    endpoint_distance = float(summary["endpoint_displacement_light_years"])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "exterior_time_years",
                "position_light_years",
                "velocity_over_c",
                "stationary_mouth_clock_years",
                "moving_mouth_clock_years",
                "clock_lag_years",
            ]
        )
        for index in range(rows):
            u = index / (rows - 1)
            theta = 2.0 * math.pi * u
            velocity = beta_at(u, duration, endpoint_distance, beta_max)
            position = (
                endpoint_distance * (3.0 * u * u - 2.0 * u**3)
                + beta_max * duration / (2.0 * math.pi) * (1.0 - math.cos(theta))
            )
            # Integrate the accumulated lag on a fixed, even grid to avoid
            # changing quadrature resolution from row to row.
            partial_intervals = 2000
            if u == 0:
                lag_at_u = 0.0
            else:
                lag_at_u = duration * u * simpson_mean(
                    lambda s: 1.0
                    - math.sqrt(1.0 - beta_at(u * s, duration, endpoint_distance, beta_max) ** 2),
                    partial_intervals,
                )
            moving_clock = duration * u - lag_at_u
            writer.writerow(
                [
                    f"{duration * u:.9f}",
                    f"{position:.9f}",
                    f"{velocity:.12f}",
                    f"{duration * u:.9f}",
                    f"{moving_clock:.9f}",
                    f"{lag_at_u:.9f}",
                ]
            )
    if not math.isclose(
        float(summary["clock_lag_fraction_of_exterior_duration"]) * duration,
        float(summary["lookback_clock_offset_years"]),
        rel_tol=1e-12,
    ):
        raise ArithmeticError("clock-offset integration did not reproduce the requested lookback")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lookback-years", type=float, default=2000.0)
    parser.add_argument("--beta-max", type=float, default=0.8)
    parser.add_argument("--endpoint-displacement-ly", type=float, default=0.0)
    parser.add_argument("--intervals", type=int, default=20_000)
    parser.add_argument("--csv", type=Path, help="optional sampled continuous worldline/clock map")
    args = parser.parse_args()

    result = estimate(args.lookback_years, args.beta_max, args.endpoint_displacement_ly, args.intervals)
    if args.csv:
        write_csv(args.csv, result)
        result["csv_samples"] = str(args.csv)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
