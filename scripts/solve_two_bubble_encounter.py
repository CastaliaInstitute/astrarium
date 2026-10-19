#!/usr/bin/env python3
"""Scale the published symmetric CTG centerline through a 1+1 target event.

This is a reproducible kinematic encounter calculation for the explicit
Shoshany-Snodgrass profile. It does not add Earth's gravity, solve a 3D
observer intercept, propagate photons, or certify collision clearance.
"""
from __future__ import annotations

import argparse
import json
import math


def smooth_step(x: float) -> float:
    """Primitive q^(-1)(x) for q=140 x^3 (1-x)^3."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    return 35*x**4 - 84*x**5 + 70*x**6 - 20*x**7


def second_primitive(x: float) -> float:
    """Second primitive q^(-2)(x), with q^(-2)(1)=1/2."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return x - 0.5
    return 7*x**5 - 14*x**6 + 10*x**7 - 2.5*x**8


def simpson(function, left: float, right: float, intervals: int = 4096) -> float:
    if intervals % 2:
        intervals += 1
    step = (right - left) / intervals
    total = function(left) + function(right)
    total += 4.0 * sum(function(left + i*step) for i in range(1, intervals, 2))
    total += 2.0 * sum(function(left + i*step) for i in range(2, intervals, 2))
    return total * step / 3.0


