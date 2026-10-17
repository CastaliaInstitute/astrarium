#!/usr/bin/env python3
"""Exact slice integral of the Eulerian density for a prescribed oblate shift bubble.

The result applies only to the constant-velocity, unit-lapse, flat-slice metric
and compact quintic ellipsoidal profile documented in docs/temporal-drive-candidate.md.
It is neither an ADM mass nor a physical warp-drive energy budget.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

C = 299_792_458.0  # exact, m/s
G = 6.67430e-11  # CODATA 2022, m^3 kg^-1 s^-2


def calculate(a_m: float, b_m: float, wall_parameter: float, speed_fraction_c: float) -> dict[str, float | str]:
    if a_m <= 0 or b_m <= 0 or not 0 < wall_parameter < 2:
        raise ValueError("semiaxes must be positive and wall_parameter must be in (0, 2)")
    v = speed_fraction_c * C
    delta = wall_parameter
    # For F(u)=1-10u^3+15u^4-6u^5, the exact profile integral is
    # integral_(-1/2)^(1/2) (1+delta*s)^2 [dF/ds]^2 ds
    #   = 10/7 + 5 delta^2/154.
    profile_integral = 10.0 / 7.0 + 5.0 * delta**2 / 154.0
    energy = -(C**2 * v**2 * a_m) / (12.0 * G * delta) * profile_integral
    max_density_scale = (C**4 / (32.0 * math.pi * G)) * speed_fraction_c**2 / (delta * min(a_m, b_m))**2
    return {
        "method": "analytic ellipsoidal-coordinate reduction for quintic wall profile",
        "axial_semiaxis_m": a_m,
        "radial_semiaxis_m": b_m,
        "dimensionless_wall_parameter": delta,
        "speed_fraction_c": speed_fraction_c,
        "profile_integral": profile_integral,
        "volume_integral_eulerian_density_J": energy,
        "volume_integral_equivalent_mass_kg": energy / C**2,
        "local_density_order_scale_J_m3": max_density_scale,
        "shape_result": "integral independent of radial semiaxis b for this chosen profile; proportional to axial semiaxis a",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--axial-semiaxis-m", type=float, default=10.0)
    parser.add_argument("--radial-semiaxis-m", type=float, default=20.0)
    parser.add_argument("--wall-parameter", type=float, default=0.1)
    parser.add_argument("--speed-fraction-c", type=float, default=0.1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = calculate(args.axial_semiaxis_m, args.radial_semiaxis_m, args.wall_parameter, args.speed_fraction_c)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
