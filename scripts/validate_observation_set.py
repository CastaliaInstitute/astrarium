#!/usr/bin/env python3
"""Validate bundled telescope observation products against their manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "parent-pwa/observations/validation-set.json"


def read_json(path: Path):
    return json.loads(path.read_text())


def check_file(root: Path, relpath: str, label: str, errors: list[str]) -> bool:
    path = root / "parent-pwa" / relpath
    if path.is_file() and path.stat().st_size > 0:
        return True
    errors.append(f"Missing or empty {label}: {path.relative_to(root)}")
    return False


def image_summary(path: Path) -> dict:
    with Image.open(path) as source:
        image = source.convert("RGB")
        pixels = np.asarray(image, dtype=np.uint8)
    luminance = pixels.max(axis=2)
    return {
        "dimensions": [int(pixels.shape[1]), int(pixels.shape[0])],
        "unique_colors_sampled": int(len(np.unique(pixels[::8, ::8].reshape(-1, 3), axis=0))),
        "nonblack_fraction": float(np.mean(luminance > 0)),
        "signal_percentiles": [float(v) for v in np.percentile(luminance, [50, 90, 99, 99.9])],
    }


def rgb_distribution_summary(path: Path, dimensions: tuple[int, int], flip_horizontal: bool = False, flip_vertical: bool = False) -> dict:
    """Return descriptive RGB quartiles for visual comparison, not photometry."""
    with Image.open(path) as source:
        image = source.convert("RGB").resize(dimensions, Image.Resampling.BOX)
        if flip_horizontal:
            image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if flip_vertical:
            image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        pixels = np.asarray(image, dtype=np.uint8)
    values = np.percentile(pixels.reshape(-1, 3), [25, 50, 75], axis=0)
    return {"p25_p50_p75_by_channel": values.T.round(2).tolist()}


def registered_highpass_similarity(reference_path: Path, image_path: Path, size: tuple[int, int], max_shift: int, flip_reference_horizontal: bool = False, flip_reference_vertical: bool = False) -> dict:
    """Compare resolved star/nebula structure while suppressing display stretch."""
    with Image.open(reference_path) as source:
        reference = source.convert("RGB")
        if flip_reference_horizontal:
            reference = reference.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if flip_reference_vertical:
            reference = reference.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        reference = reference.resize(size, Image.Resampling.LANCZOS).convert("L")
    with Image.open(image_path) as source:
        candidate = source.convert("RGB").resize(size, Image.Resampling.LANCZOS).convert("L")
    reference_hp = np.asarray(reference, dtype=np.float32) - np.asarray(reference.filter(ImageFilter.GaussianBlur(4)), dtype=np.float32)
    candidate_pixels = np.asarray(candidate, dtype=np.float32)
    candidate_hp = candidate_pixels - np.asarray(candidate.filter(ImageFilter.GaussianBlur(4)), dtype=np.float32)
    valid = candidate_pixels > 0
    best = (-2.0, 0, 0)
    width, height = size
    for dy in range(-max_shift, max_shift + 1):
        ref_y = slice(max(0, dy), min(height, height + dy))
        img_y = slice(max(0, -dy), min(height, height - dy))
        for dx in range(-max_shift, max_shift + 1):
            ref_x = slice(max(0, dx), min(width, width + dx))
            img_x = slice(max(0, -dx), min(width, width - dx))
            mask = valid[img_y, img_x]
            if int(mask.sum()) < 5000:
                continue
            x = reference_hp[ref_y, ref_x][mask]
            y = candidate_hp[img_y, img_x][mask]
            score = float(np.corrcoef(x, y)[0, 1])
            if score > best[0]:
                best = (score, dx, dy)
    return {"highpass_correlation": best[0], "shift_pixels": [best[1], best[2]], "comparison_dimensions": list(size), "max_search_shift_pixels": max_shift, "reference_flipped_horizontally": flip_reference_horizontal, "reference_flipped_vertically": flip_reference_vertical}


def close(actual, expected, tolerance=1e-6):
    return math.isclose(float(actual), float(expected), rel_tol=0, abs_tol=tolerance)


def sky_wcs_matrix(header: dict) -> np.ndarray:
    """Return the FITS linear pixel-to-tangent-plane matrix in degrees/pixel."""
    if all(key in header for key in ("CD1_1", "CD1_2", "CD2_1", "CD2_2")):
        return np.array([[header["CD1_1"], header["CD1_2"]], [header["CD2_1"], header["CD2_2"]]], dtype=float)
    if "CDELT1" not in header or "CDELT2" not in header:
        raise ValueError("FITS WCS lacks a CD matrix and CDELT scale")
    pc = np.array([[header.get("PC1_1", 1), header.get("PC1_2", 0)],
                   [header.get("PC2_1", 0), header.get("PC2_2", 1)]], dtype=float)
    return np.diag([header["CDELT1"], header["CDELT2"]]) @ pc


def validate_target(target: dict, root: Path) -> tuple[dict, list[str]]:
    errors: list[str] = []
    observations = []
    observation_summaries = {}
    center = target["expected_center_icrs_deg"]
    field = target["expected_field_arcsec"]
    expected_dims = target["expected_dimensions"]
    target_folders = {Path(relpath).parent.name for relpath in target["observations"]}
    require_aligned_layers = target.get("require_aligned_layers", True)
    for relpath in target["observations"]:
        path = root / "parent-pwa" / relpath
        if not path.is_file():
            errors.append(f"Missing metadata: {path.relative_to(root)}")
            continue
        meta = read_json(path)
        observations.append(meta)
        observation_summaries[relpath] = meta
        expected_filters = target.get("expected_filters", {}).get(relpath)
        if expected_filters is not None:
            actual_filters = sorted(meta.get("filters", {}))
            if actual_filters != sorted(expected_filters):
                errors.append(f"{target['id']}: {relpath} filters {actual_filters} != expected {sorted(expected_filters)}")
        expected_channel_filters = target.get("expected_channel_filters", {}).get(relpath)
        if expected_channel_filters is not None:
            actual_channel_filters = sorted(channel.get("filter") for channel in meta.get("channels", []) if channel.get("filter"))
            if actual_channel_filters != sorted(expected_channel_filters):
                errors.append(f"{target['id']}: {relpath} channel filters {actual_channel_filters} != expected {sorted(expected_channel_filters)}")
        expected_palette = target.get("expected_channel_palette_rgb", {}).get(relpath)
        if expected_palette is not None:
            actual_palette = {channel.get("filter"): channel.get("palette_rgb") for channel in meta.get("channels", []) if channel.get("filter")}
            if actual_palette != expected_palette:
                errors.append(f"{target['id']}: {relpath} filter palette {actual_palette} != expected {expected_palette}")
        expected_gains = target.get("expected_channel_display_gains", {}).get(relpath)
        if expected_gains:
            channels = {channel.get("filter"): channel for channel in meta.get("channels", [])}
            for band, expected_gain in expected_gains.items():
                actual_gain = channels.get(band, {}).get("display_stretch", {}).get("display_gain")
                if actual_gain is None or not close(actual_gain, expected_gain, 1e-5):
                    errors.append(f"{target['id']}: {relpath} {band} display gain {actual_gain!r} != expected {expected_gain}")
        expected_palette_gain = target.get("expected_palette_gain")
        if expected_palette_gain is not None:
            actual_gain = meta.get("display_stretch", {}).get("palette_gain")
            if actual_gain is None or not close(actual_gain, expected_palette_gain, 1e-5):
                errors.append(f"{target['id']}: {relpath} palette gain {actual_gain!r} != expected {expected_palette_gain}")
    if require_aligned_layers:
        for folder in target_folders:
            base = root / "parent-pwa/observations" / folder
            for image_path in sorted(base.glob("*-aligned.png")):
                check_file(root, f"observations/{folder}/{image_path.name}", f"{target['id']} filter layer", errors)
            if not list(base.glob("*-aligned.png")):
                errors.append(f"No aligned filter layer PNGs found for {target['id']} in {base.relative_to(root)}")
    layer_summaries = {}
    for relpath, filters in target.get("expected_filters", {}).items():
        if not require_aligned_layers:
            continue
        prefix = target.get("layer_prefixes", {}).get(relpath)
        filenames = target.get("layer_files", {}).get(relpath, {})
        if not prefix and not filenames:
            errors.append(f"{target['id']}: no layer filename prefix declared for {relpath}")
            continue
        folder = Path(relpath).parent
        for band in filters:
            filename = filenames.get(band) if filenames else f"{prefix}-{band.lower()}-aligned.png"
            layer_relpath = str(folder / filename)
            image_path = root / "parent-pwa" / layer_relpath
            if not check_file(root, layer_relpath, f"{target['id']} {band} aligned layer", errors):
                continue
            try:
                summary = image_summary(image_path)
                layer_summaries[layer_relpath] = summary
                if summary["dimensions"] != expected_dims:
                    errors.append(f"{target['id']}: {layer_relpath} pixels {summary['dimensions']} != expected {expected_dims}")
                if summary["unique_colors_sampled"] < 4 or summary["nonblack_fraction"] < 0.001:
                    errors.append(f"{target['id']}: {layer_relpath} contains too little image signal: {summary}")
            except Exception as exc:
                errors.append(f"{target['id']}: could not decode {layer_relpath}: {exc}")

    for meta in observations:
        actual_center = meta.get("target_center_icrs_deg") or meta.get("center_icrs_deg")
        if not actual_center:
            errors.append(f"{target['id']}: observation metadata lacks target center")
        elif len(actual_center) != 2 or not all(close(a, b) for a, b in zip(actual_center, center)):
            errors.append(f"{target['id']}: center {actual_center} != expected {center}")
        if "field_arcsec" not in meta:
            errors.append(f"{target['id']}: observation metadata lacks field_arcsec")
        elif not close(meta["field_arcsec"], field, 1e-4):
            errors.append(f"{target['id']}: field {meta['field_arcsec']} != expected {field} arcsec")
        expected_height = target.get("expected_field_height_arcsec")
        if expected_height is not None:
            actual_height = meta.get("field_height_arcsec")
            if actual_height is None or not close(actual_height, expected_height, 1e-4):
                errors.append(f"{target['id']}: field height {actual_height!r} != expected {expected_height} arcsec")
        expected_pa = target.get("expected_position_angle_deg")
        if expected_pa is not None:
            actual_pa = meta.get("position_angle_deg")
            if actual_pa is None or not close(actual_pa, expected_pa, 1e-4):
                errors.append(f"{target['id']}: position angle {actual_pa!r} != expected {expected_pa} degrees")
        dims = meta.get("output_dimensions")
        if dims is None:
            errors.append(f"{target['id']}: observation metadata lacks output_dimensions")
        elif dims != expected_dims:
            errors.append(f"{target['id']}: dimensions {dims} != expected {expected_dims}")

    wcs_checks = []
    alignment_spec = target.get("expected_wcs_alignment")
    if alignment_spec:
        min_dot = float(alignment_spec.get("minimum_axis_alignment_cosine", 0.999))
        max_center_offset = float(alignment_spec.get("max_source_center_offset_arcsec", 1.0))
        theta = math.radians(float(target.get("expected_position_angle_deg", 0)))
        output_x = np.array([math.cos(theta), math.sin(theta)])
        output_y_down = np.array([math.sin(theta), -math.cos(theta)])
        for relpath, meta in observation_summaries.items():
            products = meta.get("source_products", [])
            if not products:
                errors.append(f"{target['id']}: {relpath} has no source FITS WCS products")
                continue
            for source in products:
                header = source.get("science_wcs") or {}
                try:
                    matrix = sky_wcs_matrix(header)
                    src_x, src_y = matrix[:, 0], matrix[:, 1]
                    src_x = src_x / np.linalg.norm(src_x)
                    src_y = src_y / np.linalg.norm(src_y)
                    x_alignment = float(np.dot(src_x, output_x))
                    y_alignment = float(np.dot(src_y, output_y_down))
                    ra = float(header["CRVAL1"])
                    dec = float(header["CRVAL2"])
                    dra = (ra - center[0] + 180) % 360 - 180
                    center_offset = math.hypot(dra * math.cos(math.radians(center[1])), dec - center[1]) * 3600
                    result = {
                        "filter": source.get("filter"),
                        "x_axis_alignment_cosine": x_alignment,
                        "y_axis_alignment_cosine": y_alignment,
                        "source_center_offset_arcsec": center_offset,
                    }
                    wcs_checks.append(result)
                    if min(x_alignment, y_alignment) < min_dot:
                        errors.append(f"{target['id']}: {source.get('filter')} source WCS axes do not align with output PA {target.get('expected_position_angle_deg')} (cosines {x_alignment:.6f}, {y_alignment:.6f})")
                    if center_offset > max_center_offset:
                        errors.append(f"{target['id']}: {source.get('filter')} source WCS center is {center_offset:.3f} arcsec from the expected field center")
                except (KeyError, TypeError, ValueError, np.linalg.LinAlgError) as exc:
                    errors.append(f"{target['id']}: cannot verify {source.get('filter')} source FITS WCS alignment: {exc}")

    for relpath, fields in target.get("coverage_assertions", {}).items():
        meta = observation_summaries.get(relpath, {})
        for metadata_key, expected in fields.items():
            actual = meta.get(metadata_key)
            if actual is None:
                errors.append(f"{target['id']}: {relpath} lacks coverage value {metadata_key}")
            elif not close(actual, expected, 0.003):
                errors.append(f"{target['id']}: {relpath} {metadata_key}={actual} != expected ~{expected}")

    rendered_summaries = {}
    for relpath in target.get("rendered_images", []):
        if check_file(root, relpath, f"{target['id']} rendered comparison", errors):
            path = root / "parent-pwa" / relpath
            try:
                summary = image_summary(path)
                rendered_summaries[relpath] = summary
                image_expected_dims = target.get("expected_rendered_dimensions", {}).get(relpath, expected_dims)
                if summary["dimensions"] != image_expected_dims:
                    errors.append(f"{target['id']}: {relpath} pixels {summary['dimensions']} != expected {image_expected_dims}")
                if summary["unique_colors_sampled"] < 24 or summary["nonblack_fraction"] < 0.03:
                    errors.append(f"{target['id']}: {relpath} has too little visible image signal: {summary}")
            except Exception as exc:
                errors.append(f"{target['id']}: could not decode {relpath}: {exc}")
    morphology_comparisons = []
    for comparison in target.get("morphology_comparisons", []):
        first = root / "parent-pwa" / comparison["first"]
        second = root / "parent-pwa" / comparison["second"]
        comparison_id = comparison["id"]
        if not first.is_file() or not second.is_file():
            errors.append(f"{target['id']}: morphology comparison {comparison_id} is missing an input image")
            continue
        similarity = registered_highpass_similarity(
            first,
            second,
            tuple(comparison.get("comparison_dimensions", [360, 360])),
            int(comparison.get("max_search_shift_pixels", 4)),
            bool(comparison.get("flip_reference_horizontally", False)),
            bool(comparison.get("flip_reference_vertically", False)),
        )
        similarity["id"] = comparison_id
        similarity["first"] = comparison["first"]
        similarity["second"] = comparison["second"]
        reference_rgb = rgb_distribution_summary(first, tuple(comparison.get("comparison_dimensions", [360, 360])), bool(comparison.get("flip_reference_horizontally", False)), bool(comparison.get("flip_reference_vertically", False)))
        candidate_rgb = rgb_distribution_summary(second, tuple(comparison.get("comparison_dimensions", [360, 360])))
        reference_median = np.asarray(reference_rgb["p25_p50_p75_by_channel"])[:, 1]
        candidate_median = np.asarray(candidate_rgb["p25_p50_p75_by_channel"])[:, 1]
        similarity["rgb_distribution"] = {
            "reference": reference_rgb,
            "candidate": candidate_rgb,
            "absolute_median_rgb_delta": np.abs(candidate_median - reference_median).round(2).tolist(),
            "interpretation": "descriptive display-color comparison only; not calibrated photometry",
        }
        morphology_comparisons.append(similarity)
        minimum = float(comparison.get("minimum_highpass_correlation", 0))
        if similarity["highpass_correlation"] < minimum:
            errors.append(f"{target['id']} {comparison_id} morphology correlation {similarity['highpass_correlation']:.3f} is below {minimum}")
        max_offset = int(comparison.get("maximum_abs_shift_pixels", similarity["max_search_shift_pixels"]))
        if max(abs(value) for value in similarity["shift_pixels"]) > max_offset:
            errors.append(f"{target['id']} {comparison_id} morphology offset {similarity['shift_pixels']} exceeds {max_offset} comparison pixels")
    if target.get("review_plate"):
        check_file(root, target["review_plate"], f"{target['id']} review plate", errors)
    for relpath in target.get("additional_review_plates", []):
        check_file(root, relpath, f"{target['id']} additional review plate", errors)
    reference = target.get("official_reference")
    if reference and not reference.startswith("http"):
        if check_file(root, reference, f"{target['id']} independent reference", errors):
            ref_path = root / "parent-pwa" / reference
            try:
                ref_summary = image_summary(ref_path)
                if ref_summary["unique_colors_sampled"] < 24 or ref_summary["nonblack_fraction"] < 0.03:
                    errors.append(f"{target['id']}: independent reference image has too little visible signal: {ref_summary}")
            except Exception as exc:
                errors.append(f"{target['id']}: could not decode official reference {reference}: {exc}")
    else:
        ref_summary = None

    return {
        "id": target["id"],
        "name": target["name"],
        "observation_metadata_files": len(observations),
        "filters": {meta.get("id", meta.get("mission", "observation")): sorted(meta.get("filters", {})) for meta in observations},
        "rendered_image_content": rendered_summaries,
        "registered_morphology_comparisons": morphology_comparisons,
        "aligned_filter_layer_count": len(layer_summaries),
        "official_reference_content": ref_summary,
        "expected_center_icrs_deg": center,
        "expected_field_arcsec": field,
        "expected_dimensions": expected_dims,
        "wcs_alignment_checks": wcs_checks,
        "checks": target.get("checks", []),
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
    }, errors


def validate_imported(root: Path, expectations: list[dict] | None = None) -> tuple[dict, list[str]]:
    """Check dynamically imported MAST renders as well as bundled targets."""
    errors: list[str] = []
    index_path = root / "parent-pwa/observations/imported/index.json"
    if not index_path.is_file():
        return {"status": "PASS", "observation_count": 0, "observations": []}, errors
    index = read_json(index_path)
    observations = []
    entries_by_id = {item.get("id"): item for item in index.get("observations", [])}
    for item in index.get("observations", []):
        image_rel = item.get("image")
        metadata_rel = item.get("metadata")
        summary = {"id": item.get("id"), "label": item.get("label"), "render_mode": item.get("render_mode", "single-filter-grayscale")}
        for relpath, description in ((image_rel, "image"), (metadata_rel, "metadata")):
            if not relpath or not check_file(root, f"{relpath}", f"imported {summary['id']} {description}", errors):
                continue
        if not image_rel or not metadata_rel:
            continue
        image_path = root / "parent-pwa" / image_rel
        metadata_path = root / "parent-pwa" / metadata_rel
        if not image_path.is_file() or not metadata_path.is_file():
            continue
        try:
            meta = read_json(metadata_path)
            content = image_summary(image_path)
            summary.update({"dimensions": content["dimensions"], "nonblack_fraction": content["nonblack_fraction"], "unique_colors_sampled": content["unique_colors_sampled"], "valid_coverage_fraction": item.get("valid_coverage_fraction"), "rendered_image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest()})
            if meta.get("id") != item.get("id") or meta.get("image") != image_rel:
                errors.append(f"Imported observation {item.get('id')} index and metadata disagree")
            if meta.get("render_mode", "single-filter-grayscale") != summary["render_mode"]:
                errors.append(f"Imported observation {item.get('id')} render mode differs between index and metadata")
            reproduction = meta.get("reproduction")
            if reproduction:
                for path_key, hash_key, label in (("manifest_path", "manifest_sha256", "manifest"), ("renderer_path", "renderer_sha256", "renderer")):
                    source_path = root / Path(reproduction.get(path_key, ""))
                    expected_hash = reproduction.get(hash_key, "")
                    if not source_path.is_file():
                        errors.append(f"Imported observation {item.get('id')} reproduction {label} is missing: {source_path}")
                    elif hashlib.sha256(source_path.read_bytes()).hexdigest() != expected_hash:
                        errors.append(f"Imported observation {item.get('id')} reproduction {label} hash does not match")
                source_products = meta.get("source_products", [])
                source_uris = meta.get("source_product_uris", [])
                if len(source_products) != len(source_uris) or [source.get("product_uri") for source in source_products] != source_uris:
                    errors.append(f"Imported observation {item.get('id')} source product inventory does not match its URI list")
                for source in source_products:
                    if source.get("science_data_offset_bytes") is None or not source.get("science_wcs") or not source.get("science_cutout_xyxy"):
                        errors.append(f"Imported observation {item.get('id')} source {source.get('product_uri')} lacks SCI extraction provenance")
                    if source.get("weight_map_used") and source.get("weight_data_offset_bytes") is None:
                        errors.append(f"Imported observation {item.get('id')} source {source.get('product_uri')} lacks WHT extraction provenance")
                    if source.get("error_map_used") and (source.get("error_data_offset_bytes") is None or not source.get("error_cutout_xyxy")):
                        errors.append(f"Imported observation {item.get('id')} source {source.get('product_uri')} lacks ERR extraction provenance")
                    if source.get("dq_do_not_use_mask_applied") and (source.get("dq_data_offset_bytes") is None or not source.get("dq_cutout_xyxy") or source.get("dq_mask_flags", {}).get("DO_NOT_USE") != 1):
                        errors.append(f"Imported observation {item.get('id')} source {source.get('product_uri')} lacks DQ-mask extraction provenance")
                if reproduction.get("output_dimensions") != meta.get("output_dimensions"):
                    errors.append(f"Imported observation {item.get('id')} reproduction dimensions differ from metadata")
            if not 0 <= float(item.get("valid_coverage_fraction", -1)) <= 1:
                errors.append(f"Imported observation {item.get('id')} has invalid coverage fraction")
            if content["nonblack_fraction"] < 0.001 or content["unique_colors_sampled"] < 4:
                errors.append(f"Imported observation {item.get('id')} contains too little image signal: {content}")
            if summary["render_mode"] == "rgb-composite" and not meta.get("channels"):
                errors.append(f"Imported RGB observation {item.get('id')} lacks channel provenance")
            if summary["render_mode"] == "hubble-ir-two-band":
                channels = {channel.get("filter"): channel for channel in meta.get("channels", [])}
                if set(channels) != {"F110W", "F160W"}:
                    errors.append(f"Imported Hubble IR observation {item.get('id')} must record F110W and F160W")
                for band, color in (("F110W", "blue"), ("F160W", "yellow")):
                    channel = channels.get(band, {})
                    if channel.get("display_color") != color or not channel.get("product_uris"):
                        errors.append(f"Imported Hubble IR observation {item.get('id')} lacks {band} display or source provenance")
                    if channel.get("instrument") != "WFC3/IR":
                        errors.append(f"Imported Hubble IR observation {item.get('id')} {band} channel is not WFC3/IR")
        except Exception as exc:
            errors.append(f"Could not validate imported observation {item.get('id')}: {exc}")
        observations.append(summary)
    expectation_results = []
    for expected in expectations or []:
        item = entries_by_id.get(expected["id"])
        result = {"id": expected["id"], "status": "PASS", "errors": []}
        if item is None:
            result["errors"].append(f"Expected imported observation {expected['id']} is missing")
        else:
            metadata_path = root / "parent-pwa" / item["metadata"]
            meta = read_json(metadata_path) if metadata_path.is_file() else {}
            for key in ("render_mode", "field_arcsec", "field_height_arcsec", "position_angle_deg", "output_dimensions"):
                if key in expected:
                    actual = meta.get(key) if key != "render_mode" else item.get(key)
                    if isinstance(expected[key], (int, float)):
                        ok = actual is not None and close(actual, expected[key], 1e-4)
                    else:
                        ok = actual == expected[key]
                    if not ok:
                        result["errors"].append(f"{expected['id']} {key}={actual!r} != expected {expected[key]!r}")
            if "expected_center_icrs_deg" in expected:
                actual = item.get("center_icrs_deg")
                if not actual or any(not close(a, b, 1e-6) for a, b in zip(actual, expected["expected_center_icrs_deg"])):
                    result["errors"].append(f"{expected['id']} center {actual!r} != expected {expected['expected_center_icrs_deg']!r}")
            minimum = expected.get("min_valid_coverage_fraction")
            if minimum is not None and float(item.get("valid_coverage_fraction", -1)) < minimum:
                result["errors"].append(f"{expected['id']} coverage {item.get('valid_coverage_fraction')} is below {minimum}")
            expected_channels = expected.get("channels", {})
            actual_channels = {channel.get("filter"): channel for channel in meta.get("channels", [])}
            for band, channel_expectation in expected_channels.items():
                actual = actual_channels.get(band, {})
                if actual.get("display_color") != channel_expectation.get("display_color"):
                    result["errors"].append(f"{expected['id']} {band} display color is {actual.get('display_color')!r}")
                if len(actual.get("product_uris", [])) != channel_expectation.get("product_count"):
                    result["errors"].append(f"{expected['id']} {band} product count is {len(actual.get('product_uris', []))}")
                if "display_gain" in channel_expectation and actual.get("display_gain") != channel_expectation["display_gain"]:
                    result["errors"].append(f"{expected['id']} {band} display gains {actual.get('display_gain')!r} != expected {channel_expectation['display_gain']!r}")
                if "display_gamma" in channel_expectation and actual.get("display_gamma") != channel_expectation["display_gamma"]:
                    result["errors"].append(f"{expected['id']} {band} display gamma {actual.get('display_gamma')!r} != expected {channel_expectation['display_gamma']!r}")
            similarity_expectation = expected.get("morphology_comparison")
            if similarity_expectation and item is not None:
                reference = (root / "parent-pwa" / similarity_expectation["reference"]).resolve()
                image_path = (root / "parent-pwa" / item["image"]).resolve()
                similarity = registered_highpass_similarity(
                    reference,
                    image_path,
                    tuple(similarity_expectation.get("comparison_dimensions", [360, 337])),
                    int(similarity_expectation.get("max_search_shift_pixels", 12)),
                    bool(similarity_expectation.get("flip_reference_horizontally", False)),
                )
                result["morphology_comparison"] = similarity
                if similarity["highpass_correlation"] < float(similarity_expectation.get("minimum_highpass_correlation", 0)):
                    result["errors"].append(f"{expected['id']} morphology correlation {similarity['highpass_correlation']:.3f} is below {similarity_expectation['minimum_highpass_correlation']}")
                max_offset = int(similarity_expectation.get("maximum_abs_shift_pixels", similarity["max_search_shift_pixels"]))
                if max(abs(value) for value in similarity["shift_pixels"]) > max_offset:
                    result["errors"].append(f"{expected['id']} morphology offset {similarity['shift_pixels']} exceeds {max_offset} downsampled pixels")
            for relpath, description in ((expected.get("official_reference"), "official reference"), (expected.get("review_plate"), "review plate")):
                if relpath:
                    path = (root / "parent-pwa" / relpath).resolve()
                    if not path.is_file() or path.stat().st_size == 0:
                        result["errors"].append(f"{expected['id']} {description} missing: {relpath}")
        if result["errors"]:
            errors.extend(result["errors"])
            result["status"] = "FAIL"
        expectation_results.append(result)
    return {"status": "PASS" if not errors else "FAIL", "observation_count": len(observations), "observations": observations, "expectation_results": expectation_results}, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--report", type=Path, help="Write JSON report to this path")
    args = parser.parse_args()
    root = args.manifest.resolve().parents[2]
    manifest = read_json(args.manifest)
    results, all_errors = [], []
    for target in manifest["targets"]:
        result, errors = validate_target(target, root)
        results.append(result)
        all_errors.extend(errors)
    imported, imported_errors = validate_imported(root, manifest.get("imported_observation_expectations", []))
    all_errors.extend(imported_errors)
    report = {
        "schema": "astrarium-observation-validation-report-v1",
        "manifest": str(args.manifest),
        "status": "PASS" if not all_errors else "FAIL",
        "targets": results,
        "imported_observations": imported,
        "errors": all_errors,
        "scope_note": "Structural, provenance, and registered high-pass morphology checks. Color, depth, and final appearance still require human review against the official references.",
    }
    output = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output)
    print(output, end="")
    return 0 if not all_errors else 1


if __name__ == "__main__":
    sys.exit(main())
