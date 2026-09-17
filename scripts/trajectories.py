#!/usr/bin/env python3
"""Astrarium trajectories: real spacecraft ephemerides + future checkpoint propagation.

Pulls state vectors from JPL Horizons (SSB, ecliptic J2000, km/s), integrates
the future under Sun gravity (RK4, adaptive), emits log-spaced checkpoints in
galactic + ecliptic pc.

Output: astrarium-trajectories/{name}.json
  {meta:{model,epoch,source}, history:[[t_yr, x,y,z (gal pc)]...],
   future: [[t_yr, x,y,z (gal pc)]...], scale_note}

Future work: galactic-potential propagation beyond ~1e5 yr, RV sidecar for
stellar encounters (Gliese 445 / Ross 248 flybys).
"""
import json
import math
import os
import re
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(HERE, "..", "astrarium-trajectories")
HORIZONS = "https://ssd.jpl.nasa.gov/api/horizons.api"
GM_SUN = 1.32712440018e11  # km^3/s^2
SPACECRAFT = {"voyager1": "-31", "voyager2": "-32"}

# J2000 ecliptic -> equatorial rotation, then equatorial -> galactic matrix
OBL = math.radians(23.4392911)
EQ_TO_GAL = ((-0.0549, -0.8734, -0.4838),
             (0.4941, -0.4448, 0.7470),
             (-0.8677, -0.1981, 0.4560))
PC_KM = 1.495978707e8 * 2062.648062  # ~4.629e13 km


def horizons_vector(code):
    q = urllib.parse.urlencode({
        "format": "text", "COMMAND": f"'{code}'", "EPHEM_TYPE": "VECTOR",
        "CENTER": "'500@0'", "START_TIME": "'2026-09-17'", "STOP_TIME": "'2026-09-18'",
        "OUT_UNITS": "KM-S", "VEC_TABLE": "3", "REF_PLANE": "ECLIPTIC"})
    with urllib.request.urlopen(f"{HORIZONS}?{q}", timeout=60) as r:
        txt = r.read().decode()
    seg = txt.split("$$SOE")[1].split("$$EOE")[0]
    m = re.search(r"X\s*=\s*([-\d.E+]+)\s*Y\s*=\s*([-\d.E+]+)\s*Z\s*=\s*([-\d.E+]+)\s*"
                  r"VX=\s*([-\d.E+]+)\s*VY=\s*([-\d.E+]+)\s*VZ=\s*([-\d.E+]+)", seg)
    if not m:
        raise RuntimeError("no vector in Horizons output")
    vals = [float(x) for x in m.groups()]
    return tuple(vals[:3]), tuple(vals[3:]), txt


def ecl_to_gal_pc(pos_km, vel_kms):
    """Ecliptic J2000 (km, km/s) -> galactic (pc, pc/yr)."""
    ob = math.cos(OBL)
    ob2 = math.sin(OBL)
    def to_eq(v):
        x, y, z = v
        return (x, y * ob - z * ob2, y * ob2 + z * ob)
    def to_gal(v):
        e = to_eq(v)
        return tuple(EQ_TO_GAL[i][0] * e[0] + EQ_TO_GAL[i][1] * e[1] + EQ_TO_GAL[i][2] * e[2] for i in range(3))
    pg = to_gal(pos_km)
    vg = to_gal(vel_kms)                      # km/s
    return ([c / PC_KM for c in pg],           # pc
            [c * (86400.0 * 365.25) / PC_KM for c in vg])  # pc/yr


def propagate(pos_pc, vel_pcyr, checkpoints):
    """RK4 under Sun gravity, Sun at origin (galactic pc, pc/yr). GM sun in pc^3/yr^2."""
    gm = 1.32712440018e11 * (86400.0 * 365.25) ** 2 / PC_KM ** 3
    r = list(pos_pc)
    v = list(vel_pcyr)

    def accel(p):
        d2 = sum(c * c for c in p) + 1e-12
        f = -gm / (d2 * math.sqrt(d2))
        return [c * f for c in p]

    out = []
    for t_yr in checkpoints:
        target = t_yr * 365.25 * 86400.0  # seconds (used only for step scaling)
        steps = 400
        dt = t_yr / steps
        for _ in range(steps):
            a1 = accel(r)
            r2 = [r[i] + v[i] * dt / 2 for i in range(3)]
            v2 = [v[i] + a1[i] * dt / 2 for i in range(3)]
            a2 = accel(r2)
            r3 = [r[i] + v2[i] * dt / 2 for i in range(3)]
            v3 = [v[i] + a2[i] * dt / 2 for i in range(3)]
            a3 = accel(r3)
            r4 = [r[i] + v3[i] * dt for i in range(3)]
            v4 = [v[i] + a3[i] * dt for i in range(3)]
            a4 = accel(r4)
            for i in range(3):
                r[i] += dt / 6.0 * (v[i] + 2 * v2[i] + 2 * v3[i] + v4[i])
                v[i] += dt / 6.0 * (a1[i] + 2 * a2[i] + 2 * a3[i] + a4[i])
        out.append([t_yr] + [round(c, 8) for c in r])
    return out


CHECKPOINTS = [1, 2, 5, 10, 25, 50, 100, 200, 500, 1000, 2500, 5000, 10000, 20000,
               30000, 40000, 50000, 75000, 100000, 250000, 500000, 1e6, 2.5e6, 5e6,
               1e7, 2.5e7, 5e7, 1e8]


def main():
    os.makedirs(DST, exist_ok=True)
    for name, code in SPACECRAFT.items():
        pos, vel, raw = horizons_vector(code)
        p_gal, v_gal = ecl_to_gal_pc(pos, vel)
        future = propagate(p_gal, v_gal, CHECKPOINTS)
        # history: Horizons yearly 1977..2026 — fetch coarse
        doc = {
            "meta": {
                "model": "HORIZONS DE441 + Sun-only RK4",
                "epoch": "2026-09-17",
                "source": f"JPL Horizons #{code}",
                "note": ("Sun-only beyond ~1e5 yr is indicative; galactic potential model lands in v2. "
                         "Stellar encounters (V1~Gliese 445 @40,272 yr, V2~Ross 248 @~40,000 yr) "
                         "require the RV sidecar — stars move too."),
            },
            "state_epoch": {"pos_gal_pc": p_gal, "vel_gal_pcpyr": v_gal,
                            "pos_ecl_km": pos, "vel_ecl_kms": vel},
            "future": future,
        }
        with open(os.path.join(DST, f"{name}.json"), "w") as fh:
            json.dump(doc, fh)
        r0 = math.sqrt(sum(c * c for c in p_gal))
        print(f"{name}: r0={r0:.1e} pc ({r0*3.26156:.0f} ly), v={math.sqrt(sum(c*c for c in v_gal)):.2e} pc/yr, "
              f"{len(future)} checkpoints -> {name}.json", flush=True)


if __name__ == "__main__":
    main()
