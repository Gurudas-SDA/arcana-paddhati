"""V8 — Chaitanya Academy logo on the cover as Vraja Lila's vector (Vraja Lila msg 663/742, 20.10.2026;
saskarnes īpašnieks, «Стандарты» 0а; nodots-izpildei 20.10 12:40).

Rule text (verbatim, msg 742): «масштабируй его правильно». Criteria (assistant, Vraja's words): «логотип векторный,
пропорции 257:83, чёткий на iPhone/desktop, обложка не прыгает; скриншот светлая тема и „Ночь"».

Checks (every device, light theme and «Тёмный»):
  - the cover carries an inline <svg class="home-cover-logo"> with Vraja's viewBox 0 0 257.42361 83.22854 and
    width / height attributes, already in the page's HTML (drawn with it — nothing loads later, no jump);
  - drawn box proportion = 257.42 : 83.23 (≤ 0.5 % — # tehniskais slieksnis Lipikāra, nav S noteikums);
  - in the place of the old raster logo: left 33.72 %, top 87.54 %, width 32.56 % of the cover (≤ 0.5 % of the
    cover — # tehniskais slieksnis Lipikāra, nav S noteikums), inside the cover;
  - the served cover WebP has no raster logo left under it (no red / dark pixels in the logo area);
  - the lettering is readable: contrast to the cover's background ≥ 4.5 (# tehniskais slieksnis Lipikāra, nav S
    noteikums — WCAG AA), also in «Тёмный»;
  - a tap on the logo reaches the cover (the logo takes no taps).
Static: masters/ and public/media/common/ca-logo.svg = Vraja's file byte for byte; public/media/cover/cover.jpg (PDF /
EPUB) keeps its logo.

usage: python s62_ca_logo_vector.py <base-url>   devices: QA_DEVICES
"""
import hashlib
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
SHA1 = "3ad8908b8bd5ef649302730c79943991765efd13"     # Vraja Lila's CA-logo.svg (6 000 B)
VIEWBOX = "0 0 257.42361 83.22854"
RATIO = 257.42361 / 83.22854
PLACE = {"left": 33.72, "top": 87.54, "width": 32.56}
TOL = 0.5          # % — tehniskais slieksnis Lipikāra, nav S noteikums
CONTRAST_MIN = 4.5  # tehniskais slieksnis Lipikāra, nav S noteikums (WCAG AA)
LOGO_AREA = (280, 1085, 594, 1180)   # raster logo ink in the 874 × 1240 cover
DEVICES = qa.devices(["iphone14", "pixel7", "ipad-portrait", "desktop"])
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else json.dumps(evidence, ensure_ascii=False)}", flush=True)


def lum(rgb):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb[:3]
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def logo_ink(im):
    """Red (mark) or dark (lettering) pixels in the old logo's area of an 874 × 1240 cover."""
    im = im.convert("RGB").resize((874, 1240)) if im.size != (874, 1240) else im.convert("RGB")
    n = 0
    x0, y0, x1, y1 = LOGO_AREA
    for y in range(y0, y1, 2):
        for x in range(x0, x1, 2):
            r, g, b = im.getpixel((x, y))
            if (r - g > 60) or (r + g + b < 450):
                n += 1
    return n


