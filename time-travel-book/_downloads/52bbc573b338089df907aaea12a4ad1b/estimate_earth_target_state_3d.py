#!/usr/bin/env python3
"""Estimate the 6 BCE Earth-center event in the present Earth-rest frame.

Solar-system relative states are frozen from JPL Horizons (Earth center relative
Sun center, DE441-based, geometric ICRF vectors, TDB). Solar Galactic motion is
a local constant-velocity plus constant-acceleration approximation. This is a
vector kinematic reference calculation, not a Galactic orbit integration.
"""
from __future__ import annotations

from math import cos, pi, sin, sqrt

C_KM_S = 299_792.458
KM_PER_LY = 9.4607304725808e12
SECONDS_PER_YEAR = 365.25 * 24 * 3600
KM_PER_AU = 149_597_870.7

# Horizons: target 399 (Earth center), center 500@10 (Sun center),
# VECTORS / VEC_TABLE=2 / geometric / ICRF / FRAME / TDB / KM-S.
# Epochs: JD TDB 1719520.5 = 0006-Oct-17 B.C. (Julian calendar),
#         JD TDB 2461330.5 = 2026-Oct-17 A.D.
HORIZONS_EARTH_SUN = {
    "target": 399,
    "center": "500@10",
    "ancient_jd_tdb": 1719520.5,
    "departure_jd_tdb": 2461330.5,
    "ancient_position_km": (9.701676704389264e7, 1.021062593296688e8, 4.483358971095032e7),
    "ancient_velocity_km_s": (-23.00495860430597, 17.84614940046488, 7.835514783700567),
    "departure_position_km": (1.369887116888706e8, 5.404765584697053e7, 2.342808456130781e7),
    "departure_velocity_km_s": (-12.26195718077133, 25.00520005222703, 10.83863899522872),
    "source": "NASA/JPL Horizons API, DE441-based planetary state",
}

# Local Galactic model: circular speed plus Schönrich et al. solar peculiar
# velocity (U toward Galactic center, V in rotation direction, W to NGP).
GALACTIC_CIRCULAR_SPEED_KM_S = 230.0
SUN_PECULIAR_UVW_KM_S = (11.1, 12.24, 7.25)
GALACTOCENTRIC_RADIUS_KPC = 8.2
KM_PER_KPC = 3.085677581491367e16


def dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return sum(x * y for x, y in zip(a, b))


