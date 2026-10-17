# A.R.G.O. as the Star of Bethlehem

## A whitepaper on time-travel navigation in Astrarium

**Primary reference hypothesis:** A.R.G.O. traveled to the Bethlehem-era past and was perceived as the Star of Bethlehem. This is the mission premise explored here, not an established historical or scientific conclusion.
**Status:** Navigation concept and capability gap analysis
**Scope:** Astrarium treats travel through time and space as a real capability within its modeled universe. A navigator selects a destination state at a chosen epoch and follows A.R.G.O.'s worldline through the shared, time-dependent celestial scene. The scientific model must state which physics and data support each segment.

**Vehicle:** A.R.G.O. (Astrarium Research & Galactic Observatory), the saucer-shaped craft whose hull and co-moving spacetime bubble are modeled as one system. Astrarium remains the observatory and navigation software.

**Reference mission:** Navigate A.R.G.O. continuously through space and time until it becomes the light described in Matthew 2, then compare the predicted view with natural-sky interpretations, especially Jupiter. The text leaves the date, observer position, range, and track uncertain, so the mission begins as an ensemble of hypotheses rather than a unique solved route.

## Abstract

This paper develops Astrarium's primary reference hypothesis: A.R.G.O. traveled back through space and time and became the Star of Bethlehem. Treating that journey as possible is a product premise, not an established historical claim or a result of general relativity. The user chooses a departure state and candidate destination states that differ in position and epoch; A.R.G.O. must follow one continuous worldline through the changing celestial scene, with onboard proper time increasing and collisions checked along the route. The hypothesis does not select a physical mechanism. Any implementation must declare a temporal-drive model and its consequences; the current planner does not.

Astrarium already has a shared time control, ephemeris-backed body positions, an initial Lambert transfer, numerical trajectory integration, and partial encounter screening. Its backward route is only reverse playback: it swaps the endpoints and epochs, solves an ordinary forward-time transfer, then presents that arc backward. The force model never integrates with decreasing dynamical time. It does not model traveler proper time, temporal propulsion, continuous temporal-drive dynamics, causality, or temporal arrival uncertainty. Its collision checks apply only to the synthetic spatial arc against available object histories at the matched epochs; they do not evaluate a continuous temporal-drive worldline. The planner therefore does not currently navigate a physical time traveler, even under the product's “time travel is possible” premise. This paper defines the experience and a staged model for building it. Its current 3000 BCE–3000 CE clock is a software interval and model range.

Astrarium's defining experience is to travel backward in environment epoch and space until the traveler literally becomes a historical light event, here interpreted under the A.R.G.O.-as-Star hypothesis. “Become” means the simulated vehicle occupies a candidate location and epoch, creates a modeled appearance, and connects to departure and continuation through one continuous worldline. For the first reference mission, that premise is applied to the Star of Bethlehem story. This is an imaginative, testable-in-principle scenario, not an assertion about what happened. Every modeled route segment is checked for collisions and hazardous encounters against the celestial bodies, spacecraft, atmosphere, terrain, and other hazards present at the corresponding event. The navigation system must compare predictions against competing readings of the evidence rather than treat the UFO interpretation as established.

## Reference experience: become the Star of Bethlehem

The reference mission treats Matthew 2:1–12 as a sparse historical observation narrative and asks whether a hypothetical A.R.G.O. worldline could produce the described light. It is not a modern witness report: the text supplies no exact observation date, observer coordinates, angular measurements, range, spectrum, duration, or continuous track. The mission therefore uses a family of candidate epochs and broad observer/target regions, with missing quantities left unknown. The passage says the Magi saw a star, traveled from the east, and later saw it go before them and stand over the place where the child was; whether this describes unusual apparent motion, a conventional celestial sign, literary/theological imagery, or something else is unresolved.

The linked discussion asks at 2:08 whether the Star could have been a UFO. Its answer distinguishes logical possibility from evidential support, then argues that Matthew need not imply extraordinary motion and favors a Jupiter interpretation. Astrarium uses that distinction as a test discipline: model A.R.G.O. as one conditional source hypothesis, and compare it against natural-sky hypotheses instead of treating the UFO reading as data. Candidate astronomical proposals include the 7 BCE Jupiter–Saturn triple conjunction and lunar occultations of Jupiter in 6 BCE; these are scholarly interpretations, not settled identifications.

The user's proposed mission is to make A.R.G.O. the light the Magi perceived. A valid route must place the craft and its emitted/reflected photons on one continuous, causally consistent history, reproduce the apparent motion from the observers' changing viewpoints, and explain any reported standstill without assigning the star a made-up range or altitude. The broad Bethlehem region is a candidate destination area, not a verified house coordinate. Where the source text does not constrain a state, the solver must expose a user-selected scenario range and show how the result changes across that range.

