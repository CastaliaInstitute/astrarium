#!/usr/bin/env python3
"""Harvest the complete Gaia DR3 source catalog (1.812B) into CSV chunks.

Final schema for the Astrarium pipeline: ra, dec, parallax, pmra, pmdec,
phot_g_mean_mag, bp_rp. Position-only sources (no parallax) included — they
become 2D-shell records downstream. Parallel resumable async-TAP jobs,
partitioned by magnitude band x RA slice x Dec band.

Usage: python3 gaia_harvest.py [--workers 6]
"""
import concurrent.futures as cf
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "gaia")
TAP = "https://gea.esac.esa.int/tap-server/tap"
COLS = "ra,dec,parallax,pmra,pmdec,phot_g_mean_mag,bp_rp"
G_MAX = 22.5
MAG_BANDS = [(0.0, 8.0), (8.0, 10.0), (10.0, 12.0), (12.0, 13.0), (13.0, 14.0),
             (14.0, 15.0), (15.0, 16.0), (16.0, 17.0), (17.0, 18.0), (18.0, 19.0),
             (19.0, 20.0), (20.0, 21.0), (21.0, G_MAX)]
RA_STEPS = 12
DEC_BANDS = [(-90.0, -30.0), (-30.0, 30.0), (30.0, 90.0)]


def job_name(mag_lo, mag_hi, ra_lo, ra_hi, dec_lo, dec_hi):
    return f"g{mag_lo:g}-{mag_hi:g}_ra{ra_lo:g}-{ra_hi:g}_dec{dec_lo:g}-{dec_hi:g}.csv"


def run_job(mag_lo, mag_hi, ra_lo, ra_hi, dec_lo, dec_hi):
    name = job_name(mag_lo, mag_hi, ra_lo, ra_hi, dec_lo, dec_hi)
    path = os.path.join(OUT, name)
    if os.path.exists(path) and os.path.getsize(path) > 100:
        return name, "cached"
    dec_hi = min(dec_hi, 89.999999)
    adql = (f"SELECT {COLS} FROM gaiadr3.gaia_source WHERE "
            f"phot_g_mean_mag IS NOT NULL AND phot_g_mean_mag >= {mag_lo} AND phot_g_mean_mag < {mag_hi} "
            f"AND ra >= {ra_lo} AND ra < {ra_hi} AND dec >= {dec_lo} AND dec < {dec_hi}")
    data = urllib.parse.urlencode({
        "REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "METHOD": "ASYNCHRONOUS",
        "QUERY": adql}).encode()
    for attempt in range(6):
        try:
            req = urllib.request.Request(f"{TAP}/async", data=data, method="POST")
            with urllib.request.urlopen(req, timeout=120) as r:
                loc = r.headers.get("Location")
                if loc:
                    job_url = loc
                else:
                    body = r.read().decode()
                    m = re.search(r"<uws:jobId><!\[CDATA\[([^\]]+)\]\]></uws:jobId>", body) or \
                        re.search(r"<uws:jobId>([^<]+)</uws:jobId>", body)
                    if not m:
                        raise RuntimeError("no jobId in response")
                    job_url = f"{TAP}/async/{m.group(1).strip()}"
            urllib.request.urlopen(urllib.request.Request(
                job_url + "/phase", data=b"PHASE=RUN",
                headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=60)
            t0 = time.time()
            while time.time() - t0 < 7200:
                with urllib.request.urlopen(job_url + "/phase", timeout=60) as r:
                    phase = r.read().decode().strip()
                if phase == "COMPLETED":
                    with urllib.request.urlopen(job_url + "/results/result", timeout=1800) as r:
                        with open(path + ".tmp", "wb") as fh:
                            while True:
                                chunk = r.read(1 << 20)
                                if not chunk:
                                    break
                                fh.write(chunk)
                    os.replace(path + ".tmp", path)
                    return name, f"{os.path.getsize(path)//1_000_000} MB"
                if phase in ("ERROR", "ABORTED"):
                    raise RuntimeError(f"job {phase}")
                time.sleep(15 if time.time() - t0 < 300 else 60)
            raise RuntimeError("timeout")
        except Exception as e:
            if attempt == 5:
                return name, f"FAILED: {e}"
            time.sleep(30 * (attempt + 1))
    return name, "FAILED"


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
    os.makedirs(OUT, exist_ok=True)
    jobs = []
    for mag_lo, mag_hi in MAG_BANDS:
        for i in range(RA_STEPS):
            for dec_lo, dec_hi in DEC_BANDS:
                jobs.append((mag_lo, mag_hi, i * 360.0 / RA_STEPS, (i + 1) * 360.0 / RA_STEPS,
                             dec_lo, dec_hi))
    print(f"{len(jobs)} jobs, {workers} workers -> {OUT}", flush=True)
    done = failed = 0
    with cf.ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(run_job, *j): j for j in jobs}
        for fut in cf.as_completed(futs):
            name, status = fut.result()
            done += 1
            if status.startswith("FAILED"):
                failed += 1
                print(f"[{done}/{len(jobs)}] {name}: {status}", flush=True)
            elif done % 10 == 0 or status == "cached":
                print(f"[{done}/{len(jobs)}] {name}: {status}", flush=True)
    print(f"DONE jobs={done} failed={failed}", flush=True)


if __name__ == "__main__":
    main()
