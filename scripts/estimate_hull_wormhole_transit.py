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
from decimal import Decimal, localcontext

from estimate_smooth_wormhole_clock_offset import clock_lag_years, estimate

C = 299_792_458.0
G = 6.67430e-11
HBAR = 1.054571817e-34
JULIAN_YEAR_S = 365.25 * 86400.0
JULIAN_YEAR_D = Decimal("31557600")
C_D = Decimal("299792458")
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


def static_ellis_flat_mouth_junction(
    throat_radius_m: float, mouth_radius_m: float
) -> dict[str, float | str]:
    """Israel shell required to join a truncated static Ellis interior to flat space.

    A spherical boundary at areal radius R>r0 cuts the Ellis metric at
    |ell|=sqrt(R^2-r0^2). Each of the two cut mouths is joined to a separate
    static Minkowski exterior. This is a static thin-shell baseline, not the
    accelerated-mouth geometry used by the clock-offset toy.
    """
    a = throat_radius_m
    radius = mouth_radius_m
    if radius <= a:
        raise ValueError("mouth areal radius must exceed the Ellis throat radius")
    ell_m = math.sqrt(radius**2 - a**2)
    # Use a^2/[R^2(R+ell)] to avoid cancellation in (R-ell)/R^2.
    angular_curvature_jump = a**2 / (radius**2 * (radius + ell_m))
    surface_energy_density = -(C**4 / (4.0 * math.pi * G)) * angular_curvature_jump
    surface_pressure = (C**4 / (8.0 * math.pi * G)) * angular_curvature_jump
    shell_energy_one = 4.0 * math.pi * radius**2 * surface_energy_density
    shell_energy_two = 2.0 * shell_energy_one
    bulk_energy = -(C**4 * a / G) * math.atan(ell_m / a)
    return {
        "model": "static truncated Ellis interior joined at two spherical mouths to separate Minkowski exteriors",
        "mouth_areal_radius_m": radius,
        "ellis_proper_radial_cut_coordinate_m": ell_m,
        "induced_metric_match": "continuous; static proper time and areal sphere radius agree at each shell",
        "interior_extrinsic_curvature_angular_per_m": ell_m / radius**2,
        "flat_exterior_extrinsic_curvature_angular_per_m": 1.0 / radius,
        "jump_angular_extrinsic_curvature_per_m": angular_curvature_jump,
        "surface_energy_density_per_mouth_j_m2": surface_energy_density,
        "surface_tangential_pressure_per_mouth_j_m2": surface_pressure,
        "surface_sigma_plus_pressure_nec_j_m2": surface_energy_density + surface_pressure,
        "shell_energy_per_mouth_j": shell_energy_one,
        "shell_energy_both_mouths_j": shell_energy_two,
        "truncated_ellis_bulk_energy_both_sides_j": bulk_energy,
        "bulk_plus_shell_static_slice_energy_j": bulk_energy + shell_energy_two,
        "interpretation": "Israel stress required by the static jump; no shell material action, accelerated-shell dynamics, or gravitational ADM-energy calculation is supplied",
    }


def ellis_junction_transverse_impulse_screen(
    throat_radius_m: float,
    mouth_radius_m: float,
    hull_width_m: float,
    local_speed_m_s: float,
) -> dict[str, float | str | bool | None]:
    """Linearized transverse velocity kick at one static thin-shell junction.

    In the thin-shell limit, the jump in transverse extrinsic curvature gives
    a finite relative-velocity impulse for a radially moving extended object.
    This reports the per-junction screen only; it does not resolve the finite
    hull, shell thickness, material response, or transport of transverse axes
    between the two mouths.
    """
    a = throat_radius_m
    radius = mouth_radius_m
    if radius <= a:
        raise ValueError("mouth areal radius must exceed throat radius")
    if hull_width_m <= 0.0 or not 0.0 <= local_speed_m_s < C:
        raise ValueError("hull width must be positive and local speed must be subluminal")
    ell_m = math.sqrt(radius**2 - a**2)
    curvature_jump = 1.0 / radius - ell_m / radius**2
    beta = local_speed_m_s / C
    gamma = 1.0 / math.sqrt(1.0 - beta**2)
    impulse_gradient = gamma * local_speed_m_s * curvature_jump
    return {
        "model": "linearized transverse thin-shell impulse for a radial traveler; SI form of Delta_v_perp/Delta_x_perp = gamma*v*[K_perp_perp]",
        "junction_curvature_jump_per_m": curvature_jump,
        "local_speed_m_s": local_speed_m_s,
        "lorentz_factor": gamma,
        "relative_velocity_impulse_per_unit_transverse_separation_s_inv": impulse_gradient,
        "formal_relative_velocity_impulse_across_visible_width_m_s": impulse_gradient * hull_width_m,
        "visible_width_to_mouth_radius_ratio": hull_width_m / radius,
        "small_separation_approximation_controlled_below_0_1_ratio": hull_width_m / radius < 0.1,
        "peak_acceleration": "undefined in the zero-thickness shell idealization; a finite-thickness layer is required",
        "combined_entry_exit_impulse_m_s": None,
        "combined_impulse_limit": "requires the transverse tetrad identification and finite-body response across both mouths",
        "interpretation": (
            "per-mouth first-order impulse screen with hull width below 0.1 of mouth radius; this is not a finite-body stress or safety result"
            if hull_width_m / radius < 0.1 else
            "per-mouth formal linearized kick; hull width is not small compared with mouth radius, so this extrapolation is uncontrolled"
        ),
    }


def ellis_two_shell_jacobi_screen(
    throat_radius_m: float,
    throat_length_m: float,
    transit_seconds: float,
    hull_width_m: float,
) -> dict[str, float | str | bool]:
    """Propagate a small transverse separation through both static junctions.

    Neighboring points are initially comoving in the flat B-side exterior.
    The entry-shell impulse sets the interior Jacobi derivative; the smooth
    Ellis region is propagated analytically; then the exit-shell impulse is
    applied. This is a linearized geodesic-deviation screen, not a finite-body
    or structural model.
    """
    a = throat_radius_m
    length = throat_length_m
    width = hull_width_m
    if min(a, length, transit_seconds, width) <= 0.0:
        raise ValueError("throat dimensions, transit time, and hull width must be positive")

    x = 0.5 * length
    radius = math.hypot(a, x)
    theta = math.atan(x / a)
    q = length / (C * transit_seconds)
    gamma = math.sqrt(1.0 + q**2)
    speed = C * q / gamma
    curvature_jump = 1.0 / radius - x / radius**2
    entry_slope_after_shell_per_ell = curvature_jump * width

    # Two exact Jacobi basis functions for the smooth ultrastatic Ellis region.
    def basis(ell: float) -> tuple[float, float, float, float]:
        areal = math.sqrt(ell * ell + a * a)
        angle = math.atan(ell / a)
        f = areal
        g = areal / a * angle
        fp = ell / areal
        gp = ell * angle / (a * areal) + 1.0 / areal
        return f, g, fp, gp

    f_in, g_in, fp_in, gp_in = basis(-x)
    f_out, g_out, fp_out, gp_out = basis(x)
    # The Wronskian f*g' - f'*g is one for this normalization.
    coefficient_f = width * gp_in - entry_slope_after_shell_per_ell * g_in
    coefficient_g = f_in * entry_slope_after_shell_per_ell - fp_in * width
    width_center = coefficient_f * a
    width_before_exit_shell = coefficient_f * f_out + coefficient_g * g_out
    slope_before_exit_shell_per_ell = (
        coefficient_f * fp_out + coefficient_g * gp_out
    )
    relative_speed_before_exit_shell = gamma * speed * slope_before_exit_shell_per_ell
    exit_shell_kick = gamma * speed * curvature_jump * width_before_exit_shell
    relative_speed_after_exit_shell = relative_speed_before_exit_shell + exit_shell_kick
    return {
        "model": "linearized transverse Jacobi field; flat-exterior comoving entry, entry thin-shell kick, exact smooth Ellis propagation, exit thin-shell kick",
        "transverse_frame_assumption": "same angular basis at both static cuts, with no twist across the Ellis throat; this does not specify the accelerated global mouth tetrads",
        "mouth_areal_radius_m": radius,
        "curvature_jump_each_shell_per_m": curvature_jump,
        "initial_exterior_relative_transverse_speed_m_s": 0.0,
        "entry_shell_kick_m_s_across_width": gamma * speed * curvature_jump * width,
        "interior_jacobi_derivative_after_entry_per_ell": entry_slope_after_shell_per_ell,
        "formal_transverse_width_at_throat_center_m": width_center,
        "formal_transverse_width_before_exit_shell_m": width_before_exit_shell,
        "formal_exit_width_to_mouth_diameter_ratio": width_before_exit_shell / (2.0 * radius),
        "formal_relative_transverse_speed_before_exit_shell_m_s": relative_speed_before_exit_shell,
        "exit_shell_kick_m_s_across_width": exit_shell_kick,
        "formal_relative_transverse_speed_after_exit_shell_m_s": relative_speed_after_exit_shell,
        "entry_width_to_mouth_radius_ratio": width / radius,
        "small_separation_approximation_controlled_below_0_1_ratio": width / radius < 0.1,
        "interpretation": (
            "conditional first-order propagation only; hull width is below 0.1 of mouth radius, so the linearized size screen is controlled, but this is not a finite-body stress or safety result"
            if width / radius < 0.1 else
            "conditional first-order propagation only; hull width is not small compared with mouth radius, so hull-scale values are uncontrolled and are not a pass/fail prediction"
        ),
    }


def ellis_radial_tidal_screen(
    throat_radius_m: float,
    throat_length_m: float,
    transit_seconds: float,
    hull_width_m: float,
) -> dict[str, float | str | bool]:
    """Leading-order transverse geodesic-deviation scale in a static Ellis throat.

    This is a test-geodesic curvature screen for a radial, constant-speed
    passage. It is not a finite-body structural calculation. In particular,
    the linearized estimate is uncontrolled when hull_width/r0 is not small.
    """
    a = throat_radius_m
    length = throat_length_m
    q = length / (C * transit_seconds)  # gamma * beta
    gamma = math.sqrt(1.0 + q**2)
    speed = C * q / gamma

    # In the static orthonormal frame R_ltheta ltheta = -a^2/(l^2+a^2)^2
    # and R_thetathetat = 0. A radial boost gives the traveler-frame
    # transverse tidal-gradient magnitude gamma^2 v^2 a^2/(l^2+a^2)^2.
    max_gradient = gamma**2 * speed**2 / a**2
    max_differential_acceleration = max_gradient * hull_width_m

    # Integrate that linearized relative acceleration over traveler proper
    # time d_tau = d_l/(gamma*v), from -L/2 to +L/2.
    x = 0.5 * length
    curvature_integral = (
        x / (a**2 * (x**2 + a**2)) + math.atan(x / a) / a**3
    )
    relative_velocity_per_m = gamma * speed * a**2 * curvature_integral
    linearized_relative_velocity = relative_velocity_per_m * hull_width_m
    entry_radius = math.sqrt(x**2 + a**2)
    geodesic_width_at_center = hull_width_m * a / entry_radius
    fractional_width_compression = 1.0 - a / entry_radius
    max_relative_transverse_speed = (
        hull_width_m * gamma * speed * x / entry_radius**2
    )
    theta = math.atan(x / a)
    jacobi_entry_factor = 1.0 + x * theta / a
    comoving_jacobi_center_ratio = a / entry_radius * jacobi_entry_factor
    comoving_jacobi_exit_ratio = 1.0 + 2.0 * x * theta / a
    comoving_jacobi_exit_slope = (
        2.0 * hull_width_m * x * jacobi_entry_factor / entry_radius**2
    )
    size_parameter = hull_width_m / a
    return {
        "model": "smooth static ultrastatic Ellis interior only; linearized radial tidal impulse and initially comoving Jacobi field compared with exact fixed-angle radial test-geodesic congruence; thin-shell junction impulses excluded",
        "throat_center_transverse_tidal_gradient_s2": max_gradient,
        "formal_differential_acceleration_across_hull_width_m_s2": max_differential_acceleration,
        "integrated_relative_velocity_per_unit_separation_s1": relative_velocity_per_m,
        "formal_integrated_relative_velocity_across_hull_width_m_s": linearized_relative_velocity,
        "radial_geodesic_congruence_width_at_throat_center_m": geodesic_width_at_center,
        "radial_geodesic_congruence_fractional_width_compression": fractional_width_compression,
        "radial_geodesic_congruence_max_relative_transverse_speed_m_s": max_relative_transverse_speed,
        "initially_comoving_linearized_jacobi_width_at_throat_center_m": hull_width_m * comoving_jacobi_center_ratio,
        "initially_comoving_linearized_jacobi_width_at_exit_m": hull_width_m * comoving_jacobi_exit_ratio,
        "initially_comoving_linearized_jacobi_exit_width_ratio": comoving_jacobi_exit_ratio,
        "initially_comoving_linearized_jacobi_max_relative_speed_at_exit_m_s": gamma * speed * comoving_jacobi_exit_slope,
        "hull_width_to_curvature_radius_ratio": size_parameter,
        "small_body_limit_controlled": size_parameter < 0.1,
        "interpretation": (
            "the fixed-angle congruence is an exact family of radial test geodesics but begins with relative transverse velocity; "
            "the initially comoving Jacobi field is a size-controlled linearized estimate, not a finite-body stress or safety result"
            if size_parameter < 0.1 else
            "the fixed-angle congruence is an exact family of radial test geodesics but begins with relative transverse velocity; "
            "the initially comoving Jacobi field is only linearized and uncontrolled because hull width is not small compared with the throat curvature radius"
        ),
    }


