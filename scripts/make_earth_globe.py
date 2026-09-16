"""Bake a shaded Earth globe (front hemisphere, centered on home) into a PNG for StarField3D."""
import os
import urllib.request

import numpy as np
from PIL import Image

OUT = os.path.join(os.path.dirname(__file__), "..", "player", "app", "src", "main", "assets", "sky", "planets", "earth_globe.png")
SIZE = 1024
TEX_URLS = [
    "https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg",
    "https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57752/land_shallow_topo_2048.jpg",
]
TEX_TMP = "/tmp/earth_map.jpg"

CENTER_LON_DEG = -105.0  # Colorado
CENTER_LAT_DEG = 38.0

L = np.array([-0.5, 0.3, 0.85])
L = L / np.linalg.norm(L)


def fetch_texture():
    if not os.path.exists(TEX_TMP):
        for url in TEX_URLS:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "atlas"})
                with urllib.request.urlopen(req, timeout=90) as r, open(TEX_TMP, "wb") as f:
                    f.write(r.read())
                Image.open(TEX_TMP).verify()
                break
            except Exception as e:
                print("fetch failed", url, e)
    return Image.open(TEX_TMP).convert("RGB")


def main():
    tex = np.asarray(fetch_texture(), dtype=np.float32) / 255.0
    th, tw = tex.shape[:2]

    tilt = np.radians(CENTER_LAT_DEG)
    lon0 = np.radians(CENTER_LON_DEG)
    cosT, sinT = np.cos(tilt), np.sin(tilt)

    n = SIZE
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float32)
    c = (n - 1) / 2.0
    nx = (xs - c) / (n / 2.0)
    ny = (ys - c) / (n / 2.0)
    r2 = nx * nx + ny * ny
    inside = r2 <= 1.0
    nz = np.sqrt(np.clip(1.0 - r2, 0.0, 1.0))

    # tilt sphere so the center of the disc shows (centerLat, centerLon)
    gy = ny * cosT + nz * sinT
    gz = nz * cosT - ny * sinT
    lat = np.arcsin(np.clip(gy, -1, 1))
    lon = np.arctan2(nx, gz) + lon0

    u = (lon / (2 * np.pi)) + 0.5
    v = 0.5 - lat / np.pi
    uu = np.clip((u * (tw - 1)).astype(np.int32), 0, tw - 1)
    vv = np.clip((v * (th - 1)).astype(np.int32), 0, th - 1)

    lit = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0.0, 1.0)
    shade = (0.16 + 0.95 * np.power(lit, 0.9)).astype(np.float32)
    limb = np.clip(1.0 - 0.4 * np.power(np.clip(r2, 0, 1), 2.0), 0.4, 1.0)

    rgb = tex[vv, uu] * (shade * limb)[..., None]
    rgb = np.clip(rgb * 1.08 + 0.015, 0, 1)

    # subtle atmosphere rim toward the edge
    r = np.sqrt(np.clip(r2, 0, 1))
    rim = np.clip((r - 0.86) / 0.14, 0, 1) ** 2
    atmo = np.array([0.45, 0.65, 1.0], np.float32)
    rgb = rgb * (1 - rim[..., None] * 0.55) + atmo * (rim * 0.55)[..., None]

    edge = np.clip((1.0 - r) * (n / 2.0) / 1.5, 0, 1)
    alpha = np.clip(edge * 255, 0, 255).astype(np.uint8)

    out = np.dstack([(np.clip(rgb, 0, 1) * 255).astype(np.uint8), alpha])
    Image.fromarray(out, "RGBA").save(OUT)
    print("wrote", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
