"""V67 — the cover stands vertically centred between the top and the bottom bar, also while the book is being saved / has been saved.
Vraja Lila msg 7365, literally: «обложка должна быть хорошо вертикально отцентрована между верхним и нижним меню при скачивании
книги тоже… когда книга скачана смотри как хорошо смотрится». Two screenshots (iPhone, EN): bad = under the cover the card
«The whole book is saved / Internet is no longer needed / hide» — the cover is pushed up, its top edge under the top bar; good = the
«Continue reading» card — the cover + the card are centred between the top bar and the bottom «Forward» bar.
Criteria (register V67): (1) the block (the cover + the card under it, whichever card) has the same gap above (from the top bar's lower
edge to the cover's top) and below (from the card's lower edge to the bottom bar's upper edge); (2) the cover's top is never above the
top bar's lower edge; (3) the same with the card «saving», «saved» and «Continue reading»; (4) on a phone, a tablet and a computer.
# tehniskais slieksnis Lipikāra, nav S noteikums: the two gaps differ by at most 2 px; settle 900 ms
usage: python s139_cover_centered_v67.py <base-url>
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7", "ipad-portrait", "desktop", "mac-safari"])
TOL = 2
results = []

PLACE = {"v": 1, "section": "worship-sixteen-articles", "anchor": "guru-pankti-namaskara", "block": 0, "offset": 0, "lang": "ru-iast"}
CASES = [
    ("save card: saving", None, {"s": "loading", "d": 40, "t": 120}, ".home-save"),
    ("save card: the whole book is saved", None, {"s": "done", "d": 120, "t": 120}, ".home-save"),
    ("Continue reading card", PLACE, {"s": "seen"}, "a.home-resume"),
]

GEOM = """(card) => { const r = (e) => e ? e.getBoundingClientRect() : null;
  const top = document.querySelector('.reader-bar-top'), bot = document.querySelector('.reader-bar-bottom');
  const cover = r(document.querySelector('img.home-cover')), c = r(document.querySelector(card));
  const topBottom = top.offsetHeight, botTop = window.innerHeight - bot.offsetHeight;
  return {coverTop: cover && cover.top, cardBottom: c && c.bottom, topBarBottom: topBottom, bottomBarTop: botTop,
          gapAbove: cover && cover.top - topBottom, gapBelow: c && botTop - c.bottom}; }"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:500]}", flush=True)


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        for name, place, save, card in CASES:
            c = b.new_context(service_workers="block", locale="en-US", **opts)
            init = "localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');"
            init += "localStorage.setItem('ap.offlineSave', %s);" % json.dumps(json.dumps(save))
            if place:
                init += "localStorage.setItem('ap.readingPlace', %s);" % json.dumps(json.dumps(dict(place, time=int(time.time() * 1000))))
            c.add_init_script(init)
            pg = c.new_page()
            pg.goto(f"{BASE}/ru-iast/", wait_until="networkidle")
            pg.wait_for_timeout(900)
            g = pg.evaluate(GEOM, card)
            ok_geo = g["gapAbove"] is not None and g["gapBelow"] is not None
            check(dev, f"{name}: the gap above the cover = the gap below the card (±{TOL} px)",
                  ok_geo and abs(g["gapAbove"] - g["gapBelow"]) <= TOL, g)
            check(dev, f"{name}: the cover's top is not above the top bar's lower edge",
                  ok_geo and g["coverTop"] >= g["topBarBottom"], g)
            c.close()
        b.close()

# V67 Vraja Lila msg 7373/7374: the lit bookmark's mark = Б2-а (::before with a mask, --ap-gold), not a 3 px border
BAR = """(el) => { const b = getComputedStyle(el, '::before'); const p = document.createElement('i'); p.style.color = 'var(--ap-gold)';
  document.body.appendChild(p); const gold = getComputedStyle(p).color; p.remove();
  return {content: b.content, mask: (b.maskImage || b.webkitMaskImage || 'none') !== 'none', bg: b.backgroundColor, gold: gold,
          borderLeft: getComputedStyle(el).borderLeftWidth}; }"""
with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        c = b.new_context(service_workers="block", locale="ru-RU", **opts)
        items = [{"id": "b0", "section": "introduction", "anchor": None, "block": 0, "lang": "ru-iast", "time": 1000, "name": "Введение"}]
        c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');"
                          "localStorage.setItem('ap.bookmarks', JSON.stringify({v:1,items:%s}));" % json.dumps(items))
        pg = c.new_page()
        pg.goto(f"{BASE}/ru-iast/introduction/", wait_until="networkidle")
        pg.wait_for_timeout(1200)
        pg.evaluate("() => document.querySelector('[data-reader-action=contents]').click()")
        pg.wait_for_timeout(700)
        pg.evaluate("() => { const t = document.querySelector('[data-sidebar-tab=bookmarks]'); if (t) t.click(); }")
        pg.wait_for_selector("[data-bookmark-lit]", timeout=8000)
        g = pg.evaluate(BAR, pg.query_selector("[data-bookmark-lit]"))
        check(dev, "the lit bookmark's mark = a rounded bar Б2-а (::before with a mask, --ap-gold); border-left is not 3 px",
              g["content"] not in ("none", "normal") and g["mask"] and g["bg"] == g["gold"] and g["borderLeft"] != "3px", g)
        c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
