"""V13 — the «16 предметов» picture replaced by Vraja Lila's schematic (Vraja Lila msg 736/738/740, 20.10.2026;
saskarnes īpašnieks, «Стандарты» 0а; nodots-izpildei 20.10 12:33).

Rule text (verbatim): «замена рисунка (сделаешь оптимизацию?)»; criterion (assistant, Vraja's words):
«новая схема в книге без искажения; скриншот». Order (Lipikāra): original unchanged in masters/ (as the
portraits), in the book WebP without distortion, optimisation as the portraits (q58).

Checks
  static: masters/ and public/media PNG = Vraja's file byte for byte (sha1); the app's WebP is encoded from it at
          its own size 1254 × 1254 (no crop / resize); data/hotspots.json w × h = the picture; 18 masks of that size.
  browser (every language on desktop; ru-iast + en on phones), both pages that show the picture
  (worship-sixteen-articles, main-worship-sixteen-items):
    - the figure shows the new WebP (currentSrc), natural size 1254 × 1254;
    - figure box and drawn image keep the picture's proportion 1 : 1 (≤ 0.5 % — # tehniskais slieksnis Lipikāra,
      nav S noteikums) — no stretching; the box ratio comes from the data (aspect-ratio), so the page does not jump;
    - tapping each object 1–18 lights the list row with that number (desktop: all 18; phones: 1, 3, 7, 14, 18).

V20 — highlight masks whole (Vraja Lila msg 5617–5620, 20.10.2026, iPhone screenshots of the live book, objects 1, 2, 3).
Rule text (verbatim): «3 элемента не выделены/вырезаны целиком на пересечении серых линий, а также цифры — при выделении.
Исправь». Criterion (Lipikāra, Vraja's words): the lit object is the whole object, also where the tray's grey lines cross
it, and its printed number is whole.
  static (masks, alpha ≥ 0.5 = lit):
    - crossing points: every pixel listed in CROSSINGS (the drawn line of the object / its number exactly where a tray
      rim crosses it — measured on the picture 20.10.2026) is lit in its own mask and in no other mask;
    - all 18: a drawn black pixel (luminance < 128 — # tehniskais slieksnis Lipikāra, nav S noteikums) enclosed by an
      object's lit outline is lit too (no line inside the object left faded); no drawn pixel is lit in two masks.

usage: python s61_paraphernalia_schema.py <base-url> [--static]   devices: QA_DEVICES
"""
import hashlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from PIL import Image  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
STATIC_ONLY = "--static" in sys.argv
SHA1 = "cf19467b6043b909b1c709f925fded80730e24b5"   # Vraja Lila's PNG (inbox 1792488731998-AgADECAAAnI-uFI.png, 662 288 B)
SIZE = (1254, 1254)
TOL = 0.5          # % — tehniskais slieksnis Lipikāra, nav S noteikums
PAGES = ["worship-sixteen-articles", "main-worship-sixteen-items"]
NUMS = [str(i) for i in range(1, 19)]
PHONE_NUMS = ["1", "3", "7", "14", "18"]
LANGS = [l["code"] for l in json.load(open(os.path.join(qa.REPO, "lib", "languages.json"), encoding="utf-8"))
         if not l.get("replacedBy")]
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else json.dumps(evidence, ensure_ascii=False)}", flush=True)


