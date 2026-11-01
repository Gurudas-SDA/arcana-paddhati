"""V62 — the search field keeps its corner radius in focus (Vraja Lila msg 7208, 01.11.2026, 2 iPhone photos).

Vraja Lila (verbatim): «строка поиска при нажатии не должна менять радиус углов»
(photos: «Search sections» field, corners rounded without focus, almost square after a tap, keyboard open).
Checks, per device x theme (white, sepia, night): the corner radii (all 4) of the search field in «Содержание» and
of the bookmark name field are the SAME without focus, after keyboard focus (:focus-visible), and after a tap.
Vraja Lila msg 7210 (verbatim): «но рамка становится толще — с этим всё окей» - the thicker frame (inset box-shadow) in focus stays.
usage: python s131_search_radius_focus_v62.py <base-url>
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
LANG = "ru-iast"
CH = "daily-duties-brahma-muhurta"
SEED = [{"id": "b-ff", "section": "arcana-procedure", "anchor": "2-svagata", "block": 0, "lang": "ru-iast", "time": 1792000000000, "name": "Утро"}]
MENU = ".mobile-menu[data-open]"
SHOTS = os.environ.get("V62_SHOTS")
results = []
RAD = """(el) => { const s = getComputedStyle(el); return [s.borderTopLeftRadius, s.borderTopRightRadius, s.borderBottomRightRadius, s.borderBottomLeftRadius].join(' '); }"""


def check(tag, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {tag} {name} {json.dumps(evidence, ensure_ascii=False)[:600]}", flush=True)


def probe(pg, tag, what, sel, shot=None):
    loc = pg.locator(sel).first
    pg.evaluate("() => document.activeElement && document.activeElement.blur && document.activeElement.blur()")
    pg.wait_for_timeout(250)
    r0 = loc.evaluate(RAD)
    pg.keyboard.press("Shift")
    loc.evaluate("e => e.focus({preventScroll: true})")
    pg.wait_for_timeout(300)
    r1 = loc.evaluate(RAD)
    bs = loc.evaluate("e => getComputedStyle(e).boxShadow")
    if shot:
        pg.screenshot(path=shot)
    pg.evaluate("() => document.activeElement && document.activeElement.blur && document.activeElement.blur()")
    pg.wait_for_timeout(250)
    loc.evaluate("e => e.click()")
    pg.wait_for_timeout(300)
    r2 = loc.evaluate(RAD)
    check(tag, f"{what}: corner radius in focus = without focus", r0 == r1 == r2 and r0.split()[0] != "0px",
          {"none": r0, "focus": r1, "tap": r2})
    check(tag, f"{what}: the thicker frame in focus stays (Vraja Lila msg 7210)",
          bs != "none" and "inset" in bs, {"box-shadow": bs})


def run(browser, dev, opts, theme):
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    init = ("if (!sessionStorage.getItem('qaSeeded')) { localStorage.setItem('ap.readerHintSeen','1');"
            "localStorage.setItem('installDismissed','true');"
            f"localStorage.setItem('ap.bookmarks', JSON.stringify({json.dumps({'v': 1, 'items': SEED}, ensure_ascii=False)}));"
            "sessionStorage.setItem('qaSeeded','1'); }")
    init += ("localStorage.removeItem('ap.readerTheme');" if theme == "white" else f"localStorage.setItem('ap.readerTheme','{theme}');")
    c.add_init_script(init)
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    tag = f"{dev}/{theme}"
    try:
        pg.goto(f"{BASE}/{LANG}/{CH}/", wait_until="networkidle")
        pg.wait_for_timeout(1500)
        if not pg.locator(".reader-chrome[data-shown]").count():
            pg.mouse.click(200, 430)
            pg.wait_for_timeout(500)
        pg.locator("[data-reader-action=contents]").evaluate("b => b.click()")
        pg.wait_for_timeout(700)
        shot = None
        if SHOTS and theme == "white":
            os.makedirs(SHOTS, exist_ok=True)
            shot = os.path.join(SHOTS, f"{dev}_{os.environ.get('V62_TAG', 'x')}.png")
        probe(pg, tag, "search field in «Содержание»", f"{MENU} .search-input", shot)
        tab = pg.locator(f"{MENU} [data-sidebar-tab=bookmarks]")
        if tab.count():
            tab.evaluate("b => b.click()")
            pg.wait_for_timeout(400)
            pg.locator(f"{MENU} [data-bookmark-id=b-ff] [data-bookmark-rename]").evaluate("b => b.click()")
            pg.wait_for_timeout(500)
            probe(pg, tag, "bookmark name field", "[data-bookmark-dialog-input]")
        check(tag, "no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(tag, "scenario ran", False, str(error)[:300])
    finally:
        c.close()


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "desktop"]):
        b = getattr(p, eng).launch()
        for theme in ("white", "sepia", "night"):
            run(b, dev, opts, theme)
        b.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
