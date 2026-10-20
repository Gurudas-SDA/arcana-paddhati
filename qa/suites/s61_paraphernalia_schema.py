"""V13 — the «16 предметов» picture replaced by Vraja Lila's schematic (Vraja Lila msg 736/738/740, 20.10.2026;
saskarnes īpašnieks, «Стандарты» 0а; nodots-izpildei 20.10 12:33).

Rule text (verbatim): «замена рисунка (сделаешь оптимизацию?)»; criterion (assistant, Vraja's words):
«новая схема в книге без искажения; скриншот». Order (Lipikāra): original unchanged in masters/ (as the
portraits), in the book WebP without distortion, optimisation as the portraits (q58).

Checks
  static: masters/ PNG = Vraja's file byte for byte (sha1; public/media PNG — see V20c); the app's WebP is encoded from it at
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

V20b — Vraja Lila msg 5637 «ты обрезал цифру» (the foot of «1») + 5638 (the shell's spiral and the stand's inner lines,
the spoon in the cup stay grey on the iPhone; all lines of the object inside its outline must be lit).
  static:
    - all 18 numbers whole: every drawn pixel (luminance < 200 — # tehniskais slieksnis Lipikāra, nav S noteikums)
      next to the number's black strokes (≤ 2 px, inside their box + 2 px) is lit in its own mask;
    - the lit picture is baked (data "ink", picture size) and every drawn pixel (< 200) under a lit mask is dark in it
      (< 128 — tehniskais slieksnis Lipikāra) — no inner line of a lit object stays grey; spoon / spiral in CROSSINGS.
  browser: after a tap the lit layer draws that baked picture, with no SVG filter.
  (V20 / V20b pixel points of the old PNG are retired with that PNG in V20c.)

V20c — Vraja Lila msg 5658 (21.10.2026): the schematic as a layered SVG «всё сделал, но не оптимизировал SVG, зато разбил
всё по слоям и по номерам» (layers _x31_ … _x31_8 = objects 1–18 with their numbers, Deities, plate) — answer to the
V20 / V20b cut numbers and lines. Criterion (Lipikāra, Vraja's words): object N lights up = exactly its layer's content
(lines + number), no pixel guessing; the book picture rasterised from the same SVG, so mask and picture match exactly.
  static (the suite rasterises the SVG itself with Chromium):
    - masters/: Vraja's SVG byte for byte (sha1); the svgo copy (the build source) looks the same (mean |Δ| ≤ 0.1 / 255,
      ≤ 0.05 % pixels |Δ| > 16 — tehniskais slieksnis Lipikāra, nav S noteikums);
    - every layer 1–18 holds its printed number (glyphs of the number font — as many as the number has digits);
    - public/media PNG = the SVG rasterised at 1254 × 1254 (|Δ| ≤ 2 / 255 — tehniskais slieksnis Lipikāra);
    - mask N (alpha ≥ 0.5) = layer N's pixels: IoU ≥ 0.99 (tehniskais slieksnis Lipikāra, nav S noteikums), and the
      number's pixels all lit (number whole);
    - lit picture: each object exactly as its layer (|Δ| ≤ 2), its lines (coverage ≥ 0.9) dark (< 128), nothing
      outside the objects drawn.

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
    # V13's PNG stays in masters/ as history; since V20c the book's PNG is rasterised from the SVG (mask_checks)
    p = os.path.join(qa.REPO, "masters", "media", *rel.split("/"))
    h = hashlib.sha1(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None
    check("static", f"masters/media/{rel} = Vraja Lila's V13 original, unchanged (sha1)", h == SHA1, h)
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


SVG_SHA1 = "0c16197a33c4d9691ee642e976bd5b350c2890d6"   # Vraja Lila's layered SVG (msg 5658, 1 176 812 B)
SVG_ORIG = ("masters", "media", "common", "paraphernalia-layers-original.svg")
SVG_OPT = ("masters", "media", "common", "paraphernalia-layers.svg")
IOU = 0.99          # tehniskais slieksnis Lipikāra, nav S noteikums
DARK = 128          # tehniskais slieksnis Lipikāra, nav S noteikums


def layer_id(n):
    return f"_x3{n[0]}_{n[1:]}"     # Illustrator: "1" -> _x31_, "10" -> _x31_0


def glyphs_of(cov):
    """Number glyphs in a layer: connected pieces (coverage ≥ 0.5) 21–26 px high, 12–19 px wide (the number font)."""
    import numpy as np
    from scipy import ndimage as ndi
    lab, _ = ndi.label(cov >= 0.5, structure=np.ones((3, 3)))
    return [(sl[1].start, sl[0].start, sl[1].stop - sl[1].start, sl[0].stop - sl[0].start) for sl in ndi.find_objects(lab)
            if 21 <= sl[0].stop - sl[0].start <= 26 and 12 <= sl[1].stop - sl[1].start <= 19]


def raster(path, ids_list):
    """Chromium rasterisation of the SVG at 1254 × 1254: per entry of ids_list (None = all but the background) the
    coverage 0..1 and the luminance on white."""
    import re
    import numpy as np
    svg = re.sub(r"^\s*<\?xml[^>]*>", "", open(path, encoding="utf-8").read())
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": SIZE[0], "height": SIZE[1]}, device_scale_factor=1)
        pg.set_content(f'<!doctype html><html><body style="margin:0;background:transparent">{svg}</body></html>')
        pg.evaluate("""() => { const s = document.querySelector('svg'); s.setAttribute('width', 1254); s.setAttribute('height', 1254);
            s.style.display = 'block'; document.getElementById('background')?.remove(); }""")
        for ids in ids_list:
            pg.evaluate("""(ids) => { for (const c of document.querySelector('svg').children) if (c.tagName !== 'defs')
                c.style.display = ids === null || ids.includes(c.id) ? '' : 'none'; }""", ids)
            a = np.asarray(Image.open(io.BytesIO(pg.screenshot(omit_background=True))).convert("RGBA")).astype(float)
            cov = a[..., 3] / 255
            out.append((cov, (a[..., :3] @ [0.299, 0.587, 0.114]) * cov + 255 * (1 - cov)))
        b.close()
    return out


def mask_checks(hs):
    import numpy as np
    orig = os.path.join(qa.REPO, *SVG_ORIG)
    opt = os.path.join(qa.REPO, *SVG_OPT)
    h = hashlib.sha1(open(orig, "rb").read()).hexdigest() if os.path.exists(orig) else None
    check("static", "masters/media/common/paraphernalia-layers-original.svg = Vraja Lila's SVG (msg 5658), unchanged (sha1)",
          h == SVG_SHA1, h)
    if not os.path.exists(opt) or h != SVG_SHA1:
        check("static", "optimised SVG (build source) present", False, SVG_OPT)
        return
    (r_o,) = raster(orig, [None])
    rs = raster(opt, [None] + [[layer_id(n)] for n in NUMS])
    glyphs = {layer_id(n): glyphs_of(rs[i + 1][0]) for i, n in enumerate(NUMS)}
    whole = rs[0][1]
    d = np.abs(whole - r_o[1])
    check("static", f"optimised SVG looks the same as Vraja's (mean |Δ| {d.mean():.3f}, {int((d > 16).sum())} px > 16)",
          d.mean() <= 0.1 and (d > 16).sum() <= 0.0005 * d.size, {"mean": float(d.mean()), "px>16": int((d > 16).sum())})
    nog = {n: len(glyphs.get(layer_id(n), [])) for n in NUMS if len(glyphs.get(layer_id(n), [])) != len(n)}
    check("static", "every layer 1–18 holds its printed number (number glyphs = digits)", not nog, nog)
    png = np.asarray(Image.open(os.path.join(qa.REPO, "public", "media", "common", "paraphernalia.png")).convert("L")).astype(float)
    dp = np.abs(png - whole)
    check("static", "public/media PNG = the SVG rasterised at 1254 × 1254 (|Δ| ≤ 2)", dp.max() <= 2,
          {"max": float(dp.max()), "px>2": int((dp > 2).sum())})
    lit = {n: np.asarray(Image.open(os.path.join(qa.REPO, "public", "media", "hotspots",
                                                 *hs["spots"][n]["mask"].split("/"))).getchannel("A")) >= 128
           for n in NUMS}
    layer = {n: rs[i + 1][0] for i, n in enumerate(NUMS)}
    bad, cut = {}, {}
    H, W = SIZE[1], SIZE[0]
    for n in NUMS:
        L = layer[n] > 0
        iou = (lit[n] & L).sum() / max((lit[n] | L).sum(), 1)
        if iou < IOU:
            bad[n] = round(float(iou), 4)
        for x, y, w, gh in glyphs.get(layer_id(n), []):
            box = np.zeros_like(L)
            box[int(y) - 1:int(y + gh) + 2, int(x) - 1:int(x + w) + 2] = True
            miss = L & (layer[n] >= 0.5) & box & ~lit[n]
            if miss.any() or not (L & box).any():
                cut[n] = int(miss.sum())
    check("static", f"all 18: mask N = SVG layer N (IoU ≥ {IOU})", not bad, bad)
    check("static", "all 18 numbers whole: every pixel of the number's glyphs lit in its mask", not cut, cut)
    shared = {}
    for i, a in enumerate(NUMS):
        for b in NUMS[i + 1:]:
            c = int((lit[a] & lit[b]).sum())
            if c:
                shared[f"{a}+{b}"] = c
    check("static", "all 18: no pixel lit in two masks (never a piece of a neighbour)", not shared, shared)
    ink_rel = hs.get("ink")
    p = os.path.join(qa.REPO, "public", "media", "hotspots", *(ink_rel or "-").split("/"))
    if not ink_rel or not os.path.exists(p):
        check("static", "lit picture baked (hotspots.json \"ink\")", False, ink_rel)
        return
    ink_img = np.asarray(Image.open(p).convert("L")).astype(float)
    grey, diff = {}, {}
    for i, n in enumerate(NUMS):
        g = int(((layer[n] >= 0.9) & (ink_img >= DARK)).sum())
        if g:
            grey[n] = g
        dd = np.abs(ink_img - rs[i + 1][1])[layer[n] > 0]
        if dd.size and dd.max() > 2:
            diff[n] = float(dd.max())
    check("static", "all 18: every line of a lit object (coverage ≥ 0.9) is dark (< 128) in the lit picture", not grey, grey)
    check("static", "all 18: the lit picture shows each object exactly as its SVG layer (|Δ| ≤ 2)", not diff, diff)
    anyl = np.logical_or.reduce([layer[n] > 0 for n in NUMS])
    stray = int(((ink_img < 250) & ~anyl).sum())
    check("static", "lit picture: nothing drawn outside the objects 1–18 (no Deities, no tray)", stray == 0, stray)


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
            lit_img = pg.evaluate("""() => { const i = document.querySelector('.app-main .hs-lit image');
                return i ? {href: i.getAttribute('href'), filter: i.getAttribute('filter')} : null; }""")
            check(dev, f"{lang}/{sid}: the lit layer draws the baked picture, no SVG filter",
                  lit_img and "/media/hotspots/paraphernalia/ink-" in (lit_img["href"] or "") and not lit_img["filter"], lit_img)
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
