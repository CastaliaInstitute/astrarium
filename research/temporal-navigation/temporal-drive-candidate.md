# A continuous-worldline reference model for temporal navigation

## Moving-mouth traversable wormhole

**Status:** Conditional general-relativistic reference model for simulation design. This is a synthesis of established theoretical work, not a new wormhole solution, an engineering proposal, or evidence that time travel is physically realizable.

## Abstract

We specify a candidate mechanism for a traveler to reach an earlier exterior epoch while maintaining a continuous, future-directed timelike worldline: passage through a traversable wormhole whose mouths have acquired a relative clock offset. The traveler crosses a finite throat in finite proper time. The earlier exterior date is produced by the spacetime's causal structure and mouth identification, not by reversing a numerical integrator or assigning a new date to the vehicle. A closed timelike curve forms only if the wormhole time offset exceeds the duration of a return path through the exterior. This construction is conditional on a traversable throat and its supporting stress-energy; in classical Einstein gravity, the usual flare-out condition entails null-energy-condition violation. Quantum inequalities, backreaction near chronology horizons, formation, stability, and mouth control remain major unresolved problems. We derive the route and collision-check requirements this model imposes on Astrarium and state what its current trajectory planner cannot establish.

## 1. Scope and claim discipline

The model answers a narrow question: **what continuous spacetime route could make a past-directed exterior arrival compatible with increasing traveler proper time?** It does not provide a temporal propulsion law that can be built from known matter, a complete time-dependent Einstein solution for an accelerated wormhole, or a safety case for a real mission.

The reference geometry is the Morris–Thorne class of traversable wormholes. Morris, Thorne, and Yurtsever showed how a wormhole that is assumed to exist and remain traversable can, under relative motion of its mouths, become a time machine. The “assumed to exist” condition is decisive: it is not a known process for creating or stabilizing one. We use that construction to organize a conditional simulation, not as a claim that Astrarium's temporal-drive postulate follows from established physics.

Terminology in this note:

- \(\tau\): traveler proper time, increasing along a massive traveler worldline.
- \(T\): an exterior inertial time coordinate, available separately near the two mouths. In a chronology-violating spacetime there is no single global time function covering the full route.
- \(A,B\): the two wormhole mouths, represented by finite world tubes rather than dimensionless points.
- \(\Delta_{AB}\): the signed, operationally defined exterior clock offset between mouth events identified by traversal through the throat. Positive \(\Delta_{AB}\) means arrival through the throat at \(B\) has an earlier exterior \(T\) than entry at \(A\), after accounting for finite throat transit time.

The route is a single continuous curve on the spacetime manifold. A coordinate chart that covers the exterior near \(A\) need not cover the throat and exterior near \(B\) with one globally meaningful time coordinate. A chart change or nontrivial topology is not a physical discontinuity; a teleportation operation that replaces the event or state without a connecting curve is. Astrarium must render the throat segment as an actual modeled path and retain its proper-time duration. A straight line or instantaneous endpoint swap between mouths is not an acceptable route representation.

Manifold continuity alone is not enough for Astrarium's no-jump requirement. The route must also expose a continuous traveler-epoch map \(E(\tau)\) whose exterior endpoint values agree with the mouth matching map and the ephemeris events used for hazard queries. Any variation of \(E\) through the throat must follow from a specified metric and atlas, not an arbitrary smooth interpolation. If a model cannot provide this continuous map, it fails the product requirement even if its abstract manifold curve is continuous.

## 2. Local throat geometry

In a static, spherically symmetric neighborhood of the throat, use proper radial distance \(\ell\) and write the Morris–Thorne line element as

\[
ds^2=-e^{2\Phi(\ell)}c^2dt_w^2+d\ell^2+r^2(\ell)d\Omega^2,
\qquad d\Omega^2=d\theta^2+\sin^2\theta\,d\phi^2.
\]

Here \(t_w\) is a local throat time coordinate, \(r(\ell)\) is the areal radius, and \(\Phi(\ell)\) is the redshift function. A traversable throat at \(\ell=0\) has a minimum area radius \(r_0=r(0)>0\), with

