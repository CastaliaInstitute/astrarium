#!/usr/bin/env python3
"""Download and reproject HST Heritage M16 filter mosaics into an Astrarium view.

Inputs are the public WFC3/UVIS Level-4 Heritage HLSP science FITS mosaics from MAST.
The output filter planes and RGB image are built from calibrated FITS pixel values, not
NASA publicity composites and not generated nebula/star mattes.
"""
import json
import math
import os
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "m16-hst"
OUT = ROOT / "parent-pwa" / "observations" / "m16-hst"
MAST = "https://mast.stsci.edu/api/v0.1/Download/file?"
CENTER_RA = 274.721587
CENTER_DEC = -13.841549
FIELD_ARCSEC = 200.0
OUTPUT_SIZE = 2000
FILTER_BLACK_PERCENTILE = 5.0
FILTER_WHITE_PERCENTILE = 99.92
FILTER_LAYER_GAMMA = 0.85
FILTER_GAINS = {"F502N": 0.916515, "F657N": 0.894427, "F673N": 1.341641}
FILTER_CHANNEL_GAMMAS = {"F502N": 0.75, "F657N": 0.725, "F673N": 0.585}
COMPOSITE_ASINH_SCALE = 1.0
HIGHLIGHT_DESATURATION_START = 0.45
HIGHLIGHT_DESATURATION_FULL = 0.82
HIGHLIGHT_DESATURATION_STRENGTH = 0.85
# Hubble Heritage visible-light color mapping: [O III] blue, H-alpha+[N II] green, [S II] red.
FILTERS = {
    "F502N": ("hlsp_heritage_hst_wfc3-uvis_m16_f502n_v1_drz.fits", "blue"),
    "F657N": ("hlsp_heritage_hst_wfc3-uvis_m16_f657n_v1_drz.fits", "green"),
    "F673N": ("hlsp_heritage_hst_wfc3-uvis_m16_f673n_v1_drz.fits", "red"),
}


def mast_uri(dataset):
    return f"mast:HLSP/url/cgi-bin/getdata.cgi?dataset={dataset}"


def fetch_fits(filename):
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / filename
    if path.exists() and path.stat().st_size > 100_000:
        return path
    dataset = filename[:-5]
    uri = mast_uri(dataset)
    url = "https://mast.stsci.edu/api/v0.1/Download/file?" + urllib.parse.urlencode({"uri": uri})
    tmp = path.with_suffix(path.suffix + ".tmp")
    existing = tmp.stat().st_size if tmp.exists() else 0
    headers = {"User-Agent": "Astrarium/1.0 MAST HST data ingest"}
    if existing:
        headers["Range"] = f"bytes={existing}-"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=300) as response:
        status = response.status
        response_headers = response.headers
        append = existing and status == 206
        if existing and not append:
            existing = 0
        with open(tmp, "ab" if append else "wb") as output:
            while True:
                block = response.read(1 << 20)
                if not block:
                    break
                output.write(block)
    expected = None
    if response_headers.get("Content-Range"):
        expected = int(response_headers["Content-Range"].rsplit("/", 1)[1])
    elif response_headers.get("Content-Length"):
        expected = int(response_headers["Content-Length"]) + existing
    if expected and tmp.stat().st_size < expected:
        raise RuntimeError(f"Incomplete MAST FITS download ({tmp.stat().st_size}/{expected} bytes); rerun to resume")
    os.replace(tmp, path)
    return path


def read_header(path):
    header = {}
    cards = []
    with open(path, "rb") as stream:
        while True:
            block = stream.read(2880)
            if len(block) != 2880:
                raise RuntimeError(f"Incomplete FITS header in {path.name}")
            cards.append(block)
            done = False
            for start in range(0, 2880, 80):
                card = block[start:start + 80].decode("ascii", "replace")
                key = card[:8].strip()
                if key == "END":
                    done = True
                    break
                if card[8:10] == "= ":
                    value = card[10:30].strip()
                    if value.startswith("'"):
                        value = value[1:].split("'", 1)[0].strip()
                    else:
                        value = value.split("/", 1)[0].strip()
                        try:
                            value = float(value.replace("D", "E"))
                            if value.is_integer():
                                value = int(value)
                        except ValueError:
                            pass
                    header[key] = value
            if done:
                return header, len(cards) * 2880