This is a deliberately conditional product scenario: known ephemerides describe where modeled celestial objects were, but do not provide a mechanism for reaching an earlier epoch. The temporal-drive model must define the worldline and causal rules. The Star narrative motivates the encounter constraint; it does not establish that A.R.G.O. or any other vehicle was present. Known spacecraft and planetary trajectories are validation datasets, not alternate reference missions. UTC, dynamical ephemeris time, and traveler proper time τ remain distinct time axes with explicit transformations.

### Mission constraint: a star that appears to lead and stand still

For this vehicle model, A.R.G.O. is the craft: a saucer-shaped material hull $\mathcal H$ and its co-moving spacetime bubble $\mathcal B$. They travel as one system along a continuous world-tube. The hull has a finite collision envelope; the bubble has a separate field region and transition layer that also need physical interaction and hazard rules. A bubble boundary is not automatically a solid surface, and drawing one does not define a metric or temporal-drive law.

The narrative does not say that the light was the vehicle, that it appeared and disappeared in a modern UFO-report sense, or that it made several passes. If Astrarium explores repeated visits as a scenario, every pass must be part of the same globally consistent CTC with increasing onboard proper time; the renderer cannot spawn duplicates as a substitute for a worldline. Compare each pass's apparent angular position and brightness with a defined narrative interpretation, and check hull and field-world-tube intersections. No repeat count is supplied by the source.

The reference implementation has two linked parts:

- **Historical-text encounter.** A provenance-backed record of what Matthew 2 says, kept separate from later interpretation. Candidate dates, observer locations, viewing directions, range, and duration are scenario inputs with explicit uncertainty; the software must not present them as measured facts. The route solver returns a complete closed worldline and predicts the apparent sky from candidate observer sites, with collision and atmospheric/terrain clearance along every leg and loop closure.
- **Temporal navigation model.** Define allowed environment-epoch histories \(t(\tau)\) while onboard elapsed time \(\tau\) advances, temporal-drive control and resource limits, continuous traveler position and epoch evolution, and how interactions and causality are represented. Keep this model explicit and replaceable; it is a required design layer, not something Lambert transfers or ephemerides provide.

For crew experience, distinguish proper time \(\tau\), which advances along A.R.G.O.'s continuous worldline, from the exterior epoch \(E(\tau)\), which can decrease along part of a CTC. The Bethlehem-era encounter must lie on the full closed loop; the cited model returns to its departure event, so it does not describe a one-way arrival followed by an open-ended continuation. The crew's local memories and physiology still accumulate forward with \(\tau\); they encounter exterior epochs in reverse order on a segment where \(E(\tau)\) decreases. Disorientation or reluctance to interact is a possible story hypothesis, not a consequence of the metric. Local interaction remains possible when the ship, observers, and signals meet causally. The companion [temporal-drive candidate](temporal-drive-candidate.md) separates these claims and proposes testable observables.

The lead route should report whether the Star narrative is adequate to constrain a globally closed trajectory. It is not: event date, viewing geometry, and physical range are missing. The book must show that underdetermination rather than fill it with invented telemetry. Historical trajectory datasets such as Apollo reconstructions can validate frames and interpolation, but do not constrain the Star narrative or establish a UFO interpretation.

Start with a source-and-interpretation ledger for Matthew 2, then implement scenario ranges, sky reconstruction, route constraints, and observer-view prediction. Use source-backed celestial data and known trajectory records to validate epoch conversion, frame transforms, interpolation, and route continuity. Test state estimation, spatial maneuver control, encounter reconstruction, and temporal travel behavior separately so success in one does not imply success in another.

The Bethlehem mission is the book's central journey: under the A.R.G.O.-as-Star hypothesis, reconstruct candidate skies and observer views at an uncertain ancient epoch, then ask what continuous closed route and hazard checks would be required. Competing natural-sky interpretations remain visible in the same analysis. The mission premise does not make temporal travel an established physical capability.

(physical-status-and-continuity)=
## 1. Physical status and the continuity requirement

This proposal separates three claims that are easy to conflate:

1. **Ordinary relativistic time dilation is established physics.** A traveler can accumulate less proper time than observers on a chosen reference worldline and still move toward their future. This does not provide a route into an earlier Earth epoch.
2. **General relativity admits mathematical spacetimes with closed timelike curves (CTCs), subject to global and physical caveats.** A CTC is a continuous timelike worldline that returns to an event in its own causal past. Such solutions are not evidence that a traversable time machine can be built. Proposed constructions can require unusual stress-energy or assumptions whose physical realizability is unsettled. Hawking's chronology-protection conjecture argues that quantum effects may prevent macroscopic chronology violation; it is a conjecture, not a proved universal theorem.
3. **Astrarium's past-directed navigation is a product postulate.** The software may explore it as a conditional model, but must not describe the postulate as a consequence of ephemerides, a solved GR trajectory, or demonstrated engineering.

