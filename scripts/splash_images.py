"""iOS startup pictures for the start screen (Vraja Lila 20.10.2026, ДА msg 5520).

One PNG per screen in lib/splash-devices.json, portrait and landscape: white, the CA sign
(Vraja Lila's loader, lib/caSplash.ts, frame 0 = the sign at rest) 200 CSS px in the middle
(V53, Vraja Lila 23.10 msg 6433: 170 px where the screen is narrower than 640 px - the same media rule as SPLASH_CSS) -
drawn by the browser from the same markup as the start screen, so the first frame matches.
Names = lib/splashImages.ts (ios-<px w>x<px h>.png). Run after a change of the sign or the list:
    python scripts/splash_images.py
"""
import json
import os
import re

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "public", "splash")
src = open(os.path.join(ROOT, "lib", "caSplash.ts"), encoding="utf-8").read()
css = re.search(r"export const CA_LOADER_CSS = `(.*?)`;", src, re.S).group(1)
svg = re.search(r"export const CA_LOADER_SVG = `(.*?)`;", src, re.S).group(1)
v53 = re.search(r"(@media \(max-width: 639px\)\{#ap-splash \.ca-loader\{[^}]*\}\})", src).group(1)  # V53: phone 170 px
devices = json.load(open(os.path.join(ROOT, "lib", "splash-devices.json"), encoding="utf-8"))

# The start screen's layer (SPLASH_CSS: fixed, flex-centred, white) with every animation at frame 0.
HTML = f"""<!doctype html><html><head><meta charset="utf-8"><style>{css}
{v53}
html,body{{margin:0;height:100%;background:#fff}}
#ap-splash{{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:#fff}}
*{{animation-play-state:paused!important;animation-delay:0s!important}}
</style></head><body><div id="ap-splash"><div class="ap-splash-sign" style="display:block">{svg}</div></div></body></html>"""

os.makedirs(OUT, exist_ok=True)
keep = set()
with sync_playwright() as p:
    b = p.chromium.launch()
    for d in devices:
        for w, h in ((d["w"], d["h"]), (d["h"], d["w"])):
            name = f"ios-{w * d['dpr']}x{h * d['dpr']}.png"
            keep.add(name)
            pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=d["dpr"])
            pg.set_content(HTML)
            pg.screenshot(path=os.path.join(OUT, name))
            pg.close()
            # white + one red: a 32-colour palette keeps the edges smooth at a third of the size
            im = Image.open(os.path.join(OUT, name)).convert("RGB").quantize(colors=32, method=Image.Quantize.MEDIANCUT)
            im.save(os.path.join(OUT, name), optimize=True)
    b.close()
for f in os.listdir(OUT):
    if f.startswith("ios-") and f not in keep:
        os.remove(os.path.join(OUT, f))
print(f"{len(keep)} pictures -> public/splash/")
