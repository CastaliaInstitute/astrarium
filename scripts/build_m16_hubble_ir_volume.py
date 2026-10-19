#!/usr/bin/env python3
"""Build a point-based 3D view from calibrated Hubble M16 WFC3/IR data.

Diffuse image samples are registered to the NASA/STScI gas geometry. Resolved
image peaks remain separate star points; Gaia matches use measured parallax,
while unmatched peaks use a documented Gaia-field distance prior for display.
"""
import gzip
import json
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / "parent-pwa" / "observations" / "m16-jwst"
IMAGE = ROOT / "parent-pwa" / "observations" / "imported" / "icrs-274-717042-13-834792-hubble-wfc3ir-f110w-f160w.png"
IMAGE_METADATA = IMAGE.with_suffix(".json")
GAIA = OBS / "gaia-dr3-wide-stars.json"
MODEL = OBS / "pillars-stsci-mesh.bin.gz"
OUTPUT = ROOT / "parent-pwa" / "observations" / "m16-hst" / "hubble-wfc3ir-volume.bin.gz"
METADATA = ROOT / "parent-pwa" / "observations" / "m16-hst" / "hubble-wfc3ir-volume-metadata.json"
MESH_COLORS = ROOT / "parent-pwa" / "observations" / "m16-hst" / "hubble-wfc3ir-mesh-colors.bin.gz"
MESH_COLOR_METADATA = ROOT / "parent-pwa" / "observations" / "m16-hst" / "hubble-wfc3ir-mesh-colors-metadata.json"
FIELD_WIDTH = 2.1
FIELD_HEIGHT = FIELD_WIDTH * 243.0415 / 260.0
IMAGE_X_STRETCH = 1.4  # registration correction to the published mesh's projected silhouette
GRID_SIZE = 256
GAS_STRIDE = 2
GAS_THRESHOLD = 45
STAR_THRESHOLD = 60
STAR_DEPTH_SEED = 161018


