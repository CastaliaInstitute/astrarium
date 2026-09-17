#!/usr/bin/env python3
"""Pack harvested Gaia CSVs into the Astrarium tile catalog (final schema).

Output layout (atlas-projector/astrarium-stars/):
  LK/
    space.bin        3D records (12 B) sorted by octree Morton key (depth 8, ±8192 pc, 64 pc cells)
    space_index.bin  (u64 morton, u32 byteOffset, u32 count)
    shell.bin        2D-shell records (8 B) sorted by sky-zone key (4096 RA x 2048 Dec)
    shell_index.bin  (u64 zoneKey, u32 byteOffset, u32 count)
    sky.bin          bright levels only: space.bin records RE-SORTED by sky zone (dup, small)
    sky_index.bin    (u64 zoneKey, u32 byteOffset, u32 count) into sky.bin
  manifest.json

3D record   (12 B): in-cell xyz 3xu16 | mag u16 (G*100) | col u8 (BP-RP*50+128; 128 if null)
                    | pmra s8 (*0.2 mas/yr, clamp) | pmdec s8 | flags u8
                    flags: bit0 has_bp_rp, bit1 pm_clamped, bit2 parallax quality flag
2D record    (8 B): in-zone ra u16 | dec u16 | mag u16 | col u8 | flags u8
"""
import glob
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "data", "gaia")
DST = os.path.join(HERE, "..", "astrarium-stars")

PC_BOX = 8192
OCT_DEPTH = 8
RA_BINS = 4096
DEC_BINS = 2048
BRIGHT_LEVELS = ("L0", "L1", "L2", "L3")

BAND_LEVEL = {
    (0.0, 8.0): "L0", (8.0, 10.0): "L1",
    (10.0, 12.0): "L2", (12.0, 13.0): "L2",
    (13.0, 14.0): "L3", (14.0, 15.0): "L4", (15.0, 16.0): "L5",
    (16.0, 17.0): "L6", (17.0, 18.0): "L7", (18.0, 19.0): "L8",
    (19.0, 20.0): "L9", (20.0, 21.0): "L10", (21.0, 22.5): "L11",
}
BANDS = sorted(BAND_LEVEL)


def load_band(mag_lo, mag_hi):
    chunks = []
    for f in glob.glob(os.path.join(SRC, f"g{mag_lo:g}-{mag_hi:g}_ra*.csv")):
        try:
            a = np.genfromtxt(f, delimiter=",", names=True)
        except Exception:
            continue
        a = np.atleast_1d(a)
        if a.size == 0 or "ra" not in a.dtype.names:
            continue
        chunks.append(np.stack([np.nan_to_num(a["ra"], nan=0.0),
                                np.nan_to_num(a["dec"], nan=0.0),
                                np.nan_to_num(a["parallax"], nan=0.0),
                                np.nan_to_num(a["pmra"], nan=0.0),
                                np.nan_to_num(a["pmdec"], nan=0.0),
                                np.nan_to_num(a["phot_g_mean_mag"], nan=0.0),
                                np.nan_to_num(a["bp_rp"], nan=-999.0)], axis=1))
    if not chunks:
        return None
    return np.concatenate(chunks)


def sph_to_xyz(ra_deg, dec_deg, dist_pc):
    ra = np.radians(ra_deg)
    dec = np.radians(dec_deg)
    return np.stack([dist_pc * np.cos(dec) * np.cos(ra),
                     dist_pc * np.cos(dec) * np.sin(ra),
                     dist_pc * np.sin(dec)], axis=1)


def morton_encode(x, y, z):
    def spread(v):
        v = v.astype(np.uint64)
        v = (v | (v << np.uint64(8))) & np.uint64(0x00FF00FF)
        v = (v | (v << np.uint64(4))) & np.uint64(0x0F0F0F0F)
        v = (v | (v << np.uint64(2))) & np.uint64(0x33333333)
        v = (v | (v << np.uint64(1))) & np.uint64(0x55555555)
        return v
    return (spread(x) | (spread(y) << np.uint64(1)) | (spread(z) << np.uint64(2)))


def zone_key(ra_deg, dec_deg):
    rb = np.clip((ra_deg % 360.0) / 360.0 * RA_BINS, 0, RA_BINS - 1).astype(np.uint64)
    db = np.clip((dec_deg + 90.0) / 180.0 * DEC_BINS, 0, DEC_BINS - 1).astype(np.uint64)
    return (rb << 11) | db