def ford_roman_qi_diagnostic(
    throat_radius_m: float, curvature_time_fraction: float = 0.01
) -> dict[str, float | str]:
    """Local-flat Lorentzian QI scale for an ordinary free scalar field.

    This is a diagnostic, not a universal bound on all possible sources. The
    Ellis drainhole is sourced by a wrong-sign classical scalar, which is not
    the unitary quantized scalar covered by the Ford-Roman inequality.
    """
    if not 0.0 < curvature_time_fraction < 1.0:
        raise ValueError("curvature_time_fraction must be between 0 and 1")
    curvature_time_s = throat_radius_m / C
    sampling_time_s = curvature_time_fraction * curvature_time_s
    qi_magnitude = 3.0 * HBAR / (
        32.0 * math.pi**2 * C**3 * sampling_time_s**4
    )
    ellis_density_magnitude = C**4 / (8.0 * math.pi * G * throat_radius_m**2)
    return {
        "scope": "local-flat Lorentzian quantum inequality for a free, massless, minimally coupled quantized scalar; not a universal source bound",
        "sampling_function": "Lorentzian",
        "sampling_fraction_of_throat_curvature_time": curvature_time_fraction,
        "throat_curvature_time_s": curvature_time_s,
        "sampling_time_s": sampling_time_s,
        "negative_energy_density_lower_bound_j_m3": -qi_magnitude,
        "ellis_required_density_magnitude_j_m3": ellis_density_magnitude,
        "ellis_to_qi_bound_magnitude_ratio": ellis_density_magnitude / qi_magnitude,
    }


def flat_space_null_intercept(
    emitter_position_km: tuple[float, float, float],
    witness_position_at_emission_km: tuple[float, float, float],
    witness_velocity_km_s: tuple[float, float, float],
) -> dict[str, object]:
    """Intersect a future null ray with a constant-velocity inertial observer.

    Positions and velocity share one Cartesian frame at emission. This is a
    flat-space check after the hull exit, not a propagation through the throat.
    """
    emitter = tuple(float(v) for v in emitter_position_km)
    witness = tuple(float(v) for v in witness_position_at_emission_km)
    velocity = tuple(float(v) for v in witness_velocity_km_s)
    if not (len(emitter) == len(witness) == len(velocity) == 3):
        raise ValueError("emitter position, witness position, and velocity must be 3-vectors")
    c_km_s = C / 1000.0
    speed2 = sum(v*v for v in velocity)
    if speed2 >= c_km_s*c_km_s:
        raise ValueError("witness speed must be less than c")
    separation = tuple(witness[i] - emitter[i] for i in range(3))
    r2 = sum(v*v for v in separation)
    rv = sum(separation[i] * velocity[i] for i in range(3))
    if r2 == 0.0:
        return {
            "status": "coincident_emission_and_witness_event",
            "flight_time_seconds": 0.0,
            "photon_path_length_km": 0.0,
            "initial_separation_km": 0.0,
            "photon_direction_unit_vector": None,
            "witness_reception_position_km": list(witness),
        }
    a = c_km_s*c_km_s - speed2
    flight_s = (rv + math.sqrt(rv*rv + a*r2)) / a
    reception = tuple(witness[i] + velocity[i] * flight_s for i in range(3))
    ray = tuple(reception[i] - emitter[i] for i in range(3))
    path_km = math.sqrt(sum(v*v for v in ray))
    return {
        "status": "flat_space_null_intercept_computed",
        "flight_time_seconds": flight_s,
        "photon_path_length_km": path_km,
        "initial_separation_km": math.sqrt(r2),
        "photon_direction_unit_vector": [v / path_km for v in ray],
        "witness_reception_position_km": list(reception),
    }


def flat_space_apparent_track(
    emission_samples: list[dict[str, object]],
    witness_position_at_final_emission_km: tuple[float, float, float],
    witness_velocity_km_s: tuple[float, float, float],
    emission_beam_axis_unit_vector_in_source_rest_frame: tuple[float, float, float] | None = None,
    emission_cone_half_angle_deg: float | None = None,
    emission_recoil_integrated_in_segment: bool = False,
) -> dict[str, object]:
    """Map sampled emitter events to a moving inertial witness's apparent sky.

    Each photon is propagated in flat spacetime to the same constant-velocity
    observer worldline. Apparent directions are transformed into the
    observer's instantaneous rest frame (special-relativistic aberration).
    Radiometry and curved-spacetime propagation are deliberately excluded.
    """
    if not emission_samples:
        raise ValueError("at least one emitter worldline sample is required")
    witness_final = tuple(float(v) for v in witness_position_at_final_emission_km)
    witness_velocity = tuple(float(v) for v in witness_velocity_km_s)
    if len(witness_final) != 3 or len(witness_velocity) != 3:
        raise ValueError("witness position and velocity must be 3-vectors")
    beam_axis = None
    if emission_beam_axis_unit_vector_in_source_rest_frame is not None:
        beam_axis = tuple(float(v) for v in emission_beam_axis_unit_vector_in_source_rest_frame)
        beam_norm = math.sqrt(sum(v*v for v in beam_axis)) if len(beam_axis) == 3 else 0.0
        if not math.isfinite(beam_norm) or beam_norm == 0.0:
            raise ValueError("emission beam axis must be a nonzero 3-vector")
        if emission_cone_half_angle_deg is None or not 0.0 <= emission_cone_half_angle_deg <= 180.0:
            raise ValueError("a beam axis requires a cone half-angle between 0 and 180 degrees")
        beam_axis = tuple(v/beam_norm for v in beam_axis)
    c_km_s = C / 1000.0
    speed2 = sum(v*v for v in witness_velocity)
    if speed2 >= c_km_s*c_km_s:
        raise ValueError("witness speed must be less than c")
    final_time = float(emission_samples[-1]["coordinate_time_from_throat_exit_s"])
    beta = tuple(v/c_km_s for v in witness_velocity)
    beta2 = sum(v*v for v in beta)
    gamma = 1.0/math.sqrt(1.0-beta2)
    observations = []
    for sample in emission_samples:
        emission_time = float(sample["coordinate_time_from_throat_exit_s"])
        emitter = tuple(float(v) for v in sample["position_km"])
        emitter_velocity = tuple(
            float(v) for v in sample.get("velocity_km_s", (0.0, 0.0, 0.0))
        )
        if len(emitter_velocity) != 3:
            raise ValueError("emitter velocity samples must be 3-vectors")
        emitter_beta = tuple(v/c_km_s for v in emitter_velocity)
        emitter_beta2 = sum(v*v for v in emitter_beta)
        if emitter_beta2 >= 1.0:
            raise ValueError("emitter speed must be less than c")
        emitter_gamma = 1.0/math.sqrt(1.0-emitter_beta2)
        witness_at_emission = tuple(
            witness_final[i]-witness_velocity[i]*(final_time-emission_time)
            for i in range(3)
        )
        ray = flat_space_null_intercept(
            emitter, witness_at_emission, witness_velocity
        )
        if ray["photon_direction_unit_vector"] is None:
            apparent_direction = None
            frequency_ratio = None
            source_frame_photon_direction = None
        else:
            photon_n = tuple(float(v) for v in ray["photon_direction_unit_vector"])
            beta_dot_n = sum(beta[i]*photon_n[i] for i in range(3))
            emitter_beta_dot_n = sum(
                emitter_beta[i]*photon_n[i] for i in range(3)
            )
            frequency_ratio = (
                gamma*(1.0-beta_dot_n)
                / (emitter_gamma*(1.0-emitter_beta_dot_n))
            )
            if beta2 == 0.0:
                photon_in_observer_frame = photon_n
            else:
                factor = ((gamma-1.0)*beta_dot_n/beta2)-gamma
                photon_in_observer_frame = tuple(
                    photon_n[i]+factor*beta[i] for i in range(3)
                )
            source_direction = tuple(-v for v in photon_in_observer_frame)
            direction_norm = math.sqrt(sum(v*v for v in source_direction))
            apparent_direction = [v/direction_norm for v in source_direction]
            if emitter_beta2 == 0.0:
                source_frame_photon_direction = photon_n
            else:
                source_beta_dot_n = sum(emitter_beta[i]*photon_n[i] for i in range(3))
                source_factor = (emitter_gamma-1.0)*source_beta_dot_n/emitter_beta2-emitter_gamma
                source_frame_photon_direction = tuple(
                    (photon_n[i]+source_factor*emitter_beta[i])
                    /(emitter_gamma*(1.0-source_beta_dot_n))
                    for i in range(3)
                )
        beam_axis_dot = (
            sum(source_frame_photon_direction[i]*beam_axis[i] for i in range(3))
            if source_frame_photon_direction is not None and beam_axis is not None else None
        )
        observations.append({
            "emission_coordinate_time_from_throat_exit_s": emission_time,
            "reception_coordinate_time_from_throat_exit_s":
                emission_time+float(ray["flight_time_seconds"]),
            "reception_proper_time_s":
                (emission_time+float(ray["flight_time_seconds"]))/gamma,
            "photon_flight_time_s": float(ray["flight_time_seconds"]),
            "photon_path_length_km": float(ray["photon_path_length_km"]),
            "emitter_velocity_km_s": list(emitter_velocity),
            "photon_direction_unit_vector_in_coordinate_frame":
                ray["photon_direction_unit_vector"],
            "photon_direction_unit_vector_in_emitter_rest_frame": (
                list(source_frame_photon_direction)
                if source_frame_photon_direction is not None else None
            ),
            "emission_beam_axis_dot_photon_direction": beam_axis_dot,
            "inside_emission_cone": (
                beam_axis_dot >= math.cos(math.radians(emission_cone_half_angle_deg))-1e-12
                if beam_axis_dot is not None and emission_cone_half_angle_deg is not None else None
            ),
            "frequency_ratio_observed_to_emitted": frequency_ratio,
            "observed_wavelength_nm_for_550nm_emission": (
                550.0/frequency_ratio if frequency_ratio is not None else None
            ),
            "apparent_source_direction_unit_vector_in_witness_rest_frame":
                apparent_direction,
        })
    track_observations = (
        [item for item in observations if item["inside_emission_cone"]]
        if beam_axis is not None else observations
    )
    angular_steps = []
    for first, second in zip(track_observations, track_observations[1:]):
        a = first["apparent_source_direction_unit_vector_in_witness_rest_frame"]
        b = second["apparent_source_direction_unit_vector_in_witness_rest_frame"]
        if a is None or b is None:
            continue
        dot = max(-1.0, min(1.0, sum(a[i]*b[i] for i in range(3))))
        cross = (
            a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0],
        )
        angle = math.atan2(math.sqrt(sum(v*v for v in cross)), dot)
        elapsed = (
            float(second["reception_proper_time_s"])
            - float(first["reception_proper_time_s"])
        )
        if elapsed > 0.0:
            angular_steps.append((angle, elapsed))
    total_angle = sum(angle for angle, _ in angular_steps)
    maximum_rate = max(
        (angle/elapsed for angle, elapsed in angular_steps), default=0.0
    )
    return {
        "model": "flat-spacetime retarded null rays to a constant-velocity inertial observer",
        "observer_frame_correction": "apparent source directions include special-relativistic aberration and frequencies use emitter/witness four-velocity Doppler shift",
        "frequency_ratio_interpretation": "the photon energy ratio is the same frame-to-frame measurement as the frequency ratio; it is not energy created in flight",
        "observer_proper_time_conversion": "d tau_witness = dt/gamma for this inertial observer",
        "sample_count": len(observations),
        "beam_illuminated_sample_count": len(track_observations),
        "angular_track_metric_scope": (
            "only consecutive samples whose retarded rays fall inside the supplied emission cone"
            if beam_axis is not None else
            "all sampled retarded rays; no emission-cone restriction supplied"
        ),
        "total_sampled_angular_path_rad": total_angle,
        "maximum_adjacent_sample_angular_rate_rad_s": maximum_rate,
        "samples": observations,
        "unmodeled": [
            "curved-spacetime photon propagation and gravitational lensing",
            "Earth rotation/orbit and witness acceleration",
            "finite hull surface, attitude, radiance, spectrum, and emission mechanism",
            *([] if emission_recoil_integrated_in_segment else [
                "local emitter recoil and four-momentum exchange with hull, chronal field, and throat",
            ]),
            "atmospheric extinction, background, detector response, and visual perception",
            "sampling/interpolation error in the candidate emitter worldline",
        ],
    }