def mesh_depth_grid():
    mesh = gzip.open(MODEL, "rb").read()
    if mesh[:8] != b"ASTL3D1\0":
        raise ValueError("Unexpected STScI mesh encoding")
    vertex_count = struct.unpack_from("<I", mesh, 8)[0]
    vertices = np.frombuffer(mesh, dtype="<f4", count=vertex_count * 3, offset=40).reshape(-1, 3)
    lower, upper = vertices.min(axis=0), vertices.max(axis=0)
    center = (lower + upper) * 0.5
    dimensions = upper - lower
    common_scale = FIELD_WIDTH / max(dimensions[0], dimensions[2])
    image_x_scale = common_scale * IMAGE_X_STRETCH
    image_y_scale = FIELD_HEIGHT / max(dimensions[0], dimensions[2])
    depth_scale = FIELD_WIDTH / dimensions.max()
    projected = np.column_stack(((vertices[:, 0] - center[0]) * image_x_scale,
                                 (vertices[:, 2] - center[2]) * image_y_scale))
    depth = -(vertices[:, 1] - center[1]) * depth_scale

    x_index = (projected[:, 0] / FIELD_WIDTH + 0.5) * GRID_SIZE
    y_index = (0.5 - projected[:, 1] / FIELD_HEIGHT) * GRID_SIZE
    cells = np.clip(np.column_stack((x_index, y_index)).astype(int), 0, GRID_SIZE - 1)
    buckets = [[[] for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    for index, (gx, gy) in enumerate(cells):
        buckets[gy][gx].append(index)

    depth_grid = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.float32)
    support = np.zeros((GRID_SIZE, GRID_SIZE), dtype=bool)
    max_radius = 1.6 * max(FIELD_WIDTH, FIELD_HEIGHT) / GRID_SIZE
    for gy in range(GRID_SIZE):
        for gx in range(GRID_SIZE):
            candidates = []
            for radius in (2, 5, 11):
                for cy in range(max(0, gy - radius), min(GRID_SIZE, gy + radius + 1)):
                    for cx in range(max(0, gx - radius), min(GRID_SIZE, gx + radius + 1)):
                        candidates.extend(buckets[cy][cx])
                if candidates:
                    break
            if not candidates:
                continue
            indices = np.asarray(candidates, dtype=np.int32)
            target = np.array([((gx + 0.5) / GRID_SIZE - 0.5) * FIELD_WIDTH,
                               (0.5 - (gy + 0.5) / GRID_SIZE) * FIELD_HEIGHT])
            delta = projected[indices] - target
            nearest = indices[np.square(delta).sum(axis=1).argmin()]
            distance = float(np.square(projected[nearest] - target).sum()) ** 0.5
            depth_grid[gy, gx] = depth[nearest]
            support[gy, gx] = distance <= max_radius
    return depth_grid, support, image_x_scale, image_y_scale, depth_scale, vertices, center


def gaia_sources(image_meta, width, height):
    source = json.loads(GAIA.read_text())
    center_ra, center_dec = image_meta["target_center_icrs_deg"]
    half_width = image_meta["field_arcsec"] / 2
    half_height = image_meta["field_height_arcsec"] / 2
    angle = math.radians(image_meta["position_angle_deg"])
    ra0, dec0 = math.radians(center_ra), math.radians(center_dec)
    records = []
    for star in source["stars"]:
        if float(star.get("parallax_mas", 0)) <= 0:
            continue
        ra, dec = math.radians(float(star["ra_deg"])), math.radians(float(star["dec_deg"]))
        dra = (ra - ra0 + math.pi) % (2 * math.pi) - math.pi
        cosc = math.sin(dec0) * math.sin(dec) + math.cos(dec0) * math.cos(dec) * math.cos(dra)
        if cosc <= 0:
            continue
        east = math.cos(dec) * math.sin(dra) / cosc * 180 / math.pi * 3600
        north = (math.cos(dec0) * math.sin(dec) - math.sin(dec0) * math.cos(dec) * math.cos(dra)) / cosc * 180 / math.pi * 3600
        image_east = east * math.cos(angle) + north * math.sin(angle)
        image_north = -east * math.sin(angle) + north * math.cos(angle)
        if abs(image_east) > half_width or abs(image_north) > half_height:
            continue
        col = (image_east / half_width + 1) * 0.5 * (width - 1)
        row = (0.5 - image_north / (2 * half_height)) * (height - 1)
        distance_ly = 1000 / float(star["parallax_mas"]) * 3.26156
        compressed = 26 * math.log1p(distance_ly / 0.1) / math.log1p(6500 / 0.1)
        z = float(np.clip(26 - compressed, -1.5, 1.5))
        records.append({"col": col, "row": row, "z": z, "source_id": str(star["source_id"])})
    return records


def encode_records(x, y, z, rgb, sizes, star_flags):
    records = np.empty((len(x), 10), dtype=np.uint8)
    records[:, 0:2] = np.rint(x * 65535).astype("<u2").view(np.uint8).reshape(-1, 2)
    records[:, 2:4] = np.rint(y * 65535).astype("<u2").view(np.uint8).reshape(-1, 2)
    records[:, 4:6] = np.rint((z + 1.5) / 3.0 * 65535).astype("<u2").view(np.uint8).reshape(-1, 2)
    records[:, 6:9] = rgb
    records[:, 9] = sizes.astype(np.uint8) | np.where(star_flags, 0x80, 0).astype(np.uint8)
    return records


def main():
    image_meta = json.loads(IMAGE_METADATA.read_text())
    image = np.asarray(Image.open(IMAGE).convert("RGB"), dtype=np.uint8)
    height, width = image.shape[:2]
    brightness = image.max(axis=2)
    depth_grid, support, image_x_scale, image_y_scale, depth_scale, vertices, mesh_center = mesh_depth_grid()

    image_x = (vertices[:, 0] - mesh_center[0]) * image_x_scale
    image_y = (vertices[:, 2] - mesh_center[2]) * image_y_scale
    mesh_cols = np.clip(np.rint((image_x / FIELD_WIDTH + 0.5) * (width - 1)).astype(int), 0, width - 1)
    mesh_rows = np.clip(np.rint((0.5 - image_y / FIELD_HEIGHT) * (height - 1)).astype(int), 0, height - 1)
    vertex_rgb = image[mesh_rows, mesh_cols]
    mesh_color_bytes = b"ASTVC1\0\0" + struct.pack("<I", len(vertices)) + vertex_rgb.tobytes()
    with MESH_COLORS.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as zipped:
            zipped.write(mesh_color_bytes)
    MESH_COLOR_METADATA.write_text(json.dumps({
        "asset": MESH_COLORS.name,
        "source": "Calibrated MAST Hubble Heritage WFC3/IR F110W and F160W SCI mosaics",
        "image": IMAGE.relative_to(ROOT).as_posix(),
        "mesh": MODEL.name,
        "encoding": "Observed Hubble infrared composite RGB sampled onto STScI mesh vertices; no generated pixels or image plane",
        "registration_scales": {"image_plane_x": float(image_x_scale), "image_plane_y": float(image_y_scale)},
        "vertices": int(len(vertices)),
        "compressed_bytes": MESH_COLORS.stat().st_size,
    }, indent=2) + "\n")

    # Strict 3x3 maxima make one resolved source point per local image peak.
    padded = np.pad(brightness, 1, constant_values=0)
    peaks = np.ones_like(brightness, dtype=bool)
    for dy in range(3):
        for dx in range(3):
            if dx == 1 and dy == 1:
                continue
            peaks &= brightness > padded[dy:dy + height, dx:dx + width]
    peak_rows, peak_cols = np.nonzero(peaks & (brightness >= STAR_THRESHOLD))
    gaia = gaia_sources(image_meta, width, height)
    gaia_xy = np.asarray([[star["col"], star["row"]] for star in gaia], dtype=np.float32).reshape(-1, 2)
    peak_xy = np.column_stack((peak_cols, peak_rows)).astype(np.float32)
    matched = np.zeros(len(peak_rows), dtype=bool)
    if len(gaia_xy):
        nearest_gaia = np.square(peak_xy[:, None, :] - gaia_xy[None, :, :]).sum(axis=2).argmin(axis=1)
        nearest_distance = np.square(peak_xy - gaia_xy[nearest_gaia]).sum(axis=1) ** 0.5
        matched = nearest_distance <= 5.0

    # Remove detected stellar cores from the diffuse gas samples.
    star_holes = np.zeros((height, width), dtype=bool)
    radius = 2
    for row, col in zip(peak_rows, peak_cols):
        star_holes[max(0, row - radius):min(height, row + radius + 1),
                   max(0, col - radius):min(width, col + radius + 1)] = True

    rows, cols = np.mgrid[0:height:GAS_STRIDE, 0:width:GAS_STRIDE]
    sampled_brightness = brightness[::GAS_STRIDE, ::GAS_STRIDE]
    gx = np.clip(((cols / (width - 1)) * GRID_SIZE).astype(int), 0, GRID_SIZE - 1)
    gy = np.clip(((rows / (height - 1)) * GRID_SIZE).astype(int), 0, GRID_SIZE - 1)
    gas_mask = support[gy, gx] & (sampled_brightness >= GAS_THRESHOLD) & ~star_holes[::GAS_STRIDE, ::GAS_STRIDE]
    gas_rows, gas_cols = rows[gas_mask], cols[gas_mask]
    gas_gx, gas_gy = gx[gas_mask], gy[gas_mask]
    gas_rgb = image[gas_rows, gas_cols]
    gas_brightness = brightness[gas_rows, gas_cols].astype(np.float32)
    gas_key = gas_rows.astype(np.uint32) * 1664525 + gas_cols.astype(np.uint32) * 1013904223
    gas_jitter = ((gas_key % 65521).astype(np.float32) / 65520 - 0.5) * 0.035
    gas_z = np.clip(depth_grid[gas_gy, gas_gx] + gas_jitter, -1.5, 1.5)
    gas_sizes = np.clip(1 + (gas_brightness - GAS_THRESHOLD) / 36, 1, 6).astype(np.uint8)
    gas_records = encode_records(gas_cols / (width - 1), gas_rows / (height - 1), gas_z,
                                 gas_rgb, gas_sizes, np.zeros(len(gas_rows), dtype=bool))

    # Gaia detections keep their measured distances. Other Hubble peaks borrow
    # from the local Gaia depth distribution as an explicit visualization prior.
    star_rows, star_cols = peak_rows[~matched], peak_cols[~matched]
    star_rgb = image[star_rows, star_cols]
    star_brightness = brightness[star_rows, star_cols].astype(np.float32)
    gaia_depths = np.asarray([star["z"] for star in gaia], dtype=np.float32)
    if len(gaia_depths):
        seed = (star_rows.astype(np.uint32) * 1664525 + star_cols.astype(np.uint32) * 1013904223 + STAR_DEPTH_SEED)
        choice = (seed % len(gaia_depths)).astype(np.int32)
        star_z = gaia_depths[choice]
    else:
        seed = star_rows.astype(np.uint32) * 1664525 + star_cols.astype(np.uint32) * 1013904223 + STAR_DEPTH_SEED
        star_z = ((seed % 65521).astype(np.float32) / 65520 - 0.5) * 2.2
    star_sizes = np.clip(3 + (star_brightness - STAR_THRESHOLD) / 50, 3, 8).astype(np.uint8)
    star_records = encode_records(star_cols / (width - 1), star_rows / (height - 1), star_z,
                                  star_rgb, star_sizes, np.ones(len(star_rows), dtype=bool))
    records = np.concatenate((gas_records, star_records), axis=0)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as zipped:
            zipped.write(b"ASTIR1\0\0" + struct.pack("<I", len(records)))
            zipped.write(records.tobytes())
    METADATA.write_text(json.dumps({
        "asset": OUTPUT.name,
        "source": "Calibrated MAST Hubble Heritage WFC3/IR SCI mosaics, F110W and F160W",
        "image": IMAGE.relative_to(ROOT).as_posix(),
        "image_source_metadata": IMAGE_METADATA.relative_to(ROOT).as_posix(),
        "filters": ["F110W", "F160W"],
        "mesh_depth_reference": MODEL.name,
        "field_arcsec": image_meta["field_arcsec"],
        "field_height_arcsec": image_meta["field_height_arcsec"],
        "image_dimensions": [width, height],
        "registration_scales": {"image_plane_x": float(image_x_scale), "image_plane_y": float(image_y_scale), "depth": float(depth_scale)},
        "gas_points": int(len(gas_records)),
        "resolved_star_points": int(len(star_records)),
        "gaia_sources_in_field": len(gaia),
        "image_peaks_matched_to_gaia_and_rendered_in_measured_layer": int(matched.sum()),
        "depth_interpretation": "Gas samples follow the NASA/STScI authored visualization geometry. Gaia DR3 points retain measured parallax; other resolved Hubble point sources use a deterministic empirical Gaia-field depth prior for display and do not have individually measured distances.",
        "gas_geometry_mask": "Projected STScI mesh support; bright point-source cores removed from diffuse samples",
        "gas_threshold_max_channel": GAS_THRESHOLD,
        "star_peak_threshold_max_channel": STAR_THRESHOLD,
        "compressed_bytes": OUTPUT.stat().st_size,
        "mesh_color_asset": MESH_COLORS.name,
    }, indent=2) + "\n")
    print(f"Wrote {len(gas_records):,} gas samples and {len(star_records):,} Hubble IR point sources ({OUTPUT.stat().st_size:,} compressed bytes)")


if __name__ == "__main__":
    main()