def runs(sorted_keys):
    starts = np.flatnonzero(np.r_[True, sorted_keys[1:] != sorted_keys[:-1]])
    counts = np.diff(np.r_[starts, len(sorted_keys)])
    return starts, counts


def write_index(path, unique_keys, byte_starts, counts):
    n = len(unique_keys)
    idx = np.empty((n, 16), dtype=np.uint8)
    idx[:, 0:8] = unique_keys.astype(np.uint64)[:, None].view(np.uint8)
    idx[:, 8:12] = byte_starts.astype(np.uint32)[:, None].view(np.uint8)
    idx[:, 12:16] = counts.astype(np.uint32)[:, None].view(np.uint8)
    idx.tofile(path)


def pack_band_3d(ra, dec, plx, pmra, pmdec, g, bprp):
    """Returns (records n×12 u8, morton keys n u64, zone keys n u64)."""
    dist = 1000.0 / np.clip(plx, 1e-3, None)
    xyz = sph_to_xyz(ra, dec, dist)
    scale = np.float64((1 << OCT_DEPTH) - 1) / (2.0 * PC_BOX)
    cx = np.clip(((xyz[:, 0] + PC_BOX) * scale).astype(np.int64), 0, (1 << OCT_DEPTH) - 1)
    cy = np.clip(((xyz[:, 1] + PC_BOX) * scale).astype(np.int64), 0, (1 << OCT_DEPTH) - 1)
    cz = np.clip(((xyz[:, 2] + PC_BOX) * scale).astype(np.int64), 0, (1 << OCT_DEPTH) - 1)
    key = morton_encode(cx, cy, cz)
    order = np.argsort(key, kind="stable")
    key_s = key[order]

    cell_edge = 2.0 * PC_BOX / (1 << OCT_DEPTH)
    cell_lo = -PC_BOX + np.stack([cx, cy, cz], axis=1) * cell_edge
    fx = np.clip(((xyz - cell_lo) / cell_edge * 65535.0), 0, 65535).astype(np.uint16)[order]
    mags = np.clip(g * 100.0, 0, 65535).astype(np.uint16)[order]
    hasbprp = bprp > -900
    col = np.clip(np.where(hasbprp, bprp, 0.0) * 50.0 + 128.0, 0, 255).astype(np.uint8)[order]
    pmx = np.clip(np.rint(pmra / 0.2), -128, 127).astype(np.int8)
    pmy = np.clip(np.rint(pmdec / 0.2), -128, 127).astype(np.int8)
    pm_clamped = (np.abs(pmra / 0.2) > 127) | (np.abs(pmdec / 0.2) > 127)
    plx_bad = plx < 1.0
    flags = (hasbprp[order].astype(np.uint8)
             | (pm_clamped[order].astype(np.uint8) << 1)
             | (plx_bad[order].astype(np.uint8) << 2))

    n = len(g)
    out = np.empty((n, 12), dtype=np.uint8)
    out[:, 0:2] = fx[:, 0:1].view(np.uint8)
    out[:, 2:4] = fx[:, 1:2].view(np.uint8)
    out[:, 4:6] = fx[:, 2:3].view(np.uint8)
    out[:, 6:8] = mags[:, None].view(np.uint8)
    out[:, 8] = col
    out[:, 9] = pmx[order].view(np.uint8)
    out[:, 10] = pmy[order].view(np.uint8)
    out[:, 11] = flags
    return out, key_s, zone_key(ra, dec)[order]


