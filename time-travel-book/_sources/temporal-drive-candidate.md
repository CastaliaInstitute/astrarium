# Continuous-worldline temporal-drive candidates

## Two-bubble warp CTC, the A.R.G.O. payload, and the Bethlehem target

## First, the idea in everyday language

Could a traveler follow one unbroken path and arrive at an earlier date, while the traveler's own clock keeps moving forward? Some equations in general relativity describe special space-times where a path can loop back to an earlier event. This chapter checks one such mathematical example and asks what it would take for A.R.G.O. to follow it.

The example uses two separate regions of curved space-time. A tiny test traveler follows a path through them; the published equations do not build a saucer, create those regions, or show how to control them. Our calculations can check the rules of the example and estimate some scales. They cannot yet tell us how to make a real time-travel drive.

The pages below use advanced equations. In short: we need the route to stay continuous, the crew's clock to keep moving forward, the whole ship to fit safely inside its modeled region, and the path to avoid hazards. If the math or data cannot answer one of these questions, we mark it as an open problem.

**Status:** Conditional general-relativistic reference model for simulation design. This is a critical synthesis and extension of published metrics, not a new solution to Einstein's equations, an engineering proposal, or evidence that time travel is physically realizable.

## Summary

This note asks what a continuous A.R.G.O. trip to an earlier Earth date would require. It examines a published mathematical example with two regions of curved space-time and follows the path of a test traveler. The example is not a complete ship design: it does not show how to make or control the regions, how to carry a saucer-shaped hull safely, or where exactly the craft would meet the people in the Bethlehem story.

We check the example's loop condition, explore a simplified endpoint calculation, and estimate how far apart the example's events may be. A separate saucer-shaped model is used for one energy-density calculation; it is not the source of the two-region route. A wormhole is discussed as another mathematical idea. The Star story does not give a measured date or a unique object identity, so those remain open choices for the mission scenario.

## 1. Scope and claim discipline

The models answer a narrow question: **what continuous spacetime route could make a past-directed exterior arrival compatible with increasing traveler proper time, and what does the bubble-shaped craft premise actually constrain?** They do not provide a temporal propulsion law that can be built from known matter, a complete source-and-control theory for the published CTG geometry, or a safety case for a real mission.

The temporal-drive reference is the two-bubble rest-frame-transition construction of Shoshany and Snodgrass (2024), which explicitly gives a continuous timelike geodesic returning to its past in a prescribed spacetime. The geodesic is that of a test traveler in a metric containing two distinct, disjoint compact field supports; it is not a construction of a single material bubble or a physical vehicle. No known matter theory sources the prescribed geometry, and the paper does not show how its fields could be formed or controlled. It is a mathematical reference for a possible A.R.G.O. worldline, not yet a vehicle design. The Morris–Thorne moving-mouth wormhole is a separate comparator: it too can produce a time machine if a traversable throat and a global mouth-matching map are assumed, but no known process creates or stabilizes it.

Terminology in this note:

- $\tau$: traveler proper time, increasing along a massive traveler worldline.
- $T$: an exterior inertial time coordinate, available separately near the two mouths. In a chronology-violating spacetime there is no single global time function covering the full route.
- $A,B$: the two wormhole mouths, represented by finite world tubes rather than dimensionless points.
- $\Delta_{AB}$: the signed, operationally defined exterior clock offset between mouth events identified by traversal through the throat. Positive $\Delta_{AB}$ means arrival through the throat at $B$ has an earlier exterior $T$ than entry at $A$, after accounting for finite throat transit time.

For the two-bubble model, use $E(\tau)$ for the exterior epoch read in the initial asymptotic frame along the traveler's worldline. It is not globally a time function in a CTC spacetime and should not be confused with the traveler’s proper time $\tau$.

The route is a single continuous curve on the spacetime manifold. A coordinate chart that covers the exterior near $A$ need not cover the throat and exterior near $B$ with one globally meaningful time coordinate. A chart change or nontrivial topology is not a physical discontinuity; a teleportation operation that replaces the event or state without a connecting curve is. Astrarium must render the throat segment as an actual modeled path and retain its proper-time duration. A straight line or instantaneous endpoint swap between mouths is not an acceptable route representation.

Manifold continuity alone is not enough for Astrarium's no-jump requirement. The route must also expose a continuous traveler-epoch map $E(\tau)$ whose exterior endpoint values agree with the mouth matching map and the ephemeris events used for hazard queries. Any variation of $E$ through the throat must follow from a specified metric and atlas, not an arbitrary smooth interpolation. If a model cannot provide this continuous map, it fails the product requirement even if its abstract manifold curve is continuous.

## 2. Local throat geometry

In a static, spherically symmetric neighborhood of the throat, use proper radial distance $\ell$ and write the Morris–Thorne line element as

$$
ds^2=-e^{2\Phi(\ell)}c^2dt_w^2+d\ell^2+r^2(\ell)d\Omega^2,
\qquad d\Omega^2=d\theta^2+\sin^2\theta\,d\phi^2.
$$

Here $t_w$ is a local throat time coordinate, $r(\ell)$ is the areal radius, and $\Phi(\ell)$ is the redshift function. A traversable throat at $\ell=0$ has a minimum area radius $r_0=r(0)>0$, with

$$
r'(0)=0,\qquad r''(0)>0,
$$

and finite $\Phi$ so that no event horizon blocks passage. A physical model must also match this local geometry to two exterior regions, specify mouth world tubes and boundary/junction conditions, and solve for the stress-energy that sources the full geometry. The static metric alone does not encode the moving-mouth clock offset and is not a complete time-machine spacetime.

### Coordinate time inside a throat is not the drive

For a reduced continuity test, one may write a stationary radial chart ansatz

$$
ds^2=-c^2N^2(\ell)\left[dt-\frac{\alpha(\ell)}{c}d\ell\right]^2+d\ell^2+r^2(\ell)d\Omega^2,
$$

where $N(\ell)>0$ is a lapse and the dimensionless $\alpha(\ell)$ is a radial shift. For a radial traveler with $\dot\ell=d\ell/d\tau>0$, proper-time normalization and the local future branch give

$$
\frac{dt}{d\tau}=\frac{\alpha(\ell)}{c}\dot\ell+
\frac{1}{N(\ell)}\sqrt{1+\frac{\dot\ell^2}{c^2}}.
$$

Algebraically, this chart rate becomes negative when

$$
\frac{\alpha(\ell)}{c}\dot\ell<-
\frac{1}{N(\ell)}\sqrt{1+\frac{\dot\ell^2}{c^2}}.
$$

But this is only a **coordinate rate**, not a time-travel criterion. If $\alpha$ depends only on $\ell$, define

$$
t'=t-\frac{1}{c}\int_0^\ell\alpha(\xi)d\xi,
\qquad dt'=dt-\frac{\alpha(\ell)}{c}d\ell.
$$

The metric becomes $ds^2=-c^2N^2(\ell)dt'^2+d\ell^2+r^2(\ell)d\Omega^2$. The shift has been removed and no invariant earlier arrival follows from the negative $dt/d\tau$. It is mathematically the same coordinate pitfall as the flat-spacetime example below. This ansatz is a useful test that code can integrate smooth coordinates and match endpoints, but it cannot serve as the physical drive model, calculate an observable $\Delta_{AB}$, or demonstrate a wormhole time machine.

For an actual moving-mouth wormhole, the relative clock offset is a **global matching property** of the two mouth world tubes and the throat identification. It is not a local radial shift. The model must specify the full spacetime atlas, metric on both exteriors and the throat, mouth histories, and the identification map for events and tetrads across the throat. Only then can one compare entry and exit events using clocks synchronized by an explicitly stated exterior protocol and determine whether an exit is earlier in the relevant exterior time. The clock map must be derived from the complete geometry and mouth histories, not fit to a desired result. Before using any ansatz as physics, compute its Einstein tensor and source $T_{\mu\nu}$, check covariant conservation and energy conditions, and establish regular matching and stability.
The coordinate-artifact issue can be demonstrated without a wormhole. In flat spacetime, start with inertial coordinates $T,x$ and define $t=T-\kappa x/c$. For an inertial traveler with $x=vT$,

$$
\frac{dt}{d\tau}=\gamma\left(1-\kappa\frac{v}{c}\right),\qquad
\gamma=\frac{1}{\sqrt{1-v^2/c^2}}.
$$

At $v=0.8c$ and $\kappa=2$, this gives $dt/d\tau=-1$, even though inertial time $T$, proper time $\tau$, and causal order all increase. The transformed metric has $g^{tt}=(\kappa^2-1)/c^2>0$, so the $t=\mathrm{constant}$ surfaces are timelike, not valid shared simultaneity slices. The transformation is globally a coordinate relabeling of Minkowski space and creates no time machine. Therefore Astrarium must define external epoch by calibrated exterior clocks and ephemeris event labels, not an arbitrary coordinate. A physical earlier arrival is a relation between those externally anchored events, supported by the full geometry and matching map; a negative coordinate derivative alone is insufficient.

