"""«Закладки»: remove a bookmark with the icon on its row, variant 2а (Vraja Lila msg 5439/5440, 20.10.2026).

Rule text (Vraja Lila msg 5440, verbatim): «да, делай так» — to the plan (Purohita, from msg 5439 and the mock-up
Vraja_Lila/faili/2026.10.20_Закладки — снять значком (макет).png, frames 1 and 2а):
 - on the right of every row of «Закладки» a filled bookmark icon — the same ribbon as in the top bar, #8B6508,
   tap target ≥ 44 px;
 - a tap on it removes the bookmark: the row turns pale and stays in place, the icon is empty, the toast
   «Закладка убрана · Отменить» (the same toast as for the top-bar button); «Отменить» brings it back;
   when the toast is over the row is gone;
 - a tap on the row itself (not the icon) still goes to the place.
usage: python s56_bookmark_remove_icon.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from toc import Contents  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
CH = "arcana-procedure"
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
T0 = 1792000000000
SEED = [{"id": "b-svagata", "section": CH, "anchor": "2-svagata", "block": 0, "lang": "ru-iast", "time": T0 + 3},
        {"id": "b-gandha", "section": CH, "anchor": "11-gandha", "block": 0, "lang": "ru-iast", "time": T0 + 2},
        {"id": "b-acamana", "section": CH, "anchor": "5-acamana", "block": 0, "lang": "ru-iast", "time": T0 + 1}]
INIT = ("if (!sessionStorage.getItem('qaSeeded')) { localStorage.setItem('ap.readerHintSeen','1');"
        f"localStorage.setItem('ap.bookmarks', JSON.stringify({json.dumps({'v': 1, 'items': SEED})}));"
        "sessionStorage.setItem('qaSeeded','1'); }")
MENU = ".mobile-menu[data-open]"
TOAST = "[data-bookmark-toast]"
GOLD = "rgb(139, 101, 8)"  # #8B6508
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


def stored(pg):
    return [b["id"] for b in pg.evaluate("(JSON.parse(localStorage.getItem('ap.bookmarks') || 'null') || {items: []}).items")]


def tap(pg, loc, touch, wait=400):
    (loc.tap if touch else loc.click)()
    pg.wait_for_timeout(wait)


ROW = """(row) => { const btn = row.querySelector('[data-bookmark-remove]'); const r = row.getBoundingClientRect();
  if (!btn) return {btn: false};
  const b = btn.getBoundingClientRect(); const svg = btn.querySelector('svg'); const path = svg && svg.querySelector('path');
  const t = row.querySelector('[data-bookmark-title]'); const tr = t.getBoundingClientRect();
  return {btn: true, w: Math.round(b.width), h: Math.round(b.height), right: Math.round(r.right - b.right),
          textClear: Math.round(b.left - tr.right) >= 0, inRow: b.top >= r.top - 1 && b.bottom <= r.bottom + 1,
          fill: path ? getComputedStyle(path).fill : null, stroke: path ? getComputedStyle(path).stroke : null,
          nested: !!btn.closest('a'), opacity: (() => { let o = 1; for (let e = t; e && e !== row.parentElement; e = e.parentElement) o *= +getComputedStyle(e).opacity; return o; })(),
          faded: row.hasAttribute('data-bookmark-faded')}; }"""
ONTOP = """(sel) => { const el = document.querySelector(sel); if (!el) return false; const r = el.getBoundingClientRect();
  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!hit && el.contains(hit); }"""


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        touch = opts.get("has_touch", False)
        c = b.new_context(service_workers="block", locale="ru-RU", **opts)
        c.add_init_script(INIT)
        pg = c.new_page()
        pg.goto(f"{BASE}/ru-iast/{CH}/#1-asana", wait_until="networkidle")
        pg.wait_for_timeout(1500)
        flow = Contents(pg, qa.TocMode("default"), touch)
        flow.contents()
        tab = pg.locator(f"{MENU} [data-sidebar-tab=bookmarks]")
        if tab.count():
            tap(pg, tab, touch)
        rows = pg.locator(f"{MENU} [data-bookmark-row]")
        check(dev, "three bookmarks listed", rows.count() == 3, rows.count())
        looks = [rows.nth(i).evaluate(ROW) for i in range(rows.count())]
        check(dev, "1 every row has the icon on the right", len(looks) == 3 and all(x["btn"] and x["right"] <= 12 and x["textClear"] and x["inRow"] for x in looks), looks)
        if not all(x["btn"] for x in looks) or len(looks) != 3:
            c.close(); b.close()
            continue
        check(dev, "1 icon filled, #8B6508 (the ribbon of the top bar)", all(x["fill"] == GOLD for x in looks), [x["fill"] for x in looks])
        check(dev, "1 tap target ≥ 44 px", all(x["w"] >= 44 and x["h"] >= 44 for x in looks), [(x["w"], x["h"]) for x in looks])
        check(dev, "icon is not inside the row link (two separate targets)", not any(x["nested"] for x in looks), [x["nested"] for x in looks])

        h0 = pg.evaluate("history.length")
        url0 = pg.url
        row = pg.locator(f"{MENU} [data-bookmark-row][data-bookmark-id=b-gandha]")
        tap(pg, row.locator("[data-bookmark-remove]"), touch)
        after = row.evaluate(ROW) if row.count() else None
        check(dev, "2а tap on the icon removes the bookmark from storage", stored(pg) == ["b-svagata", "b-acamana"], stored(pg))
        check(dev, "2а the row stays in place, pale, icon empty",
              after is not None and after["faded"] and after["opacity"] < 0.8 and after["fill"] in ("none", "rgba(0, 0, 0, 0)")
              and after["stroke"] == GOLD and rows.count() == 3 and rows.nth(1).get_attribute("data-bookmark-id") == "b-gandha", after)
        ttxt = pg.locator(TOAST).inner_text() if pg.locator(TOAST).count() else ""
        check(dev, "2а toast «Закладка убрана · Отменить» (the top bar's toast)", "Закладка убрана" in ttxt and "Отменить" in ttxt, ttxt)
        check(dev, "2а the toast is on top of the open contents", pg.evaluate(ONTOP, f"{TOAST} button"))
        check(dev, "10.2 no history step, menu stays open", pg.evaluate("history.length") == h0 and pg.url == url0
              and pg.locator(MENU).count() == 1, {"h": pg.evaluate("history.length"), "url": pg.url})

        if pg.locator(f"{TOAST} button").count():
            tap(pg, pg.locator(f"{TOAST} button"), touch)
        back = row.evaluate(ROW) if row.count() else None
        check(dev, "2а «Отменить» brings it back (storage and row)",
              stored(pg) == ["b-svagata", "b-gandha", "b-acamana"] and back is not None and not back["faded"] and back["fill"] == GOLD, back)

        tap(pg, row.locator("[data-bookmark-remove]"), touch)
        pg.wait_for_timeout(4600)
        check(dev, "2а when the toast is over the row is gone",
              pg.locator(TOAST).count() == 0 and rows.count() == 2 and row.count() == 0 and stored(pg) == ["b-svagata", "b-acamana"],
              {"rows": rows.count(), "stored": stored(pg)})

        # a tap on the row itself still goes to the place
        tap(pg, rows.nth(1).locator("[data-bookmark-title]"), touch, wait=1500)
        check(dev, "a tap on the row goes to the place (5. Ачаман)", "5-acamana" in pg.url and stored(pg) == ["b-svagata", "b-acamana"], pg.url)
        c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