def project_fits(path):
    header, data_offset = read_header(path)
    if header.get("NAXIS") != 2 or header.get("BITPIX") not in (-32, -64):
        raise RuntimeError(f"Expected 2-D floating-point science FITS, got {path.name}: {header.get('NAXIS')} / {header.get('BITPIX')}")
    ny, nx = int(header["NAXIS2"]), int(header["NAXIS1"])
    dtype = ">f4" if int(header["BITPIX"]) == -32 else ">f8"
    science = np.memmap(path, dtype=dtype, mode="r", offset=data_offset, shape=(ny, nx))
    cd = np.array([[float(header["CD1_1"]), float(header["CD1_2"])],
                   [float(header["CD2_1"]), float(header["CD2_2"])]], dtype=np.float64)
    inverse_cd = np.linalg.inv(cd)
    size = OUTPUT_SIZE
    scale = FIELD_ARCSEC / size / 3600.0 * math.pi / 180.0
    xx, yy = np.meshgrid(np.arange(size, dtype=np.float64), np.arange(size, dtype=np.float64))
    xi = (xx - (size - 1) / 2) * scale
    eta = - (yy - (size - 1) / 2) * scale
    rho = np.hypot(xi, eta)
    c = np.arctan(rho)
    ra0 = math.radians(CENTER_RA); dec0 = math.radians(CENTER_DEC)
    safe_rho = np.where(rho == 0, 1.0, rho)
    dec = np.arcsin(np.cos(c) * math.sin(dec0) + eta * np.sin(c) * math.cos(dec0) / safe_rho)
    ra = ra0 + np.arctan2(xi * np.sin(c), safe_rho * math.cos(dec0) * np.cos(c) - eta * math.sin(dec0) * np.sin(c))
    dra = (ra - math.radians(float(header["CRVAL1"])) + math.pi) % (2 * math.pi) - math.pi
    ref_dec = math.radians(float(header["CRVAL2"]))
    cosc = np.sin(ref_dec) * np.sin(dec) + math.cos(ref_dec) * np.cos(dec) * np.cos(dra)
    safe_cosc = np.where(cosc <= 1e-8, 1e-8, cosc)
    source_plane = np.stack([
        np.cos(dec) * np.sin(dra) / safe_cosc * 180 / math.pi,
        (math.cos(ref_dec) * np.sin(dec) - math.sin(ref_dec) * np.cos(dec) * np.cos(dra)) / safe_cosc * 180 / math.pi,
    ], axis=0).reshape(2, -1)
    delta = inverse_cd @ source_plane
    sx = (float(header["CRPIX1"]) - 1 + delta[0]).reshape(size, size)
    sy = (float(header["CRPIX2"]) - 1 + delta[1]).reshape(size, size)
    x0 = np.floor(sx).astype(np.int32); y0 = np.floor(sy).astype(np.int32)
    dx = sx - x0; dy = sy - y0
    valid = (cosc > 0) & (x0 >= 0) & (y0 >= 0) & (x0 + 1 < nx) & (y0 + 1 < ny)
    x = np.clip(x0, 0, nx - 2); y = np.clip(y0, 0, ny - 2)
    a = np.asarray(science[y, x], dtype=np.float32)
    b = np.asarray(science[y, x + 1], dtype=np.float32)
    c0 = np.asarray(science[y + 1, x], dtype=np.float32)
    d = np.asarray(science[y + 1, x + 1], dtype=np.float32)
    image = (a * (1 - dx) + b * dx) * (1 - dy) + (c0 * (1 - dx) + d * dx) * dy
    image[~valid] = np.nan
    return image, valid, header, data_offset


