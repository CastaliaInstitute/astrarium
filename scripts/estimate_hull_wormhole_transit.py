#!/usr/bin/env python3
"""Compute a conditional A.R.G.O. hull transit through a time-shifted throat.

The throat is the ultrastatic Ellis/Morris-Thorne shape b(r)=r0^2/r,
integrated over a finite matching interval of proper length L. One wormhole
mouth stays on an Earth-following worldline; the other has a prescribed,
closed, subluminal sinusoidal history in a flat exterior. This is a toy
benchmark, not a sourced dynamic wormhole or a navigation solution.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from estimate_smooth_wormhole_clock_offset import estimate

C = 299_792_458.0
G = 6.67430e-11
JULIAN_YEAR_S = 365.25 * 86400.0
JUPITER_MASS_KG = 1.89813e27


def ellis_source(throat_radius_m: float) -> dict[str, float]:
    """Source scales for the massless Ellis throat on one static slice.

    The integrated quantity is int(epsilon dV) over both asymptotic ends;
    it is not the ADM mass of the spacetime.
    """
    a = throat_radius_m
    epsilon_throat = -(C**4) / (8.0 * math.pi * G * a**2)
    integrated = -(math.pi * C**4 * a) / (2.0 * G)
    return {
        "throat_energy_density_j_m3": epsilon_throat,
        "throat_energy_density_mass_equivalent_kg_m3": epsilon_throat / C**2,
        "integrated_eulerian_source_energy_both_ends_j": integrated,
        "integrated_energy_mass_equivalent_kg": integrated / C**2,
        "integrated_energy_jupiter_mass_equivalent": integrated / C**2 / JUPITER_MASS_KG,
    }


def build(
    lookback_years: float,
    throat_radius_m: float,
    throat_length_m: float,
    hull_width_m: float,
    transit_seconds: float,
    beta_values: tuple[float, ...],
) -> dict[str, object]:
    if min(lookback_years, throat_radius_m, throat_length_m, hull_width_m, transit_seconds) <= 0:
        raise ValueError("all lengths, durations, and lookback must be positive")
    if hull_width_m >= 2.0 * throat_radius_m:
        raise ValueError("hull width must be smaller than the throat diameter")
    # Treat transit_seconds as the hull's requested proper time. In the
    # ultrastatic throat, solve L/(gamma*v)=tau exactly.
    beta_gamma = throat_length_m / (C * transit_seconds)
    beta = beta_gamma / math.sqrt(1.0 + beta_gamma**2)
    local_speed = C * beta
    if local_speed >= C:
        raise ValueError("throat transit would require a local speed at or above c")
    gamma = math.sqrt(1.0 + beta_gamma**2)
    proper_crossing_s = throat_length_m / (gamma * local_speed)
    throat_clock_advance_s = throat_length_m / local_speed
    lag_needed_years = lookback_years + throat_clock_advance_s / JULIAN_YEAR_S
    mouth_cases = []
    for beta in beta_values:
        case = estimate(lag_needed_years, beta)
        mouth_cases.append(case)
    return {
        "model": "conditional hull traversal through an Ellis-type throat with a prescribed twin-mouth clock lag",
        "status": "kinematic toy coupled to a static analytic throat; dynamic source and full exterior solution absent",
        "target_exit_lookback_years": lookback_years,
        "throat": {
            "metric": "ds^2 = -c^2 dt_A^2 + dl^2 + (l^2 + r0^2) dOmega^2",
            "shape_function": "b(r)=r0^2/r, redshift function Phi=0",
            "radius_m": throat_radius_m,
            "minimum_clear_diameter_m": 2.0 * throat_radius_m,
            "hull_visible_width_m": hull_width_m,
            "centered_side_clearance_m": (2.0 * throat_radius_m - hull_width_m) / 2.0,
            "proper_crossing_length_m": throat_length_m,
            "local_hull_speed_m_s": local_speed,
            "hull_crossing_proper_time_s": proper_crossing_s,
            "A_mouth_clock_advance_during_throat_s": throat_clock_advance_s,
            **ellis_source(throat_radius_m),
        },
        "mouth_clock_map": {
            "relation": "tau_A(exit)=tau_B(entry)+delta_throat_A; at reunion tau_B=T-lag",
            "exit_epoch_relation": "T_exit=T_entry-lag+delta_throat_A",
            "required_clock_lag_years": lag_needed_years,
            "histories": mouth_cases,
        },
        "limits": [
            "The Earth-following mouth must exist and remain traversable at the historical exit event.",
            "The moving-mouth clock histories are prescribed flat-exterior kinematics, not an Einstein-equation solution.",
            "The Ellis source is a phantom scalar with wrong-sign kinetic energy; no stable physical source is provided.",
            "The integrated source energy is a static-slice integral, not the spacetime ADM mass or a buildable energy budget.",
            "No target-site worldline, full hull envelope, throat junction, tidal force, collision screen, or witness light propagation is solved.",
            "The past exit and ordinary return to the entry event create a chronology loop; no global consistency rule is selected.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lookback-years", type=float, default=2030.964437489177)
    parser.add_argument("--throat-radius-m", type=float, default=5.0)
    parser.add_argument("--throat-length-m", type=float, default=10.0)
    parser.add_argument("--hull-width-m", type=float, default=7.224)
    parser.add_argument("--transit-seconds", type=float, default=300.0)
    parser.add_argument("--beta-max", type=float, nargs="+", default=[0.8, 0.99])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build(
        args.lookback_years,
        args.throat_radius_m,
        args.throat_length_m,
        args.hull_width_m,
        args.transit_seconds,
        tuple(args.beta_max),
    )
    output = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