def static_checks():
    rel = "common/paraphernalia.png"
    for where in ("masters/media", "public/media"):
        p = os.path.join(qa.REPO, *where.split("/"), *rel.split("/"))
        h = hashlib.sha1(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None
        check("static", f"{where}/{rel} = Vraja Lila's original, unchanged (sha1)", h == SHA1, h)
    webp = json.load(open(os.path.join(qa.REPO, "lib", "webp-images.json"), encoding="utf-8")).get(rel)
    size = None
    if webp:
        with Image.open(os.path.join(qa.REPO, "public", "media", *webp.split("/"))) as im:
            size, fmt = im.size, im.format
    check("static", f"app WebP ({webp}) encoded at the picture's own size {SIZE[0]}×{SIZE[1]}", size == SIZE and fmt == "WEBP",
          {"webp": webp, "size": size})
    hs = json.load(open(os.path.join(qa.DATA, "hotspots.json"), encoding="utf-8"))[rel]
    check("static", "hotspots.json w × h = the picture", (hs["w"], hs["h"]) == SIZE, [hs["w"], hs["h"]])
    bad = []
    for n in NUMS:
        m = hs["spots"].get(n, {}).get("mask")
        p = os.path.join(qa.REPO, "public", "media", "hotspots", *(m or "-").split("/"))
        if not m or not os.path.exists(p) or Image.open(p).size != SIZE:
            bad.append(n)
    check("static", "18 object masks, each of the picture's size", not bad, bad)
    if not bad:
        mask_checks(hs)
    return webp


# (number, x, y, what) — pixels of the drawing where a grey tray rim crosses the object or its number
# (picture coordinates, 1254 × 1254; Vraja Lila msg 5617–5620: 1, 2, 3 cut at the crossings, numbers too).
CROSSINGS = [
    ("1", 467, 974, "spoon, upper end beside the bell's saucer"),
    ("1", 437, 1048, "cup bottom on the inner rim"),
    ("2", 503, 935, "shell top left, under the inner rim"),
    ("2", 543, 941, "shell top, under the inner rim"),
    ("2", 587, 944, "spout tip, under the inner rim"),
    ("2", 582, 955, "spout underside"),
    ("2", 576, 1012, "right foot of the stand"),
    ("3", 440, 918, "bell neck under the outer rim"),
    ("3", 452, 938, "bell dome right, under the inner rim"),
    ("3", 422, 945, "bell dome left, under the inner rim"),
    ("3", 432, 943, "bell band, under the inner rim"),
    ("3", 392, 959, "number 3, top stroke under the outer rim"),
    ("5", 407, 876, "lamp foot, right end"),
]
DARK = 128   # tehniskais slieksnis Lipikāra, nav S noteikums


def mask_checks(hs):
    import numpy as np
    from scipy import ndimage as ndi
    lum = np.asarray(Image.open(os.path.join(qa.REPO, "public", "media", "common", "paraphernalia.png")).convert("L"))
    lit = {n: np.asarray(Image.open(os.path.join(qa.REPO, "public", "media", "hotspots",
                                                 *hs["spots"][n]["mask"].split("/"))).getchannel("A")) >= 128
           for n in NUMS}
    bad = []
    for n, x, y, what in CROSSINGS:
        others = [k for k in NUMS if k != n and lit[k][y, x]]
        if not lit[n][y, x] or others:
            bad.append({"n": n, "xy": [x, y], "what": what, "lit_in_own": bool(lit[n][y, x]), "lit_in": others})
    check("static", f"crossings: {len(CROSSINGS)} pixels where a tray rim crosses objects 1, 2, 3, 5 / number 3 are lit "
                    f"in their own mask only", not bad, bad)
    dark = lum < DARK
    ink = lum < 235
    holes = {}
    for n in NUMS:
        own = lit[n] & ink
        inside = ndi.binary_fill_holes(own) & ~own
        miss = dark & inside & ~lit[n]
        if miss.any():
            ys, xs = np.where(miss)
            holes[n] = {"px": int(miss.sum()), "first": [int(xs[0]), int(ys[0])]}
    check("static", "all 18: no black line enclosed by an object's lit outline is left faded", not holes, holes)
    shared = {}
    for i, a in enumerate(NUMS):
        for b in NUMS[i + 1:]:
            c = int((lit[a] & lit[b] & ink).sum())
            if c:
                shared[f"{a}+{b}"] = c
    check("static", "all 18: no drawn pixel lit in two masks (never a piece of a neighbour)", not shared, shared)


PROBE = """() => {
  const fig = [...document.querySelectorAll('.app-main [data-reader-current] .hs-figure, .app-main .hs-figure')]
    .find(f => /paraphernalia/.test(f.querySelector('img')?.getAttribute('src') || ''));
  if (!fig) return null;
  fig.scrollIntoView({block: 'start'});
  const main = document.querySelector('.app-main');
  if (main) main.scrollTop -= 70;
  const img = fig.querySelector('img');
  const fr = fig.getBoundingClientRect(), ir = img.getBoundingClientRect();
  return {src: img.currentSrc || img.src, nw: img.naturalWidth, nh: img.naturalHeight, fw: fr.width, fh: fr.height,
          iw: ir.width, ih: ir.height, ar: fig.style.aspectRatio};
}"""

TAP_PT = """(n) => {
  // the picture in the text, or its floating copy (.hs-peek) when the picture is off-screen
  const imgs = [...document.querySelectorAll('img')].filter(i => /paraphernalia/.test(i.getAttribute('src') || ''));
  for (const img of imgs) {
    const box = img.parentElement;
    const g = [...box.querySelectorAll('.hs-hit')].find(e => e.getAttribute('aria-label') === n);
    if (!g) continue;
    const cands = [...g.querySelectorAll('ellipse, circle')].map(e => e.getBoundingClientRect())
      .map(r => ({x: r.left + r.width / 2, y: r.top + r.height / 2}));
    for (const c of cands) { const el = document.elementFromPoint(c.x, c.y); if (el && el.closest('.hs-hit') === g) return c; }
  }
  return null;
}"""

ACTIVE = """() => [...document.querySelectorAll('.app-main .hs-row[data-active]')].map(r => r.getAttribute('data-hs-nums'))"""


def url(lang, sid):
    return f"{BASE}/{sid}/" if lang == "en" else f"{BASE}/{lang}/{sid}/"


def run(p, dev, eng, o, webp):
    b = getattr(p, eng).launch()
    c = b.new_context(locale="en-US", **o)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    pg = c.new_page()
    touch = o.get("has_touch", False)
    langs = LANGS if dev == "desktop" else ["ru-iast", "en"]
    nums = NUMS if dev == "desktop" else PHONE_NUMS
    for lang in langs:
        for sid in PAGES:
            pg.goto(url(lang, sid), wait_until="networkidle")
            pg.wait_for_timeout(500)
            info = pg.evaluate(PROBE)
            if not info:
                check(dev, f"{lang}/{sid}: the picture is on the page", False)
                continue
            pg.wait_for_function("""() => [...document.querySelectorAll('.app-main .hs-figure img')]
                .every(i => i.complete && i.naturalWidth > 0)""", timeout=15000)
            info = pg.evaluate(PROBE)
            pg.wait_for_timeout(300)
            name = info["src"].rsplit("/", 1)[-1]
            check(dev, f"{lang}/{sid}: shows the new WebP {name}, natural {info['nw']}×{info['nh']}",
                  webp and name == webp.rsplit("/", 1)[-1] and (info["nw"], info["nh"]) == SIZE, info)
            fr = info["fw"] / info["fh"] if info["fh"] else 0
            ir = info["iw"] / info["ih"] if info["ih"] else 0
            check(dev, f"{lang}/{sid}: figure and image 1:1, not stretched (box {info['fw']:.0f}×{info['fh']:.0f}), "
                       f"aspect-ratio from data", abs(fr - 1) * 100 <= TOL and abs(ir - 1) * 100 <= TOL
                  and info["ar"].replace(" ", "") == "1254/1254", info)
            if lang not in ("ru-iast", "en"):
                continue
            bad = {}
            for n in nums:
                pg.evaluate(PROBE)
                pg.wait_for_timeout(250)
                pt = pg.evaluate(TAP_PT, n)
                if not pt:
                    bad[n] = "no tap point"
                    continue
                (pg.touchscreen.tap if touch else pg.mouse.click)(pt["x"], pt["y"])
                pg.wait_for_timeout(450)
                act = pg.evaluate(ACTIVE)
                pg.wait_for_timeout(600)   # the row's own scroll fix-up (Hotspots.tsx, 700 ms) is over before the next tap
                if not act or not all(n in a.split(",") for a in act):
                    bad[n] = act
            check(dev, f"{lang}/{sid}: tap on object {','.join(nums)} → its row lit", not bad, bad)
    b.close()


def main():
    webp = static_checks()
    if STATIC_ONLY:
        print(f"RESULT {'PASS' if all(results) else 'FAIL'} {sum(results)}/{len(results)}")
        sys.exit(0 if all(results) else 1)
    with sync_playwright() as p:
        for dev, eng, o in DEVICES:
            try:
                run(p, dev, eng, o, webp)
            except Exception as e:  # noqa: BLE001
                check(dev, "scenario ran", False, repr(e)[:300])
    print(f"RESULT {'PASS' if all(results) else 'FAIL'} {sum(results)}/{len(results)}")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