def add(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(x + y for x, y in zip(a, b))


def sub(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(x - y for x, y in zip(a, b))


def scale(a: tuple[float, ...], k: float) -> tuple[float, ...]:
    return tuple(k * x for x in a)


def norm(a: tuple[float, ...]) -> float:
    return sqrt(dot(a, a))


def unit_from_radec(ra_deg: float, dec_deg: float) -> tuple[float, float, float]:
    ra, dec = ra_deg * pi / 180, dec_deg * pi / 180
    return cos(dec) * cos(ra), cos(dec) * sin(ra), sin(dec)


def galactic_axes_in_icrf() -> tuple[tuple[float, ...], ...]:
    """Return Galactic x/y/z unit axes expressed in ICRF coordinates."""
    x = unit_from_radec(266.4051, -28.936175)  # Galactic center
    z = unit_from_radec(192.85948, 27.12825)  # North Galactic pole
    cross = (z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0])
    y = scale(cross, 1.0 / norm(cross))
    return x, y, z


def estimate() -> dict[str, object]:
    data = HORIZONS_EARTH_SUN
    interval_days = data["departure_jd_tdb"] - data["ancient_jd_tdb"]
    lookback_s = interval_days * 86400.0
    lookback_y = interval_days / 365.25

    gx, gy, gz = galactic_axes_in_icrf()
    u, v, w = SUN_PECULIAR_UVW_KM_S
    solar_velocity = add(add(scale(gx, u), scale(gy, GALACTIC_CIRCULAR_SPEED_KM_S + v)), scale(gz, w))
    earth_orbit_velocity_now = data["departure_velocity_km_s"]
    departure_velocity = add(solar_velocity, earth_orbit_velocity_now)

    # Approximate local Galactic acceleration toward the Galactic center.
    acceleration_m_s2 = (GALACTIC_CIRCULAR_SPEED_KM_S * 1000.0) ** 2 / (GALACTOCENTRIC_RADIUS_KPC * KM_PER_KPC * 1000.0)
    acceleration_km_s2 = scale(gx, acceleration_m_s2 / 1000.0)

    delta_earth_sun = sub(data["ancient_position_km"], data["departure_position_km"])
    target_delta_galactic = add(
        sub(delta_earth_sun, scale(solar_velocity, lookback_s)),
        scale(acceleration_km_s2, 0.5 * lookback_s**2),
    )

    beta = scale(departure_velocity, 1.0 / C_KM_S)
    beta2 = dot(beta, beta)
    gamma = 1.0 / sqrt(1.0 - beta2)
    dt_galactic_s = -lookback_s
    target_delta_departure = add(
        add(target_delta_galactic,
            scale(beta, (gamma - 1.0) * dot(beta, target_delta_galactic) / beta2)),
        scale(beta, -gamma * C_KM_S * dt_galactic_s),
    )
    time_departure_s = gamma * (C_KM_S * dt_galactic_s - dot(beta, target_delta_galactic)) / C_KM_S
    position_ly = scale(target_delta_departure, 1.0 / KM_PER_LY)

    vhat = scale(departure_velocity, 1.0 / norm(departure_velocity))
    along_velocity_ly = dot(position_ly, vhat)
    cross_track = sub(position_ly, scale(vhat, along_velocity_ly))
    distance_ly = norm(position_ly)
    cosine = max(-1.0, min(1.0, along_velocity_ly / distance_ly))

    earth_orbit_direction = scale(earth_orbit_velocity_now, 1.0 / norm(earth_orbit_velocity_now))
    along_orbit_ly = dot(position_ly, earth_orbit_direction)
    orbit_cross_track = sub(position_ly, scale(earth_orbit_direction, along_orbit_ly))
    orbit_cosine = max(-1.0, min(1.0, along_orbit_ly / distance_ly))

    return {
        "scenario": "Earth center at 6 BCE-10-17 Julian, departure at 2026-10-17 TDB",
        "source": data["source"],
        "earth_sun_state": data,
        "lookback_years_galactic": lookback_y,
        "target_time_in_departure_frame_years": time_departure_s / SECONDS_PER_YEAR,
        "target_position_departure_frame_icrf_lightyears": position_ly,
        "target_distance_lightyears": distance_ly,
        "departure_velocity_icrf_km_s": departure_velocity,
        "departure_speed_km_s": norm(departure_velocity),
        "target_projection_along_departure_velocity_lightyears": along_velocity_ly,
        "target_cross_track_from_departure_velocity_axis_lightyears": norm(cross_track),
        "target_angle_from_departure_velocity_axis_degrees": __import__("math").acos(cosine) * 180.0 / pi,
        "target_projection_along_earth_orbital_velocity_lightyears": along_orbit_ly,
        "target_cross_track_from_earth_orbital_velocity_axis_lightyears": norm(orbit_cross_track),
        "target_angle_from_earth_orbital_velocity_axis_degrees": __import__("math").acos(orbit_cosine) * 180.0 / pi,
        "galactic_model": {
            "circular_speed_km_s": GALACTIC_CIRCULAR_SPEED_KM_S,
            "solar_peculiar_UVW_km_s": SUN_PECULIAR_UVW_KM_S,
            "galactocentric_radius_kpc": GALACTOCENTRIC_RADIUS_KPC,
            "acceleration_model": "constant local centripetal acceleration over lookback",
        },
        "interpretation": "The spatial axis for the 1D loop is chosen along this transformed target displacement. The Galactic potential and ancient Earth rotation/site state are approximated or omitted; this is not a historical observer intercept.",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(estimate(), indent=2))
