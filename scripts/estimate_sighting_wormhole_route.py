#!/usr/bin/env python3
"""Compute a conditional historical-emitter / moving-mouth sighting scenario.

This joins a dated witness event to a target-side light emission, then asks
what smooth flat-exterior twin-mouth kinematics would accumulate that clock
offset. In --earth-worldline mode, the geocenter endpoint event and velocity
are imposed in the target endpoint rest chart. It still does not model an
actual wormhole metric, Earth-fixed observer worldline, historical emitter,
or material vehicle arrival. Paired --control-jd-tdb/--witness-jd-tdb inputs
enable BCE timing calculations only; ephemeris anchoring and Earth clearance
remain available only in the UTC mode.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estimate_earth_worldline_intercept import local_solar_galactic_state  # noqa: E402
from estimate_earth_target_state_3d import KM_PER_LY  # noqa: E402
from estimate_smooth_wormhole_clock_offset import (
    beta_at,
    beta_derivative_per_year,
    estimate,
    position_at,
    simpson_mean,
)  # noqa: E402

C_M_S = 299_792_458.0
JULIAN_YEAR_S = 365.25 * 86400.0
SECONDS_PER_DAY = 86400.0
METERS_PER_LIGHT_YEAR = C_M_S * JULIAN_YEAR_S
EARTH_EQUATORIAL_RADIUS_KM = 6378.137
EARTH_POLAR_RADIUS_KM = 6356.7523142


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamps must include a UTC offset or Z")
    return parsed.astimezone(timezone.utc)


def event_epoch_label(
    epoch_s: float | Decimal, jd_tdb_mode: bool, jd_anchor_tdb: Decimal | None = None
) -> str:
    """Format a route-coordinate epoch without forcing BCE dates into datetime."""
    if jd_tdb_mode:
        if jd_anchor_tdb is None:
            raise ValueError("JD TDB event labels require an anchor Julian date")
        with localcontext() as context:
            context.prec = 30
            epoch_delta = epoch_s if isinstance(epoch_s, Decimal) else Decimal(str(epoch_s))
            jd = jd_anchor_tdb + epoch_delta / Decimal(str(SECONDS_PER_DAY))
        return f"JD TDB {jd:.15f}"
    return datetime.fromtimestamp(epoch_s, timezone.utc).isoformat()


def lorentz_transform_event_to_rest(
    delta_time_s: float,
    delta_position_km: tuple[float, float, float],
    frame_velocity_beta: tuple[float, float, float],
) -> tuple[float, tuple[float, float, float]]:
    """Transform an event separation from ICRF to the frame moving at beta."""
    beta2 = sum(value*value for value in frame_velocity_beta)
    gamma = 1.0/math.sqrt(1.0-beta2)
    beta_dot_r = sum(frame_velocity_beta[i]*delta_position_km[i] for i in range(3))
    c_km_s = C_M_S/1000.0
    time_rest = gamma*(delta_time_s-beta_dot_r/c_km_s)
    spatial_factor = (
        (gamma-1.0)*beta_dot_r/beta2-gamma*c_km_s*delta_time_s
        if beta2 > 0.0 else 0.0
    )
    position_rest = tuple(
        delta_position_km[i]+spatial_factor*frame_velocity_beta[i] for i in range(3)
    )
    return time_rest, position_rest


def lorentz_transform_velocity_to_rest(
    velocity_beta: tuple[float, float, float],
    frame_velocity_beta: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Transform a 3-velocity from ICRF to an inertial frame moving at beta."""
    beta2 = sum(value*value for value in frame_velocity_beta)
    gamma = 1.0/math.sqrt(1.0-beta2)
    dot = sum(velocity_beta[i]*frame_velocity_beta[i] for i in range(3))
    factor = ((gamma-1.0)*dot/beta2-gamma) if beta2 > 0.0 else 0.0
    return tuple(
        (velocity_beta[i]+factor*frame_velocity_beta[i])/(gamma*(1.0-dot))
        for i in range(3)
    )


def lorentz_transform_spatial_vector_to_rest(
    vector: tuple[float, float, float], frame_velocity_beta: tuple[float, float, float]
) -> tuple[float, float, float]:
    """Transform a purely spatial vector to a frame moving at beta."""
    beta2 = sum(value*value for value in frame_velocity_beta)
    if beta2 == 0.0:
        return vector
    gamma = 1.0/math.sqrt(1.0-beta2)
    dot = sum(vector[i]*frame_velocity_beta[i] for i in range(3))
    factor = (gamma-1.0)*dot/beta2
    return tuple(vector[i]+factor*frame_velocity_beta[i] for i in range(3))


def query_earth_sun_icrf_utc(
    events: list[datetime],
) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    """Query DE441 Earth-center ICRF positions and velocities relative to Sun."""
    params = {
        "format": "json",
        "COMMAND": "'399'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'VECTORS'",
        "CENTER": "'500@10'",
        "TLIST": " ".join(f"'{event.strftime('%Y-%b-%d %H:%M:%S.%f')}'" for event in events),
        "TLIST_TYPE": "'CAL'",
        "TIME_TYPE": "'UT'",
        "OUT_UNITS": "'KM-S'",
        "VEC_TABLE": "'2'",
        "REF_PLANE": "'FRAME'",
        "REF_SYSTEM": "'ICRF'",
        "VEC_CORR": "'NONE'",
        "TIME_DIGITS": "'FRACSEC'",
        "CSV_FORMAT": "'YES'",
    }
    url = "https://ssd.jpl.nasa.gov/api/horizons.api?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = json.load(response)
    if payload.get("error"):
        raise RuntimeError(f"JPL Horizons error: {payload['error']}")
    block = payload.get("result", "")
    if "$$SOE" not in block or "$$EOE" not in block:
        raise RuntimeError("JPL Horizons response did not contain vector rows")
    states: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
    for line in block.split("$$SOE", 1)[1].split("$$EOE", 1)[0].splitlines():
        cells = [cell.strip() for cell in line.strip().rstrip(",").split(",")]
        if len(cells) < 8:
            continue
        values = [float(value.replace("D", "E")) for value in cells[2:8]]
        states.append(((values[0], values[1], values[2]), (values[3], values[4], values[5])))
    if len(states) != len(events):
        raise RuntimeError(f"Expected {len(events)} Earth states, received {len(states)}")
    return states


def query_sun_icrf_from_geodetic_site_utc(
    events: list[datetime], longitude_latitude_altitude: tuple[float, float, float]
) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    """Query geometric Sun states from a Horizons geodetic Earth site.

    Horizons applies its Earth-orientation model to the site center, including
    the site's rotational state. Coordinates are east longitude, geodetic
    latitude in degrees, and height above the reference ellipsoid in km.
    """
    longitude, latitude, altitude_km = longitude_latitude_altitude
    params = {
        "format": "json",
        "COMMAND": "'10'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'VECTORS'",
        "CENTER": "'coord@399'",
        "COORD_TYPE": "'GEODETIC'",
        "SITE_COORD": f"'{longitude:.10f},{latitude:.10f},{altitude_km:.6f}'",
        "TLIST": " ".join(f"'{event.strftime('%Y-%b-%d %H:%M:%S.%f')}'" for event in events),
        "TLIST_TYPE": "'CAL'",
        "TIME_TYPE": "'UT'",
        "OUT_UNITS": "'KM-S'",
        "VEC_TABLE": "'2'",
        "REF_PLANE": "'FRAME'",
        "REF_SYSTEM": "'ICRF'",
        "VEC_CORR": "'NONE'",
        "TIME_DIGITS": "'FRACSEC'",
        "CSV_FORMAT": "'YES'",
    }
    url = "https://ssd.jpl.nasa.gov/api/horizons.api?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = json.load(response)
    if payload.get("error"):
        raise RuntimeError(f"JPL Horizons topocentric site error: {payload['error']}")
    block = payload.get("result", "")
    if "$$SOE" not in block or "$$EOE" not in block:
        raise RuntimeError("JPL Horizons site response did not contain vector rows")
    states: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
    for line in block.split("$$SOE", 1)[1].split("$$EOE", 1)[0].splitlines():
        cells = [cell.strip() for cell in line.strip().rstrip(",").split(",")]
        if len(cells) < 8:
            continue
        values = [float(value.replace("D", "E")) for value in cells[2:8]]
        states.append(((values[0], values[1], values[2]), (values[3], values[4], values[5])))
    if len(states) != len(events):
        raise RuntimeError(f"Expected {len(events)} site states, received {len(states)}")
    return states


