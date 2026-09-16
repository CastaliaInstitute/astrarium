import os
import urllib.request

SATS = [(25544, "ISS (ZARYA)"), (48274, "CSS (TIANGONG)"), (20580, "HST")]
OUT = os.path.join(os.path.dirname(__file__), "..", "player", "app", "src", "main", "assets", "sky", "satellites.tle")

with open(OUT, "w") as f:
    for norad, _ in SATS:
        url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad}&FORMAT=TLE"
        with urllib.request.urlopen(url, timeout=30) as r:
            text = r.read().decode().strip()
        if text:
            f.write(text + "\n")
            print("fetched:", text.splitlines()[0])
        else:
            print("empty response for", norad)
