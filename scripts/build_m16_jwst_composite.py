#!/usr/bin/env python3
"""Build a WCS-aligned M16 JWST image from calibrated MAST Level-3 FITS data.

The builder reads only SCI and WHT pixel ranges covering the M16 output field.
It does not download the multi-gigabyte complete i2d products, and it never uses
the archive's display JPEG previews as image input.
"""
import json
import math
import re
import urllib.request
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "parent-pwa" / "observations" / "m16-jwst"
CACHE = ROOT / "data" / "m16-jwst-cutouts"
BASE = "https://mast.stsci.edu/api/v0.1/Download/file?uri=mast:JWST/product/"
CENTER_RA, CENTER_DEC = 274.721587, -13.841549
FIELD_ARCSEC, OUTPUT_SIZE = 200.0, 2000
COMPOSITE_WHITE_TARGET = 0.9
COMPOSITE_TONE_MAP_Q = 4.0
FILTER_BLACK_PERCENTILE = 10.0
FILTER_LAYER_GAMMA = 0.55
FILTER_GAINS = {
    "F090W": 0.35,
    "F187N": 1.0,
    "F200W": 2.0,
    "F335M": 1.7,
    "F444W": 1.1,
    "F470N": 1.1,
}
# Reference-tuned output-channel transfer, after the NASA filter hues have been
# mixed and the shared luminance curve applied. This affects display only.
COMPOSITE_CHANNEL_GAINS = {"red": 1.125, "green": 1.1, "blue": 0.9}
COMPOSITE_CHANNEL_GAMMAS = {"red": 1.18, "green": 0.8, "blue": 0.62}
PRODUCTS = {
    "F090W": ("jw02739-o001_t001_nircam_clear-f090w_i2d.fits", (0.25, 0.0, 1.0)),
    "F187N": ("jw02739-o001_t001_nircam_clear-f187n_i2d.fits", (0.0, 0.0, 1.0)),
    "F200W": ("jw02739-o001_t001_nircam_clear-f200w_i2d.fits", (0.0, 0.8, 1.0)),
    "F335M": ("jw02739-o001_t001_nircam_clear-f335m_i2d.fits", (1.0, 0.8, 0.0)),
    "F444W": ("jw02739-o001_t001_nircam_clear-f444w_i2d.fits", (1.0, 0.28, 0.0)),
    "F470N": ("jw02739-o001_t001_nircam_f444w-f470n_i2d.fits", (1.0, 0.0, 0.0)),
}


def value(card):
    raw = card[10:80].strip()
    if raw.startswith("'"):
        return raw[1:].split("'", 1)[0].strip()
    raw = raw.split("/", 1)[0].strip()
    try:
        n = float(raw.replace("D", "E"))
        return int(n) if n.is_integer() else n
    except ValueError:
        return raw


def read_header(url, offset):
    req = urllib.request.Request(url, headers={"Range": f"bytes={offset}-{offset + 131071}"})
    with urllib.request.urlopen(req, timeout=60) as response:
        data = response.read()
        if response.status != 206:
            raise RuntimeError(f"MAST did not honor FITS header range: {url}")
    header = {}
    for block_offset in range(0, len(data), 2880):
        block = data[block_offset:block_offset + 2880]
        if len(block) != 2880:
            break
        for i in range(0, 2880, 80):
            card = block[i:i + 80].decode("ascii", "replace")
            key = card[:8].strip()
            if key == "END":
                return header, offset + block_offset + 2880
            if card[8:10] == "= ":
                header[key] = value(card)
    raise RuntimeError(f"No FITS END card at byte {offset}: {url}")


def hdu_data_bytes(header):
    if int(header.get("NAXIS", 0)) == 0:
        return 0
    size = abs(int(header.get("BITPIX", 8))) // 8
    for axis in range(1, int(header.get("NAXIS", 0)) + 1):
        size *= int(header[f"NAXIS{axis}"])
    return (size + int(header.get("PCOUNT", 0))) * int(header.get("GCOUNT", 1))


