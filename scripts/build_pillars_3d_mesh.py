#!/usr/bin/env python3
"""Build the compact Astrarium mesh from NASA/STScI's four pillar STLs."""
from __future__ import annotations

import gzip
import hashlib
import json
import struct
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data/nebula-3d/pillars-of-creation"
OUTPUT_DIR = ROOT / "parent-pwa/observations/m16-jwst"
OUTPUT = OUTPUT_DIR / "pillars-stsci-mesh.bin.gz"
METADATA = OUTPUT_DIR / "pillars-stsci-mesh-metadata.json"
VOXEL_MM = 0.5
SOURCES = {
    "pillar-1a.stl": "https://assets.science.nasa.gov/content/dam/science/cds/3d/resources/printable/pillars-of-creation/Pillars%20of%20Creation%20(pillar%201A).stl?emrc=6ad474c287612",
    "pillar-1b.stl": "https://assets.science.nasa.gov/content/dam/science/cds/3d/resources/printable/pillars-of-creation/Pillars%20of%20Creation%20(pillar%201B).stl?emrc=6ad474c287d83",
    "pillar-2.stl": "https://assets.science.nasa.gov/content/dam/science/cds/3d/resources/printable/pillars-of-creation/Pillars%20of%20Creation%20(pillar%202).stl?emrc=6ad474c28844f",
    "pillar-3.stl": "https://assets.science.nasa.gov/content/dam/science/cds/3d/resources/printable/pillars-of-creation/Pillars%20of%20Creation%20(pillar%203).stl?emrc=6ad474c288b5a",
}


def load_triangles(path: Path) -> np.ndarray:
    content = path.read_bytes()
    if len(content) < 84:
        raise ValueError(f"Truncated STL: {path}")
    count = struct.unpack_from("<I", content, 80)[0]
    if len(content) != 84 + count * 50:
        raise ValueError(f"Expected binary STL triangles in {path}")
    return np.ndarray((count, 12), dtype="<f4", buffer=content, offset=84, strides=(50, 4))[:, 3:12].reshape(-1, 3).copy()


def main() -> None:
    source_data = {}
    groups = []
    for filename, page in SOURCES.items():
        path = SOURCE_DIR / filename
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(urllib.request.urlopen(page, timeout=120).read())
        raw = path.read_bytes()
        source_data[filename] = {
            "url": page,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "triangles": struct.unpack_from("<I", raw, 80)[0],
        }
        groups.append(load_triangles(path))

    triangles = np.concatenate(groups, axis=0)
    minimum, maximum = triangles.min(0), triangles.max(0)
    quantized = np.rint((triangles - minimum) / VOXEL_MM).astype(np.uint16)
    keys = ((quantized[:, 0].astype(np.uint64) << 32)
            | (quantized[:, 1].astype(np.uint64) << 16)
            | quantized[:, 2].astype(np.uint64))
    unique_keys, inverse = np.unique(keys, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    valid = ((faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 2] != faces[:, 0]))
    faces = faces[valid].astype("<u4")
    vertices = np.empty((len(unique_keys), 3), dtype="<f4")
    vertices[:, 0] = minimum[0] + ((unique_keys >> 32) & 65535) * VOXEL_MM
    vertices[:, 1] = minimum[1] + ((unique_keys >> 16) & 65535) * VOXEL_MM
    vertices[:, 2] = minimum[2] + (unique_keys & 65535) * VOXEL_MM
    raw_mesh = (struct.pack("<8sII6f", b"ASTL3D1\0", len(vertices), faces.size, *minimum, *maximum)
                + vertices.tobytes() + faces.tobytes())
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("wb") as stream:
        with gzip.GzipFile(fileobj=stream, mode="wb", compresslevel=7, mtime=0) as zipped:
            zipped.write(raw_mesh)
    METADATA.write_text(json.dumps({
        "asset": OUTPUT.name,
        "source": "NASA/STScI Pillars of Creation 3D visualization, four individually published pillar components",
        "source_page": "https://science.nasa.gov/3d-resources/pillars-of-creation/",
        "source_components": source_data,
        "simplification": f"{VOXEL_MM:g} mm vertex clustering; degenerate faces removed",
        "source_triangles": int(len(triangles) / 3),
        "vertices": int(len(vertices)),
        "triangles": int(len(faces)),
        "bounds_mm": {"min": minimum.tolist(), "max": maximum.tolist()},
        "compressed_bytes": OUTPUT.stat().st_size,
        "scientific_status": "NASA/STScI authored scientific visualization geometry; relative shape and orientation are illustrative, not direct volumetric tomography or a measured depth map",
    }, indent=2) + "\n")
    print(f"Wrote {len(faces):,} triangles / {len(vertices):,} vertices, {OUTPUT.stat().st_size:,} compressed bytes")


if __name__ == "__main__":
    main()
