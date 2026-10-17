# Interactive 3D scene: watch the planets and A.R.G.O.

<iframe
  src="_static/argo-time-scene.html"
  title="Interactive three-dimensional solar system and A.R.G.O. route"
  width="100%"
  height="760"
  loading="lazy"
  style="border: 0; width: 100%; max-width: 100%;">
</iframe>

Drag the scene to turn it, use the mouse wheel or trackpad to zoom, and scrub **crew proper time** through the calculated loop. The marker advances along one sampled worldline while the displayed $T_S$ coordinate can run forward or backward. Switch to **Planetary context** for an independent sky-date slider that shows the planets at selected dates. The two views are deliberately separate because the route model and planetary visualization do not yet share a complete, self-consistent ephemeris frame.

The route view is generated from the book's explicit symmetric two-bubble closed-timelike-geodesic calculation, using $U=0.75$, $\alpha=10$, and $\omega=0.95$. Its 7,198 samples include the published 1+1 centerline and the source profile's small transverse sidestep; the route is colored by segment. The event marker follows the samples using traveler proper time $\tau$, which increases continuously. The plot uses the same linear scale for time and distance ($c=1$), so the 2 km sidestep is far too small to see beside a tens-of-thousands-of-light-years excursion. The date label reports model-frame coordinate time $T_S$ relative to departure; it is not a direct civil-calendar date. Only the selected target event is labeled as the **6 BCE test scenario**.

This is a computed path within a published mathematical model, not a physically validated navigation trajectory. The plotted sidestep is not independently solved as part of a 3+1 geodesic. The model loop starts and closes at Earth's center, and its selected ancient target is also Earth's center: those are collisions. The target does not specify a Bethlehem observer or a light ray. The long excursion reaches tens of thousands of light-years, and the current scene has no common-frame, all-hazards clearance check. Do not read the picture as a safe route.

In **Planetary context**, orbital distances are compressed for display and the Moon and planets are drawn larger. The renderer uses NASA/JPL long-range approximate planetary elements over its stated date range; this view shows order and motion, not flight-distance scale. It is not synchronized to points along the calculated CTC. The Moon marker uses a low-order visual orbit and is not an ephemeris-grade lunar position.

The trajectory data are reproducible with [`build_argo_interactive_trajectory.py`](../scripts/build_argo_interactive_trajectory.py), which calls [`solve_two_bubble_encounter.py`](../scripts/solve_two_bubble_encounter.py) and the frozen-state estimator [`estimate_earth_target_state_3d.py`](../scripts/estimate_earth_target_state_3d.py). These scripts and the page state the model boundary and collision result explicitly.

**Source:** NASA/JPL, [Approximate Positions of the Planets](https://ssd.jpl.nasa.gov/planets/approx_pos.html). The Moon marker uses a low-order visual orbit and is not an ephemeris-grade lunar position.