def static_checks():
    for where in ("masters/media", "public/media"):
        p = os.path.join(qa.REPO, *where.split("/"), "common", "ca-logo.svg")
        h = hashlib.sha1(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None
        check("static", f"{where}/common/ca-logo.svg = Vraja Lila's file, unchanged (sha1)", h == SHA1, h)
    n = logo_ink(Image.open(os.path.join(qa.REPO, "public", "media", "cover", "cover.jpg")))
    check("static", "public/media/cover/cover.jpg (PDF / EPUB cover) keeps its logo", n > 500, n)
    html = os.path.join(qa.OUT, "index.html")
    if os.path.exists(html):
        s = open(html, encoding="utf-8").read()
        check("static", "out/index.html: the logo svg is in the HTML (drawn with the page, no later load)",
              "home-cover-logo" in s and VIEWBOX in s)


PROBE = """() => {
  const img = document.querySelector('.home-cover');
  const svg = document.querySelector('svg.home-cover-logo');
  if (!img || !svg) return {img: !!img, svg: !!svg};
  const ir = img.getBoundingClientRect(), lr = svg.getBoundingClientRect();
  const box = svg.parentElement.getBoundingClientRect();
  const txt = [...svg.querySelectorAll('[fill="currentColor"]')];
  const cx = lr.left + lr.width / 2, cy = lr.top + lr.height / 2;
  const hit = document.elementFromPoint(cx, cy);
  return {img: true, svg: true, vb: svg.getAttribute('viewBox'), wa: svg.getAttribute('width'), ha: svg.getAttribute('height'),
    ir: [ir.left, ir.top, ir.width, ir.height], lr: [lr.left, lr.top, lr.width, lr.height],
    box: [box.left, box.top, box.width, box.height], color: getComputedStyle(svg).color, ntxt: txt.length,
    filter: getComputedStyle(svg).filter, coverFilter: getComputedStyle(img).filter,
    hit: hit ? (hit === img ? 'cover' : hit.tagName + '.' + (hit.getAttribute('class') || '')) : null,
    src: img.currentSrc || img.src, complete: img.complete && img.naturalWidth > 0};
}"""


def rgb(css):
    return [int(float(v)) for v in css[css.index("(") + 1:css.index(")")].split(",")[:3]]


def run(p, dev, eng, o):
    b = getattr(p, eng).launch()
    for theme in ("light", "night"):
        c = b.new_context(locale="ru-RU", **o)
        c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
        if theme == "night":
            c.add_init_script("try{localStorage.setItem('ap.readerTheme','night')}catch(e){}")
        pg = c.new_page()
        pg.goto(f"{BASE}/ru-iast/", wait_until="networkidle")
        if theme == "night":
            pg.evaluate("()=>document.documentElement.setAttribute('data-reader-theme','night')")
        pg.wait_for_function("() => { const i = document.querySelector('.home-cover'); return i && i.complete && i.naturalWidth > 0 }",
                             timeout=15000)
        pg.wait_for_timeout(400)
        r = pg.evaluate(PROBE)
        t = f"{theme}:"
        check(dev, f"{t} inline vector logo on the cover", r.get("svg") and r.get("vb") == VIEWBOX and r.get("wa") and r.get("ha"), r)
        if not r.get("svg"):
            c.close()
            continue
        il, it, iw, ih = r["ir"]
        ll, lt, lw, lh = r["lr"]
        ratio = lw / lh if lh else 0
        check(dev, f"{t} logo proportion 257.42 : 83.23 (drawn {lw:.1f}×{lh:.1f})", abs(ratio / RATIO - 1) * 100 <= TOL, [lw, lh])
        pos = {"left": (ll - il) / iw * 100, "top": (lt - it) / ih * 100, "width": lw / iw * 100}
        off = {k: round(v, 2) for k, v in pos.items() if abs(v - PLACE[k]) > TOL}
        inside = ll >= il and lt >= it and ll + lw <= il + iw + 0.5 and lt + lh <= it + ih + 0.5
        check(dev, f"{t} logo in the old logo's place, inside the cover", not off and inside, {"off": off, "pos": pos})
        bl, bt, bw, bh = r["box"]
        check(dev, f"{t} the logo's box is exactly the cover", abs(bl - il) < 1 and abs(bt - it) < 1 and abs(bw - iw) < 1 and abs(bh - ih) < 1,
              {"box": r["box"], "img": r["ir"]})
        raw = urllib.request.urlopen(r["src"] if r["src"].startswith("http") else ORIGIN + r["src"]).read()
        n = logo_ink(Image.open(io.BytesIO(raw)))
        check(dev, f"{t} served cover ({r['src'].rsplit('/', 1)[-1]}) has no raster logo under the vector", n == 0, n)
        bright = 0.9 if "brightness(0.9)" in (r["filter"] or "") else 1.0
        bg = [v * (0.9 if "brightness(0.9)" in (r["coverFilter"] or "") else 1.0) for v in (245, 238, 222)]
        col = [v * bright for v in rgb(r["color"])]
        cr = contrast(col, bg)
        check(dev, f"{t} lettering readable on the cover (contrast {cr:.1f})", r["ntxt"] > 0 and cr >= CONTRAST_MIN, r["color"])
        check(dev, f"{t} a tap on the logo reaches the cover", r["hit"] == "cover", r["hit"])
        c.close()
    b.close()


def main():
    static_checks()
    with sync_playwright() as p:
        for dev, eng, o in DEVICES:
            try:
                run(p, dev, eng, o)
            except Exception as e:  # noqa: BLE001
                check(dev, "scenario ran", False, repr(e)[:300])
    print(f"RESULT {'PASS' if all(results) else 'FAIL'} {sum(results)}/{len(results)}")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