For an idealized, radial, zero-angular-momentum traversal with no thrust, the local geodesic equations follow from the metric. More generally the vehicle four-velocity $u^\mu=dx^\mu/d\tau$ must satisfy

$$
g_{\mu\nu}u^\mu u^\nu=-c^2,\qquad
u^\nu\nabla_\nu u^\mu=a^\mu,\qquad
u_\mu a^\mu=0,
$$

where $a^\mu=0$ for free fall and nonzero $a^\mu$ represents a specified onboard force per unit mass. These equations preserve continuity and normalization, but do not supply the metric, mouth dynamics, or feasible vehicle control. Those must be inputs or solved as a coupled field-and-motion problem.

## 3. Producing an exterior time offset

The standard thought experiment begins with mouths synchronized while adjacent. One mouth is then transported on a relativistic journey and returned, or held at a different gravitational potential. Its accumulated proper time differs from the other mouth's. In an approximately Minkowski exterior, the exact kinematic proper-time difference along a prescribed mouth path is

$$
\Delta\tau_{\rm kin}
=\int_{T_0}^{T_1}\left(1-\sqrt{1-\frac{v_B^2(T)}{c^2}}\right)dT,
$$

where $v_B(T)$ is the transported mouth's speed in the chosen inertial exterior frame. This is an exact special-relativistic expression for the kinematic proper-time difference in that inertial frame, not a weak-field approximation. In a weak, slowly varying gravitational field with potential $\varphi$, include the leading gravitational contribution by using

$$
d\tau\simeq dT\left(1+\frac{\varphi}{c^2}-\frac{v^2}{2c^2}\right).
$$

The clock difference is not yet the traversal map. The model must specify how the two mouth clock readings are identified through the interior, the proper-time and redshift accumulated in crossing, and the exterior coordinate transformations at each mouth. Define $\Delta_{AB}$ from that complete matching map; do not silently equate it to $\Delta\tau_{\rm kin}$ when acceleration, gravity, or throat dynamics matter.

For the idealized twin-paradox construction, take a short throat and small mouths, initially colocated and at rest in an approximately Minkowski exterior. Let $T$ be inertial time in the frame where mouth $A$ remains at rest, and let mouth $B$ follow a specified round-trip worldline. If their mouth clocks start synchronized and are identified by equal elapsed mouth proper time through the throat, then