Use signature \((-+++)\). A massive traveler is represented by a differentiable (or piecewise differentiable with continuous tangent) curve \(x^\mu(\tau)\), parameterized by onboard proper time \(\tau\), satisfying

\[
g_{\mu\nu}(x)\,\frac{dx^\mu}{d\tau}\frac{dx^\nu}{d\tau}=-c^2.
\]

The curve is continuous and has no teleportation, event splice, or instantaneous epoch reassignment. The traveler experiences increasing \(\tau\). In ordinary globally hyperbolic GR, a global time function \(T(x)\) increases along every future-directed causal curve. Consequently, if the “environment epoch” \(t\) is such a time function, \(dt/d\tau<0\) is incompatible with ordinary future-directed timelike motion. A mere coordinate reparameterization cannot evade this: coordinates can change labels, but do not change causal order.

For simulation, distinguish the spacetime event \(x^\mu(\tau)\) from the displayed environment epoch \(t(\tau)\). A decreasing displayed epoch has physical meaning only if the chosen spacetime admits the relevant causal structure (for example, a CTC scenario), or if Astrarium explicitly adds new physics that changes the metric, causal cones, or the mapping between the traveler and environment. The latter is a phenomenological extension, not GR. A scalar control curve \(t(\tau)\) alone is not a physical drive law: it supplies no stress-energy tensor, equations of motion, energy budget, stability analysis, or interaction/causality rules. This whitepaper does not invent those missing quantities.

A moving-mouth traversable wormhole is used here as a conditional reference geometry because it can connect earlier exterior events with a continuous future-directed worldline. Its finite throat path, mouth clock matching, stress-energy, and unresolved formation/stability questions are developed in the [temporal-drive candidate model](temporal-drive-candidate.md). The candidate is not a new wormhole solution or a claim of realizability; it provides equations and validation obligations for a future toy-spacetime implementation.

**Continuity axiom.** Every candidate route is one connected worldline on a single parameter interval \([\tau_0,\tau_1]\). Position, velocity, onboard state, and the physical spacetime event are continuous; where forces are finite, their derivatives must also be finite. The environment event used to query hazards is evaluated along that same curve. A displayed epoch may increase or decrease only when the selected spacetime and its coordinate atlas support that behavior. The traveler-epoch map must itself remain continuous and match exterior ephemeris events at route boundaries; arbitrary interpolation through unsupported intervals does not meet this axiom. No route may jump between epochs or splice disconnected orbit samples and call them one journey. A smooth \(t(\tau)\) sketch is only a kinematic input for a conditional simulation until a spacetime metric and compatible dynamics are supplied.

The continuity axiom is necessary but not sufficient for navigation. For a true relativistic route, collision checks occur at the spacetime events on the worldline, not by comparing a Euclidean position to an object's state at an independently selected date. The implementation must transform traveler and hazard states into the same frame and event convention, account for light-time/causal interaction where relevant, and propagate bounded or probabilistic state uncertainty. If the underlying causal model is unspecified, the result is a visualization with unknown physical clearance.

## 2. Goal: navigate through time and space

For the navigation interface, keep onboard proper time \(\tau\), spacetime event \(x^\mu(\tau)\), and displayed environment epoch \(t(\tau)\) distinct. The ordinary route is a continuous future-directed worldline. A past-directed environment epoch with increasing onboard time is allowed only as a conditional speculative scenario whose causal spacetime model is separately declared. In a simplified solar-system sandbox, \(r(\tau)\) and \(t(\tau)\) may be used as reduced coordinates, but must be labeled kinematic rather than a GR solution. The route remains one continuous curve; selecting a mission event sets a target and never teleports the traveler.

Historical data supplies reference states, not the temporal travel mechanism. An artificial satellite track exists only after launch and where tracking records exist; a traveler may be simulated at epochs where no vehicle history was recorded, but that route must be generated by an explicitly declared model and clearly distinguished from observed history. An absent history is an uncertainty in hazard coverage, not evidence of empty space.

## 3. A single time axis for spacetime navigation

The sky projector and 3D star field share one simulation instant. This is the foundation: one time coordinate drives the observer, stars, planets, moons, spacecraft records, and route marker. Spacetime navigation must make the vehicle's epoch part of its state and let time controls move the vehicle and environment together. A route view should distinguish the selected worldline, recorded/observed history, and predicted or simulated portions, while exposing uncertainty and coverage.

Astrarium uses astronomical year numbering: year 0 is 1 BCE, year -3000 is 3001 BCE. For modern epochs, interface dates use civil UTC. For ancient dates, the same calendar controls encode a UT1-like instant because UTC did not exist. Dynamical calculations may use a different time scale, such as TDB or TT, and must convert explicitly rather than treating the calendar label as a universal time standard.

