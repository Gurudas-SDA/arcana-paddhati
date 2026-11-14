"""V97, Vraja Lila msg 2947/2949/8231/8232 — сброс настроек
«Сбросить настройки» in the «Аа» panel (compact row, rotate-cw icon, Vraja msg 8231-8233): theme -> white, size -> 100 %,
layout -> «Листать», «Показывать все переводы» off, opened verses folded; the language does not change; the reader stays in
the same chapter/section (URL) after the reset — in «Страницы» and in «Лента».
# tehniskais slieksnis Lipikāra, nav S noteikums: settle 1500 ms after the click.
usage: python s_v97_reset_settings.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["pixel7"])
LANG = "ru-iast"
CHAP = "mangala-arati-songs"
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:900]}", flush=True)


STATE = """() => { const ls = k => localStorage.getItem(k);
  const sw = document.querySelector('[data-reader-switch="tr"] .reader-switch-track');
  const btn = document.querySelector('.reader-reset');
  const sec = document.querySelector('[data-reader-current]');
  return {theme: ls('ap.readerTheme'), size: ls('ap.readerSize'), layout: ls('ap.readerLayout'),
    htmlTheme: document.documentElement.getAttribute('data-reader-theme'),
    trOn: sw ? sw.hasAttribute('data-on') : null, path: location.pathname,
    section: sec ? (sec.dataset.bookSection || sec.id || null) : null,
    icon: btn ? !!btn.querySelector('svg.lucide-rotate-cw path[d^="M21 12a9 9 0 1 1"]') : false,
    iconPx: btn ? btn.querySelector('svg').getBoundingClientRect().width : null,
    rvInUrl: location.search.includes('rv=')}; }"""


def open_panel(pg):
    pg.evaluate("document.querySelector('[data-reader-action=\"aa\"]').click()")
    pg.wait_for_selector(".reader-panel", timeout=10000)
    pg.wait_for_timeout(500)


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        for layout in ("page", "scroll"):
            c = b.new_context(service_workers="block", locale="ru-RU", **opts)
            c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');"
                              "localStorage.setItem('ap.readerTheme','night');localStorage.setItem('ap.readerSize','1.2');"
                              f"localStorage.setItem('ap.readerLayout','{layout}');}}catch(e){{}}")
            pg = c.new_page()
            pg.goto(f"{BASE}/{LANG}/{CHAP}/", wait_until="networkidle")
            if layout == "scroll":
                pg.wait_for_selector("[data-continuous-book]", state="attached", timeout=30000)
                qa.wait_for_book_chapter(pg, CHAP)
            pg.wait_for_timeout(1000)
            open_panel(pg)
            pg.evaluate("document.querySelector('[data-reader-switch=\"tr\"]').click()")
            pg.wait_for_timeout(500)
            before = pg.evaluate(f"({STATE})()")
            check(dev, f"{layout}: before — night, 1.2, tr on", before["theme"] == "night" and before["size"] == "1.2" and before["trOn"] is True, before)
            pg.evaluate("document.querySelector('.reader-reset').click()")
            pg.wait_for_timeout(2500)
            if not pg.query_selector(".reader-reset"):
                open_panel(pg)
            after = pg.evaluate(f"({STATE})()")
            check(dev, f"{layout}: theme white, size 1, layout page, tr off",
                  after["theme"] == "white" and after["htmlTheme"] in (None, "white") and after["size"] == "1"
                  and after["layout"] == "page" and after["trOn"] is False, after)
            same = after["path"] == before["path"] and not after["rvInUrl"] and (after["section"] in (None, before["section"], CHAP))
            check(dev, f"{layout}: stays in the same chapter/section, language unchanged", same and f"/{LANG}/" in after["path"], {"b": before, "a": after})
            check(dev, f"{layout}: rotate-cw icon, 18 px like the bar icons", after["icon"] and after["iconPx"] == 18, after)
            c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