def find_hdu(url, name):
    header, data_offset = read_header(url, 0)
    offset = (data_offset + hdu_data_bytes(header) + 2879) // 2880 * 2880
    while True:
        header, data_offset = read_header(url, offset)
        if header.get("EXTNAME", "").strip().upper() == name:
            if header.get("NAXIS") != 2 or header.get("BITPIX") != -32:
                raise RuntimeError(f"Expected float32 2-D {name} extension in {url}")
            return header, data_offset
        offset = (data_offset + hdu_data_bytes(header) + 2879) // 2880 * 2880


def read_crop(url, h, data_offset, bounds):
    """Fetch a 2-D float FITS crop as a multipart range of discontiguous rows."""
    x0, y0, x1, y1 = bounds
    nx = int(h["NAXIS1"]); row_bytes = nx * 4; width = x1 - x0
    result = np.empty((y1 - y0, width), dtype=np.float32)
    rows_per_request = 96
    batches = []
    for y_first in range(y0, y1, rows_per_request):
        y_last = min(y1, y_first + rows_per_request)
        ranges = []
        for y in range(y_first, y_last):
            start = data_offset + y * row_bytes + x0 * 4
            ranges.append(f"{start}-{start + width * 4 - 1}")
        batches.append((y_first, y_last, ranges))

    def fetch(batch):
        y_first, y_last, ranges = batch
        req = urllib.request.Request(url, headers={"Range": "bytes=" + ",".join(ranges)})
        with urllib.request.urlopen(req, timeout=90) as response:
            if response.status != 206:
                raise RuntimeError(f"MAST did not honor pixel range: {url}")
            content_type = response.headers.get("Content-Type", "")
            data = response.read()
        boundary_match = re.search(r"boundary=\"?([^;\" ]+)", content_type, re.I)
        if not boundary_match:
            raise RuntimeError(f"Expected multipart byte ranges, got {content_type}")
        parts = data.split(("--" + boundary_match.group(1)).encode())[1:-1]
        if len(parts) != y_last - y_first:
            raise RuntimeError(f"Expected {y_last-y_first} FITS rows, got {len(parts)}")
        rows = np.empty((y_last - y_first, width), dtype=np.float32)
        for row, part in enumerate(parts):
            header, sep, payload = part.partition(b"\r\n\r\n")
            match = re.search(rb"Content-range:\s*bytes\s+(\d+)-(\d+)", header, re.I)
            payload = payload.removesuffix(b"\r\n")
            if not sep or not match or len(payload) != width * 4:
                raise RuntimeError("Malformed multipart FITS row response")
            rows[row] = np.frombuffer(payload, dtype=">f4")
        return y_first, rows

    with ThreadPoolExecutor(max_workers=8) as pool:
        for y_first, rows in pool.map(fetch, batches):
            result[y_first - y0:y_first - y0 + rows.shape[0]] = rows
    return result


def matrix(h):
    if all(k in h for k in ("CD1_1", "CD1_2", "CD2_1", "CD2_2")):
        return np.array([[h["CD1_1"], h["CD1_2"]], [h["CD2_1"], h["CD2_2"]]], dtype=float)
    pc = np.array([[h.get("PC1_1", 1.0), h.get("PC1_2", 0.0)],
                   [h.get("PC2_1", 0.0), h.get("PC2_2", 1.0)]], dtype=float)
    return np.diag([h["CDELT1"], h["CDELT2"]]) @ pc


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


def pixels_for_sky(h, ra, dec):
    ra0, dec0 = math.radians(h["CRVAL1"]), math.radians(h["CRVAL2"])
    dra = (ra - ra0 + math.pi) % (2 * math.pi) - math.pi
    cosc = np.sin(dec0) * np.sin(dec) + math.cos(dec0) * np.cos(dec) * np.cos(dra)
    safe = np.maximum(cosc, 1e-10)
    xi = np.cos(dec) * np.sin(dra) / safe * 180 / math.pi
    eta = (math.cos(dec0) * np.sin(dec) - math.sin(dec0) * np.cos(dec) * np.cos(dra)) / safe * 180 / math.pi
    delta = np.linalg.inv(matrix(h)) @ np.stack([xi.ravel(), eta.ravel()])
    sx = (h["CRPIX1"] - 1 + delta[0]).reshape(ra.shape)
    sy = (h["CRPIX2"] - 1 + delta[1]).reshape(dec.shape)
    return sx, sy, cosc


