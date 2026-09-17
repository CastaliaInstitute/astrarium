#!/usr/bin/env python3
"""Real-data Milky Way background texture from Gaia DR3 (paginated, streaming).

The foreground 3D catalog draws bright stars; this aggregates everything
fainter (G 10-12, paginated by RA) into an equirectangular (RA/dec) RGBA
texture. The player draws it as a full-sky dome behind the individual 3D
stars, so the whole Gaia sky is visually present without holding rows.

Output: assets/sky/galactex.png
"""
import math
import os
import struct
import sys
import time
import urllib.parse
import urllib.request
import zlib

OUT = os.path.join(os.path.dirname(__file__), "..", "player", "app", "src", "main", "assets", "sky", "galactex.png")
W, H = 1024, 512
G_MIN = 10.0
G_MAX = 12.0
SLICES = [(10.0, 11.0), (11.0, 12.0)]
RA_STEPS = 15
COLS = 3
FLUX_BASE = 12.0
USER_AGENT = "astrarium-build/0.1 (contact: dcmcshan@castalia.institute)"


def query(adql):
    u = "https://gea.esac.esa.int/tap-server/tap/sync?" + urllib.parse.urlencode(
        {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": adql}
    )
    req = urllib.request.Request(u, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=1800)


def tint(bp_rp):
    t = max(0.0, min(1.0, (bp_rp + 0.5) / 5.0))
    return (1.0 - t) * 0.78 + t * 1.08, (1.0 - t) * 0.86 + t * 0.86, (1.0 - t) * 1.02 + t * 0.70


def accumulate(sky, gmin, gmax, ra_min, ra_max):
    adql = (
        "SELECT ra, dec, phot_g_mean_mag, bp_rp FROM gaiadr3.gaia_source "
        "WHERE phot_g_mean_mag BETWEEN %.1f AND %.1f AND ra BETWEEN %.2f AND %.2f"
        % (gmin, gmax, ra_min, ra_max)
    )
    r = query(adql)
    total = 0
    f = r.buffer if hasattr(r, "buffer") else r
    header = f.readline().decode("utf-8", "replace")
    if "ra," not in header:
        # TAP error or empty: read why
        err = header + f.read(512).decode("utf-8", "replace")
        print("  [warn] %s" % err[:200], flush=True)
        return 0
    for raw in f:
        try:
            line = raw.decode("utf-8", "replace")
        except Exception:
            continue
        parts = line.rstrip("\n").split(",")
        if len(parts) < 4:
            continue
        try:
            ra = float(parts[0])
            dec = float(parts[1])
            g = float(parts[2])
            bp_rp0 = float(parts[3]) if parts[3].strip() else 0.6
        except ValueError:
            continue
        if not (G_MIN <= g <= G_MAX):
            continue
        flux = 10.0 ** (-0.4 * (g - FLUX_BASE))
        tr, tg, tb = tint(bp_rp0)
        ra_r = math.radians(ra)
        dec_r = math.radians(dec)
        u = (ra_r / (2.0 * math.pi)) * W - 0.5
        v = (0.5 - dec_r / math.pi) * H - 0.5
        for dy in (-1, 0, 1):
            yc = int(round(v)) + dy
            for dx in (-1, 0, 1):
                xc = int(round(u)) + dx
                xc %= W
                if 0 <= yc < H:
                    w = math.exp(-0.5 * (dx * dx + dy * dy))
                    row = sky[yc]
                    o = xc * COLS
                    row[o] += flux * tr * w
                    row[o + 1] += flux * tg * w
                    row[o + 2] += flux * tb * w
        total += 1
        if total % 500000 == 0:
            print("    %d rows" % total, flush=True)
    return total


def main():
    sky = [[0.0] * (W * COLS) for _ in range(H)]
    total = 0
    step = 360.0 / RA_STEPS
    for gmin, gmax in SLICES:
        for i in range(RA_STEPS):
            ra0 = i * step
            ra1 = ra0 + step
            print("slice G %.1f-%.1f RA %5.1f-%5.1f ..." % (gmin, gmax, ra0, ra1), flush=True)
            n = accumulate(sky, gmin, gmax, ra0, ra1)
            total += n
            print("  -> %d rows" % n, flush=True)
            time.sleep(0.3)

    hi = 0.0
    for row in sky:
        for c in range(W * COLS):
            if row[c] > hi:
                hi = row[c]
    print("rows=%d max_flux=%.2f" % (total, hi), flush=True)
    if hi <= 0:
        print("no data; aborting", flush=True)
        sys.exit(1)
    scale = 235.0 / hi
    px = bytearray(W * H * 4)
    for y in range(H):
        row = sky[y]
        for x in range(W):
            o = y * W * 4 + x * 4
            lum = max(row[x * COLS], row[x * COLS + 1], row[x * COLS + 2]) * scale
            if lum < 1e-5:
                continue
            a = int(round((lum / 235.0) ** (1.0 / 2.4) * 255.0))
            a = min(255, max(0, a + int(round(lum * 0.03))))
            px[o] = min(255, int(round(row[x * COLS] * scale)))
            px[o + 1] = min(255, int(round(row[x * COLS + 1] * scale)))
            px[o + 2] = min(255, int(round(row[x * COLS + 2] * scale)))
            px[o + 3] = a
    raw = b"".join(b"\x00" + bytes(px[y * W * 4:(y + 1) * W * 4]) for y in range(H))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6))
    png += chunk(b"IEND", b"")
    with open(OUT, "wb") as f:
        f.write(png)
    print("wrote %s (%.2f MB)" % (OUT, os.path.getsize(OUT) / 1e6))


if __name__ == "__main__":
    main()