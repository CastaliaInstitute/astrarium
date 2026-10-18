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
MODEL = OBS / "pillars-stsci-mesh.bin.gz"
VERTEX_COLORS = OBS / "pillars-jwst-colors.bin.gz"
VERTEX_COLOR_METADATA = OBS / "pillars-jwst-colors-metadata.json"
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

    # Sample the calibrated telescope signal at each vertex of the published
    # STScI gas geometry. This keeps the observation in Three.js geometry
    # vertex colors instead of drawing the full square as a 2D point plane.
    mesh_bytes = gzip.open(MODEL, "rb").read()
    if mesh_bytes[:8] != b"ASTL3D1\0":
        raise ValueError(f"Unexpected STScI mesh format in {MODEL}")
    vertex_count, index_count = struct.unpack_from("<II", mesh_bytes, 8)
    mesh_positions = np.frombuffer(mesh_bytes, dtype="<f4", count=vertex_count * 3, offset=40).reshape(-1, 3)
    mesh_min, mesh_max = mesh_positions.min(axis=0), mesh_positions.max(axis=0)
    mesh_center = (mesh_min + mesh_max) * 0.5
    mesh_scale = FIELD_SIZE / float((mesh_max - mesh_min).max())
    image_width, image_height = rgb.shape[1], rgb.shape[0]
    image_x = (mesh_positions[:, 0] - mesh_center[0]) * mesh_scale
    image_y = (mesh_positions[:, 2] - mesh_center[2]) * mesh_scale
    image_cols = np.rint((image_x / FIELD_SIZE + 0.5) * (image_width - 1)).astype(np.int32)
    image_rows = np.rint((0.5 - image_y / FIELD_SIZE) * (image_height - 1)).astype(np.int32)
    image_cols = np.clip(image_cols, 0, image_width - 1)
    image_rows = np.clip(image_rows, 0, image_height - 1)
    vertex_rgb = np.clip(rgb[image_rows, image_cols], 0, 1)
    vertex_rgb_u8 = np.rint(vertex_rgb * 255).astype(np.uint8)
    vertex_bytes = b"ASTVC1\0\0" + struct.pack("<I", vertex_count) + vertex_rgb_u8.tobytes()
    with VERTEX_COLORS.open("wb") as stream:
        with gzip.GzipFile(fileobj=stream, mode="wb", compresslevel=9, mtime=0) as zipped:
            zipped.write(vertex_bytes)
    VERTEX_COLOR_METADATA.write_text(json.dumps({
        "asset": VERTEX_COLORS.name,
        "source": "MAST JWST/NIRCam proposal 2739 calibrated Level-3 SCI arrays in six filters",
        "source_filters": [name.upper() for name, _, _ in FILTERS],
        "mesh": MODEL.name,
        "encoding": "RGB vertex colors sampled from WCS-aligned calibrated SCI signal; no image plane or texture",
        "registration": "The 200 arcsec square image field is projected onto the STScI mesh x/z bounds; this assigns observed colors to model vertices but does not add measured depth to the authored gas geometry.",
        "vertices": int(vertex_count),
        "compressed_bytes": VERTEX_COLORS.stat().st_size,
    }, indent=2) + "\n")

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
        "encoding": "Each retained sample is a colored Three.js point: normalized 16-bit x/y, RGB from the six filter SCI values, and point size from signal strength. This legacy projected-point asset is not used by the live 3D scene.",
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
    print(f"Wrote JWST SCI vertex colors for {vertex_count:,} STScI mesh vertices ({VERTEX_COLORS.stat().st_size:,} compressed bytes)")


if __name__ == "__main__":
    main()
