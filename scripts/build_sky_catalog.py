import json
import os
import urllib.request

STARS_URL = "https://raw.githubusercontent.com/ofrohn/d3-celestial/master/data/stars.6.json"
LABELS_URL = "https://raw.githubusercontent.com/ofrohn/d3-celestial/master/data/constellations.json"
LINES_URL = "https://raw.githubusercontent.com/ofrohn/d3-celestial/master/data/constellations.lines.json"
OUT = os.path.join(os.path.dirname(__file__), "..", "player", "app", "src", "main", "assets", "sky", "stars.json")


def fetch(url):
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def main():
    stars = fetch(STARS_URL)
    labels = fetch(LABELS_URL)
    lines = fetch(LINES_URL)

    names = {f["id"]: f["properties"].get("name", "") for f in labels["features"] if f.get("id")}

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
        out_stars.append([round(float(ra), 2), round(float(dec), 2), round(float(mag), 2), round(bv, 2)])

    out_figs = []
    for f in lines["features"]:
        g = f.get("geometry")
        if g is None or g["type"] != "MultiLineString":
            continue
        name = names.get(f.get("id"), "")
        segs = [[[round(p[0], 2), round(p[1], 2)] for p in seg] for seg in g["coordinates"]]
        out_figs.append({"name": name, "lines": segs})

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump({"stars": out_stars, "figs": out_figs}, fh, separators=(",", ":"))
    print(f"wrote {OUT}: {len(out_stars)} stars, {len(out_figs)} figures")
    print("sample names:", sorted({f['name'] for f in out_figs})[:12])


if __name__ == "__main__":
    main()