def display_stretch(image):
    finite = image[np.isfinite(image)]
    positive = finite[finite > 0]
    black = float(np.percentile(positive, FILTER_BLACK_PERCENTILE))
    white = float(np.percentile(positive, FILTER_WHITE_PERCENTILE))
    normalized = np.clip((np.nan_to_num(image, nan=black) - black) / max(white - black, 1e-20), 0, 1)
    stretched = np.arcsinh(3.0 * normalized) / np.arcsinh(3.0)
    return np.power(stretched, FILTER_LAYER_GAMMA), {
        "black_value": black,
        "black_percentile": FILTER_BLACK_PERCENTILE,
        "white_value": white,
        "white_percentile": FILTER_WHITE_PERCENTILE,
        "asinh_scale": 3.0,
        "gamma": FILTER_LAYER_GAMMA,
    }


def write_gaia_overlay():
    """Clip locally cached Gaia DR3 tiles to the same 240-arcsec TAN footprint."""
    import csv
    import glob
    rows = []
    ra0, dec0 = math.radians(CENTER_RA), math.radians(CENTER_DEC)
    radius = FIELD_ARCSEC / 3600.0
    for filename in glob.glob(str(ROOT / "data" / "gaia_full" / "g*_ra270-300_dec-30-30.csv")):
        with open(filename, newline="") as stream:
            for row in csv.DictReader(stream):
                try:
                    ra_deg, dec_deg = float(row["ra"]), float(row["dec"])
                    mag = float(row["phot_g_mean_mag"])
                    bp_rp = float(row["bp_rp"]) if row["bp_rp"] else None
                    plx = float(row["parallax"]) if row["parallax"] else None
                except (ValueError, KeyError):
                    continue
                ra, dec = math.radians(ra_deg), math.radians(dec_deg)
                dra = (ra - ra0 + math.pi) % (2 * math.pi) - math.pi
                cosc = math.sin(dec0) * math.sin(dec) + math.cos(dec0) * math.cos(dec) * math.cos(dra)
                if cosc <= 0:
                    continue
                xi = math.cos(dec) * math.sin(dra) / cosc * 180 / math.pi
                eta = (math.cos(dec0) * math.sin(dec) - math.sin(dec0) * math.cos(dec) * math.cos(dra)) / cosc * 180 / math.pi
                if abs(xi) > radius / 2 or abs(eta) > radius / 2:
                    continue
                rows.append({"ra_deg": ra_deg, "dec_deg": dec_deg, "g_mag": mag,
                             "bp_rp": bp_rp, "parallax_mas": plx})
    out = OUT / "gaia-dr3-stars.json"
    out.write_text(json.dumps({"source": "Gaia DR3", "center_icrs_deg": [CENTER_RA, CENTER_DEC],
                               "field_arcsec": FIELD_ARCSEC, "stars": rows}, separators=(",", ":")) + "\n")
    return len(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    layers = {}; products = {}; coverage = None
    for filt, (filename, hue) in FILTERS.items():
        path = fetch_fits(filename)
        image, valid, header, data_offset = project_fits(path)
        weight_mask_path = OUT / f"m16-{filt.lower()}-wht-mask.png"
        if not weight_mask_path.is_file():
            raise RuntimeError(f"Missing HLA WHT coverage mask {weight_mask_path.name}; run scripts/build_m16_hst_wht_masks.py first")
        with Image.open(weight_mask_path) as weight_mask_image:
            weight_mask = np.asarray(weight_mask_image.convert("L"), dtype=np.uint8) > 0
        if weight_mask.shape != valid.shape:
            raise RuntimeError(f"HLA WHT mask dimensions {weight_mask.shape} do not match SCI projection {valid.shape}")
        valid &= weight_mask
        image[~valid] = np.nan
        layer, stretch_meta = display_stretch(image)
        layers[filt] = layer
        coverage = valid if coverage is None else coverage & valid
        plane = np.clip(layer * 255, 0, 255).astype(np.uint8)
        Image.fromarray(plane, "L").save(OUT / f"m16-{filt.lower()}-aligned.png", optimize=True)
        products[filt] = {
            "source_uri": mast_uri(filename[:-5]),
            "source_filename": filename,
            "source_bytes": path.stat().st_size,
            "instrument": "WFC3/UVIS",
            "band": {"F502N": "[O III]", "F657N": "H-alpha + [N II]", "F673N": "[S II]"}[filt],
            "composite_gain": FILTER_GAINS[filt],
            "display_stretch": stretch_meta,
            "unit": header.get("BUNIT", ""),
            "fits_header_bytes": data_offset,
            "weight_mask_file": weight_mask_path.name,
            "weight_mask_source": "MAST HLA SCI/WHT products from the six matching HST proposal 13926 WFC3/UVIS visits, reprojected via each WHT FITS WCS and unioned within filter",
            "positive_wht_coverage_fraction": float(valid.mean()),
            "wcs": {key: header[key] for key in ("CRPIX1", "CRPIX2", "CRVAL1", "CRVAL2", "CD1_1", "CD1_2", "CD2_1", "CD2_2", "CTYPE1", "CTYPE2")},
        }
    # The Hubble Heritage palette maps oxygen to blue, hydrogen to green and sulfur to red.
    rgb = np.stack([
        layers["F673N"] * FILTER_GAINS["F673N"],
        layers["F657N"] * FILTER_GAINS["F657N"],
        layers["F502N"] * FILTER_GAINS["F502N"],
    ], axis=2)
    # Hubble Heritage's visible-light palette: sulfur/red, hydrogen/gold, oxygen/blue.
    rgb = np.arcsinh(COMPOSITE_ASINH_SCALE * rgb) / np.arcsinh(COMPOSITE_ASINH_SCALE)
    rgb = np.stack([
        np.clip(rgb[:, :, 0], 0, 1) ** FILTER_CHANNEL_GAMMAS["F673N"],
        np.clip(rgb[:, :, 1], 0, 1) ** FILTER_CHANNEL_GAMMAS["F657N"],
        np.clip(rgb[:, :, 2], 0, 1) ** FILTER_CHANNEL_GAMMAS["F502N"],
    ], axis=2)
    # The release-matched channel curves retain the nebular palette. Compress
    # saturation only in the brightest composite highlights, where the
    # independently stretched narrowband point-source cores clip and turn pink.
    luminance = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    highlight = np.clip(
        (luminance - HIGHLIGHT_DESATURATION_START)
        / (HIGHLIGHT_DESATURATION_FULL - HIGHLIGHT_DESATURATION_START),
        0,
        1,
    )
    highlight = highlight * highlight * (3 - 2 * highlight)
    saturation = 1 - HIGHLIGHT_DESATURATION_STRENGTH * highlight
    rgb = luminance[:, :, None] + (rgb - luminance[:, :, None]) * saturation[:, :, None]
    rgb = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(rgb, "RGB").save(OUT / "m16-wfc3uvis-mast-composite.png", optimize=True)
    Image.fromarray(rgb, "RGB").save(OUT / "eagle-nebula-m16-hubble-reconstruction.png", optimize=True)
    gaia_star_count = write_gaia_overlay()
    metadata = {
        "target": "M16 / Eagle Nebula / Pillars of Creation",
        "mission": "Hubble Space Telescope",
        "instrument": "WFC3/UVIS",
        "proposal_id": "13926",
        "observation_date": "2014-09",
        "archive": "MAST Hubble Heritage HLSP",
        "source_level": "Calibrated and drizzled Level-4 science FITS mosaics; 2014 WFC3 UVIS data",
        "composite_method": "WCS-reprojected calibrated FITS SCI pixels; NASA Hubble 2014 palette (blue=F502N [O III], green=F657N H-alpha+[N II], red=F673N [S II]); each filter uses a recorded percentile asinh stretch; reference-tuned display curves map the nebular colors and a highlight-only saturation rolloff reduces pink clipping in bright stars; no generated image pixels, nebula mattes, or star mattes",
        "center_icrs_deg": [CENTER_RA, CENTER_DEC],
        "field_arcsec": FIELD_ARCSEC,
        "output_dimensions": [OUTPUT_SIZE, OUTPUT_SIZE],
        "pixel_scale_arcsec": FIELD_ARCSEC / OUTPUT_SIZE,
        "common_coverage_fraction": float(coverage.mean()),
        "coverage_method": "Finite HST SCI samples intersected with per-filter positive HLA WHT masks projected from all six matching proposal 13926 visits; the displayed composite is black outside common valid coverage.",
        "weight_mask_inventory": {
            "archive": "MAST HLA / CAOM", "proposal_id": "13926", "visits": 6,
            "filters": ["F502N", "F657N", "F673N"],
            "products_with_sci_and_wht_extensions": 18,
            "application_status": "projected via each WHT FITS WCS, unioned within filter, and applied to the corresponding Heritage SCI plane"
        },
        "weight_mask_provenance": "MAST HLA SCI/WHT products for proposal 13926; exact per-visit data URIs, HDU offsets, WCS, and cutout footprints are recorded in hla-wht-provenance.json and wht-coverage-metadata.json.",
        "no_synthetic_pixels": True,
        "no_synthetic_mattes": True,
        "filters": products,
        "composite_display": {
            "filter_gains": FILTER_GAINS,
            "channel_gamma_exponents": FILTER_CHANNEL_GAMMAS,
            "asinh_scale": COMPOSITE_ASINH_SCALE,
            "calibration_reference": "NASA 2014 Hubble WFC3/UVIS release; approximately registered, used only to tune display curves",
            "calibration_method": "Independent channel gain and power-exponent fit on matching registered pixels, blended 50% with the prior mapping; a smooth saturation rolloff is applied to the brightest highlights to control narrowband star-core color",
            "curve_fit_interpolation_fraction": 0.5,
            "per_channel_fit_mean_squared_error": {"F673N_red": 0.01134, "F657N_green": 0.00403, "F502N_blue": 0.00367},
            "combined_rgb_mean_squared_error": 0.00644,
            "registered_highpass_correlation": 0.8208,
            "highlight_saturation_rolloff": {
                "start_luminance": HIGHLIGHT_DESATURATION_START,
                "full_luminance": HIGHLIGHT_DESATURATION_FULL,
                "strength": HIGHLIGHT_DESATURATION_STRENGTH,
                "method": "smoothstep blend toward channel-neutral luminance; applies to composite highlights only",
            },
        },
        "gaia_dr3_overlay": {"file": "gaia-dr3-stars.json", "stars": gaia_star_count,
                             "source": "Local Gaia DR3 cached tiles clipped using the shared TAN sky footprint"},
        "references": ["https://archive.stsci.edu/prepds/heritage/m16/", "https://archive.stsci.edu/prepds/heritage/m16/hlsp_heritage_hst_wfc3_m16_all_v1_readme.txt", "https://science.nasa.gov/asset/hubble/a-view-of-the-pillars-of-creation-in-visible-and-in-near-infrared-light/"],
        "nasa_visible_reference": {
            "file": "nasa-wfc3uvis-reference.jpg",
            "url": "https://assets.science.nasa.gov/dynamicimage/assets/science/missions/hubble/releases/2015/01/STScI-01EVT2RBPDHYADWQX62QR1ABJ2.tif?fit=clip&h=3000&w=3000",
            "proposal_id": "13926",
            "filters": ["F502N", "F657N", "F673N"],
        },
    }
    (OUT / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Wrote HST WFC3/UVIS 3-filter composite; common footprint {coverage.mean():.1%}; Gaia DR3 overlay {gaia_star_count:,} stars")
    for filt, layer in layers.items():
        print(f"  {filt}: {int(np.count_nonzero(layer)):,} finite output pixels")


if __name__ == "__main__":
    main()
