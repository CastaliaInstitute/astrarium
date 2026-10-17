# Interactive solar system and A.R.G.O. mission

<iframe
  src="_static/argo-time-scene.html"
  title="Three-dimensional solar-system timeline and A.R.G.O. route"
  width="100%"
  height="760"
  loading="lazy"
  style="border: 0; width: 100%; max-width: 100%;">
</iframe>

Drag the scene to turn it, use the mouse wheel or trackpad to zoom, and move the year slider to watch the planets change places. Play starts at 2026 CE and runs toward the 6 BCE mission example; the slider can go farther into the past. The real solar system is too large to fit on one screen, so distances are squeezed and the Moon and planets are drawn larger. This helps you see their order and motion, but the picture is not to scale.

The slider covers 3000 BCE to 2026 CE. Orbital distances are compressed for display, so the scene preserves ordering and movement rather than distance scale. A.R.G.O.'s displayed path is a continuous cubic curve between a near-Earth departure in 2026 CE and a near-Earth encounter in a **6 BCE scenario**. The slider maps its year linearly to position along that curve; for years before the scenario endpoint, the planets continue while A.R.G.O. is outside the route interval. The scene uses JPL long-range approximate planetary elements, not a DE441 trajectory solution. The A.R.G.O. curve is a visualization scaffold: it is not dynamically integrated, does not place the craft at a solved Bethlehem viewing angle, and has not been collision-screened. It lets us inspect a moving celestial background and a continuous proposed path before connecting a complete temporal-drive and hazard model.

**Source:** NASA/JPL, [Approximate Positions of the Planets](https://ssd.jpl.nasa.gov/planets/approx_pos.html). The Moon marker uses a low-order visual orbit and is not an ephemeris-grade lunar position.
