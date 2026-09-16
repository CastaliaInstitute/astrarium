#!/usr/bin/env python3
"""Procedural home-page artwork for astrarium.castalia.institute.

Renders deep-space scenes in the site palette (deep navy + amber) with PIL/numpy.
Usage: python3 scripts/render_site_images.py <out-dir>
"""
import os
import sys
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

random.seed(7)
rng = np.random.default_rng(7)

NAVY0 = (7, 8, 15)
NAVY1 = (13, 16, 32)
NAVY2 = (23, 28, 46)
AMBER = (242, 178, 92)
AMBER_SOFT = (255, 214, 160)
WHITE = (255, 255, 255)
BLUE = (190, 216, 255)
TEAL = (120, 200, 210)
ROSE = (255, 180, 160)
STAR_COLORS = [WHITE, BLUE, AMBER_SOFT, ROSE]


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lerp(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def make_starfield(w, h, band_center=None, band_width=None, n=3800,
                   background=(NAVY0, NAVY1), wobble=0.06):
    """Full-starfield canvas with an optional galactic band (density falloff)."""
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    g = ImageDraw.Draw(img)

    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=lerp(background[0], background[1], t))

    xs = rng.uniform(0, w, n)
    ys = rng.uniform(0, h, n)
    if band_center is not None:
        if band_width is None:
            band_width = h * 0.42
        yc = band_center + band_width * 0.5 * wobble * np.sin(xs / w * math.tau * 3)
        density = np.exp(-0.5 * ((ys - yc) / (band_width * 0.5)) ** 2)
        keep = rng.uniform(0, 1, n) < np.clip(density, 0.02, 1.0)
        xs, ys = xs[keep], ys[keep]

    mags = rng.exponential(1.0, len(xs))
    cols = rng.integers(0, len(STAR_COLORS), len(xs))
    for x, y, m, c in zip(xs, ys, mags, cols):
        r = math.exp(-0.55 * m) * (0.9 + 0.4 * abs(math.sin(x)))
        r = max(0.6, min(2.6, r))
        col = STAR_COLORS[int(c)]
        al = max(60, min(255, int(255 * math.exp(-0.8 * m))))
        if r >= 2.6 and m < 0.35:
            d.line([(x - 3.2, y), (x + 3.2, y)], fill=col)
            d.line([(x, y - 3.2), (x, y + 3.2)], fill=col)
        g.ellipse([x - r * 2, y - r * 2, x + r * 2, y + r * 2],
                  fill=col + ((int(al * 0.45)),))

    return img


def add_nebula(img, specks, place, strength=(150, 70, 60), radius=0.16):
    """Soft nebula blobs over an RGB image. specks: list of (x,y,size,brightness,color)."""
    w, h = img.size
    overlay = Image.new("RGB", (w, h), (0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for (x, y, size, br, col) in specks:
        sc = min(w, h) * size
        r = max(1, int(sc))
        od.ellipse([x - r, y - r, x + r, y + r], fill=lerp((0, 0, 0), col, br))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=min(w, h) * radius))
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i in range(3):
        x = rng.uniform(0, w); y = rng.uniform(0, h)
        r = min(w, h) * 0.5
        gd.ellipse([x - r, y - r, x + r, y + r], fill=(int(strength[i] * 0.5), int(strength[i] * 0.25), 40))
    glow = glow.filter(ImageFilter.GaussianBlur(min(w, h) * 0.6))
    base = np.array(img, dtype=np.float32)
    ov = np.array(overlay, dtype=np.float32)
    gl = np.array(glow, dtype=np.float32)
    out = np.clip(base + gl * 0.35 + ov, 0, 255).astype(np.uint8)
    return Image.fromarray(out)


def constellation_lines(stars, index):
    """Simple constellation figure for known W/Cassiopeia-label shapes."""
    figs = {
        "cassiopeia": [0, 1, 2, 3, 4],
        "bigdipper": [0, 1, 2, 3, 4, 5, 6],
        "orion_belt": [0, 1, 2],
        "swan": [0, 1, 2, 3],
    }
    return figs[index]


def scene_constellation(w=1200, h=800, name="cassiopeia"):
    """Feature tile: constellation line art over a starfield."""
    img = make_starfield(w, h, band_center=0.28, band_width=0.3, n=1200)
    canvas = img.convert("RGBA")
    d = ImageDraw.Draw(canvas)

    cy = h * 0.42
    base = [(w * 0.55, cy - h * 0.30),
            (w * 0.74, cy - h * 0.18),
            (w * 0.60, cy - h * 0.10),
            (w * 0.82, cy + h * 0.02),
            (w * 0.62, cy + h * 0.16)]
    base = [(x + (rng.uniform(-12, 12)), y + (rng.uniform(-12, 12))) for x, y in base]
    line_col = AMBER_SOFT + (190,)

    idx = constellation_lines(stars=None, index=name)
    pts = [base[i] for i in idx]
    poly = pts[0]
    for p in pts[1:]:
        d.line([poly, p], fill=line_col, width=int(h * 0.004))
        poly = p

    for (x, y) in base:
        d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=AMBER)
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=WHITE)
    d.text((w * 0.06, h * 0.06), name.upper(),
           fill=lerp(WHITE, AMBER_SOFT, 0.5), font=ImageFont_default(14))
    return canvas.convert("RGB")


