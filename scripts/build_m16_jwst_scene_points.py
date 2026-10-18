#!/usr/bin/env python3
"""Encode calibrated JWST M16 filter samples as a compact Three.js point cloud.

Inputs are the six WCS-aligned, single-filter display planes generated directly
from MAST Level-3 SCI/WHT arrays. The result is point geometry, never a texture.
"""
import gzip
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / "parent-pwa" / "observations" / "m16-jwst"
OUTPUT = OBS / "m16-science-points.bin.gz"
METADATA = OBS / "m16-science-points-metadata.json"
STRIDE = 2
SIGNAL_THRESHOLD = 0.60
FIELD_SIZE = 2.1
FILTERS = (
    ("f090w", (0.25, 0.0, 1.0), 0.35),
    ("f187n", (0.0, 0.0, 1.0), 1.0),
    ("f200w", (0.0, 0.8, 1.0), 2.0),
    ("f335m", (1.0, 0.8, 0.0), 1.7),
    ("f444w", (1.0, 0.28, 0.0), 1.1),
    ("f470n", (1.0, 0.0, 0.0), 1.1),
)


def main():
    layers = []
    shape = None
    for name, color, gain in FILTERS:
        image = np.asarray(Image.open(OBS / f"m16-{name}-aligned.png"), dtype=np.float32) / 255.0
        if image.ndim != 2 or (shape is not None and image.shape != shape):
            raise ValueError(f"Unexpected aligned image shape for {name}: {image.shape}")
        shape = image.shape
        layers.append((image[::STRIDE, ::STRIDE], np.asarray(color, dtype=np.float32), gain))

    rgb = np.zeros((*layers[0][0].shape, 3), dtype=np.float32)
    for layer, color, gain in layers:
        rgb += layer[:, :, None] * color * gain
    luminance = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    white = float(np.percentile(luminance, 99.9))
    if not np.isfinite(white) or white <= 0:
        raise ValueError("No positive JWST science signal in aligned M16 bands")
    normalized = luminance / white
    mapped = np.arcsinh(4.0 * normalized) / np.arcsinh(4.0)
    rgb *= 0.9 / white
    rgb *= (mapped / np.maximum(normalized, 1e-12))[:, :, None]
    rgb = np.stack([
        np.clip(rgb[:, :, index] * gain, 0.0, 1.0) ** gamma
        for index, (gain, gamma) in enumerate(((1.125, 1.18), (1.1, 0.8), (0.9, 0.62)))
    ], axis=2)

    signal = rgb.max(axis=2)
    rows, cols = np.nonzero(signal >= SIGNAL_THRESHOLD)
    colors = np.clip(rgb[rows, cols] * 255.0, 0, 255).astype(np.uint8)
    brightness = signal[rows, cols]
    sizes = np.clip(1.0 + 2.5 * np.sqrt(brightness), 1.0, 4.0).astype(np.uint8)
    records = np.empty((len(rows), 8), dtype=np.uint8)
    x16 = np.rint(cols / max(1, rgb.shape[1] - 1) * 65535).astype("<u2")
    y16 = np.rint(rows / max(1, rgb.shape[0] - 1) * 65535).astype("<u2")
    records[:, 0:2] = x16.view(np.uint8).reshape(-1, 2)
    records[:, 2:4] = y16.view(np.uint8).reshape(-1, 2)
    records[:, 4:7] = colors
    records[:, 7] = sizes

    with gzip.open(OUTPUT, "wb", compresslevel=9) as stream:
        stream.write(b"ASTPTS1\0")
        stream.write(struct.pack("<I", len(records)))
        stream.write(records.tobytes())
    metadata = {
        "asset": OUTPUT.name,
        "source": "MAST JWST/NIRCam proposal 2739 Level-3 calibrated SCI pixels, with WHT validity masks applied before alignment",
        "source_metadata": "metadata.json",
        "source_filters": [name.upper() for name, _, _ in FILTERS],
        "encoding": "Each retained sample is a colored Three.js point: normalized 16-bit x/y, RGB from the six filter SCI values, and point size from signal strength. No composite image or image texture is used.",
        "projection": "200 arcsec square WCS-aligned field; point depth is a projected observation layer, not measured tomography. STScI geometry supplies the separately authored 3D gas form.",
        "field_arcsec": 200.0,
        "grid_stride": STRIDE,
        "signal_threshold": SIGNAL_THRESHOLD,
        "points": int(len(records)),
        "compressed_bytes": OUTPUT.stat().st_size,
        "science_pixels_are_calibrated_flux": True,
    }
    METADATA.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Wrote {len(records):,} JWST SCI point samples ({OUTPUT.stat().st_size:,} compressed bytes)")


if __name__ == "__main__":
    main()
