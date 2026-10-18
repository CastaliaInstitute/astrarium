#!/usr/bin/env python3
"""Build HST M16 positive-WHT coverage masks from the six MAST HLA visits.

Only target-intersecting rows from the HLA WHT FITS extensions are fetched. The
weight maps are projected through their own FITS WCS and combined by valid
coverage, then registered with the Heritage SCI render on one shared TAN grid.
"""
from __future__ import annotations

import json
import math
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / "parent-pwa/observations/m16-hst"
MANIFEST = OBS / "hla-wht-provenance.json"
CENTER_RA, CENTER_DEC = 274.721587, -13.841549
FIELD_ARCSEC = 200.0
OUTPUT_SIZE = 2000


def output_grid():
    n = OUTPUT_SIZE
    scale = FIELD_ARCSEC / n / 3600 * math.pi / 180
    xx, yy = np.meshgrid(np.arange(n), np.arange(n))
    xi, eta = (xx - (n - 1) / 2) * scale, -(yy - (n - 1) / 2) * scale
    rho = np.hypot(xi, eta); c = np.arctan(rho); safe = np.where(rho == 0, 1, rho)
    ra0, dec0 = math.radians(CENTER_RA), math.radians(CENTER_DEC)
    dec = np.arcsin(np.cos(c) * math.sin(dec0) + eta * np.sin(c) * math.cos(dec0) / safe)
    ra = ra0 + np.arctan2(xi * np.sin(c), safe * math.cos(dec0) * np.cos(c) - eta * math.sin(dec0) * np.sin(c))
    return ra, dec


def pixels_for_sky(wcs, ra, dec):
    ra0, dec0 = math.radians(wcs["CRVAL1"]), math.radians(wcs["CRVAL2"])
    dra = (ra - ra0 + math.pi) % (2 * math.pi) - math.pi
    cosc = np.sin(dec0) * np.sin(dec) + math.cos(dec0) * np.cos(dec) * np.cos(dra)
    safe = np.maximum(cosc, 1e-10)
    xi = np.cos(dec) * np.sin(dra) / safe * 180 / math.pi
    eta = (math.cos(dec0) * np.sin(dec) - math.sin(dec0) * np.cos(dec) * np.cos(dra)) / safe * 180 / math.pi
    cd = np.array([[wcs["CD1_1"], wcs["CD1_2"]], [wcs["CD2_1"], wcs["CD2_2"]]], dtype=np.float64)
    delta = np.linalg.inv(cd) @ np.stack([xi.ravel(), eta.ravel()])
    sx = (wcs["CRPIX1"] - 1 + delta[0]).reshape(ra.shape)
    sy = (wcs["CRPIX2"] - 1 + delta[1]).reshape(dec.shape)
    return sx, sy, cosc


def read_weight_crop(uri, offset, dimensions, bounds):
    x0, y0, x1, y1 = bounds
    nx, ny = dimensions
    width = x1 - x0
    output = np.empty((y1 - y0, width), dtype=np.float32)
    url = "https://mast.stsci.edu/api/v0.1/Download/file?" + urllib.parse.urlencode({"uri": uri})
    batches = []
    for first in range(y0, y1, 48):
        last = min(y1, first + 48)
        ranges = []
        for y in range(first, last):
            start = offset + (y * nx + x0) * 4
            ranges.append(f"{start}-{start + width * 4 - 1}")
        batches.append((first, last, ranges))

    def fetch(batch):
        first, last, ranges = batch
        req = urllib.request.Request(url, headers={"Range": "bytes=" + ",".join(ranges)})
        with urllib.request.urlopen(req, timeout=90) as response:
            if response.status != 206:
                raise RuntimeError(f"MAST did not honor WHT byte ranges for {uri}")
            content_type = response.headers.get("Content-Type", "")
            data = response.read()
        boundary = re.search(r'boundary="?([^;" ]+)', content_type, re.I)
        if not boundary:
            raise RuntimeError(f"Expected multipart WHT rows, got {content_type}")
        parts = data.split(("--" + boundary.group(1)).encode())[1:-1]
        if len(parts) != last - first:
            raise RuntimeError(f"Expected {last-first} WHT rows, received {len(parts)}")
        rows = np.empty((last - first, width), dtype=np.float32)
        for i, part in enumerate(parts):
            header, sep, payload = part.partition(b"\r\n\r\n")
            match = re.search(rb"Content-range:\s*bytes\s+(\d+)-(\d+)", header, re.I)
            payload = payload.removesuffix(b"\r\n")
            if not sep or not match or len(payload) != width * 4:
                raise RuntimeError("Malformed MAST multipart WHT response")
            rows[i] = np.frombuffer(payload, dtype=">f4")
        return first, rows

    with ThreadPoolExecutor(max_workers=6) as pool:
        for first, rows in pool.map(fetch, batches):
            output[first-y0:first-y0+rows.shape[0]] = rows
    return output


