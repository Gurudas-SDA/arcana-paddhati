"""«Закладки»: the bookmark of the place being read is highlighted like the current row in «Содержание»
(Vraja Lila msg 5436, 20.10.2026).

Rule text (Vraja Lila msg 5436, verbatim):
 «если какая-то закладка выбрана, она должна быть „подсвечена" так же, как подсвечены главы в Contents»
Task (Purohita, from the screenshot: reading 2.9, the «2.9 …» bookmark not highlighted):
 - the bookmark on the place being read (same subsection; no subsection — the chapter) is highlighted with
   the SAME look as the current row in «Содержание» (background, left bar, text colour/weight; rule 9.2 — one sign);
 - several bookmarks on that place — the newest one is highlighted;  # tehniskais lēmums Lipikāra, nav S noteikums
 - opening the tab brings the highlighted row into view, as «Содержание» does (9.12).
usage: python s55_bookmark_lit.py <base-url>
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
HERE = "11-gandha"
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
# Other places (newer bookmarks) so the one being read sits at the very bottom of a long list.
OTHERS = [("daily-deity-schedule", a) for a in ("preparations", "waking-the-lord", "washing-mouth")] + \
         [("worship-sixteen-articles", a) for a in ("required-paraphernalia", "asana-sthapana", "patra-sthapana")] + \
         [(CH, a) for a in ("1-asana", "2-svagata", "3-padya")] + \
         [("vigraha-tattva", a) for a in ("vigraha-not-idol", "vigraha-sac-cid-ananda", "vigraha-fourth-form")] + \
         [("gaudiya-emblem", a) for a in ("emblem-gaudiya-matha", "emblem-centre", "emblem-mahaprabhu-guru")] + \
         [("daily-duties-brahma-muhurta", a) for a in ("morning-prayers", "taking-bath", "tirtha-avahana")] + \
         [("introduction", None), ("parampara", None)]
T0 = 1792000000000
SEED = [{"id": f"o{i}", "section": s, "anchor": a, "block": 0, "lang": "ru-iast", "time": T0 + 1000 + i}
        for i, (s, a) in enumerate(OTHERS)]
SEED += [{"id": "here-new", "section": CH, "anchor": HERE, "block": 0, "lang": "ru-iast", "time": T0 + 2},
         {"id": "here-old", "section": CH, "anchor": HERE, "block": 0, "lang": "ru-iast", "time": T0 + 1}]
INIT = ("localStorage.setItem('ap.readerHintSeen','1');"
        f"localStorage.setItem('ap.bookmarks', JSON.stringify({json.dumps({'v': 1, 'items': SEED})}));")

MENU = ".mobile-menu[data-open]"
LOOK = """(el) => { const s = getComputedStyle(el); const t = el.matches('[data-bookmark-row]')
    ? el.querySelector('[data-bookmark-title]') : (el.querySelector('span:not([aria-hidden])') || el);
  const ts = getComputedStyle(t || el);
  return {bg: s.backgroundColor, bar: s.borderLeftColor, barW: s.borderLeftWidth, barS: s.borderLeftStyle,
          color: ts.color, weight: ts.fontWeight}; }"""
INVIEW = """(el) => { const box = el.closest('[data-bookmarks-list]'); if (!box) return {ok: false};
  const n = box.getBoundingClientRect(), r = el.getBoundingClientRect();
  return {ok: r.top >= n.top - 1 && r.bottom <= n.bottom + 1, top: Math.round(r.top), bottom: Math.round(r.bottom),
          listTop: Math.round(n.top), listBottom: Math.round(n.bottom), scrolled: box.scrollTop}; }"""
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


def tap(pg, loc, touch):
    (loc.tap if touch else loc.click)()
    pg.wait_for_timeout(400)


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        touch = opts.get("has_touch", False)
        c = b.new_context(service_workers="block", locale="ru-RU", **opts)
        c.add_init_script(f"if (!sessionStorage.getItem('qaSeeded')) {{ {INIT} sessionStorage.setItem('qaSeeded','1'); }}")
        pg = c.new_page()
        pg.goto(f"{BASE}/ru-iast/{CH}/#{HERE}", wait_until="networkidle")
        pg.wait_for_timeout(1500)
        flow = Contents(pg, qa.TocMode("default"), touch)
        flow.contents()
        toc_lit = pg.locator(f"{MENU} [data-toc-lit]")
        toc_look = toc_lit.first.evaluate(LOOK) if toc_lit.count() else None
        check(dev, "«Содержание» marks the place being read (11. Гандха)", toc_lit.count() == 1 and "Гандха" in toc_lit.first.inner_text(),
              toc_lit.first.inner_text() if toc_lit.count() else "")

        tab = pg.locator(f"{MENU} [data-sidebar-tab=bookmarks]")
        if tab.count():
            tap(pg, tab, touch)
        pg.wait_for_timeout(500)
        rows = pg.locator(f"{MENU} [data-bookmark-row]")
        lit = pg.locator(f"{MENU} [data-bookmark-row][data-bookmark-lit]")
        check(dev, "list shows all bookmarks", rows.count() == len(SEED), rows.count())
        check(dev, "5436 exactly one bookmark highlighted — the place being read (11. Гандха)",
              lit.count() == 1 and "Гандха" in lit.first.inner_text(), lit.count())
        if lit.count() != 1:
            c.close(); b.close()
            continue
        check(dev, "several on the same place — the newest one is highlighted", lit.first.get_attribute("data-bookmark-id") == "here-new",
              lit.first.get_attribute("data-bookmark-id"))
        bm_look = lit.first.evaluate(LOOK)
        check(dev, "9.2 one sign: same background, left bar, text colour and weight as «Содержание»",
              toc_look is not None and bm_look == toc_look, {"toc": toc_look, "bookmark": bm_look})
        plain = rows.nth(0).evaluate(LOOK)
        check(dev, "other bookmarks are not highlighted", plain["bg"] != bm_look["bg"] and plain["bar"] != bm_look["bar"], plain)
        x_lit = lit.first.locator("[data-bookmark-title]").evaluate("e => Math.round(e.getBoundingClientRect().left)")
        x_plain = rows.nth(0).locator("[data-bookmark-title]").evaluate("e => Math.round(e.getBoundingClientRect().left)")
        check(dev, "text of the highlighted row does not move sideways", x_lit == x_plain, {"lit": x_lit, "plain": x_plain})
        view = lit.first.evaluate(INVIEW)
        check(dev, "9.12 opening the tab brings the highlighted bookmark into view", view.get("ok"), view)
        c.close()

        # a place without a bookmark: nothing is highlighted
        c = b.new_context(service_workers="block", locale="ru-RU", **opts)
        c.add_init_script(f"if (!sessionStorage.getItem('qaSeeded')) {{ {INIT} sessionStorage.setItem('qaSeeded','1'); }}")
        pg = c.new_page()
        pg.goto(f"{BASE}/ru-iast/{CH}/#16-pranama", wait_until="networkidle")
        pg.wait_for_timeout(1500)
        flow = Contents(pg, qa.TocMode("default"), touch)
        flow.contents()
        tab = pg.locator(f"{MENU} [data-sidebar-tab=bookmarks]")
        if tab.count():
            tap(pg, tab, touch)
        n = pg.locator(f"{MENU} [data-bookmark-row]").count()
        check(dev, "no bookmark on the place being read — none highlighted",
              n == len(SEED) and pg.locator(f"{MENU} [data-bookmark-row][data-bookmark-lit]").count() == 0, n)
        c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