\[
r'(0)=0,\qquad r''(0)>0,
\]

and finite \(\Phi\) so that no event horizon blocks passage. A physical model must also match this local geometry to two exterior regions, specify mouth world tubes and boundary/junction conditions, and solve for the stress-energy that sources the full geometry. The static metric alone does not encode the moving-mouth clock offset and is not a complete time-machine spacetime.

### Coordinate time inside a throat is not the drive

For a reduced continuity test, one may write a stationary radial chart ansatz

\[
ds^2=-c^2N^2(\ell)\left[dt-\frac{\alpha(\ell)}{c}d\ell\right]^2+d\ell^2+r^2(\ell)d\Omega^2,
\]

where \(N(\ell)>0\) is a lapse and the dimensionless \(\alpha(\ell)\) is a radial shift. For a radial traveler with \(\dot\ell=d\ell/d\tau>0\), proper-time normalization and the local future branch give

\[
\frac{dt}{d\tau}=\frac{\alpha(\ell)}{c}\dot\ell+
\frac{1}{N(\ell)}\sqrt{1+\frac{\dot\ell^2}{c^2}}.
\]

Algebraically, this chart rate becomes negative when

\[
\frac{\alpha(\ell)}{c}\dot\ell<-
\frac{1}{N(\ell)}\sqrt{1+\frac{\dot\ell^2}{c^2}}.
\]

But this is only a **coordinate rate**, not a time-travel criterion. If \(\alpha\) depends only on \(\ell\), define

\[
t'=t-\frac{1}{c}\int_0^\ell\alpha(\xi)d\xi,
\qquad dt'=dt-\frac{\alpha(\ell)}{c}d\ell.
\]