Earth's spin matters as much as its orbit when presenting the local night sky. Astrarium uses Earth Rotation Angle and a long-term precession model to place the date's equator and local sky. Historical ΔT (TT minus UT) is estimated from NASA's published model, but ancient Earth rotation is uncertain. The application exposes relevant uncertainty rather than implying that an ancient horizon is exact.

## 4. Reconstructing the sky

### 4.1 Stars

Gaia astrometry gives reference positions and proper motions for many stars. Astrarium propagates catalogued motion from the reference epoch to the selected year and precesses directions into the equator of date. For stars with measured radial velocity and a usable distance, a linear three-dimensional motion model captures perspective effects. Where radial velocity or distance is absent, the model uses angular proper motion. This is an approximation: constant velocity omits Galactic acceleration, unmeasured radial motion, and close gravitational encounters. Precision should be described as object- and epoch-dependent.

### 4.2 Planets and the Moon

Planetary positions are evaluated for the selected date from JPL Horizons vectors based on DE441 where available, with a compact approximate-position fallback for some bodies. Horizons vectors are cached and interpolated between samples. The fallback is useful for continuity, but is not equivalent to a high-precision ephemeris. Planetary-system barycenters and planet centers are not interchangeable, especially when comparing a planet with its moons.

The Moon is handled through time-tagged JPL Horizons vectors and interpolation, with a compact orbit approximation available while data is missing. The lunar position is especially important for the Earth–Moon barycenter split, local sky appearance, and route encounters. Network availability and lunar model coverage must remain visible to the user.

### 4.3 Natural satellites

The route and rendering catalogs include 79 named moons across Mars, Jupiter, Saturn, Uranus, Neptune, and Pluto. Their JPL solutions have object-specific time spans; a solution may cover only decades or centuries, not the full 6,000-year clock. JPL's planetary satellite ephemeris table is therefore queried for its actual kernel ranges. A missing kernel state is unknown, not evidence that the moon was absent or safely distant.

Only selected moon gravitational parameters are currently included in route integration. Other catalogued moons can participate in collision screening when their states and radii are available, but do not necessarily perturb the computed vehicle trajectory. Distant irregular satellites also require sufficiently large screening regions; a narrow parent-centered cutoff can miss a real encounter.

## 5. Historical traffic: satellites and spacecraft

“All satellites” spans at least two distinct datasets. Natural moons are celestial bodies with long-term orbital solutions of uneven coverage. Artificial satellites are human-launched objects whose trajectories begin at launch and change through maneuvers, drag, deployments, failures, and fragmentation. No 5,000-year ephemeris can supply the future histories of objects not yet launched or the unobserved histories of objects whose records are missing.

For Earth-orbiting objects, Astrarium can use dated TLE/OMM element sets and SGP4/SDP4 propagation. The integrated ETH Zurich archive begins continuous collection on 2023-03-10 and has object and date gaps. User-imported TLE, 3LE, OMM JSON, or GP CSV files can extend local history. Propagation is limited to 60 days from each element epoch, because old orbital elements rapidly lose validity. The system also includes a curated set of reconstructed interplanetary mission histories from NAIF SPICE and JPL Horizons. These records represent selected missions, not every spacecraft.

The correct data contract for any track is: object identity, source and provenance, time scale, reference frame, time span, sample cadence, uncertainty where known, and propagation method. Gaps and out-of-coverage times must remain explicit. A blank region in a plot must never silently mean empty space.

## 6. Spacetime navigation is estimation, planning, and control

Let the vehicle state include position, velocity, attitude, mass, relevant propulsion state, and temporal coordinate/rate. Let its estimate at epoch \(t_k\) include an uncertainty description, such as a covariance matrix or a bounded state region. A navigation cycle has four parts:

1. **Determine state.** Combine available observations—such as range, range rate, Doppler, optical landmarks, star angles, radiometric tracking, or inter-satellite measurements—with a dynamical model to estimate position and velocity and their uncertainty.
2. **Predict.** Propagate the state and uncertainty under a declared force model, including gravity, non-gravitational forces that matter for the vehicle, and planned or observed maneuvers.
3. **Plan and control.** Solve for feasible thrust and attitude histories subject to propulsion limits, arrival conditions, power, communications, thermal constraints, and keep-out zones. Produce maneuver opportunities and correction policies, not just a geometric transfer arc.
4. **Observe and correct.** Compare new measurements with predictions, update the estimate, assess residuals, and replan when the flight departs from its expected corridor.