def ImageFont_default(size):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def scene_window(w=1200, h=800):
    """Window-mode porthole over an Earth horizon."""
    img = make_starfield(w, h, band_center=0.30, band_width=0.3, n=1500)
    img = add_nebula(img,
                     [(w * 0.7, h * 0.2, 0.07, 0.65, AMBER_SOFT),
                      (w * 0.3, h * 0.6, 0.05, 0.4, BLUE)],
                     place=None, strength=(70, 60, 40))
    canvas = img.convert("RGBA")
    d = ImageDraw.Draw(canvas)
    # horizon
    hr = w * 1.1
    hc = h * 1.35
    d.ellipse([w * 0.5 - hr, hc - hr, w * 0.5 + hr, hc + hr],
              fill=(16, 34, 60, 255))
    d.ellipse([w * 0.5 - hr, hc - hr, w * 0.5 + hr, hc + hr],
              outline=BLUE + (120,), width=int(h * 0.004))
    # atmosphere glow
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([w * 0.5 - hr, hc - hr, w * 0.5 + hr, hc + hr],
               fill=(90, 150, 235, 60))
    glow = glow.filter(ImageFilter.GaussianBlur(20))
    canvas.alpha_composite(glow)
    # porthole frame
    inset = int(h * 0.045)
    d.rounded_rectangle([inset, inset, w - inset, h - inset], radius=int(h * 0.06),
                        outline=(242, 178, 92, 200), width=int(h * 0.012))
    return canvas.convert("RGB")


def scene_f300(w=1200, h=800):
    """Bedroom: F300 on nightstand, projection cone to a starry ceiling."""
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=lerp(NAVY1, (5, 6, 11), t))

    # ceiling stars (upper half)
    xs, ys = rng.uniform(0, w, 700), rng.uniform(0, h * 0.55, 700)
    mags = rng.exponential(1.0, len(xs))
    for x, y, m in zip(xs, ys, mags):
        r = max(0.6, min(1.8, math.exp(-0.5 * m)))
        d.ellipse([x - r, y - r, x + r, y + r],
                  fill=lerp(WHITE, AMBER_SOFT, m * 0.3))

    # cone
    cone = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cone)
    tip = (w * 0.68, h * 0.80)
    lx = lambda a: tip[0] - (tip[0] - a[0]) * 1.45
    cd.polygon([(tip[0] - w * 0.16, h * 0.80), (tip[0] + w * 0.16, h * 0.80),
                (w * 0.80, h * 0.02), (w * 0.24, h * 0.02)],
               fill=(242, 178, 92, 30))
    cone = cone.filter(ImageFilter.GaussianBlur(3))
    img = Image.alpha_composite(img.convert("RGBA"), cone)

    # child in bed (silhouette, no face)
    d = ImageDraw.Draw(Image.new("RGBA", (w, h)))
    img = img.convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    bed_x = w * 0.08
    d.rounded_rectangle([bed_x, h * 0.72, bed_x + w * 0.34, h * 0.98],
                        radius=int(h * 0.025), fill=(30, 34, 52, 255))
    d.rounded_rectangle([bed_x, h * 0.70, bed_x + w * 0.34, h * 0.75],
                        radius=int(h * 0.02), fill=(40, 46, 70, 255))
    d.ellipse([bed_x + w * 0.26, h * 0.55, bed_x + w * 0.38, h * 0.72],
              fill=(18, 21, 36, 255))
    d.rounded_rectangle([bed_x + w * 0.30, h * 0.68, bed_x + w * 0.52, h * 0.72],
                        radius=int(h * 0.015), fill=(26, 30, 48, 255))

    # F300 unit
    px = w * 0.56
    py = h * 0.82
    d.rounded_rectangle([px, py, px + w * 0.22, py + h * 0.10],
                        radius=int(h * 0.014), fill=(58, 66, 95, 255))
    d.rounded_rectangle([px + w * 0.03, py - h * 0.05, px + w * 0.19, py],
                        radius=int(h * 0.008), fill=(78, 88, 122, 255))
    d.ellipse([px + w * 0.035, py - h * 0.038, px + w * 0.085, py + h * 0.012],
              fill=(242, 220, 170, 255))
    d.ellipse([px + w * 0.09, py - h * 0.03, px + w * 0.2, py + h * 0.03],
              fill=(10, 12, 20, 255))
    d.text((px + w * 0.08, py + h * 0.018), "F300",
           fill=(10, 12, 20, 255))

    # faint star pinhole shine on bed blanket
    d.ellipse([bed_x + w * 0.06, h * 0.73, bed_x + w * 0.30, h * 0.86],
              fill=(150, 120, 90, 12))
    return img.convert("RGB")


def scene_hero(w=1600, h=800, n=5000):
    """Hero: dense band + nebula glow, dark enough for white text overlay."""
    img = make_starfield(w, h, band_center=0.6, band_width=0.20, n=n)
    img = add_nebula(img,
                     [(w * 0.75, h * 0.55, 0.09, 0.6, AMBER_SOFT),
                      (w * 0.2, h * 0.3, 0.06, 0.5, BLUE),
                      (w * 0.45, h * 0.75, 0.07, 0.35, ROSE)],
                     place=None, strength=(90, 70, 50))
    return img


def og_banner(w=1200, h=630):
    """Framed hero variant for social previews."""
    img = scene_hero(w, h, n=4000)
    return img


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/astrarium-img"
    os.makedirs(out, exist_ok=True)
    scenes = {
        "hero": lambda: scene_hero(1600, 800),
        "constellation": lambda: scene_constellation(1200, 800, "cassiopeia"),
        "window": lambda: scene_window(1200, 800),
        "f300": lambda: scene_f300(1200, 800),
        "og": lambda: og_banner(),
    }
    for name, fn in scenes.items():
        img = fn()
        path = os.path.join(out, f"{name}.png")
        img.save(path, optimize=True)
        print(f"{name}.png  {img.size}  {os.path.getsize(path)//1024}KB")


if __name__ == "__main__":
    main()