#!/usr/bin/env python3
"""Procedural galactic population for the 3D star field.

Adds synthetic stars so the sky stays populated at distant destination stars:
  1. a spiral-arm disk sample along the journey corridor (band structure),
  2. a "neighborhood" burst centered on each constellation's farthest star
     (same farthest-star rule as the player uses).

Output rows [x, y, z, absMag, ci], equatorial cartesian, kpc units; mag is
ABSOLUTE (player's loader treats galaxy3d.json magnitudes as absolute).
"""
import json
import math
import random

random.seed(20260916)

M = [
    [-0.0549, -0.8734, -0.4838],
    [0.4941, -0.4448, 0.7470],
    [-0.8677, -0.1981, 0.4560],
]

R0 = 8.2      # kpc, sun's galactocentric radius
RH = 2.6
ZH = 0.30
N_DISK = 120_000
N_BURST = 15_000
BURST_R = 0.45  # kpc
MAX_DIST_SUN = 7.0

def gal_to_eq(l, b, d):
    g1 = d * math.cos(b) * math.cos(l)
    g2 = d * math.cos(b) * math.sin(l)
    g3 = d * math.sin(b)
    return (
        M[0][0] * g1 + M[0][1] * g2 + M[0][2] * g3,
        M[1][0] * g1 + M[1][1] * g2 + M[1][2] * g3,
        M[2][0] * g1 + M[2][1] * g2 + M[2][2] * g3,
    )

def sample_absM():
    u = random.random()
    if u < 0.02: return random.uniform(-7.5, -3.0)   # rare OB supergiants
    if u < 0.10: return random.uniform(-3.0, 0.5)    # giants
    if u < 0.35: return random.uniform(0.5, 3.5)     # A/F
    if u < 0.70: return random.uniform(3.5, 7.0)     # G/K
    return random.uniform(7.0, 12.0)                 # M dwarfs (filler)

def sample_ci(am):
    if am < -4: return random.uniform(-0.35, -0.2)
    if am < -1: return random.uniform(-0.3, 0.1)
    if am < 2.5: return random.uniform(0.0, 0.6)
    if am < 6.0: return random.uniform(0.6, 1.3)
    if am < 7.5: return random.uniform(1.4, 2.0)
    return random.uniform(1.6, 2.4)

out = []

# --- 1. spiral-arm disk along the corridor ---
trials = 0
while len(out) < N_DISK and trials < N_DISK * 40:
    trials += 1
    R = random.uniform(2.0, 14.0)
    theta = random.uniform(0, 2 * math.pi)
    z = random.gauss(0.0, ZH)
    xs = R * math.cos(theta) - R0
    ys = R * math.sin(theta)
    if xs * xs + ys * ys + z * z > MAX_DIST_SUN ** 2:
        continue
    w = math.exp(-R / RH)
    arm = 0.0
    if random.random() < 0.55:
        s = 1 if random.random() < 0.5 else -1
        theta_arm = (math.log(max(R, 0.5) / 2.0) / 0.28) * s + (0 if s > 0 else math.pi)
        dth = (theta - theta_arm + math.pi) % (2 * math.pi) - math.pi
        arm = 0.9 * math.exp(-((dth / 0.25) ** 2)) * math.exp(-abs(z) / 0.25)
    p = w + arm
    if random.random() > min(p, 1.0):
        continue
    am = sample_absM()
    ci = sample_ci(am)
    d = math.sqrt(xs * xs + ys * ys + z * z)
    # protect the real catalog sky at home: synthetic star must be faint from Earth
    m_earth = am + 5 * math.log10(max(d * 1000, 10) / 10)
    if m_earth > 7.2:
        continue
    ex, ey, ez = gal_to_eq(math.atan2(ys, xs), math.asin(max(-1, min(1, z / d))), d)
    out.append([ex, ey, ez, round(am, 2), round(ci, 2)])

# --- 2. farthest-star bursts ---
root = json.load(open("player/app/src/main/assets/sky/stars3d.json"))
cat = root["stars"]
sky = json.load(open("player/app/src/main/assets/sky/stars.json"))

def fig_star_coords(fig):
    pts = []
    for seg in fig["lines"]:
        pts.append((seg[0][0], seg[0][1]))
        pts.append((seg[1][0], seg[1][1]))
    return pts

def farthest_star(fig):
    best, bd = None, 0.0
    for ra_deg, dec_deg in fig_star_coords(fig):
        ra = math.radians(ra_deg)
        dec = math.radians(dec_deg)
        ux, uy, uz = math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec)
        for s in cat:
            d = math.sqrt(s[0] ** 2 + s[1] ** 2 + s[2] ** 2)
            if d <= bd or d > 2000 or d < 1e-6:
                continue
            if (s[0] * ux + s[1] * uy + s[2] * uz) / d > 0.9995:
                best, bd = s, d
    return best, bd

FEATURED = {
    "Orion", "Cassiopeia", "Andromeda", "Ursa Minor", "Ursa Major",
    "Scorpius", "Cygnus", "Lyra", "Taurus", "Pegasus",
}

seen = {}
for fig in sky["figs"]:
    if fig["name"] not in FEATURED:
        continue
    star, d = farthest_star(fig)
    if star is None or d < 50:
        continue
    key = tuple(round(c, 3) for c in star[:3])
    seen[key] = (star, d, fig["name"])

for (star, d, name) in seen.values():
    x0, y0, z0 = star[0], star[1], star[2]
    made = 0
    while made < N_BURST:
        # exponential-ish local disk around the star
        r = random.random() ** (1 / 3) * BURST_R
        a = random.uniform(0, 2 * math.pi)
        zz = random.gauss(0.0, 0.08)
        dx, dy, dz = r * math.cos(a), r * math.sin(a), zz
        if dx * dx + dy * dy + dz * dz > BURST_R ** 2:
            continue
        # rotate offset into a random orientation (disk orientation unknown) — isotropic is fine
        am = sample_absM()
        ci = sample_ci(am)
        out.append([x0 + dx, y0 + dy, z0 + dz, round(am, 2), round(ci, 2)])
        made += 1
    print(f"burst {name}: center {d:.0f} pc")

random.shuffle(out)
with open("player/app/src/main/assets/sky/galaxy3d.json", "w") as f:
    json.dump({"stars": out}, f, separators=(",", ":"))
import struct
with open("player/app/src/main/assets/sky/galaxy3d.bin", "wb") as f:
    for s in out:
        f.write(struct.pack("<5f", *s))
print(f"wrote {len(out)} stars")

# --- sanity: visible count from each dest ---
for (star, d, name) in seen.values():
    x0, y0, z0 = star[0], star[1], star[2]
    vis = 0
    for s in out:
        dx = (s[0] - x0) * 1000
        dy = (s[1] - y0) * 1000
        dz = (s[2] - z0) * 1000
        dd = math.sqrt(dx * dx + dy * dy + dz * dz)
        if dd < 1e-6:
            continue
        if s[3] + 5 * math.log10(max(dd, 10) / 10) < 7:
            vis += 1
    print(f"visible from {name} dest ({d:.0f} pc): {vis}")
