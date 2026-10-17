# Trajectory planning through time and space

## Product goal

Let a user define a departure state, destination, and time window, then explore
candidate paths through a moving celestial environment. A path is a worldline:
spacecraft position and velocity are evaluated at each simulation time, against
body positions at that same time. The display should show when the spacecraft
passes bodies and its closest approach to each one.

“Collision-free” should mean that the entire path clears each modeled body's
physical radius plus a configurable safety margin. Checking only sampled
waypoints is insufficient because a fast path can cross a body between samples.

## Model layers

### Solar-system navigation

- Treat onboard elapsed time `τ` and environment epoch `t(τ)` as separate
  state variables. A forward-experiencing traveler moving into the past has
  `dt/dτ < 0` in the reduced display model; this is not reverse playback of an
  ordinary orbit and is not, by itself, a GR solution. Ordinary future-directed
  causal motion in a globally hyperbolic spacetime cannot run backward along a
  global time function. Treat past-directed epoch evolution as a conditional
  postulate requiring an explicit causal spacetime or new-physics model. Require
  one continuous worldline and continuous epoch evolution with no jumps, event
  splices, or instantaneous reassignment. Until compatible dynamics and
  uncertainty are modeled, return a hypothetical, incomplete result and do not
  claim the temporal route itself is collision-screened.

- Use a single dynamical time scale internally (TDB) and convert to calendar
  dates only for the interface.
- Obtain time-dependent Sun, planet, and Moon states from a JPL planetary
  ephemeris. DE431/DE441 cover the multi-millennial interval relevant to
  Astrarium; JPL distributes them as SPICE kernels. The compact JPL approximate
  element model already integrated into Astrarium is useful for visualization,
  but its stated outer-planet errors are too large to claim safe passage.
- Represent a vehicle by position, velocity, and optional thrust/control
  history. Integrate its path under selected gravity sources; expose the model
  assumptions and accuracy with the result.
- Search candidate departure times and control parameters, reject paths that
  hit a body's radius plus safety margin, then rank the survivors by travel
  time, fuel, or clearance.
- Find closest approach continuously along integrated arcs. Use adaptive
  stepping and root/minimum searches so collision checks cannot tunnel through
  a body between coarse samples.

### Satellites and coverage

“All satellites” includes two different populations, and neither has complete
trajectory data over the full 5,000-year sky window:

- **Natural satellites:** use the JPL/NAIF SPK ephemeris for each moon where
  its time coverage includes the route. JPL's published files cover selected
  moons, with different start and stop dates; many listed windows are only a
  few centuries. The planetary DE431/DE441 kernel does not by itself provide
  every moon's detailed orbit.
- **Artificial satellites and spacecraft:** use archived state histories or
  mission SPKs for the specific object and interval. The currently integrated
  ETH Zurich TLE archive begins continuous collection on 2023-03-10 and has
  gaps; it cannot provide trajectories for all satellites since 1957.
  Earth-orbiting objects need historical tracking data such as archived
  GP/TLE sets, and those records have varying accuracy. Spacecraft trajectories generally
  need mission-specific archives. An object has no trajectory before launch,
  and a present-day orbit cannot safely be propagated back through unknown
  maneuvers or drag history.
- Astrarium bundles 25 reconstructed Sun-centered mission histories from NAIF
  SPICE and JPL Horizons, including planetary probes, orbiters, and landers.
  Route screening now reads records whose catalog coverage overlaps the trip,
  converts their ICRF vectors to ecliptic J2000, and estimates closest approach
  by interpolating between adjacent samples. This improves the sampled-object
  screen, but the catalog is not a census of spacecraft and interpolation does
  not certify collision avoidance.
- Store each object's identity, physical size where known, source, reference
  frame, time scale, coverage interval, and position uncertainty alongside its
  trajectory. Route checks must treat an uncovered interval as **unknown**,
  never as empty space.
- Screen major planets against bounding spheres using the JPL equatorial radius
  where available, so the reference ellipsoid is not reduced to a mean-radius
  sphere. This is a surface-intersection screen only: atmospheric entry,
  local terrain, and body/ephemeris uncertainty require separate hazard models.
- Saturn's dense D–F ring region has a separate plane-and-radius encounter
  screen. It treats the region from 66,900 to 141,000 km from Saturn's center
  as a continuous annulus with a 1 km half-thickness and applies the route's
  configured margin. Pole orientation uses NASA's linear-in-century
  Saturn pole model transformed into the route frame. A flagged result means
  the geometric zone enters the margin; it does not predict particle impacts.
  Ring gaps, warps, the diffuse E/G rings, and uncertainties remain unmodeled.
