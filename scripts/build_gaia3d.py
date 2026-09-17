#!/usr/bin/env python3
"""Real-star expansion from Gaia DR3.

Pulls fainter stars (phot_g_mean_mag in a band ABOVE the HYG catalog limit of
9.0) with reliable parallaxes (parallax_over_error > 5) and writes a binary
star file: rows of LE floats [x, y, z, absMag, ci], xyz in pc (equatorial
cartesian, Sun at origin). absMag = G - 5*log10(d/10). The player loader
re-derives apparent magnitude from the stored distance.
"""
import csv
import io
import math
import os
import struct
import sys
import time
import urllib.parse
import urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "player", "app", "src", "main", "assets", "sky", "gaia3d.bin")
G_MIN, G_MAX = 9.0, 10.0
PARALLAX_MIN = 0.05  # mas -> d < 20 kpc
PLX_ERR = 5.0

SLICES = [(9.0, 9.4), (9.4, 9.7), (9.7, 9.9), (9.9, 10.0)]


def query(gmin, gmax):
    adql = (
        "SELECT ra, dec, parallax, phot_g_mean_mag, bp_rp FROM gaiadr3.gaia_source "
        "WHERE phot_g_mean_mag BETWEEN %.1f AND %.1f AND parallax_over_error > %s "
        "AND parallax > %s" % (gmin, gmax, PLX_ERR, PARALLAX_MIN)
    )
    u = "https://gea.esac.esa.int/tap-server/tap/sync?" + urllib.parse.urlencode(
        {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": adql}
    )
    req = urllib.request.Request(u, headers={"User-Agent": "astrarium-build"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read().decode("utf-8")


def main():
    rows = 0
    stars = []
    for gmin, gmax in SLICES:
        best = G_MAX
        data = query(gmin, gmax)
        parsed = list(csv.DictReader(io.StringIO(data)))
        for row in parsed:
            try:
                ra = float(row["ra"])
                dec = float(row["dec"])
                plx = float(row["parallax"])
                g = float(row["phot_g_mean_mag"])
                c = row["bp_rp"]
                bp_rp = float(c) if c else 0.6
            except (ValueError, KeyError):
                continue
            if not (plx > PARALLAX_MIN < 999.9):
                continue
            if not (G_MIN <= g <= G_MAX):
                continue
            d = 1000.0 / plx
            ra = math.radians(ra)
            dec = math.radians(dec)
            x = d * math.cos(dec) * math.cos(ra)
            y = d * math.cos(dec) * math.sin(ra)
            z = d * math.sin(dec)
            absm = g - 5.0 * math.log10(max(d, 1e-6) / 10.0)
            ci = bp_rp * 0.9 - 0.15
            stars.append((x, y, z, absm, ci))
            rows += 1
        print("slice %.1f-%.1f: +%d stars" % (gmin, gmax, len(parsed) and rows), flush=True)
        sys.stdout.flush()
        time.sleep(1)

    with open(OUT, "wb") as f:
        for x, y, z, am, ci in stars:
            f.write(struct.pack("<5f", x, y, z, am, ci))
    print("wrote %s: %d stars (%.1f MB)" % (OUT, len(stars), os.path.getsize(OUT) / 1e6))


if __name__ == "__main__":
    main()