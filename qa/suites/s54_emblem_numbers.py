"""Emblem numbers (Vraja Lila msg 5429/5432, 20.10.2026 — saskarnes īpašnieks, «Стандарты» 0а).

Rule text (verbatim, msg 5429/5432): «утверждено» / «делай с размытием» — maketi
`Vraja_Lila/faili/2026.10.20_Эмблема — цифры, крупно.png` («после исправления») and
`…/2026.10.20_Эмблема — цифры, подложка с размытием.png` (right side):
  - all numbers 1–12, 2.1–2.6 alike: colour #6E1A2E, white 60 % pill, backdrop blur 3.5 px
    (`backdrop-filter` + `-webkit-backdrop-filter`), in their own HTML layer without mix-blend-mode;
  - 8 by the mridanga in the «kīrtanam» field (78; 86), 10 right of Mahāprabhu (57; 8),
    11 right of Rādhā (93.5; 49.5); the others in their places (12 by the throne);
  - the app's picture carries no burned-in numbers (they are drawn by the app); the PNG for the
    PDF / EPUB keeps its numbers.
Checks: every language (desktop: 18 numbers, style, places); iPhone / iPad / desktop: also taps on the
numbers 1–11 select their row, and «Ночь»: number contrast on its pill ≥ 4.5 (# tehniskais slieksnis
Lipikāra, nav S noteikums — WCAG AA). usage: python s54_emblem_numbers.py <base-url>
"""
import io
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from PIL import Image  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
ORIGIN = BASE.split("/arcana-paddhati")[0]
NUMS = ["1", "2", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
# places on the picture (% of width / height) — the maquette «после исправления»
PLACE = {"1": (40.4, 50.0), "2": (63.2, 50.0), "2.1": (50.0, 34.0), "2.2": (63.6, 41.3), "2.3": (63.6, 58.7),
         "2.4": (50.0, 66.2), "2.5": (36.4, 58.7), "2.6": (36.4, 41.3), "3": (30.0, 10.5), "4": (65.0, 34.5),
         "5": (16.5, 76.0), "6": (83.2, 76.0), "7": (40.0, 79.0), "8": (78.0, 86.0), "9": (52.7, 76.8),
         "10": (57.0, 8.0), "11": (93.5, 49.5), "12": (9.0, 33.5)}
TOL = 1.0          # % — tehniskais slieksnis Lipikāra, nav S noteikums
CONTRAST_MIN = 4.5  # tehniskais slieksnis Lipikāra, nav S noteikums (WCAG AA)
TAP_NUMS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]
# burned-in numbers 1–9 of the original picture (px of the 1000×1000 PNG)
BURNED = {"2": (623, 639, 491, 512), "3": (291, 307, 97, 118), "4": (641, 659, 337, 357),
          "5": (156, 172, 752, 773), "6": (824, 841, 751, 773), "7": (392, 408, 782, 802),
          "8": (581, 598, 806, 828), "9": (518, 535, 759, 781)}
LANGS = [l["code"] for l in json.load(open(os.path.join(qa.REPO, "lib", "languages.json"), encoding="utf-8"))
         if not l.get("replacedBy")]
DEVICES = qa.devices(["iphone14", "ipad-portrait", "desktop"])
results = []

