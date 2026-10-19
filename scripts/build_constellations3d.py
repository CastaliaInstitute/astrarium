#!/usr/bin/env python3
"""3D constellation lines: project d3-celestial figure vertices onto a sky dome.

Reads assets sky/stars.json (figs = ra/dec polylines of naked-eye stars). Every
figure vertex becomes a 3D point on a sphere of radius R, so the figures render
identically to the familiar Earth-sky shapes and rotate as you travel, without
the spaghetti caused by connecting stars at their wildly different true depths.

Output: assets/sky/constellations3d.json  {"figs":[{"n":name,"poly":[[[x,y,z]...],...]}]}
"""
import json
import math
import os

HERE = os.path.dirname(__file__)
SKY = os.path.join(HERE, "..", "player", "app", "src", "main", "assets", "sky")
R = 5000.0


def main():
    stars2d = json.load(open(os.path.join(SKY, "stars.json")))

    out = []
    total = 0
    for fig in stars2d["figs"]:
        polys = []
        for line in fig["lines"]:
            poly = []
            for ra, dec in line:
                total += 1
                ra_r = math.radians(float(ra))
                dec_r = math.radians(float(dec))
                x = R * math.cos(dec_r) * math.cos(ra_r)
                y = R * math.cos(dec_r) * math.sin(ra_r)
                z = R * math.sin(dec_r)
                if poly and abs(poly[-1][0] - x) < 1e-6 and abs(poly[-1][1] - y) < 1e-6 and abs(poly[-1][2] - z) < 1e-6:
                    continue
                poly.append([round(x, 4), round(y, 4), round(z, 4)])
            if len(poly) >= 2:
                polys.append(poly)
        if polys:
            out.append({"n": fig["name"], "poly": polys})

    res = {"figs": out}
    dest = os.path.join(SKY, "constellations3d.json")
    with open(dest, "w") as fh:
        json.dump(res, fh, separators=(",", ":"))
    print("dome-projected %d vertices, %d constellations -> %s (%.0f KB)" % (
        total, len(out), dest, os.path.getsize(dest) / 1024))


if __name__ == "__main__":
    main()