def project(crop, h, bounds, ra, dec):
    x0, y0, _, _ = bounds
    sx, sy, cosc = pixels_for_sky(h, ra, dec)
    sx -= x0; sy -= y0
    ix, iy = np.floor(sx).astype(np.int32), np.floor(sy).astype(np.int32)
    dx, dy = sx - ix, sy - iy
    valid = (cosc > 0) & (ix >= 0) & (iy >= 0) & (ix + 1 < crop.shape[1]) & (iy + 1 < crop.shape[0])
    x, y = np.clip(ix, 0, crop.shape[1] - 2), np.clip(iy, 0, crop.shape[0] - 2)
    a, b = crop[y, x], crop[y, x + 1]
    c, d = crop[y + 1, x], crop[y + 1, x + 1]
    image = (a * (1 - dx) + b * dx) * (1 - dy) + (c * (1 - dx) + d * dx) * dy
    valid &= np.isfinite(image)
    image[~valid] = np.nan
    return image, valid


def display_stretch(image, valid):
    samples = image[valid & np.isfinite(image)]
    # Use the measured background as black and a robust high percentile as white.
    black = float(np.percentile(samples, FILTER_BLACK_PERCENTILE))
    white = float(np.percentile(samples, 99.9))
    normalized = np.clip((np.nan_to_num(image, nan=black) - black) / max(white - black, 1e-30), 0, 1)
    stretched = np.arcsinh(7 * normalized) / np.arcsinh(7)
    return np.power(stretched, FILTER_LAYER_GAMMA), {
        "black_value": black, "black_percentile": FILTER_BLACK_PERCENTILE,
        "white_value": white, "white_percentile": 99.9,
        "stretch": f"{FILTER_BLACK_PERCENTILE:g}th percentile black, 99.9th percentile white, asinh(7x), gamma {FILTER_LAYER_GAMMA}",
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cached_metadata_path = ROOT / "parent-pwa" / "observations" / "m16-jwst" / "metadata.json"
    cached_metadata = json.loads(cached_metadata_path.read_text()) if cached_metadata_path.exists() else {}
    ra, dec = output_grid(); layers = {}; products = {}; common = None
    for filt, (filename, color) in PRODUCTS.items():
        url = BASE + filename
        CACHE.mkdir(parents=True, exist_ok=True)
        sci_cache = CACHE / f"{filt.lower()}-sci.npy"
        wht_cache = CACHE / f"{filt.lower()}-wht.npy"
        record = cached_metadata.get("filters", {}).get(filt)
        use_cached_headers = bool(record and sci_cache.exists() and wht_cache.exists())
        if use_cached_headers:
            nx, ny = record["source_dimensions"]
            h = {**record["wcs"], "NAXIS": 2, "NAXIS1": nx, "NAXIS2": ny, "BITPIX": -32, "BUNIT": record.get("unit", "")}
            wh = h
            sci_offset = record["sci_data_offset"]
            wht_offset = record["wht_data_offset"]
            bounds = tuple(record["source_cutout_xyxy"])
        else:
            h, sci_offset = find_hdu(url, "SCI")
            wh, wht_offset = find_hdu(url, "WHT")
            sx, sy, _ = pixels_for_sky(h, ra, dec)
            nx, ny = int(h["NAXIS1"]), int(h["NAXIS2"])
            inside = (sx >= -2) & (sx < nx + 1) & (sy >= -2) & (sy < ny + 1)
            if not inside.any():
                raise RuntimeError(f"M16 footprint misses {filename}")
            bounds = (max(0, int(np.floor(sx[inside].min())) - 2),
                      max(0, int(np.floor(sy[inside].min())) - 2),
                      min(nx, int(np.ceil(sx[inside].max())) + 3),
                      min(ny, int(np.ceil(sy[inside].max())) + 3))
            if bounds[2] - bounds[0] < 2 or bounds[3] - bounds[1] < 2:
                raise RuntimeError(f"Invalid M16 cutout bounds for {filename}: {bounds}")
        if sci_cache.exists() and wht_cache.exists():
            sci = np.load(sci_cache, mmap_mode="r")
            wht = np.load(wht_cache, mmap_mode="r")
            if list(sci.shape) != [bounds[3] - bounds[1], bounds[2] - bounds[0]] or wht.shape != sci.shape:
                sci_cache.unlink(missing_ok=True); wht_cache.unlink(missing_ok=True)
                sci = read_crop(url, h, sci_offset, bounds); np.save(sci_cache, sci)
                wht = read_crop(url, wh, wht_offset, bounds); np.save(wht_cache, wht)
        else:
            sci = read_crop(url, h, sci_offset, bounds); np.save(sci_cache, sci)
            wht = read_crop(url, wh, wht_offset, bounds); np.save(wht_cache, wht)
        layer, valid = project(sci, h, bounds, ra, dec)
        weight, wvalid = project(wht, h, bounds, ra, dec)
        valid &= wvalid & np.isfinite(weight) & (weight > 0)
        layer[~valid] = np.nan
        layers[filt], stretch_meta = display_stretch(layer, valid)
        common = valid if common is None else common & valid
        Image.fromarray((np.clip(np.nan_to_num(layers[filt]), 0, 1) * 255).astype(np.uint8), "L").save(OUT / f"m16-{filt.lower()}-aligned.png", optimize=True)
        products[filt] = {
            "filename": filename, "source_uri": f"mast:JWST/product/{filename}", "source_url": url,
            "instrument": "NIRCam", "product_level": "Level 3 i2d",
            "source_level": "Calibrated FITS SCI array with WHT quality mask",
            "unit": h.get("BUNIT", ""), "source_file_bytes": "range-read SCI/WHT cutouts; full FITS not downloaded",
            "source_dimensions": [nx, ny], "sci_data_offset": sci_offset, "wht_data_offset": wht_offset,
            "source_cutout_xyxy": list(bounds), "cutout_bytes_per_extension": int(sci.nbytes),
            "wcs": {k: h[k] for k in ("CRPIX1", "CRPIX2", "CRVAL1", "CRVAL2", "CDELT1", "CDELT2", "PC1_1", "PC1_2", "PC2_1", "PC2_2", "CTYPE1", "CTYPE2") if k in h},
            "display_color_rgb": [round(c * 255) for c in color],
            "display_gain": FILTER_GAINS[filt], "display_stretch": stretch_meta,
            "valid_wht_coverage_fraction": float(valid.mean()),
        }
        print(f"Loaded calibrated JWST M16 {filt}: cutout {sci.shape[1]}x{sci.shape[0]}, {valid.mean():.1%} WHT coverage", flush=True)

    rgb = np.zeros((OUTPUT_SIZE, OUTPUT_SIZE, 3), np.float32)
    for filt, (_, color) in PRODUCTS.items():
        rgb += layers[filt][:, :, None] * np.asarray(color, np.float32) * FILTER_GAINS[filt]
    # A single shared scale preserves the assigned filter hues. Normalizing
    # channels independently changes those hues when their total color weights
    # differ (green was boosted relative to red and blue in earlier renders).
    luminance = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    composite_white = float(np.percentile(luminance[common], 99.9))
    if not np.isfinite(composite_white) or composite_white <= 0:
        raise RuntimeError("JWST RGB composite has no positive finite signal")
    rgb *= COMPOSITE_WHITE_TARGET / composite_white
    # A shared luminance curve lifts faint structure while preserving each
    # pixel's filter-mixed hue. Independent RGB curves would shift the palette.
    normalized_luminance = luminance / composite_white
    mapped_luminance = np.arcsinh(COMPOSITE_TONE_MAP_Q * normalized_luminance) / np.arcsinh(COMPOSITE_TONE_MAP_Q)
    rgb *= (mapped_luminance / np.maximum(normalized_luminance, 1e-12))[:, :, None]
    rgb = np.stack([
        np.clip(rgb[:, :, i] * COMPOSITE_CHANNEL_GAINS[channel], 0, 1)
        ** COMPOSITE_CHANNEL_GAMMAS[channel]
        for i, channel in enumerate(("red", "green", "blue"))
    ], axis=2)
    rgb[~common] = 0
    rgb = (np.clip(rgb, 0.0, 1.0) * 255).astype(np.uint8)
    Image.fromarray(rgb, "RGB").save(OUT / "m16-nircam-mast-composite.png", optimize=True)
    if OUTPUT_SIZE == 2000:
        artifact = ROOT / "artifacts" / "deep-sky-screenshots" / "eagle-nebula-m16-reconstruction.png"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgb, "RGB").save(artifact, optimize=True)
    metadata = {
        "target": "M16 / Eagle Nebula / Pillars of Creation", "mission": "JWST", "instrument": "NIRCam",
        "proposal_id": "2739", "telescope_observation_date": "2022-08-14", "source_archive": "MAST public JWST archive",
        "source_level": "Calibrated Level 3 i2d FITS science pixels; SCI/WHT cutouts read by HTTP byte ranges",
        "composite_method": "Reprojected calibrated FITS SCI flux pixels; WHT > 0 mask; per-filter 10th-to-99.9th-percentile asinh display stretch with explicit gamma and per-filter display gains; NASA Pillars filter hues additively mixed, then a shared asinh(Q=4) luminance tone curve lifts faint signal; final per-channel gain and gamma are fitted against the approximately registered NASA release for display only; out-of-range display values clipped; no generated nebula or star mattes",
        "center_icrs_deg": [CENTER_RA, CENTER_DEC], "field_arcsec": FIELD_ARCSEC,
        "output_dimensions": [OUTPUT_SIZE, OUTPUT_SIZE], "pixel_scale_arcsec": FIELD_ARCSEC / OUTPUT_SIZE,
        "common_wht_coverage_fraction": float(common.mean()), "composite_white_luminance": composite_white,
        "composite_tone_map": {"method": "hue-preserving asinh luminance", "q": COMPOSITE_TONE_MAP_Q, "input_white_target": COMPOSITE_WHITE_TARGET},
        "composite_channel_calibration": {
            "reference": "NASA JWST NIRCam Pillars release; approximate registration without FITS WCS",
            "method": "Per-channel gain and power-exponent fit against matching registered pixels; applied after shared asinh luminance mapping; NASA pixels are not included in the rendered output",
            "channel_gains": COMPOSITE_CHANNEL_GAINS,
            "channel_gamma_exponents": COMPOSITE_CHANNEL_GAMMAS,
            "reference_mask": "reference maximum RGB > 0.04 and render maximum RGB > 0.015; every 20th selected pixel in row-major order",
            "training_channel_mse_before": {"red": 0.006403, "green": 0.014949, "blue": 0.022063},
            "training_channel_mse_after": {"red": 0.005821, "green": 0.006044, "blue": 0.005082},
            "training_combined_rgb_mse_before": 0.014472,
            "training_combined_rgb_mse_after": 0.005649,
        },
        "filters": products,
        "references": ["https://science.nasa.gov/asset/webb/pillars-of-creation-nircam-image/", "https://assets.science.nasa.gov/dynamicimage/assets/science/missions/webb/science/2022/10/STScI-01GGF8H15VZ09MET9HFBRQX4S3.png?fit=clip&h=2000&w=1155", "https://mast.stsci.edu/"],
    }
    (OUT / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Wrote calibrated WCS-aligned JWST M16 composite; common WHT coverage {common.mean():.1%}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-size", type=int, default=OUTPUT_SIZE, choices=(2000, 6000),
                        help="square registered output in pixels; 6000 matches the native JWST sampling more closely")
    parser.add_argument("--output-dir", type=Path, default=OUT,
                        help="output directory (default: the standard 2000px M16 view)")
    args = parser.parse_args()
    OUTPUT_SIZE = args.output_size
    OUT = args.output_dir.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    main()
