# Astrarium time travel

## What you can do here

Choose a date and watch the modeled sky change. Earth turns, the planets move, and stars slowly shift position. The same time control is shared across the sky projector and the 3D star field, so both views show the same chosen moment.

Try moving the date a year at a time, then watch what changes. Ancient sky positions can be less certain because Earth's old rotation is not known perfectly. The detailed notes below explain the time scales and data Astrarium uses, and where its estimates become uncertain.

The sky projector and 3D star field share one simulation clock. For modern dates
its civil-time fields are UTC; for historical dates they are a UTC-like encoding
of a UT1 instant because UTC did not exist. Setting a year keeps the current
month, day, and clock time; the exact-instant controls use that astronomical
year (including year 0 and negative BCE years). Choosing a date or stepping the
shared instant by one hour, day, month, or year pauses the clock at that instant.
The warp controls run the shared clock forward or backward continuously
and can pause at any selected date. The
projector computes the local sky from propagated star positions and
selected-date solar-system calculations. The 3D scene evaluates its local Sun,
Moon, and planet positions at the same epoch.
The dashboard's equatorial star map propagates Gaia-matched proper motion to the
fractional year of the shared instant. Its date-equator precession matrices
refresh at day boundaries, and the mobile horizon view computes horizon
coordinates from that same shared instant and mean-equator frame.
The native local-sky and mobile horizon calculations share Earth Rotation Angle plus the long-term
precession model's equinox shift, so local sidereal time and catalog star coordinates use
the same mean equinox frame. The browser uses the native sidereal value when connected,
with a conventional GMST fallback offline. Earth rotation uses the selected
UTC-like instant as UT1, while compact solar-system fallback orbits use the
NASA GSFC Espenak-Meeus estimate of ΔT = TT−UT to shift their dynamical epoch.
The estimated ΔT and NASA's approximate one-sigma uncertainty are exposed by
the epoch API and dashboard; table values are interpolated between NASA's
published anchor years, and the dashboard also shows the corresponding
uncertainty in Earth-rotation angle. Uncertainty is left unquantified for dates
where NASA publishes no general estimate. Ancient ΔT values and future
extrapolations are uncertain, and this model does not recover irregular Earth
rotation from historical observations, so distant local-horizon orientations
remain uncertain. The polynomial model is published by
[NASA GSFC](https://eclipse.gsfc.nasa.gov/LEcat5/deltatpoly.html), and its
uncertainty guidance is [here](https://eclipse.gsfc.nasa.gov/SEcat5/uncertainty.html).
The Earth Rotation Angle relation follows the
[IERS Conventions](https://iers-conventions.obspm.fr/conventions/content/tn36.pdf).
Interplanetary route departure controls use the same astronomical year convention
with separate month, day, and UT-like time fields, so route screening can begin at a
BCE instant as well as at a modern date. “Use shared sky date” copies the current
clock instant into those route fields.

For the Moon, the app requests geocentric vectors from JPL Horizons for the
selected UTC day, stores the 25 hourly states in its private cache, and
interpolates between them. Until that day is loaded or when the request fails,
the renderer uses its compact lunar orbit approximation. The Moon source is
included in the live sky and dashboard astronomy data so the fallback is
visible. Earth and Moon heliocentric positions use the same lunar vector when
available, correcting the Earth-Moon barycenter split used by the planet model.

The app's route catalog contains 79 named moons of Mars, Jupiter, Saturn,
Uranus, Neptune, and Pluto, including the five-member Pluto system, inner ring
moons, and several distant irregular satellites. Pluto's Charon, Nix, Hydra,
Kerberos, and Styx use JPL's PLU060 solution (1800–2200); these five can also
be selected as route endpoints. The local sky and 3D scene request and draw every target available
in its kernel interval. The sky labels the 24 largest targets to keep the
planetary fields readable; smaller moons remain visible as points. Requests are
made only when the selected date lies inside each target's kernel coverage.
Jupiter's distant Himalia is included with JPL Horizons target 506 and the
JUP344 solution (1799-12-25 through 2199-01-10); Jupiter's route encounter
window includes Himalia's roughly 11.37-million-kilometer orbit. Elara,
Pasiphae, Sinope, Lysithea, Carme, Ananke, and Leda also use JUP344; their
positions are tracked, while unknown radii make route clearance explicitly
unknown. Those bodies are excluded from surface endpoint selection.
Horizons returns these target states relative to the Sun; the sky renderers
subtract Earth's heliocentric position before converting each state into the
Earth-centered line of sight used by the planets. The projector reports the
number of catalogued moon kernels covering the selected instant, cached states,
pending requests, and targets outside their kernel intervals. Its astronomy
debug response also lists each moon's parent, kernel, published date bounds,
and state (`available`, `loading`, `not_loaded`, `unavailable`, or
`outside_kernel`), distinguishing missing historical coverage from a state
that is still loading. Route
planning uses the catalogued targets near their supported parent systems. Covered states
are interpolated locally; missing or out-of-kernel dates remain absent or mark
route coverage incomplete. JPL lists natural-satellite trajectories as useful
over decades to centuries, shorter than its planetary-system ephemerides; the
5,000-year view must therefore show kernel coverage gaps rather than implying
that every moon's position is known. See JPL's [satellite ephemeris coverage](https://ssd.jpl.nasa.gov/sats/ephem/)
and [description of trajectory limits](https://ssd.jpl.nasa.gov/orbits_doc.html).

## Space-time navigation and collision screening

The [continuous-worldline temporal-drive candidate](temporal-drive-candidate.md)
sets out a conditional moving-mouth wormhole reference model, the metric and
clock-offset equations it assumes, and why it does not yet constitute a
physically realizable drive. In particular, a negative coordinate-time rate
can be a coordinate artifact; epoch must be anchored to external clocks and
ephemeris event labels.

### Physics boundary

Onboard elapsed proper time $\tau$, the traveler event $x^\mu(\tau)$, and
the displayed environment epoch $t(\tau)$ are distinct. Every proposed trip
must be a single connected, continuous worldline with no teleportation, epoch
jump, or splice across missing trajectory segments. Changing the selected sky
date in the ordinary UI is clock scrubbing; it does not model a traveler.

In ordinary globally hyperbolic general relativity, a global time function
increases on future-directed causal worldlines. Thus a decreasing environment
epoch while onboard time increases requires chronology-violating spacetime
structure or an explicit new-physics postulate. A smooth curve for $t(\tau)$
is only a kinematic prescription: it does not derive a metric, stress-energy,
drive law, energy budget, stability, or causal interaction rules. Astrarium's
temporal travel premise is therefore conditional simulation physics, not an
established capability. See the [mission brief's physics boundary and references](whitepaper-space-time-travel.md).

The planner must carry that same continuous route through every hazard check.
Checking a set of sampled positions against stored object states cannot certify
the unsampled intervals, and missing history remains unknown rather than safe.

Time direction is part of route playback, but the current planner does not yet
model a temporal traveler. Its backward mode swaps the endpoints and epochs,
solves an ordinary forward-time gravity arc, then plays its samples backward.
The current dynamics do not integrate a vehicle with decreasing environment
epoch while its onboard elapsed time advances. No proper-time relationship,
continuous temporal-drive law, or transition path is defined. We require the
actual traveler's position and environment epoch to evolve continuously; its
onboard time continues forward. Its collision checks apply only
to the synthetic spatial arc against covered object histories at corresponding
epochs; they do not certify the intended continuous time-travel worldline.
Reverse results therefore report `hypothetical_reverse_playback_incomplete`,
even when the synthetic arc has no modeled collision. The Apollo 11 waypoint
preset uses lunar touchdown and launch as endpoints for this modeled transfer;
it is not the flown Apollo trajectory. The recorded mission navigator can also
play available histories backward, and its selected epoch updates the shared
sky clock.

The Apollo 11 event navigator includes source-backed UTC and ground-elapsed-time
waypoints for launch, translunar injection, lunar orbit insertion, spacecraft
separation, landing, EVA, lunar liftoff, trans-Earth injection, and splashdown.
Selecting an event sets both the shared sky instant and route date. The timeline
contains event timing only; it does not imply a recovered CSM/LM position at
every event. Event times are sourced from NASA's [Record of Lunar Events](https://www.nasa.gov/wp-content/uploads/static/history/ap11ann/ap11events.html),
[Apollo 11 trajectory reconstruction report](https://ntrs.nasa.gov/citations/19700014995),
and [mission overview](https://www.nasa.gov/history/apollo-11-mission-overview/).
The separate **Apollo 11 · reverse the recorded landing segment** control now
plays the bundled Eagle P-66 final-descent reconstruction backward from
touchdown. This is a 140-second, Moon-local downrange/altitude profile digitized
from NASA TM 20220007267; it has no lateral coordinate or geodetic state. The
replay stops at its source-coverage boundary. It does not bridge to launch,
fabricate a CSM/LM cruise, or claim a historical collision clearance. The
adjacent interplanetary planner remains an explicitly modeled route between
selected body waypoints, with the available chronological hazard screens and
their coverage gaps.
The recorded-trajectory navigator now includes the final 140 seconds of the
Apollo 11 Eagle LM's P-66 landing phase. The local downrange/altitude profile is
digitized from Figure 11 in [NASA TM 20220007267](https://ntrs.nasa.gov/citations/20220007267),
starts at GET 102:43:20, uses 0.5-second samples, and can be played forward or
backward while the shared sky follows its epoch. NASA's report reconstructs the
curve from published plots because the original data were unavailable. The
profile has no crossrange or geodetic track bearing; it is shown as a local
profile and cannot be checked against lunar terrain. The viewer does screen the
digitized centerline altitude against the report's zero-altitude reference plane,
reporting an interpolated crossing or the minimum sampled clearance. This is a
limited contact screen: local relief, landing-gear/vehicle dimensions, lateral
position, and reconstruction uncertainty are not modeled, so it cannot establish
terrain clearance or collision safety. The profile is a real but short segment
of the mission, not the CSM/LM journey from launch to return.

Archived spacecraft are screened as moving hazards using their recorded
positions and the route's interpolated positions at the union of both sample
times. A gap larger than an archive's cadence or any missing interval marks the
screen incomplete. The Apollo 11 S-IVB history is a reconstructed, uncrewed
upper-stage track from 1969-07-17 through 1969-07-24 at 30-minute cadence; it
does not represent the crewed command/service module or lunar module. A zero
modeled clearance is a detected intersection under the selected radius and
margin assumptions. No detected intersection does not certify a route safe:
untracked debris, catalog gaps, finite sampling, and orbit uncertainty remain
outside the model.

Planet collision bounds use equatorial radii where available. Saturn's dense
D–F ring annulus is screened separately using a geometric ring-plane distance,
its configured margin, and a time-varying pole orientation. A potential ring
encounter is reported as a hazard rather than a solid-body collision and is
also considered when ranking departure dates. The model treats the annulus as
continuous; it does not resolve gaps, ring warps, or the diffuse E/G rings.
Atmospheric entry, local terrain, and object/ephemeris uncertainty are separate
hazards and are not included in this route screen.

## Stellar positions

The bundled bright-star catalog is cross-matched to local Gaia DR3 `G < 8`
astrometry. Matched coordinates, proper motions, and positive-parallax distance
are stored at Gaia's J2016.0 reference epoch. The projector propagates angular
motion at constant proper-motion speed along a great circle from the catalog's
observation epoch to the selected observation year, then precesses the direction
into the equator of date. For bright stars with measured Gaia DR3 radial
velocity, the projector instead advances the full 3D position and velocity,
including linear perspective effects. Stars without radial-velocity measurements
keep the great-circle proper-motion model. Catalog positions already describe
apparent directions at their observation epochs, so stellar light time is not
subtracted again. This avoids tangent-plane drift over multi-millennial
intervals. Constellation line vertices use the same motion data when a Gaia
counterpart is available. Stars
without a match keep their original J2000 coordinates and receive precession
only. The radial-velocity supplement contains 53,137 Gaia DR3 sources with
`G < 8` and a published velocity; 476 of the current 5,044 projector catalog
stars have matched radial velocities. Gaia documents its `radial_velocity`
field in km/s in the [DR3 source catalog data model](https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_main_source_catalogue/ssec_dm_gaia_source.html).
Regenerate the supplement with `scripts/gaia_bright_radial_velocity.py`, then
rebuild the projector catalog with `scripts/build_sky_catalog.py` and the
dashboard map with `scripts/enrich_parent_star_astrometry.py`.

The browser star map contains 83,468 rows, including the Sun, and currently
has 81,851 Gaia J2016 astrometry entries: 81,844 matches from the local query
plus seven retained matches from the earlier bright-star cross-match. The local cross-match
requires positions within 0.02° and magnitudes within 2.5; it copies Gaia's
J2016.0 coordinates as well as its proper motions. The browser propagates those
matches and applies the same Vondrák date-equator precession used by the
projector. The remaining 1,616 unmatched map stars and named-object positions
receive precession without proper motion.

The 3D Gaia tile catalog uses its packed proper motions to move stars from
J2016.0 in the selected year along the same constant-speed great-circle model,
preserving catalog distance. Its proper motions are quantized and can be
clamped by the tile format. The bright local HYG 3D catalog also matches 447
stars to Gaia astrometry, including measured radial velocities where available.
Those stars move in 3D through the selected epoch; their projected locations,
named-star waypoints, and crosshair labels use the same propagated positions.
Regenerate the match asset with `scripts/enrich_starfield3d_astrometry.py`.

The route departure-window comparison ranks transfers with no detected modeled
collision and acceptable arrival targeting first, then prefers fewer known
coverage gaps and greater minimum modeled clearance. It adds up to four
midpoint screens in same-status coarse intervals, prioritizing intervals whose
modeled clearances are nearest zero, then bisects each observed collision-status
transition four times. This improves sampled coverage but can miss narrow safe
or hazardous windows between samples. It identifies a preferred candidate only
when those modeled checks pass; incomplete object catalogs, ephemeris gaps, and
trajectory uncertainty still mean that no candidate is certified collision-safe.

## Limits

This is a visualization model, not a precision historical almanac. Gaia
radial-velocity coverage is incomplete, and linear stellar motion omits Galactic
acceleration, close encounters, and perspective acceleration beyond the constant
velocity model. The projector uses the Vondrák, Capitaine &
Wallace long-term precession model. For the selected sky date it downloads
daily geometric vectors from JPL Horizons, which currently identifies DE441 as
the source for these bodies, then uses cubic-Hermite interpolation. This is
cached by route interval on device and fetched in the background for sky-only
scrubbing. Mercury, Venus, and Earth use planet-center vectors; Mars and the
outer planets, including Pluto, use DE441 system barycenters. If a vector is
missing for Mercury through Neptune, the compact JPL approximate-position model
is used and the view reports that fallback. Pluto has no compact fallback, so
its marker is omitted until its DE441 vector is available. A Pluto moon can
still appear when its own PLU060 state is available. Route status remains
incomplete if its requested interval lacks Pluto's vector. Planetary barycenter offsets remain a limitation; historical outer-planet
positions carry larger uncertainty than inner-planet positions. The NASA ΔT
estimate shifts only compact fallback orbital calculations; Horizons vectors
are queried at the selected UT-like epoch. ΔT and historical Earth rotation
remain uncertain at distant epochs.

The precession matrix implementation follows the SOFA/ERFA formulation of the
Vondrák model. Its epoch 1666.666 matrix agrees with the SOFA reference test
values; this numerical check does not validate the rest of the sky pipeline.

The compact fallback coefficients and stated fit range come from [JPL's
approximate positions page](https://ssd.jpl.nasa.gov/planets/approx_pos.html).
JPL documents DE441 as spanning 13,200 BCE to 17,191 CE, and notes that
Horizons currently serves its long-range subinterval through 9999 BCE–9999 CE.
Astrarium's clock currently spans 3000 BCE–3000 CE, within that Horizons
interval. The [DE440/DE441 documentation](https://ssd.jpl.nasa.gov/doc/de440_de441.html)
recommends DE441 for historic epochs; its long-span fit has less modern-century
accuracy than DE440.

The lunar state is queried from the [JPL Horizons API](https://ssd-api.jpl.nasa.gov/doc/horizons.html)
on demand rather than bundled as a kernel. This supports the shared clock's
millennial range where Horizons responds, but is network-dependent on a cache
miss and is not an offline high-precision lunar ephemeris.

The dashboard's year field uses astronomical year numbering: year 0 is 1 BCE,
and year -3000 is 3001 BCE. Artificial satellite trajectories are loaded for
the selected UTC day from ETH Zurich's public Satellite Database archive when
network access is available. Results are cached by day on the device. The
projector draws a one-orbit sky arc for each returned object and limits
propagation to 60 days from its TLE epoch. The bundled current TLE file is used
as an offline fallback. ETH Zurich began continuously collecting this archive
on 2023-03-10; it has date and object gaps and is not a 1957-to-present
catalog. Dates before that start or after the current day are reported outside
the archive range; an empty response within the range means no records were
returned for that query, not that no satellites existed. The ETH API returns
dated TLE snapshots, and SGP4 propagation from a snapshot is limited here to 60
days from its epoch. It does not provide full historical state trajectories.
Separately, the route planner screens 24 bundled, reconstructed interplanetary
spacecraft histories from NAIF SPICE and JPL Horizons when their date coverage
overlaps the route. These are mission spacecraft tracks, not the full population
of Earth-orbiting satellites. They use daily or finer samples and are interpolated
in ICRF/ecliptic J2000 coordinates; incomplete catalog coverage remains unknown.
The interplanetary path screen samples the available catalog at 65 equally
spaced times across the route. It adds TLE propagation samples for every
integrated path segment whose spacecraft-to-Earth chord passes within
250,000 km: up to five minutes apart generally, refined to 30 seconds when the
route passes within 50,000 km of Earth. This covers the departure and arrival
regions where Earth-orbiting satellites can intersect the route. The chart draws up to 2,000 historical
satellite tracks that pass within 250,000 km of the vehicle, sampled from those
route epochs; it breaks tracks at archive gaps longer than 15 minutes rather
than connecting across missing data. It reports how many time samples had usable records,
how many are pending, failed, stale, empty, or outside the archive date range,
and the closest sampled clearances for returned NORAD objects. It also propagates
those records into the heliocentric route plot. Per-object closest-approach
rows include the age and provenance of the selected orbital element set at that time (ETH
archive, user import, or bundled fallback). This is not a continuous
satellite catalog: route planning fetches sampled UTC days concurrently within
an eight-second archive wait budget, and uses only snapshots cached by the end
of that prefetch plus the bundled fallback. Therefore missing
samples, uncataloged objects, and route periods outside an element set's
60-day validity remain unknown. Between route samples up to five minutes apart
(30 seconds in the innermost screening zone), closest approach uses cubic
Hermite interpolation from the integrated vehicle state and SGP4 satellite
position and velocity, with a numerical minimum search whenever the straight
chord estimate falls within the safety margin plus 10,000 km. More distant
intervals keep the chord estimate. This refines likely encounters without
running the full minimizer for every satellite and interval. It represents
orbital curvature better than a straight chord near a potential encounter,
but element changes, model and frame uncertainty, catalog gaps, and intervals
longer than five minutes remain unknown. The screen uses a 1 km assumed
satellite collision radius plus the user margin and is not a conjunction
certification.

Both visual arcs and route checks use the Vallado SGP4/SDP4 implementation with
WGS-72 constants to propagate archived TLEs into TEME positions. The model
includes the standard near-Earth and deep-space perturbation terms, but TLE age,
catalog omissions, the route's finite sampling, and the simplified path model
still make the result unsuitable for conjunction or collision certification.
The archive contains public catalog TLE records, but object/time
coverage varies and cannot provide a complete trajectory for every satellite.
Astrarium labels the archive record count and reports when the selected date
has no returned records. The shared sky clock spans 3000 BCE–3000 CE; artificial
satellite records begin with the space age and have gaps.

The historical records are fetched from the [ETH Zurich Satellite Database
API](https://satdb.ethz.ch/api-documentation/), which provides archived TLEs
with selectable time ranges. The database states that continuous collection
began on 2023-03-10 ([about the archive](https://satdb.ethz.ch/about/)). A TLE
is an orbital-element snapshot, not a continuous archived state history. The
short track drawn by Astrarium is propagated from the nearest returned element
set.

Older user-obtained two-line TLE, three-line TLE/3LE, SGP4 OMM JSON, or GP CSV files can be imported from the dashboard's
Historical satellite elements control. OMM JSON supports full catalog identifiers that do not fit in the TLE five-character field. Astrarium groups them by each element set's
own epoch, keeps the source snapshots on device, and selects the closest
per-object element within the SGP4 60-day limit for the selected sky date and
each route sample. Re-importing overlapping TLE files deduplicates exact
element lines; OMM rows deduplicate by catalog ID and normalized UTC epoch.
Changed day files are written through a same-directory temporary file and
atomically replaced. These records appear in the local sky when visible and are
included in route screening; an imported-only date remains marked partial.
The dashboard also summarizes the persisted imported snapshot count, object
count, UTC epoch-day count, and first-to-last epoch range after reload, with
buttons to jump the shared sky clock to the first or latest snapshot and a
selector for each stored UTC snapshot date. Its NORAD object browser lists the
imported epochs for one catalog ID and can jump the shared sky clock to any of
those element records. The plot shows archived element-epoch positions as
separate points, plus the selected epoch's nearest SGP4-propagated one-orbit
arc. It does not connect observations from different dates or claim a
continuous reconstructed history between element sets. Positions use a
TEME-to-ecliptic-J2000 approximation with long-term precession; nutation and
equation-of-equinoxes corrections are omitted. The archive-wide range does not
imply continuous coverage. For ordinary sky and route queries, imported files
are scanned only within 60 days of each requested epoch; the complete imported
archive is not retained as live SGP4 objects in memory. Summary scans read only
record IDs and epochs, and per-object browsing instantiates only that object's
element sets.
Imported records augment the ETH archive and do not imply complete catalog coverage. TLE and OMM records both remain element-set snapshots, and propagation stays limited to 60 days from their epoch. Space-Track GP_History and CelesTrak archived OMM exports can supply additional historical records, but Astrarium does not fetch them directly or claim a complete catalog. CelesTrak offers
unclassified historical GP records from 1957 through its latest update, but
its special-request workflow limits each request to 100 objects and 20,000
records, delivers results by email, and requires a CAPTCHA; its TLE format is
limited to five-digit catalog numbers. Astrarium accepts TLE/3LE text, SGP4 OMM JSON, and GP CSV with the required SGP4 element columns. See the [CelesTrak historical archive
request](https://celestrak.org/NORAD/archives/request.php).

Space-Track documents more than 138 million historical general-perturbation
element sets in GP_History. It requires an account and is subject to its query
guidelines; large or long-range queries should use its yearly archive bundles.
For a specific period, export GP_History in JSON/OMM format and import the files
through the dashboard's Historical satellite elements control, which accepts
multiple date-sliced files in one selection (each file up to 20 MB) or a ZIP
bundle up to 100 MB. ZIP import reads TLE, 3LE, OMM JSON, and GP CSV entries
without extracting archive paths, caps each expanded entry at 20 MB and the
whole archive at 200 MB, and validates the complete ZIP before importing any
contained records. Invalid data entries are reported individually; valid entries
from the same archive can still be imported. The importer
accepts Space-Track's UTC `EPOCH` values with or without a trailing timezone
suffix, groups records by element epoch, and the route viewer propagates the closest
valid element set for each object. This can extend a user's local history back
to early satellite records, but it cannot reconstruct periods or objects absent
from the downloaded archive. See the official [Space-Track API documentation](https://www.space-track.org/documentation).

For routes passing near Mars, Jupiter, Saturn, Uranus, Neptune, or Pluto, the planner
requests JPL Horizons vectors for 79 named moons. Targets use their own
published kernel intervals: for example, the Saturnian inner-satellite solution
SAT415 covers 1990–2018, while Uranian inner-satellite solution URA184 covers
1900–2100. Pluto's five major moons use PLU060, with coverage from 1800–2200.
The route collision screen represents Pluto with its DE441 system barycenter
and uses a 3,350 km conservative envelope around that point, covering Pluto's
radius plus the Charon-driven barycenter offset. The inputs come from JPL's
[Pluto satellite mean elements](https://ssd.jpl.nasa.gov/sats/elem/) and
[physical parameters](https://ssd.jpl.nasa.gov/sats/phys_par/).
Neptune's listed irregular moons expand the encounter screen to include
Nereid's distant orbit. Returned states are cached on device and shown
on the route plot. JPL's current catalog lists many more objects than this
curated set; the route time window is also capped. Outside a target's kernel
interval, for unlisted moons, or when a request or sample window is incomplete,
coverage is unknown. This is not a complete natural-satellite catalog.
JPL publishes the live kernel spans in its [planetary-satellite ephemeris table](https://ssd.jpl.nasa.gov/sats/ephem/)
and Pluto's elements in the [mean-elements table](https://ssd.jpl.nasa.gov/sats/elem/).

The route origin and destination selectors also include the catalogued moons.
For those endpoints the planner obtains heliocentric Horizons vectors at the
departure and arrival instants and uses each moon's physical radius when placing
the transfer endpoints. The clearance point is placed along the local radial
direction away from the moon's parent. The transfer still assumes an instantaneous
departure or capture there; it does not integrate a launch or landing through the
local moon's gravity. Kernel gaps are reported as unknown rather than replaced
with an invented orbit. The transfer dynamics still use Sun and major-planet
point-mass gravity and do not model the selected moon's local escape trajectory
or powered capture; moon-to-moon routes therefore remain coarse path screens.
The planner marks these routes `incomplete_coverage` because selected-moon
gravity and powered departure/capture are not integrated.

The initial route uses the short-way zero-revolution Lambert branch. If a
preliminary route detects a planet or listed-moon collision, or clearance within
100,000 km of the configured safety boundary, Astrarium also evaluates the
long-way Lambert branch and chooses the branch with fewer preliminary modeled
collisions, then greater minimum planet/moon clearance. It endpoint-corrects
that branch and runs the full collision screen afterward. This branch choice
is shown with the preliminary collision counts and clearances used in the
decision. It does not optimize against asteroids, Earth satellites, or recorded
spacecraft; those still require a separate departure-window search. Neither
branch is a certified flight plan.

Route integration includes the Sun, major planets, and Earth's Moon. For close
approaches to other moon systems, the planner first samples a preliminary route,
fetches covered Horizons moon states near those encounters, and re-shoots the
transfer with interpolated point-mass forces for moons with populated JPL
[gravitational parameters](https://ssd.jpl.nasa.gov/sats/phys_par/). The current GM table covers selected major moons;
other catalogued moons are still checked for collision but do not bend the
integrated route. For the DE441 system-barycenter vectors, covered moon offsets
also shift the modeled primary center; Pluto's combined system GM is reduced by
the represented satellite GMs to avoid adding those masses twice. Missing moon
states or GM values are reported as incomplete
gravity coverage. Moon trajectories and gravity therefore remain too sparse
and incomplete for collision certification.

## Reported aerial observations

The projector can display a reported aerial observation as an event in local
sky coordinates. The bundled `sky/ufo-sightings.json` pair is a synthetic
geometry fixture, not witness data or a NUFORC export. Each record carries a
UTC observation time, observer latitude/longitude, reported azimuth/elevation, angular
uncertainty, source attribution, and optional range and event-match fields.
The dashboard's UTC sky-instant control and observation picker set the exact
replay time and pause the shared sky clock there; moving the warp control off
zero resumes it. The renderer shows an event only within its stated timestamp
uncertainty (at the exact second when that uncertainty is absent). A single
sightline requires the configured observer to be within
roughly 17 km of the report location; a triangulated estimate can be viewed
from other configured sites. Reported events are not treated as recurring
objects.

Azimuth/elevation define an observer's line of sight. They do not determine
range, so a report without measured range is not assigned a 3D craft position.
If the source supplies a range, Astrarium combines it with the bearing and
shows the result as a range-based estimate with its range uncertainty when
provided.
When two or more observations share an `eventId`, have reported directions and
angular/time uncertainty values, their time-uncertainty intervals overlap, the
observations span no more than ten minutes, and their sight lines have adequate crossing angle,
Astrarium computes a least-squares closest point in a WGS‑84 Earth-fixed
frame. It rejects behind-observer, underground, very high-altitude, and
high-residual solutions; triangulation requires an explicit angular uncertainty
for every bearing. The estimated position and RMS miss distance are
derived values, not reported facts; the current display uses the estimate to
reproject the marker for the selected observer. Optional `rangeKm` and
`rangeUncertaintyKm` fields are reserved for sourced estimates. Ingested public
reports must preserve their original identifiers, source URLs, precision, and
reuse terms; do not infer sky direction from a city-level location or narrative
alone. Import redistributable source data with the documented
[CSV importer](ufo-data.md). NUFORC's [terms of service](https://nuforc.org/terms/) claim ownership or
control over its sighting database compilation, so Astrarium must not copy its
records into the bundled catalog without permission; use a licensed feed or
records whose rights permit redistribution. NASA's [UAP study](https://www.nasa.gov/wp-content/uploads/2023/09/uap-independent-study-team-final-report-0.pdf)
also notes that missing metadata and calibrated corroborating measurements
limit reliable conclusions from many witness reports.