- Report “no modeled collision found within covered data and stated margins,”
  rather than claiming a route is safe when relevant object coverage or
  uncertainty is missing.

### Interstellar and galactic context

- Keep the Gaia proper-motion and radial-velocity model for moving stars.
- Treat the Milky Way potential as a large-scale context model, not as a source
  of precise local navigation forces.
- Make solar-system and interstellar navigation separate scales in the
  integrator, since their distances, times, and useful force models differ by
  many orders of magnitude.

## User interaction

1. Choose a start location, destination, departure date, and allowed travel
   interval.
2. Generate one or more candidate paths.
3. Scrub simulation time to move both the vehicle and celestial bodies.
4. Inspect closest approach, clearance margin, and the assumptions used for
   each candidate.
5. Reject a path if any modeled body's uncertainty or the trajectory's
   numerical error consumes its clearance margin.

The visual timeline should make time the shared control for the sky, body
positions, vehicle position, and route marker. The current year selector can
seed the departure date, but a route needs finer time resolution than a year.
The dashboard route scrubber now follows changes to the shared sky clock made
through the instant controls or warp, clamping its plotted vehicle marker to the
nearest route endpoint and explicitly labeling sky instants outside the route
interval. Scrubbing the route still writes the selected instant back to the
shared clock. Vehicle, planet, natural-moon, and small-body markers are
interpolated by their recorded UTC epochs; moon and small-body markers disappear
outside their available track intervals. Archived satellite markers appear only
inside sampled track segments, which are collected near the vehicle path and do
not represent a complete orbit or a complete satellite census.

## Current implementation boundary

Astrarium currently has historical sky rendering, on-demand JPL Horizons DE441
planetary vectors with a compact approximate-position fallback, a JPL Horizons
lunar vector cache with a simplified orbit fallback, simplified local orbit
demonstrations, a fixed smooth Milky Way potential for stellar context, and playback of recorded terrain
trajectories. The dashboard solves a zero-revolution Lambert transfer between
points just above selected endpoint bodies, uses that Lambert result as an
initial guess, then corrects departure velocity with finite-difference single
shooting under the modeled gravity field. The vehicle is integrated under Sun,
planet, and Earth-Moon point-mass gravity with adaptive-step RK4, and checks closest
approach against the Sun, planets, and Earth's Moon over each integration
segment. Before a full route, Astrarium downloads one-day heliocentric vectors
for Mercury, Venus, Earth, and the Mars through Neptune system barycenters from
JPL Horizons (DE441), caches them by route interval, and uses cubic-Hermite
interpolation at RK4 stages and during close-approach refinement. If any body
fetch is unavailable, that body uses the compact approximate model and
planetary coverage is marked incomplete. The model's Mars and outer-planet
system barycenters omit their moon-induced offsets from planet centers. For a
Moon departure or arrival, the route planner prepares the selected endpoint
day's lunar Horizons vector before integration; it reports missing endpoint
coverage and uses the compact lunar fallback when unavailable. The route model
uses lunar vectors already cached for other sampled dates and falls back to the
compact model outside cached dates. The separate natural-moon
encounter screen uses JPL Horizons vectors where their coverage permits. RK4
step doubling controls the integration step and reports the
estimated maximum local position error, accepted and rejected steps, and
arrival miss distance. Endpoint correction is bounded to three iterations and
reports the starting Lambert miss and final miss; its 1,000 km convergence
tolerance does not include body-ephemeris uncertainty. The local integration
estimate is not a global trajectory error
bound. Every accepted integration segment is screened with a relative-motion
arc bound, then eight-way bracketing and cubic Hermite local minimum searches
refine possible close passes. This reduces missed encounters between accepted
steps but is not a certified event detector or a formal closest-approach bound.
The model omits powered departure and arrival maneuvers, uncertainty in the
compact JPL body positions, and several object populations.
Gravity is softened inside modeled physical radii so an intersecting path can
be integrated far enough to report a clearance flag; this is a numerical
convenience and not a physical model of passage through a body.
For close passes of Mars, Jupiter, Saturn, Uranus, and Neptune, the route screen
requests time-tagged states for 66 named moons whose Horizons targets use the
configured JPL SPK families, and caches each response on device. The catalog
includes ring moons, Neptune's distant irregular moons, and previously covered
major moons. The screening regions include Phoebe's distant Saturn orbit and
Nereid's distant Neptune orbit. Targets with separate SPK solutions report
their own kernel family and date interval, including the shorter SAT415 and
URA184 ranges. These calls are limited
to an hourly grid around a close parent-system approach and refined between
samples; they are not continuous event detection. The encounter window is
capped, and a capped or uncovered window is reported as incomplete. Many
irregular and unlisted moons, most asteroids and comets, debris, and some
spacecraft remain uncovered; Earth-orbiting satellite records are sparse and SGP4-propagated from
archived TLEs. A “no modeled collision” result remains incomplete and is not a
flight-safety claim. Route moon coverage can only be evaluated inside the
published per-system SPK date ranges.
Small inner-moon radii are approximate literature values used as collision
spheres; uncertainty in shape, ephemeris, and the trajectory remains outside the
reported clearance.

