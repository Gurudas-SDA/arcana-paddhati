"""V98, Vraja Lila msg 2967/2969 (15.11) — the «Аа» panel's last button (rotate-cw icon, below the divider; V97 «Сбросить настройки»)
changes its FUNCTION: «Свернуть содержание».
Vraja's criteria: (1) the button resets NOTHING — theme, size, layout, switches, language stay as they are;
(2) a tap folds every opened chapter / section / subsection in the contents (as at the first opening);
(3) the reader goes to the cover; (4) the name: RU «Свернуть содержание», EN «Collapse contents»; (5) icon rotate-cw and place unchanged.
# tehniskais slieksnis Lipikāra, nav S noteikums: settle 2500 ms after the click.
usage: python s_v98_collapse_contents.py <base-url>
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
  return {theme: ls('ap.readerTheme'), size: ls('ap.readerSize'), layout: ls('ap.readerLayout'),
    htmlTheme: document.documentElement.getAttribute('data-reader-theme'),
    trOn: sw ? sw.hasAttribute('data-on') : null, path: location.pathname,
    icon: btn ? !!btn.querySelector('svg.lucide-rotate-cw path[d^="M21 12a9 9 0 1 1"]') : false,
    iconPx: btn ? btn.querySelector('svg').getBoundingClientRect().width : null,
    label: btn ? btn.innerText.trim() : null}; }"""

OPEN_COUNT = "() => document.querySelectorAll('.mobile-menu[data-open] [aria-expanded=\"true\"]').length"


def reload(pg, layout):
    pg.reload(wait_until="networkidle")
    if layout == "scroll":
        pg.wait_for_selector("[data-continuous-book]", state="attached", timeout=30000)
        qa.wait_for_book_chapter(pg, CHAP)
    pg.wait_for_timeout(1000)


def open_panel(pg):
    pg.evaluate("document.querySelector('[data-reader-action=\"aa\"]').click()")
    pg.wait_for_selector(".reader-panel", timeout=10000)
    pg.wait_for_timeout(500)


def open_menu(pg):
    for _ in range(3):
        pg.evaluate("document.querySelector('[data-reader-action=\"contents\"]').click()")
        pg.wait_for_timeout(800)
        if pg.evaluate("!!document.querySelector('.mobile-menu[data-open]')"):
            return True
    return False


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
            check(dev, f"{layout}: label RU «Свернуть содержание», icon rotate-cw 18 px",
                  before["label"] == "Свернуть содержание" and before["icon"] and before["iconPx"] == 18, before)
            # open the contents and unfold every group by hand (two taps per row), so that something is opened
            reload(pg, layout)
            menu_ok = open_menu(pg)
            for _ in range(2):
                pg.evaluate("document.querySelectorAll('.mobile-menu[data-open] [data-toc-group-row]').forEach(e => e.click())")
                pg.wait_for_timeout(500)
            opened = pg.evaluate(f"({OPEN_COUNT})()")
            check(dev, f"{layout}: before — contents have opened rows", menu_ok and opened >= 1, {"menu": menu_ok, "opened": opened})
            reload(pg, layout)
            open_panel(pg)
            pg.evaluate("document.querySelector('.reader-reset').click()")
            pg.wait_for_timeout(2500)
            after = pg.evaluate(f"({STATE})()")
            at_cover = after["path"].rstrip("/").endswith(f"/{LANG}")
            check(dev, f"{layout}: the reader is on the cover", at_cover, after)
            check(dev, f"{layout}: nothing reset — theme night, size 1.2, layout kept, language kept",
                  after["theme"] == "night" and after["size"] == "1.2" and after["layout"] == layout and f"/{LANG}" in after["path"], after)
            tr_ls = pg.evaluate("Object.keys(localStorage).filter(k => /transl/i.test(k)).map(k => [k, localStorage.getItem(k)])")
            check(dev, f"{layout}: «show all translations» switch stays on", any(v == "1" for _, v in tr_ls), tr_ls)
            menu_ok = open_menu(pg)
            left = pg.evaluate(f"({OPEN_COUNT})()")
            check(dev, f"{layout}: contents folded — no opened part / chapter / section", menu_ok and left == 0, {"menu": menu_ok, "opened": left})
            c.close()
        b.close()
    b = getattr(p, DEVICES[0][1]).launch()
    c = b.new_context(service_workers="block", locale="en-US", **DEVICES[0][2])
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');}catch(e){}")
    pg = c.new_page()
    pg.goto(f"{BASE}/{CHAP}/", wait_until="networkidle")
    pg.wait_for_timeout(1000)
    open_panel(pg)
    en = pg.evaluate(f"({STATE})()")
    check("pixel7", "EN label «Collapse contents»", en["label"] == "Collapse contents", en)
    b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