def query_earth_sun_series_utc(
    start_utc: datetime, stop_utc: datetime, step: str = "1 d"
) -> list[tuple[datetime, tuple[float, float, float], tuple[float, float, float]]]:
    """Query a uniformly sampled geometric Earth-Sun ICRF state series."""
    params = {
        "format": "json",
        "COMMAND": "'399'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'VECTORS'",
        "CENTER": "'500@10'",
        "START_TIME": f"'{start_utc.strftime('%Y-%b-%d %H:%M:%S')}'",
        "STOP_TIME": f"'{stop_utc.strftime('%Y-%b-%d %H:%M:%S')}'",
        "STEP_SIZE": f"'{step}'",
        "TIME_TYPE": "'UT'",
        "OUT_UNITS": "'KM-S'",
        "VEC_TABLE": "'2'",
        "REF_PLANE": "'FRAME'",
        "REF_SYSTEM": "'ICRF'",
        "VEC_CORR": "'NONE'",
        "TIME_DIGITS": "'FRACSEC'",
        "CSV_FORMAT": "'YES'",
    }
    url = "https://ssd.jpl.nasa.gov/api/horizons.api?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=120) as response:
        payload = json.load(response)
    if payload.get("error"):
        raise RuntimeError(f"JPL Horizons Earth worldline error: {payload['error']}")
    block = payload.get("result", "")
    if "$$SOE" not in block or "$$EOE" not in block:
        raise RuntimeError("JPL Horizons response did not contain Earth worldline rows")
    rows = []
    for line in block.split("$$SOE", 1)[1].split("$$EOE", 1)[0].splitlines():
        cells = [cell.strip() for cell in line.strip().rstrip(",").split(",")]
        if len(cells) < 8:
            continue
        event_text = cells[1].removeprefix("A.D. ")
        event_utc = datetime.strptime(event_text, "%Y-%b-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
        values = [float(value.replace("D", "E")) for value in cells[2:8]]
        rows.append((event_utc, tuple(values[:3]), tuple(values[3:])))
    if len(rows) < 2:
        raise RuntimeError(f"Expected multiple Earth states, received {len(rows)}")
    return rows


def query_sun_from_site_series_utc(
    start_utc: datetime,
    stop_utc: datetime,
    longitude_latitude_altitude: tuple[float, float, float],
    step: str = "1 d",
) -> list[tuple[datetime, tuple[float, float, float], tuple[float, float, float]]]:
    """Query the Sun's ICRF state from a geodetic site for Earth orientation."""
    longitude, latitude, altitude_km = longitude_latitude_altitude
    params = {
        "format": "json",
        "COMMAND": "'10'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'VECTORS'",
        "CENTER": "'coord@399'",
        "COORD_TYPE": "'GEODETIC'",
        "SITE_COORD": f"'{longitude:.10f},{latitude:.10f},{altitude_km:.6f}'",
        "START_TIME": f"'{start_utc.strftime('%Y-%b-%d %H:%M:%S')}'",
        "STOP_TIME": f"'{stop_utc.strftime('%Y-%b-%d %H:%M:%S')}'",
        "STEP_SIZE": f"'{step}'",
        "TIME_TYPE": "'UT'",
        "OUT_UNITS": "'KM-S'",
        "VEC_TABLE": "'2'",
        "REF_PLANE": "'FRAME'",
        "REF_SYSTEM": "'ICRF'",
        "VEC_CORR": "'NONE'",
        "TIME_DIGITS": "'FRACSEC'",
        "CSV_FORMAT": "'YES'",
    }
    url = "https://ssd.jpl.nasa.gov/api/horizons.api?"+urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=120) as response:
        payload = json.load(response)
    if payload.get("error"):
        raise RuntimeError(f"JPL Horizons Earth-orientation site error: {payload['error']}")
    block = payload.get("result", "")
    if "$$SOE" not in block or "$$EOE" not in block:
        raise RuntimeError("JPL Horizons response did not contain site orientation rows")
    rows = []
    for line in block.split("$$SOE", 1)[1].split("$$EOE", 1)[0].splitlines():
        cells = [cell.strip() for cell in line.strip().rstrip(",").split(",")]
        if len(cells) < 8:
            continue
        event_utc = datetime.strptime(cells[1].removeprefix("A.D. "), "%Y-%b-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
        values = [float(value.replace("D", "E")) for value in cells[2:8]]
        rows.append((event_utc, tuple(values[:3]), tuple(values[3:])))
    if len(rows) < 2:
        raise RuntimeError(f"Expected multiple Earth-orientation rows, received {len(rows)}")
    return rows


def earth_site_endpoint_displacement(
    target_utc: datetime,
    control_utc: datetime,
    emitter_range_km: float,
    target_earth_offset_icrf_km: tuple[float, float, float] = (0.0, 0.0, 0.0),
    control_earth_offset_icrf_km: tuple[float, float, float] = (0.0, 0.0, 0.0),
    target_site_lon_lat_alt: tuple[float, float, float] | None = None,
    control_site_lon_lat_alt: tuple[float, float, float] | None = None,
) -> dict[str, object]:
    """Estimate target-to-control Earth-site displacement in a local ICRF frame.

    Earth-Sun vectors are DE441 geometric ICRF states from Horizons. The Sun's
    Galactic translation uses the existing constant-velocity plus constant-
    centripetal-acceleration approximation; this is not a Galactic orbit solve.
    Endpoint offsets may be supplied as ICRF event vectors. Alternatively,
    Horizons may compute geodetic site states, including Earth orientation and
    rotation, at both event times.
    """
    (target_sun, target_orbital_velocity), (control_sun, control_orbital_velocity) = (
        query_earth_sun_icrf_utc([target_utc, control_utc])
    )
    target_site_velocity_offset = (0.0, 0.0, 0.0)
    control_site_velocity_offset = (0.0, 0.0, 0.0)
    site_source = "explicit ICRF endpoint offsets; site velocities unavailable"
    if target_site_lon_lat_alt is not None and control_site_lon_lat_alt is not None:
        target_sun_from_site, control_sun_from_site = query_sun_icrf_from_geodetic_site_utc(
            [target_utc, control_utc], target_site_lon_lat_alt
        ) if target_site_lon_lat_alt == control_site_lon_lat_alt else (None, None)
        if target_sun_from_site is None or control_sun_from_site is None:
            target_sun_from_site = query_sun_icrf_from_geodetic_site_utc([target_utc], target_site_lon_lat_alt)[0]
            control_sun_from_site = query_sun_icrf_from_geodetic_site_utc([control_utc], control_site_lon_lat_alt)[0]
        target_earth_offset_icrf_km = tuple(
            -target_sun_from_site[0][i]-target_sun[i] for i in range(3)
        )
        control_earth_offset_icrf_km = tuple(
            -control_sun_from_site[0][i]-control_sun[i] for i in range(3)
        )
        target_site_velocity_offset = tuple(
            -target_sun_from_site[1][i]-target_orbital_velocity[i] for i in range(3)
        )
        control_site_velocity_offset = tuple(
            -control_sun_from_site[1][i]-control_orbital_velocity[i] for i in range(3)
        )
        site_source = "JPL Horizons geodetic site states with Earth orientation and site rotation at each endpoint"
    elapsed = (control_utc - target_utc).total_seconds()
    solar_velocity, solar_acceleration = local_solar_galactic_state()
    earth_sun_delta = tuple(target_sun[i] - control_sun[i] for i in range(3))
    target_minus_control = tuple(
        earth_sun_delta[i] - solar_velocity[i] * elapsed
        + 0.5 * solar_acceleration[i] * elapsed**2
        + target_earth_offset_icrf_km[i] - control_earth_offset_icrf_km[i]
        for i in range(3)
    )
    distance_km = math.sqrt(sum(value * value for value in target_minus_control))
    target_to_control = tuple(-value for value in target_minus_control)
    elapsed_years = elapsed / JULIAN_YEAR_S
    mean_reference_velocity_beta = tuple(
        value / KM_PER_LY / elapsed_years for value in target_to_control
    )
    mean_reference_speed_beta = math.sqrt(
        sum(value * value for value in mean_reference_velocity_beta)
    )
    # Transform endpoint events to the instantaneous rest frame of the target
    # geocenter or geodetic site, according to the supplied endpoint model.
    # The local Galactic velocity is anchored at the control epoch; propagate
    # it backward by the local acceleration when constructing the target state.
    c_km_s = C_M_S / 1000.0
    target_geocenter_velocity_icrf = tuple(
        solar_velocity[i] - solar_acceleration[i]*elapsed + target_orbital_velocity[i] for i in range(3)
    )
    control_geocenter_velocity_icrf = tuple(
        solar_velocity[i] + control_orbital_velocity[i]
        for i in range(3)
    )
    target_endpoint_velocity_icrf = tuple(
        target_geocenter_velocity_icrf[i] + target_site_velocity_offset[i] for i in range(3)
    )
    control_endpoint_velocity_icrf = tuple(
        control_geocenter_velocity_icrf[i] + control_site_velocity_offset[i] for i in range(3)
    )
    beta0 = tuple(value/c_km_s for value in target_endpoint_velocity_icrf)
    beta02 = sum(value*value for value in beta0)
    gamma0 = 1.0/math.sqrt(1.0-beta02)
    delta_r_icrf = tuple(-value for value in target_minus_control)
    beta_dot_r_km = sum(beta0[i]*delta_r_icrf[i] for i in range(3))
    if beta02 > 0.0:
        spatial_factor = (gamma0-1.0)*beta_dot_r_km/beta02 - gamma0*c_km_s*elapsed
    else:
        spatial_factor = 0.0
    delta_r_target_rest_km = tuple(
        delta_r_icrf[i] + spatial_factor*beta0[i] for i in range(3)
    )
    delta_t_target_rest_s = gamma0*(elapsed-beta_dot_r_km/c_km_s)
    beta_control = tuple(value/c_km_s for value in control_endpoint_velocity_icrf)
    beta0_dot_control = sum(beta0[i]*beta_control[i] for i in range(3))
    if beta02 > 0.0:
        velocity_factor = (gamma0-1.0)*beta0_dot_control/beta02-gamma0
    else:
        velocity_factor = 0.0
    control_velocity_target_rest_beta = tuple(
        (beta_control[i]+velocity_factor*beta0[i])
        /(gamma0*(1.0-beta0_dot_control))
        for i in range(3)
    )
    beta_control_geocenter = tuple(value/c_km_s for value in control_geocenter_velocity_icrf)
    beta0_dot_geocenter = sum(beta0[i]*beta_control_geocenter[i] for i in range(3))
    geocenter_velocity_factor = (
        (gamma0-1.0)*beta0_dot_geocenter/beta02-gamma0 if beta02 > 0.0 else 0.0
    )
    control_geocenter_velocity_target_rest_beta = tuple(
        (beta_control_geocenter[i]+geocenter_velocity_factor*beta0[i])
        /(gamma0*(1.0-beta0_dot_geocenter)) for i in range(3)
    )
    endpoint_distance_target_rest_km = math.sqrt(
        sum(value*value for value in delta_r_target_rest_km)
    )
    target_offset_radius_km = math.sqrt(sum(v*v for v in target_earth_offset_icrf_km))
    control_offset_radius_km = math.sqrt(sum(v*v for v in control_earth_offset_icrf_km))
    return {
        "model": "DE441 Earth-Sun geocenter states plus Horizons geodetic site states or explicit ICRF event offsets and constant local solar Galactic velocity/acceleration",
        "time_tags": "UTC inputs interpreted by Horizons as UT; geometric ICRF vectors; endpoint interval uses UTC elapsed seconds",
        "target_emission_event_utc": target_utc.isoformat(),
        "control_event_utc": control_utc.isoformat(),
        "earth_sun_position_at_target_km_icrf": list(target_sun),
        "earth_sun_position_at_control_km_icrf": list(control_sun),
        "earth_sun_velocity_at_target_km_s_icrf": list(target_orbital_velocity),
        "earth_sun_velocity_at_control_km_s_icrf": list(control_orbital_velocity),
        "target_earth_geocenter_offset_km_icrf": list(target_earth_offset_icrf_km),
        "control_earth_geocenter_offset_km_icrf": list(control_earth_offset_icrf_km),
        "target_event_radius_from_earth_center_km": target_offset_radius_km,
        "control_event_radius_from_earth_center_km": control_offset_radius_km,
        "local_solar_velocity_km_s_icrf": list(solar_velocity),
        "local_solar_acceleration_km_s2_icrf": list(solar_acceleration),
        "endpoint_equation": "r_site(target)-r_site(control) = r_ES(target)-r_ES(control)-v_sun*dt+0.5*a_sun*dt^2 + rho_target - rho_control",
        "target_minus_control_site_vector_km_icrf": list(target_minus_control),
        "target_minus_control_site_vector_ly_icrf": [value / KM_PER_LY for value in target_minus_control],
        "target_geocenter_velocity_km_s_icrf": list(target_geocenter_velocity_icrf),
        "control_geocenter_velocity_km_s_icrf": list(control_geocenter_velocity_icrf),
        "target_endpoint_velocity_km_s_icrf": list(target_endpoint_velocity_icrf),
        "control_endpoint_velocity_km_s_icrf": list(control_endpoint_velocity_icrf),
        "target_endpoint_velocity_fraction_of_c_icrf": list(beta0),
        "target_site_rotational_velocity_offset_km_s_icrf": list(target_site_velocity_offset),
        "control_site_rotational_velocity_offset_km_s_icrf": list(control_site_velocity_offset),
        "site_state_source": site_source,
        "target_site_longitude_latitude_altitude": list(target_site_lon_lat_alt) if target_site_lon_lat_alt else None,
        "control_site_longitude_latitude_altitude": list(control_site_lon_lat_alt) if control_site_lon_lat_alt else None,
        "endpoint_event_separation_in_target_endpoint_rest_frame": {
            "rest_frame_anchor": "target geodetic site" if target_site_lon_lat_alt is not None else "target geocenter",
            "target_endpoint_velocity_fraction_of_c_icrf": list(beta0),
            "target_endpoint_gamma": gamma0,
            "transform": "Lorentz transform using the target endpoint's instantaneous ICRF velocity; local solar acceleration advances the geocenter state",
            "target_to_control_coordinate_time_s": delta_t_target_rest_s,
            "target_to_control_spatial_vector_km": list(delta_r_target_rest_km),
            "target_to_control_spatial_vector_lightyears": [value/KM_PER_LY for value in delta_r_target_rest_km],
            "target_to_control_distance_lightyears": endpoint_distance_target_rest_km/KM_PER_LY,
            "control_geocenter_velocity_fraction_of_c_in_target_endpoint_rest_frame": list(control_geocenter_velocity_target_rest_beta),
            "control_endpoint_velocity_fraction_of_c": list(control_velocity_target_rest_beta),
            "target_endpoint_velocity_km_s_icrf": list(target_endpoint_velocity_icrf),
            "site_rotational_velocity": "included at endpoints only when Horizons geodetic site states are requested; continuous site worldline not yet evaluated",
            "not_a_return_path": "this is an endpoint event separation and four-velocity diagnostic, not a mouth trajectory, Earth worldline, or collision-clearance route",
        },
        "route_axis_target_to_control_unit_icrf": (
            [value / distance_km for value in target_to_control] if distance_km else None
        ),
        "mean_reference_worldline_velocity_beta_icrf": list(mean_reference_velocity_beta),
        "mean_reference_worldline_speed_fraction_of_c": mean_reference_speed_beta,
        "mean_velocity_interval_years": elapsed_years,
        "endpoint_displacement_light_years": distance_km / KM_PER_LY,
        "site_and_emitter_offset_bound_km": 2.0 * 6378.137 + emitter_range_km * 1000.0,
        "site_and_emitter_offset_bound_light_years": (2.0 * 6378.137 + emitter_range_km * 1000.0) / KM_PER_LY,
        "reference_earth_radii_km": {
            "polar": EARTH_POLAR_RADIUS_KM,
            "equatorial": EARTH_EQUATORIAL_RADIUS_KM,
            "model": "WGS84 reference ellipsoid radii; no terrain or geoid model",
        },
        "limits": (
            "Horizons Earth orientation and site rotation are evaluated only at the two endpoint events; no continuous Earth/site or witness worldline is propagated. A.R.G.O. location and Galactic potential are not solved. The endpoint Lorentz transform is special-relativistic in the local approximation, not curved-spacetime frame transport."
            if target_site_lon_lat_alt is not None else
            "Explicit ICRF offsets specify endpoint event positions only and provide no site velocity. No site or witness worldline is propagated. A.R.G.O. location and Galactic potential are not solved. The endpoint Lorentz transform is special-relativistic in the local approximation, not curved-spacetime frame transport."
        ),
    }


def planar_profile(
    lookback_years: float,
    beta_max: float,
    endpoint_distance_ly: float,
    transverse_excursion_ly: float,
    profile: str,
    endpoint_velocity_beta: tuple[float, float] = (0.0, 0.0),
) -> dict[str, float | str]:
    """Solve a mouth excursion in the inertial frame comoving with mouth A.

    Mouth A is at rest in this chart, so its proper-time rate is one. Mouth B
    follows the selected relative trajectory, including optional terminal
    velocity boundary data. In Earth-worldline mode the chart is the target
    geocenter's instantaneous rest frame; site rotation is not included.
    """
    if profile not in {"sin", "c2"}:
        raise ValueError("profile must be 'sin' or 'c2'")
    if transverse_excursion_ly == 0.0 and endpoint_velocity_beta == (0.0, 0.0):
        return estimate(lookback_years, beta_max, endpoint_distance_ly, profile=profile)

    intervals = 4000
    samples = intervals

    def terminal_velocity_basis(u: float) -> tuple[float, float, float]:
        # Adds a prescribed terminal velocity while preserving zero initial
        # position/velocity/acceleration and zero terminal position/acceleration.
        h = -4.0*u**3 + 7.0*u**4 - 3.0*u**5
        dh = -12.0*u**2 + 28.0*u**3 - 15.0*u**4
        ddh = (-24.0*u + 84.0*u**2 - 60.0*u**3)
        return h, dh, ddh

    def state(duration: float, u: float) -> tuple[float, float, float, float, float]:
        h, dh, _ = terminal_velocity_basis(u)
        terminal_vx, terminal_vy = endpoint_velocity_beta
        vx = beta_at(u, duration, endpoint_distance_ly, beta_max, profile) + terminal_vx*dh
        theta = math.pi * u
        if profile == "c2":
            vy = 4.0 * math.pi * transverse_excursion_ly / duration * math.sin(theta) ** 3 * math.cos(theta) + terminal_vy*dh
            y = transverse_excursion_ly * math.sin(theta) ** 4 + duration*terminal_vy*h
        else:
            vy = transverse_excursion_ly * math.pi / duration * math.sin(2.0 * theta) + terminal_vy*dh
            y = transverse_excursion_ly * math.sin(theta) ** 2 + duration*terminal_vy*h
        x = position_at(u, duration, endpoint_distance_ly, beta_max, profile) + duration*terminal_vx*h
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
    baseline = estimate(lookback_years, beta_max, endpoint_distance_ly, profile=profile)
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
    actual_lag, max_relative_speed = lag_and_speed(duration)
    if actual_lag is None:
        raise ArithmeticError("planar profile root is not subluminal")

    max_radius = 0.0
    max_relative_excursion = 0.0
    path_length = 0.0
    max_accel_beta_per_year = 0.0
    max_proper_accel_m_s2 = 0.0
    max_gamma = 1.0
    max_specific_ke_j_kg = 0.0
    positive_work_j_kg = 0.0
    previous_specific_ke_j_kg = 0.0
    previous_xy: tuple[float, float] | None = None
    for i in range(samples + 1):
        u = i / samples
        x, y, vx, vy, speed = state(duration, u)
        relative_xy = (x, y)
        max_radius = max(max_radius, math.hypot(x, y))
        max_relative_excursion = max(max_relative_excursion, math.hypot(x, y))
        if previous_xy is not None:
            path_length += math.hypot(relative_xy[0] - previous_xy[0], relative_xy[1] - previous_xy[1])
        previous_xy = relative_xy
        _, _, ddh = terminal_velocity_basis(u)
        terminal_vx, terminal_vy = endpoint_velocity_beta
        ax = beta_derivative_per_year(u, duration, endpoint_distance_ly, beta_max, profile) + terminal_vx*ddh/duration
        if profile == "c2":
            sine = math.sin(math.pi*u)
            ay = 4.0 * math.pi**2 * transverse_excursion_ly / duration**2 * (
                3.0*sine**2 - 4.0*sine**4
            ) + terminal_vy*ddh/duration
        else:
            ay = transverse_excursion_ly * 2.0 * math.pi**2 / duration**2 * math.cos(2.0*math.pi*u) + terminal_vy*ddh/duration
        accel_mag = math.hypot(ax, ay)
        max_accel_beta_per_year = max(max_accel_beta_per_year, accel_mag)
        gamma = 1.0 / math.sqrt(1.0 - speed * speed)
        proper_accel_beta_per_year = math.sqrt(
            gamma**4 * accel_mag**2 + gamma**6 * (vx * ax + vy * ay) ** 2
        )
        max_proper_accel_m_s2 = max(
            max_proper_accel_m_s2,
            proper_accel_beta_per_year * C_M_S / JULIAN_YEAR_S,
        )
        max_gamma = max(max_gamma, gamma)
        specific_ke = (gamma - 1.0) * C_M_S**2
        max_specific_ke_j_kg = max(max_specific_ke_j_kg, specific_ke)
        if i:
            positive_work_j_kg += max(0.0, specific_ke - previous_specific_ke_j_kg)
        previous_specific_ke_j_kg = specific_ke

    reference_proper_time = duration
    moving_proper_time = duration - float(actual_lag)
    return {
        "model": "flat-exterior smooth planar twin-mouth kinematics",
        "lookback_clock_offset_years": lookback_years,
        "clock_lag_solver_residual_seconds": (float(actual_lag) - lookback_years) * JULIAN_YEAR_S,
        "integrated_clock_lag_years": float(actual_lag),
        "endpoint_displacement_light_years": endpoint_distance_ly,
        "terminal_velocity_fraction_of_c": list(endpoint_velocity_beta),
        "transverse_excursion_amplitude_light_years": transverse_excursion_ly,
        "maximum_speed_fraction_of_c": max_relative_speed,
        "profile_amplitude_parameter_fraction_of_c": beta_max,
        "velocity_profile": profile,
        "clock_lag_fraction_of_exterior_duration": lookback_years / duration,
        "exterior_duration_years": duration,
        "moving_mouth_proper_time_years": moving_proper_time,
        "reference_mouth_proper_time_years": reference_proper_time,
        "stationary_mouth_proper_time_years": reference_proper_time,
        "maximum_displacement_from_initial_site_light_years": max_radius,
        "maximum_relative_excursion_from_reference_mouth_light_years": max_relative_excursion,
        "total_path_length_light_years": path_length,
        "maximum_coordinate_acceleration_m_s2": max_accel_beta_per_year * C_M_S / JULIAN_YEAR_S,
        "maximum_proper_acceleration_m_s2": max_proper_accel_m_s2,
        "maximum_lorentz_factor": max_gamma,
        "maximum_specific_kinetic_energy_j_kg": max_specific_ke_j_kg,
        "ideal_positive_work_per_kg_without_regeneration_j_kg": positive_work_j_kg,
        "profile_smoothness": (
            "relative velocity and acceleration vanish at both endpoints; the moving mouth joins the reference mouth with matching tangent"
            if profile == "c2"
            else "relative velocity vanishes but relative acceleration steps at endpoints; the moving mouth still joins with matching tangent"
        ),
        "profile": (
            f"{profile} x velocity; y=b*sin(pi*u)^4; total speed from both components"
            if profile == "c2"
            else "sin x velocity; y=b*sin(pi*u)^2; total speed from both components"
        ),
        "duration_solver": "1% geometric scan, then bisection; 4,000-interval Simpson proper-time integration",
    }


def write_planar_worldline_csv(
    path: Path,
    summary: dict[str, float | str | list[float]],
    transverse_excursion_ly: float,
    endpoint_velocity_beta: tuple[float, float],
    rows: int = 2001,
) -> None:
    """Write samples of the actual 2D curve, including terminal-state terms."""
    duration = float(summary["exterior_duration_years"])
    endpoint_distance = float(summary["endpoint_displacement_light_years"])
    beta_max = float(summary["profile_amplitude_parameter_fraction_of_c"])
    profile = str(summary["velocity_profile"])

    def state(u: float) -> tuple[float, float, float, float, float, float, float]:
        h = -4.0*u**3 + 7.0*u**4 - 3.0*u**5
        dh = -12.0*u**2 + 28.0*u**3 - 15.0*u**4
        ddh = -24.0*u + 84.0*u**2 - 60.0*u**3
        theta = math.pi*u
        vx = beta_at(u, duration, endpoint_distance, beta_max, profile) + endpoint_velocity_beta[0]*dh
        ax = beta_derivative_per_year(u, duration, endpoint_distance, beta_max, profile) + endpoint_velocity_beta[0]*ddh/duration
        x = position_at(u, duration, endpoint_distance, beta_max, profile) + duration*endpoint_velocity_beta[0]*h
        if profile == "c2":
            base_y = transverse_excursion_ly*math.sin(theta)**4
            base_vy = 4.0*math.pi*transverse_excursion_ly/duration*math.sin(theta)**3*math.cos(theta)
            base_ay = 4.0*math.pi**2*transverse_excursion_ly/duration**2*(3.0*math.sin(theta)**2-4.0*math.sin(theta)**4)
        else:
            base_y = transverse_excursion_ly*math.sin(theta)**2
            base_vy = math.pi*transverse_excursion_ly/duration*math.sin(2.0*theta)
            base_ay = 2.0*math.pi**2*transverse_excursion_ly/duration**2*math.cos(2.0*theta)
        y = base_y+duration*endpoint_velocity_beta[1]*h
        vy = base_vy+endpoint_velocity_beta[1]*dh
        ay = base_ay+endpoint_velocity_beta[1]*ddh/duration
        return x, y, vx, vy, ax, ay, math.hypot(vx, vy)

    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow([
            "exterior_time_years", "x_light_years", "y_light_years",
            "vx_over_c", "vy_over_c", "speed_over_c",
            "stationary_mouth_clock_years", "moving_mouth_clock_years",
            "clock_lag_years", "coordinate_acceleration_m_s2",
            "proper_acceleration_m_s2", "specific_kinetic_energy_j_kg",
        ])
        for index in range(rows):
            u = index/(rows-1)
            x, y, vx, vy, ax, ay, speed = state(u)
            if speed >= 1.0:
                raise ArithmeticError("CSV worldline contains a non-timelike sample")
            lag = duration*u*simpson_mean(
                lambda s: 1.0-math.sqrt(1.0-state(u*s)[6]**2), 2000
            ) if u else 0.0
            gamma = 1.0/math.sqrt(1.0-speed**2)
            accel = math.hypot(ax, ay)
            dot = vx*ax+vy*ay
            proper_accel = gamma**2*math.sqrt(accel**2+gamma**2*dot**2)
            writer.writerow([
                f"{duration*u:.9f}", f"{x:.12f}", f"{y:.12f}",
                f"{vx:.12f}", f"{vy:.12f}", f"{speed:.12f}",
                f"{duration*u:.9f}", f"{duration*u-lag:.9f}", f"{lag:.9f}",
                f"{accel*C_M_S/JULIAN_YEAR_S:.12e}",
                f"{proper_accel*C_M_S/JULIAN_YEAR_S:.12e}",
                f"{(gamma-1.0)*C_M_S**2:.12e}",
            ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-utc", type=parse_utc, help="control event in UTC; legacy AD calendar mode")
    parser.add_argument("--witness-utc", type=parse_utc, help="witness event in UTC; legacy AD calendar mode")
    parser.add_argument("--control-jd-tdb", type=Decimal, help="control event as Julian Date in TDB; must be paired with --witness-jd-tdb")
    parser.add_argument("--witness-jd-tdb", type=Decimal, help="witness event as Julian Date in TDB; supports astronomical BCE dates")
    parser.add_argument("--wormhole-formation-utc", type=parse_utc, help="assumed synchronized mouth-pair formation event; checked against the latest formation date allowed by the prescribed mouth history")
    parser.add_argument("--wormhole-formation-jd-tdb", type=Decimal, help="assumed synchronized pair formation event as Julian Date TDB; use with the JD event mode")
    parser.add_argument("--range-km", type=float, default=10.0, help="assumed emitter-to-witness distance")
    parser.add_argument("--witness-transverse-baseline-km", type=float, help="projected separation between two witnesses perpendicular to the first line of sight")
    parser.add_argument(
        "--target-emitter-power-w",
        "--witness-source-power-w",
        dest="witness_source_power_w",
        type=float,
        help=(
            "assumed optical power of an optional target-side emitter, in watts; "
            "not the lead A.R.G.O.-beacon transfer (legacy alias: --witness-source-power-w)"
        ),
    )
    parser.add_argument(
        "--target-emitter-beam-solid-angle-sr",
        "--witness-beam-solid-angle-sr",
        dest="witness_beam_solid_angle_sr",
        type=float,
        help="assumed uniform top-hat cone from the optional target-side emitter (legacy witness-named alias retained)",
    )
    parser.add_argument("--witness-transmission", type=float, default=1.0, help="assumed source-to-witness transmission fraction, from 0 to 1")
    parser.add_argument("--witness-lensing-magnification", type=float, default=1.0, help="assumed total geometric-optics magnification; 1 means no lensing correction")
    parser.add_argument("--witness-wavelength-nm", type=float, help="assumed monochromatic-equivalent wavelength for photon-flux conversion")
    parser.add_argument(
        "--target-emitter-aperture-diameter-m",
        "--witness-aperture-diameter-m",
        dest="witness_aperture_diameter_m",
        type=float,
        help="assumed circular target-side emitter aperture for a diffraction screen",
    )
    parser.add_argument(
        "--target-emission-duration-s",
        "--witness-emission-duration-s",
        dest="witness_emission_duration_s",
        type=float,
        help="assumed target-side emission duration for pulse energy and fluence",
    )
    parser.add_argument("--mouth-gap-m", type=float, default=1000.0, help="small initial and final separation between mouths")
    parser.add_argument("--transverse-excursion-ly", type=float, default=0.0, help="peak sideways amplitude of a smooth mouth excursion that returns to the initial axis")
    parser.add_argument("--throat-seconds", type=float, default=0.0, help="assumed signal transit time through throat")
    parser.add_argument("--beta-max", type=float, default=0.8)
    parser.add_argument("--profile", choices=("sin", "c2"), default="c2", help="mouth velocity profile; c2 has zero endpoint acceleration")
    parser.add_argument("--view-span-years", type=float, default=5000.0, help="remote proper-time span requested for the crew viewpoint")
    parser.add_argument("--crew-minutes", type=float, default=5.0, help="A.R.G.O. proper-time duration for the requested viewpoint scan")
    parser.add_argument("--endpoint-displacement-ly", type=float, help="prescribed endpoint displacement; incompatible with --earth-worldline")
    parser.add_argument("--earth-worldline", action="store_true", help="derive endpoint events from DE441 Earth states plus the documented local Galactic approximation")
    parser.add_argument("--target-site-lon-lat-alt", type=float, nargs=3, metavar=("LON_E_DEG", "LAT_DEG", "ALT_KM"), help="target hull-center geodetic site; Horizons applies Earth orientation/site rotation")
    parser.add_argument("--control-site-lon-lat-alt", type=float, nargs=3, metavar=("LON_E_DEG", "LAT_DEG", "ALT_KM"), help="control hull-center geodetic site; Horizons applies Earth orientation/site rotation")
    parser.add_argument("--target-earth-offset-icrf-km", type=float, nargs=3, metavar=("X", "Y", "Z"), help="target-event offset from Earth's geocenter in ICRF km; site velocity is not available")
    parser.add_argument("--control-earth-offset-icrf-km", type=float, nargs=3, metavar=("X", "Y", "Z"), help="control-event offset from Earth's geocenter in ICRF km; site velocity is not available")
    parser.add_argument("--return-hull-radius-m", type=float, default=3.766, help="spherical hull-envelope radius used by the exterior return clearance screen")
    parser.add_argument("--return-hazard", type=float, nargs=5, action="append", metavar=("X", "Y", "VX", "VY", "R"), default=[], help="moving circular hazard in the return plane: center x/y at target exit and velocity vx/vy in light-years and c, then radius in light-years; repeatable")
    parser.add_argument("--csv", type=Path, help="write sampled mouth worldline and clock history")
    args = parser.parse_args()

    jd_tdb_mode = args.control_jd_tdb is not None or args.witness_jd_tdb is not None
    if jd_tdb_mode:
        if args.control_jd_tdb is None or args.witness_jd_tdb is None:
            parser.error("--control-jd-tdb and --witness-jd-tdb must be supplied together")
        if args.control_utc is not None or args.witness_utc is not None:
            parser.error("choose either UTC dates or the paired JD TDB dates, not both")
        if args.earth_worldline:
            parser.error("JD TDB event mode is timing-only for now; --earth-worldline still requires UTC and cannot anchor BCE endpoints")
        if args.wormhole_formation_utc is not None and args.wormhole_formation_jd_tdb is not None:
            parser.error("choose one wormhole formation time scale")
        if args.wormhole_formation_utc is not None:
            parser.error("use --wormhole-formation-jd-tdb with JD TDB event mode")
        if not args.control_jd_tdb.is_finite() or not args.witness_jd_tdb.is_finite():
            parser.error("Julian dates must be finite numbers")
        jd_anchor_tdb = args.control_jd_tdb
        control = 0.0
        witness = float((args.witness_jd_tdb - args.control_jd_tdb) * Decimal(str(SECONDS_PER_DAY)))
        control_utc = witness_utc = None
    else:
        if args.wormhole_formation_jd_tdb is not None:
            parser.error("--wormhole-formation-jd-tdb requires the paired JD TDB event mode")
        control_utc = args.control_utc or parse_utc("2026-10-18T03:15:00Z")
        witness_utc = args.witness_utc or parse_utc("1997-03-14T03:15:00Z")
        control = control_utc.timestamp()
        witness = witness_utc.timestamp()
        jd_anchor_tdb = None

    if (
        not all(math.isfinite(value) for value in (
            args.range_km, args.mouth_gap_m, args.throat_seconds,
            args.transverse_excursion_ly, args.return_hull_radius_m,
        ))
        or args.range_km < 0 or args.mouth_gap_m <= 0 or args.throat_seconds < 0
        or args.transverse_excursion_ly < 0 or args.return_hull_radius_m < 0
    ):
        parser.error("range, throat transit, transverse excursion, and hull radius must be nonnegative; mouth gap must be positive")
    if args.witness_transverse_baseline_km is not None and (
        not math.isfinite(args.witness_transverse_baseline_km)
        or args.witness_transverse_baseline_km < 0.0
        or args.range_km <= 0.0
    ):
        parser.error("--witness-transverse-baseline-km must be finite and nonnegative, with a positive range")
    if (args.witness_source_power_w is None) != (args.witness_beam_solid_angle_sr is None):
        parser.error("provide both --witness-source-power-w and --witness-beam-solid-angle-sr for an optical flux estimate")
    if args.witness_source_power_w is not None and (
        not math.isfinite(args.witness_source_power_w)
        or not math.isfinite(args.witness_beam_solid_angle_sr)
        or args.witness_source_power_w < 0.0 or args.witness_beam_solid_angle_sr <= 0.0
        or args.witness_beam_solid_angle_sr >= 2.0*math.pi or args.range_km <= 0.0
    ):
        parser.error("optical source power must be nonnegative, beam solid angle in (0, 2π), and range positive")
    if not 0.0 <= args.witness_transmission <= 1.0:
        parser.error("--witness-transmission must be in [0, 1]")
    if args.witness_lensing_magnification < 0.0 or not math.isfinite(args.witness_lensing_magnification):
        parser.error("--witness-lensing-magnification must be finite and nonnegative")
    if args.witness_wavelength_nm is not None and (
        not math.isfinite(args.witness_wavelength_nm) or args.witness_wavelength_nm <= 0.0
    ):
        parser.error("--witness-wavelength-nm must be positive")
    if args.witness_aperture_diameter_m is not None and (
        not math.isfinite(args.witness_aperture_diameter_m)
        or args.witness_aperture_diameter_m <= 0.0
        or args.witness_wavelength_nm is None
        or args.range_km <= 0.0
    ):
        parser.error("a positive aperture diameter requires a positive wavelength and range")
    if (
        args.witness_wavelength_nm is not None
        and args.witness_source_power_w is None
        and args.witness_aperture_diameter_m is None
    ):
        parser.error("wavelength requires source power for photon flux or an aperture for diffraction")
    if args.witness_emission_duration_s is not None and (
        not math.isfinite(args.witness_emission_duration_s) or args.witness_emission_duration_s <= 0.0
    ):
        parser.error("--witness-emission-duration-s must be positive")
    if args.witness_emission_duration_s is not None and args.witness_source_power_w is None:
        parser.error("--witness-emission-duration-s requires source power and beam solid angle")
    for hazard in args.return_hazard:
        if (
            not all(math.isfinite(value) for value in hazard)
            or hazard[4] <= 0.0
            or math.hypot(hazard[2], hazard[3]) >= 1.0
        ):
            parser.error("return hazards need a positive radius and a subluminal velocity")
    if args.view_span_years < 0 or args.crew_minutes <= 0:
        parser.error("view span must be nonnegative and crew duration must be positive")
    if args.earth_worldline and args.endpoint_displacement_ly is not None:
        parser.error("choose either --earth-worldline or --endpoint-displacement-ly")
    if not args.earth_worldline and any((args.target_earth_offset_icrf_km, args.control_earth_offset_icrf_km, args.target_site_lon_lat_alt, args.control_site_lon_lat_alt)):
        parser.error("Earth-site offset vectors require --earth-worldline")
    if bool(args.target_site_lon_lat_alt) != bool(args.control_site_lon_lat_alt):
        parser.error("provide both target and control geodetic site coordinates")
    for site in (args.target_site_lon_lat_alt, args.control_site_lon_lat_alt):
        if site and (not all(math.isfinite(value) for value in site) or not -90.0 <= site[1] <= 90.0):
            parser.error("site coordinates must be finite and latitude must be within [-90, 90] degrees")
    if (args.target_site_lon_lat_alt or args.control_site_lon_lat_alt) and (args.target_earth_offset_icrf_km or args.control_earth_offset_icrf_km):
        parser.error("choose Horizons geodetic site coordinates or explicit ICRF offsets, not both")
    if control <= witness:
        parser.error("control event must be later than the witness event")
    range_m = args.range_km * 1000.0
    witness_optics = {
        "status": "not calculated; provide source power and beam solid angle",
        "model_branch": "optional target-side emitter; not the lead A.R.G.O.-emitted beacon path",
        "assumed_range_km": args.range_km,
        "scope": "optional target-side optical source only (for example, a probe tip or field-manifestation branch); this is not the lead A.R.G.O.-emitted beacon transfer, and propagation through any chronology-changing route is not modeled",
    }
    witness_baseline = {
        "status": "not calculated; provide projected transverse witness separation",
        "reference_range_km": args.range_km,
    }
    if args.witness_transverse_baseline_km is not None:
        baseline_m = args.witness_transverse_baseline_km*1000.0
        second_range_m = math.hypot(range_m, baseline_m)
        parallax_rad = math.atan2(baseline_m, range_m) if range_m > 0.0 else math.pi/2.0
        second_observer_delay_s = (second_range_m-range_m)/C_M_S
        witness_baseline.update({
            "status": "conditional two-observer geometric screen",
            "model": "two static observers; baseline is exactly transverse to observer 1 line of sight",
            "projected_transverse_baseline_km": args.witness_transverse_baseline_km,
            "range_to_observer_1_km": args.range_km,
            "range_to_observer_2_km": second_range_m/1000.0,
            "geometric_parallax_angle_rad": parallax_rad,
            "geometric_parallax_angle_deg": math.degrees(parallax_rad),
            "additional_light_travel_time_to_observer_2_s": second_observer_delay_s,
            "inverse_square_flux_ratio_if_both_observers_illuminated": (range_m/second_range_m)**2 if second_range_m > 0.0 else None,
            "limits": "does not model Earth curvature, terrain/horizon occultation, witness motion, atmospheric differences, source extent, or a curved-spacetime ray solution",
        })
        if args.witness_beam_solid_angle_sr is not None:
            beam_half_angle = math.acos(1.0-args.witness_beam_solid_angle_sr/(2.0*math.pi))
            witness_baseline["assumed_beam_half_angle_rad"] = beam_half_angle
            witness_baseline["observer_2_inside_axis_aimed_top_hat_beam"] = parallax_rad <= beam_half_angle
        witness_baseline["minimum_axis_aimed_top_hat_solid_angle_to_include_observer_2_sr"] = (
            2.0*math.pi*(1.0-math.cos(parallax_rad))
        )
    if args.witness_aperture_diameter_m is not None:
        wavelength_m = args.witness_wavelength_nm*1e-9
        aperture_m = args.witness_aperture_diameter_m
        fraunhofer_distance_m = 2.0*aperture_m**2/wavelength_m
        witness_optics["diffraction_screen"] = {
            "model": "monochromatic, uniformly illuminated, unobscured circular aperture",
            "wavelength_nm": args.witness_wavelength_nm,
            "aperture_diameter_m": aperture_m,
            "range_m": range_m,
            "fraunhofer_distance_m": fraunhofer_distance_m,
            "far_field_condition_met": range_m >= fraunhofer_distance_m,
            "apparent_hull_angular_size": "not inferred from aperture diameter",
        }
        if args.witness_source_power_w is None:
            witness_optics["status"] = "conditional diffraction screen calculated; flux not calculated"
        if range_m >= fraunhofer_distance_m:
            airy_first_null_radius_rad = 1.22*wavelength_m/aperture_m
            airy_first_null_diameter_rad = 2.0*airy_first_null_radius_rad
            witness_optics["diffraction_screen"].update({
                "status": "far-field Airy first-null scale; not a hull outline",
                "airy_first_null_radius_rad": airy_first_null_radius_rad,
                "airy_first_null_diameter_rad": airy_first_null_diameter_rad,
                "airy_first_null_diameter_arcsec": math.degrees(airy_first_null_diameter_rad)*3600.0,
                "first_null_diameter_at_witness_plane_m": (
                    2.0*range_m*math.tan(airy_first_null_radius_rad)
                ),
            })
            if args.witness_beam_solid_angle_sr is not None:
                airy_main_lobe_solid_angle_sr = math.pi*airy_first_null_radius_rad**2
                witness_optics["diffraction_screen"]["airy_main_lobe_solid_angle_sr_small_angle"] = airy_main_lobe_solid_angle_sr
                witness_optics["diffraction_screen"]["declared_top_hat_narrower_than_airy_first_null"] = (
                    args.witness_beam_solid_angle_sr < airy_main_lobe_solid_angle_sr
                )
        else:
            witness_optics["diffraction_screen"].update({
                "status": "near field; Airy far-field formula is invalid at this range",
                "fresnel_propagation_required": True,
            })
    if args.witness_source_power_w is not None:
        source_power = args.witness_source_power_w
        beam_solid_angle = args.witness_beam_solid_angle_sr
        half_angle = math.acos(1.0 - beam_solid_angle/(2.0*math.pi))
        irradiance = (
            source_power * args.witness_transmission
            * args.witness_lensing_magnification
            / (beam_solid_angle*range_m**2)
        )
        witness_optics.update({
            "status": "conditional top-hat optical estimate from user-supplied assumptions",
            "model_branch": "optional target-side emitter; not the lead A.R.G.O.-emitted beacon path",
            "source_optical_power_w": source_power,
            "beam_solid_angle_sr": beam_solid_angle,
            "source_to_witness_transmission_fraction": args.witness_transmission,
            "assumed_lensing_magnification": args.witness_lensing_magnification,
            "emission_cone_full_divergence_angle_rad": 2.0*half_angle,
            "emission_cone_full_divergence_angle_deg": math.degrees(2.0*half_angle),
            "beam_diameter_at_witness_plane_m": 2.0*range_m*math.tan(half_angle),
            "witness_irradiance_w_m2": irradiance,
            "scope": "uniform top-hat cone, face-on irradiance, inverse-square propagation, and user-supplied scalar magnification; no wave optics, spatial source model, atmospheric spectrum, observer orientation, or chronology-changing propagation is solved",
        })
        witness_optics["apparent_source_angular_size"] = (
            "not calculated; requires the emitter aperture and spatial brightness distribution"
        )
        if args.witness_wavelength_nm is not None:
            photon_energy_j = 6.62607015e-34*C_M_S/(args.witness_wavelength_nm*1e-9)
            witness_optics["assumed_monochromatic_wavelength_nm"] = args.witness_wavelength_nm
            witness_optics["photon_flux_m2_s"] = irradiance/photon_energy_j
        if args.witness_emission_duration_s is not None:
            witness_optics["rectangular_pulse_duration_s"] = args.witness_emission_duration_s
            witness_optics["emitted_pulse_energy_j"] = source_power*args.witness_emission_duration_s
            witness_optics["witness_fluence_j_m2"] = irradiance*args.witness_emission_duration_s
        witness_optics["visibility_classification"] = "not assessed; apparent magnitude requires spectrum, angular profile, background, atmospheric state, and observer model"
    light_time_s = range_m / C_M_S
    emitter_epoch = witness - light_time_s
    coordinate_epoch_gap_s = control - emitter_epoch
    endpoint_model = None
    mouth_gap_ly = args.mouth_gap_m / METERS_PER_LIGHT_YEAR
    endpoint_distance_ly = args.endpoint_displacement_ly or 0.0
    earth_endpoint_distance_ly: float | None = None
    endpoint_velocity_beta = (0.0, 0.0)
    route_plane_basis: tuple[tuple[float, float, float], tuple[float, float, float]] | None = None
    reference_velocity_beta_icrf = (0.0, 0.0, 0.0)
    if args.earth_worldline:
        target_emission_utc = witness_utc - timedelta(seconds=light_time_s)
        try:
            endpoint_model = earth_site_endpoint_displacement(
                target_emission_utc,
                control_utc,
                args.range_km,
                tuple(args.target_earth_offset_icrf_km or (0.0, 0.0, 0.0)),
                tuple(args.control_earth_offset_icrf_km or (0.0, 0.0, 0.0)),
                tuple(args.target_site_lon_lat_alt) if args.target_site_lon_lat_alt else None,
                tuple(args.control_site_lon_lat_alt) if args.control_site_lon_lat_alt else None,
            )
        except Exception as exc:
            parser.error(f"could not query/compute the DE441 Earth endpoint: {exc}")
        # Use the Earth endpoint event separation and control-event velocity
        # in the target endpoint's instantaneous rest chart as terminal
        # boundary data for the prescribed relative mouth curve. The 2D chart
        # spans the endpoint vector and transverse terminal velocity.
        rest_state = endpoint_model["endpoint_event_separation_in_target_endpoint_rest_frame"]
        # The boundary events and the prescribed curve must use one chart's
        # coordinate interval, including relativity of simultaneity.
        coordinate_epoch_gap_s = float(rest_state["target_to_control_coordinate_time_s"])
        endpoint_vector = tuple(rest_state["target_to_control_spatial_vector_lightyears"])
        earth_endpoint_distance_ly = float(rest_state["target_to_control_distance_lightyears"])
        # The mouth-history profile starts with B displaced by the prescribed
        # gap along the endpoint chord. Subtract that initial offset so the
        # absolute terminal B position lands on the Earth endpoint event.
        endpoint_distance_ly = earth_endpoint_distance_ly-mouth_gap_ly
        if endpoint_distance_ly < 0.0:
            parser.error("mouth gap exceeds the Earth endpoint separation; choose a smaller --mouth-gap-m")
        earth_velocity = tuple(rest_state["control_endpoint_velocity_fraction_of_c"])
        if endpoint_distance_ly > 0.0:
            route_axis = tuple(value/earth_endpoint_distance_ly for value in endpoint_vector)
            parallel_velocity = sum(route_axis[i]*earth_velocity[i] for i in range(3))
            transverse = tuple(earth_velocity[i]-parallel_velocity*route_axis[i] for i in range(3))
            transverse_speed = math.sqrt(sum(value*value for value in transverse))
            endpoint_velocity_beta = (parallel_velocity, transverse_speed)
            if transverse_speed > 1e-15:
                transverse_axis = tuple(value/transverse_speed for value in transverse)
            else:
                reference_axis = (1.0, 0.0, 0.0) if abs(route_axis[0]) < 0.8 else (0.0, 1.0, 0.0)
                cross = (
                    route_axis[1]*reference_axis[2]-route_axis[2]*reference_axis[1],
                    route_axis[2]*reference_axis[0]-route_axis[0]*reference_axis[2],
                    route_axis[0]*reference_axis[1]-route_axis[1]*reference_axis[0],
                )
                cross_norm = math.sqrt(sum(value*value for value in cross))
                transverse_axis = tuple(value/cross_norm for value in cross)
            route_plane_basis = (route_axis, transverse_axis)
        reference_velocity_beta_icrf = tuple(
            endpoint_model["mean_reference_worldline_velocity_beta_icrf"]
        )
    required_offset_s = coordinate_epoch_gap_s + args.throat_seconds
    lag_years = required_offset_s / JULIAN_YEAR_S
    if endpoint_distance_ly < 0:
        parser.error("endpoint displacement must be nonnegative; the route axis is oriented toward the endpoint")
    try:
        result = planar_profile(
            lag_years,
            args.beta_max,
            endpoint_distance_ly,
            args.transverse_excursion_ly,
            args.profile,
            endpoint_velocity_beta,
        )
    except ValueError as exc:
        parser.error(str(exc))
    if "clock_lag_solver_residual_seconds" not in result:
        # Reintegrate the prescribed 1D profile at the solved duration. The
        # requested offset is billions of seconds in some scenarios, so the
        # endpoint check below must use this relative clock difference rather
        # than subtracting two large absolute epochs.
        solved_duration = float(result["exterior_duration_years"])
        integrated_lag_years = solved_duration * simpson_mean(
            lambda u: 1.0 - math.sqrt(
                1.0 - beta_at(
                    u, solved_duration, endpoint_distance_ly, args.beta_max, args.profile
                ) ** 2
            ),
            20_000,
        )
        result["clock_lag_solver_residual_seconds"] = (
            integrated_lag_years - lag_years
        ) * JULIAN_YEAR_S
        result["integrated_clock_lag_years"] = integrated_lag_years
    crew_seconds = args.crew_minutes * 60.0
    crew_years = crew_seconds / JULIAN_YEAR_S
    requested_rate = args.view_span_years / crew_years if crew_years else float("inf")
    equal_clock_span_years = crew_years
    # Preliminary return-ray screen in the same flat 2D spatial embedding: at
    # the target-mouth exit event, emit an ordinary null signal toward the
    # moving entry mouth along its solved planar worldline.
    profile_duration = float(result["exterior_duration_years"])
    target_exit_year = (
        float(result["moving_mouth_proper_time_years"])
        + args.throat_seconds / JULIAN_YEAR_S
    )
    # Match the exit event using relative clock differences. Reconstructing
    # it as (control - profile duration) + mouth proper age subtracts large
    # absolute epochs and can manufacture a much larger residual. Keep the
    # exact input date arithmetic in Decimal where TDB Julian dates were given.
    year_decimal = Decimal(str(JULIAN_YEAR_S))
    throat_decimal = Decimal(str(args.throat_seconds))
    integrated_lag_decimal_s = (
        Decimal(str(result["integrated_clock_lag_years"])) * year_decimal
    )
    if jd_tdb_mode:
        requested_gap_decimal_s = (
            (args.control_jd_tdb - args.witness_jd_tdb) * Decimal(str(SECONDS_PER_DAY))
            + Decimal(str(light_time_s))
        )
    else:
        requested_gap_decimal_s = Decimal(str(coordinate_epoch_gap_s))
    endpoint_residual_decimal_s = (
        requested_gap_decimal_s + throat_decimal - integrated_lag_decimal_s
    )
    if args.witness_transverse_baseline_km is not None:
        observer_2_delay = Decimal(str(witness_baseline["additional_light_travel_time_to_observer_2_s"]))
        if jd_tdb_mode:
            observer_2_prediction_jd = args.witness_jd_tdb + (
                endpoint_residual_decimal_s+observer_2_delay
            )/Decimal(str(SECONDS_PER_DAY))
            witness_baseline["observer_2_geometric_arrival_if_separately_illuminated_jd_tdb"] = (
                f"{observer_2_prediction_jd:.15f}"
            )
        else:
            witness_baseline["observer_2_geometric_arrival_if_separately_illuminated_utc"] = (
                witness_utc + timedelta(seconds=float(endpoint_residual_decimal_s+observer_2_delay))
            ).isoformat()
    beta_profile = args.beta_max
    profile_name = args.profile
    endpoint_ly = endpoint_distance_ly

    def terminal_basis(u: float) -> tuple[float, float, float]:
        h = -4.0*u**3 + 7.0*u**4 - 3.0*u**5
        dh = -12.0*u**2 + 28.0*u**3 - 15.0*u**4
        ddh = -24.0*u + 84.0*u**2 - 60.0*u**3
        return h, dh, ddh

    def mouth_xy(time_years: float) -> tuple[float, float]:
        if time_years >= profile_duration:
            return mouth_gap_ly + endpoint_ly, 0.0
        u = max(0.0, time_years / profile_duration)
        h, _, _ = terminal_basis(u)
        x = position_at(u, profile_duration, endpoint_ly, beta_profile, profile_name) + profile_duration*endpoint_velocity_beta[0]*h
        y_power = 4 if profile_name == "c2" else 2
        y = args.transverse_excursion_ly * math.sin(math.pi*u) ** y_power + profile_duration*endpoint_velocity_beta[1]*h
        return mouth_gap_ly + x, y

    def mouth_velocity(u: float) -> tuple[float, float]:
        theta = math.pi * u
        _, dh, _ = terminal_basis(u)
        vx = beta_at(u, profile_duration, endpoint_ly, beta_profile, profile_name) + endpoint_velocity_beta[0]*dh
        if profile_name == "c2":
            vy = (
                4.0 * math.pi * args.transverse_excursion_ly / profile_duration
                * math.sin(theta) ** 3 * math.cos(theta)
            ) + endpoint_velocity_beta[1]*dh
        else:
            vy = (
                math.pi * args.transverse_excursion_ly / profile_duration
                * math.sin(2.0 * theta)
            ) + endpoint_velocity_beta[1]*dh
        return vx, vy

    def mouth_acceleration(u: float) -> tuple[float, float]:
        theta = math.pi * u
        ax = beta_derivative_per_year(
            u, profile_duration, endpoint_ly, beta_profile, profile_name
        ) + endpoint_velocity_beta[0]*terminal_basis(u)[2]/profile_duration
        if profile_name == "c2":
            ay = (
                4.0 * math.pi**2 * args.transverse_excursion_ly / profile_duration**2
                * (3.0 * math.sin(theta)**2 * math.cos(theta)**2 - math.sin(theta)**4)
            ) + endpoint_velocity_beta[1]*terminal_basis(u)[2]/profile_duration
        else:
            ay = (
                2.0 * math.pi**2 * args.transverse_excursion_ly / profile_duration**2
                * math.cos(2.0 * theta)
            ) + endpoint_velocity_beta[1]*terminal_basis(u)[2]/profile_duration
        return ax, ay

    def evaluate_bezier(controls: list[tuple[float, float]], u: float) -> tuple[float, float]:
        level = list(controls)
        while len(level) > 1:
            level = [
                ((1.0-u)*level[i][0] + u*level[i+1][0],
                 (1.0-u)*level[i][1] + u*level[i+1][1])
                for i in range(len(level)-1)
            ]
        return level[0]

    def split_bezier_half(
        controls: list[tuple[float, float]],
    ) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
        levels = [list(controls)]
        while len(levels[-1]) > 1:
            previous = levels[-1]
            levels.append([
                ((previous[i][0]+previous[i+1][0])/2.0,
                 (previous[i][1]+previous[i+1][1])/2.0)
                for i in range(len(previous)-1)
            ])
        left = [level[0] for level in levels]
        right = [level[-1] for level in reversed(levels)]
        return left, right

    def certified_bezier_speed_bound(
        controls: list[tuple[float, float]], depth: int = 0,
    ) -> float | None:
        bound = max(math.hypot(x, y) for x, y in controls)
        if bound < 1.0:
            return bound
        if depth >= 16:
            return None
        left, right = split_bezier_half(controls)
        left_bound = certified_bezier_speed_bound(left, depth+1)
        right_bound = certified_bezier_speed_bound(right, depth+1)
        if left_bound is None or right_bound is None:
            return None
        return max(left_bound, right_bound)

    def earth_return_clearance(
        controls: list[tuple[float, float]],
        velocity_controls: list[tuple[float, float]],
        acceleration_controls: list[tuple[float, float]],
        duration: float,
        hull_speed_bound_beta: float | None,
    ) -> dict[str, object]:
        """Screen the 3D return hull against the sampled, rotating Earth."""
        if endpoint_model is None or route_plane_basis is None:
            return {"status": "unknown_no_earth_worldline_or_3d_basis", "sample_count": 0}
        target_utc = datetime.fromisoformat(endpoint_model["target_emission_event_utc"])
        control_utc = datetime.fromisoformat(endpoint_model["control_event_utc"])
        query_start, query_stop = target_utc-timedelta(days=1), control_utc+timedelta(days=1)
        earth_rows = query_earth_sun_series_utc(query_start, query_stop, "1 d")
        earth_rows.extend([
            (target_utc, tuple(endpoint_model["earth_sun_position_at_target_km_icrf"]), tuple(endpoint_model["earth_sun_velocity_at_target_km_s_icrf"])),
            (control_utc, tuple(endpoint_model["earth_sun_position_at_control_km_icrf"]), tuple(endpoint_model["earth_sun_velocity_at_control_km_s_icrf"])),
        ])
        target_site = endpoint_model.get("target_site_longitude_latitude_altitude")
        control_site = endpoint_model.get("control_site_longitude_latitude_altitude")
        site_orientation_available = target_site is not None and control_site is not None
        if site_orientation_available:
            near_endpoint_windows = [
                (target_utc, target_utc+timedelta(seconds=220), "220"),
                (target_utc+timedelta(seconds=220), target_utc+timedelta(seconds=600), "76"),
                (target_utc+timedelta(seconds=600), target_utc+timedelta(hours=1), "100"),
                (target_utc+timedelta(hours=1), target_utc+timedelta(days=1), "276"),
                (target_utc+timedelta(days=1), target_utc+timedelta(days=3), "8"),
                (control_utc-timedelta(days=3), control_utc-timedelta(days=1), "8"),
                (control_utc-timedelta(days=1), control_utc-timedelta(hours=1), "276"),
                (control_utc-timedelta(hours=1), control_utc-timedelta(seconds=600), "100"),
                (control_utc-timedelta(seconds=600), control_utc-timedelta(seconds=220), "76"),
                (control_utc-timedelta(seconds=220), control_utc, "220"),
            ]
            for window_start, window_stop, step in near_endpoint_windows:
                if window_start < target_utc or window_stop > control_utc:
                    continue
                earth_rows.extend(query_earth_sun_series_utc(window_start, window_stop, step))
        target_epoch = target_utc.timestamp()
        total_elapsed = control_utc.timestamp()-target_epoch
        target_sun = tuple(endpoint_model["earth_sun_position_at_target_km_icrf"])
        target_site_offset = tuple(endpoint_model["target_earth_geocenter_offset_km_icrf"])
        solar_velocity = tuple(endpoint_model["local_solar_velocity_km_s_icrf"])
        solar_acceleration = tuple(endpoint_model["local_solar_acceleration_km_s2_icrf"])
        rest = endpoint_model["endpoint_event_separation_in_target_endpoint_rest_frame"]
        frame_beta = tuple(rest["target_endpoint_velocity_fraction_of_c_icrf"])
        duration_s = duration*JULIAN_YEAR_S
        route_axis, transverse_axis = route_plane_basis
        earth_acceleration_bound_m_s2 = 0.02
        earth_angular_rate_rad_s = 7.2921150e-5
        axis_rate_allowance_rad_s = 1e-8
        a_m = EARTH_EQUATORIAL_RADIUS_KM*1000.0
        b_m = EARTH_POLAR_RADIUS_KM*1000.0
        hull_radius_m = args.return_hull_radius_m
        endpoint_axis_rate_rad_s = 0.0
        if site_orientation_available and target_site is not None and control_site is not None:
            def infer_spin_axis(site_vector_km: tuple[float, float, float],
                                rotation_velocity_km_s: tuple[float, float, float],
                                latitude_deg: float) -> tuple[float, float, float]:
                radius2 = sum(value*value for value in site_vector_km)
                radius = math.sqrt(radius2)
                radial = tuple(value/radius for value in site_vector_km)
                cross = (
                    site_vector_km[1]*rotation_velocity_km_s[2]-site_vector_km[2]*rotation_velocity_km_s[1],
                    site_vector_km[2]*rotation_velocity_km_s[0]-site_vector_km[0]*rotation_velocity_km_s[2],
                    site_vector_km[0]*rotation_velocity_km_s[1]-site_vector_km[1]*rotation_velocity_km_s[0],
                )
                omega_perpendicular = tuple(value/radius2 for value in cross)
                perpendicular2 = sum(value*value for value in omega_perpendicular)
                parallel_magnitude = math.sqrt(max(
                    0.0, earth_angular_rate_rad_s**2-perpendicular2
                ))
                parallel = math.copysign(parallel_magnitude, latitude_deg)
                omega = tuple(
                    omega_perpendicular[i]+parallel*radial[i] for i in range(3)
                )
                norm = math.sqrt(sum(value*value for value in omega))
                return tuple(value/norm for value in omega)

            target_axis_icrf = infer_spin_axis(
                tuple(endpoint_model["target_earth_geocenter_offset_km_icrf"]),
                tuple(endpoint_model["target_site_rotational_velocity_offset_km_s_icrf"]),
                float(target_site[1]),
            )
            control_axis_icrf = infer_spin_axis(
                tuple(endpoint_model["control_earth_geocenter_offset_km_icrf"]),
                tuple(endpoint_model["control_site_rotational_velocity_offset_km_s_icrf"]),
                float(control_site[1]),
            )
            endpoint_axis_dot = sum(target_axis_icrf[i]*control_axis_icrf[i] for i in range(3))
            if endpoint_axis_dot < 0.0:
                control_axis_icrf = tuple(-value for value in control_axis_icrf)
                endpoint_axis_dot = -endpoint_axis_dot
            endpoint_axis_rate_rad_s = math.acos(min(1.0, endpoint_axis_dot))/duration_s
            target_axis_target = lorentz_transform_spatial_vector_to_rest(target_axis_icrf, frame_beta)
            control_axis_target = lorentz_transform_spatial_vector_to_rest(control_axis_icrf, frame_beta)
        else:
            target_axis_target = control_axis_target = (0.0, 0.0, 1.0)
        hull_acceleration_bound_beta_per_year = max(
            math.hypot(ax, ay) for ax, ay in acceleration_controls
        )
        samples: list[tuple[float, float, float, tuple[float, float, float], datetime, float, tuple[float, float, float]]] = []
        endpoint_sample_geometry: list[dict[str, float | str]] = []
        for event_utc, earth_sun, orbital_velocity in earth_rows:
            dt = event_utc.timestamp()-target_epoch
            target_solar_velocity = tuple(
                solar_velocity[i]-solar_acceleration[i]*total_elapsed for i in range(3)
            )
            delta_position = tuple(
                earth_sun[i]-target_sun[i]+target_solar_velocity[i]*dt
                +0.5*solar_acceleration[i]*dt*dt-target_site_offset[i]
                for i in range(3)
            )
            tau, earth_position = lorentz_transform_event_to_rest(dt, delta_position, frame_beta)
            earth_velocity_icrf = tuple(
                solar_velocity[i]+solar_acceleration[i]*(dt-total_elapsed)+orbital_velocity[i]
                for i in range(3)
            )
            earth_velocity_beta = lorentz_transform_velocity_to_rest(
                tuple(value/(C_M_S/1000.0) for value in earth_velocity_icrf), frame_beta
            )
            earth_speed_beta = math.sqrt(sum(value*value for value in earth_velocity_beta))
            if 0.0 <= tau <= duration_s:
                u = tau/duration_s
                x, y = evaluate_bezier(controls, u)
                hull_position = tuple(
                    (x*route_axis[i]+y*transverse_axis[i])*KM_PER_LY for i in range(3)
                )
                vx, vy = evaluate_bezier(velocity_controls, u)
                hull_velocity_beta = tuple(vx*route_axis[i]+vy*transverse_axis[i] for i in range(3))
                relative_speed_beta = math.sqrt(sum(
                    (hull_velocity_beta[i]-earth_velocity_beta[i])**2 for i in range(3)
                ))
                relative_position = tuple(hull_position[i]-earth_position[i] for i in range(3))
                distance_km = math.sqrt(sum(value*value for value in relative_position))
                if site_orientation_available:
                    axis_weight = max(0.0, min(1.0, tau/duration_s))
                    spin_axis_target = tuple(
                        (1.0-axis_weight)*target_axis_target[i]+axis_weight*control_axis_target[i]
                        for i in range(3)
                    )
                    spin_norm = math.sqrt(sum(value*value for value in spin_axis_target))
                    spin_axis_target = tuple(value/spin_norm for value in spin_axis_target)
                    radial_hat = tuple(value/distance_km for value in relative_position)
                    axial_cosine = sum(radial_hat[i]*spin_axis_target[i] for i in range(3))
                    boundary_m = 1.0/math.sqrt(
                        (1.0-axial_cosine*axial_cosine)/(a_m*a_m)
                        + axial_cosine*axial_cosine/(b_m*b_m)
                    )
                else:
                    spin_axis_target = (0.0, 0.0, 1.0)
                    boundary_m = a_m
                clearance_m = distance_km*1000.0-boundary_m-hull_radius_m
                samples.append((tau, clearance_m, earth_speed_beta, spin_axis_target, event_utc, relative_speed_beta, relative_position))
                if abs(dt) < 2.0 or abs(dt-total_elapsed) < 2.0:
                    endpoint_sample_geometry.append({
                        "event_utc": event_utc.isoformat(),
                        "hull_center_radius_from_earth_center_km": distance_km,
                        "ellipsoid_radial_boundary_m": boundary_m,
                        "hull_radius_m": hull_radius_m,
                        "clearance_m": clearance_m,
                        "radial_axis_cosine": axial_cosine,
                    })
        # The geodetic endpoint events are exact route boundary conditions.
        # Preserve their declared ellipsoid altitudes even if Horizons' UTC
        # output rounds the neighboring ephemeris state by a second and the
        # Lorentz transform places the Earth-center event just outside the
        # sampled tau interval.
        if not samples:
            return {"status": "unresolved_no_earth_samples", "sample_count": 0}
        if site_orientation_available and target_site is not None and control_site is not None:
            target_nearest = min(samples, key=lambda row: abs(row[0]))
            control_nearest = min(samples, key=lambda row: abs(row[0]-duration_s))
            target_site_vector = lorentz_transform_spatial_vector_to_rest(
                tuple(endpoint_model["target_earth_geocenter_offset_km_icrf"]), frame_beta
            )
            control_site_vector = lorentz_transform_spatial_vector_to_rest(
                tuple(endpoint_model["control_earth_geocenter_offset_km_icrf"]), frame_beta
            )
            endpoint_samples = [
                (0.0, float(target_site[2])*1000.0-hull_radius_m,
                 target_nearest[2], target_nearest[3], target_utc, target_nearest[5], target_site_vector),
                (duration_s, float(control_site[2])*1000.0-hull_radius_m,
                 control_nearest[2], control_nearest[3], control_utc, control_nearest[5], control_site_vector),
            ]
            samples.extend(endpoint_samples)
            endpoint_sample_geometry.extend([
                {
                    "event_utc": target_utc.isoformat(),
                    "clearance_m": float(target_site[2])*1000.0-hull_radius_m,
                    "clearance_source": "declared geodetic hull-center altitude minus hull radius",
                },
                {
                    "event_utc": control_utc.isoformat(),
                    "clearance_m": float(control_site[2])*1000.0-hull_radius_m,
                    "clearance_source": "declared geodetic hull-center altitude minus hull radius",
                },
            ])
        samples.sort(key=lambda row: row[0])
        if len(samples) < 2:
            return {"status": "unresolved_insufficient_earth_samples", "sample_count": len(samples)}
        min_sample = min(samples, key=lambda row: row[1])
        min_lower_bound_m = math.inf
        max_interval_s = 0.0
        max_earth_speed_beta = max(row[2] for row in samples)
        observed_axis_rate = endpoint_axis_rate_rad_s
        interval_diagnostics: list[dict[str, float]] = []
        for first, second in zip(samples, samples[1:]):
            dt = second[0]-first[0]
            if dt <= 0.0:
                continue
            max_interval_s = max(max_interval_s, dt)
            axis_dot_signed = sum(first[3][i]*second[3][i] for i in range(3))
            axis_sign = 1.0 if axis_dot_signed >= 0.0 else -1.0
            axis_mid = tuple(first[3][i]+axis_sign*second[3][i] for i in range(3))
            axis_mid_norm = math.sqrt(sum(value*value for value in axis_mid))
            axis_mid = tuple(value/axis_mid_norm for value in axis_mid)

            def scale_to_unit_ellipsoid(vector_km: tuple[float, float, float]) -> tuple[float, float, float]:
                vector_m = tuple(value*1000.0 for value in vector_km)
                axial = sum(vector_m[i]*axis_mid[i] for i in range(3))
                return tuple(
                    vector_m[i]/a_m+axis_mid[i]*axial*(1.0/b_m-1.0/a_m)
                    for i in range(3)
                )

            first_scaled = scale_to_unit_ellipsoid(first[6])
            second_scaled = scale_to_unit_ellipsoid(second[6])
            chord = tuple(second_scaled[i]-first_scaled[i] for i in range(3))
            chord2 = sum(value*value for value in chord)
            chord_parameter = (
                max(0.0, min(1.0, -sum(first_scaled[i]*chord[i] for i in range(3))/chord2))
                if chord2 > 0.0 else 0.0
            )
            chord_nearest = tuple(first_scaled[i]+chord_parameter*chord[i] for i in range(3))
            chord_min_scaled_radius = math.sqrt(sum(value*value for value in chord_nearest))
            chord_clearance_m = b_m*(chord_min_scaled_radius-1.0)-hull_radius_m

            # A twice-differentiable relative path stays within A*dt^2/8 of
            # its endpoint chord when its acceleration is bounded by A. The
            # ellipsoid's axial orientation is bounded separately below.
            hull_acceleration_m_s2 = (
                hull_acceleration_bound_beta_per_year*C_M_S/JULIAN_YEAR_S
            )
            relative_acceleration_m_s2 = earth_acceleration_bound_m_s2+hull_acceleration_m_s2
            curve_interpolation_error_m = relative_acceleration_m_s2*dt*dt/8.0
            axis_angle_bound = (endpoint_axis_rate_rad_s+axis_rate_allowance_rad_s)*dt
            axis_orientation_error_m = a_m*axis_angle_bound
            lower = chord_clearance_m-curve_interpolation_error_m-axis_orientation_error_m
            min_lower_bound_m = min(min_lower_bound_m, lower)
            interval_diagnostics.append({
                "start_years_after_target_exit": first[0]/JULIAN_YEAR_S,
                "end_years_after_target_exit": second[0]/JULIAN_YEAR_S,
                "start_clearance_m": first[1],
                "end_clearance_m": second[1],
                "sampled_relative_speed_m_s": max(first[5], second[5])*C_M_S,
                "linear_chord_ellipsoid_clearance_lower_m": chord_clearance_m,
                "relative_path_interpolation_error_bound_m": curve_interpolation_error_m,
                "earth_axis_orientation_error_bound_m": axis_orientation_error_m,
                "continuous_clearance_lower_bound_m": lower,
            })
        if min_sample[1] <= 0.0:
            status = "rejected_sampled_earth_hull_intersection" if site_orientation_available else "possible_intersection_with_spherical_earth_envelope"
        elif min_lower_bound_m > 0.0:
            status = "conditionally_clear_of_idealized_earth_envelope_on_material_return"
        else:
            status = "unresolved_continuous_earth_clearance"
        return {
            "status": status,
            "model": "3D C2 material return versus DE441 Earth centerline transformed into the target endpoint rest frame",
            "earth_shape": "WGS84 oblate ellipsoid oriented from interpolated Horizons geodetic endpoint spin axes" if site_orientation_available else "conservative WGS84 equatorial-radius sphere; overlaps indicate possible collision only",
            "earth_orientation_source": "spin axis inferred from Horizons geodetic endpoint position/velocity, interpolated between endpoint axes; interior-axis departure bounded by the declared angular-rate allowance" if site_orientation_available else "unavailable without geodetic site coordinates",
            "endpoint_sample_geometry": endpoint_sample_geometry,
            "sample_count": len(samples),
            "ephemeris_step": "1 d baseline with endpoint-refined intervals",
            "minimum_sampled_clearance_m": min_sample[1],
            "minimum_sample_time_years_after_target_exit": min_sample[0]/JULIAN_YEAR_S,
            "continuous_clearance_lower_bound_m": min_lower_bound_m,
            "maximum_sample_interval_seconds": max_interval_s,
            "maximum_sampled_earth_speed_fraction_of_c": max_earth_speed_beta,
            "earth_center_acceleration_bound_m_s2": earth_acceleration_bound_m_s2,
            "earth_spin_axis_rate_allowance_rad_s": axis_rate_allowance_rad_s,
            "interpolated_earth_axis_rate_rad_s": observed_axis_rate,
            "endpoint_inferred_earth_axis_rate_rad_s": endpoint_axis_rate_rad_s,
            "certified_return_speed_upper_bound_fraction_of_c": hull_speed_bound_beta,
            "return_acceleration_upper_bound_beta_per_year": hull_acceleration_bound_beta_per_year,
            "lowest_sampled_interval_bounds": sorted(
                interval_diagnostics, key=lambda row: row["continuous_clearance_lower_bound_m"]
            )[:8],
            "bound_basis": "minimum endpoint-chord distance in scaled WGS84 ellipsoid coordinates, reduced by the A*dt^2/8 relative-curve deviation bound and a*axis-angle Earth-orientation allowance",
            "relative_acceleration_bound_m_s2": earth_acceleration_bound_m_s2+hull_acceleration_bound_beta_per_year*C_M_S/JULIAN_YEAR_S,
            "scope_limits": "conditional on the stated Earth-center acceleration and interior Earth-axis-rate bounds; only the material exterior return and ideal Earth envelope are screened; earlier mouth history, terrain, structures, Moon, satellites, other planets, throat, and ephemeris/model uncertainties are not covered",
        }

    def timelike_return_candidate() -> dict[str, object]:
        """Build a C2 quintic return in the prescribed flat 2D exterior."""
        duration = profile_duration - target_exit_year
        if duration <= 0.0:
            return {"status": "unavailable: no positive exterior interval to the control event"}
        start = (0.0, 0.0)
        end = mouth_xy(profile_duration)
        start_velocity = (0.0, 0.0)
        start_acceleration = (0.0, 0.0)
        end_velocity = mouth_velocity(1.0)
        end_acceleration = mouth_acceleration(1.0)
        t = duration
        controls = [
            start,
            (start[0]+t*start_velocity[0]/5.0,
             start[1]+t*start_velocity[1]/5.0),
            (start[0]+2*t*start_velocity[0]/5.0+t*t*start_acceleration[0]/20.0,
             start[1]+2*t*start_velocity[1]/5.0+t*t*start_acceleration[1]/20.0),
            (end[0]-2*t*end_velocity[0]/5.0+t*t*end_acceleration[0]/20.0,
             end[1]-2*t*end_velocity[1]/5.0+t*t*end_acceleration[1]/20.0),
            (end[0]-t*end_velocity[0]/5.0,
             end[1]-t*end_velocity[1]/5.0),
            end,
        ]
        velocity_controls = [
            (5.0*(controls[i+1][0]-controls[i][0])/t,
             5.0*(controls[i+1][1]-controls[i][1])/t)
            for i in range(5)
        ]
        acceleration_controls = [
            (4.0*(velocity_controls[i+1][0]-velocity_controls[i][0])/t,
             4.0*(velocity_controls[i+1][1]-velocity_controls[i][1])/t)
            for i in range(4)
        ]
        speed_bound = certified_bezier_speed_bound(velocity_controls)
        earth_clearance = earth_return_clearance(
            controls, velocity_controls, acceleration_controls, duration, speed_bound
        )
        intervals = 20_000
        proper_integral = 0.0
        sampled_timelike = True
        max_sample_speed = 0.0
        max_coordinate_acceleration = 0.0
        max_proper_acceleration = 0.0
        for i in range(intervals+1):
            u = i/intervals
            v = evaluate_bezier(velocity_controls, u)
            a = evaluate_bezier(acceleration_controls, u)
            speed2 = v[0]*v[0] + v[1]*v[1]
            if speed2 >= 1.0:
                sampled_timelike = False
                speed2 = 1.0
            weight = 1.0 if i in (0, intervals) else (4.0 if i % 2 else 2.0)
            proper_integral += weight*math.sqrt(1.0-speed2)
            speed = math.sqrt(v[0]*v[0]+v[1]*v[1])
            acceleration = math.hypot(a[0], a[1])
            max_sample_speed = max(max_sample_speed, speed)
            max_coordinate_acceleration = max(max_coordinate_acceleration, acceleration)
            if speed < 1.0:
                gamma = 1.0/math.sqrt(1.0-speed*speed)
                dot = v[0]*a[0]+v[1]*a[1]
                proper_acceleration = gamma**2*math.sqrt(
                    acceleration**2 + gamma**2*dot**2
                )
                max_proper_acceleration = max(max_proper_acceleration, proper_acceleration)
        certified = speed_bound is not None and speed_bound < 1.0
        proper_years = (
            duration*proper_integral/(3.0*intervals) if sampled_timelike else None
        )
        proper_time_seconds_decimal = (
            Decimal(str(proper_years)) * Decimal(str(JULIAN_YEAR_S))
            + Decimal(str(args.throat_seconds))
            if proper_years is not None else None
        )
        hull_radius_ly = args.return_hull_radius_m/METERS_PER_LIGHT_YEAR
        clearance_results: list[dict[str, object]] = []
        if not args.return_hazard:
            clearance_status = "unknown_no_return_hazards_supplied"
        else:
            clearance_status = "certified_clear_for_all_declared_2d_circles"
            clearance_intervals = 4_000
            dt = duration/clearance_intervals
            for hazard_index, hazard in enumerate(args.return_hazard, start=1):
                hx, hy, hvx, hvy, obstacle_radius = hazard
                obstacle_speed = math.hypot(hvx, hvy)
                minimum_clearance = math.inf
                minimum_time = 0.0
                minimum_position = [0.0, 0.0]
                for sample_index in range(clearance_intervals+1):
                    u = sample_index/clearance_intervals
                    position = evaluate_bezier(controls, u)
                    local_time = duration*u
                    obstacle_position = (hx+hvx*local_time, hy+hvy*local_time)
                    clearance = (
                        math.hypot(position[0]-obstacle_position[0], position[1]-obstacle_position[1])
                        - obstacle_radius-hull_radius_ly
                    )
                    if clearance < minimum_clearance:
                        minimum_clearance = clearance
                        minimum_time = local_time
                        minimum_position = [position[0], position[1]]
                between_sample_margin = (
                    0.5*dt*(speed_bound+obstacle_speed) if speed_bound is not None else None
                )
                lower_bound = (
                    minimum_clearance-between_sample_margin
                    if between_sample_margin is not None else None
                )
                if minimum_clearance <= 0.0:
                    hazard_status = "sampled_hull_envelope_intersection"
                elif lower_bound is not None and lower_bound > 0.0:
                    hazard_status = "certified_clear_for_declared_2d_circle"
                else:
                    hazard_status = "clearance_unresolved_by_sampling_bound"
                clearance_results.append({
                    "hazard": f"return_hazard_{hazard_index}",
                    "status": hazard_status,
                    "obstacle_initial_center_light_years_at_target_exit": [hx, hy],
                    "obstacle_velocity_fraction_of_c": [hvx, hvy],
                    "obstacle_radius_light_years": obstacle_radius,
                    "hull_envelope_radius_m": args.return_hull_radius_m,
                    "minimum_sampled_centerline_clearance_light_years": minimum_clearance,
                    "minimum_sampled_centerline_clearance_m": minimum_clearance*METERS_PER_LIGHT_YEAR,
                    "minimum_sample_time_years_after_exit": minimum_time,
                    "hull_position_at_minimum_sample_light_years": minimum_position,
                    "conservative_full_segment_clearance_lower_bound_light_years": lower_bound,
                    "conservative_full_segment_clearance_lower_bound_m": (
                        lower_bound*METERS_PER_LIGHT_YEAR if lower_bound is not None else None
                    ),
                    "between_sample_margin_light_years": between_sample_margin,
                    "bound_basis": "distance to a circle is 1-Lipschitz; a certified hull-speed upper bound plus constant obstacle speed bounds motion between adjacent samples",
                })
                if hazard_status == "sampled_hull_envelope_intersection":
                    clearance_status = "rejected_by_declared_return_hazard"
                elif hazard_status == "clearance_unresolved_by_sampling_bound" and clearance_status != "rejected_by_declared_return_hazard":
                    clearance_status = "return_hazard_clearance_unresolved"
        clearance_summary = {
            "status": clearance_status,
            "model": "continuous-clearance bounds against user-supplied constant-velocity circles in the flat return plane",
            "hull_envelope_radius_m": args.return_hull_radius_m,
            "hazards": clearance_results,
            "unmodeled": "absence of supplied hazards is not clearance; 3D shape, Earth rotation/orbit, terrain, other bodies, throat, and unlisted hazards are not covered",
        }
        if certified and earth_clearance["status"] == "rejected_sampled_earth_hull_intersection":
            return_status = "certified_timelike_candidate_rejected_by_earth_collision"
        elif certified and clearance_status == "rejected_by_declared_return_hazard":
            return_status = "certified_timelike_candidate_rejected_by_declared_hazard"
        else:
            return_status = (
                "certified_timelike_flat_exterior_candidate"
                if certified else "not_certified_subluminal"
            )
        return {
            "status": return_status,
            "coordinate_duration_years": duration,
            "start_position_light_years": list(start),
            "end_position_light_years": list(end),
            "start_velocity_over_c": list(start_velocity),
            "end_velocity_over_c_matched_to_entry_mouth": list(end_velocity),
            "end_acceleration_light_years_per_year2_matched_to_entry_mouth": list(end_acceleration),
            "sampled_peak_speed_fraction_of_c": max_sample_speed,
            "certified_full_curve_speed_upper_bound_fraction_of_c": speed_bound,
            "exterior_return_proper_time_years_simpson_20000_intervals": proper_years,
            "sampled_peak_coordinate_acceleration_m_s2": max_coordinate_acceleration*C_M_S/JULIAN_YEAR_S,
            "sampled_peak_proper_acceleration_m_s2": max_proper_acceleration*C_M_S/JULIAN_YEAR_S,
            "continuous_hazard_clearance": clearance_summary,
            "earth_collision_clearance": earth_clearance,
            "conditional_closed_loop_hull_proper_time_years_including_throat": (
                proper_years+args.throat_seconds/JULIAN_YEAR_S if certified else None
            ),
            "conditional_closed_loop_hull_proper_time_seconds_including_throat_decimal": (
                str(proper_time_seconds_decimal) if certified else None
            ),
            "throat_transit_below_return_proper_time_float_resolution": (
                args.throat_seconds < math.ulp(proper_years)*JULIAN_YEAR_S if certified else None
            ),
            "curve": "quintic Bezier matching position, velocity, and acceleration at both endpoints; speed bound from recursive subdivision of the quartic velocity control polygon",
            "scope": "flat 2D material curve embedded in a 3D Earth-centered inertial chart; entry approach, throat event/tangent map, other 3D hazards, attitude, and field-state closure are not solved",
        }

    def return_residual(time_years: float) -> float:
        x, y = mouth_xy(time_years)
        return time_years - target_exit_year - math.hypot(x, y)

    closure = {
        "model": "flat 2D spatial null-reachability and quintic timelike-return screens against the same smooth planar mouth worldline",
        "return_curve_type": "null (light ray)",
        "null_intersection_geometry": "flat 2D Minkowski exterior with c=1 light-year/year; target exit is at the spatial origin and the entry mouth follows the prescribed mouth_xy(T) worldline",
        "null_intersection_equation": "T_return - T_exit - hypot(x_entry(T_return), y_entry(T_return)) = 0",
        "null_intersection_solver": "90-step bisection on the flat-space null travel-time residual; not a geodesic integration through a throat metric",
        "material_traveler_ctc_status": (
            "not demonstrated until the separately reported timelike exterior candidate is certified; throat, Earth placement, hazards, and field-state closure remain open"
        ),
        "timelike_route_requirement": (
            "the null ray is a causal reachability screen; a material traveler needs a subluminal return curve that intersects the entry-mouth worldline with matching four-velocity"
        ),
    }
    timelike_route = timelike_return_candidate()
    closure["timelike_exterior_return_candidate"] = timelike_route
    if timelike_route.get("status") == "certified_timelike_candidate_rejected_by_earth_collision":
        closure["material_traveler_ctc_status"] = (
            "the material return intersects the sampled Earth envelope and is rejected"
        )
    elif timelike_route.get("status") == "certified_timelike_flat_exterior_candidate":
        return_clearance_status = timelike_route["continuous_hazard_clearance"]["status"]
        if return_clearance_status == "rejected_by_declared_return_hazard":
            closure["material_traveler_ctc_status"] = (
                "the timelike exterior candidate is rejected by at least one supplied 2D hazard"
            )
        else:
            closure["material_traveler_ctc_status"] = (
                "a C2 timelike exterior return candidate is certified in the prescribed flat 2D model; its Earth-ellipsoid clearance is conditional on the reported acceleration and axis-rate bounds, while the throat map, full 3D hazards, and field-state closure remain unsolved"
            )
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
            "null_intersection_residual_years": return_residual(return_time),
            "return_light_travel_time_years": return_time - target_exit_year,
            "control_event_coordinate_years_from_mouth_start": profile_duration,
            "remaining_wait_on_entry_mouth_worldline_years": profile_duration - return_time,
            "preliminary_loop_margin_years": profile_duration - return_time,
            "status": "null return intersects before or at control event; requires full geometry and state matching",
        })
    else:
        control_mouth_x, control_mouth_y = mouth_xy(profile_duration)
        closure.update({
            "target_exit_coordinate_years_from_mouth_start": target_exit_year,
            "control_event_coordinate_years_from_mouth_start": profile_duration,
            "null_intersection_residual_at_control_years": residual_at_control,
            "null_return_distance_at_control_light_years": math.hypot(
                control_mouth_x, control_mouth_y
            ),
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
    # An explicit, intentionally uncompressed image payload benchmark. This
    # is not a model of human vision or of the fictional channel; it makes
    # the data-rate consequence of the requested scan duration inspectable.
    bits_per_frame = 1920 * 1080 * 24
    raw_frame_rate_hz = Decimal("30")
    remote_acquisition_seconds_decimal = Decimal(str(args.view_span_years)) * year_decimal
    crew_window_seconds_decimal = Decimal(str(args.crew_minutes)) * Decimal("60")
    total_raw_frames_decimal = remote_acquisition_seconds_decimal * raw_frame_rate_hz
    total_raw_bits_decimal = total_raw_frames_decimal * Decimal(bits_per_frame)
    native_raw_rate = bits_per_frame * int(raw_frame_rate_hz)
    two_crossing_delay_decimal = Decimal(2) * throat_decimal
    raw_payload_rate = {
        "model": "uncompressed 1920x1080 RGB, 24 bits per pixel, 30 frames per second",
        "remote_acquisition_span_seconds_decimal": str(remote_acquisition_seconds_decimal),
        "remote_frame_count_decimal": str(total_raw_frames_decimal),
        "total_payload_bits_decimal": str(total_raw_bits_decimal),
        "native_continuous_stream_rate_bits_per_second": native_raw_rate,
        "native_rate_payload_delivery_duration_seconds_decimal": str(
            total_raw_bits_decimal / Decimal(native_raw_rate)
        ),
        "native_rate_first_sample_arrival_after_control_seconds_decimal": str(
            two_crossing_delay_decimal
        ),
        "native_rate_last_sample_arrival_after_control_seconds_decimal": str(
            remote_acquisition_seconds_decimal + two_crossing_delay_decimal
        ),
        "required_rate_if_all_remote_frames_arrive_during_crew_window_bits_per_second_decimal": str(
            total_raw_bits_decimal / crew_window_seconds_decimal
        ),
        "crew_window_seconds": args.crew_minutes * 60.0,
        "illustrative_assumption_only": True,
        "limits": "does not specify compression, perceptual quality, channel capacity, noise, energy, or a physical transfer mechanism",
    }
    acquisition_seconds_decimal = Decimal(str(args.view_span_years)) * year_decimal
    return_delay_decimal_s = (
        acquisition_seconds_decimal + Decimal(2) * throat_decimal
    )
    if jd_tdb_mode:
        return_receiver_event_label = (
            f"JD TDB {args.control_jd_tdb + return_delay_decimal_s / Decimal(str(SECONDS_PER_DAY)):.15f}"
        )
    elif control_utc is not None:
        return_receiver_event_label = (
            control_utc + timedelta(seconds=float(return_delay_decimal_s))
        ).isoformat()
    else:
        return_receiver_event_label = None
    return_payload_timing = {
        "model": "post-reunion equal-clock two-way timing; symmetric crossings are assumed",
        "target_side_acquisition_span_years": args.view_span_years,
        "outbound_throat_crossing_seconds": args.throat_seconds,
        "return_throat_crossing_seconds": args.throat_seconds,
        "receiver_delay_after_control_seconds_decimal": str(return_delay_decimal_s),
        "first_sample_receiver_delay_after_control_seconds_decimal": str(two_crossing_delay_decimal),
        "home_receiver_event_label": return_receiver_event_label,
        "time_compression": "none; target-side acquisition advances at unit slope in the mouth clock",
        "scope": "timing identity only; excludes detector, encoding, transfer, decoding, and solved-throat delays",
        "status": "return arrives after control by acquisition duration plus both throat crossings",
    }
    # In Earth-worldline mode, map the control event into the target
    # geocenter's instantaneous rest chart using the target event as the time
    # origin. Do not subtract a rest-frame duration from the raw UTC control
    # timestamp (that would mix distant simultaneity conventions).
    chart_control_epoch = (
        emitter_epoch + coordinate_epoch_gap_s if endpoint_model is not None else control
    )
    profile_start_epoch = chart_control_epoch - profile_duration * JULIAN_YEAR_S
    legacy_absolute_target_exit_epoch = profile_start_epoch + target_exit_year * JULIAN_YEAR_S
    if jd_tdb_mode:
        target_exit_epoch: float | Decimal = (
            (args.witness_jd_tdb - args.control_jd_tdb)
            * Decimal(str(SECONDS_PER_DAY))
            - Decimal(str(light_time_s))
            + endpoint_residual_decimal_s
        )
    else:
        target_exit_epoch = emitter_epoch + float(endpoint_residual_decimal_s)
    return_intercept_epoch = None
    if "return_signal_intersects_entry_mouth_at_years_from_start" in closure:
        return_intercept_epoch = profile_start_epoch + float(closure["return_signal_intersects_entry_mouth_at_years_from_start"]) * JULIAN_YEAR_S
    if endpoint_model is None:
        earth_frame_match = {
            "status": "unknown_no_earth_worldline_endpoint_supplied",
            "note": "the smooth-mouth endpoint is not anchored to an Earth event",
        }
    else:
        target_rest = endpoint_model["endpoint_event_separation_in_target_endpoint_rest_frame"]
        required_endpoint_ly = float(target_rest["target_to_control_distance_lightyears"])
        modeled_profile_displacement_ly = float(result["endpoint_displacement_light_years"])
        modeled_endpoint_ly = mouth_gap_ly+modeled_profile_displacement_ly
        control_beta = tuple(target_rest["control_endpoint_velocity_fraction_of_c"])
        control_speed_beta = math.sqrt(sum(value*value for value in control_beta))
        modeled_velocity = tuple(result["terminal_velocity_fraction_of_c"])
        modeled_speed_beta = math.sqrt(sum(value*value for value in modeled_velocity))
        velocity_residual_beta = abs(control_speed_beta-modeled_speed_beta)
        position_residual_ly = abs(required_endpoint_ly-modeled_endpoint_ly)
        earth_frame_match = {
            "status": "endpoint_position_and_velocity_boundary_conditions_imposed; material_return_earth_clearance="+str(timelike_route.get("earth_collision_clearance", {}).get("status", "not evaluated")),
            "target_to_control_site_event_separation_lightyears_in_target_endpoint_rest_frame": required_endpoint_ly,
            "prescribed_profile_relative_displacement_lightyears": modeled_profile_displacement_ly,
            "initial_gap_along_endpoint_chord_lightyears": mouth_gap_ly,
            "prescribed_moving_mouth_absolute_endpoint_position_lightyears": modeled_endpoint_ly,
            "endpoint_position_residual_magnitude_lightyears": position_residual_ly,
            "control_endpoint_velocity_fraction_of_c_in_target_rest_frame": list(control_beta),
            "control_endpoint_speed_fraction_of_c_in_target_rest_frame": control_speed_beta,
            "prescribed_moving_mouth_endpoint_velocity_in_route_plane_fraction_of_c": list(modeled_velocity),
            "prescribed_moving_mouth_endpoint_speed_fraction_of_c": modeled_speed_beta,
            "endpoint_speed_residual_fraction_of_c": velocity_residual_beta,
            "endpoint_velocity_match": "endpoint terminal velocity imposed after Lorentz transformation; 2D route plane spans the endpoint vector and terminal velocity",
            "mouth_gap_direction": "assumed aligned with the target-to-control endpoint chord so the initial gap plus profile displacement reaches the control endpoint",
            "site_rotation": endpoint_model["site_state_source"],
            "interpretation": "endpoint position and velocity are imposed; the separate material-return Earth screen covers only the modeled exterior leg under its declared bounds",
        }
    if endpoint_model is None:
        endpoint_clearance = {
            "status": "not evaluated; no Earth event endpoint was supplied",
            "route_note": "A prescribed scalar endpoint distance contains no Earth-site location or collision geometry.",
        }
    else:
        target_offset_norm = float(endpoint_model["target_event_radius_from_earth_center_km"])
        control_offset_norm = float(endpoint_model["control_event_radius_from_earth_center_km"])
        target_site = endpoint_model.get("target_site_longitude_latitude_altitude")
        control_site = endpoint_model.get("control_site_longitude_latitude_altitude")

        def reference_earth_status(radius_km: float, label: str) -> str:
            if radius_km < EARTH_POLAR_RADIUS_KM:
                return f"definitely inside the WGS84 reference ellipsoid ({label})"
            if radius_km > EARTH_EQUATORIAL_RADIUS_KM:
                return f"outside the WGS84 reference ellipsoid ({label}); terrain and route clearance remain unchecked"
            return f"ellipsoid intersection depends on Earth-fixed orientation ({label}); clearance unresolved"

        if target_site is not None and control_site is not None:
            target_hull_clearance_m = float(target_site[2])*1000.0-args.return_hull_radius_m
            control_hull_clearance_m = float(control_site[2])*1000.0-args.return_hull_radius_m
            target_endpoint_status = (
                f"hull envelope clears the reference ellipsoid by {target_hull_clearance_m:.3f} m at the endpoint; local terrain/structure clearance unknown"
                if target_hull_clearance_m > 0.0 else
                f"hull envelope intersects the reference ellipsoid by {-target_hull_clearance_m:.3f} m at the endpoint"
            )
            control_endpoint_status = (
                f"hull envelope clears the reference ellipsoid by {control_hull_clearance_m:.3f} m at the endpoint; local terrain/structure clearance unknown"
                if control_hull_clearance_m > 0.0 else
                f"hull envelope intersects the reference ellipsoid by {-control_hull_clearance_m:.3f} m at the endpoint"
            )
            endpoint_collision = target_hull_clearance_m <= 0.0 or control_hull_clearance_m <= 0.0
        else:
            target_endpoint_status = reference_earth_status(target_offset_norm, "geocenter offset")
            control_endpoint_status = reference_earth_status(control_offset_norm, "geocenter offset")
            target_hull_clearance_m = None
            control_hull_clearance_m = None
            endpoint_collision = target_offset_norm < EARTH_POLAR_RADIUS_KM or control_offset_norm < EARTH_POLAR_RADIUS_KM
        endpoint_clearance = {
            "target_event": target_endpoint_status,
            "control_event": control_endpoint_status,
            "target_offset_radius_km": target_offset_norm,
            "control_offset_radius_km": control_offset_norm,
            "target_hull_center_clearance_from_reference_ellipsoid_m": target_hull_clearance_m,
            "control_hull_center_clearance_from_reference_ellipsoid_m": control_hull_clearance_m,
            "site_coordinates": {"target": target_site, "control": control_site},
            "status": "rejected: endpoint hull intersects Earth" if endpoint_collision else "geodetic endpoint screen passed; terrain and full-loop hazard clearance are separate gates",
        }
    formation_constraint = {
        "model": "finite-formation, synchronized zero-offset mouths at or before the prescribed mouth-history start; no throat-formation dynamics are solved",
        "scope": "the formation-date bound applies to the standard equal-clock mouth map; a pre-shifted initial map would assume, not generate, the chronology-violating offset. Earth-worldline dates use the reference-mouth coordinate label anchored at the target event.",
        "latest_pair_formation_event_reference_mouth_coordinate_label": event_epoch_label(
            profile_start_epoch, jd_tdb_mode, jd_anchor_tdb
        ),
        "anchor_mouth_clock_age_at_target_exit_years_since_profile_start": target_exit_year,
        "target_exit_occurs_after_profile_start": target_exit_year > 0.0,
        "required_historical_presence": (
            "the anchor mouth and its supporting spacetime must exist on a propagated worldtube through the target event; "
            "a throat formed after that event cannot produce this exit under the equal-clock map"
        ),
        "unmodeled": "pair formation, pre-history, target-mouth trajectory to the event, and its gravitational/optical/environmental footprint",
    }
    formation_epoch = None
    if args.wormhole_formation_utc is not None:
        formation_epoch = args.wormhole_formation_utc.timestamp()
    elif args.wormhole_formation_jd_tdb is not None:
        if not args.wormhole_formation_jd_tdb.is_finite():
            parser.error("wormhole formation Julian date must be finite")
        formation_epoch = float(
            (args.wormhole_formation_jd_tdb - jd_anchor_tdb) * Decimal(str(SECONDS_PER_DAY))
        )
    if formation_epoch is None:
        formation_constraint.update({
            "assumed_pair_formation_event_label": None,
            "assumed_pair_formation_utc_label": None,
            "assumed_pair_formation_jd_tdb": None,
            "formation_time_gate_status": "not evaluated; supply a formation event in the same time scale as the route",
            "formation_margin_years_before_profile_start": None,
        })
    else:
        formation_margin_years = (profile_start_epoch - formation_epoch) / JULIAN_YEAR_S
        formation_constraint.update({
            "assumed_pair_formation_event_label": event_epoch_label(
                formation_epoch, jd_tdb_mode, jd_anchor_tdb
            ),
            "assumed_pair_formation_utc_label": (
                args.wormhole_formation_utc.isoformat()
                if args.wormhole_formation_utc is not None else None
            ),
            "assumed_pair_formation_jd_tdb": (
                str(args.wormhole_formation_jd_tdb)
                if args.wormhole_formation_jd_tdb is not None else None
            ),
            "formation_margin_years_before_profile_start": formation_margin_years,
            "formation_time_gate_status": (
                "passes date-ordering screen only; target-mouth intercept and formation physics remain unsolved"
                if formation_margin_years >= 0.0
                else "fails: this synchronized pair forms after the prescribed clock-offset history begins"
            ),
        })
    formation_fails = (
        formation_epoch is not None and formation_margin_years < 0.0
    )
    mission_viability = {
        "status": "rejected_by_formation_time_gate" if formation_fails else "not_demonstrated",
        "scope": "status for this prescribed synchronized-mouth candidate only; it is not a verdict on every possible chronology-violating spacetime",
        "gates": {
            "formation_time": formation_constraint["formation_time_gate_status"],
            "mouth_history": "prescribed flat-exterior kinematics; no dynamical wormhole solution",
            "throat_source_and_stability": "not solved",
            "target_site_intercept": endpoint_clearance["status"],
            "earth_endpoint_frame_match": earth_frame_match["status"],
            "material_return_earth_clearance": timelike_route.get("earth_collision_clearance", {}).get("status", "not evaluated"),
            "declared_2d_timelike_return_hazards": timelike_route.get("continuous_hazard_clearance", {}).get("status", "not evaluated"),
            "witness_optical_prediction": (
                "conditional scalar flux calculated from supplied target-side source assumptions; full witness geometry and route transfer remain unsolved"
                if args.witness_source_power_w is not None else
                "not calculated; source field and full witness geometry are not solved"
            ),
            "null_return_screen": closure["status"],
            "material_traveler_loop": closure["material_traveler_ctc_status"],
        },
    }
    if args.csv:
        write_planar_worldline_csv(
            args.csv, result, args.transverse_excursion_ly, endpoint_velocity_beta
        )
    output = {
        "scenario": (
            "conditional Star-era TDB timing illustration"
            if jd_tdb_mode else "conditional Phoenix Lights pilot-account timing illustration"
        ),
        "navigation_validation": {
            "overall_status": "conditional timing and prescribed-mouth kinematics; not validated temporal navigation",
            "home_to_target_beacon_path": "not ray-traced; target event is assigned by the assumed equal-clock mouth map",
            "target_to_witness_path": "flat scalar range divided by c; no event-specific null geodesic or actual witness worldline",
            "lead_dark_matter_endoscope": "not modeled",
            "interpretation": "event labels and residuals are timing diagnostics, not proof that a photon or vehicle follows a continuous physical route",
        },
        "control_event_utc": control_utc.isoformat() if control_utc is not None else None,
        "control_event_jd_tdb": str(args.control_jd_tdb) if jd_tdb_mode else None,
        "control_event_target_frame_coordinate_label": event_epoch_label(
            chart_control_epoch, jd_tdb_mode, jd_anchor_tdb
        ),
        "nominal_witness_event_utc": witness_utc.isoformat() if witness_utc is not None else None,
        "nominal_witness_event_jd_tdb": str(args.witness_jd_tdb) if jd_tdb_mode else None,
        "target_emission_event_utc": event_epoch_label(emitter_epoch, False) if not jd_tdb_mode else None,
        "target_emission_event_jd_tdb": (
            f"{args.witness_jd_tdb-Decimal(str(light_time_s))/Decimal(str(SECONDS_PER_DAY)):.15f}"
            if jd_tdb_mode else None
        ),
        "predicted_witness_reception_event_utc": (
            (witness_utc + timedelta(seconds=float(endpoint_residual_decimal_s))).isoformat()
            if witness_utc is not None else None
        ),
        "predicted_witness_reception_event_jd_tdb": (
            f"{args.witness_jd_tdb+endpoint_residual_decimal_s/Decimal(str(SECONDS_PER_DAY)):.15f}"
            if jd_tdb_mode else None
        ),
        "witness_reception_timing_residual_seconds": float(endpoint_residual_decimal_s),
        "witness_optical_prediction": witness_optics,
        "witness_baseline_parallax_screen": witness_baseline,
        "mouth_history_start_reference_mouth_clock_label": event_epoch_label(
            profile_start_epoch, jd_tdb_mode, jd_anchor_tdb
        ),
        "target_mouth_exit_target_frame_coordinate_label": event_epoch_label(
            target_exit_epoch, jd_tdb_mode, jd_anchor_tdb
        ),
        "event_label_convention": (
            "In --earth-worldline mode, historical labels are target-endpoint-rest-frame coordinate labels anchored to the target emission UTC label; the distant control event is Lorentz-synchronized, not assigned its raw UTC label. They are not independent UTC predictions."
            if endpoint_model is not None else
            "Julian Date TDB coordinate arithmetic; no conversion to UTC/POSIX" if jd_tdb_mode else
            "UTC/POSIX labels; leap seconds omitted"
        ),
        "wormhole_formation_constraint": formation_constraint,
        "flat_model_target_exit_vs_emitter_epoch_residual_seconds": float(endpoint_residual_decimal_s),
        "legacy_absolute_epoch_subtraction_residual_seconds": legacy_absolute_target_exit_epoch - emitter_epoch,
        "required_offset_float_resolution_seconds": math.ulp(lag_years) * JULIAN_YEAR_S,
        "throat_transit_below_required_offset_float_resolution": (
            args.throat_seconds < math.ulp(lag_years) * JULIAN_YEAR_S
        ),
        "elapsed_time_convention": (
            "TDB coordinate interval computed from supplied Julian dates; throat-clock model remains flat-space kinematics"
            if jd_tdb_mode else
            "POSIX seconds derived from UTC labels; leap seconds are omitted; calendar consistency only, not TAI/TDB propagation"
        ),
        "return_signal_mouth_intercept_target_frame_coordinate_label": (
            event_epoch_label(return_intercept_epoch, jd_tdb_mode, jd_anchor_tdb)
            if return_intercept_epoch is not None else None
        ),
        "assumed_emitter_to_witness_range_km": args.range_km,
        "coordinate_gap_control_to_emission_seconds": coordinate_epoch_gap_s,
        "coordinate_gap_frame": (
            "target endpoint instantaneous rest frame; Lorentz-transformed event interval"
            if endpoint_model is not None else "input UTC/POSIX coordinate frame"
        ),
        "reference_worldline_velocity_beta_icrf": list(reference_velocity_beta_icrf),
        "assumed_initial_and_final_mouth_gap_m": args.mouth_gap_m,
        "assumed_peak_transverse_mouth_excursion_light_years": args.transverse_excursion_ly,
        "endpoint_anchor": endpoint_model or {
            "model": "user-prescribed endpoint displacement" if args.endpoint_displacement_ly is not None else "zero endpoint displacement",
            "endpoint_displacement_light_years": endpoint_distance_ly,
        },
        "earth_clearance_screen": endpoint_clearance,
        "earth_endpoint_frame_match": earth_frame_match,
        "ordinary_light_flight_time_seconds": light_time_s,
        "assumed_throat_transit_seconds": args.throat_seconds,
        "required_mouth_clock_offset_years": lag_years,
        "required_mouth_clock_offset_definition": "proper time accumulated by comoving reference mouth A minus proper time accumulated by moving mouth B; finite throat crossing allowance is added in A-mouth clock time",
        "mouth_history_frame": {
            "model": "local inertial frame comoving with target endpoint/reference mouth A",
            "reference_mouth_at_rest": True,
            "earth_endpoint_chord_use": "for --earth-worldline, endpoint event separation and terminal velocity are Lorentz-transformed to the target endpoint rest frame and imposed as mouth boundary conditions",
            "worldline_representation": "planar route chart spans transformed endpoint displacement and terminal endpoint velocity; site rotation enters endpoint states when Horizons geodetic sites are supplied, but continuous Earth/site motion and full 3D clearance are not represented",
            "lorentz_boost_applied_to_worldline_samples": False,
        },
        "crew_viewpoint_map": view_map,
        "raw_video_payload_rate_check": raw_payload_rate,
        "unit_slope_return_payload_timing": return_payload_timing,
        "preliminary_chronology_closure": closure,
        "mission_viability": mission_viability,
        "mouth_history_kinematics": result,
        "interpretation": (
            "The result is a conditional prescribed-mouth worldline and event-timing calculation, with an optional flat local target-emitter screen. "
            "It is not a ray-traced A.R.G.O.-beacon route, a reconstructed Phoenix Lights trajectory, or a material A.R.G.O. arrival."
        ),
        "limits": [
            "NUFORC 8345 date/time is a retrospective single-witness report; 8:15 p.m. March 13 is approximate.",
            "The 10 km range is an illustrative input, not a measured sighting distance.",
            "Flat exterior and prescribed local solar Galactic acceleration; the --earth-worldline option anchors Earth geocenter but not the topocentric site, witness, or a full Galactic orbit.",
            "No solved wormhole throat geometry, stress-energy, optical source, or collision analysis.",
            "The prescribed mouth history assumes a synchronized traversable pair exists by its reference-mouth clock label; the target exit must lie on the anchor mouth's post-formation worldtube. No formation mechanism or historical footprint is modeled.",
            "The moving-mouth history only creates a clock offset; its equal-clock transfer map does not create the requested fast viewpoint scan.",
            "The null-return margin is a flat-space causal screen. A separate quintic timelike return candidate is reported, but the throat map, entry approach, Earth placement, hazard clearance, attitude, and field-state matching are not integrated into one physical CTC.",
            "UTC dates are differenced as POSIX timestamps, so leap seconds are omitted; high-precision event matching requires explicit UTC-to-TAI/TT/TDB conversions.",
            "The target-side mouth is placed at the Earth geocenter plus the user-supplied event offset; the scalar emitter range does not supply emitter/witness coordinates or a direction.",
            "With --earth-worldline and default zero site offsets, the target and control mouths are placed at Earth geocenters and definitively intersect Earth; these defaults are endpoint-scale diagnostics, not a viable material-hull mission. Supply site/emitter ICRF offsets for endpoint placement, then separately solve Earth orientation and continuous world-tube clearance.",
        ],
    }
    if args.csv:
        output["sampled_worldline_csv"] = str(args.csv)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
