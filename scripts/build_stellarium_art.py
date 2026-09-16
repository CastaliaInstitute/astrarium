import json
import math
import os
import subprocess
import urllib.request

BASE = "https://raw.githubusercontent.com/Stellarium/stellarium/v0.20.4/skycultures/western"
FAB = "/tmp/constellationsart.fab"
STARS6 = os.path.join(os.path.dirname(__file__), "..", "player", "app", "src", "main", "assets", "sky", "stars.json")
OUT_ASSETS = os.path.join(os.path.dirname(__file__), "..", "player", "app", "src", "main", "assets", "sky")
ART_DIR = os.path.join(OUT_ASSETS, "art")
MAX_W = 1280


def fetch(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "atlas"})
    with urllib.request.urlopen(req) as r, open(path, "wb") as f:
        f.write(r.read())


def img_size(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    w, h = out.split(",")
    return int(w), int(h)


def ensure_alpha(path):
    import numpy as np
    from PIL import Image
    im = Image.open(path)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        return
    arr = np.asarray(im.convert("RGB"))
    alpha = arr.max(axis=2).astype(np.uint8)
    Image.fromarray(np.dstack([arr, alpha]), "RGBA").save(path)


def main():
    src = json.load(open("/tmp/stars6.json"))
    hip = {f["id"]: f["geometry"]["coordinates"] for f in src["features"] if f.get("geometry") and f.get("id") is not None}
    print("HIP entries in source:", len(hip))
    labels = json.load(open("/tmp/constellations.json"))
    names = {f["id"]: f["properties"].get("name", "") for f in labels["features"] if f.get("id")}

    os.makedirs(ART_DIR, exist_ok=True)
    art = []
    missing = 0
    for line in open(FAB):
        parts = line.split()
        if len(parts) < 7 or parts[0].startswith("#"):
            continue
        cid, image = parts[0], parts[1]
        raw_path = os.path.join("/tmp", "art_" + image)
        out_path = os.path.join(ART_DIR, image)
        if not os.path.exists(out_path):
            try:
                fetch(f"{BASE}/{image}", raw_path)
                w, h = img_size(raw_path)
                if w > MAX_W:
                    nh = int(h * MAX_W / w)
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw_path,
                                    "-vf", f"scale={MAX_W}:{nh}", out_path], check=True)
                else:
                    subprocess.run(["cp", raw_path, out_path], check=True)
            except Exception as e:
                print("download failed", image, e)
                continue
        w, h = img_size(out_path)
        ensure_alpha(out_path)
        vals = parts[2:]
        pts = []
        out_h = int(h * MAX_W / w) if w > MAX_W else h
        out_w = min(w, MAX_W)
        sx = out_w / w
        sy = out_h / h
        for i in range(0, len(vals) - 2, 3):
            u = float(vals[i])
            v = float(vals[i + 1])
            hp = int(vals[i + 2])
            if hp not in hip:
                missing += 1
                continue
            ra, dec = hip[hp]
            pts.append([round(ra, 3), round(dec, 3), round(u * sx, 2), round(v * sy, 2)])
        if len(pts) >= 2:
            art.append({"id": cid, "name": names.get(cid, ""), "image": image, "w": out_w, "h": out_h, "pts": pts})

    with open(os.path.join(OUT_ASSETS, "art.json"), "w") as fh:
        json.dump(art, fh, separators=(",", ":"))
    total = sum(os.path.getsize(os.path.join(ART_DIR, f)) for f in os.listdir(ART_DIR))
    print(f"art.json: {len(art)} constellations, {missing} stars unmapped, art total {total // 1024} KB")


if __name__ == "__main__":
    main()
