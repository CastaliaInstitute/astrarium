import json
import os
import csv
import glob
import math
import urllib.request

STARS_URL = "https://raw.githubusercontent.com/ofrohn/d3-celestial/master/data/stars.6.json"
LABELS_URL = "https://raw.githubusercontent.com/ofrohn/d3-celestial/master/data/constellations.json"
LINES_URL = "https://raw.githubusercontent.com/ofrohn/d3-celestial/master/data/constellations.lines.json"
OUT = os.path.join(os.path.dirname(__file__), "..", "player", "app", "src", "main", "assets", "sky", "stars.json")
GAIA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "gaia")
RV_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "gaia-bright-radial-velocity.csv")


def fetch(url):
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def gaia_bright_rows():
    """Load the local G<8 Gaia subset, whose astrometry is at epoch J2016.0."""
    radial_velocity = {}
    if os.path.isfile(RV_CSV):
        with open(RV_CSV, newline="") as fh:
            for row in csv.DictReader(fh):
                try:
                    key = (round(float(row["ra"]), 6), round(float(row["dec"]), 6))
                    radial_velocity[key] = float(row["radial_velocity"])
                except (KeyError, TypeError, ValueError):
                    continue
    rows = []
    for path in glob.glob(os.path.join(GAIA_DIR, "g0-8_*.csv")):
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                try:
                    ra, dec = float(row["ra"]), float(row["dec"])
                    pmra, pmdec = float(row["pmra"]), float(row["pmdec"])
                    parallax = float(row["parallax"])
                    if not all(math.isfinite(v) for v in (ra, dec, pmra, pmdec)):
                        continue
                    distance_pc = 1000.0 / parallax if parallax > 0.0 else 0.0
                    rows.append((ra, dec, pmra, pmdec, distance_pc,
                                 radial_velocity.get((round(ra, 6), round(dec, 6)))))
                except (KeyError, TypeError, ValueError):
                    continue
    return rows


def match_gaia(ra_deg, dec_deg, by_dec):
    """Nearest bright Gaia counterpart within 0.15 degrees of the J2000 source."""
    limit = math.radians(0.15)
    cos_dec = max(0.01, abs(math.cos(math.radians(dec_deg))))
    ra_limit = min(180.0, 0.15 / cos_dec)
    best, best_sep = None, limit
    for band in range(int(math.floor((dec_deg - 0.2) * 4)), int(math.ceil((dec_deg + 0.2) * 4)) + 1):
        for row in by_dec.get(band, ()):
            dra_deg = abs((row[0] - ra_deg + 180.0) % 360.0 - 180.0)
            if dra_deg > ra_limit:
                continue
            dra, d1, d2 = math.radians(dra_deg), math.radians(dec_deg), math.radians(row[1])
            dot = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(dra)
            sep = math.acos(max(-1.0, min(1.0, dot)))
            if sep < best_sep:
                best, best_sep = row, sep
    return best


def main():
    stars = fetch(STARS_URL)
    labels = fetch(LABELS_URL)
    lines = fetch(LINES_URL)

    names = {f["id"]: f["properties"].get("name", "") for f in labels["features"] if f.get("id")}

    gaia_rows = gaia_bright_rows()
    gaia_by_dec = {}
    for row in gaia_rows:
        gaia_by_dec.setdefault(int(math.floor(row[1] * 4)), []).append(row)

    out_stars = []
    for f in stars["features"]:
        g = f.get("geometry")
        if g is None:
            continue
        ra, dec = g["coordinates"]
        p = f["properties"]
        mag = p.get("mag", 6.9)
        try:
            bv = float(p.get("bv", 0.6))
        except (TypeError, ValueError):
            bv = 0.6
        match = match_gaia(float(ra) * 15.0, float(dec), gaia_by_dec) if gaia_rows else None
        if match:
            # Keep Gaia's J2016.0 position as the astrometric reference coordinate.
            out_stars.append([round(match[0] / 15.0, 6), round(match[1], 6), round(float(mag), 2),
                              round(bv, 2), round(match[2], 4), round(match[3], 4), round(match[4], 4), 2016.0,
                              round(match[5], 3) if match[5] is not None else None])
        else:
            out_stars.append([round(float(ra), 2), round(float(dec), 2), round(float(mag), 2), round(bv, 2), 0, 0, 0, 2000.0])

    out_figs = []
    for f in lines["features"]:
        g = f.get("geometry")
        if g is None or g["type"] != "MultiLineString":
            continue
        name = names.get(f.get("id"), "")
        segs = []
        for line in g["coordinates"]:
            points = []
            for p in line:
                match = match_gaia(float(p[0]), float(p[1]), gaia_by_dec) if gaia_rows else None
                if match:
                    points.append([round(match[0], 6), round(match[1], 6), round(match[2], 4), round(match[3], 4),
                                   round(match[4], 4), 2016.0, round(match[5], 3) if match[5] is not None else None])
                else:
                    points.append([round(p[0], 2), round(p[1], 2), 0, 0, 0, 2000.0])
            segs.append(points)
        out_figs.append({"name": name, "lines": segs})

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump({"version": 3, "source": "D3 Celestial + Gaia DR3 local cross-match", "epoch": "J2016.0",
                   "coordinate": "ICRS", "radialVelocityUnits": "km/s; null when Gaia DR3 has no measurement",
                   "stars": out_stars, "figs": out_figs}, fh, separators=(",", ":"))
    print(f"wrote {OUT}: {len(out_stars)} stars ({sum(1 for s in out_stars if s[4] or s[5])} with Gaia motion), {len(out_figs)} figures")
    print("sample names:", sorted({f['name'] for f in out_figs})[:12])


if __name__ == "__main__":
    main()