def pack_band_2d(ra, dec, g, bprp):
    """Returns (records n×8 u8, zone keys n u64)."""
    zk = zone_key(ra, dec)
    order = np.argsort(zk, kind="stable")
    zk_s = zk[order]
    cell_edge_ra = 360.0 / RA_BINS
    cell_edge_dec = 180.0 / DEC_BINS
    rb = (zk // 2048).astype(np.int64)
    db = (zk % 2048).astype(np.int64)
    fu = np.clip((ra - rb * cell_edge_ra) / cell_edge_ra * 65535.0, 0, 65535).astype(np.uint16)
    fv = np.clip((dec - (-90.0 + db * cell_edge_dec)) / cell_edge_dec * 65535.0, 0, 65535).astype(np.uint16)
    mags = np.clip(g * 100.0, 0, 65535).astype(np.uint16)
    hasbprp = bprp > -900
    col = np.clip(np.where(hasbprp, bprp, 0.0) * 50.0 + 128.0, 0, 255).astype(np.uint8)

    n = len(g)
    out = np.empty((n, 8), dtype=np.uint8)
    out[:, 0:2] = fu[order][:, None].view(np.uint8)
    out[:, 2:4] = fv[order][:, None].view(np.uint8)
    out[:, 4:6] = mags[order][:, None].view(np.uint8)
    out[:, 6] = col[order]
    out[:, 7] = hasbprp[order].astype(np.uint8)
    return out, zk_s


def pack():
    os.makedirs(DST, exist_ok=True)
    manifest = {"record_bytes": {"3d": 12, "2d": 8}, "pc_box": PC_BOX,
                "oct_depth": OCT_DEPTH, "ra_bins": RA_BINS, "dec_bins": DEC_BINS,
                "levels": {}}
    buf3 = {}
    buf2 = {}

    for band in BANDS:
        lvl = BAND_LEVEL[band]
        data = load_band(*band)
        if data is None:
            print(f"{lvl} band {band}: no CSVs yet, skipped", flush=True)
            continue
        ra, dec, plx, pmra, pmdec, g, bprp = (data[:, 0], data[:, 1], data[:, 2],
                                              data[:, 3], data[:, 4], data[:, 5], data[:, 6])
        has3d = plx > 0
        if has3d.any():
            o3, k3, z3 = pack_band_3d(ra[has3d], dec[has3d], plx[has3d], pmra[has3d],
                                      pmdec[has3d], g[has3d], bprp[has3d])
            buf3.setdefault(lvl, []).append((o3, k3, z3))
            print(f"{lvl} band {band}: {len(o3):,} x 3D", flush=True)
        if (~has3d).any():
            o2, k2 = pack_band_2d(ra[~has3d], dec[~has3d], g[~has3d], bprp[~has3d])
            buf2.setdefault(lvl, []).append((o2, k2))
            print(f"{lvl} band {band}: {len(o2):,} x 2D", flush=True)

    for lvl in sorted(set(buf3) | set(buf2)):
        ldir = os.path.join(DST, lvl)
        os.makedirs(ldir, exist_ok=True)
        info = {}
        if lvl in buf3:
            recs = np.concatenate([b[0] for b in buf3[lvl]])
            keys = np.concatenate([b[1] for b in buf3[lvl]])
            zkeys = np.concatenate([b[2] for b in buf3[lvl]])
            order = np.argsort(keys, kind="stable")
            recs = recs[order]
            keys = keys[order]
            recs.tofile(os.path.join(ldir, "space.bin"))
            starts, counts = runs(keys)
            write_index(os.path.join(ldir, "space_index.bin"), keys[starts], starts * 12, counts)
            info["stars3d"] = int(len(recs))
            info["cells3d"] = int(len(starts))
            print(f"{lvl}: {info['stars3d']:,} x 3D, {info['cells3d']:,} cells", flush=True)
            if lvl in BRIGHT_LEVELS:
                so = np.argsort(zkeys, kind="stable")
                recs[so].tofile(os.path.join(ldir, "sky.bin"))
                zs, zc = runs(zkeys[so])
                write_index(os.path.join(ldir, "sky_index.bin"), zkeys[so][zs], zs * 12, zc)
                info["sky_rows"] = int(len(zs))
        if lvl in buf2:
            recs = np.concatenate([b[0] for b in buf2[lvl]])
            keys = np.concatenate([b[1] for b in buf2[lvl]])
            order = np.argsort(keys, kind="stable")
            recs = recs[order]
            keys = keys[order]
            recs.tofile(os.path.join(ldir, "shell.bin"))
            starts, counts = runs(keys)
            write_index(os.path.join(ldir, "shell_index.bin"), keys[starts], starts * 8, counts)
            info["stars2d"] = int(len(recs))
            info["cells2d"] = int(len(starts))
            print(f"{lvl}: {info['stars2d']:,} x 2D, {info['cells2d']:,} cells", flush=True)
        manifest["levels"][lvl] = info

    with open(os.path.join(DST, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    t3 = sum(v.get("stars3d", 0) for v in manifest["levels"].values())
    t2 = sum(v.get("stars2d", 0) for v in manifest["levels"].values())
    print(f"TOTAL {t3:,} x 3D + {t2:,} x 2D -> {DST}", flush=True)


if __name__ == "__main__":
    pack()