The metric becomes \(ds^2=-c^2N^2(\ell)dt'^2+d\ell^2+r^2(\ell)d\Omega^2\). The shift has been removed and no invariant earlier arrival follows from the negative \(dt/d\tau\). It is mathematically the same coordinate pitfall as the flat-spacetime example below. This ansatz is a useful test that code can integrate smooth coordinates and match endpoints, but it cannot serve as the physical drive model, calculate an observable \(\Delta_{AB}\), or demonstrate a wormhole time machine.

For an actual moving-mouth wormhole, the relative clock offset is a **global matching property** of the two mouth world tubes and the throat identification. It is not a local radial shift. The model must specify the full spacetime atlas, metric on both exteriors and the throat, mouth histories, and the identification map for events and tetrads across the throat. Only then can one compare entry and exit events using clocks synchronized by an explicitly stated exterior protocol and determine whether an exit is earlier in the relevant exterior time. The clock map must be derived from the complete geometry and mouth histories, not fit to a desired result. Before using any ansatz as physics, compute its Einstein tensor and source \(T_{\mu\nu}\), check covariant conservation and energy conditions, and establish regular matching and stability.
The coordinate-artifact issue can be demonstrated without a wormhole. In flat spacetime, start with inertial coordinates \(T,x\) and define \(t=T-\kappa x/c\). For an inertial traveler with \(x=vT\),

\[
\frac{dt}{d\tau}=\gamma\left(1-\kappa\frac{v}{c}\right),\qquad
\gamma=\frac{1}{\sqrt{1-v^2/c^2}}.
\]

At \(v=0.8c\) and \(\kappa=2\), this gives \(dt/d\tau=-1\), even though inertial time \(T\), proper time \(\tau\), and causal order all increase. The transformed metric has \(g^{tt}=(\kappa^2-1)/c^2>0\), so the \(t=\mathrm{constant}\) surfaces are timelike, not valid shared simultaneity slices. The transformation is globally a coordinate relabeling of Minkowski space and creates no time machine. Therefore Astrarium must define external epoch by calibrated exterior clocks and ephemeris event labels, not an arbitrary coordinate. A physical earlier arrival is a relation between those externally anchored events, supported by the full geometry and matching map; a negative coordinate derivative alone is insufficient.

For an idealized, radial, zero-angular-momentum traversal with no thrust, the local geodesic equations follow from the metric. More generally the vehicle four-velocity \(u^\mu=dx^\mu/d\tau\) must satisfy

\[
g_{\mu\nu}u^\mu u^\nu=-c^2,\qquad
u^\nu\nabla_\nu u^\mu=a^\mu,\qquad
u_\mu a^\mu=0,
\]

where \(a^\mu=0\) for free fall and nonzero \(a^\mu\) represents a specified onboard force per unit mass. These equations preserve continuity and normalization, but do not supply the metric, mouth dynamics, or feasible vehicle control. Those must be inputs or solved as a coupled field-and-motion problem.

## 3. Producing an exterior time offset

The standard thought experiment begins with mouths synchronized while adjacent. One mouth is then transported on a relativistic journey and returned, or held at a different gravitational potential. Its accumulated proper time differs from the other mouth's. In an approximately Minkowski exterior, the exact kinematic proper-time difference along a prescribed mouth path is

\[
\Delta\tau_{\rm kin}
=\int_{T_0}^{T_1}\left(1-\sqrt{1-\frac{v_B^2(T)}{c^2}}\right)dT,
\]

where \(v_B(T)\) is the transported mouth's speed in the chosen inertial exterior frame. This is an exact special-relativistic expression for the kinematic proper-time difference in that inertial frame, not a weak-field approximation. In a weak, slowly varying gravitational field with potential \(\varphi\), include the leading gravitational contribution by using

\[
d\tau\simeq dT\left(1+\frac{\varphi}{c^2}-\frac{v^2}{2c^2}\right).
\]

The clock difference is not yet the traversal map. The model must specify how the two mouth clock readings are identified through the interior, the proper-time and redshift accumulated in crossing, and the exterior coordinate transformations at each mouth. Define \(\Delta_{AB}\) from that complete matching map; do not silently equate it to \(\Delta\tau_{\rm kin}\) when acceleration, gravity, or throat dynamics matter.

For the idealized twin-paradox construction, take a short throat and small mouths, initially colocated and at rest in an approximately Minkowski exterior. Let \(T\) be inertial time in the frame where mouth \(A\) remains at rest, and let mouth \(B\) follow a specified round-trip worldline. If their mouth clocks start synchronized and are identified by equal elapsed mouth proper time through the throat, then

\[
\tau_A(T)=T-T_0,\qquad
\tau_B(T)=\int_{T_0}^{T}\sqrt{1-\frac{v_B^2(T')}{c^2}}\,dT'.
\]

At a reunion event \(T_1\), the clock lag is

\[
\Delta_{\rm clock}=\tau_A(T_1)-\tau_B(T_1)
=\int_{T_0}^{T_1}\left(1-\sqrt{1-\frac{v_B^2(T)}{c^2}}\right)dT>0.
\]

In this idealized model the wormhole identification connects mouth events with equal throat-clock readings. An \(A\to B\) crossing at the reunion can emerge at the earlier exterior event where \(B\)'s clock reads \(\tau_A(T_1)\); the exterior date separation is \(\Delta_{\rm clock}\), up to finite throat length, acceleration regions, gravity, and mouth size corrections. The reverse crossing has the opposite offset. This statement depends on the stated identification protocol and inertial frame; a different global identification can give a different map. It is not caused by an interior coordinate shift. The round-trip construction brings the mouths back together to make the clock lag and comparison transparent; creating a CTC also requires an exterior return route whose travel time is less than the lag. This is the canonical special-relativistic limit described by Morris, Thorne, and Yurtsever, not a complete solution for a finite, accelerated, self-gravitating wormhole.

**Worked kinematic scale (idealized).** Let mouth \(B\) travel at constant speed \(0.8c\) for one year of inertial-frame time outbound and one year inbound, with turnaround duration neglected. Then \(\gamma=5/3\), the total exterior duration is 2 years, and

\[
\Delta_{\rm clock}=2\,\mathrm{yr}\left(1-\sqrt{1-0.8^2}\right)=0.8\,\mathrm{yr}\approx 2.52\times10^7\,\mathrm{s}.
\]

The idealized path length is 0.8 light-year each way. This is a large clock lag in a hypothetical scenario, not a propulsion design: the mouth's acceleration, stresses, gravity, finite wormhole geometry, and source of the throat are all omitted. Smooth finite-duration acceleration changes the integral and must be included for any specified worldline. For comparison, the flat-space light-time across 384,400 km is approximately 1.282 s; a timelike exterior return across that separation takes longer. The toy lag greatly exceeds that kinematic lower bound, but this comparison alone proves neither a realizable wormhole nor a globally regular CTC spacetime.

Let a traveler enter mouth \(A\) at exterior event \(p_A\), cross a regular throat in finite proper time \(\Delta\tau_w>0\), and exit at \(B\) at event \(p_B\). In the exterior charts, the matching may yield

\[
T_B(p_B)=T_A(p_A)-\Delta_{AB},
\]

where \(\Delta_{AB}>0\) denotes an earlier exterior date at exit. This relation is shorthand for the full geometry's mouth identification, not a discontinuous update of \(T\) along a globally valid chart. The worldline includes the approach to \(A\), the finite throat traversal, and the departure from \(B\); the traveler proper time increases throughout. Which traversal direction yields the earlier exit depends on mouth history and matching convention; derive the sign from those data rather than choosing it after route integration.

If the mouths are separated by exterior distance \(D\), and an exterior timelike return path from \(B\) to \(A\) takes duration \(T_{\rm ext}\) in the relevant exterior chart, a closed timelike curve becomes possible when

\[
\Delta_{AB}>T_{\rm ext}.
\]

Because a massive traveler cannot cover distance \(D\) in less than \(D/c\) in a local inertial frame, \(\Delta_{AB}>D/c\) is a necessary scale estimate for a CTC in a nearly flat, static exterior, not a complete condition in a curved or moving-mouth geometry. If the offset exceeds the minimum exterior travel time, a return segment and, if needed, a finite timelike waiting segment can close the curve. For an Earth–Moon center separation near the mean 384,400 km, the flat-space light-travel lower bound is about 1.282 s; a timelike return takes longer. This is only a scale illustration—actual mouth positions, trajectories, gravitational field, and throat transit determine the mission bound. The actual test is global: integrate the exterior and throat segments with one matched geometry and verify that the future-directed timelike curve returns to its initial event. A one-way earlier exit and a CTC are distinct claims. NASA/JPL reports the mean Earth–Moon distance as [384,400 km](https://www.jpl.nasa.gov/edu/resources/lesson-plan/modeling-the-earth-moon-system/).

## 4. Stress-energy and known obstacles

The geometry must satisfy Einstein's field equation

\[
G_{\mu\nu}=\frac{8\pi G}{c^4}T_{\mu\nu}.
\]

For the static, spherical Morris–Thorne geometry in classical Einstein gravity, the throat flare-out condition requires violation of the null energy condition (NEC) somewhere at or near the throat: for some null vector \(k^\mu\), \(T_{\mu\nu}k^\mu k^\nu<0\). “Exotic matter” here is a statement about this stress-energy condition; it is not a specified material or a proposed engineering recipe.

As a diagnostic example only, set \(\Phi=0\) and choose the shape function \(b(r)=r_0^2/r\), so \(ds^2=-c^2dt_w^2+dr^2/(1-r_0^2/r)+r^2d\Omega^2\). In a static orthonormal frame, the throat energy density and radial pressure are

\[
\epsilon(r_0)=-\frac{c^4}{8\pi G r_0^2},\qquad
p_r(r_0)=-\frac{c^4}{8\pi G r_0^2},\qquad
\epsilon+p_r=-\frac{c^4}{4\pi G r_0^2}<0.
\]

This is the source required by the chosen idealized metric under the Einstein equation; it is not evidence such a source exists. Its magnitude scales as \(r_0^{-2}\), and the example says nothing by itself about total integrated energy, formation, dynamic stability, quantum state realizability, or backreaction.

Relevant unresolved issues include:

1. **Source and energy conditions.** A complete model needs a covariantly conserved stress-energy tensor \(\nabla_\mu T^{\mu\nu}=0\), a physical matter/field theory producing it, and consistency with observational and quantum-field constraints. Quantum fields can violate pointwise energy conditions, but that fact does not establish macroscopic, long-lived wormhole support.
2. **Formation and control.** The thought experiment assumes an already existing traversable wormhole and controlled transport of one mouth. No known process creates, enlarges, moves, or stabilizes such an object.
3. **Backreaction and chronology horizon.** As a configuration approaches chronology violation, semiclassical stress-energy and stability may invalidate the fixed-background solution. Hawking's chronology-protection conjecture is an influential proposal, not a theorem resolving every spacetime.
4. **Initial-value and consistency problems.** CTC spacetimes can fail to admit ordinary global Cauchy data. A simulator must declare whether it imposes global self-consistency, a boundary-value solution, branching histories, or another rule; choosing one changes the model's predictions.
5. **Tidal and radiation hazards.** A navigable throat must meet constraints on tidal curvature, acceleration, traversal duration, radiation and particle flux, mouth environment, and structural clearance. These are not captured by endpoint positions or a simple collision radius.

Accordingly, this candidate is a conditional GR geometry plus an unresolved source problem. It does not establish a realizable temporal drive.

## 5. Continuous route and navigation state

Represent a mission as a connected, piecewise-smooth curve \(\gamma:[\tau_0,\tau_1]\rightarrow\mathcal{M}\), with continuous tangent at segment boundaries. Segments can include exterior approach, mouth entry, throat transit, exit, and exterior flight. The manifold atlas may change between segments, but the physical event, four-velocity, vehicle state, and proper time must match under the chart transition. No segment may be replaced by a zero-duration state assignment.

At the mouths, impose explicit matching conditions for the induced geometry and the traveler state. At minimum, the simulation must state whether position and tangent are continuous in a regular atlas, whether a thin shell carries a surface stress tensor, how clocks and tetrads are identified, and how the craft's attitude and control state are transported. If the idealized mouth boundary is represented by a junction with a surface layer, its Israel junction conditions and surface stress-energy are part of the model rather than hidden implementation details.

For a hazard worldline \(h_i(\lambda)\), collision is an invariant world-tube intersection: let \(\mathcal W_v\) be the vehicle's occupied spacetime tube and \(\mathcal H_i\) the hazard's occupied tube, including physical extent and stated uncertainty. A collision occurs if \(\mathcal W_v\cap\mathcal H_i\ne\varnothing\). A safety margin enlarges these tubes in a declared local rest-space geometry; it is not an extra coordinate-time offset. If the finite-body tubes or uncertainty sets cannot be mapped through the throat geometry, clearance is unknown. The reduced Astrarium screen

\[
\|\mathbf r(\tau)-\mathbf b_i(T(\tau))\|>R_i+M_i
\]

is valid only on exterior segments where both states are expressed in a shared local frame and event chart. It cannot be continued through a wormhole by carrying one heliocentric position vector across chart boundaries. Through the throat, screen against the throat's geometry, supporting fields, trapped radiation, and other travelers/objects in the throat. After exit, evaluate hazards in the destination exterior at the actual matched exit event.

The route result must include: metric and parameter source; mouth world tubes and matching maps; \(\Delta_{AB}\) and its uncertainty; traveler proper-time duration; four-velocity and control history; curvature/tidal exposure; stress-energy/energy-condition diagnostics; event and frame conventions; external ephemeris/hazard coverage; and numerical error bounds. Unknown source physics or uncovered hazards force an **unknown clearance** result.

## 6. Falsifiable mathematical checks for a simulator

Even without an engineering realization, an implementation of this conditional model can be tested against mathematical invariants:

1. **Worldline continuity:** at every segment and chart boundary, compare the same manifold event and tangent after applying the transition map. Position, four-velocity, attitude state, and onboard proper time may not reset.
2. **Timelike normalization:** verify \(g_{\mu\nu}u^\mu u^\nu=-c^2\) along the full route within a declared integration tolerance.
3. **Local future direction:** choose a continuous time orientation and verify each local tangent is future-directed in its chart. A decrease in one exterior \(T\) label is not itself evidence of past-directed local motion.
4. **Clock-map closure:** compare the numerical mouth-to-mouth map against the specified clock transport, gravitational redshift, throat transit, and boundary matching; propagate parameter uncertainty.
5. **CTC criterion:** only report a CTC after the complete future-directed route returns to the same spacetime event (or a declared event-equivalent state), with positive proper time and timelike tangent everywhere.
6. **Convergence:** refine geodesic/control integration and event detection until exit event, proper time, closest approach, and curvature exposure converge under stated bounds.
7. **Energy source audit:** calculate \(T_{\mu\nu}=c^4G_{\mu\nu}/(8\pi G)\), verify \(\nabla_\mu T^{\mu\nu}=0\), evaluate relevant energy conditions and averaged/quantum bounds, and report any failure. Passing these algebraic checks does not establish that the tensor is physically realizable.

These checks validate the solver against its assumptions. They do not validate the assumptions against nature.

## 7. Consequence for historical sighting navigation

An Astrarium sighting destination is an uncertain exterior spacetime region inferred from observation records, not a measured vehicle worldline. Under this candidate, a traveler cannot simply reverse a route or assign the reported coordinates and date to the craft. A conditional past-arrival route must specify mouth world tubes and the global matching map, a continuous throat path, the resulting exterior trajectory, the witness/view geometry, and a globally consistent causal model. No mouth geometry or time-offset data exists for any sighting; therefore Astrarium can currently reconstruct reports and model hypothetical encounters, but cannot claim to navigate physically to a historical sighting or establish that a traveler caused one.

The candidate suggests a useful software boundary: keep the ordinary celestial propagator, the temporal-geometry model, and the route/collision solver separate but coupled through explicit event/frame interfaces. A future implementation can first test a synthetic wormhole metric in a toy spacetime, then connect exterior segments to solar-system ephemerides only after a complete, validated matching model exists. This must not be presented as an operational solar-system time machine.

## 8. Conclusion

A moving-mouth traversable wormhole is a well-known conditional construction, not a working temporal-drive model. The local stationary shift ansatz in this note is explicitly **not** the mechanism: its negative chart-time rate is removable and produces no invariant time travel. A physical claim requires a fully specified global metric, mouth histories, and event-matching map, followed by derivations of the source, energy-condition accounting, stability and quantum-consistency analysis, and independent expert review. On the evidence assembled here, the result is a careful theoretical design note and falsifiable software specification; it is not yet publishable as a new physical model or feasible drive.

## References

- M. S. Morris, K. S. Thorne, and U. Yurtsever, [“Wormholes, Time Machines, and the Weak Energy Condition,” *Physical Review Letters* 61, 1446–1449 (1988)](https://doi.org/10.1103/PhysRevLett.61.1446).
- M. S. Morris and K. S. Thorne, [“Wormholes in spacetime and their use for interstellar travel: A tool for teaching general relativity,” *American Journal of Physics* 56, 395–412 (1988)](https://doi.org/10.1119/1.15620).
- S. W. Hawking, [“Chronology protection conjecture,” *Physical Review D* 46, 603–611 (1992)](https://doi.org/10.1103/PhysRevD.46.603).
- L. H. Ford and T. A. Roman, [“Quantum field theory constrains traversable wormhole geometries,” *Physical Review D* 53, 5496–5507 (1996)](https://arxiv.org/abs/gr-qc/9510071).
- J. L. Friedman et al., [“Cauchy problem in spacetimes with closed timelike curves,” *Physical Review D* 42, 1915–1930 (1990)](https://doi.org/10.1103/PhysRevD.42.1915).
- B. S. Kay, M. J. Radzikowski, and R. M. Wald, [“Quantum Field Theory on Spacetimes with a Compactly Generated Cauchy Horizon,” *Communications in Mathematical Physics* 183, 533–556 (1997)](https://arxiv.org/abs/gr-qc/9603012). This theorem identifies a breakdown of the standard Hadamard condition at certain Cauchy-horizon base points; it is a serious obstruction, but not by itself a universal proof that all time-machine spacetimes are impossible.