def project_weight(product, ra, dec):
    hdu = product["extensions"]["WHT"]
    nx, ny = hdu["dimensions"]
    sx, sy, cosc = pixels_for_sky(hdu["wcs"], ra, dec)
    inside = (cosc > 0) & (sx >= 0) & (sy >= 0) & (sx + 1 < nx) & (sy + 1 < ny)
    if not inside.any():
        return np.zeros(ra.shape, dtype=bool), [0, 0, 0, 0]
    x0 = max(0, int(np.floor(sx[inside].min())))
    y0 = max(0, int(np.floor(sy[inside].min())))
    x1 = min(nx, int(np.ceil(sx[inside].max())) + 2)
    y1 = min(ny, int(np.ceil(sy[inside].max())) + 2)
    bounds = (x0, y0, x1, y1)
    wht = read_weight_crop(product["uri"], hdu["data_offset"], (nx, ny), bounds)
    px, py = sx-x0, sy-y0
    ix, iy = np.floor(px).astype(np.int32), np.floor(py).astype(np.int32)
    dx, dy = px-ix, py-iy
    ix = np.clip(ix, 0, wht.shape[1]-2); iy = np.clip(iy, 0, wht.shape[0]-2)
    a,b,c,d = wht[iy,ix],wht[iy,ix+1],wht[iy+1,ix],wht[iy+1,ix+1]
    projected = (a*(1-dx)+b*dx)*(1-dy)+(c*(1-dx)+d*dx)*dy
    valid = inside & np.isfinite(projected) & (projected > 0)
    return valid, list(bounds)


def main():
    manifest = json.loads(MANIFEST.read_text())
    ra, dec = output_grid()
    filters = {}
    for filt in ("F502N", "F657N", "F673N"):
        products = [p for p in manifest["products"] if p["filter"] == filt]
        coverage = np.zeros((OUTPUT_SIZE, OUTPUT_SIZE), dtype=bool)
        tile_records = []
        for product in products:
            valid, bounds = project_weight(product, ra, dec)
            coverage |= valid
            tile_records.append({"visit": product["visit"], "uri": product["uri"], "cutout_xyxy": bounds,
                                 "coverage_fraction": float(valid.mean())})
            print(f"{filt} {product['visit']}: WHT-positive projected coverage {valid.mean():.2%}", flush=True)
        Image.fromarray(coverage.astype(np.uint8)*255, "L").save(OBS / f"m16-{filt.lower()}-wht-mask.png", optimize=True)
        filters[filt] = {"positive_wht_coverage_fraction": float(coverage.mean()), "mask": f"m16-{filt.lower()}-wht-mask.png", "visit_products": tile_records}
        print(f"{filt}: union coverage {coverage.mean():.2%}", flush=True)
    common = np.logical_and.reduce([np.asarray(Image.open(OBS / value["mask"])) > 0 for value in filters.values()])
    result = {"source": "MAST HLA SCI/WHT extensions from six HST proposal 13926 WFC3/UVIS visits per filter",
              "weight_definition": "Reprojected bilinear WHT > 0; union across the six visit products within each filter.",
              "science_render": "Heritage drizzled SCI images; weights used only as sky-coordinate quality/coverage masks.",
              "center_icrs_deg": [CENTER_RA, CENTER_DEC], "field_arcsec": FIELD_ARCSEC,
              "output_dimensions": [OUTPUT_SIZE, OUTPUT_SIZE], "filters": filters,
              "common_positive_wht_coverage_fraction": float(common.mean())}
    (OBS / "wht-coverage-metadata.json").write_text(json.dumps(result, indent=2)+"\n")
    print(f"Common three-filter positive-WHT coverage: {common.mean():.2%}")


if __name__ == "__main__":
    main()