The temporal travel model adds its own planning variables and constraints: a spacetime metric and causal structure, equations of motion, relation between onboard elapsed time and environment epoch, drive control and resource limits if new physics is postulated, and rules for interactions and arrival. Conventional celestial ephemerides describe where modeled objects are at an epoch; they do not specify how a vehicle changes its epoch. Until a mechanism and its dynamics are supplied, the planner can show hypothetical continuous waypoint geometry, but cannot claim to solve a time traveler's motion.

For a route parameterized by onboard time \(\tau\), collision screening evaluates the traveler and each hazard at the same spacetime event convention along the continuous worldline. In a reduced solar-system model, this is approximated by comparing \(r(\tau)\) with hazard state \(b_i(t(\tau))\), including uncertainty in both states and the epoch map. The temporal mechanism and its uncertainty must be included; if either is undefined, clearance is unknown. The model must define causal interactions, duplicate worldlines, and whether records represent physical states or only archival observations.

Collision avoidance is a primary navigation objective. In the reduced coordinate model, parameterize the continuous route by onboard time \(\tau\), with vehicle position \(r(\tau)\) and environment epoch \(t(\tau)\). Let body \(i\) have position \(b_i(t(\tau))\), collision radius \(R_i\), and required margin \(M_i\). Nominal clearance requires

\[
\min_{\tau \in [\tau_0,\tau_1]} \|r(\tau)-b_i(t(\tau))\| > R_i + M_i
\]

for every relevant object and the entire route. This Euclidean criterion is only a proxy; a relativistic implementation must define collision locally in a common physical frame. Vehicle and body state uncertainty, model error, maneuver execution error, temporal arrival error, and finite observation cadence create a distribution or bounded set of possible worldlines. The planner must evaluate whether that set enters the hazard region at any point, with explicit confidence or a conservative bound. The required threshold depends on mission class and governing standards; Astrarium must not invent one. A finite list of waypoints is not enough: continuity between waypoints must be represented and checked, including epochs between data samples.

Astrarium currently forms an initial transfer using a zero-revolution Lambert solution, corrects departure velocity by single shooting, integrates with adaptive RK4 step-doubling, and screens selected planets, moons, small bodies, archived Earth satellite elements, and recorded spacecraft. It reports closest modeled approaches and incomplete coverage. In backward mode, it swaps endpoints, integrates a conventional forward-time arc, then requests reverse playback. Although the positional curve is the same set of samples reversed, this does not make it a physically derived traveler worldline: velocities are not tied to increasing traveler proper time, no temporal drive/control law is solved, and the required continuous decreasing-epoch dynamics are absent. A collision screen over that arc can identify some geometric intersections with covered objects, but it cannot support a conclusion about a time-travel route. Reverse-mode results are therefore explicitly classified as hypothetical reverse playback and incomplete even when the synthetic arc has no modeled collision. Moreover, collision sampling is heterogeneous: planetary checks use integrated segments, natural moons are screened near selected parent-system windows and available kernels, small bodies use a curated list and daily vectors, spacecraft are checked only over record overlap, Earth satellites use sparse route epochs plus local refinement, and Saturn rings use a separate annulus approximation. These checks can miss hazards between samples or outside catalog/ephemeris coverage. The planner has no measurement-driven navigation filter, state covariance propagation, finite-burn thrust/attitude model, operational maneuver execution loop, or re-planning from tracking data. It also lacks validated force-model fidelity and complete hazard populations. Those define the difference between a visualization and an operational navigation capability.

This remains a coarse planning screen. A user can explore candidate routes, but cannot use the output as an operational command or certify a real vehicle trajectory. Full navigation also needs coordinate-frame and time-scale discipline from sensor measurements through control outputs; calibrated sensor models and bias estimation; validated force models and parameter uncertainty; finite-thrust guidance; maneuver planning with execution dispersion; robust encounter analysis; and a closed-loop process for tracking, orbit determination, maneuver decision, command generation, and post-maneuver verification.

## 7. Operational safety case and data coverage

Every navigation result should carry both a state-estimation report and a collision/coverage ledger, not just a colored path. The state report should state epoch, frame, time scale, estimated state, uncertainty, observations used, residual quality, and prediction horizon. The trajectory report should identify force models, vehicle parameters, continuous temporal-drive assumptions, maneuver assumptions, numerical convergence, and arrival dispersions. For every screened object, the hazard ledger should show closest approach, epoch, relative speed, clearance from physical envelope plus margin, uncertainty, and source/frame/time coverage. It should list uncovered objects and intervals explicitly. A screen can only support a safety case when the mission's required hazard set, data quality, uncertainty bounds, and verification criteria are met.

Useful result language is:

> No hazard-region entry was found for the modeled objects over the evaluated interval at the stated confidence and under the displayed assumptions. Coverage gaps or unbounded uncertainty prevent a safety conclusion.

