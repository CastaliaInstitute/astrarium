#!/usr/bin/env python3
"""Build an ephemeris-anchored Earth worldline and past-event intercept panel.

Earth's orbit about the Sun is queried from JPL Horizons/DE441. The Sun's
motion through the local Galactic frame is approximated over 5,000 years by
its present velocity plus a constant local centripetal acceleration. This is
not a Galactic orbit integration, a historical site solution, or a signal
trajectory. The output is a four-event/worldline coordinate aid for the book.
"""
from __future__ import annotations

import argparse
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from estimate_earth_target_state_3d import (
    C_KM_S,
    GALACTIC_CIRCULAR_SPEED_KM_S,
    GALACTOCENTRIC_RADIUS_KPC,
    HORIZONS_EARTH_SUN,
    KM_PER_KPC,
    KM_PER_LY,
    SECONDS_PER_YEAR,
    SUN_PECULIAR_UVW_KM_S,
    add,
    dot,
    galactic_axes_in_icrf,
    norm,
    scale,
    sub,
)

HORIZONS_API = "https://ssd.jpl.nasa.gov/api/horizons.api"
DEPARTURE_JD_TDB = HORIZONS_EARTH_SUN["departure_jd_tdb"]
TARGET_EVENTS = (
    {
        "name": "7 BCE candidate epoch (17 October placeholder)",
        "jd_tdb": 1719155.5,
        "context": "Year associated with the proposed Jupiter-Saturn conjunction; this calendar day is a computational placeholder.",
    },
    {
        "name": "6 BCE candidate epoch (17 October placeholder)",
        "jd_tdb": 1719520.5,
        "context": "Year associated with proposed Jupiter occultations; this calendar day is a computational placeholder.",
    },
)
EARTH_EQUATORIAL_RADIUS_KM = 6378.137
KM_PER_AU = 149_597_870.7


def horizons_rows(jds: list[float]) -> list[dict[str, object]]:
    params = {
        "format": "json",
        "COMMAND": "'399'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'VECTORS'",
        "CENTER": "'500@10'",
        "TLIST": ",".join(f"{jd:.1f}" for jd in jds),
        "TLIST_TYPE": "'JD'",
        "OUT_UNITS": "'KM-S'",
        "VEC_TABLE": "2",
        "REF_PLANE": "'FRAME'",
        "REF_SYSTEM": "'ICRF'",
        "VEC_CORR": "'NONE'",
        "CSV_FORMAT": "'YES'",
    }
    url = HORIZONS_API + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = json.load(response)
    if payload.get("error"):
        raise RuntimeError(f"JPL Horizons error: {payload['error']}")
    result = payload.get("result", "")
    if "$$SOE" not in result or "$$EOE" not in result:
        raise RuntimeError("JPL Horizons response did not contain vector rows")
    rows: list[dict[str, object]] = []
    for line in result.split("$$SOE", 1)[1].split("$$EOE", 1)[0].splitlines():
        cells = [cell.strip() for cell in line.strip().rstrip(",").split(",")]
        if len(cells) < 8:
            continue
        values = [float(value.replace("D", "E")) for value in cells[2:8]]
        rows.append(
            {
                "jd_tdb": float(cells[0]),
                "calendar_tdb": cells[1],
                "earth_sun_position_km": values[:3],
                "earth_sun_velocity_km_s": values[3:],
            }
        )
    if len(rows) != len(jds):
        raise RuntimeError(f"Expected {len(jds)} Horizons states, received {len(rows)}")
    return rows


def local_solar_galactic_state() -> tuple[tuple[float, ...], tuple[float, ...]]:
    gx, gy, gz = galactic_axes_in_icrf()
    u, v, w = SUN_PECULIAR_UVW_KM_S
    velocity = add(
        add(scale(gx, u), scale(gy, GALACTIC_CIRCULAR_SPEED_KM_S + v)),
        scale(gz, w),
    )
    acceleration_m_s2 = (
        (GALACTIC_CIRCULAR_SPEED_KM_S * 1000.0) ** 2
        / (GALACTOCENTRIC_RADIUS_KPC * KM_PER_KPC * 1000.0)
    )
    acceleration_km_s2 = scale(gx, acceleration_m_s2 / 1000.0)
    return velocity, acceleration_km_s2