def calculate_encounter(
    target_time_years: float = -2030.9994123053214,
    target_z_lightyears: float = 0.20175011373519103,
    frame_speed: float = 0.75,
    alpha: float = 10.0,
    omega: float = 0.95,
    support_radius_km: float = 1.0,
    sidestep_duration_years: float = 0.8,
    sidestep_factor: float = 2.0,
    support_fade_margin_factor: float = 0.0,
) -> dict[str, float | str]:
    """Fit a target event on the source's explicit 1+1 centerline.

    The target must be in the past of the departure event. The construction is
    evaluated first with T2=1, then uniformly scaled to match the target time.
    The target is restricted to the return rest-frame-transition leg, where the
    published centerline has an analytic expression. The optional transverse
    sidestep is a candidate lift to the paper's general 3D path ansatz; this
    function does not instantiate that metric or integrate its 3D geodesic.
    """
    u = frame_speed
    if not 0.0 < u < 1.0:
        raise ValueError("frame_speed must be between 0 and 1")
    if alpha <= 0.0 or not 0.0 < omega < 1.0:
        raise ValueError("alpha must be positive and omega must be in (0, 1)")
    if target_time_years >= 0.0:
        raise ValueError("target_time_years must be before the departure event")
    if support_radius_km <= 0.0 or sidestep_duration_years <= 0.0 or sidestep_factor <= 0.0 or support_fade_margin_factor < 0.0:
        raise ValueError("support radius and sidestep values must be positive; fade margin cannot be negative")

    gamma = 1.0 / math.sqrt(1.0 - u*u)
    # Normalize T2=1 year. Lengths are in light-years and c=1 ly/year.
    t2_unit = 1.0
    t1 = omega * t2_unit
    t_mid = 0.5 * t1
    k1 = (alpha + 2.0) * u / t1
    k2 = alpha * u / t1

    def outgoing_z(t: float) -> float:
        return (
            k1 * t_mid**2 * second_primitive(t / t_mid)
            - k2 * (t1 - t_mid)**2 * second_primitive((t - t_mid) / (t1 - t_mid))
        )

    z2 = outgoing_z(t2_unit)
    average_speed = u * (1.0 + omega * (alpha - 1.0) / 4.0)
    finish_ratio = (2.0*average_speed - u*(1.0 + average_speed**2)) / (average_speed - u)
    if finish_ratio >= 0.0:
        raise ValueError("these parameters do not produce a past-closing symmetric loop")
    if not u > 2.0*average_speed / (1.0 + average_speed**2):
        raise ValueError("the symmetric CTC threshold is not satisfied")

    # Lorentz-transform the end of the first leg into the return frame S-hat.
    hat_t0 = gamma * (t2_unit - u*z2)
    hat_z0 = gamma * (z2 - u*t2_unit)
    hat_t2 = gamma * finish_ratio
    hat_duration = hat_t2 - hat_t0
    hat_first_leg_duration = omega * hat_duration
    half_transition = 0.5 * hat_first_leg_duration
    if hat_duration <= 0.0:
        raise ValueError("return-frame duration is not positive")
    hat_k1 = (alpha + 2.0) * u / hat_first_leg_duration
    hat_k2 = alpha * u / hat_first_leg_duration

    def return_position(fraction: float) -> tuple[float, float]:
        """Return centerline (t,z) in S at fraction of full S-hat duration."""
        elapsed = fraction * hat_duration
        hat_t = hat_t0 + elapsed
        hat_z = (
            hat_z0
            - hat_k1 * half_transition**2 * second_primitive(elapsed / half_transition)
            + hat_k2 * half_transition**2 * second_primitive((elapsed - half_transition) / half_transition)
        )
        return gamma * (hat_t + u*hat_z), gamma * (hat_z + u*hat_t)

    # Search the first smooth return transition [0, omega] for a point on the
    # same target ray in the t-z diagram. Only roots with t<0 scale to T2>0.
    target_ratio = target_z_lightyears / target_time_years

    def residual(fraction: float) -> tuple[float, float, float]:
        t, z = return_position(fraction)
        return z - target_ratio*t, t, z

    roots: list[float] = []
    samples = 4096
    left = 0.0
    f_left, t_left, _ = residual(left)
    for index in range(1, samples + 1):
        right = omega * index / samples
        f_right, t_right, _ = residual(right)
        if t_left < 0.0 and t_right < 0.0 and f_left*f_right < 0.0:
            lo, hi = left, right
            flo = f_left
            for _ in range(64):
                mid = 0.5*(lo + hi)
                f_mid, t_mid_value, _ = residual(mid)
                if t_mid_value >= 0.0:
                    break
                if flo*f_mid <= 0.0:
                    hi = mid
                else:
                    lo, flo = mid, f_mid
            roots.append(0.5*(lo + hi))
        left, f_left, t_left = right, f_right, t_right
    if not roots:
        raise ValueError("the selected target ray does not intersect the return transition")

    # The late crossing is closest to the stationary return and is the one used
    # for the reproducible collision example.
    encounter_fraction = max(roots)
    target_t_unit, target_z_unit = return_position(encounter_fraction)
    scale_years = target_time_years / target_t_unit
    if scale_years <= 0.0:
        raise ValueError("target event implies a nonpositive construction scale")
    outgoing_unit_lapse_years = omega * scale_years
    return_unit_lapse_years = omega * hat_duration * scale_years
    if sidestep_duration_years > outgoing_unit_lapse_years:
        raise ValueError("outgoing transverse ramp must finish before the outgoing rest-frame transition")
    if sidestep_duration_years > return_unit_lapse_years:
        raise ValueError("return transverse ramp must finish before the return rest-frame transition")
    hit_t = target_t_unit * scale_years
    hit_z = target_z_unit * scale_years

    # At this fraction the traveler is still in the return RFT's first phase,
    # where proper time equals d(hat t). Compute the hatted center velocity.
    elapsed_unit = encounter_fraction * hat_duration
    q1_arg = elapsed_unit / half_transition
    q2_arg = (elapsed_unit - half_transition) / half_transition
    hat_velocity = (
        -hat_k1 * half_transition * smooth_step(q1_arg)
        + hat_k2 * half_transition * smooth_step(q2_arg)
    )
    dt_dproper = gamma * (1.0 + u*hat_velocity)
    dz_dproper = gamma * (hat_velocity + u)
    coordinate_velocity = dz_dproper / dt_dproper

    # Proper time to the encounter: outgoing leg through its lapse transition,
    # then the elapsed S-hat time on the return leg's first phase.
    t1_scaled = omega * scale_years
    support_radius_ly = support_radius_km * 1000.0 / 9.4607304725808e15
    fade_margin_years = support_fade_margin_factor*support_radius_ly
    transition_span = ((1.0-omega)*scale_years - u*gamma*support_radius_ly - fade_margin_years)
    transition_end = scale_years - u*gamma*support_radius_ly - fade_margin_years
    if transition_span == 0.0:
        raise ValueError("the outgoing lapse transition has no positive duration")
    proper_transition = transition_span * simpson(
        lambda fraction: math.sqrt(1.0 - u*u*smooth_step(fraction)**2),
        0.0,
        1.0,
    )
    # After the compact field vanishes at transition_end, the traveler coasts
    # inertially at speed u in S until the first-leg endpoint T2.
    flat_coast = (u*gamma*support_radius_ly + fade_margin_years) / gamma
    proper_first = t1_scaled + proper_transition + flat_coast
    return_elapsed_years = elapsed_unit * scale_years
    proper_age_at_target = proper_first + return_elapsed_years

    # In the source's example, the return sidestep is complete by this event.
    # Return its actual source-profile x offset for audit rather than assuming it.
    x_progress = return_elapsed_years / sidestep_duration_years
    x_offset_ly = sidestep_factor*support_radius_ly * (1.0 - smooth_step(x_progress))

    return {
        "model": ("explicit symmetric two-bubble CTG centerline, one-axis target projection"
                  if abs(sidestep_factor-2.0) < 1e-12 and support_fade_margin_factor == 0.0 else
                  "explicit two-bubble CTG with parameterized smooth transverse-path and support-fade margins"),
        "source": "Shoshany and Snodgrass (2024), compact-support profile and general smooth center-path construction",
        "target_event_time_S_years": target_time_years,
        "target_event_z_S_lightyears": target_z_lightyears,
        "target_coordinate_residual_years": hit_t - target_time_years,
        "target_coordinate_residual_lightyears": hit_z - target_z_lightyears,
        "return_transition_fraction": encounter_fraction,
        "frame_speed_U": u,
        "average_bubble_speed_V": average_speed,
        "alpha": alpha,
        "omega": omega,
        "support_radius_km": support_radius_km,
        "sidestep_factor": sidestep_factor,
        "support_fade_margin_factor": support_fade_margin_factor,
        "support_fade_margin_years": fade_margin_years,
        "support_fade_margin_microseconds": fade_margin_years*31557600.0*1e6,
        "outgoing_support_end_S_years": transition_end,
        "outgoing_support_end_offset_before_T2_km": support_radius_km*(u*gamma+support_fade_margin_factor),
        "return_support_end_hat_years": gamma*finish_ratio*scale_years - u*gamma*support_radius_ly - fade_margin_years,
        "return_support_end_offset_before_hat_T2_km": support_radius_km*(u*gamma+support_fade_margin_factor),
        "sidestep_amplitude_km": support_radius_km*sidestep_factor,
        "support_boundary_margin_km_at_parallel_centerline_crossing": support_radius_km*(sidestep_factor-2.0),
        "T2_first_leg_years": scale_years,
        "first_leg_separation_lightyears": average_speed*scale_years,
        "loop_finish_time_S_years": finish_ratio*scale_years,
        "traveler_proper_time_at_target_years": proper_age_at_target,
        "return_frame_elapsed_at_target_years": return_elapsed_years,
        "outgoing_initial_unit_lapse_duration_years": outgoing_unit_lapse_years,
        "return_initial_unit_lapse_duration_years": return_unit_lapse_years,
        "hat_velocity_z_at_target_fraction_c": hat_velocity,
        "dS_time_dproper_time_at_target": dt_dproper,
        "dS_position_dproper_time_fraction_c": dz_dproper,
        "S_coordinate_velocity_z_fraction_c": coordinate_velocity,
        "return_centerline_x_at_target_lightyears": x_offset_ly,
        "return_centerline_y_at_target_lightyears": 0.0,
        "return_sidestep_duration_years": sidestep_duration_years,
        "return_sidestep_complete_at_target": return_elapsed_years >= sidestep_duration_years,
        "return_bubble_x_offset_at_target_lightyears": x_offset_ly,
        "return_bubble_x_offset_at_target_km": x_offset_ly*9.4607304725808e12,
        "transverse_path_status": "prescribed smooth candidate path; full 3+1 metric and geodesic not computed",
        "full_3d_metric_instantiated": False,
        "full_3d_geodesic_integrated": False,
        "interpretation": "The chosen one-axis target event is an Earth-center event; coincidence is a collision, not a safe sighting. No Earth gravity, witness, photon, finite-hull, or hazard propagation is included.",
    }


