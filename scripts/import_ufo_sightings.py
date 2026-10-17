#!/usr/bin/env python3
"""Normalize a licensed, bearing-capable sighting CSV into Astrarium JSON.

This tool intentionally does not fetch or scrape source websites. The operator
must attest that redistribution is permitted and supply the source's rights
statement for provenance. It preserves missing angular precision as null and
never derives azimuth/elevation from narrative or city-level coordinates.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


def number(row: dict[str, str], field: str, line: int) -> float | None:
    raw = (row.get(field) or "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"CSV line {line}: {field} must be numeric") from exc
    if not math.isfinite(value):
        raise ValueError(f"CSV line {line}: {field} must be finite")
    return value


def timestamp_utc(raw: str, line: int) -> str:
    text = raw.strip()
    if not text:
        raise ValueError(f"CSV line {line}: observedAtUtc is required")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"CSV line {line}: observedAtUtc must be ISO 8601 with a timezone") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"CSV line {line}: observedAtUtc must include Z or a UTC offset")
    parsed = parsed.astimezone(timezone.utc)
    return parsed.isoformat(timespec="auto").replace("+00:00", "Z")


def normalize(row: dict[str, str], line: int, args: argparse.Namespace) -> dict:
    record_id = (row.get("id") or "").strip()
    if not record_id:
        raise ValueError(f"CSV line {line}: id is required")
    lat = number(row, "latitudeDeg", line)
    lon = number(row, "longitudeDeg", line)
    if lat is None or lon is None or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError(f"CSV line {line}: valid latitudeDeg and longitudeDeg are required")
    az = number(row, "azimuthDeg", line)
    el = number(row, "elevationDeg", line)
    if (az is None) != (el is None):
        raise ValueError(f"CSV line {line}: azimuthDeg and elevationDeg must both be present or both blank")
    if az is not None:
        if not 0 <= az < 360 or not -90 <= el <= 90:
            raise ValueError(f"CSV line {line}: azimuthDeg must be [0,360), elevationDeg [-90,90]")
    angular = number(row, "angularUncertaintyDeg", line)
    if angular is not None and not 0.01 <= angular <= 90:
        raise ValueError(f"CSV line {line}: angularUncertaintyDeg must be [0.01,90]")
    if angular is not None and az is None:
        raise ValueError(f"CSV line {line}: angularUncertaintyDeg requires a reported direction")
    range_km = number(row, "rangeKm", line)
    range_uncertainty = number(row, "rangeUncertaintyKm", line)
    if range_km is not None and range_km <= 0:
        raise ValueError(f"CSV line {line}: rangeKm must be positive")
    if range_uncertainty is not None and range_uncertainty < 0:
        raise ValueError(f"CSV line {line}: rangeUncertaintyKm cannot be negative")
    if range_uncertainty is not None and range_km is None:
        raise ValueError(f"CSV line {line}: rangeUncertaintyKm requires rangeKm")
    time_uncertainty = number(row, "timeUncertaintySec", line)
    if time_uncertainty is not None and time_uncertainty < 0:
        raise ValueError(f"CSV line {line}: timeUncertaintySec cannot be negative")
    observer_altitude = number(row, "observerAltitudeKm", line)
    if observer_altitude is not None and not 0 <= observer_altitude <= 20:
        raise ValueError(f"CSV line {line}: observerAltitudeKm must be [0,20]")
    return {
        "id": record_id,
        "label": (row.get("label") or "").strip() or f"Reported observation {record_id}",
        "source": args.source,
        "sourceUrl": args.source_url,
        "sourceRights": args.source_rights,
        "redistributionPermitted": True,
        "observedAtUtc": timestamp_utc(row.get("observedAtUtc") or "", line),
        "timeUncertaintySec": time_uncertainty,
        "latitudeDeg": lat,
        "longitudeDeg": lon,
        "observerAltitudeKm": observer_altitude,
        "azimuthDeg": az,
        "elevationDeg": el,
        "angularUncertaintyDeg": angular,
        "rangeKm": range_km,
        "rangeUncertaintyKm": range_uncertainty,
        "eventId": (row.get("eventId") or "").strip() or None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--source", required=True, help="dataset or publisher name")
    parser.add_argument("--source-url", required=True, help="canonical dataset or record URL")
    parser.add_argument("--source-rights", required=True, help="license or written permission reference")
    parser.add_argument("--redistribution-permitted", action="store_true",
                        help="attest that the supplied source rights allow redistribution in Astrarium")
    parser.add_argument("--append", action="store_true", help="append to an existing Astrarium JSON array")
    args = parser.parse_args()
    if not args.redistribution_permitted:
        parser.error("confirm source redistribution rights with --redistribution-permitted")
    if not args.source.strip() or not args.source_rights.strip():
        parser.error("--source and --source-rights must be non-empty")
    if urlparse(args.source_url).scheme not in {"http", "https"}:
        parser.error("--source-url must be an http(s) URL")
    required = {"id", "observedAtUtc", "latitudeDeg", "longitudeDeg"}
    records: list[dict] = []
    try:
        with args.input_csv.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError("missing required CSV columns: " + ", ".join(sorted(missing)))
            for line, row in enumerate(reader, start=2):
                if not any((value or "").strip() for value in row.values()):
                    continue
                records.append(normalize(row, line, args))
        if not records:
            raise ValueError("CSV contains no sighting records")
        existing: list[dict] = []
        if args.append and args.output_json.exists():
            existing = json.loads(args.output_json.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                raise ValueError("append target must be a JSON array")
        ids = [record["id"] for record in existing] + [record["id"] for record in records]
        if len(ids) != len(set(ids)):
            raise ValueError("record IDs must be unique across imported and existing records")
        payload = json.dumps(existing + records, ensure_ascii=False, indent=2) + "\n"
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{args.output_json.name}.", dir=args.output_json.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, args.output_json)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"import failed: {exc}", file=sys.stderr)
        return 2
    bearing_count = sum(record["azimuthDeg"] is not None for record in records)
    range_count = sum(record["rangeKm"] is not None for record in records)
    event_count = len({record["eventId"] for record in records if record["eventId"]})
    print(f"Imported {len(records)} records ({bearing_count} with direction, {range_count} with range, {event_count} event groups).")
    print("No direction, range, or event match was inferred from location or narrative.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
