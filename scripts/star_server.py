#!/usr/bin/env python3
"""Astrarium Atlas star server — serves Gaia catalog tiles to clients.

API (v1):
  GET /api/v1/manifest
  GET /api/v1/tiles/space/{level}/{mortonKey}    -> gzip 3D records (12 B each)
  GET /api/v1/tiles/shell/{level}/{zoneKey}      -> gzip 2D records (8 B each)
  GET /api/v1/tiles/sky/{level}/{zoneKey}        -> gzip sky-ordered 3D records (bright levels)

Levels L0..L11. Keys are decimal or hex (0x...). Missing tile -> 404.
Catalog root: atlas-projector/astrarium-stars (pass as argv[1] to override).
"""
import gzip
import json
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "astrarium-stars")
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8900


class LevelIndex:
    def __init__(self, path):
        self.keys = np.empty(0, dtype=np.uint64)
        self.offsets = np.empty(0, dtype=np.uint32)
        self.counts = np.empty(0, dtype=np.uint32)
        idx_path = os.path.join(path, "space_index.bin")
        if os.path.exists(idx_path):
            raw = np.fromfile(idx_path, dtype=np.uint8).reshape(-1, 16)
            self.keys = raw[:, 0:8].copy().view(np.uint64).ravel()
            self.offsets = raw[:, 8:12].copy().view(np.uint32).ravel()
            self.counts = raw[:, 12:16].copy().view(np.uint32).ravel()
            self.keys = np.sort(self.keys)  # ensure sorted
            order = np.argsort(self.keys)
            self.keys = self.keys[order]
            self.offsets = self.offsets[order]
            self.counts = self.counts[order]

    def lookup(self, key):
        i = np.searchsorted(self.keys, np.uint64(key))
        if i < len(self.keys) and self.keys[i] == np.uint64(key):
            return int(self.offsets[i]), int(self.counts[i])
        return None


class ZoneIndex(LevelIndex):
    def __init__(self, path, index_name):
        self.keys = np.empty(0, dtype=np.uint64)
        self.offsets = np.empty(0, dtype=np.uint32)
        self.counts = np.empty(0, dtype=np.uint32)
        idx_path = os.path.join(path, index_name)
        if os.path.exists(idx_path):
            raw = np.fromfile(idx_path, dtype=np.uint8).reshape(-1, 16)
            self.keys = raw[:, 0:8].copy().view(np.uint64).ravel()
            self.offsets = raw[:, 8:12].copy().view(np.uint32).ravel()
            self.counts = raw[:, 12:16].copy().view(np.uint32).ravel()
            order = np.argsort(self.keys)
            self.keys = self.keys[order]
            self.offsets = self.offsets[order]
            self.counts = self.counts[order]

    def lookup(self, key):
        i = np.searchsorted(self.keys, np.uint64(key))
        if i < len(self.keys) and self.keys[i] == np.uint64(key):
            return int(self.offsets[i]), int(self.counts[i])
        return None


LEVELS = {}
SHELL = {}
SKY = {}
MANIFEST = {}


def load_catalog():
    global MANIFEST
    with open(os.path.join(CATALOG, "manifest.json")) as fh:
        MANIFEST = json.load(fh)
    for lvl in MANIFEST["levels"]:
        d = os.path.join(CATALOG, lvl)
        LEVELS[lvl] = LevelIndex(d)
        SHELL[lvl] = ZoneIndex(d, "shell_index.bin")
        SKY[lvl] = ZoneIndex(d, "sky_index.bin")
    print(f"catalog loaded: {list(MANIFEST['levels'])}", flush=True)


def read_records(level, kind, offset, count):
    fname = {"space": "space.bin", "shell": "shell.bin", "sky": "sky.bin"}[kind]
    rec_bytes = 12 if kind in ("space", "sky") else 8
    with open(os.path.join(CATALOG, level, fname), "rb") as fh:
        fh.seek(offset)
        return fh.read(count * rec_bytes)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path).path.strip("/").split("/")
        try:
            if u[:3] == ["api", "v1", "manifest"] and len(u) == 3:
                self._send(200, json.dumps(MANIFEST).encode())
                return
            if u[:3] == ["api", "v1", "tiles"] and len(u) == 6:
                _, _, _, kind, level, key_s = u
                key = int(key_s, 0)
                if kind == "space":
                    hit = LEVELS.get(level, LevelIndex.__new__(LevelIndex)).lookup(key)
                elif kind == "shell":
                    hit = SHELL.get(level, ZoneIndex.__new__(ZoneIndex)).lookup(key)
                elif kind == "sky":
                    hit = SKY.get(level, ZoneIndex.__new__(ZoneIndex)).lookup(key)
                else:
                    hit = None
                if hit is None:
                    self._send(404, b'{"error":"no such tile"}')
                    return
                off, cnt = hit
                recs = read_records(level, kind, off, cnt)
                gz = gzip.compress(recs, 6)
                self._send(200, gz, "application/octet-stream")
                return
            if u[:2] == ["api", "v1"] and len(u) == 5 and u[2] == "core":
                # core catalog file: /api/v1/core/{level}/{filename}
                level, fname = u[3], u[4]
                if not re.fullmatch(r"L\d+", level) or "/" in fname or ".." in fname \
                        or fname not in ("space.bin", "space_index.bin", "shell.bin", "shell_index.bin", "sky.bin", "sky_index.bin"):
                    self._send(404, b'{"error":"bad core path"}')
                    return
                p = os.path.join(CATALOG, level, fname)
                if not os.path.exists(p):
                    self._send(404, b'{"error":"no such core file"}')
                    return
                with open(p, "rb") as fh:
                    body = fh.read()
                self._send(200, body, "application/octet-stream")
                return
            if u[:2] == ["api", "v1"] and u[2] == "health":
                self._send(200, b'{"ok":true}')
                return
            self._send(404, b'{"error":"not found"}')
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}).encode())


def main():
    load_catalog()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"star server on :{PORT} serving {CATALOG}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