def local_conical_emission_recoil(
    initial_rest_mass_kg: float,
    emitted_energy_j: float,
    cone_half_angle_deg: float,
    pulse_duration_proper_s: float | None = None,
    pulse_envelope: str = "sin2",
) -> dict[str, object]:
    """Compute local recoil and a finite-duration photon-rocket segment.

    The source plus its local energy store starts at rest in its own frame.
    Photon energy is measured in that frame and is uniform per solid angle
    within a cone. The instantaneous result is a four-momentum comparator;
    the finite result is a local flat-space segment, not a throat-field model.
    """
    if not all(math.isfinite(v) for v in (
        initial_rest_mass_kg, emitted_energy_j, cone_half_angle_deg
    )) or initial_rest_mass_kg <= 0.0 or emitted_energy_j < 0.0:
        raise ValueError("initial rest mass must be positive and emitted energy nonnegative")
    if not 0.0 <= cone_half_angle_deg <= 180.0:
        raise ValueError("cone half-angle must lie between 0 and 180 degrees")
    if pulse_duration_proper_s is not None and (
        not math.isfinite(pulse_duration_proper_s) or pulse_duration_proper_s <= 0.0
    ):
        raise ValueError("pulse proper duration must be positive")
    if pulse_envelope not in {"sin2", "constant"}:
        raise ValueError("pulse envelope must be 'sin2' or 'constant'")
    initial_rest_energy = initial_rest_mass_kg*C**2
    momentum_fraction = 0.5*(1.0+math.cos(math.radians(cone_half_angle_deg)))
    emitted_energy_fraction = emitted_energy_j/initial_rest_energy
    maximum_energy_fraction = 1.0/(1.0+momentum_fraction)
    remaining_energy = initial_rest_energy-emitted_energy_j
    photon_momentum_c = momentum_fraction*emitted_energy_j
    remnant_rest_energy_ratio_sq = (
        (1.0-emitted_energy_fraction)**2
        -(momentum_fraction*emitted_energy_fraction)**2
    )
    if remaining_energy <= 0.0 or emitted_energy_fraction >= maximum_energy_fraction:
        return {
            "model": "single local photon pulse; exact special-relativistic four-momentum balance",
            "status": "no_timelike_remnant_for_supplied_pulse",
            "initial_rest_mass_kg": initial_rest_mass_kg,
            "emitted_energy_in_source_rest_frame_j": emitted_energy_j,
            "beam_half_angle_deg": cone_half_angle_deg,
            "uniform_cone_momentum_fraction": momentum_fraction,
            "maximum_emitted_energy_fraction_of_initial_rest_energy": maximum_energy_fraction,
            "interpretation": "the assumed isolated source cannot emit this pulse and leave a massive timelike remnant",
            "trajectory_coupling": "no post-emission hull trajectory is integrated",
            "continuous_emission_segment": None,
        }
    final_rest_energy_ratio = math.sqrt(remnant_rest_energy_ratio_sq)
    final_rest_energy = initial_rest_energy*final_rest_energy_ratio
    # Rationalized form retains the tiny rest-mass defect when E/(Mc^2)
    # is below floating-point resolution in 1 - E/(Mc^2).
    rest_mass_loss_fraction = (
        2.0*emitted_energy_fraction
        -(1.0-momentum_fraction**2)*emitted_energy_fraction**2
    )/(1.0+final_rest_energy_ratio)
    recoil_beta = photon_momentum_c/remaining_energy
    recoil_gamma = remaining_energy/final_rest_energy
    result = {
        "model": "instantaneous-pulse four-momentum comparison with optional finite-duration photon-rocket integration",
        "status": "timelike_remnant",
        "initial_rest_mass_kg": initial_rest_mass_kg,
        "initial_rest_energy_j": initial_rest_energy,
        "emitted_energy_in_source_rest_frame_j": emitted_energy_j,
        "energy_input_interpretation": (
            "total photon energy in the initial source rest frame for the instantaneous-pulse comparison; finite-duration mode instead treats this value as integrated energy in each instantaneous emitter rest frame"
            if pulse_duration_proper_s is not None else
            "total photon energy in the initial source rest frame for the instantaneous-pulse calculation"
        ),
        "emitted_energy_fraction_of_initial_rest_energy": emitted_energy_fraction,
        "beam_half_angle_deg": cone_half_angle_deg,
        "uniform_cone_momentum_fraction": momentum_fraction,
        "photon_net_momentum_kg_m_s": momentum_fraction*emitted_energy_j/C,
        "remnant_rest_mass_kg": initial_rest_mass_kg*(1.0-rest_mass_loss_fraction),
        "remnant_rest_mass_loss_kg": initial_rest_mass_kg*rest_mass_loss_fraction,
        "remnant_recoil_speed_m_s": recoil_beta*C,
        "remnant_recoil_speed_fraction_of_c": recoil_beta,
        "remnant_lorentz_factor_in_initial_source_frame": recoil_gamma,
        "recoil_direction_in_source_frame": "opposite the emitted cone axis",
        "recoil_axis_direction": "not specified; magnitude is independent of cone orientation",
        "interpretation": "assumes the radiating hull and its local energy store form one isolated material source during this pulse",
        "trajectory_coupling": "the recoil is not applied to the prescribed hull worldline or any later return path",
    }
    if pulse_duration_proper_s is None:
        result["continuous_emission_segment"] = None
        result["trajectory_coupling"] = (
            "impulse magnitude only; no finite pulse history or post-emission hull trajectory is integrated"
        )
        return result

    # The default sin^2 envelope has zero power and zero power slope at each
    # endpoint. Its cumulative emitted-energy fraction is q(u)=u-sin(2*pi*u)/(2*pi).
    # The constant profile remains as a sharp-edged comparison case.
    # The cone is fixed to the craft and there is no external force.
    # The rocket rapidity follows d(chi)/d(tau)= -f_p P/[M(tau)c], with
    # M(tau)=M0-P*tau/c^2. Integrate this smooth local-rest-frame worldline.
    duration = pulse_duration_proper_s
    average_power = emitted_energy_j/duration
    steps = 10_000
    rapidity_integrand_time = []
    rapidity_integrand_displacement = []
    photon_energy_integrand = []
    max_proper_acceleration = 0.0
    for k in range(steps+1):
        u = k/steps
        if pulse_envelope == "sin2":
            energy_fraction_by_u = u-math.sin(2.0*math.pi*u)/(2.0*math.pi)
            power_factor = 0.0 if k in (0, steps) else 2.0*math.sin(math.pi*u)**2
        else:
            energy_fraction_by_u = u
            power_factor = 1.0
        mass_fraction = 1.0-emitted_energy_fraction*energy_fraction_by_u
        rapidity = momentum_fraction*math.log1p(-emitted_energy_fraction*energy_fraction_by_u)
        gamma = math.cosh(rapidity)
        velocity_fraction = math.tanh(rapidity)
        rapidity_integrand_time.append(gamma)
        rapidity_integrand_displacement.append(math.sinh(rapidity))
        # Transform instantaneous-frame photon energy and net momentum into
        # the initial source frame before integrating the finite pulse.
        photon_energy_integrand.append(
            power_factor*gamma*(1.0+momentum_fraction*velocity_fraction)
        )
        instantaneous_mass = initial_rest_mass_kg*mass_fraction
        power = average_power*power_factor
        proper_acceleration = (
            momentum_fraction*power/(instantaneous_mass*C)
            if momentum_fraction > 0.0 else 0.0
        )
        max_proper_acceleration = max(max_proper_acceleration, proper_acceleration)

    def simpson(values: list[float]) -> float:
        h = 1.0/steps
        return h/3.0*(
            values[0]+values[-1]
            +4.0*sum(values[1:-1:2])
            +2.0*sum(values[2:-1:2])
        )

    def partial_simpson(values: list[float], end: int) -> float:
        if end == 0:
            return 0.0
        h = 1.0/steps
        return h/3.0*(
            values[0]+values[end]
            +4.0*sum(values[1:end:2])
            +2.0*sum(values[2:end:2])
        )

    coordinate_duration = duration*simpson(rapidity_integrand_time)
    displacement = C*duration*simpson(rapidity_integrand_displacement)
    initial_frame_photon_energy = emitted_energy_j*simpson(photon_energy_integrand)
    final_rapidity = momentum_fraction*math.log1p(-emitted_energy_fraction)
    final_gamma = math.cosh(final_rapidity)
    final_velocity = C*math.tanh(final_rapidity)
    sampled_local_worldline = []
    for k in range(0, steps+1, 50):
        u = k/steps
        if pulse_envelope == "sin2":
            energy_fraction_by_u = u-math.sin(2.0*math.pi*u)/(2.0*math.pi)
            power_factor = 0.0 if k in (0, steps) else 2.0*math.sin(math.pi*u)**2
        else:
            energy_fraction_by_u = u
            power_factor = 1.0
        mass_fraction = 1.0-emitted_energy_fraction*energy_fraction_by_u
        rapidity = momentum_fraction*math.log1p(-emitted_energy_fraction*energy_fraction_by_u)
        sample_acceleration = (
            momentum_fraction*average_power*power_factor
            /(initial_rest_mass_kg*mass_fraction*C)
            if momentum_fraction > 0.0 else 0.0
        )
        sampled_local_worldline.append({
            "proper_time_from_emission_start_s": u*duration,
            "coordinate_time_in_initial_source_frame_s": duration*partial_simpson(rapidity_integrand_time, k),
            "displacement_m_along_opposite_beam_axis": C*duration*partial_simpson(rapidity_integrand_displacement, k),
            "velocity_m_s_along_opposite_beam_axis": C*math.tanh(rapidity),
            "proper_acceleration_m_s2": sample_acceleration,
        })
    final_mass_loss = emitted_energy_j/C**2
    final_mass = initial_rest_mass_kg-final_mass_loss
    result["continuous_emission_segment"] = {
        "model": "one-dimensional relativistic photon rocket in the initial source rest frame",
        "status": "continuous position and tangent; local flat-space segment integrated",
        "emission_power_average_in_instantaneous_source_frame_w": average_power,
        "emission_power_peak_in_instantaneous_source_frame_w": (
            2.0*average_power if pulse_envelope == "sin2" else average_power
        ),
        "pulse_power_envelope": pulse_envelope,
        "pulse_proper_duration_s": duration,
        "coordinate_duration_in_initial_source_frame_s": coordinate_duration,
        "proper_acceleration_max_m_s2": max_proper_acceleration,
        "displacement_m_along_opposite_beam_axis": displacement,
        "final_velocity_m_s_along_opposite_beam_axis": final_velocity,
        "final_rapidity_along_opposite_beam_axis": final_rapidity,
        "final_lorentz_factor": final_gamma,
        "final_rest_mass_kg": final_mass,
        "initial_frame_total_photon_energy_j": initial_frame_photon_energy,
        "final_rest_mass_loss_kg": final_mass_loss,
        "sampled_local_worldline_for_observation_projection": sampled_local_worldline,
        "integration": "10,000-interval Simpson integration of exact variable-mass rapidity law",
        "assumptions": [
            "power follows the declared proper-time envelope; default sin-squared envelope starts and ends at zero power",
            "uniform radiated power per solid angle inside a cone fixed to the craft",
            "no external force, gravity, torque, or hull deformation during the pulse",
            "one-dimensional motion along the cone axis in the craft's initial rest frame",
        ],
        "not_connected_to": [
            "the exterior mouth tetrad or global mission coordinate frame",
            "the pre-emission post-exit Hermite route",
            "Earth/site or other collision hazards",
            "any later wormhole return path",
        ],
    }
    result["trajectory_coupling"] = (
        "finite continuous local photon-rocket segment is computed in the initial source rest frame; transform and join it only with an explicit chart event, frame velocity, and beam axis"
    )
    return result


def boost_local_emission_worldline_to_chart(
    local_samples: list[dict[str, float]],
    initial_position_km: tuple[float, float, float],
    initial_velocity_km_s: tuple[float, float, float],
    beam_axis_unit_vector_in_initial_rest_frame: tuple[float, float, float],
    coordinate_time_offset_s: float = 0.0,
) -> list[dict[str, object]]:
    """Boost a collinear local photon-rocket segment into the mission chart.

    The local axis is the canonical rotationless-boost basis at the pulse
    start. Collinear acceleration preserves this nonrotating axis through the
    pulse. This is flat-spacetime frame kinematics, not throat transport.
    """
    position = tuple(float(v) for v in initial_position_km)
    velocity = tuple(float(v) for v in initial_velocity_km_s)
    axis = tuple(float(v) for v in beam_axis_unit_vector_in_initial_rest_frame)
    if len(position) != 3 or len(velocity) != 3 or len(axis) != 3:
        raise ValueError("position, velocity, and beam axis must be 3-vectors")
    axis_norm = math.sqrt(sum(v*v for v in axis))
    if not math.isfinite(axis_norm) or axis_norm == 0.0:
        raise ValueError("beam axis must be nonzero")
    axis = tuple(v/axis_norm for v in axis)
    c_km_s = C/1000.0
    speed2 = sum(v*v for v in velocity)
    if speed2 >= c_km_s*c_km_s:
        raise ValueError("initial chart velocity must be subluminal")
    gamma = 1.0/math.sqrt(1.0-speed2/c_km_s**2)
    output = []
    for sample in local_samples:
        dt_local = float(sample["coordinate_time_in_initial_source_frame_s"])
        displacement_local_km = (
            float(sample["displacement_m_along_opposite_beam_axis"])/1000.0
        )
        local_position = tuple(displacement_local_km*v for v in axis)
        v_dot_r = sum(velocity[i]*local_position[i] for i in range(3))
        dt_chart = gamma*(dt_local+v_dot_r/c_km_s**2)
        transformed_position = tuple(
            position[i]+local_position[i]
            +(gamma-1.0)*v_dot_r*velocity[i]/speed2 if speed2 > 0.0
            else position[i]+local_position[i]
            for i in range(3)
        )
        if speed2 > 0.0:
            transformed_position = tuple(
                transformed_position[i]+gamma*velocity[i]*dt_local
                for i in range(3)
            )
        else:
            transformed_position = tuple(
                transformed_position[i]+velocity[i]*dt_local
                for i in range(3)
            )
        local_velocity = tuple(
            float(sample["velocity_m_s_along_opposite_beam_axis"])/1000.0*v
            for v in axis
        )
        chart_velocity = lorentz_add_velocity(local_velocity, velocity)
        output.append({
            "coordinate_time_from_throat_exit_s": coordinate_time_offset_s+dt_chart,
            "position_km": list(transformed_position),
            "velocity_km_s": list(chart_velocity),
            "emission_pulse_proper_time_s": sample["proper_time_from_emission_start_s"],
        })
    return output