$$
\tau_A(T)=T-T_0,\qquad
\tau_B(T)=\int_{T_0}^{T}\sqrt{1-\frac{v_B^2(T')}{c^2}}\,dT'.
$$

At a reunion event $T_1$, the clock lag is

$$
\Delta_{\rm clock}=\tau_A(T_1)-\tau_B(T_1)
=\int_{T_0}^{T_1}\left(1-\sqrt{1-\frac{v_B^2(T)}{c^2}}\right)dT>0.
$$

In this idealized model the wormhole identification connects mouth events with equal throat-clock readings. A $B\to A$ crossing at reunion can emerge at the earlier exterior event where $A$'s clock reads $\tau_B(T_1)$; the exterior date separation is $\Delta_{\rm clock}$, up to finite throat length, acceleration regions, gravity, and mouth-size corrections. In the notation above, where positive $\Delta_{AB}$ means an earlier $A\to B$ exit, this twin-paradox arrangement has $\Delta_{AB}=-\Delta_{\rm clock}$, while the reverse $B\to A$ traversal has the positive past offset $\Delta_{BA}=+\Delta_{\rm clock}$. This statement depends on the stated identification protocol and inertial frame; a different global identification can give a different map. It is not caused by an interior coordinate shift. The round-trip construction brings the mouths back near one another to make the clock lag and comparison transparent; creating a CTC also requires an exterior return route whose travel time is less than the lag. This is the canonical special-relativistic limit described by Morris, Thorne, and Yurtsever, not a complete solution for a finite, accelerated, self-gravitating wormhole.

**Worked kinematic scale (idealized).** Let mouth $B$ travel at constant speed $0.8c$ for one year of inertial-frame time outbound and one year inbound, with turnaround duration neglected. Then $\gamma=5/3$, the total exterior duration is 2 years, and

$$
\Delta_{\rm clock}=2\,\mathrm{yr}\left(1-\sqrt{1-0.8^2}\right)=0.8\,\mathrm{yr}\approx 2.52\times10^7\,\mathrm{s}.
$$

The idealized path length is 0.8 light-year each way. This is a large clock lag in a hypothetical scenario, not a propulsion design: the mouth's acceleration, stresses, gravity, finite wormhole geometry, and source of the throat are all omitted. Smooth finite-duration acceleration changes the integral and must be included for any specified worldline. For comparison, the flat-space light-time across 384,400 km is approximately 1.282 s; a timelike exterior return across that separation takes longer. The toy lag greatly exceeds that kinematic lower bound, but this comparison alone proves neither a realizable wormhole nor a globally regular CTC spacetime.

Let a traveler enter mouth $A$ at exterior event $p_A$, cross a regular throat in finite proper time $\Delta\tau_w>0$, and exit at $B$ at event $p_B$. In the exterior charts, the matching may yield

$$
T_B(p_B)=T_A(p_A)-\Delta_{AB},
$$

where $\Delta_{AB}>0$ denotes an earlier exterior date at exit. This relation is shorthand for the full geometry's mouth identification, not a discontinuous update of $T$ along a globally valid chart. The worldline includes the approach to $A$, the finite throat traversal, and the departure from $B$; the traveler proper time increases throughout. Which traversal direction yields the earlier exit depends on mouth history and matching convention; derive the sign from those data rather than choosing it after route integration.

For a proposed past-directed traversal, call its entry mouth $I$ and exit mouth $O$, and define the positive offset $\Delta_{\rm past}=T_I(\text{entry})-T_O(\text{exit})$. Define $T_{\rm ext}$ as the exterior elapsed time from the exit event at $O$ to an actual intersection with the entry mouth $I$'s world-tube, computed along a specified future-directed timelike path in the full exterior geometry. The return event must precede the original entry event on $I$; a later timelike segment along the mouth world-tube must then reach that same entry event. A scalar mouth separation alone does not establish this intersection. Define the loop margin

$$
M_{\rm loop}=\Delta_{\rm past}-T_{\rm ext}.
$$

If $M_{\rm loop}>0$ and the specified path intersects $I$'s world-tube as described, the traveler returns to $I$ before the original entry event and can, in the idealized setting, follow a future-directed timelike segment along the mouth world-tube to that same event. $M_{\rm loop}=0$ is a limiting null/closed boundary, not a timelike traveler loop; $M_{\rm loop}<0$ means this proposed return route does not close to the past. A positive margin is only a kinematic closure test for that route, not proof the full spacetime is regular, stable, or physically sourced. If the mouth-offset and return-time uncertainties are bounded by $\sigma_\Delta$ and $\sigma_T$, respectively, a conservative robust condition is $\Delta_{\rm past}-\sigma_\Delta>T_{\rm ext}+\sigma_T$. Otherwise classify closure as indeterminate rather than asserting a CTC.

If the mouths are separated by exterior distance $D$, and an exterior timelike return path from $O$ to $I$ takes duration $T_{\rm ext}$ in the relevant exterior chart, a closed timelike curve becomes possible when

$$
\Delta_{\rm past}>T_{\rm ext}.
$$

Because a massive traveler cannot cover distance $D$ in less than $D/c$ in a local inertial frame, $\Delta_{\rm past}>D/c$ is a necessary scale estimate for a CTC in a nearly flat, static exterior, not a complete condition in a curved or moving-mouth geometry. If the offset exceeds the minimum exterior travel time, a return segment and, if needed, a finite timelike waiting segment can close the curve. For an Earth–Moon center separation near the mean 384,400 km, the flat-space light-travel lower bound is about 1.282 s; a timelike return takes longer. This is only a scale illustration—actual mouth positions, trajectories, gravitational field, and throat transit determine the mission bound. The actual test is global: integrate the exterior and throat segments with one matched geometry and verify that the future-directed timelike curve returns to its initial event. A one-way earlier exit and a CTC are distinct claims. NASA/JPL reports the mean Earth–Moon distance as [384,400 km](https://www.jpl.nasa.gov/edu/resources/lesson-plan/modeling-the-earth-moon-system/).

## 4. Stress-energy and known obstacles

### 4.1 When the craft is a spacetime bubble

The product premise that Astrarium's saucer hull is enclosed by a moving spacetime bubble should be modeled separately from the moving-mouth wormhole above. A bubble warp metric and a wormhole throat are different geometries with different causal structures and source terms; equations from the two cannot be combined as though they described one device. An Alcubierre-type bubble can transport a payload through a chosen exterior history in its standard construction, but that ansatz does not by itself provide a past-directed exterior arrival. Superluminal bubble configurations raise separate horizon and causality issues; historical time travel requires a full global construction, not just a local bubble around the hull.

For a transparent, axisymmetric saucer candidate, use cylindrical coordinates $ (t,x,\rho,\phi) $ with symmetry axis $x$. Define a compact, at least twice continuously differentiable profile with a flat interior and exterior,

$$
f(x,\rho,t)=F\!\left(\frac{\sqrt{(x-X(t))^2/a^2+\rho^2/b^2}-1}{\delta}\right),
\qquad v(t)=\dot X(t),
$$

where $a$ is the axial semiaxis, $b$ the radial semiaxis, and $F(s)=1$ for $s\le-1/2$, $F(s)=0$ for $s\ge1/2$, with a smooth transition between them. The dimensionless $\delta$ sets the wall width in the ellipsoidal coordinate; physical normal thickness varies over the surface. The oblate/saucer geometry uses $a<b$. The line element

$$
ds^2=-c^2dt^2+[dx-v(t)f(x,\rho,t)dt]^2+d\rho^2+\rho^2d\phi^2
$$

is an **ansatz**, not a derived solution. At $f\simeq1$, the hull is carried near $x=X(t)$; outside the wall $f\simeq0$, the metric is Minkowski in these coordinates. The hull world-tube, bubble interior, and finite transition layer are distinct objects. The field wall is not a material collision surface by definition. The metric is regular only if the selected $F$, its derivatives, $X(t)$, and boundary behavior meet the needed smoothness conditions; sharp edges make curvature and source terms singular or distributional.

In ADM form this ansatz has lapse $N=1$, spatial metric $h_{ij}=\delta_{ij}$ in Cartesian coordinates, and shift $\beta^x=-vf$. Its Eulerian observers have four-velocity normal to the $t=\mathrm{constant}$ slices and measure energy density $\epsilon=T_{\mu\nu}n^\mu n^\nu$. For a constant-velocity, one-dimensional bubble segment, the Einstein constraint gives

$$
\epsilon=-\frac{c^2}{32\pi G}\left[\left(\frac{\partial (vf)}{\partial y}\right)^2+
\left(\frac{\partial (vf)}{\partial z}\right)^2\right],
$$

where $y,z$ are transverse Cartesian coordinates; equivalently, the negative density is proportional to the squared transverse gradient of the shift. For a compact, rapidly decaying shift in this unit-lapse flat-slice metric class, the pointwise Eulerian density is negative somewhere for the chosen profile; this is a result for this ansatz, not a theorem that all warp metrics violate the WEC. Acceleration $\dot v\ne0$, axisymmetric wall stresses, and nonzero shear require the full Einstein tensor and all stress components; the displayed constraint alone is not a complete source audit. For any proposed $F,a,b,\delta,X(t)$, compute $T_{\mu\nu}=c^4G_{\mu\nu}/(8\pi G)$, verify $\nabla_\mu T^{\mu\nu}=0$, regularity, and the relevant energy conditions before claiming a sourced solution.

An order-of-magnitude calculation illustrates why a saucer silhouette is not enough to specify a drive. Near a locally planar wall with characteristic normal thickness $L$, take a shift change of order $v$ across $L$. Then

$$
|\epsilon|\sim\frac{c^4}{32\pi G}\left(\frac{v}{c}\right)^2\frac{1}{L^2}
\approx 1.21\times10^{42}\left(\frac{v}{c}\right)^2\left(\frac{1\,\mathrm m}{L}\right)^2\mathrm{J\,m^{-3}}.
$$

For a 10 m axial semiaxis, 20 m radial semiaxis, dimensionless wall parameter $\delta=0.1$, and $v=0.1c$, the wall is roughly 1–2 m thick depending on surface location. The local scale is around $10^{40}\,\mathrm{J\,m^{-3}}$. For the integral, take $s=(q-1)/\delta$, $q=\sqrt{(x/a)^2+(\rho/b)^2}$, and $u=s+1/2$ in the transition layer $-1/2<s<1/2$; set $F=1-10u^3+15u^4-6u^5$ there and use the constant plateaus outside. This yields a $C^2$ metric profile and makes the quadrature reproducible. Direct integration of its Hamiltonian-constraint density gives

$$
\int \epsilon\,dV=-1.4411\times10^{43}\,\mathrm J,
\qquad \frac{1}{c^2}\int\epsilon\,dV=-1.6034\times10^{26}\,\mathrm{kg}.
$$

For this profile, the three-dimensional integral reduces exactly to

$$
\int\epsilon\,dV=-\frac{c^2v^2a}{12G\delta}\left(\frac{10}{7}+\frac{5\delta^2}{154}\right).
$$

To see the reduction, axisymmetry gives $(\partial_y f)^2+(\partial_z f)^2=(\partial_\rho f)^2$, so

$$
\int\epsilon\,dV=-\frac{c^2v^2}{16G}\int_{-\infty}^{\infty}\int_0^\infty
\rho\,(\partial_\rho f)^2\,d\rho\,dx.
$$

With $X=x/a$, $R=\rho/b$, and polar coordinates $(X,R)=(q\cos\theta,q\sin\theta)$ on the half-plane $R\ge0$, the $b$ dependence cancels and the angular integral is $\int_0^\pi\sin^3\theta\,d\theta=4/3$. For the quintic transition, $\int_{-1/2}^{1/2}(1+\delta s)^2[F'(s)]^2ds=10/7+5\delta^2/154$. This gives the expression above.

Notably, the integral is independent of the radial semiaxis $b$ for this particular profile and is proportional to axial semiaxis $a$. Halving $a$ at fixed $b,\delta,v$ halves this slice integral; changing $b$ alone does not change it. This is a result about this ansatz, not a universal shape-optimization law. The reproducible calculation is [`scripts/estimate_saucer_bubble_source.py`](../scripts/estimate_saucer_bubble_source.py). This is the slice integral of Eulerian energy density for the prescribed shift metric, not an ADM mass, full stress-energy audit, or demonstrated energy budget. The stress tensor includes pressures and momentum flux, and the integral does not show that any quantum state can source the metric.

The metric also has an important interpretive limit: when $v(t)$ is prescribed, the bubble's motion is an input trajectory, not a solved response to a propulsion system. There is no drive actuator or control equation in this ansatz. For superluminal coordinate bubble speed, horizons can prevent the onboard crew from creating or controlling the bubble wall on demand from inside; this is a global causal limitation, not fixed by choosing a saucer-shaped profile. A route planner may integrate a test worldline through this metric, but it cannot label it a controllable vehicle trajectory until a physically consistent formation and control model is supplied.

Most importantly for Astrarium's temporal-navigation premise, $t$ above is a global time function for the regular prescribed-bubble metric: $g^{tt}=-1/c^2<0$ for every value of the prescribed shift, so constant-$t$ slices are spacelike and every future-directed causal worldline advances in $t$. This single-bubble spacetime is globally hyperbolic and contains no closed causal curve, even if the bubble center has superluminal coordinate speed. A traveler can have a coordinate $dx/dt$ that differs greatly from local intuition, but cannot arrive at a lower $t$ along a future-directed timelike path in this metric. However, two-bubble constructions with smooth rest-frame transitions have been shown to admit closed timelike geodesics; see Section 4.2. Those use a different global metric, including a non-unit lapse during the frame transition. Superposing two copies of this unit-lapse metric is not enough to reproduce that result. Thus this bubble is a useful one-leg geometry for the saucer craft, but it does **not alone** solve the past-arrival mission.

### 4.2 Two-bubble rest-frame-transition CTC

This is the closest published mathematical model found so far to a continuous A.R.G.O. time-travel route, but its vehicle interpretation has a gap. Shoshany and Snodgrass construct a spacetime in which one test traveler follows two distinct compactly supported warp-field regions, changes inertial rest frame through a finite metric transition, and returns to the starting spacetime event along a closed timelike geodesic (CTG). The traveler is not teleported: the worldline is continuous, future-directed, and has increasing proper time. But the paper does not make one material bubble persist through both field supports, or specify a saucer hull, its stress, or its coupling to either support. For this draft, A.R.G.O. is the test payload/worldline. Identifying it with the source of the prescribed metric is an additional open matter-and-geometry problem.

### A.R.G.O. reference vehicle and concept geometry

The supplied A.R.G.O. concept rendering shows a roughly 14 ft (4.267 m) diameter trampoline/projection dome, a 23.7 ft (7.224 m) outside diameter across the planted berm and solar-panel footprint, a 7 ft (2.134 m) above-ground height, and a berm approximately 3 ft (0.914 m) high. It also depicts an underground equipment/storage volume, but gives no below-ground depth or footprint. These are visual concept dimensions, not a surveyed engineering drawing; they constrain a first envelope model, not mass, material strength, or field-source geometry.

```{figure} ./_static/images/argo-aluminet-canopy.png
:width: 760px
:alt: A.R.G.O. concept with a reflective mesh Aluminet layer over the observatory dome, with solar panels and the entrance left clear.

Updated concept illustration showing the requested Aluminet canopy as a distinct outer shade layer. The mesh is shown over the dome while the entrance and solar-panel faces remain clear. This is an architectural visualization, not a construction drawing or evidence of measured thermal or electromagnetic performance.
```

| Rendering dimension | SI value | What it constrains |
|---|---:|---|
| Outer footprint diameter | 7.224 m | Maximum visible radial extent of the surface installation; not necessarily the moving hull |
| Trampoline/dome diameter | 4.267 m | Upper occupied/projection volume diameter |
| Above-ground height | 2.134 m | Visible vertical envelope above local ground |
| Berm height | 0.914 m | Terrain/array elevation around the perimeter |
| Underground compartment | Unspecified | Extends the occupied envelope and may dominate mass; cannot be bounded from this rendering |

For a preliminary *visible-envelope* curvature screen only, set the hull radial scale to $L_r=3.612\,\mathrm m$ (half the outer footprint diameter) and the vertical scale to $L_z=2.134\,\mathrm m$. Those scales are deliberately conservative for the visible installation, but the buried room means the full ship envelope is unknown. The centerline-to-hull test must therefore use a measured three-dimensional envelope, including hatch, legs, supports, buried structure, and clearance, before it can pass. The bubble's passenger region must contain that full envelope plus a specified clearance; the metric wall must lie outside it. Solar panels and berm are ordinary power/site infrastructure and do not supply a temporal-drive stress-energy tensor.

The rendering labels each flexible panel as 300 W and 58.3 by 27.6 in (1.481 by 0.701 m). A rough radial tiling of the annulus, excluding the stated entrance gap and allowing no allowance for spacing or shading, suggests on the order of 20 panels or 6 kW nameplate. This is only a layout-scale estimate: exact panel count, orientation, shading, storage, and duty cycle are absent. Even a verified electrical budget would constrain conventional subsystems; it would not establish the energy source or feasibility of the spacetime metric.

The A.R.G.O. exterior will be covered by an Aluminet canopy: a reflective, knitted shade layer supported outside the dome and shell. Commercial Aluminet products are metalized HDPE knit with open mesh, and are sold in multiple shade densities; the specific grade, color, coverage, and measured optical properties remain design inputs. [Product construction and shade options](https://www.ecologictechnologiesinc.com/shade_cloth_films_screens_greenhouse_shade_cloth_aluminet.html), [Aluminet specification sheet](https://www.hummert.com/content/files/pdf/496-497.pdf). The first-pass installation should stand off from the shell to preserve an air gap and be divided into removable or retractable panels around the projection aperture, entrance, rear hatch, vents, sensors, antennas, and solar-panel faces. The panels should not shade the photovoltaic surfaces in their deployed operating configuration; the edge treatment and support frame must also preserve egress and drainage. These interface details need a site drawing and an installed thermal test.

Aluminet is the ship's outer shade/thermal-control layer, not its Faraday cage. Because standard Aluminet is an open knit rather than an electrically continuous metal skin, it cannot be assumed to provide enclosure shielding; this is an engineering inference from its stated construction, and any EMC benefit would require testing in the actual installed configuration. The inner conductive enclosure and its bonded seams, penetrations, and shielding tests remain specified below. Neither layer is credited with ionizing-radiation protection or any temporal-drive effect.

### Crew enclosure and participant apparel

The A.R.G.O. concept includes a conductive Faraday enclosure around the occupied cabin and sensitive electronics. Its design target is electromagnetic compatibility and electrostatic-discharge control: a continuous conductive skin, electrically bonded seams and hatch, and filtered or shielded penetrations for power, data, ventilation, and antennas. The projection dome, entrance, rear hatch, and service openings interrupt a simple conductive shell; transparent conductive coatings or screened apertures would need measured performance and must be reconciled with the optical projection and radio links. The enclosure specification should state frequency bands and attenuation in dB, then verify them with an installed-system shielding-effectiveness test. NASA spacecraft practice likewise places sensitive electronics in conductive enclosures and treats exposed dielectric surfaces and bonding as part of the design. [NASA preferred practice for spacecraft electrostatic-discharge control](https://extapps.ksc.nasa.gov/Reliability/Documents/Preferred_Practices/1244.pdf)

Define the cage's performance as a frequency-dependent test result, not a material label. For field amplitude, report electric-field shielding effectiveness

$$
SE_E(f)=20\log_{10}\!\left(\frac{E_{\rm ref}(f)}{E_{\rm in}(f)}\right)\;\mathrm{dB},
$$

with the reference measurement taken in the same test geometry without the enclosure. Measure magnetic-field attenuation separately where near-field or low-frequency sources matter; one scalar “Faraday cage” rating cannot cover electric and magnetic coupling in every regime. Specify source polarization and distance, frequency sweep, interior probe locations, door/hatch state, and the as-operated state of ventilation, optical windows, power/data feedthroughs, and antennas. Publish the minimum attenuation over each declared band and configuration. Until bands and required thresholds are selected and the assembled system is measured, the design has no demonstrated shielding effectiveness. Any external radio link must use an engineered feedthrough or antenna arrangement and be included in the same configuration record.

A Faraday enclosure is not a general-purpose space-radiation or temporal-drive shield. It can reduce electric-field and radio-frequency coupling when its openings and bonds are engineered for the frequencies of interest; it does not stop high-energy ionizing particles merely because the wall is conductive. NASA distinguishes solar-particle shielding from the harder galactic-cosmic-ray problem, where energetic particles can generate secondary radiation in spacecraft walls and shielding must be evaluated by material, areal density, spectrum, and dose. The enclosure does not modify the spacetime metric or protect against curvature or tidal forces. [NASA on space-radiation protection](https://www.nasa.gov/science-research/heliophysics/real-martians-how-to-protect-astronauts-from-space-radiation-on-mars/)

Participants are shown wearing reflective orange emergency ponchos as A.R.G.O. mission apparel. This illustration is a concept image, not a photograph of an actual crew or a safety test. A lightweight poncho may serve as ordinary emergency clothing, but it is not a pressure suit, oxygen supply, fire-protection system, radiation shield, or substitute for a tested cabin shelter. Do not count it toward Faraday-cage attenuation or crew dose reduction.

```{figure} ./_static/images/argo-crew-ponchos.png
:width: 760px
:alt: Adults and children in orange and silver reflective emergency ponchos beneath the star projection inside the A.R.G.O. dome.

Concept illustration of adults and children in A.R.G.O. participant ponchos. The image shows the proposed look of the crew apparel; it makes no claim about NASA manufacture, flight qualification, or protective performance.
```

The separate oblate, unit-lapse source calculation later in this note is not a model of the rendering. Substituting $a=2.134\,\mathrm m$ and $b=3.612\,\mathrm m$ into that ansatz would be a convenient dimensional sensitivity check, but the pictured dome-plus-berm-plus-buried-volume is neither that profile nor the two-bubble non-unit-lapse metric. Its slice integral cannot be interpreted as A.R.G.O.'s mass, required energy, or drive budget. A source calculation for this design first needs an explicit spacetime metric and source tensor, then a defined mapping from the built hull and field wall into that metric.

For a useful finite-ship calculation, the next design inputs are: (i) the full hull and buried-volume CAD envelope and its center of mass; (ii) mass, inertia tensor, materials, joints, and allowable acceleration/tidal loads; (iii) bubble passenger-region dimensions, wall thickness, and their orientation relative to the hull; and (iv) the metric and stress-energy tensor that couple the field to the hull. Until these are supplied, the rendering yields scale constraints for collision and tidal screens, but no numerical pass/fail result for a real craft.

#### The Earth departure boundary

The rendering places A.R.G.O. partly below grade and surrounds it with a planted berm and solar panels. A time-travel route cannot begin at an abstract point above that drawing: its departure state must identify what physically leaves the ground. There are two distinct vehicle definitions. In the **whole-installation** case, the dome, buried compartment, berm, panels, and any soil or foundation carried inside the field all belong to the moving system; their mass and full envelope must be included. In the **detachable-craft** case, a defined hull separates from a stationary site, and the model must include the detachment, ground clearance, and any structures or utilities left behind. The concept image specifies neither boundary, and it depicts no lift, thrust, or release mechanism. A solver that starts A.R.G.O. already clear of terrain has skipped a required continuous segment of the mission.

As a conventional-gravity reference only, raising a mass $M$ from Earth's surface to infinity requires Newtonian potential-energy change

$$
\Delta E_{\rm grav}=\frac{GM_\oplus M}{R_\oplus},
\qquad v_{\rm esc}=\sqrt{\frac{2GM_\oplus}{R_\oplus}},
$$

or about $6.3\times10^7\,\mathrm{J\,kg^{-1}}$ and $11.2\,\mathrm{km\,s^{-1}}$ for Earth, using NASA's Earth mass-parameter, radius, and escape-speed values. These are idealized surface-to-infinity scales: they omit rotation, atmosphere, finite launch losses, terrain release, and any field coupling. They are not an estimate of A.R.G.O.'s launch energy because its moving mass and departure mechanism are unknown, and they are not a warp/CTC energy budget. If the temporal metric is supposed to alter the support force or carry Earth material with the craft, that interaction must be stated in the metric and source model rather than silently replacing the launch segment.

The mission initial condition must therefore give the complete departure event, the vehicle-versus-site boundary, the mass and center-of-mass state, clearance from terrain and atmosphere, and the outgoing four-velocity. Only after the hull world-tube is disjoint from the ground and stationary site can the exterior route and collision screening be initialized. This is also necessary to distinguish “A.R.G.O. will appear in an ancient sky” from a simulation that has merely assigned it an ancient coordinate.

### Conditional extension: from a test traveler to a finite ship

The published compact profile distinguishes the inner passenger-region radius $r_1$ from the outer support radius $r_2$, with $r_2>r_1$. If $\mathcal H(\tau)$ is the finite hull in the bubble-centered orthonormal rest space, define its required radius as $R_H=\sup_{\tau,\,p\in\mathcal H(\tau)}|\mathbf X_p(\tau)|$. A necessary geometric containment condition is

$$
R_H+m\le r_1<r_2,
$$

where $m$ is a declared hull-to-wall clearance. The outer radius is not a free visualization scale: in the paper's transition profile $N=1-b(t)(z-Z)s(r)$, $t_2=T_2-u\gamma_u r_2$, $T_1=\omega T_2$, and $0\le s\le1$. In units $c=1$, the bump $q(x)=140x^3(1-x)^3$ has maximum $35/16$, while $\lambda\le\gamma_u=(1-u^2)^{-1/2}$. Hence a conservative bound is

$$
0\le b(t)\le b_{\max}\equiv\frac{u\gamma_u^2(35/16)}{t_2-T_1},\qquad N\ge1-b_{\max}r_2.
$$

Therefore $b_{\max}r_2<1$ is sufficient (not necessary) for positive lapse throughout this spherical support. Substituting $t_2-T_1=(1-\omega)T_2-u\gamma_u r_2$ gives the conservative parameter interval

$$
R_H+m\le r_1<r_2<\frac{(1-\omega)T_2}{u\gamma_u^2(35/16)+u\gamma_u}.
$$

This is only a profile-level regularity/containment screen; it does not prove the stress-energy is realizable, that the CTC closes through a target event, or that the hull is safe. For scale, the reference drawing's outer installation radius is 3.612 m if the entire surface installation travels. Choosing $r_1=10$ m would contain that visible radial scale with 6.388 m of nominal margin, but the drawing leaves the underground extent and grade datum unresolved, so this does not establish full containment. The paper's plotted $r_2=1$ km is an example support scale, not a prescribed A.R.G.O. design. Every return-bubble quantity must be checked in its hatted frame as well. The source also notes that its explicit CTC does not lie inside the generic globally flat finite passenger cylinder used in its broader rest-frame-transition discussion; thus one cannot infer zero hull tides for the complete loop merely from an inner-radius label. Curvature must be evaluated along the actual CTC and across the finite hull. [Source metric and parameter definitions](https://arxiv.org/html/2309.10072v3).

The published CTG is a centerline for a test traveler in a prescribed metric. To ask whether the rendered A.R.G.O. can follow it, promote that centerline to the center of a finite occupied world-tube. Let $u^\mu=dx^\mu/d\tau$ be the centerline four-velocity and let $\xi^\mu$ be a small separation to a neighboring freely falling point on the hull, expressed in a Fermi-transported local frame. In the small-body, geodesic approximation, relative displacement obeys geodesic deviation,

$$
\frac{D^2\xi^\mu}{D\tau^2}=-R^\mu{}_{\nu\alpha\beta}u^\nu\xi^\alpha u^\beta.
$$

This provides a first physical screen the point-particle result does not: the curvature along the centerline produces differential acceleration across the ship. In a local orthonormal frame, a useful order scale is

$$
a_{\rm tidal}\sim c^2\,\|R_{\hat 0\hat i\hat 0\hat j}\|\,L,
$$

where $L$ is the relevant hull dimension and the curvature norm is evaluated in the ship's frame. A candidate trajectory must report the maximum tidal tensor eigenvalue, hull extent and orientation, and compare the resulting differential acceleration with declared crew and structure limits. It must also check that the entire hull world-tube—not only its centerline—remains inside the passenger region and avoids the finite-support field walls and the second bubble's support. The paper's geodesic alone supplies none of these values.

This is only a test-body extension, not a self-sourced ship solution. Its validity requires the craft's stress-energy and gravitational backreaction to be negligible for the prescribed metric, the curvature to vary smoothly over the hull scale ($L^2\|R\|\ll1$), and non-gravitational forces to be either negligible or explicitly modeled. A small compactness estimate $2GM_{\rm ship}/(c^2L)\ll1$ is a useful necessary screen in a weakly curved exterior, but it does not bound backreaction on a chronology horizon or prove that the bubble field can carry the hull. Geodesic deviation treats neighboring freely falling test points; it is not a rigid-body or materials model. A physical hull calculation must solve for internal stress and deformation under the tidal field, maintain stress-energy conservation, and include any propulsion or field-wall forces. If these effects cannot be treated as small, one must solve a coupled metric, source, and finite-body problem. The published two-bubble construction is therefore a geometry in which a test traveler can follow a CTG, not a design for a single saucer that generates its own time machine. [Shoshany and Snodgrass](https://arxiv.org/abs/2309.10072)

### Conditional extension: from a trajectory to an observed sighting

A craft crossing a historical event is not yet a predicted sighting. Let $x^\mu_{\rm em}$ be a candidate emission or scattering event on the ship's hull world-tube, and let $O^\mu(\tau_o)$ be a witness worldline. A visible encounter requires a future-directed null geodesic $k^\mu(\lambda)$ of the same spacetime to connect those events:

$$
\frac{dx_\gamma^\mu}{d\lambda}=k^\mu,\qquad
k^\nu\nabla_\nu k^\mu=0,\qquad
g_{\mu\nu}k^\mu k^\nu=0,\qquad
x_\gamma^\mu(\lambda_e)=x_{\rm em}^\mu,\quad
x_\gamma^\mu(\lambda_o)=O^\mu(\tau_o).
$$

The measured frequency is proportional to $-u_\mu k^\mu$ at each endpoint, where $u^\mu_{\rm em}$ is the local emitting-surface four-velocity and $u^\mu_{\rm obs}$ is the observer four-velocity. The predicted redshift is

$$
1+z=\frac{(-u_{{\rm em}\,\mu} k^\mu)_{\rm emission}}{(-u_{{\rm obs}\,\mu} k^\mu)_{\rm observation}}.
$$

The observer's local tetrad then gives the apparent direction and angular track. A brightness prediction additionally needs a stated emission or reflection law, craft orientation and occultation geometry, and propagation through any field wall. A chronology-violating metric may admit more than one null-geodesic branch between an emitter and observer; the solver must enumerate branches within its domain and distinguish multiple optical paths from multiple craft. This makes the sighting constraint a boundary-value problem for the ship world-tube, witness worldline, and photon null geodesics in one declared metric. A plotted craft marker at an ancient coordinate time does not establish that its photons reach a witness there. For the Bethlehem scenario, the observer coordinates and historical event time remain unconstrained inputs; for a modern UFO report, timestamp, observer state, angular measurements, and source provenance must be supplied by the record.

These extensions define a tractable development sequence: first reproduce the paper's point-particle CTG in its exact prescribed metric; then propagate a finite test-body envelope and tidal tensor; then solve ship-to-observer null-geodesic boundary conditions; only after those pass should an astrophysical encounter or collision screen be attached. None of the later stages should be inferred from success at the preceding stage.

In units $c=1$, each warp region uses the ADM form

$$
ds^2=-N^2dt^2+\delta_{ij}(dx^i-\beta^i dt)(dx^j-\beta^jdt).
$$

The non-unit lapse $N(t,\mathbf x)>0$ is essential to the rest-frame transition: while the shift-supported field fades smoothly, the test geodesic exits into flat space with a changed inertial four-velocity. The return field is defined in a Lorentz-boosted frame. Compact support and a finite spatial sidestep keep the two curved regions disjoint, so their metric perturbations can be joined without assuming negligible field overlap. In the flat interval the traveler can follow a timelike segment back to the original departure event, closing the CTG. The time map $t(\tau)$ is continuous and piecewise differentiable; $\tau$ increases throughout even where $dt/d\tau<0$.

For the idealized symmetric case, let $V=\bar v/c>1$ and $\hat V=\hat{\bar v}/c>1$ be the average warp-bubble speeds in the two respective inertial frames, and let $U=u/c\in(0,1)$ be their relative frame speed. If the first leg lasts coordinate time $T_2$ in frame $S$, the second leg returns to the starting spatial point at

$$
\frac{T_{\rm finish}}{T_2}
=\frac{V+\hat V-U(1+V\hat V)}{\hat V-U}.
$$

The condition for $T_{\rm finish}<0$ is

$$
U>\frac{V+\hat V}{1+V\hat V}.
$$

For equal average speeds $V=\hat V=V_0$, this reduces to $U>2V_0/(1+V_0^2)$. The explicit smooth-profile example in the paper chooses $U=0.75$, an acceleration-profile parameter $\alpha=10$, and a duration ratio $\omega=T_1/T_2=0.95$, which gives

$$
V_0=U\left(1+\frac{\omega}{4}(\alpha-1)\right)=2.353125,
\qquad U_{\rm crit}=\frac{2V_0}{1+V_0^2}\approx0.71992,
\qquad \frac{T_{\rm finish}}{T_2}\approx-0.12267.
$$

Thus this worked construction reaches an event about $0.123T_2$ before departure in the external $S$ time coordinate, then the worldline's flat-space segment proceeds forward to close at $t=0$. The result is a geometric existence proof within the prescribed metric, not an engineering forecast. Both legs have superluminal **average separation speed** in their respective frames; the traveler’s local four-velocity remains timelike. The paper does not provide a known way to generate or control its lapse/shift fields. For the flat-slice, non-unit-lapse metric class, the authors prove WEC violation under stated smoothness, falloff, and non-degeneracy conditions; they also discuss exceptional cases and a lapse-dependent reduction of integrated Eulerian density that lengthens onboard duration. Do not generalize that result to every possible warp metric. A physical source and control system, and backreaction and quantum-field consistency, remain open.

The time-shift condition also imposes a large spatial excursion in this symmetric model. Let the first-leg displacement be $D=V_0cT_2$ in $S$, and define the positive lookback $\Delta=-T_{\rm finish}$. Then

$$
\frac{\Delta}{D/c}=\frac{U(1+V_0^2)-2V_0}{V_0(V_0-U)}<U<1.
$$

Consequently, an idealized return to the *same inertial spatial point* requires an outbound displacement greater than the lookback measured in light-years; for the paper's explicit parameter set the ratio is about 0.05213. This is a coordinate scale from the flat symmetric model, not a Bethlehem route. It underscores that a warp-drive time machine is not a short local maneuver: the return must exploit a large spacelike separation between frame-related legs.

The same flat-background kinematics can be written for a nonzero target displacement. In units $c=1$, with time measured in years and distance in light-years, start at $A=(0,0)$, let the first leg end at $B=(T,VT)$, and let the return leg have average velocity $-V$ in the frame $S'$, which moves at speed $U$ relative to $S$. Frame $S$ is the traveler's departure-comoving inertial frame: the published construction starts the traveler at rest there before the first warp leg. If its endpoint is $C=(t_C,z_C)$ in $S$, Lorentz transforming the return displacement and imposing $\Delta z'=-V\Delta t'$ gives

$$
t_C=\frac{2V-U(1+V^2)}{V-U}\,T+
\frac{VU-1}{V-U}\,z_C.
$$

### A lower bound for the symmetric endpoint extension

The nonzero-target endpoint extension above admits a useful parameter-independent scale check. Keep its assumptions: equal average bubble speeds $V>1$, frame speed $0<U<1$, first-leg duration $T>0$, and a target endpoint $C=(t_C,z_C)$ in the departure-comoving frame $S$. In units $c=1$, the endpoint equation is $t_C=aT+bz_C$, with

$$
a=\frac{2V-U(1+V^2)}{V-U},\qquad b=\frac{VU-1}{V-U}.
$$

For the time-travel branch $a<0$. Also,

$$
b+1=\frac{(V-1)(U+1)}{V-U}>0,\qquad 1-b=\frac{(V+1)(1-U)}{V-U}>0,
$$

so $-1<b<1$. Writing $L=-t_C>0$, the first-leg distance is

$$
D=VT=L(1-br)\frac{V}{-a},\qquad r=\frac{z_C}{t_C}.
$$

The symmetric CTC condition $U>2V/(1+V^2)$ gives $U(1+V^2)-2V>0$ [as derived for the published model](https://arxiv.org/abs/2309.10072). Since $U<1$ and $V>1$,

$$
V(V-U)-[U(1+V^2)-2V]=V^2+2V-U(V^2+V+1)>V-1>0,
$$

so $V/(-a)>1$. If the target is timelike-separated from departure ($|z_C|<|t_C|$), then $1-br\ge1-|r|>0$. Therefore

$$
D>|t_C|-|z_C|.
$$

With the notebook's central one-axis transformation for the 6 BCE scenario, this is $D>2030.80$ light-years; the selected published parameters give about 38,963 light-years. The lower bound persists as $U$ and $V$ are varied within this symmetric endpoint algebra, so parameter tuning cannot make this *endpoint construction* a local Solar-System route. It is not a theorem about every point along the published closed geodesic or every possible time-machine geometry. In particular, assigning a nonzero-displacement Earth event to $C$ does not solve the finite-support metric's endpoint tangent matching or the geodesic boundary-value problem. This is a kinematic obstruction for the proposed endpoint retargeting, not a navigated route or a universal no-go result.


**Frame-consistent target estimate.** Multiplying $230\,\mathrm{km\,s^{-1}}$ by 2,031 years gives 1.56 light-years in a Galactic frame, but that is not the target displacement $z_C$ in $S$: the published model's $S$ frame is the traveler's initial rest frame, and its illustrative first leg starts from rest there. The Sun's shared Galactic drift must be transformed together with A.R.G.O.'s departure velocity, while Earth's orbital velocity remains in the departure-frame target offset. For a one-axis scale case, assume the Sun's Galactic velocity and Earth's orbital velocity are collinear, with $\beta_s=v_s/c$, $\beta_e=v_e/c$, and $\beta_0=(\beta_s+\beta_e)/(1+\beta_s\beta_e)$ for A.R.G.O.'s departure speed in a Galactic inertial frame. Approximate the historical Earth center as sharing the Sun's linear Galactic drift and returning to the same heliocentric orbital phase, so $(\Delta t_G,\Delta z_G)=(-L,-\beta_s L)$. The Lorentz transform to the departure frame is

$$
\Delta t_S=\gamma_0(\Delta t_G-\beta_0\Delta z_G),\qquad
\Delta z_S=\gamma_0(\Delta z_G-\beta_0\Delta t_G),\qquad
\gamma_0=(1-\beta_0^2)^{-1/2}.
$$

For $L=2{,}031$ years, $v_s=230\,\mathrm{km\,s^{-1}}$, and Earth's mean orbital speed $v_e=29.78\,\mathrm{km\,s^{-1}}$, this gives $\Delta t_S\approx-2{,}030.9994$ years and $\Delta z_S\approx0.20175$ light-years. The leading position offset is the Earth's orbital velocity times the lookback, because the departure frame follows the present Earth velocity while the historical Earth remains near its solar orbit; it is not the Sun's Galactic travel distance. This is a deliberately simplified collinear projection, not a reconstructed Earth or Bethlehem-observer worldline.

The calculator adds a projected sensitivity envelope of $\pm2$ AU for Earth's unknown orbital-phase difference, up to $0.465\,\mathrm{km\,s^{-1}}$ for an equatorial site's rotational velocity projected along the chosen axis, and $2.87$ AU for the local circular-Galactic-orbit curvature scale from $v_s^2/R$ with $R=8.2\,\mathrm{kpc}$. Added as absolute one-axis bounds, these give approximately $\Delta z_S=0.20175\pm0.00323$ light-years; they are not statistical errors or a complete uncertainty budget. The circular-orbit and radius assumptions are illustrative, and exact Earth and observer states require an ephemeris in a declared frame.

Using the transformed target event and the same illustrative $V=2.353125$, $U=0.75$, the flat endpoint equation gives $T\approx16{,}558.02$ years and first-leg separation $VT\approx38{,}963.09$ light-years. The projected position envelope changes the first-leg time only by about $0.013$ years on either side. The target and departure events are timelike-separated in this flat extension: a straight segment from the target event back to departure would have speed about $-29.78\,\mathrm{km\,s^{-1}}$ in the chosen axis and proper duration about $2{,}030.9994$ years. This checks only endpoint separability. It does **not** show that this segment's tangent matches the return-bubble exit four-velocity, that the entire path is a smooth geodesic, or that the point is on the published CTG. The corrected endpoint still demands a galactic-scale excursion in algebra that assumes one flat inertial background and omits Galactic gravity. This is a diagnostic failure of the endpoint extension as a mission-scale route, not a Bethlehem trajectory. Choosing a different inertial frame is allowed, but then the initial state, target event, and both leg transformations must all be transformed consistently. Neither version retargets or integrates the paper's compact-support metric. The calculation is reproducible with [`scripts/estimate_two_bubble_ctc.py`](../scripts/estimate_two_bubble_ctc.py); it does not close a CTG through the Bethlehem observation region or establish that the narrative describes a physical moving object. [The source construction's initial rest frame and example parameters](https://arxiv.org/html/2309.10072v3)

(phoenix-encounter-gap)=
**Bethlehem encounter gap.** The published construction gives a closed loop: after positive proper time, the test traveler returns to the *same spacetime event* where it began. It does not give an open-ended vehicle that arrives at an earlier event and then proceeds to a distinct later departure event; the Bethlehem-era encounter must lie on the closed loop, with a future-directed continuation around it. The nonzero-endpoint equation above is only a flat-background kinematic extension for one leg; it is not a retargeted compact-support metric or a closed loop through a historically constrained event. A valid reference mission must solve the entire CTG, include a candidate event region and the rays to the Magi, then check closure back to a declared event/state under the chosen self-consistency rule. The source narrative supplies no exact date, observer coordinates, angular track, range, or duration, so those must remain scenario inputs with broad uncertainty rather than invented measurements. The corrected endpoint is an illustrative Lorentz-transformed scale case, not a reconstructed Earth/Magi worldline; its one-axis collinearity assumption is especially inadequate for collision screening. Both supports must stay disjoint, the finite hull must fit in each passenger region, and $N>0$ everywhere. Replacing the paper's spherical supports with the oblate profile in Section 4.1 is another unproved change: that unit-lapse density integral does not determine the source tensor for the non-unit-lapse CTG metric. This extension needs an independent Einstein-tensor, energy-condition, and collision calculation.

The bubble route must still collision-check the hull and external bodies in a common local frame. In addition, the geometry changes photon and matter trajectories through the wall; a physical encounter model must propagate light from the craft to candidate observers through the same metric, include wall stress-energy and radiation interactions, and compare the predicted apparent path with the source narrative. In multi-pass scenarios, compare every pass's hull world-tube and field region at common spacetime events and specify a self-consistency/interaction rule. Treating two plotted passes as the same craft does not establish that their metrics can coexist without collision, destructive field interaction, or causal inconsistency.

(crew-experience)=
### 4.3 Crew experience and the weak-interaction hypothesis

The CTC geometry gives A.R.G.O. a precise temporal orientation: along the hull worldline, proper time $\tau$ increases and the crew's physical records, metabolism, and memory formation proceed locally in their ordinary thermodynamic direction. The exterior epoch $E(\tau)$, defined by calibrated clocks outside the bubble, can decrease on part of the route. In this limited sense the crew would encounter external epochs in reverse order while living forward aboard the ship. That is not consciousness itself running backward, and it does not reverse photons or all processes in the crew's local frame. A candidate simulator should track both functions, along with the map from exterior events to onboard observations.

Calling that experience unpleasant or disorienting is a plausible narrative/biological hypothesis, not a prediction of general relativity. The metric alone supplies no psychology. Nor does visiting earlier epochs automatically make the craft unable to interact with people there: local interactions remain possible whenever the relevant worldlines and fields causally meet. A superluminal bubble horizon may limit communication or control between the interior and exterior in some configurations, but it does not by itself make the hull invisible or prevent an encounter. Therefore “they do not interact because they experience time backward” is not an explanation established by this model.

For the product hypothesis, define an interaction policy and propagate signals through the selected metric: crew-to-witness light, witness-to-ship light or matter, radio, heat, and any hull/bubble emission. Predict whether a witness could see, hear, or otherwise detect the craft, and what control messages could reach the crew. Compare those predictions against a preregistered corpus of reports, including non-interactions and failed observations to avoid selecting only apparent matches. A useful hypothesis is that the encounter is brief or weak because the ship's geometry and mission policy constrain signaling, while the crew's reversed external chronology makes sustained coordination difficult. That remains speculative until it yields distinctive, independently testable predictions.

The wormhole geometry in Sections 2–3 must satisfy Einstein's field equation

$$
G_{\mu\nu}=\frac{8\pi G}{c^4}T_{\mu\nu}.
$$

For the static, spherical Morris–Thorne geometry in classical Einstein gravity, the throat flare-out condition requires violation of the null energy condition (NEC) somewhere at or near the throat: for some null vector $k^\mu$, $T_{\mu\nu}k^\mu k^\nu<0$. “Exotic matter” here is a statement about this stress-energy condition; it is not a specified material or a proposed engineering recipe. The warp-bubble models also require a source tensor derived from their own metric; wormhole and bubble source calculations cannot be interchanged.

As a diagnostic example only, set $\Phi=0$ and choose the shape function $b(r)=r_0^2/r$, so $ds^2=-c^2dt_w^2+dr^2/(1-r_0^2/r)+r^2d\Omega^2$. In a static orthonormal frame, the throat energy density and radial pressure are

$$
\epsilon(r_0)=-\frac{c^4}{8\pi G r_0^2},\qquad
p_r(r_0)=-\frac{c^4}{8\pi G r_0^2},\qquad
\epsilon+p_r=-\frac{c^4}{4\pi G r_0^2}<0.
$$

This is the source required by the chosen idealized metric under the Einstein equation; it is not evidence such a source exists. Its magnitude scales as $r_0^{-2}$, and the example says nothing by itself about total integrated energy, formation, dynamic stability, quantum state realizability, or backreaction.

Using the 2022 CODATA values $c=299\,792\,458\ \mathrm{m\,s^{-1}}$ and $G=6.67430\times10^{-11}\ \mathrm{m^3\,kg^{-1}\,s^{-2}}$, a throat radius $r_0=1\ \mathrm m$ gives $\epsilon(r_0)\approx-4.82\times10^{42}\ \mathrm{J\,m^{-3}}$, equivalent by division by $c^2$ to about $-5.36\times10^{25}\ \mathrm{kg\,m^{-3}}$. Increasing the radius to 10 m reduces this local magnitude by a factor of 100, to $4.82\times10^{40}\ \mathrm{J\,m^{-3}}$. These are local orthonormal-frame values for this specific static metric, not estimates of the total negative energy required: integrating a source requires the full spatial profile and matching to the exterior, and a physically realizable quantum state must be shown to produce it.

Wormhole-specific unresolved issues include:

1. **Source and energy conditions.** A complete model needs a covariantly conserved stress-energy tensor $\nabla_\mu T^{\mu\nu}=0$, a physical matter/field theory producing it, and consistency with observational and quantum-field constraints. Quantum fields can violate pointwise energy conditions, but that fact does not establish macroscopic, long-lived wormhole support.
2. **Formation and control.** The thought experiment assumes an already existing traversable wormhole and controlled transport of one mouth. No known process creates, enlarges, moves, or stabilizes such an object. Separately, the warp CTC assumes prescribed compact bubble supports and lapse profiles; no known actuator or matter theory forms or controls them, and superluminal bubble horizons constrain crew control.
3. **Backreaction and chronology horizon.** As a configuration approaches chronology violation, semiclassical stress-energy and stability may invalidate the fixed-background solution. Hawking's chronology-protection conjecture is an influential proposal, not a theorem resolving every spacetime.
4. **Initial-value and consistency problems.** CTC spacetimes can fail to admit ordinary global Cauchy data. A simulator must declare whether it imposes global self-consistency, a boundary-value solution, branching histories, or another rule; choosing one changes the model's predictions.
5. **Tidal and radiation hazards.** A navigable throat must meet constraints on tidal curvature, acceleration, traversal duration, radiation and particle flux, mouth environment, and structural clearance. These are not captured by endpoint positions or a simple collision radius.

The moving-mouth wormhole and two-bubble warp CTC are separate conditional GR constructions with unresolved source problems. The single-bubble unit-lapse model is not a temporal drive, while the published two-bubble metric is a mathematical CTC solution for a test traveler with a continuous timelike path. None of these establishes a realizable temporal drive or a mission to a historical sighting.

## 5. Continuous route and navigation state

Represent a mission as a connected, piecewise-smooth curve $\gamma:[\tau_0,\tau_1]\rightarrow\mathcal{M}$, with continuous tangent at segment boundaries. Segments can include exterior approach, bubble transport, the lapse/shift rest-frame transition, flat-space intervals, a second bubble leg in a Lorentz-boosted chart, and (for the wormhole comparator) throat transit. The manifold atlas may change between segments, but the physical event, four-velocity, vehicle state, and proper time must match under the chart transition. No segment may be replaced by a zero-duration state assignment.

At wormhole mouths, impose explicit matching conditions for the induced geometry and the traveler state. For warp drives, supply lapse and shift profiles, finite support, frame transformations, and the conditions that keep (N>0) and the metric at least (C^2). At every transition, the simulation must match the same event, tangent, and craft state, transport attitude consistently, and include any thin-shell surface stress-energy if a junction is used. These are inputs to the field-and-motion model, not hidden implementation details.

For a hazard worldline $h_i(\lambda)$, collision is an invariant world-tube intersection: let $\mathcal W_v$ be the vehicle's occupied spacetime tube and $\mathcal H_i$ the hazard's occupied tube, including physical extent and stated uncertainty. A collision occurs if $\mathcal W_v\cap\mathcal H_i\ne\varnothing$. A safety margin enlarges these tubes in a declared local rest-space geometry; it is not an extra coordinate-time offset. If the finite-body tubes or uncertainty sets cannot be mapped through the throat geometry, clearance is unknown. The reduced Astrarium screen

$$
\|\mathbf r(\tau)-\mathbf b_i(T(\tau))\|>R_i+M_i
$$

is valid only on exterior segments where both states are expressed in a shared local frame and event chart. It cannot be continued through a wormhole by carrying one heliocentric position vector across chart boundaries. Through the throat, screen against the throat's geometry, supporting fields, trapped radiation, and other travelers/objects in the throat. After exit, evaluate hazards in the destination exterior at the actual matched exit event.

The route result must include: the selected metric and parameter source; wormhole mouth histories or warp lapse/shift supports; endpoint/event matching and uncertainty; traveler proper-time duration; four-velocity and control history; curvature/tidal exposure; stress-energy/energy-condition diagnostics; event and frame conventions; external ephemeris/hazard coverage; and numerical error bounds. Unknown source physics or uncovered hazards force an **unknown clearance** result.

## 6. Falsifiable mathematical checks for a simulator

Even without an engineering realization, an implementation of this conditional model can be tested against mathematical invariants:

1. **Worldline continuity:** at every segment and chart boundary, compare the same manifold event and tangent after applying the transition map. Position, four-velocity, attitude state, and onboard proper time may not reset.
2. **Timelike normalization:** verify $g_{\mu\nu}u^\mu u^\nu=-c^2$ along the full route within a declared integration tolerance.
3. **Local future direction:** choose a continuous time orientation and verify each local tangent is future-directed in its chart. A decrease in one exterior $T$ label is not itself evidence of past-directed local motion.
4. **Clock-map closure:** compare the numerical mouth-to-mouth map against the specified clock transport, gravitational redshift, throat transit, and boundary matching; propagate parameter uncertainty.
5. **CTC criterion:** only report a CTC after the complete future-directed route returns to the same spacetime event (or a declared event-equivalent state), with positive proper time and timelike tangent everywhere.
6. **Convergence:** refine geodesic/control integration and event detection until exit event, proper time, closest approach, and curvature exposure converge under stated bounds.
7. **Energy source audit:** calculate $T_{\mu\nu}=c^4G_{\mu\nu}/(8\pi G)$, verify $\nabla_\mu T^{\mu\nu}=0$, evaluate relevant energy conditions and averaged/quantum bounds, and report any failure. Passing these algebraic checks does not establish that the tensor is physically realizable.

These checks validate the solver against its assumptions. They do not validate the assumptions against nature.

## 7. Consequence for historical sighting navigation

An Astrarium/A.R.G.O. sighting destination is an uncertain exterior spacetime region inferred from observation records, not a measured vehicle worldline. Under this candidate, a traveler cannot simply reverse a route or assign the reported coordinates and date to the craft. A conditional past-arrival route must specify the selected geometry (two-bubble field history or wormhole mouth world tubes and matching map), the continuous path and event/frame maps, the resulting exterior trajectory, the witness/view geometry, and a globally consistent causal model. No field history, mouth geometry, or time-offset data exists for any sighting; therefore Astrarium can currently reconstruct reports and model hypothetical encounters, but cannot claim to navigate physically to a historical sighting or establish that a traveler caused one.

The candidate suggests a useful software boundary: keep the ordinary celestial propagator, the temporal-geometry model, and the route/collision solver separate but coupled through explicit event/frame interfaces. A future implementation can first reproduce the published two-bubble trajectory and a synthetic wormhole metric in toy spacetimes, then connect exterior segments to solar-system ephemerides only after event/frame matching and hazard propagation are validated. This must not be presented as an operational solar-system time machine.

## 8. Conclusion

The two-bubble construction supplies a published continuous timelike test-particle route that closes into its past in a prescribed metric, with smooth rest-frame transitions and disjoint compact field supports. It is the strongest mathematical reference for A.R.G.O.’s route, but not a model of a single saucer hull or its drive source. The moving-mouth traversable wormhole is a separate conditional comparator. A single unit-lapse Alcubierre-type bubble has a global time function and cannot deliver A.R.G.O. to an earlier exterior epoch; the oblate source-density integral in this note applies only to that single-bubble ansatz. No known source theory, formation mechanism, control system, stability analysis, finite-hull coupling, or verified Earth/observer-worldline intercept has been established for A.R.G.O. The Star narrative is not precise enough to supply an intercept. The earlier stationary radial-shift ansatz remains disqualified as a physical drive because its negative coordinate-time rate is removable.

The contribution here is a transparent comparison, a flat-background endpoint relation with a reproducible calculator, and an auditable density-slice integral for a separate oblate single-bubble metric. The endpoint relation is not a solution of the full two-bubble Einstein/geodesic problem and does not close a loop through the Bethlehem-era observation region; the source integral is not a source calculation for the CTG geometry. This note is not a new solution to Einstein's equations or evidence for time travel. A research submission should state these novelty limits plainly, have the axisymmetric source calculation independently checked, and undergo expert review before being described as publishable physics. The consciousness/low-interaction idea below is a phenomenological hypothesis, not an implication of the CTC geometry. A feasible temporal drive would additionally require a physical source, controllable hull worldline, and a causal/self-interaction rule for repeated visits.

## References

- M. Alcubierre, [“The warp drive: hyper-fast travel within general relativity,” *Classical and Quantum Gravity* 11, L73–L77 (1994)](https://arxiv.org/abs/gr-qc/0009013). Includes the prescribed bubble metric, timelike central trajectory, energy-condition violations, and global-hyperbolicity discussion.
- A. Bobrick and G. Martire, [“Introducing physical warp drives,” *Classical and Quantum Gravity* 38, 105009 (2021)](https://arxiv.org/abs/2102.06824). General warp-drive framework, propulsion requirement, positive-energy subluminal examples, and analysis of flattened Alcubierre profiles; they note that generalizing positive-energy solutions to axisymmetry remains open.
- M. Alcubierre and F. S. N. Lobo, [“Warp drive basics,” *Fundamental Theories of Physics* (2021)](https://arxiv.org/abs/2103.05610). Review of energy conditions, horizons, causal loops, and the onboard-control problem for superluminal bubbles.
- M. Shoshany and J. Snodgrass, [“Warp drives and closed timelike curves,” *Classical and Quantum Gravity* 41, 205005 (2024)](https://arxiv.org/abs/2309.10072). Explicit two-bubble metric with smooth rest-frame transitions, compact supports, and a closed timelike geodesic; it prescribes the geometry but does not provide a physical source or construction mechanism.
- NASA GSFC, [Does the Sun move around the Milky Way?](https://starchild.gsfc.nasa.gov/docs/StarChild/questions/question18.html), source for the approximate 230 km/s Galactic-motion scale used in the rough endpoint estimate.
- J. Bland-Hawthorn and O. Gerhard, [“The Galaxy in Context: Structural, Kinematic, and Integrated Properties,” *Annual Review of Astronomy and Astrophysics* 54 (2016)](https://doi.org/10.1146/annurev-astro-081915-023441), review adopting $R_0=8.2\pm0.1\,\mathrm{kpc}$ for the Sun's Galactocentric radius; $8.2\,\mathrm{kpc}$ is used here only as an illustrative circular-orbit scale.
- NASA NSSDC, [Earth Fact Sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html), source for Earth's mass parameter, reference radius, and escape velocity used in the idealized departure baseline.
- S. V. Krasnikov, [“Hyperfast travel in general relativity,” *Physical Review D* 57, 4760–4772 (1998)](https://arxiv.org/abs/gr-qc/9511068). A distinct spacetime-tube construction; its causal and energy requirements should not be conflated with a single Alcubierre bubble.
- M. S. Morris, K. S. Thorne, and U. Yurtsever, [“Wormholes, Time Machines, and the Weak Energy Condition,” *Physical Review Letters* 61, 1446–1449 (1988)](https://doi.org/10.1103/PhysRevLett.61.1446).
- M. S. Morris and K. S. Thorne, [“Wormholes in spacetime and their use for interstellar travel: A tool for teaching general relativity,” *American Journal of Physics* 56, 395–412 (1988)](https://doi.org/10.1119/1.15620).
- S. W. Hawking, [“Chronology protection conjecture,” *Physical Review D* 46, 603–611 (1992)](https://doi.org/10.1103/PhysRevD.46.603).
- L. H. Ford and T. A. Roman, [“Quantum field theory constrains traversable wormhole geometries,” *Physical Review D* 53, 5496–5507 (1996)](https://arxiv.org/abs/gr-qc/9510071).
- J. L. Friedman et al., [“Cauchy problem in spacetimes with closed timelike curves,” *Physical Review D* 42, 1915–1930 (1990)](https://doi.org/10.1103/PhysRevD.42.1915).
- B. S. Kay, M. J. Radzikowski, and R. M. Wald, [“Quantum Field Theory on Spacetimes with a Compactly Generated Cauchy Horizon,” *Communications in Mathematical Physics* 183, 533–556 (1997)](https://arxiv.org/abs/gr-qc/9603012). This theorem identifies a breakdown of the standard Hadamard condition at certain Cauchy-horizon base points; it is a serious obstruction, but not by itself a universal proof that all time-machine spacetimes are impossible.
- NIST/CODATA, [2022 recommended values of the fundamental physical constants](https://physics.nist.gov/cuu/pdf/RevModPhys.97.025002.pdf), used for the numerical scale above.
