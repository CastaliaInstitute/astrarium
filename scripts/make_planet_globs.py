"""Bake shaded globe spheres (front hemisphere) for the journey planets."""
import os
import urllib.request

import numpy as np
from PIL import Image

ASSETS = os.path.join(os.path.dirname(__file__), "..", "player", "app", "src", "main", "assets", "sky", "planets")
SIZE = 1024
BASE = "https://www.solarsystemscope.com/textures/download/"

# name -> (texture, centerLonDeg, centerLatDeg, bumpStrength, lightDir)
PLANETS = {
    "earth": ("2k_earth_daymap.jpg", -105.0, 38.0, 0.0, (-0.5, 0.3, 0.85)),
    "moon": ("2k_moon.jpg", -30.0, 10.0, 0.55, (-0.7, 0.15, 0.7)),
    "mars": ("2k_mars.jpg", -90.0, 15.0, 0.35, (-0.65, 0.2, 0.75)),
    "jupiter": ("2k_jupiter.jpg", 0.0, 5.0, 0.0, (-0.45, 0.25, 0.87)),
    "saturn": ("2k_saturn.jpg", 0.0, 5.0, 0.0, (-0.45, 0.25, 0.87)),
}

CACHE = "/tmp/planet_tex"


def fetch(name, path):
    if os.path.exists(path):
        return
    os.makedirs(CACHE, exist_ok=True)
    req = urllib.request.Request(BASE + name, headers={"User-Agent": "atlas"})
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
        f.write(r.read())


def bake(key, texname, lon0deg, lat0deg, bump, light):
    texPath = os.path.join(CACHE, texname)
    fetch(texname, texPath)
    tex = np.asarray(Image.open(texPath).convert("RGB"), dtype=np.float32) / 255.0
    th, tw = tex.shape[:2]

    lum = tex @ np.array([0.299, 0.587, 0.114], np.float32)
    gx = np.roll(lum, -1, axis=1) - np.roll(lum, 1, axis=1)
    gy = np.roll(lum, -1, axis=0) - np.roll(lum, 1, axis=0)

    L = np.array(light, np.float32)
    L /= np.linalg.norm(L)

    tilt = np.radians(lat0deg)
    lon0 = np.radians(lon0deg)
    cosT, sinT = np.cos(tilt), np.sin(tilt)

    n = SIZE
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float32)
    c = (n - 1) / 2.0
    nx = (xs - c) / (n / 2.0)
    ny = (ys - c) / (n / 2.0)
    r2 = nx * nx + ny * ny
    nz = np.sqrt(np.clip(1.0 - r2, 0.0, 1.0))

    gy_t = ny * cosT + nz * sinT
    gz_t = nz * cosT - ny * sinT
    lat = np.arcsin(np.clip(gy_t, -1, 1))
    lon = np.arctan2(nx, gz_t) + lon0

    u = (lon / (2 * np.pi)) + 0.5
    v = 0.5 - lat / np.pi
    uu = np.clip((u * (tw - 1)).astype(np.int32), 0, tw - 1)
    vv = np.clip((v * (th - 1)).astype(np.int32), 0, th - 1)

    lit = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0.0, 1.0)
    shade = (0.14 + 0.95 * np.power(lit, 0.9)).astype(np.float32)

    if bump > 0:
        # texture-space relief: brighten slopes facing the baked light azimuth
        relief = 1.0 + bump * (gx[vv, uu] * 22.0 * (-0.8) + gy[vv, uu] * 22.0 * (0.35))
        shade = shade * np.clip(relief, 0.75, 1.45)

    limb = np.clip(1.0 - 0.4 * np.power(np.clip(r2, 0, 1), 2.0), 0.4, 1.0)
    rgb = tex[vv, uu] * (shade * limb)[..., None]
    rgb = np.clip(rgb * 1.06 + 0.012, 0, 1)

    r = np.sqrt(np.clip(r2, 0, 1))
    rim = np.clip((r - 0.87) / 0.13, 0, 1) ** 2
    if key == "earth":
        atmo = np.array([0.45, 0.65, 1.0], np.float32)
        rgb = rgb * (1 - rim[..., None] * 0.55) + atmo * (rim * 0.55)[..., None]
    else:
        rgb = rgb * (1 - rim[..., None] * 0.25)

    edge = np.clip((1.0 - r) * (n / 2.0) / 1.5, 0, 1)
    alpha = np.clip(edge * 255, 0, 255).astype(np.uint8)
    out = np.dstack([(np.clip(rgb, 0, 1) * 255).astype(np.uint8), alpha])
    Image.fromarray(out, "RGBA").save(os.path.join(ASSETS, f"{key}_globe.png"))
    print("baked", key)


def main():
    for key, (texname, lon0, lat0, bump, light) in PLANETS.items():
        bake(key, texname, lon0, lat0, bump, light)


if __name__ == "__main__":
    main()