For a route, Horizons also supplies daily vectors for eight curated small
bodies: Ceres, Pallas, Vesta, Hygiea, Interamnia, Eros, Apophis, and Itokawa.
Their vector tracks and minimum modeled clearances are shown on the route plot.
The collision spheres use nominal radii; radius and orbit uncertainty are not
included in the clearance. This selection is not a census of asteroids or
comets, and the planner keeps overall coverage incomplete even when every
selected target is available.

The dashboard can compare 2–9 evenly spaced departure candidates over a
user-selected window (up to ±3,650 days). It ranks candidates without detected
planetary/Earth-Moon collisions before candidates with a detected collision,
then by minimum clearance from those modeled bodies. Transfer candidates whose
integrated path misses the destination are labeled `transfer_miss`; other
non-collision candidates remain incomplete because natural moons and satellites
are not evaluated during this lightweight comparison. This is a
sparse search, not an optimized launch-window solution; satellite archive
coverage is not evaluated during this lightweight comparison. Selecting a
candidate runs the full route screen, which requests the exact UTC dates used
for its 65 baseline satellite samples and additional five-minute epochs near
Earth in parallel under a bounded wait. It checks closest relative chord
approach between consecutive satellite and vehicle samples when both records
are present and no more than five minutes apart, using a 1 km assumed satellite
collision radius plus the user margin. Missing samples and longer intervals
remain unknown. Minimum-clearance reporting includes the sampled satellite
catalog when that screen is enabled; the check does not certify conjunction
avoidance. The sample count includes any fresh usable TLE states, including
user-imported and bundled snapshots; interval coverage remains incomplete
unless the online archive reports data at every adjacent sampled interval.

### Recorded probe flights

The projector also replays spacecraft histories on a Sun-centered J2000/ICRF
map. The Phoenix cruise and Mars EDL products come from the NAIF mission SPICE
archive. Additional mission histories are ingested from JPL Horizons using
each spacecraft's Horizons target ID and Sun-centered geometric vectors. The
imported records retain the requested TDB coverage, target ID, service response
metadata, and one-day sample cadence. Horizons products can contain tracking
reconstructions or propagated extensions; their source notes and coverage stay
attached to the replay. Daily samples smooth over short encounters and
maneuvers. A surface-relative EDL or orbital pass is a separate body-fixed
record, as shown by Phoenix EDL and the MRO Jezero pass.

To add a cruise history, use `scripts/ingest_horizons_trajectory.py` with the
probe's Horizons ID and a date range inside its published ephemeris coverage.
The projector discovers installed records through
`player/app/src/main/assets/trajectories/catalog.json`.

The current catalog is a curated initial set, not a claim that every spacecraft
ever launched has coverage. Horizons availability, target ephemeris intervals,
archive reconstruction, and useful sampling cadence vary by mission. Each
inertial catalog entry declares its coordinate origin; Phoenix SPICE is Sun
centered, and JPL Horizons entries are Sun centered. Expand the catalog from the
NAIF/PDS SPICE archive and other mission archives while recording those limits
for each entry.

The installed catalog currently contains the Apollo 11 S-IVB post-separation
heliocentric departure reconstruction (1969-07-17 to 1969-07-24), an Apollo 11
LM P-66 final-descent local profile (140 seconds at 0.5-second cadence), Phoenix
cruise and EDL, the MRO
Jezero pass, and 21 Sun-centered JPL Horizons mission histories: Voyager 1 and
2, Cassini, Galileo, New Horizons, Juno, Mars Reconnaissance Orbiter, Mars
Odyssey, Mars Express, MAVEN, Curiosity, Perseverance, Dawn, Rosetta,
MESSENGER, Parker Solar Probe, OSIRIS-REx, BepiColombo, NEAR Shoemaker,
InSight, and Tianwen-1. The Horizons histories use one-day samples from the
target-specific coverage dates recorded in the catalog; the two Phoenix SPICE
tracks and MRO local pass retain their finer source cadences.