def build_result() -> dict[str, object]:
    # One-year cadence over the full 5,000-year interface range. Exact Star-
    # proposal markers are queried separately so they do not depend on cadence.
    start_jd = DEPARTURE_JD_TDB - 5000.0 * 365.25
    sample_params = {
        "format": "json",
        "COMMAND": "'399'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'VECTORS'",
        "CENTER": "'500@10'",
        "START_TIME": f"'JD {start_jd:.1f}'",
        "STOP_TIME": f"'JD {DEPARTURE_JD_TDB:.1f}'",
        "STEP_SIZE": "'1 y'",
        "OUT_UNITS": "'KM-S'",
        "VEC_TABLE": "2",
        "REF_PLANE": "'FRAME'",
        "REF_SYSTEM": "'ICRF'",
        "VEC_CORR": "'NONE'",
        "CSV_FORMAT": "'YES'",
    }
    url = HORIZONS_API + "?" + urllib.parse.urlencode(sample_params)
    with urllib.request.urlopen(url, timeout=90) as response:
        payload = json.load(response)
    if payload.get("error"):
        raise RuntimeError(f"JPL Horizons error: {payload['error']}")
    result = payload.get("result", "")
    if "$$SOE" not in result or "$$EOE" not in result:
        raise RuntimeError("JPL Horizons response did not contain the annual Earth states")
    annual_rows: list[dict[str, object]] = []
    for line in result.split("$$SOE", 1)[1].split("$$EOE", 1)[0].splitlines():
        cells = [cell.strip() for cell in line.strip().rstrip(",").split(",")]
        if len(cells) < 8:
            continue
        values = [float(value.replace("D", "E")) for value in cells[2:8]]
        annual_rows.append(
            {
                "jd_tdb": float(cells[0]),
                "calendar_tdb": cells[1],
                "earth_sun_position_km": values[:3],
                "earth_sun_velocity_km_s": values[3:],
            }
        )
    if len(annual_rows) < 4900:
        raise RuntimeError(f"Expected about 5,000 annual states, received {len(annual_rows)}")

    candidate_rows = horizons_rows([event["jd_tdb"] for event in TARGET_EVENTS])
    candidate_by_jd = {row["jd_tdb"]: row for row in candidate_rows}
    departure_row = annual_rows[-1]
    departure_earth_sun = tuple(departure_row["earth_sun_position_km"])
    solar_velocity, solar_acceleration = local_solar_galactic_state()

    def convert(row: dict[str, object]) -> dict[str, object]:
        lookback_seconds = (DEPARTURE_JD_TDB - float(row["jd_tdb"])) * 86400.0
        earth_sun_delta = sub(tuple(row["earth_sun_position_km"]), departure_earth_sun)
        sun_galactic_delta = add(
            scale(solar_velocity, -lookback_seconds),
            scale(solar_acceleration, 0.5 * lookback_seconds**2),
        )
        delta_km = add(earth_sun_delta, sun_galactic_delta)
        delta_ly = scale(delta_km, 1.0 / KM_PER_LY)
        return {
            "jd_tdb": float(row["jd_tdb"]),
            "calendar_tdb": row["calendar_tdb"],
            "lookback_julian_years": lookback_seconds / SECONDS_PER_YEAR,
            "position_relative_to_present_earth_center_ly": [round(value, 10) for value in delta_ly],
            "distance_from_present_earth_center_ly": norm(delta_ly),
        }

    path = [convert(row) for row in annual_rows]
    markers = []
    for event in TARGET_EVENTS:
        row = candidate_by_jd[event["jd_tdb"]]
        converted = convert(row)
        markers.append({**event, **converted})

    gx, gy, gz = galactic_axes_in_icrf()
    velocity_direction = scale(solar_velocity, 1.0 / norm(solar_velocity))
    transverse_axis = gy
    vertical_axis = gz
    return {
        "title": "DE441-anchored Earth worldline in a local Galactic inertial approximation",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "name": "NASA/JPL Horizons API, Earth center relative to Sun center",
            "target": "399 (Earth geocenter)",
            "center": "500@10 (Sun center)",
            "ephemeris": "DE441",
            "vectors": "geometric Cartesian state, ICRF, TDB, km and km/s",
            "cadence": "1 calendar year over 5,000 Julian years; candidate marker dates queried exactly",
            "api": HORIZONS_API,
        },
        "reference_event": {
            "jd_tdb": DEPARTURE_JD_TDB,
            "calendar_tdb": departure_row["calendar_tdb"],
            "origin": "Earth center at the reference event; A.R.G.O. site offset is not modeled",
        },
        "coordinate_model": {
            "axes": "ICRF Cartesian axes oriented using Galactic center and pole",
            "earth_sun": "sampled from JPL DE441",
            "sun_galactic_motion": "constant present solar velocity (230 km/s circular component plus Schönrich U,V,W) and constant local centripetal acceleration toward Galactic center",
            "solar_velocity_icrf_km_s": [round(value, 9) for value in solar_velocity],
            "solar_speed_km_s": norm(solar_velocity),
            "solar_acceleration_icrf_km_s2": [round(value, 14) for value in solar_acceleration],
            "projection_axes_icrf": {
                "along_present_solar_velocity": [round(value, 12) for value in velocity_direction],
                "galactic_rotation_axis": [round(value, 12) for value in transverse_axis],
                "north_galactic_pole": [round(value, 12) for value in vertical_axis],
            },
            "site_endpoint_bound_km": 2.0 * EARTH_EQUATORIAL_RADIUS_KM,
            "limits": "No complete Milky Way potential, Earth orientation, topocentric site state, witness route, or signal path. The approximate Galactic model is not a navigation solution.",
        },
        "candidate_events": markers,
        "earth_worldline_samples": path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "docs/_static/earth-worldline-intercept.json",
        help="write the sampled Earth worldline and candidate event coordinates as JSON",
    )
    args = parser.parse_args()
    result = build_result()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "samples": len(result["earth_worldline_samples"]),
                "candidate_events": [
                    {
                        "name": event["name"],
                        "lookback_julian_years": event["lookback_julian_years"],
                        "position_relative_to_present_earth_center_ly": event[
                            "position_relative_to_present_earth_center_ly"
                        ],
                        "distance_from_present_earth_center_ly": event[
                            "distance_from_present_earth_center_ly"
                        ],
                    }
                    for event in result["candidate_events"]
                ],
                "site_endpoint_bound_km": result["coordinate_model"]["site_endpoint_bound_km"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