The system should distinguish at least: hazard detected; evaluated with stated confidence and no hazard found; and insufficient coverage or uncertainty to evaluate. The second status must only be available after mission-specific criteria are met and independently validated. The current prototype should use exploratory wording and never label a route navigation-safe.

## 8. Roadmap

1. **Build the Bethlehem scenario ensemble.** Encode only what Matthew 2 actually constrains, expose candidate chronology and observer/location ranges, reconstruct competing natural-sky candidates, and keep the A.R.G.O.-as-star model explicitly hypothetical. Do not invent a dated track or a vehicle range to make the route solvable.
2. **Define the temporal drive model.** Specify permitted \(t(\tau)\) histories, continuous epoch-evolution law, constraints, temporal arrival uncertainty, and vehicle state updates at unrecorded epochs. Include departure/arrival hazard checks and collision checks over the full continuous worldline alongside gravity and propulsion.
3. **Validate spacetime playback and hazard detection.** Check time conversions, frames, planetary and lunar vectors, event timing, onboard-time versus environment-epoch behavior, continuous temporal waypoint arrival, and interpolation against independent ephemerides and trajectory records. Verify closest-approach detection on forward and continuous decreasing-epoch paths; test collision crossings between samples.
4. **Define the reference vehicle.** Document mass properties, propulsion, finite thrust, attitude constraints, sensors, communication assumptions, and encounter success/abort conditions. Historical vehicle parameters can seed a validation model; unsupported values remain assumptions.
6. **Build orbit determination.** Ingest timestamped simulated or archival tracking measurements with frame, time scale, calibration, and uncertainty; estimate the state and covariance; preserve residuals; and compare with reference states.
7. **Add guidance and maneuver design.** Plan translunar injection, midcourse corrections, lunar orbit insertion, descent/ascent, rendezvous, and trans-Earth injection with feasible burns and arrival constraints. Separate reference, commanded, executed, and estimated trajectories.
8. **Close the loop and assess hazards.** Simulate measurement updates and maneuver errors, propagate dispersions, replan, and verify lunar and Earth encounters continuously against mission-specific criteria. Validate independently before describing results as operational navigation.
9. **Generalize beyond the Bethlehem hypothesis.** After its assumptions and natural-sky comparators are traceable, apply the encounter model to modern reports such as the Phoenix Lights, preserving the distinction between one craft, multiple lights, and multiple passes. Historical reconstruction and future state estimation remain distinct data products.

## 9. Conclusion

The Star of Bethlehem is Astrarium's reference hypothesis: follow one continuous worldline to a candidate ancient epoch and test whether A.R.G.O. could have produced the light described in Matthew 2. The source is too sparse to determine a unique trajectory, so the first deliverable is an uncertainty-aware scenario ensemble compared with natural-sky explanations, not a solved route. The moving-mouth model is a conditional reference for mathematical exploration, not an operational mechanism. The current Lambert-and-integration planner is a spatial seed, not a time-travel or operational navigation model.

## 10. Motion while “staying still”: frame-dependent velocity

“Staying still” has meaning only relative to a specified reference frame and observer. A person standing on Earth's surface is approximately at rest in the rotating Earth-fixed frame, but moves relative to an Earth-centered inertial frame, the Solar System barycenter, the Galactic center, and the cosmic microwave background (CMB) frame. There is no experimentally privileged Newtonian absolute rest frame. The CMB frame is a measurable cosmological convention—the frame in which the CMB dipole vanishes—and is useful for quoting a large-scale velocity, not a universal navigation origin.

For a surface observer at geocentric latitude \(\varphi\), the rotational speed relative to Earth's spin axis is approximately

\[
v_{\rm rot}=\omega_\oplus R_\oplus\cos\varphi,
\]

where \(\omega_\oplus\) is Earth's sidereal angular rotation rate and \(R_\oplus\) is its equatorial radius. At the equator this is about 0.465 km/s (1,670 km/h); at latitude 40° it is about 0.356 km/s. The value depends on latitude, altitude, Earth orientation, and whether the observer is attached to the crust or moving relative to it.

Earth's mean orbital speed around the Sun is about 29.78 km/s. The Sun's average orbital speed around the Milky Way is about 230 km/s, with caveats: the Galaxy is not a rigid body and the value depends on the adopted Galactic model and local standard of rest. The Solar System's velocity inferred from the CMB temperature dipole is about 369 km/s. These are vector quantities in different frames and directions; they are not scalar speeds to add. Successive velocities must be transformed between frames. Special-relativistic velocity composition is

\[
\mathbf u\oplus\mathbf v = \frac{1}{1+\mathbf u\cdot\mathbf v/c^2}
\left[\mathbf u+\frac{\mathbf v}{\gamma_u}+\frac{\gamma_u}{1+\gamma_u}\frac{\mathbf u\cdot\mathbf v}{c^2}\mathbf u\right],
\qquad \gamma_u=(1-u^2/c^2)^{-1/2},
\]