Regenerate the Apollo 11 LM P-66 local-profile asset with
`scripts/digitize_apollo11_lm_descent.py`. The script downloads NASA TM
20220007267, renders Figure 11, and records the chart-derived downrange and
altitude with source interval and limitations. It requires Poppler `pdftoppm`
and Pillow. NASA reports the source raw data were no longer available, so this
is a digitization of the report's reconstruction, not original telemetry.

## Remaining trajectory work

### Reverse-time route traversal

The route screen accepts a time direction. Backward mode swaps the endpoints
and epochs, solves an ordinary forward-time Lambert/gravity arc from the earlier
destination to the later origin, then presents the samples in reverse order.
This does not model a forward-experiencing traveler moving toward a decreasing
environment epoch. The arc is screened against available object states at
matching chronological epochs, but this geometry cannot establish clearance
for a physical temporal traveler or a time-transition mechanism. The dashboard
includes an Apollo 11 waypoint preset from lunar touchdown back to launch time;
that preset is a modeled Earth–Moon transfer, not the flown CSM/LM states. The
separate Apollo 11 recorded replay reverses the source-backed 140-second Eagle
P-66 local profile and stops at its data boundary; it does not bridge that
segment to launch. A path may be scrubbed backward.
This mode is reverse playback of an ordinary forward-time gravity solution
with endpoints swapped. It is a visualization convention, not a solution to
continuous reverse-epoch dynamics or a model of an actual temporal traveler. It
defines neither the traveler's proper time nor a continuous temporal-drive law.
The collision screen evaluates the synthetic spatial arc against objects at
those epochs, but cannot certify a time-travel worldline. Reverse results use the explicit status
`hypothetical_reverse_playback_incomplete`, even when no collision is detected
on the sampled modeled arc. Ordinary archive/kernel coverage limits still
apply.

Sun-centered recorded trajectory playback accepts forward or backward time
direction. It maps the selected sample's ET/TDB epoch to the shared sky clock,
so the observer sky and solar-system ephemerides follow the recorded route in
either direction. The Apollo 11 LM P-66 profile also plays in both directions
and updates the shared sky clock. NASA's 2022 reconstruction provides the final
140 seconds as downrange and altitude digitized from a published plot; it is a
local profile, not a geodetic state vector. Its lateral orientation is absent,
so lunar terrain clearance is not established. The player checks the digitized
centerline altitude against the zero-altitude reference plane, but does not model
terrain relief, vehicle dimensions, lateral position, or reconstruction error.
Playback stops at the final sample.
The bundled Apollo 11
S-IVB track is a NASA-contracted Earth-departure reconstruction served by JPL
Horizons (target -399110), covering 1969-07-17 17:00 to 1969-07-24 00:00 UTC
at 30-minute cadence. It is the discarded S-IVB stage, not the crewed command
or lunar module; it must not stand in for Apollo 11's full flown trajectory.

- Replace the compact JPL approximation with a selectable SPICE ephemeris
  kernel for intervals where its coverage and accuracy are appropriate.
- Expand natural-satellite targets beyond the current 66 named moons and replace
  hourly close-approach sampling with coverage-aware continuous event detection
  and uncertainty bounds.
- Add planetary perturbations and an explicit departure/arrival maneuver model.
- Replace chord-based close-approach estimates with adaptive event finding and
  numerical error bounds.
- Expand natural-moon, asteroid, debris, and spacecraft coverage with explicit
  source and interval manifests.
- Search launch windows and transfer parameters, then rank converged candidates
  by time, fuel, and clearance.

## References

- [JPL planetary physical parameters and equatorial radii](https://ssd.jpl.nasa.gov/planets/phys_par.html)
- [NASA Saturnian Rings Fact Sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/satringfact.html)
- [NASA Saturn Fact Sheet and pole orientation model](https://nssdc.gsfc.nasa.gov/planetary/factsheet/saturnfact.html)
- [JPL DE430/DE431 overview](https://ssd.jpl.nasa.gov/doc/de430_de431.html)
- [JPL ephemeris downloads and SPICE guidance](https://ssd.jpl.nasa.gov/ephem.html)
- [JPL approximate planetary positions and nominal errors](https://ssd.jpl.nasa.gov/planets/approx_pos.html)
- [JPL natural-satellite SPK files and their individual date ranges](https://ssd.jpl.nasa.gov/sats/ephem/files.html)
- [JPL Horizons API vector-query documentation](https://ssd-api.jpl.nasa.gov/doc/horizons.html)
- [JPL Horizons spacecraft target lookup API](https://ssd-api.jpl.nasa.gov/doc/horizons_lookup.html)
- [JPL guidance on satellite ephemeris limits and uncertainty](https://ssd.jpl.nasa.gov/horizons/manual.html)
- [Space-Track GP history documentation](https://www.space-track.org/documentation)
