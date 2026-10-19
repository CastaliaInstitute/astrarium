#!/usr/bin/env python3
"""Export the notebook's computed two-bubble centerline for the web scene.

The exported path is the published model's 1+1 centerline plus its prescribed
small transverse sidestep. It is not a 3+1 geodesic or a collision-safe route.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from estimate_earth_target_state_3d import estimate  # noqa: E402
from solve_two_bubble_encounter import calculate_encounter, sample_worldline  # noqa: E402


def main() -> None:
    target = estimate()
    encounter = calculate_encounter(
        target_time_years=float(target["target_time_in_departure_frame_years"]),
        target_z_lightyears=float(target["target_distance_lightyears"]),
        frame_speed=0.75,
        alpha=10.0,
        omega=0.95,
    )
    samples = sample_worldline(encounter, count=2400)
    points: list[dict[str, float | str]] = []
    for segment, prefix in (("outbound", "outbound"), ("return", "return"), ("closure", "closure")):
        ts = samples[f"{prefix}_t"]
        taus = samples[f"{prefix}_tau"]
        xs = samples[f"{prefix}_x"]
        zs = samples[f"{prefix}_z"]
        for t, tau, x, z in zip(ts, taus, xs, zs):
            point = {"t_years": t, "tau_years": tau, "x_lightyears": x, "z_lightyears": z, "segment": segment}
            if not points or abs(tau - float(points[-1]["tau_years"])) > 1e-10:
                points.append(point)

    payload = {
        "model": "Shoshany-Snodgrass symmetric two-bubble CTG, explicit compact-support profile",
        "frame": "departure-comoving inertial frame S; z aligned with transformed Earth-center target; x is the source profile's transverse sidestep; y=0",
        "parameters": {"U": 0.75, "alpha": 10.0, "omega": 0.95, "support_radius_km": 1.0},
        "target": {
            "t_years": encounter["target_event_time_S_years"],
            "tau_years": encounter["traveler_proper_time_at_target_years"],
            "z_lightyears": encounter["target_event_z_S_lightyears"],
            "distance_lightyears": target["target_distance_lightyears"],
            "position_icrf_lightyears": target["target_position_departure_frame_icrf_lightyears"],
            "interpretation": "Earth-center scenario event; the constructed curve passes through the modeled Earth center and is a collision, not a safe sighting.",
        },
        "summary": {
            "first_leg_years_in_S": encounter["T2_first_leg_years"],
            "first_leg_separation_lightyears": encounter["first_leg_separation_lightyears"],
            "proper_time_at_target_years": encounter["traveler_proper_time_at_target_years"],
            "loop_finish_time_years_in_S": encounter["loop_finish_time_S_years"],
            "max_coordinate_time_years_in_S": max(float(p["t_years"]) for p in points),
            "min_coordinate_time_years_in_S": min(float(p["t_years"]) for p in points),
            "max_tau_years": max(float(p["tau_years"]) for p in points),
        },
        "limitations": [
            "The curve follows the paper's 1+1 geodesic projection; the x sidestep is not independently derived as a 3+1 geodesic.",
            "The CTC is centered on Earth's departure event and the selected ancient Earth-center event; both are modeled collisions.",
            "No Earth-site worldline, finite hull, planetary hazards, self-consistent common ephemeris frame, or photon path is solved.",
        ],
        "points": points,
    }
    out = ROOT / "docs" / "_static" / "data" / "argo-computed-worldline.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
    print(f"Wrote {len(points)} computed worldline samples to {out.relative_to(ROOT)}")
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()