def sample_worldline(result: dict[str, float | str], count: int = 1200) -> dict[str, list[float]]:
    """Sample the 1+1 centerline, proper time, and prescribed 3D path extension."""
    u = float(result["frame_speed_U"])
    alpha = float(result["alpha"])
    omega = float(result["omega"])
    T2 = float(result["T2_first_leg_years"])
    gamma = 1.0 / math.sqrt(1.0-u*u)
    V = float(result["average_bubble_speed_V"])
    T1 = omega*T2
    support_radius_km = float(result.get("support_radius_km", 1.0))
    support_radius_ly = support_radius_km * 1000.0 / 9.4607304725808e15
    sidestep_duration_years = float(result.get("return_sidestep_duration_years", 0.8))
    midpoint = 0.5*T1
    k1 = (alpha+2.0)*u/T1
    k2 = alpha*u/T1

    def out_z(t: float) -> float:
        return k1*midpoint**2*second_primitive(t/midpoint) - k2*midpoint**2*second_primitive((t-midpoint)/midpoint)

    out_t = [T2*i/(count-1) for i in range(count)]
    out_pos = [out_z(t) for t in out_t]

    # Proper time on the first leg follows the paper's lapse transition.
    gamma_u_radius = u * gamma * support_radius_ly
    fade_margin_years = float(result.get("support_fade_margin_years", 0.0))
    out_transition_end = T2 - gamma_u_radius - fade_margin_years
    out_transition_start = T1
    def outgoing_dtaudt(t: float) -> float:
        if t <= out_transition_start:
            return 1.0
        if t >= out_transition_end:
            return 1.0/gamma
        q = smooth_step((t-out_transition_start)/(out_transition_end-out_transition_start))
        return math.sqrt(max(0.0, 1.0-u*u*q*q))

    out_tau = [0.0]
    for i in range(1, count):
        dt = out_t[i]-out_t[i-1]
        out_tau.append(out_tau[-1] + 0.5*dt*(outgoing_dtaudt(out_t[i-1])+outgoing_dtaudt(out_t[i])))

    # Recreate the unit-scale return transformation and apply the solved scale.
    z2_unit = V
    finish_ratio = float(result["loop_finish_time_S_years"])/T2
    hat_t0_unit = gamma*(1.0-u*z2_unit)
    hat_z0_unit = gamma*(z2_unit-u)
    hat_t2_unit = gamma*finish_ratio
    duration_unit = hat_t2_unit-hat_t0_unit
    first_duration_unit = omega*duration_unit
    half = first_duration_unit/2.0
    hk1 = (alpha+2.0)*u/first_duration_unit
    hk2 = alpha*u/first_duration_unit
    ret_t, ret_z, ret_x, ret_hat_elapsed = [], [], [], []
    sidestep_duration_unit = sidestep_duration_years / T2
    for i in range(count):
        f=i/(count-1)
        elapsed=f*duration_unit
        ht=hat_t0_unit+elapsed
        hz=hat_z0_unit-hk1*half**2*second_primitive(elapsed/half)+hk2*half**2*second_primitive((elapsed-half)/half)
        ret_t.append(gamma*(ht+u*hz)*T2)
        ret_z.append(gamma*(hz+u*ht)*T2)
        ret_hat_elapsed.append(elapsed*T2)
        # The paper's transverse support displacement, expressed in the
        # exterior frame. x is unchanged by the z-directed Lorentz boost.
        ret_x.append(float(result.get("sidestep_factor", 2.0))*support_radius_ly*(1.0-smooth_step(elapsed/sidestep_duration_unit))
                     if elapsed < sidestep_duration_unit else 0.0)

    return_phase_end = omega*duration_unit*T2
    return_transition_end = duration_unit*T2 - gamma_u_radius - fade_margin_years
    def return_dtaudthat(elapsed: float) -> float:
        if elapsed <= return_phase_end:
            return 1.0
        if elapsed >= return_transition_end:
            return 1.0/gamma
        q = smooth_step((elapsed-return_phase_end)/(return_transition_end-return_phase_end))
        return math.sqrt(max(0.0, 1.0-u*u*q*q))

    ret_tau = [out_tau[-1]]
    for i in range(1, count):
        dhat = ret_hat_elapsed[i]-ret_hat_elapsed[i-1]
        ret_tau.append(ret_tau[-1] + 0.5*dhat*(return_dtaudthat(ret_hat_elapsed[i-1])+return_dtaudthat(ret_hat_elapsed[i])))

    finish = float(result["loop_finish_time_S_years"])
    closure_t = [finish+(0.0-finish)*i/(count-1) for i in range(count)]
    closure_z = [0.0]*count
    closure_x = [0.0]*count
    out_x = [float(result.get("sidestep_factor", 2.0))*support_radius_ly*smooth_step(t/sidestep_duration_years)
             if t < sidestep_duration_years else float(result.get("sidestep_factor", 2.0))*support_radius_ly for t in out_t]
    closure_tau = [ret_tau[-1] + t-finish for t in closure_t]
    return {"outbound_t":out_t,"outbound_tau":out_tau,"outbound_x":out_x,"outbound_z":out_pos,
            "return_t":ret_t,"return_tau":ret_tau,"return_x":ret_x,"return_z":ret_z,
            "closure_t":closure_t,"closure_tau":closure_tau,"closure_x":closure_x,"closure_z":closure_z}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-time-years", type=float, default=-2030.9994123053214)
    parser.add_argument("--target-z-lightyears", type=float, default=0.20175011373519103)
    parser.add_argument("--frame-speed", type=float, default=0.75)
    parser.add_argument("--alpha", type=float, default=10.0)
    parser.add_argument("--omega", type=float, default=0.95)
    parser.add_argument("--sidestep-factor", type=float, default=2.0,
                        help="sidestep amplitude in units of the support radius (2 reproduces the source example)")
    parser.add_argument("--support-fade-margin-factor", type=float, default=0.0,
                        help="fade each compact support this many r2/c before the source endpoint (0 reproduces it)")
    args = parser.parse_args()
    print(json.dumps(calculate_encounter(
        target_time_years=args.target_time_years,
        target_z_lightyears=args.target_z_lightyears,
        frame_speed=args.frame_speed,
        alpha=args.alpha,
        omega=args.omega,
        sidestep_factor=args.sidestep_factor,
        support_fade_margin_factor=args.support_fade_margin_factor,
    ), indent=2))


if __name__ == "__main__":
    main()
