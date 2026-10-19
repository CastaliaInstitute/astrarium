#!/usr/bin/env python3
"""Encode diffuse Hubble M16 IR pixels without assigning invented 3D depth."""
import gzip
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / "parent-pwa" / "observations" / "m16-hst"
IMAGE = ROOT / "parent-pwa" / "observations" / "imported" / "icrs-274-717042-13-834792-hubble-wfc3ir-f110w-f160w.png"
IMAGE_METADATA = IMAGE.with_suffix(".json")
OUTPUT = OBS / "hubble-wfc3ir-volume.bin.gz"
METADATA = OBS / "hubble-wfc3ir-volume-metadata.json"
SAMPLE_STRIDE = 2
DIFFUSE_THRESHOLD = 45
POINT_SOURCE_THRESHOLD = 60


def main():
    image_metadata = json.loads(IMAGE_METADATA.read_text())
    image = np.asarray(Image.open(IMAGE).convert("RGB"), dtype=np.uint8)
    height, width = image.shape[:2]
    brightness = image.max(axis=2)

    # Remove small cores at observed, isolated image peaks. This separates the
    # diffuse IR display samples from stellar-looking pixels without using a
    # model silhouette, synthesized mask, or guessed source distances.
    padded = np.pad(brightness, 1, constant_values=0)
    peaks = np.ones_like(brightness, dtype=bool)
    for dy in range(3):
        for dx in range(3):
            if dx != 1 or dy != 1:
                peaks &= brightness > padded[dy:dy + height, dx:dx + width]
    point_rows, point_cols = np.nonzero(peaks & (brightness >= POINT_SOURCE_THRESHOLD))
    point_cores = np.zeros((height, width), dtype=bool)
    for row, col in zip(point_rows, point_cols):
        point_cores[max(0, row - 2):min(height, row + 3), max(0, col - 2):min(width, col + 3)] = True

    rows, cols = np.mgrid[0:height:SAMPLE_STRIDE, 0:width:SAMPLE_STRIDE]
    keep = (brightness[::SAMPLE_STRIDE, ::SAMPLE_STRIDE] >= DIFFUSE_THRESHOLD) & ~point_cores[::SAMPLE_STRIDE, ::SAMPLE_STRIDE]
    rows, cols = rows[keep], cols[keep]
    colors = image[rows, cols]
    signal = brightness[rows, cols].astype(np.uint8)
    count = len(rows)

    records = np.zeros((count, 10), dtype=np.uint8)
    records[:, 0:2] = np.rint(cols / (width - 1) * 65535).astype("<u2").view(np.uint8).reshape(-1, 2)
    records[:, 2:4] = np.rint(rows / (height - 1) * 65535).astype("<u2").view(np.uint8).reshape(-1, 2)
    # The legacy binary record retains a z field for compatibility. Zero means
    # every diffuse sample is on the same explicitly projected observation plane.
    records[:, 4:6] = np.full(count, 32768, dtype="<u2").view(np.uint8).reshape(-1, 2)
    records[:, 6:9] = colors
    records[:, 9] = np.clip(1 + (signal.astype(np.int16) - DIFFUSE_THRESHOLD) // 8, 1, 127).astype(np.uint8)

    raw_data = b"ASTIR1\0\0" + struct.pack("<I", count) + records.tobytes()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as zipped:
            zipped.write(raw_data)

    metadata = {
        "asset": OUTPUT.name,
        "source": "Hubble Heritage WFC3/IR F110W + F160W display composite, derived from calibrated MAST SCI mosaics and registered to a common WCS grid",
        "image": IMAGE.relative_to(ROOT).as_posix(),
        "image_source_metadata": IMAGE_METADATA.relative_to(ROOT).as_posix(),
        "filters": ["F110W", "F160W"],
        "pixel_values": "False-color display RGB derived from calibrated SCI mosaics; not raw flux units.",
        "center_icrs_deg": image_metadata["target_center_icrs_deg"],
        "position_angle_deg": image_metadata["position_angle_deg"],
        "field_arcsec": image_metadata["field_arcsec"],
        "field_height_arcsec": image_metadata["field_height_arcsec"],
        "image_dimensions": [width, height],
        "sample_stride_pixels": SAMPLE_STRIDE,
        "display_rgb_threshold_max_channel": DIFFUSE_THRESHOLD,
        "point_source_peak_threshold_max_rgb": POINT_SOURCE_THRESHOLD,
        "point_source_core_radius_pixels": 2,
        "samples": count,
        "source_stars_in_layer": 0,
        "depth": {
            "status": "unknown",
            "rendering": "calibrated diffuse samples projected onto an observation plane at the nominal M16 distance; this is not a measured gas volume",
            "nominal_earth_distance_ly": 6500,
            "distance_source": "https://science.nasa.gov/asset/hubble/eagle-nebula-pillars-of-creation/"
        },
        "star_handling": "Detected point-source cores are excluded from this diffuse layer; catalog stars are rendered separately only at catalog distances.",
        "geometry_mask": "none",
        "compressed_bytes": OUTPUT.stat().st_size
    }
    METADATA.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Wrote {count:,} diffuse samples from calibrated Hubble pixels ({OUTPUT.stat().st_size:,} compressed bytes)")


if __name__ == "__main__":
    main()