PROBE = """() => {
  const fig = [...document.querySelectorAll('.app-main [data-reader-current] .hs-figure, .app-main .hs-figure')]
    .find(f => /gaudiya-emblem/.test(f.querySelector('img')?.getAttribute('src') || ''));
  if (!fig) return null;
  fig.scrollIntoView({block: 'center'});
  const fr = fig.getBoundingClientRect();
  const img = fig.querySelector('img');
  const tags = [...fig.querySelectorAll('.hs-tag')].map(t => {
    const r = t.getBoundingClientRect(), cs = getComputedStyle(t);
    let blend = [], e = t;
    while (e && e !== fig) { const m = getComputedStyle(e).mixBlendMode; if (m !== 'normal') blend.push(m); e = e.parentElement; }
    return {n: t.textContent.trim(), html: !t.closest('svg'), x: (r.left + r.width / 2 - fr.left) / fr.width * 100,
      y: (r.top + r.height / 2 - fr.top) / fr.height * 100, w: r.width, h: r.height, color: cs.color,
      bg: cs.backgroundColor, bf: cs.backdropFilter || '', wbf: cs.webkitBackdropFilter || '', blend,
      vis: cs.visibility === 'visible' && cs.display !== 'none' && +cs.opacity === 1,
      box: [r.left, r.top, r.width, r.height]};
  });
  return {tags, img: img.currentSrc || img.src, fig: [fr.left, fr.top, fr.width, fr.height]};
}"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


def lum(rgb):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb[:3]
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def page_url(lang):
    return f"{BASE}/gaudiya-emblem/" if lang == "en" else f"{BASE}/{lang}/gaudiya-emblem/"


def open_emblem(pg, lang):
    pg.goto(page_url(lang), wait_until="networkidle")
    pg.wait_for_timeout(600)
    info = pg.evaluate(PROBE)
    pg.wait_for_timeout(400)
    return pg.evaluate(PROBE) if info else info


def style_checks(dev, lang, info):
    tags = info["tags"]
    names = [t["n"] for t in tags]
    check(dev, f"{lang}: all 18 numbers shown (1–12, 2.1–2.6), each once", sorted(names) == sorted(NUMS), names)
    bad = [t["n"] for t in tags if not (t["html"] and t["vis"] and t["w"] > 0 and t["color"] == "rgb(110, 26, 46)")]
    check(dev, f"{lang}: every number #6E1A2E, HTML layer, visible", not bad, bad)
    bad = [t["n"] for t in tags if not (t["bg"] in ("rgba(255, 255, 255, 0.6)",) and "blur(3.5px)" in (t["bf"] + t["wbf"]))]
    check(dev, f"{lang}: every number on a white 60 % pill with backdrop blur 3.5 px", not bad,
          bad or {"bg": tags[0]["bg"], "bf": tags[0]["bf"] or tags[0]["wbf"]})
    bad = [(t["n"], t["blend"]) for t in tags if t["blend"]]
    check(dev, f"{lang}: no mix-blend-mode on the numbers or their layer", not bad, bad)
    off = {t["n"]: [round(t["x"], 1), round(t["y"], 1)] for t in tags
           if t["n"] in PLACE and (abs(t["x"] - PLACE[t["n"]][0]) > TOL or abs(t["y"] - PLACE[t["n"]][1]) > TOL)}
    check(dev, f"{lang}: numbers in their places (8 by the mridanga, 10 by Mahāprabhu, 11 by Rādhā, 12 by the throne)",
          not off, off)


def image_checks():
    """The app's picture (served WebP) has no burned-in numbers; the PNG (PDF / EPUB) keeps them."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        info = open_emblem(pg, "ru-iast")
        b.close()
    if not info:
        check("img", "emblem picture found", False)
        return
    src = info["img"]
    raw = urllib.request.urlopen(src if src.startswith("http") else ORIGIN + src).read()
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    left = {}
    for n, (x0, x1, y0, y1) in BURNED.items():
        px = [im.getpixel((x, y)) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]
        dark = sum(1 for c in px if max(c) - min(c) < 30 and max(c) < 160)
        if dark:
            left[n] = dark
    g1 = [im.getpixel((x, y))[1] for x in range(406, 414) for y in range(494, 509)]
    if sum(g1) / len(g1) > 70:
        left["1"] = round(sum(g1) / len(g1))
    check("img", f"app picture has no burned-in numbers 1–9 ({src.rsplit('/', 1)[-1]})", not left, left)
    png = Image.open(os.path.join(qa.REPO, "public", "media", "common", "gaudiya-emblem.png")).convert("RGB")
    kept = sum(1 for (x0, x1, y0, y1) in BURNED.values() for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)
               if max(png.getpixel((x, y))) < 160 and max(png.getpixel((x, y))) - min(png.getpixel((x, y))) < 30)
    check("img", "PDF / EPUB picture (public/media PNG) keeps its numbers 1–9", kept > 1000, kept)


image_checks()

with sync_playwright() as p:
    # every language: numbers, style, places (desktop)
    b = p.chromium.launch()
    c = b.new_context(service_workers="block", viewport={"width": 1440, "height": 900})
    c.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
    pg = c.new_page()
    for lang in LANGS:
        info = open_emblem(pg, lang)
        if not info:
            check("desktop", f"{lang}: emblem picture found", False)
            continue
        style_checks("desktop", lang, info)
    b.close()

    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        for theme in ("day", "night"):
            c = b.new_context(service_workers="block", **opts)
            c.add_init_script("localStorage.setItem('ap.readerHintSeen','1')"
                              + (";localStorage.setItem('ap.readerTheme','night')" if theme == "night" else ""))
            pg = c.new_page()
            for lang in (["ru-iast", "en"] if theme == "day" else ["ru-iast"]):
                info = open_emblem(pg, lang)
                if not info:
                    check(dev, f"{lang} {theme}: emblem picture found", False)
                    continue
                style_checks(dev, f"{lang} {theme}", info)
                # contrast of each number on its pill (rendered pixels)
                shot = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
                sc = shot.width / opts["viewport"]["width"]
                low = {}
                for t in info["tags"]:
                    x, y, w, h = [v * sc for v in t["box"]]
                    crop = shot.crop((int(x), int(y), int(x + w), int(y + h)))
                    ls = sorted(lum(crop.getpixel((i, j))) for i in range(crop.width) for j in range(crop.height))
                    if not ls:
                        low[t["n"]] = "empty"
                        continue
                    dark, light = ls[int(len(ls) * 0.05)], ls[int(len(ls) * 0.9)]
                    cr = (light + 0.05) / (dark + 0.05)
                    if cr < CONTRAST_MIN:
                        low[t["n"]] = round(cr, 2)
                check(dev, f"{lang} {theme}: every number readable on its pill (contrast ≥ {CONTRAST_MIN})", not low, low)
                if theme != "day" or lang != "ru-iast":
                    continue
                # taps on the numbers select their row (as before; 8 now by the mridanga)
                missed = {}
                for n in TAP_NUMS:
                    info = pg.evaluate(PROBE)
                    t = next((t for t in info["tags"] if t["n"] == n), None)
                    if not t:
                        missed[n] = "no number"
                        continue
                    x, y, w, h = t["box"]
                    (pg.touchscreen.tap if opts.get("has_touch") else pg.mouse.click)(x + w / 2, y + h / 2)
                    pg.wait_for_timeout(450)
                    rows = pg.evaluate("[...document.querySelectorAll('.app-main .hs-row[data-active]')].map(r => r.dataset.hsNums)")
                    if not any(n in (r or "").split(",") for r in rows):
                        missed[n] = rows
                check(dev, f"{lang}: a tap on numbers 1–11 selects their row", not missed, missed)
            c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