def lorentz_add_velocity(
    local_velocity_km_s: tuple[float, float, float],
    frame_velocity_km_s: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Transform a velocity from a moving local frame into the chart frame."""
    c_km_s = C / 1000.0
    u = tuple(float(v) for v in local_velocity_km_s)
    frame = tuple(float(v) for v in frame_velocity_km_s)
    if len(u) != 3 or len(frame) != 3:
        raise ValueError("velocity transform inputs must be 3-vectors")
    frame2 = sum(v*v for v in frame)
    if frame2 >= c_km_s*c_km_s or sum(v*v for v in u) >= c_km_s*c_km_s:
        raise ValueError("local and frame velocities must be subluminal")
    gamma = 1.0 / math.sqrt(1.0 - frame2 / c_km_s**2)
    frame_dot_local = sum(frame[i]*u[i] for i in range(3))
    denominator = 1.0 + frame_dot_local / c_km_s**2
    return tuple(
        (u[i]/gamma + frame[i]
         + gamma/(gamma+1.0)*frame_dot_local*frame[i]/c_km_s**2)
        / denominator
        for i in range(3)
    )


def smooth_post_exit_leg(
    start_position_km: tuple[float, float, float],
    end_position_km: tuple[float, float, float],
    duration_s: float,
    start_velocity_km_s: tuple[float, float, float],
    end_velocity_km_s: tuple[float, float, float],
    collision_hazards: tuple[
        tuple[str, tuple[float, float, float], tuple[float, float, float], float], ...
    ] = (),
    hull_envelope_radius_km: float = 0.0,
    detour_bumps: tuple[dict[str, object], ...] = (),
) -> dict[str, object]:
    """Timelike Hermite leg, optionally augmented by compact C2 detour bumps."""
    if duration_s <= 0.0:
        raise ValueError("post-exit leg duration must be positive")
    p0 = tuple(float(v) for v in start_position_km)
    p1 = tuple(float(v) for v in end_position_km)
    v0 = tuple(float(v) for v in start_velocity_km_s)
    v1 = tuple(float(v) for v in end_velocity_km_s)
    if not all(len(v) == 3 for v in (p0, p1, v0, v1)):
        raise ValueError("post-exit positions and velocities must be 3-vectors")
    normalized_bumps = []
    for bump in detour_bumps:
        center_u = float(bump["center_fraction"])
        half_width = float(bump["half_width_fraction"])
        amplitude = float(bump["amplitude_km"])
        direction = tuple(float(v) for v in bump["direction_unit_vector"])
        direction_norm = math.sqrt(sum(v*v for v in direction)) if len(direction) == 3 else 0.0
        if (
            not 0.0 < center_u < 1.0 or not 0.0 < half_width <= 0.5
            or amplitude <= 0.0 or not math.isfinite(amplitude)
            or not math.isfinite(direction_norm) or direction_norm == 0.0
            or center_u-half_width < -1e-12 or center_u+half_width > 1.0+1e-12
        ):
            raise ValueError("detour bumps require an interior center, contained support, positive amplitude, and nonzero direction")
        normalized_bumps.append({
            **bump,
            "center_fraction": center_u,
            "half_width_fraction": half_width,
            "amplitude_km": amplitude,
            "direction_unit_vector": tuple(v/direction_norm for v in direction),
        })
    hazards = []
    for name, center, velocity, radius in collision_hazards:
        center = tuple(float(v) for v in center)
        velocity = tuple(float(v) for v in velocity)
        if len(center) != 3 or len(velocity) != 3 or radius <= 0.0:
            raise ValueError("each spherical hazard requires 3D center/velocity and positive radius")
        if sum(v*v for v in velocity) >= (C/1000.0)**2:
            raise ValueError("spherical hazard velocity must be subluminal")
        hazards.append((name, center, velocity, float(radius)))

    position_controls = (
        p0,
        tuple(p0[i]+duration_s*v0[i]/5.0 for i in range(3)),
        tuple(p0[i]+2.0*duration_s*v0[i]/5.0 for i in range(3)),
        tuple(p1[i]-2.0*duration_s*v1[i]/5.0 for i in range(3)),
        tuple(p1[i]-duration_s*v1[i]/5.0 for i in range(3)),
        p1,
    )
    velocity_controls = tuple(
        tuple(5.0*(position_controls[j+1][i]-position_controls[j][i])/duration_s for i in range(3))
        for j in range(5)
    )
    acceleration_controls = tuple(
        tuple(4.0*(velocity_controls[j+1][i]-velocity_controls[j][i])/duration_s for i in range(3))
        for j in range(4)
    )

    def bezier(controls: tuple[tuple[float, ...], ...], u: float) -> tuple[float, ...]:
        level = list(controls)
        while len(level) > 1:
            level = [
                tuple((level[j][i]*(1.0-u)+level[j+1][i]*u) for i in range(3))
                for j in range(len(level)-1)
            ]
        return level[0]

    def state(u: float) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
        pos = bezier(position_controls, u)
        vel = bezier(velocity_controls, u)
        acc = bezier(acceleration_controls, u)
        for bump in normalized_bumps:
            center_u = float(bump["center_fraction"])
            half_width = float(bump["half_width_fraction"])
            z = (u-center_u)/half_width
            if abs(z) >= 1.0:
                continue
            angle = 0.5*math.pi*z
            sine, cosine = math.sin(angle), math.cos(angle)
            shape = cosine**4
            shape_z = -4.0*cosine**3*sine
            shape_zz = 12.0*cosine*cosine*sine*sine-4.0*cosine**4
            shape_u = shape_z*0.5*math.pi/half_width
            shape_uu = shape_zz*(0.5*math.pi/half_width)**2
            amplitude = float(bump["amplitude_km"])
            direction = tuple(float(v) for v in bump["direction_unit_vector"])
            pos = tuple(pos[i]+amplitude*shape*direction[i] for i in range(3))
            vel = tuple(vel[i]+amplitude*shape_u*direction[i]/duration_s for i in range(3))
            acc = tuple(acc[i]+amplitude*shape_uu*direction[i]/duration_s**2 for i in range(3))
        return pos, vel, acc

    samples = 10_000
    speed_max = 0.0
    coordinate_acceleration_max = 0.0
    proper_acceleration_max = 0.0
    proper_integrand = []
    sampled_worldline = []
    min_hull_clearance_km = [math.inf for _ in hazards]
    min_clearance_time_s = [None for _ in hazards]
    min_clearance_position_km = [None for _ in hazards]
    for k in range(samples + 1):
        position, velocity, acceleration = state(k / samples)
        speed2 = sum(v*v for v in velocity)
        speed = math.sqrt(speed2)
        if speed >= C / 1000.0:
            raise ValueError("post-exit quintic worldline reaches or exceeds c in sampled interval")
        gamma = 1.0 / math.sqrt(1.0 - speed2 / (C / 1000.0)**2)
        accel2 = sum(a*a for a in acceleration)
        va = sum(velocity[i]*acceleration[i] for i in range(3))
        proper_accel = math.sqrt(gamma**4*accel2 + gamma**6*va**2/(C/1000.0)**2)
        speed_max = max(speed_max, speed)
        coordinate_acceleration_max = max(coordinate_acceleration_max, math.sqrt(accel2))
        proper_acceleration_max = max(proper_acceleration_max, proper_accel)
        proper_integrand.append(math.sqrt(1.0 - speed2 / (C / 1000.0)**2))
        t = duration_s * (k / samples)
        if k % 50 == 0 or k == samples:
            sampled_worldline.append({
                "coordinate_time_from_throat_exit_s": t,
                "position_km": list(position),
                "velocity_km_s": list(velocity),
            })
        for j, (_, center0, body_velocity, body_radius) in enumerate(hazards):
            center = tuple(center0[i] + body_velocity[i]*t for i in range(3))
            center_distance = math.sqrt(sum((position[i]-center[i])**2 for i in range(3)))
            clearance = center_distance-body_radius-hull_envelope_radius_km
            if clearance < min_hull_clearance_km[j]:
                min_hull_clearance_km[j] = clearance
                min_clearance_time_s[j] = t
                min_clearance_position_km[j] = list(position)
    # The quintic Hermite velocity is a quartic Bezier curve. Its values lie
    # in the convex hull of its five derivative controls. Subdivision tightens
    # that bound until the entire curve is certified below c.
    stack = [(velocity_controls, 0)]
    certified_bound = 0.0
    subdivisions = 0
    c_km_s = C / 1000.0
    while stack:
        controls, depth = stack.pop()
        control_norms = [math.sqrt(sum(v*v for v in control)) for control in controls]
        if max(control_norms) < c_km_s:
            certified_bound = max(certified_bound, max(control_norms))
            continue
        if depth >= 32 or subdivisions >= 100_000:
            raise ValueError("could not certify the complete post-exit curve as timelike")
        levels = [list(controls)]
        while len(levels[-1]) > 1:
            previous = levels[-1]
            levels.append([
                tuple((previous[j][i]+previous[j+1][i])/2.0 for i in range(3))
                for j in range(len(previous)-1)
            ])
        left_controls = tuple(level[0] for level in levels)
        right_controls = tuple(level[-1] for level in reversed(levels))
        stack.append((right_controls, depth+1))
        stack.append((left_controls, depth+1))
        subdivisions += 1
    base_certified_bound = certified_bound
    detour_derivative_bound = sum(
        2.0*math.pi*float(bump["amplitude_km"])
        /(float(bump["half_width_fraction"])*duration_s)
        for bump in normalized_bumps
    )
    certified_bound += detour_derivative_bound
    if certified_bound >= c_km_s:
        raise ValueError("the quintic-Hermite-plus-detour speed bound reaches or exceeds c")
    h = duration_s / samples
    proper_time_s = h/3.0 * (
        proper_integrand[0] + proper_integrand[-1]
        + 4.0*sum(proper_integrand[1:-1:2])
        + 2.0*sum(proper_integrand[2:-1:2])
    )
    _, start_velocity, start_acceleration = state(0.0)
    _, end_velocity, end_acceleration = state(1.0)

    def proper_acceleration_magnitude(velocity: tuple[float, ...], acceleration: tuple[float, ...]) -> float:
        v2 = sum(v*v for v in velocity)
        gamma = 1.0/math.sqrt(1.0-v2/(C/1000.0)**2)
        a2 = sum(a*a for a in acceleration)
        va = sum(velocity[i]*acceleration[i] for i in range(3))
        return math.sqrt(gamma**4*a2+gamma**6*va**2/(C/1000.0)**2)

    start_proper_acceleration = proper_acceleration_magnitude(start_velocity, start_acceleration)
    end_proper_acceleration = proper_acceleration_magnitude(end_velocity, end_acceleration)
    result: dict[str, object] = {
        "model": (
            "flat-spacetime quintic-Hermite segment with compact C2 detour bumps"
            if normalized_bumps else "flat-spacetime quintic-Hermite timelike segment"
        ),
        "status": "C2 position-velocity-acceleration curve with zero endpoint coordinate acceleration; complete segment certified timelike",
        "coordinate_duration_seconds": duration_s,
        "proper_time_seconds": proper_time_s,
        "start_position_km": list(p0),
        "end_position_km": list(p1),
        "start_velocity_km_s": list(v0),
        "end_velocity_km_s": list(v1),
        "maximum_sampled_speed_km_s": speed_max,
        "maximum_sampled_speed_fraction_of_c": speed_max / (C / 1000.0),
        "certified_speed_upper_bound_km_s": certified_bound,
        "certified_speed_upper_bound_fraction_of_c": certified_bound / (C / 1000.0),
        "base_quintic_hermite_speed_upper_bound_km_s": base_certified_bound,
        "detour_bump_derivative_speed_bound_km_s": detour_derivative_bound,
        "detour_bumps": [
            {**bump, "direction_unit_vector": list(bump["direction_unit_vector"])}
            for bump in normalized_bumps
        ],
        "timelike_certificate": "quartic Bezier derivative control polygons bound the quintic Hermite velocity; each compact C2 cos^4 bump adds at most 2*pi*amplitude/(half_width*duration) to the speed norm",
        "velocity_curve_subdivisions": subdivisions,
        "maximum_sampled_coordinate_acceleration_km_s2": coordinate_acceleration_max,
        "maximum_sampled_proper_acceleration_km_s2": proper_acceleration_max,
        "start_proper_acceleration_km_s2": start_proper_acceleration,
        "end_proper_acceleration_km_s2": end_proper_acceleration,
        "timelike_normalization": "d tau / dt = sqrt(1 - |v(t)|^2/c^2)",
        "velocity_check_samples": samples + 1,
        "sampled_worldline_for_observation_projection": sampled_worldline,
    }
    clearance_results = []
    for j, (name, center0, body_velocity, body_radius) in enumerate(hazards):
        sampled_clearance = min_hull_clearance_km[j]
        obstacle_speed = math.sqrt(sum(v*v for v in body_velocity))
        relative_speed_bound = certified_bound+obstacle_speed
        between_sample_margin = relative_speed_bound * duration_s / samples / 2.0
        lower_bound = sampled_clearance - between_sample_margin
        clearance_results.append({
            "name": name,
            "model": "constant-velocity spherical obstacle and spherical hull envelope",
            "center_at_segment_start_km": list(center0),
            "obstacle_velocity_km_s": list(body_velocity),
            "obstacle_radius_km": body_radius,
            "hull_envelope_radius_km": hull_envelope_radius_km,
            "minimum_sampled_hull_clearance_km": sampled_clearance,
            "minimum_clearance_time_s": min_clearance_time_s[j],
            "minimum_clearance_hull_position_km": min_clearance_position_km[j],
            "obstacle_speed_km_s": obstacle_speed,
            "relative_speed_upper_bound_km_s": relative_speed_bound,
            "between_sample_relative_travel_bound_km": between_sample_margin,
            "conservative_full_segment_hull_clearance_lower_bound_km": lower_bound,
            "status": (
                "collision_detected_at_sample"
                if sampled_clearance <= 0.0 else
                "clear_for_full_segment_under_spherical_bound"
                if lower_bound > 0.0 else
                "not_certified_between_samples"
            ),
            "clearance_bound_basis": "distance to a sphere is 1-Lipschitz; certified Hermite-plus-detour and obstacle speed bounds travel between samples",
        })
    result["spherical_collision_clearances"] = clearance_results
    return result


def plan_hazard_avoiding_post_exit_leg(
    start_position_km: tuple[float, float, float],
    end_position_km: tuple[float, float, float],
    duration_s: float,
    start_velocity_km_s: tuple[float, float, float],
    end_velocity_km_s: tuple[float, float, float],
    collision_hazards: tuple[
        tuple[str, tuple[float, float, float], tuple[float, float, float], float], ...
    ],
    hull_envelope_radius_km: float,
) -> dict[str, object]:
    """Search a fixed-duration Hermite leg for C2 spherical-hazard detours.

    Each detour is a compact cos^4 bump (zero through second derivative at its
    support edges) centered on a worst-clearance event. This is a deterministic
    local planner, not a globally optimal path search or a force-control law.
    """
    if not collision_hazards:
        route = smooth_post_exit_leg(
            start_position_km, end_position_km, duration_s,
            start_velocity_km_s, end_velocity_km_s,
            collision_hazards, hull_envelope_radius_km,
        )
        route["hazard_avoidance_planning"] = {
            "status": "no_hazards_supplied_nominal_route_returned",
            "method": "compact C2 bump search requires spherical hazards",
            "detour_count": 0,
        }
        return route

    bumps: list[dict[str, object]] = []
    max_iterations = max(4, 2*len(collision_hazards))
    evaluations = 0

    def evaluate(candidate_bumps: tuple[dict[str, object], ...]) -> dict[str, object]:
        nonlocal evaluations
        evaluations += 1
        return smooth_post_exit_leg(
            start_position_km, end_position_km, duration_s,
            start_velocity_km_s, end_velocity_km_s,
            collision_hazards, hull_envelope_radius_km,
            candidate_bumps,
        )

    route = evaluate(())
    for iteration in range(max_iterations+1):
        clearances = route["spherical_collision_clearances"]
        unresolved = [
            item for item in clearances
            if item["status"] != "clear_for_full_segment_under_spherical_bound"
        ]
        if not unresolved:
            route["hazard_avoidance_planning"] = {
                "status": "certified_detour_found" if bumps else "nominal_route_certified_no_detour_needed",
                "method": "fixed-duration C2 compact-bump search over the Hermite route; every listed sphere has a positive continuous clearance lower bound",
                "detour_count": len(bumps),
                "iterations": iteration,
                "candidate_route_evaluations": evaluations,
            }
            return route
        if iteration == max_iterations:
            break
        worst = min(
            unresolved,
            key=lambda item: float(item["conservative_full_segment_hull_clearance_lower_bound_km"]),
        )
        hazard = next(item for item in collision_hazards if item[0] == worst["name"])
        _, center0, obstacle_velocity, obstacle_radius = hazard
        t_closest = float(worst["minimum_clearance_time_s"])
        u0 = t_closest/duration_s
        if not 0.0 < u0 < 1.0:
            break
        half_width = min(0.5, u0, 1.0-u0)
        if half_width < 1e-3:
            break
        hull_position = tuple(float(v) for v in worst["minimum_clearance_hull_position_km"])
        obstacle_position = tuple(
            float(center0[i])+float(obstacle_velocity[i])*t_closest
            for i in range(3)
        )
        radial = tuple(hull_position[i]-obstacle_position[i] for i in range(3))
        radial_norm = math.sqrt(sum(v*v for v in radial))
        if radial_norm > 1e-12:
            radial_hat = tuple(v/radial_norm for v in radial)
            reference = min(
                ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
                key=lambda axis: abs(sum(axis[i]*radial_hat[i] for i in range(3))),
            )
            perpendicular = (
                radial_hat[1]*reference[2]-radial_hat[2]*reference[1],
                radial_hat[2]*reference[0]-radial_hat[0]*reference[2],
                radial_hat[0]*reference[1]-radial_hat[1]*reference[0],
            )
            perp_norm = math.sqrt(sum(v*v for v in perpendicular))
            perpendicular = tuple(v/perp_norm for v in perpendicular)
            second_perpendicular = (
                radial_hat[1]*perpendicular[2]-radial_hat[2]*perpendicular[1],
                radial_hat[2]*perpendicular[0]-radial_hat[0]*perpendicular[2],
                radial_hat[0]*perpendicular[1]-radial_hat[1]*perpendicular[0],
            )
            directions = (radial_hat, perpendicular, tuple(-v for v in perpendicular), second_perpendicular, tuple(-v for v in second_perpendicular))
        else:
            directions = (
                (1.0, 0.0, 0.0), (-1.0, 0.0, 0.0),
                (0.0, 1.0, 0.0), (0.0, -1.0, 0.0),
                (0.0, 0.0, 1.0), (0.0, 0.0, -1.0),
            )
        total_radius = float(obstacle_radius)+hull_envelope_radius_km
        safety_margin = max(0.05*total_radius, 1e-6)
        obstacle_speed = math.sqrt(sum(float(v)**2 for v in obstacle_velocity))
        travel_margin = (
            float(route["certified_speed_upper_bound_km_s"])+obstacle_speed
        )*duration_s/20_000.0
        target_radius = total_radius+safety_margin+travel_margin
        current_score = min(
            float(item["conservative_full_segment_hull_clearance_lower_bound_km"])
            for item in clearances
        )
        best_route = None
        best_score = -math.inf
        best_bump = None
        for direction in directions:
            radial_projection = sum(radial[i]*direction[i] for i in range(3))
            discriminant = radial_projection**2+target_radius**2-radial_norm**2
            if discriminant < 0.0:
                continue
            amplitude = max(1e-9, -radial_projection+math.sqrt(discriminant))
            bump = {
                "hazard": worst["name"],
                "center_fraction": u0,
                "half_width_fraction": half_width,
                "amplitude_km": amplitude,
                "direction_unit_vector": direction,
            }
            try:
                candidate = evaluate(tuple(bumps+[bump]))
            except ValueError:
                continue
            score = min(
                float(item["conservative_full_segment_hull_clearance_lower_bound_km"])
                for item in candidate["spherical_collision_clearances"]
            )
            if score > best_score:
                best_route, best_score, best_bump = candidate, score, bump
        if best_route is None or best_score <= current_score:
            break
        bumps.append(best_bump)
        route = best_route

    route["hazard_avoidance_planning"] = {
        "status": "no_certified_detour_found",
        "method": "fixed-duration C2 compact-bump search; the returned candidate remains subject to its per-hazard clearance statuses",
        "detour_count": len(bumps),
        "iterations": min(max_iterations, len(bumps)+1),
        "candidate_route_evaluations": evaluations,
        "unresolved_hazards": [
            item["name"] for item in route["spherical_collision_clearances"]
            if item["status"] != "clear_for_full_segment_under_spherical_bound"
        ],
    }
    return route


def build(
    lookback_years: float,
    throat_radius_m: float,
    throat_length_m: float,
    hull_width_m: float,
    transit_seconds: float,
    beta_values: tuple[float, ...],
    hull_visible_height_m: float = 2.134,
    mouth_radius_m: float | None = None,
    witness_lookback_years: float | None = None,
    emitter_range_km: float = 0.0,
    mouth_profile: str = "sin",
    pair_formation_lookback_years: float | None = None,
    emitter_position_km: tuple[float, float, float] | None = None,
    witness_position_at_emission_km: tuple[float, float, float] | None = None,
    witness_velocity_km_s: tuple[float, float, float] = (0.0, 0.0, 0.0),
    post_exit_duration_s: float = 0.0,
    post_exit_start_position_km: tuple[float, float, float] | None = None,
    post_exit_end_velocity_km_s: tuple[float, float, float] = (0.0, 0.0, 0.0),
    earth_center_position_km: tuple[float, float, float] | None = None,
    earth_radius_km: float = 6378.137,
    terrain_margin_m: float = 0.0,
    additional_spherical_hazards: tuple[tuple[float, ...], ...] = (),
    exit_normal_unit_vector: tuple[float, float, float] = (1.0, 0.0, 0.0),
    earth_velocity_km_s: tuple[float, float, float] = (0.0, 0.0, 0.0),
    throat_exit_frame_velocity_km_s: tuple[float, float, float] | None = None,
    coordinate_frame_name: str = "user-specified shared inertial Cartesian frame",
    emission_source_rest_mass_kg: float | None = None,
    emitted_cone_energy_j: float | None = None,
    emission_cone_half_angle_deg: float = 10.0,
    emission_duration_proper_s: float | None = None,
    emission_beam_axis_unit_vector_in_source_rest_frame: tuple[float, float, float] = (1.0, 0.0, 0.0),
    emission_pulse_envelope: str = "sin2",
    plan_hazard_avoiding_route: bool = False,
) -> dict[str, object]:
    if min(
        throat_radius_m,
        throat_length_m,
        hull_width_m,
        hull_visible_height_m,
        transit_seconds,
    ) <= 0:
        raise ValueError("all lengths and durations must be positive")
    if witness_lookback_years is None and lookback_years <= 0:
        raise ValueError("target exit lookback must be positive")
    # The matched cut must be at the endpoints of the finite path used by the
    # transit and tidal calculations: ell = +/- L/2 and
    # R^2 = ell^2 + r0^2 for the Ellis shape.
    selected_mouth_radius_m = (
        math.hypot(throat_radius_m, 0.5 * throat_length_m)
        if mouth_radius_m is None else mouth_radius_m
    )
    if selected_mouth_radius_m <= throat_radius_m:
        raise ValueError("mouth radius must exceed throat radius")
    matched_mouth_radius_m = math.hypot(throat_radius_m, 0.5 * throat_length_m)
    if not math.isclose(
        selected_mouth_radius_m, matched_mouth_radius_m, rel_tol=1e-10, abs_tol=1e-9
    ):
        raise ValueError(
            "mouth radius must match the finite transit endpoints: "
            "R = sqrt(r0^2 + (throat_length/2)^2)"
        )
    # A circle around the width-height rectangle is invariant under orientation
    # and conservative for a circular throat cross-section. It covers only the
    # visible drawing dimensions, not the unspecified buried compartment.
    visible_envelope_radius_m = 0.5 * math.hypot(hull_width_m, hull_visible_height_m)
    # For exterior collision screening, bound a saucer planform whose two
    # horizontal spans are each no larger than hull_width_m, plus its height.
    collision_envelope_radius_m = 0.5 * math.sqrt(
        2.0*hull_width_m*hull_width_m + hull_visible_height_m*hull_visible_height_m
    )
    if visible_envelope_radius_m >= throat_radius_m:
        raise ValueError("visible hull bounding circle must fit inside the throat radius")
    if emitter_range_km < 0.0:
        raise ValueError("emitter range cannot be negative")
    if witness_lookback_years is not None and witness_lookback_years < 0.0:
        raise ValueError("witness lookback cannot be negative")
    if (emission_source_rest_mass_kg is None) != (emitted_cone_energy_j is None):
        raise ValueError("emission source rest mass and emitted cone energy must be supplied together")
    emission_recoil_screen = (
        local_conical_emission_recoil(
            emission_source_rest_mass_kg,
            emitted_cone_energy_j,
            emission_cone_half_angle_deg,
            emission_duration_proper_s,
            emission_pulse_envelope,
        )
        if emission_source_rest_mass_kg is not None and emitted_cone_energy_j is not None
        else None
    )
    if post_exit_duration_s < 0.0:
        raise ValueError("post-exit duration cannot be negative")
    if plan_hazard_avoiding_route and post_exit_duration_s <= 0.0:
        raise ValueError("hazard-avoiding route planning requires a positive post-exit duration")
    if earth_radius_km <= 0.0 or terrain_margin_m < 0.0:
        raise ValueError("Earth radius must be positive and terrain margin cannot be negative")
    if earth_center_position_km is not None and len(earth_center_position_km) != 3:
        raise ValueError("Earth center position must be a 3-vector")
    if len(exit_normal_unit_vector) != 3 or len(earth_velocity_km_s) != 3:
        raise ValueError("exit normal and Earth velocity must be 3-vectors")
    exit_normal_norm = math.sqrt(sum(float(v)**2 for v in exit_normal_unit_vector))
    if not math.isfinite(exit_normal_norm) or exit_normal_norm == 0.0:
        raise ValueError("exit normal must have finite, nonzero length")
    exit_normal = tuple(float(v)/exit_normal_norm for v in exit_normal_unit_vector)
    earth_velocity = tuple(float(v) for v in earth_velocity_km_s)
    exit_frame_velocity = tuple(float(v) for v in (
        throat_exit_frame_velocity_km_s
        if throat_exit_frame_velocity_km_s is not None
        else earth_velocity
    ))
    if len(exit_frame_velocity) != 3:
        raise ValueError("throat-exit frame velocity must be a 3-vector")
    if sum(v*v for v in earth_velocity) >= (C/1000.0)**2:
        raise ValueError("Earth velocity must be subluminal")
    collision_hazards = []
    if earth_center_position_km is not None:
        collision_hazards.append((
            "Earth",
            tuple(earth_center_position_km),
            earth_velocity,
            earth_radius_km + terrain_margin_m / 1000.0,
        ))
    for index, hazard in enumerate(additional_spherical_hazards, start=1):
        if len(hazard) != 7 or hazard[6] <= 0.0:
            raise ValueError("additional hazards must be (x,y,z,vx,vy,vz,radius), with positive radius")
        if sum(float(v)**2 for v in hazard[3:6]) >= (C/1000.0)**2:
            raise ValueError("additional spherical hazard velocities must be subluminal")
        collision_hazards.append((
            f"obstacle_{index}", tuple(hazard[:3]), tuple(hazard[3:6]), float(hazard[6])
        ))
    if mouth_profile not in {"sin", "c2"}:
        raise ValueError("mouth profile must be 'sin' or 'c2'")
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
    local_outward_velocity = tuple(local_speed / 1000.0 * v for v in exit_normal)
    post_exit_initial_velocity = lorentz_add_velocity(
        local_outward_velocity, exit_frame_velocity
    )
    initial_beta2 = sum(v*v for v in post_exit_initial_velocity) / (C/1000.0)**2
    initial_gamma = 1.0 / math.sqrt(1.0 - initial_beta2)
    if post_exit_duration_s > 0.0 and (
        post_exit_start_position_km is None or emitter_position_km is None
    ):
        raise ValueError(
            "a nonzero post-exit leg requires throat-exit and emitter positions in one frame"
        )
    if post_exit_duration_s == 0.0 and post_exit_start_position_km is not None:
        if len(post_exit_start_position_km) != 3 or (
            emitter_position_km is not None and len(emitter_position_km) != 3
        ):
            raise ValueError("post-exit positions must be 3-vectors")
        if emitter_position_km is None or any(
            not math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=1e-9)
            for a, b in zip(post_exit_start_position_km, emitter_position_km)
        ):
            raise ValueError("zero-duration post-exit leg requires coincident exit and emitter positions")
    post_exit_route_planning = None
    post_exit_leg = None
    if post_exit_duration_s > 0.0:
        if plan_hazard_avoiding_route:
            post_exit_leg = plan_hazard_avoiding_post_exit_leg(
                post_exit_start_position_km,
                emitter_position_km,
                post_exit_duration_s,
                post_exit_initial_velocity,
                post_exit_end_velocity_km_s,
                tuple(collision_hazards),
                collision_envelope_radius_m / 1000.0,
            )
            post_exit_route_planning = post_exit_leg.get("hazard_avoidance_planning")
        else:
            post_exit_leg = smooth_post_exit_leg(
                post_exit_start_position_km,
                emitter_position_km,
                post_exit_duration_s,
                post_exit_initial_velocity,
                post_exit_end_velocity_km_s,
                tuple(collision_hazards),
                collision_envelope_radius_m / 1000.0,
            )
    if post_exit_leg is not None:
        collision_clearances = post_exit_leg["spherical_collision_clearances"]
    else:
        endpoint_position = (
            emitter_position_km
            if emitter_position_km is not None else post_exit_start_position_km
        )
        collision_clearances = []
        if endpoint_position is not None:
            for name, center, velocity, radius in collision_hazards:
                distance = math.sqrt(sum(
                    (float(endpoint_position[i])-float(center[i]))**2 for i in range(3)
                ))
                clearance = distance - radius - collision_envelope_radius_m/1000.0
                collision_clearances.append({
                    "name": name,
                    "model": "single endpoint against a constant-velocity spherical obstacle and hull envelope; no terrain",
                    "signed_clearance_definition": "d_clear=|x_hull_center-x_obstacle|-R_obstacle-R_hull",
                    "hull_envelope_assumption": "spherical bound for a saucer planform whose two horizontal spans are each no larger than hull_width_m, with height hull_visible_height_m; buried compartment excluded",
                    "minimum_sampled_hull_clearance_km": clearance,
                    "status": "collision_at_destination_endpoint" if clearance <= 0.0 else "endpoint_clear_only_path_unchecked",
                })
    global_emission_pulse_segment = None
    if (
        emission_recoil_screen is not None
        and emission_duration_proper_s is not None
        and emitter_position_km is not None
    ):
        local_pulse = emission_recoil_screen.get("continuous_emission_segment")
        local_samples = (
            local_pulse.get("sampled_local_worldline_for_observation_projection")
            if isinstance(local_pulse, dict) else None
        )
        if local_samples is not None:
            pulse_start_velocity = (
                post_exit_end_velocity_km_s
                if post_exit_leg is not None else post_exit_initial_velocity
            )
            pulse_samples = boost_local_emission_worldline_to_chart(
                local_samples,
                tuple(emitter_position_km) if emitter_position_km is not None else (0.0, 0.0, 0.0),
                tuple(pulse_start_velocity),
                emission_beam_axis_unit_vector_in_source_rest_frame,
                post_exit_duration_s,
            )
            prior_end_acceleration_m_s2 = (
                1000.0*float(post_exit_leg["end_proper_acceleration_km_s2"])
                if post_exit_leg is not None else 0.0
            )
            pulse_start_acceleration_m_s2 = float(
                local_samples[0]["proper_acceleration_m_s2"]
            )
            pulse_end_acceleration_m_s2 = float(
                local_samples[-1]["proper_acceleration_m_s2"]
            )
            acceleration_join_tolerance = max(
                1e-30,
                1e-9*max(prior_end_acceleration_m_s2, pulse_start_acceleration_m_s2),
            )
            acceleration_join_continuous = (
                prior_end_acceleration_m_s2 <= acceleration_join_tolerance
                and pulse_start_acceleration_m_s2 <= acceleration_join_tolerance
            )
            pulse_times = [
                float(sample["coordinate_time_from_throat_exit_s"])
                for sample in pulse_samples
            ]
            max_sample_interval_s = max(
                (b-a for a, b in zip(pulse_times, pulse_times[1:])),
                default=0.0,
            )
            c_km_s = C/1000.0
            initial_speed_km_s = math.sqrt(sum(v*v for v in pulse_start_velocity))
            initial_rapidity = math.atanh(initial_speed_km_s/c_km_s)
            relative_pulse_rapidity = abs(float(
                local_pulse["final_rapidity_along_opposite_beam_axis"]
            ))
            hull_speed_upper_bound_km_s = c_km_s*math.tanh(
                initial_rapidity+relative_pulse_rapidity
            )
            pulse_collision_clearances = []
            for name, center0, hazard_velocity, hazard_radius in collision_hazards:
                minimum = math.inf
                for sample in pulse_samples:
                    t = float(sample["coordinate_time_from_throat_exit_s"])
                    center = tuple(center0[i]+hazard_velocity[i]*t for i in range(3))
                    p = tuple(float(v) for v in sample["position_km"])
                    distance = math.sqrt(sum((p[i]-center[i])**2 for i in range(3)))
                    minimum = min(
                        minimum,
                        distance-hazard_radius-collision_envelope_radius_m/1000.0,
                    )
                hazard_speed = math.sqrt(sum(v*v for v in hazard_velocity))
                relative_speed_bound = hull_speed_upper_bound_km_s+hazard_speed
                between_sample_bound = relative_speed_bound*max_sample_interval_s/2.0
                lower_bound = minimum-between_sample_bound
                pulse_collision_clearances.append({
                    "name": name,
                    "minimum_sampled_hull_clearance_km": minimum,
                    "maximum_sample_interval_s": max_sample_interval_s,
                    "hull_speed_upper_bound_km_s": hull_speed_upper_bound_km_s,
                    "obstacle_speed_km_s": hazard_speed,
                    "between_sample_relative_travel_bound_km": between_sample_bound,
                    "conservative_full_pulse_clearance_lower_bound_km": lower_bound,
                    "status": (
                        "collision_detected_at_sample" if minimum <= 0.0 else
                        "clear_for_full_segment_under_relativistic_speed_bound"
                        if lower_bound > 0.0 else
                        "not_certified_between_samples"
                    ),
                    "clearance_bound_basis": "distance to the inflated spherical obstacle is 1-Lipschitz; the pulse hull speed is bounded by the triangle inequality for rapidity, obstacle speed is constant, and every point is within half the largest sample interval",
                })
            global_emission_pulse_segment = {
                "model": "finite local photon-rocket segment Lorentz-boosted into the declared flat mission chart",
                "status": "continuous endpoint position and velocity under the collinear local flat-space assumptions",
                "start_position_km": list(emitter_position_km) if emitter_position_km is not None else None,
                "start_velocity_km_s": list(pulse_start_velocity),
                "beam_axis_unit_vector_in_source_rest_frame": list(emission_beam_axis_unit_vector_in_source_rest_frame),
                "sample_count": len(pulse_samples),
                "acceleration_boundary_check": {
                    "preceding_segment_end_proper_acceleration_m_s2": prior_end_acceleration_m_s2,
                    "pulse_start_proper_acceleration_m_s2": pulse_start_acceleration_m_s2,
                    "pulse_end_proper_acceleration_m_s2": pulse_end_acceleration_m_s2,
                    "pulse_start_join_status": (
                        "zero_proper_acceleration_join"
                        if acceleration_join_continuous else
                        "proper_acceleration_discontinuous_at_pulse_start"
                    ),
                    "post_pulse_join_status": "not_evaluated_no_following_worldline",
                    "comparison_tolerance_m_s2": acceleration_join_tolerance,
                },
                "sampled_worldline_for_observation_projection": pulse_samples,
                "pulse_collision_clearances": pulse_collision_clearances,
                "clearance_method": "relativistic speed bound plus nearest-sample distance margin; positive lower bounds certify this finite pulse segment against the listed moving spheres and stated hull envelope",
                "limitations": [
                    "canonical rotationless boost defines the source-rest axes at pulse start; beam direction is Fermi-Walker transported during collinear recoil",
                    "flat chart only; no gravity, thrust, torque, hull response, or interaction with throat stress-energy",
                    "a positive speed-bound clearance certifies only against the listed constant-velocity spheres and stated hull envelope; it does not cover unlisted terrain or hazards",
                ],
            }
            emission_recoil_screen["trajectory_coupling"] = (
                "finite pulse segment is boosted into the exterior chart and used for the retarded sighting track; listed-sphere clearance is certified only when its relativistic speed-bound lower bound is positive; no post-pulse or throat-return route is integrated"
            )
    event_emitter_position_km = tuple(emitter_position_km) if emitter_position_km is not None else None
    emission_pulse_coordinate_duration_s = 0.0
    if global_emission_pulse_segment is not None:
        final_pulse_sample = global_emission_pulse_segment[
            "sampled_worldline_for_observation_projection"
        ][-1]
        event_emitter_position_km = tuple(final_pulse_sample["position_km"])
        emission_pulse_coordinate_duration_s = float(
            final_pulse_sample["coordinate_time_from_throat_exit_s"]
        )-post_exit_duration_s
        if post_exit_leg is None:
            for item in collision_clearances:
                if item["status"] == "endpoint_clear_only_path_unchecked":
                    item["status"] = "clear_at_pulse_start"
                    item["scope"] = "the post-exit endpoint is the pulse start; the subsequent pulse has its own continuous clearance bound"
    earth_clearance = next(
        (item for item in collision_clearances if item["name"] == "Earth"),
        {"status": "not_evaluated_no_Earth_sphere_supplied"},
    )
    collision_rejects_candidate = any(
        item["status"] in {"collision_detected_at_sample", "collision_at_destination_endpoint"}
        for item in collision_clearances
    ) or bool(global_emission_pulse_segment and any(
        item["status"] == "collision_detected_at_sample"
        for item in global_emission_pulse_segment["pulse_collision_clearances"]
    ))
    route_clear_statuses = {"clear_for_full_segment_under_spherical_bound", "clear_at_pulse_start"}
    route_clear = (
        bool(collision_hazards)
        and len(collision_clearances) == len(collision_hazards)
        and all(item["status"] in route_clear_statuses for item in collision_clearances)
    )
    pulse_clear = (
        global_emission_pulse_segment is None
        or (
            bool(collision_hazards)
            and len(global_emission_pulse_segment["pulse_collision_clearances"]) == len(collision_hazards)
            and all(
                item["status"] == "clear_for_full_segment_under_relativistic_speed_bound"
                for item in global_emission_pulse_segment["pulse_collision_clearances"]
            )
        )
    )
    all_hazards_clear = route_clear and pulse_clear
    pulse_clearance_unresolved = (
        global_emission_pulse_segment is not None
        and not pulse_clear
        and bool(collision_hazards)
    )
    if witness_position_at_emission_km is not None and event_emitter_position_km is None:
        raise ValueError("a witness position requires the emitter position for a geometric intercept")
    null_intercept = (
        flat_space_null_intercept(
            event_emitter_position_km,
            witness_position_at_emission_km,
            witness_velocity_km_s,
        )
        if event_emitter_position_km is not None and witness_position_at_emission_km is not None
        else None
    )
    apparent_track = None
    if null_intercept is not None:
        emission_samples = (
            global_emission_pulse_segment["sampled_worldline_for_observation_projection"]
            if global_emission_pulse_segment is not None else
            post_exit_leg["sampled_worldline_for_observation_projection"]
            if post_exit_leg is not None else
            [{
                "coordinate_time_from_throat_exit_s": 0.0,
                "position_km": list(emitter_position_km),
                "velocity_km_s": list(post_exit_initial_velocity),
            }]
        )
        apparent_track = flat_space_apparent_track(
            emission_samples,
            witness_position_at_emission_km,
            witness_velocity_km_s,
            emission_beam_axis_unit_vector_in_source_rest_frame
            if global_emission_pulse_segment is not None else None,
            emission_cone_half_angle_deg
            if global_emission_pulse_segment is not None else None,
            global_emission_pulse_segment is not None,
        )
    if null_intercept is not None:
        light_flight_s = float(null_intercept["flight_time_seconds"])
        effective_emitter_range_km = float(null_intercept["photon_path_length_km"])
        if emitter_range_km > 0.0 and not math.isclose(
            emitter_range_km, effective_emitter_range_km, rel_tol=1e-9, abs_tol=1e-9
        ):
            raise ValueError(
                "--emitter-range-km conflicts with the path length computed from the supplied positions"
            )
    else:
        light_flight_s = emitter_range_km * 1000.0 / C
        effective_emitter_range_km = emitter_range_km
    post_exit_decimal_s = Decimal(str(post_exit_duration_s+emission_pulse_coordinate_duration_s))
    if witness_lookback_years is None:
        resolved_witness_lookback_years = None
        photon_residual_s = None
        with localcontext() as ctx:
            ctx.prec = 50
            emission_lookback_decimal_years = Decimal(str(lookback_years))
            exit_lookback_decimal_years = (
                emission_lookback_decimal_years + post_exit_decimal_s/JULIAN_YEAR_D
            )
            lag_decimal_years = (
                exit_lookback_decimal_years
                + Decimal(str(throat_clock_advance_s))/JULIAN_YEAR_D
            )
    else:
        resolved_witness_lookback_years = witness_lookback_years
        # Preserve microsecond-scale emission-to-reception offsets when the
        # absolute event epochs are thousands of years from the control date.
        with localcontext() as ctx:
            ctx.prec = 50
            witness_decimal_years = Decimal(str(witness_lookback_years))
            light_flight_decimal_s = (
                Decimal(str(emitter_range_km)) * Decimal(1000) / C_D
                if null_intercept is None
                else Decimal(str(light_flight_s))
            )
            emission_lookback_decimal_years = (
                witness_decimal_years + light_flight_decimal_s/JULIAN_YEAR_D
            )
            exit_lookback_decimal_years = (
                emission_lookback_decimal_years + post_exit_decimal_s/JULIAN_YEAR_D
            )
            lag_decimal_years = (
                exit_lookback_decimal_years
                + Decimal(str(throat_clock_advance_s))/JULIAN_YEAR_D
            )
            photon_residual_s = float(
                (emission_lookback_decimal_years-witness_decimal_years)*JULIAN_YEAR_D
                - light_flight_decimal_s
            )
    exit_lookback_years = float(exit_lookback_decimal_years)
    emission_lookback_years = float(emission_lookback_decimal_years)
    if lag_decimal_years is None:
        lag_needed_years = exit_lookback_years + throat_clock_advance_s/JULIAN_YEAR_S
    else:
        lag_needed_years = float(lag_decimal_years)
    mouth_cases = []
    for beta in beta_values:
        case = estimate(lag_needed_years, beta, profile=mouth_profile)
        achieved_lag = clock_lag_years(
            float(case["exterior_duration_years"]), 0.0, beta, 20_000, mouth_profile
        )
        case["achieved_clock_lag_years_reintegrated"] = achieved_lag
        case["clock_lag_numeric_residual_seconds"] = (
            (float(achieved_lag)-lag_needed_years)*JULIAN_YEAR_S
            if achieved_lag is not None else None
        )
        mouth_cases.append(case)
    formation_cases = []
    for case in mouth_cases:
        history_years = float(case["exterior_duration_years"])
        anchor_age_at_exit_years = (
            float(case["moving_mouth_proper_time_years"])
            + throat_clock_advance_s / JULIAN_YEAR_S
        )
        if pair_formation_lookback_years is None:
            gate_status = "not evaluated; provide pair_formation_lookback_years to test this profile"
            formation_margin_years = None
        else:
            formation_margin_years = pair_formation_lookback_years - history_years
            gate_status = (
                "passes date-ordering screen only; mouth trajectory and formation physics remain unsolved"
                if formation_margin_years >= 0.0
                else "fails: the pair forms after this profile's clock-offset history begins"
            )
        formation_cases.append({
            "maximum_speed_fraction_of_c": float(case["maximum_speed_fraction_of_c"]),
            "latest_pair_formation_lookback_years_before_control": history_years,
            "anchor_mouth_clock_age_at_hull_exit_years_since_profile_start": anchor_age_at_exit_years,
            "assumed_pair_formation_lookback_years_before_control": pair_formation_lookback_years,
            "formation_margin_years_before_profile_start": formation_margin_years,
            "status": gate_status,
        })
    all_profiles_fail_formation = (
        pair_formation_lookback_years is not None
        and all(case["formation_margin_years_before_profile_start"] < 0.0 for case in formation_cases)
    )
    all_profiles_pass_formation_screen = (
        pair_formation_lookback_years is not None
        and all(case["formation_margin_years_before_profile_start"] >= 0.0 for case in formation_cases)
    )
    collision_status = (
        "collision_detected"
        if collision_rejects_candidate else
        "all_listed_spheres_clear_for_modeled_exterior_segments"
        if all_hazards_clear else
        "not_evaluated_no_spherical_hazards" if not collision_hazards else
        "not_demonstrated"
    )
    return {
        "model": "conditional hull traversal through an Ellis-type throat with a prescribed twin-mouth clock lag",
        "status": "kinematic toy coupled to a static analytic throat; dynamic source and full exterior solution absent",
        "target_exit_lookback_years": exit_lookback_years,
        "target_emission_lookback_years": emission_lookback_years,
        "sighting_event_ledger": {
            "control_entry_event_T_years": 0.0,
            "hull_throat_exit_event_T_years": -exit_lookback_years,
            "hull_emission_event_T_years": -emission_lookback_years,
            "witness_reception_event_T_years": (
                -resolved_witness_lookback_years
                if resolved_witness_lookback_years is not None else None
            ),
            "witness_lookback_input_years": resolved_witness_lookback_years,
            "target_exit_lookback_years_decimal": (
                str(exit_lookback_decimal_years)
            ),
            "target_emission_lookback_years_decimal": str(emission_lookback_decimal_years),
            "post_exit_coordinate_duration_seconds": post_exit_duration_s,
            "continuous_emission_pulse_coordinate_duration_seconds": emission_pulse_coordinate_duration_s,
            "continuous_emission_pulse_proper_duration_seconds": emission_duration_proper_s or 0.0,
            "post_exit_hull_proper_time_seconds": (
                post_exit_leg["proper_time_seconds"] if post_exit_leg is not None else 0.0
            ),
            "emitter_to_witness_range_km": effective_emitter_range_km if witness_lookback_years is not None else None,
            "ordinary_light_flight_time_seconds": light_flight_s if witness_lookback_years is not None else None,
            "emission_to_witness_reception_interval_seconds": light_flight_s if witness_lookback_years is not None else None,
            "hull_exit_to_witness_reception_interval_seconds": (
                post_exit_duration_s + emission_pulse_coordinate_duration_s + light_flight_s
                if witness_lookback_years is not None else None
            ),
            "photon_arrival_residual_seconds_decimal": photon_residual_s,
            "throat_hull_proper_time_seconds": proper_crossing_s,
            "throat_A_clock_advance_seconds": throat_clock_advance_s,
            "required_mouth_clock_lag_years": lag_needed_years,
            "required_mouth_clock_lag_years_decimal": (
                str(lag_decimal_years) if lag_decimal_years is not None else None
            ),
            "mouth_lag_float_rounding_error_seconds": (
                float((Decimal(str(lag_needed_years))-lag_decimal_years)*JULIAN_YEAR_D)
                if lag_decimal_years is not None else None
            ),
            "visibility_assumption": "The hull is optically detectable or emits/reflects photons at the emission event; radiative transfer is not modeled.",
            "interpretation": (
                "The hull follows the modeled post-exit segment and finite emission pulse; a final-pulse photon reaches the chosen witness event."
                if resolved_witness_lookback_years is not None and post_exit_leg is not None else
                "The hull exits and emits at the same event; future-directed photons reach the chosen witness event."
                if resolved_witness_lookback_years is not None else
                "No witness event was supplied; lookback_years specifies the emission epoch, and any modeled post-exit segment begins earlier."
            ),
        },
        "source_emission_recoil_screen": emission_recoil_screen,
        "source_emission_global_segment": global_emission_pulse_segment,
        "post_exit_route_planning": post_exit_route_planning,
        "destination_intercept": {
            "status": (
                str(null_intercept["status"])
                if null_intercept is not None
                else "unresolved_missing_spatial_events_and_observer_worldline"
            ),
            "hull_exit_event": {
                "time_coordinate_specified": True,
                "position_in_destination_exterior_km": (
                    list(post_exit_start_position_km)
                    if post_exit_start_position_km is not None
                    else list(emitter_position_km) if post_exit_duration_s == 0.0 and emitter_position_km is not None
                    else None
                ),
                "outward_normal_unit_vector_in_coordinate_frame": list(exit_normal),
                "local_outward_tangent_km_s_in_exit_frame": list(local_outward_velocity),
                "exit_frame_velocity_km_s_in_coordinate_frame": list(exit_frame_velocity),
                "initial_velocity_km_s_in_coordinate_frame": list(post_exit_initial_velocity),
                "initial_four_velocity_over_c": [
                    initial_gamma,
                    *(initial_gamma * v / (C/1000.0) for v in post_exit_initial_velocity),
                ],
            },
            "coordinate_frame_contract": {
                "frame_name": coordinate_frame_name,
                "post_exit_cartesian_frame": "one inertial Cartesian chart; all event positions, hazard states, velocities, and the outward-normal vector use these axes",
                "throat_to_exterior_map": "exit position is identified directly; local tangent is Lorentz-boosted by the supplied exit-frame velocity; tetrad orientation and matching remain assumptions, not a dynamic wormhole solution",
                "obstacle_states": "Earth center moves at its supplied constant velocity; additional spherical hazards move at their supplied constant velocities from the throat-exit event",
                "Earth_site_transform": "no Earth-orientation or inertial-to-Earth-fixed transformation is applied",
            },
            "post_exit_hull_leg": post_exit_leg,
            "witness_event": {
                "time_coordinate_specified": resolved_witness_lookback_years is not None,
                "worldline_model": (
                    "constant-velocity inertial line in the same flat Cartesian frame"
                    if null_intercept is not None else None
                ),
                "velocity_km_s": list(witness_velocity_km_s) if null_intercept is not None else None,
                "position_at_hull_emission_event_km": (
                    list(witness_position_at_emission_km)
                    if witness_position_at_emission_km is not None else None
                ),
            },
            "null_intercept_calculation": null_intercept,
            "apparent_track_at_witness": apparent_track,
            "collision_clearance": earth_clearance,
            "spherical_hazard_clearances": collision_clearances,
            "collision_gate_status": (
                "rejected_by_spherical_collision_envelope"
                if collision_rejects_candidate else
                "passes_only_spherical_clearance_screen"
                if all_hazards_clear else
                "not_demonstrated_pulse_clearance_bound_failed"
                if pulse_clearance_unresolved else
                "not_demonstrated_no_spherical_hazards"
                if global_emission_pulse_segment is not None and not collision_hazards else
                "not_demonstrated"
            ),
            "scope": (
                "The null ray intersects a constant-velocity witness in flat space. The optional post-exit hull leg is a quintic-Hermite candidate with zero endpoint acceleration and a certified timelike curve; gravity, Earth rotation/orbit, mouth-frame mapping, hull attitude, and finite emission geometry remain omitted."
                if null_intercept is not None and post_exit_leg is not None else
                "The null ray intersects a constant-velocity witness in flat space; gravity, Earth rotation/orbit, acceleration, hull attitude, and finite emitting surface remain omitted."
                if null_intercept is not None else
                "The optional post-exit hull leg is a quintic-Hermite flat-spacetime candidate with zero endpoint acceleration and a certified timelike curve; it is not matched to a destination mouth tetrad or gravity field."
                if post_exit_leg is not None
                else "No spatial null-intercept calculation was possible from a scalar range alone."
            ),
            "scalar_range_is_not_a_geometric_intercept": None if null_intercept is not None else (
                "emitter_range_km supplies only a path-length/time constraint; it does not specify the emitter-to-witness direction, the exit position, or whether a future-directed null geodesic intersects the witness worldline"
            ),
            "required_to_close": [
                *([] if null_intercept is not None else [
                    "historical hull-exit event position and tetrad in the destination exterior",
                    "witness worldline or event position and four-velocity in the same frame",
                ]),
                "gravity-aware propagation and the actual accelerated observer worldline",
                "gravity-aware propagation and mouth-to-exterior tetrad matching",
                *([] if post_exit_leg is not None else [
                    "continuous post-exit hull trajectory from throat exit to emission event",
                ]),
                "obstacle clearance and control/force budget along the exterior hull segment",
                "hull attitude and finite emitting surface geometry",
                "predicted angular track, spectrum, flux, and duration at the witness",
            ],
            "zoom_interpretation": (
                "A selected spacetime address has both place and time; this candidate hull leg and flat-space ray solve connect the exit, emission, and witness events, but do not establish a physical spacetime route."
                if null_intercept is not None and post_exit_leg is not None else
                "A selected spacetime address has both place and time; this flat-space ray check tests one witness intersection but does not calculate the hull's route to the emission event."
                if null_intercept is not None else
                "A selected spacetime address has both place and time; this candidate post-exit leg connects a throat exit to an emitting event, but no witness intercept was supplied."
                if post_exit_leg is not None
                else "A selected spacetime address has both place and time; matching its date and a scalar light-travel time does not navigate the hull to that address or prove a witness sees it."
            ),
        },
        "throat": {
            "metric": "ds^2 = -c^2 dt_A^2 + dl^2 + (l^2 + r0^2) dOmega^2",
            "shape_function": "b(r)=r0^2/r, redshift function Phi=0",
            "radius_m": throat_radius_m,
            "minimum_clear_diameter_m": 2.0 * throat_radius_m,
            "matched_mouth_areal_radius_m": selected_mouth_radius_m,
            "timed_path_proper_length_m": throat_length_m,
            "mouth_to_mouth_proper_length_m": 2.0 * math.sqrt(
                selected_mouth_radius_m**2 - throat_radius_m**2
            ),
            "matching_surface_at_l_plus_minus_throat_length_over_2": True,
            "hull_center_worldline": {
                "parameter": "throat proper time tau",
                "mouth_orientation": "B entry at ell=-L/2; A exit at ell=+L/2",
                "ell_of_tau": "ell(tau) = -L/2 + gamma*v*tau",
                "t_A_of_tau": "t_A(tau) = gamma*tau",
                "domain_proper_time_s": [0.0, proper_crossing_s],
                "domain_throat_coordinate_time_s": [0.0, throat_clock_advance_s],
                "local_radial_speed_m_s": local_speed,
                "lorentz_factor": gamma,
                "proper_time_normalization": "-c^2*(dt_A/dtau)^2 + (dell/dtau)^2 = -c^2",
                "curve_type": "exact radial timelike geodesic in the static ultrastatic Ellis throat",
                "scope": "local throat segment only; exterior mouth histories, their junction dynamics, and the global event-identification atlas are not joined into a complete spacetime solution",
            },
            "static_boundary_tangent_match": {
                "assumption": "each exterior mouth is instantaneously at rest in a local Minkowski frame; time and outward-normal tetrads are identified with the static Ellis boundary; zero angular velocity",
                "entry_B": {
                    "external_four_velocity_over_c_in_(time,outward_normal)": [
                        gamma,
                        -gamma * local_speed / C,
                    ],
                    "throat_four_velocity_over_c_in_(time,outward_normal)": [
                        gamma,
                        -gamma * local_speed / C,
                    ],
                    "external_radial_velocity_m_s": -local_speed,
                    "throat_dell_dtau_m_s": gamma * local_speed,
                    "tangent_continuous_under_assumed_tetrad_map": True,
                },
                "exit_A": {
                    "external_four_velocity_over_c_in_(time,outward_normal)": [
                        gamma,
                        gamma * local_speed / C,
                    ],
                    "throat_four_velocity_over_c_in_(time,outward_normal)": [
                        gamma,
                        gamma * local_speed / C,
                    ],
                    "external_radial_velocity_m_s": local_speed,
                    "throat_dell_dtau_m_s": gamma * local_speed,
                    "tangent_continuous_under_assumed_tetrad_map": True,
                },
                "normalized_four_velocity_identity": "-(u_hat0/c)^2 + (u_hatn/c)^2 = -gamma^2 + gamma^2*(v/c)^2 = -1",
                "mouth_profile": mouth_profile,
                "moving_B_endpoint_velocity_fraction_of_c": 0.0,
                "moving_B_endpoint_acceleration_matches_static_join": mouth_profile == "c2",
                "profile_join_note": (
                    "B-mouth velocity and acceleration vanish at the static join"
                    if mouth_profile == "c2" else
                    "B-mouth velocity vanishes, but its prescribed acceleration steps when joined to the static segment"
                ),
                "scope": "This verifies only local position/tangent kinematics for the static cut-and-paste benchmark. It does not match the accelerated moving-mouth metric or source, Earth-site tetrad, transverse frame twists, or post-exit trajectory.",
            },
            "hull_visible_width_m": hull_width_m,
            "hull_visible_height_m": hull_visible_height_m,
            "conservative_visible_envelope_radius_m": visible_envelope_radius_m,
            "centered_radial_margin_m": throat_radius_m - visible_envelope_radius_m,
            "buried_compartment_clearance": "unknown; the concept drawing gives no below-grade dimensions",
            "proper_crossing_length_m": throat_length_m,
            "local_hull_speed_m_s": local_speed,
            "hull_crossing_proper_time_s": proper_crossing_s,
            "A_mouth_clock_advance_during_throat_s": throat_clock_advance_s,
            **ellis_source(throat_radius_m),
            "smooth_throat_tidal_screen": ellis_radial_tidal_screen(
                throat_radius_m, throat_length_m, transit_seconds, hull_width_m
            ),
            "static_flat_exterior_mouth_junction": static_ellis_flat_mouth_junction(
                throat_radius_m, selected_mouth_radius_m
            ),
            "thin_shell_transverse_impulse_screen": ellis_junction_transverse_impulse_screen(
                throat_radius_m,
                selected_mouth_radius_m,
                hull_width_m,
                local_speed,
            ),
            "two_shell_jacobi_screen": ellis_two_shell_jacobi_screen(
                throat_radius_m,
                throat_length_m,
                transit_seconds,
                hull_width_m,
            ),
            "quantum_inequality_diagnostic": ford_roman_qi_diagnostic(throat_radius_m),
        },
        "mouth_clock_map": {
            "moving_mouth_profile": mouth_profile,
            "relation": "tau_A(exit)=tau_B(entry)+delta_throat_A; at reunion tau_B=T-lag",
            "exit_epoch_relation": "T_exit=T_entry-lag+delta_throat_A",
            "required_clock_lag_years": lag_needed_years,
            "histories": mouth_cases,
        },
        "wormhole_formation_constraint": {
            "model": "finite-formation synchronized zero-offset mouths; profile start is the latest allowed pair-formation event",
            "scope": "formation-date ordering for the standard equal-clock mouth map; nonzero pre-shifted initial data assumes rather than generates the time offset",
            "profiles": formation_cases,
            "mission_candidate_status": (
                "rejected_by_formation_time_gate_for_all_profiles"
                if all_profiles_fail_formation else "not_demonstrated"
            ),
            "unmodeled": "throat formation, historical anchor-mouth trajectory, source footprint, and all other mission gates",
        },
        "mission_viability": {
            "status": (
                "rejected_by_collision_envelope"
                if collision_rejects_candidate else
                "rejected_by_formation_time_gate_for_all_profiles"
                if all_profiles_fail_formation else "not_demonstrated"
            ),
            "gates": {
                "formation_time": (
                    "rejected for all profiles" if all_profiles_fail_formation else
                    "date ordering passes for all profiles only" if all_profiles_pass_formation_screen else
                    "not evaluated or not passed by all profiles"
                ),
                "destination_collision_hazards": collision_status,
                "Earth_clearance": earth_clearance.get("status"),
                "post_exit_timelike": post_exit_leg["status"] if post_exit_leg is not None else "no external leg requested",
                "witness_intercept": null_intercept["status"] if null_intercept is not None else "not geometrically demonstrated",
            },
            "scope": "A sampled hull-envelope intersection with any modeled sphere rejects the candidate; a clear result only passes these local spherical screens. Formation, dynamic spacetime, unmodeled hazards, and observables remain distinct gates.",
        },
        "limits": [
            "The Earth-following mouth must exist and remain traversable at the historical exit event.",
            "The moving-mouth clock histories are prescribed flat-exterior kinematics, not an Einstein-equation solution. The Israel shell output is static and does not supply the stress or dynamics of those accelerated mouths.",
            "The Ellis source is a phantom scalar with wrong-sign kinetic energy; no stable physical source is provided.",
            "The integrated source energy is a static-slice integral, not the spacetime ADM mass or a buildable energy budget.",
            "The smooth-throat screen compares a fixed-angle free-geodesic width example with an initially comoving linearized Jacobi field; neither is a finite rigid-body solution, and the hull is too large relative to the default curvature radius for the linear approximation to certify passage. Structural stress, the dynamic throat junction, moving-mouth tides, full collision screening, and gravity-aware witness-light propagation remain unsolved.",
            "The past exit and ordinary return to the entry event create a chronology loop; no global consistency rule is selected.",
            "The optional post-exit hull segment is a flat-space quintic-Hermite candidate with zero endpoint acceleration; its timelike status is certified by bounding the full velocity curve. Optional Earth clearance uses an enclosing sphere and the visible hull envelope only; terrain, the buried compartment, other obstacles, force limits, gravity, and mouth-frame transport are not solved. The optional constant-velocity Minkowski null intercept omits actual Earth/site motion and finite hull emission geometry.",
            "The optional finite photon-rocket pulse is integrated locally and Lorentz-boosted into the exterior flat chart; a relativistic speed-bound clearance can certify only the listed constant-velocity spheres and stated hull envelope when the lower bound is positive. No post-pulse route, throat recoil transfer, finite-body force model, or chronology-consistency condition is solved.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lookback-years", type=float, default=2030.964437489177,
                        help="emission-event lookback when no witness event is supplied")
    parser.add_argument("--witness-lookback-years", type=float,
                        help="witness reception-event lookback; emission and throat-exit dates are derived from light and post-exit flight times")
    parser.add_argument("--pair-formation-lookback-years", type=float,
                        help="assumed synchronized throat-pair formation age before the control event; checked against each mouth-history start")
    parser.add_argument("--emitter-range-km", type=float, default=0.0,
                        help="scalar photon path length used when no emitter/witness positions are supplied")
    parser.add_argument("--emitter-position-km", type=float, nargs=3, metavar=("X", "Y", "Z"),
                        help="emitting hull-element position at the emission event in a shared flat Cartesian frame")
    parser.add_argument("--witness-position-km", type=float, nargs=3, metavar=("X", "Y", "Z"),
                        help="witness position at the final emission event; with a finite pulse, this is after the pulse's modeled displacement")
    parser.add_argument("--witness-velocity-km-s", type=float, nargs=3, default=(0.0, 0.0, 0.0), metavar=("VX", "VY", "VZ"),
                        help="constant witness velocity in that frame; used only with both positions")
    parser.add_argument("--post-exit-duration-seconds", type=float, default=0.0,
                        help="coordinate time for a smooth external hull leg from the throat-exit event to the emission event")
    parser.add_argument("--plan-hazard-avoiding-route", action="store_true",
                        help="search a fixed-duration post-exit route using compact C2 detours around supplied spherical hazards; requires a post-exit leg")
    parser.add_argument("--post-exit-start-position-km", type=float, nargs=3, metavar=("X", "Y", "Z"),
                        help="throat-exit event position in the declared shared Cartesian frame")
    parser.add_argument("--post-exit-end-velocity-km-s", type=float, nargs=3, default=(0.0, 0.0, 0.0), metavar=("VX", "VY", "VZ"),
                        help="emitter-point velocity at the end of the post-exit quintic-Hermite segment")
    parser.add_argument("--earth-center-position-km", type=float, nargs=3, metavar=("X", "Y", "Z"),
                        help="Earth center in the same Cartesian frame; enables conservative spherical-body clearance")
    parser.add_argument("--earth-radius-km", type=float, default=6378.137,
                        help="enclosing spherical Earth radius (default: WGS84 equatorial radius)")
    parser.add_argument("--terrain-margin-m", type=float, default=0.0,
                        help="extra radial clearance beyond the spherical Earth surface")
    parser.add_argument("--spherical-hazard", type=float, nargs=7, action="append",
                        metavar=("X", "Y", "Z", "VX", "VY", "VZ", "R"),
                        help="additional spherical obstacle: center km at throat exit, constant velocity km/s, radius km; repeat per obstacle")
    parser.add_argument("--exit-normal-unit-vector", type=float, nargs=3, default=(1.0, 0.0, 0.0), metavar=("NX", "NY", "NZ"),
                        help="throat's outward exit normal in the shared coordinate frame; default +x")
    parser.add_argument("--earth-velocity-km-s", type=float, nargs=3, default=(0.0, 0.0, 0.0), metavar=("VX", "VY", "VZ"),
                        help="Earth-center velocity at throat exit in the shared frame; used for both collision motion and mouth-frame boost")
    parser.add_argument("--throat-exit-frame-velocity-km-s", type=float, nargs=3, metavar=("VX", "VY", "VZ"),
                        help="explicit local throat-exit frame velocity; defaults to --earth-velocity-km-s")
    parser.add_argument("--coordinate-frame-name", default="user-specified shared inertial Cartesian frame",
                        help="label the frame used for positions, normal, and velocities (for example Sun-centered ICRF/J2000)")
    parser.add_argument("--emission-source-rest-mass-kg", type=float,
                        help="optional local rest mass of the emitting craft plus energy store; pair with --emitted-cone-energy-j")
    parser.add_argument("--emitted-cone-energy-j", type=float,
                        help="optional photon energy emitted in the source rest frame into a uniform cone; pair with --emission-source-rest-mass-kg")
    parser.add_argument("--emission-cone-half-angle-deg", type=float, default=10.0,
                        help="uniform emission-cone half-angle used for the optional local recoil screen (default: 10 degrees)")
    parser.add_argument("--emission-duration-proper-s", type=float,
                        help="optional pulse duration in the emitter's proper time; integrates a local continuous photon-rocket segment")
    parser.add_argument("--emission-pulse-envelope", choices=("sin2", "constant"), default="sin2",
                        help="proper-time power profile for a finite pulse; sin2 tapers power smoothly to zero at both ends (default), constant is a sharp-edged comparison")
    parser.add_argument("--emission-beam-axis-unit-vector", type=float, nargs=3, default=(1.0, 0.0, 0.0), metavar=("NX", "NY", "NZ"),
                        help="emission-cone propagation axis in the emitter's initial rest-frame basis; used to boost recoil into the chart (default +x)")
    parser.add_argument("--throat-radius-m", type=float, default=5.0)
    parser.add_argument("--throat-length-m", type=float, default=10.0)
    parser.add_argument("--hull-width-m", type=float, default=7.224)
    parser.add_argument("--hull-visible-height-m", type=float, default=2.134)
    parser.add_argument("--mouth-radius-m", type=float, help="static Ellis-to-flat junction radius; must match throat_length_m endpoints (default: sqrt(r0^2 + (throat_length_m/2)^2))")
    parser.add_argument("--transit-seconds", type=float, default=300.0)
    parser.add_argument("--beta-max", type=float, nargs="+", default=[0.8, 0.99])
    parser.add_argument(
        "--mouth-profile", choices=("sin", "c2"), default="sin",
        help="prescribed moving-mouth velocity history; c2 has zero endpoint acceleration",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if (args.emission_source_rest_mass_kg is None) != (args.emitted_cone_energy_j is None):
        parser.error("--emission-source-rest-mass-kg and --emitted-cone-energy-j must be supplied together")
    result = build(
        args.lookback_years,
        args.throat_radius_m,
        args.throat_length_m,
        args.hull_width_m,
        args.transit_seconds,
        tuple(args.beta_max),
        args.hull_visible_height_m,
        args.mouth_radius_m,
        args.witness_lookback_years,
        args.emitter_range_km,
        args.mouth_profile,
        args.pair_formation_lookback_years,
        tuple(args.emitter_position_km) if args.emitter_position_km is not None else None,
        tuple(args.witness_position_km) if args.witness_position_km is not None else None,
        tuple(args.witness_velocity_km_s),
        args.post_exit_duration_seconds,
        tuple(args.post_exit_start_position_km) if args.post_exit_start_position_km is not None else None,
        tuple(args.post_exit_end_velocity_km_s),
        tuple(args.earth_center_position_km) if args.earth_center_position_km is not None else None,
        args.earth_radius_km,
        args.terrain_margin_m,
        tuple(tuple(hazard) for hazard in (args.spherical_hazard or [])),
        tuple(args.exit_normal_unit_vector),
        tuple(args.earth_velocity_km_s),
        tuple(args.throat_exit_frame_velocity_km_s)
        if args.throat_exit_frame_velocity_km_s is not None else None,
        args.coordinate_frame_name,
        args.emission_source_rest_mass_kg,
        args.emitted_cone_energy_j,
        args.emission_cone_half_angle_deg,
        args.emission_duration_proper_s,
        tuple(args.emission_beam_axis_unit_vector),
        args.emission_pulse_envelope,
        args.plan_hazard_avoiding_route,
    )
    output = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
