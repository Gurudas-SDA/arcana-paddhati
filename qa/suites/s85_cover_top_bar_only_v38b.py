"""V38b — on the cover a tap brings out ONLY the top bar (Vraja Lila msg 1320, 22.10.2026 ~00:10; saskarnes autors,
«Стандарты» 0а).

Rule text (Vraja Lila's remark, as passed on — nodots-izpildei 22.10 00:20 п.3, verbatim):
 «на ОБЛОЖКЕ по касанию выезжает ТОЛЬКО верхняя панель, нижняя нет»
Criterion (verbatim): «касание обложки — только верхняя панель».

Checks, per device:
  A  cover: a tap on the cover shows the top bar (Содержание · Поиск · Аа) on screen;
  B  cover: the bottom bar is not on screen then (not displayed, or fully below the screen / transparent);
  C  cover: «Содержание» opened from there — still no bottom bar;
  D  a chapter page: a tap still shows both bars (the bottom bar with «‹ Назад» · «Вперёд ›» stays there).
usage: python s85_cover_top_bar_only_v38b.py <base-url>
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from toc import Contents  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
LANG = "ru-iast"
CH = "daily-deity-schedule"
results = []

# Is the bar on screen: displayed, not transparent, some of it inside the viewport.
BAR = """(sel) => { const b = document.querySelector(sel); if (!b) return {exists: false, on: false};
  const cs = getComputedStyle(b); const r = b.getBoundingClientRect();
  const inView = r.height > 0 && r.bottom > 0.5 && r.top < innerHeight - 0.5;
  return {exists: true, display: cs.display, opacity: +(+cs.opacity).toFixed(2), top: Math.round(r.top), bottom: Math.round(r.bottom),
          vh: innerHeight, on: cs.display !== 'none' && +cs.opacity > 0.05 && inView}; }"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:600]}", flush=True)


def run(browser, dev, opts):
    touch = opts.get("has_touch", False)
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true')}catch(e){}")
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    flow = Contents(pg, qa.TocMode("default"), touch)
    bar = lambda sel: pg.evaluate(BAR, sel)
    try:
        pg.goto(f"{BASE}/{LANG}/", wait_until="networkidle")
        pg.wait_for_timeout(1200)
        flow.bars()
        pg.wait_for_timeout(500)
        top, bottom = bar(".reader-bar-top"), bar(".reader-bar-bottom")
        check(dev, "A cover: a tap shows the top bar", pg.locator(".reader-chrome[data-shown]").count() == 1 and top["on"], top)
        check(dev, "B cover: the bottom bar does not come out", not bottom["on"], bottom)
        flow.contents()
        pg.wait_for_timeout(600)
        bottom = bar(".reader-bar-bottom")
        check(dev, "C cover + «Содержание»: no bottom bar", pg.locator(".mobile-menu[data-open]").count() == 1 and not bottom["on"], bottom)

        pg.goto(f"{BASE}/{LANG}/{CH}/", wait_until="networkidle")
        pg.wait_for_timeout(1200)
        flow.bars()
        pg.wait_for_timeout(500)
        top, bottom = bar(".reader-bar-top"), bar(".reader-bar-bottom")
        check(dev, "D chapter page: a tap shows both bars (bottom with «‹ Назад» · «Вперёд ›»)",
              top["on"] and bottom["on"] and pg.locator("[data-reader-nav]").count() >= 1, {"top": top, "bottom": bottom})
        check(dev, "no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(dev, "scenario ran", False, str(error)[:300])
    finally:
        c.close()


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "pixel7", "desktop"]):
        b = getattr(p, eng).launch()
        run(b, dev, opts)
        b.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