when \(\mathbf v\) is measured in the rest frame reached by the first boost. For solar-system trajectory geometry at these speeds, a declared inertial frame and a Galilean vector sum are adequate to excellent approximation; relativistic transforms matter for precision timing, high-speed vehicles, and consistent frame changes. The implementation should compose state transforms at explicit epochs rather than add headline speeds.

| Motion | Approximate speed | Reference frame |
| --- | ---: | --- |
| Earth's equator relative to its spin axis | 0.465 km/s | Earth-fixed to Earth-centered inertial |
| Earth around the Sun | 29.78 km/s | Heliocentric mean orbital speed |
| Sun around the Milky Way | 230 km/s | Galactic orbital model |
| Solar System relative to the CMB | 369 km/s | CMB dipole rest frame |

As a one-day scale illustration, an equatorial point travels about 40,100 km relative to Earth's spin axis; Earth advances about 2.57 million km along its heliocentric orbit; and the Sun advances about 19.9 million km along its local Galactic orbit. These path lengths are **not** a net displacement from an absolute origin and cannot be summed into one unique displacement. Earth's orbital velocity changes direction throughout the year; Earth's rotation changes its vector each sidereal day; Galactic velocities depend on the chosen origin and epoch. For example, adding the orbital and Galactic *magnitudes* as if they pointed in the same direction would give 259.78 km/s; subtracting them would give 200.22 km/s. The actual result depends on their vector directions, and the Galactic and heliocentric quantities are defined relative to different origins.

For an Earth-fixed departure point, the Solar-System-barycentric state is assembled from Earth's barycentric state and the observer's Earth-fixed position and velocity, with Earth orientation and time-scale transformations applied. For a candidate ancient encounter, the useful question is not “how far did Earth move since then?” but “what is the vehicle's continuous position and velocity in the declared frame at the event, and where are Earth, the observers, and hazards at that same event?” A traveler that remains above a ground location must continuously match Earth's rotation and orbital motion; holding inertial position fixed instead separates the traveler from Earth. At an ancient epoch, uncertainty in Earth's rotation angle and civil-time conversion must also be carried into the observer geometry.

These speeds are small compared with \(c\), but velocity alone is neither the temporal-drive cost nor a collision criterion. Collision screening uses relative state and finite world-tubes; temporal reachability depends on the declared spacetime model and continuous worldline. In a relativistic implementation, onboard proper time is integrated from the metric along that route, not inferred by summing frame-dependent speeds.

## References and data sources

### Relativity and chronology

