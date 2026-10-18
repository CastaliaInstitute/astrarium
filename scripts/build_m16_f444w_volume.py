#!/usr/bin/env python3
"""Encode calibrated JWST F444W pixels as depth-registered Three.js dust points.

The F444W image supplies sky position and infrared brightness. Published STScI
Pillars mesh vertices supply a projected 3D depth envelope; a deterministic
small depth spread gives the pixels volume without presenting that spread as
measured tomography.
"""
import gzip
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / "parent-pwa" / "observations" / "m16-jwst"
IMAGE = OBS / "highres" / "m16-f444w-aligned.png"
MODEL = OBS / "pillars-stsci-mesh.bin.gz"
OUTPUT = OBS / "f444w-dust-volume.bin.gz"
METADATA = OBS / "f444w-dust-volume-metadata.json"
FIELD_SIZE = 2.1
STRIDE = 3
THRESHOLD = 78


def palette(values):
    """One-filter infrared display palette; input remains calibrated F444W flux."""
    stops = np.array([0, 55, 90, 125, 165, 205, 255], dtype=np.float32)
    colors = np.array([
        [2, 5, 14], [4, 19, 34], [8, 49, 77], [41, 88, 113],
        [137, 104, 81], [224, 150, 81], [255, 224, 165],
    ], dtype=np.float32)
    return np.stack([np.interp(values, stops, colors[:, c]) for c in range(3)], axis=1).round().astype(np.uint8)


def main():
    image = np.asarray(Image.open(IMAGE).convert("L"), dtype=np.uint8)
    mesh_bytes = gzip.open(MODEL, "rb").read()
    if mesh_bytes[:8] != b"ASTL3D1\0":
        raise ValueError("Unexpected STScI mesh encoding")
    vertex_count, _ = struct.unpack_from("<II", mesh_bytes, 8)
    vertices = np.frombuffer(mesh_bytes, dtype="<f4", count=vertex_count * 3, offset=40).reshape(-1, 3)
    mesh_min, mesh_max = vertices.min(axis=0), vertices.max(axis=0)
    center = (mesh_min + mesh_max) * 0.5
    scale = FIELD_SIZE / float((mesh_max - mesh_min).max())
    # The source mesh is Z-up. Its X/Z projection matches the calibrated image.
    projected = np.column_stack(((vertices[:, 0] - center[0]) * scale,
                                 (vertices[:, 2] - center[2]) * scale))
    depth = -(vertices[:, 1] - center[1]) * scale
    # Build a compact nearest-depth lookup on the image field. This avoids a
    # scipy dependency in the asset builder and is far finer than display scale.
    grid_size = 256
    cell_of_vertex = np.clip(((projected / FIELD_SIZE + 0.5) * grid_size).astype(int), 0, grid_size - 1)
    buckets = [[[] for _ in range(grid_size)] for _ in range(grid_size)]
    for index, (gx, gy) in enumerate(cell_of_vertex):
        buckets[gy][gx].append(index)
    depth_grid = np.empty((grid_size, grid_size), dtype=np.float32)
    for gy in range(grid_size):
        for gx in range(grid_size):
            candidates = []
            for radius in (2, 5, 11):
                for cy in range(max(0, gy - radius), min(grid_size, gy + radius + 1)):
                    for cx in range(max(0, gx - radius), min(grid_size, gx + radius + 1)):
                        candidates.extend(buckets[cy][cx])
                if candidates:
                    break
            if not candidates:
                depth_grid[gy, gx] = 0.0
                continue
            indexes = np.asarray(candidates, dtype=np.int32)
            target = np.array([((gx + 0.5) / grid_size - 0.5) * FIELD_SIZE,
                               (0.5 - (gy + 0.5) / grid_size) * FIELD_SIZE])
            nearest = indexes[np.square(projected[indexes] - target).sum(axis=1).argmin()]
            depth_grid[gy, gx] = depth[nearest]

    sampled = image[::STRIDE, ::STRIDE]
    rows, cols = np.nonzero(sampled >= THRESHOLD)
    rows = rows * STRIDE
    cols = cols * STRIDE
    width, height = image.shape[1], image.shape[0]
    x = (cols / (width - 1) - 0.5) * FIELD_SIZE
    y = (0.5 - rows / (height - 1)) * FIELD_SIZE
    gx = np.clip(((x / FIELD_SIZE + 0.5) * grid_size).astype(int), 0, grid_size - 1)
    gy = np.clip(((0.5 - y / FIELD_SIZE) * grid_size).astype(int), 0, grid_size - 1)

    flux = image[rows, cols].astype(np.float32)
    # Depth spread is a deterministic visualization around the published model
    # surface. It reveals volume in Three.js, but is not claimed as observation.
    key = (rows.astype(np.uint32) * 1664525 + cols.astype(np.uint32) * 1013904223)
    jitter = ((key % 65521).astype(np.float32) / 65520.0 - 0.5) * (0.04 + 0.16 * flux / 255.0)
    z = np.clip(depth_grid[gy, gx] + jitter, -1.25, 1.25)

    # record: normalized image x/y, encoded mesh depth, RGB, display size
    records = np.empty((len(rows), 10), dtype=np.uint8)
    records[:, 0:2] = np.rint(cols / (width - 1) * 65535).astype("<u2").view(np.uint8).reshape(-1, 2)
    records[:, 2:4] = np.rint(rows / (height - 1) * 65535).astype("<u2").view(np.uint8).reshape(-1, 2)
    records[:, 4:6] = np.rint((z + 1.5) / 3.0 * 65535).astype("<u2").view(np.uint8).reshape(-1, 2)
    records[:, 6:9] = palette(flux)
    records[:, 9] = np.clip(1 + (flux - THRESHOLD) / 45, 1, 4).astype(np.uint8)
    header = b"ASTIR1\0\0" + struct.pack("<I", len(records))
    with OUTPUT.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as zipped:
            zipped.write(header)
            zipped.write(records.tobytes())
    METADATA.write_text(json.dumps({
        "asset": OUTPUT.name,
        "source": "MAST JWST/NIRCam proposal 2739 calibrated Level-3 F444W SCI pixels, WHT-masked before alignment",
        "image": IMAGE.name,
        "filter": "F444W",
        "wavelength_microns": 4.44,
        "mesh_depth_reference": MODEL.name,
        "encoding": "Per-pixel Three.js points with registered sky coordinates, F444W display intensity, and depth sampled from the projected STScI mesh",
        "depth_interpretation": "Mesh-registered visualization depth plus deterministic shallow dispersion; the source image does not provide per-pixel tomography",
        "field_arcsec": 200.0,
        "image_dimensions": [width, height],
        "sampling_stride": STRIDE,
        "signal_threshold_display_value": THRESHOLD,
        "points": int(len(records)),
        "compressed_bytes": OUTPUT.stat().st_size,
    }, indent=2) + "\n")
    print(f"Wrote {len(records):,} F444W dust points ({OUTPUT.stat().st_size:,} compressed bytes)")


if __name__ == "__main__":
    main()
