"""V80 — Vraja Lila msg 7676 (interface owner; her words are the decision). Her words, literally:
«что можешь сделать уже сейчас это переименовать назад и вперёд в нижней панели на Пред.глава / След.глава.
это сделай прямо в книге сейчас».
Criteria (register V80): the bottom bar's two buttons read «‹ Пред. глава» / «След. глава ›» (RU, ru-iast; with a
space after the dot) and «‹ Prev chapter» / «Next chapter ›» (EN); arrows, data-reader-nav, targets unchanged; first
page has no «Пред. глава», last page no «След. глава»; the old «Назад» / «Вперёд» (Back / Forward) are gone from the
bar. The system «Назад» (other places) is not touched — the reader.back / reader.forward keys stay.
usage: python s154_prev_next_chapter_labels_v80.py <base-url>   (QA_DEVICES filters devices)
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
import book_order  # noqa: E402
import json, sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "desktop"])
res = []


def chk(d, n, ok, info=""):
    res.append((d, n, bool(ok), info)); print(f"  [{'PASS' if ok else 'FAIL'}] {d} {n} {'' if ok else info}", flush=True)


# static: new keys, old keys kept, other languages fall back to English
def load(rel):
    return json.load(open(_os.path.join(qa.REPO, rel), encoding="utf-8"))


nrm = lambda x: x.replace(" ‹", "‹").replace("‹ ", "‹").replace(" ›", "›").replace("› ", "›")  # textContent has no space around the arrow (own element); the gap is checked below
WANT = {"ru-iast": ("Пред. глава", "След. глава"), "ru": ("Пред. глава", "След. глава"), "en": ("Prev chapter", "Next chapter")}
for lang, (pv, nx) in WANT.items():
    d = load(f"data/ui.{lang}.json")
    chk("static", f"ui.{lang}: reader.prevChapter = «{pv}»", d.get("reader.prevChapter") == pv, d.get("reader.prevChapter"))
    chk("static", f"ui.{lang}: reader.nextChapter = «{nx}»", d.get("reader.nextChapter") == nx, d.get("reader.nextChapter"))
chk("static", "ui.en: reader.back / reader.forward kept (other «Back» places)", load("data/ui.en.json").get("reader.back") == "Back")

GEO = """() => { const q = s => { const a = document.querySelector(s); if (!a) return null; const r = a.getBoundingClientRect();
  return {t: a.textContent.replace(/\\s+/g,' ').trim(), gap: (() => { const sp = a.querySelectorAll('span'); if (sp.length < 2) return null; const x = sp[0].getBoundingClientRect(), y = sp[1].getBoundingClientRect(); return Math.round(Math.max(y.left - x.right, x.left - y.right) * 10) / 10; })(), l: r.left, r: r.right, top: r.top, bottom: r.bottom, w: r.width, h: r.height, target: a.getAttribute('data-chapter-target')}; };
  return {vw: innerWidth, vh: innerHeight, b: q('[data-reader-nav=back]'), f: q('[data-reader-nav=forward]'),
    shown: !!document.querySelector('.reader-chrome[data-shown]'), bar: document.querySelector('.reader-bar-bottom').textContent.replace(/\\s+/g,' ').trim()}; }"""


def run(p, dev, eng, o):
    br = getattr(p, eng).launch()
    touch = o.get("has_touch", False)
    ctx = br.new_context(service_workers="block", **o)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    def bars():
        if pg.locator(".reader-chrome[data-shown]").count() == 0:
            vw, vh = pg.viewport_size["width"], pg.viewport_size["height"]
            for fx, fy in ((0.5, 0.5), (0.3, 0.4), (0.7, 0.55)):
                (pg.touchscreen.tap if touch else pg.mouse.click)(vw * fx, vh * fy); pg.wait_for_timeout(500)
                if pg.locator(".reader-chrome[data-shown]").count():
                    break

    def geo(url):
        pg.goto(url, wait_until="networkidle"); pg.wait_for_timeout(700)
        pg.evaluate("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
        bars(); return pg.evaluate(GEO)

    for lang, mid, first, last in [("ru-iast", "vigraha-tattva", None, None), ("en", "vigraha-tattva", None, None)]:
        pv, nx = WANT[lang]
        pages = book_order.pages(lang)
        last = pages[-1]
        url = f"{BASE}/{lang}/{mid}/" if lang != "en" else f"{BASE}/{mid}/"
        g = geo(url)
        chk(dev, f"{lang} {mid}: «‹ {pv}»", bool(g["b"]) and nrm(g["b"]["t"]) == nrm(f"‹ {pv}"), str(g["b"]))
        chk(dev, f"{lang} {mid}: «{nx} ›»", bool(g["f"]) and nrm(g["f"]["t"]) == nrm(f"{nx} ›"), str(g["f"]))
        chk(dev, f"{lang} {mid}: on screen a gap between each arrow and its text (computed)", all(x and x["gap"] is not None and x["gap"] > 0 for x in (g["b"], g["f"])), str(g))
        chk(dev, f"{lang} {mid}: no old Назад/Вперёд/Back/Forward in the bar", not any(w in g["bar"] for w in ("Назад", "Вперёд", "Back", "Forward")), g["bar"])
        chk(dev, f"{lang} {mid}: both buttons inside the screen, >= 44 px, not overlapping",
            all(x and x["l"] >= 0 and x["r"] <= g["vw"] and x["h"] >= 44 - 0.5 for x in (g["b"], g["f"])) and g["b"]["r"] <= g["f"]["l"], str(g))
        g = geo(f"{BASE}/{lang}/" if lang != "en" else f"{BASE}/")
        chk(dev, f"{lang} cover: no «{pv}»", g["b"] is None, str(g["b"]))
        chk(dev, f"{lang} cover: «{nx} ›» present", bool(g["f"]) and nrm(g["f"]["t"]) == nrm(f"{nx} ›"), str(g["f"]))
        g = geo(url.replace(f"/{mid}/", f"/{last}/"))
        chk(dev, f"{lang} last page {last}: no «{nx}»", g["f"] is None, str(g["f"]))
        chk(dev, f"{lang} last page {last}: «‹ {pv}» present", bool(g["b"]) and nrm(g["b"]["t"]) == nrm(f"‹ {pv}"), str(g["b"]))
    chk(dev, "no page errors", not errs, str(errs[:2]))
    br.close()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        print(dev, flush=True)
        try:
            run(p, dev, eng, o)
        except Exception as e:
            chk(dev, "EXCEPTION", False, str(e)[:900])
fails = [r for r in res if not r[2]]
print(f"\n{len(res) - len(fails)}/{len(res)} passed")
for f in fails:
    print("FAILED:", f[0], f[1], f[3][:300])
sys.exit(1 if fails or not res else 0)