- [Gospel of Matthew 2:1–12](https://www.biblegateway.com/passage/?search=Matthew%202%3A1-12). The narrative text is the primary source for what the Magi and star are said to do; it does not provide a modern astrometric track.
- Jimmy Akin, [“Was the Star of Bethlehem a UFO?”](https://www.youtube.com/watch?v=DDizx6UAWJY&t=128s), especially 2:08 onward. This is the supplied discussion prompt, not an astronomical data source; it distinguishes logical possibility from evidence and argues for a Jupiter interpretation.
- D. W. Hughes, [“The Star of Bethlehem,” *Nature* 264, 513–517 (1976)](https://www.nature.com/articles/264513a0). Proposes the 7 BCE Jupiter–Saturn triple conjunction as an astrologically significant candidate.
- M. R. Molnar, [“The Magi’s Star from the Perspective of Ancient Astrological Practices,” *QJRAS* 36, 109–126 (1995)](https://articles.adsabs.harvard.edu/pdf/1995QJRAS..36..109M). Proposes Jupiter occultations in Aries in 6 BCE; this is a distinct scholarly hypothesis, not a settled identification.
- JPL, [Horizons manual and DE441 coverage](https://ssd.jpl.nasa.gov/horizons/manual.html), and [Horizons API documentation](https://ssd-api.jpl.nasa.gov/doc/horizons.html). Any future sky reconstruction must state the target solution, epoch scale, observer location, and uncertainty; historical Earth rotation and civil-time conversion are not exact.
- S. W. Hawking, [“Chronology protection conjecture,” *Physical Review D* 46, 603–611 (1992)](https://doi.org/10.1103/PhysRevD.46.603). This is the chronology-protection proposal, not an established no-go theorem.
- M. S. Morris, K. S. Thorne, and U. Yurtsever, [“Wormholes, Time Machines, and the Weak Energy Condition,” *Physical Review Letters* 61, 1446–1449 (1988)](https://doi.org/10.1103/PhysRevLett.61.1446). A theoretical construction and analysis of requirements; it does not demonstrate a realizable time machine.
- J. L. Friedman et al., [“Cauchy problem in spacetimes with closed timelike curves,” *Physical Review D* 42, 1915–1930 (1990)](https://doi.org/10.1103/PhysRevD.42.1915). Analysis of initial-value problem difficulties in chronology-violating spacetimes.
- L. H. Ford and T. A. Roman, [“Quantum field theory constrains traversable wormhole geometries,” *Physical Review D* 53, 5496–5507 (1996)](https://arxiv.org/abs/gr-qc/9510071).

- JPL, [DE440/DE441 planetary ephemerides](https://ssd.jpl.nasa.gov/doc/de440_de441.html) and [DE440/DE441 technical paper](https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf).
- JPL, [Horizons API documentation](https://ssd-api.jpl.nasa.gov/doc/horizons.html).
- NASA GSFC, [Earth fact sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html) for Earth's mean orbital speed; NASA, [Chapter 2: Reference Systems](https://science.nasa.gov/learn/basics-of-space-flight/chapter2-1/) for Earth orbital speed range and frames; NASA GSFC, [Does the Sun move around the Milky Way?](https://starchild.gsfc.nasa.gov/docs/StarChild/questions/question18.html) for approximate Galactic orbital speed; Planck Collaboration, [Doppler boosting of the CMB](https://doi.org/10.1051/0004-6361/201321556) for the Solar System's CMB-frame velocity.
- JPL, [planetary satellite ephemeris table](https://ssd.jpl.nasa.gov/sats/ephem/), [satellite mean elements](https://ssd.jpl.nasa.gov/sats/elem/), and [physical parameters](https://ssd.jpl.nasa.gov/sats/phys_par/).
- NASA GSFC, [Espenak–Meeus ΔT polynomial](https://eclipse.gsfc.nasa.gov/LEcat5/deltatpoly.html) and [ΔT uncertainty guidance](https://eclipse.gsfc.nasa.gov/SEcat5/uncertainty.html); ancient Earth-rotation uncertainty limits conversion from dynamical time to local clock time.
- ESA, [Gaia Data Release 3](https://www.cosmos.esa.int/web/gaia/dr3).
- ETH Zurich, [Satellite Database API](https://satdb.ethz.ch/api-documentation/) and [archive overview](https://satdb.ethz.ch/about/).
- NASA/JPL NAIF, [SPICE toolkit and archives](https://naif.jpl.nasa.gov/naif/).
- NASA, [Apollo 11 Mission Report](https://www.nasa.gov/wp-content/uploads/static/apollo50th/pdf/A11_MissionReport.pdf), [Flight Plan](https://www.nasa.gov/wp-content/uploads/static/history/alsj/a11/a11-fltplan.html), [Flight Journal and mission records](https://history.nasa.gov/wp-content/uploads/static/history/alsj/a11/a11.html), and [Apollo 11 Transcripts](https://www.nasa.gov/wp-content/uploads/static/history/alsj/a11/a11trans.html).
- NASA Technical Reports Server, [Apollo Mission 11 trajectory reconstruction and postflight analysis, volume 1](https://ntrs.nasa.gov/citations/19700014995), a postflight reconstruction covering CSM and LM trajectory parameters.
- Project implementation notes: [Astrarium time travel](time-travel.md) and [trajectory planning](trajectory-planning.md).


## Appendix A. Phoenix Lights: one pilot's five-light account

The Phoenix Lights remain a useful comparison case, but they are not the book's lead mission. NUFORC report 8345 records one airline pilot's account from Interstate 10 at about 8:15 p.m. local time on March 13, 1997. The witness described **five individual objects** in a roughly triangular formation, moving slowly southward; each appeared to have a brighter forward light and a fainter light behind it. The pilot said a bright star was not obscured as the lights passed, and reported that altitude was very difficult to judge. NUFORC notes that the submitted date was March 15 and that it inferred March 13 from follow-up calls. This is one retrospective witness account, not independently verified vehicle telemetry.

For A.R.G.O. modeling, keep three hypotheses distinct: five separate vehicles; one vehicle producing multiple visible lights; or one craft making repeated passes that appear as separate lights. The report's count and triangular arrangement do not decide among them. Any multi-light explanation must predict angular separation, relative motion, brightness, occultation of background stars, and viewing geometry at the moving observer. It must also model whether multiple hulls or repeated field regions collide or interact along a single self-consistent history. This makes the case a useful stress test for the user's “one ship, multiple lights” idea without treating it as support for the Star of Bethlehem hypothesis.

The “Phoenix Lights” label also covers reports from different times and observers. Do not combine all of them into one trajectory without event-by-event timestamps and source records. The reference account here is specifically [NUFORC Sighting 8345](https://nuforc.org/sighting/?id=8345); its date caveat, altitude uncertainty, and single-observer status belong in any data model.
