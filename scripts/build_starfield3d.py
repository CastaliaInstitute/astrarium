import csv
import json
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "player", "app", "src", "main", "assets", "sky", "stars3d.json")
MAG_LIMIT = 9.0


def main():
    stars = []
    labels = []
    with open("/tmp/hyg33.csv", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                mag = float(row["mag"])
                x = float(row["x"])
                y = float(row["y"])
                z = float(row["z"])
                ci = float(row["ci"]) if row["ci"] else 0.6
            except (ValueError, KeyError):
                continue
            if mag > MAG_LIMIT or (x == 0 and y == 0 and z == 0):
                continue
            stars.append([round(x, 4), round(y, 4), round(z, 4), round(mag, 2), round(ci, 2)])
            name = (row.get("proper") or "").strip()
            if name and mag < 2.6:
                labels.append({"n": name, "x": round(x, 4), "y": round(y, 4), "z": round(z, 4)})
    import math
    for n, ra, dec, dist in [
        ("Proxima Centauri", 217.429, -62.679, 1.3011),
        ("Alpha Centauri", 219.901, -60.834, 1.3388),
        ("Barnard's Star", 269.452, 4.693, 1.8269),
    ]:
        rar, decr = math.radians(ra), math.radians(dec)
        labels.append({"n": n,
                       "x": round(dist * math.cos(decr) * math.cos(rar), 4),
                       "y": round(dist * math.cos(decr) * math.sin(rar), 4),
                       "z": round(dist * math.sin(decr), 4)})
    labels.sort(key=lambda l: l["x"] ** 2 + l["y"] ** 2 + l["z"] ** 2)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump({"stars": stars, "labels": labels}, fh, separators=(",", ":"))
    print(f"wrote {len(stars)} stars, {len(labels)} named labels")


if __name__ == "__main__":
    main()
