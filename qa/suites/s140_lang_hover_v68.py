"""V68 — Vraja Lila msg 7392 (03.11), burtiski: «на компьютере при переключении языков on hover язык окрашивается
(подсвечивается) так же как и выделенный язык. нужно чтобы на hover лишь текст названия языка становился bold, а подсветка
была бы … какой из языков выбран». Msg 7393: izvēlētā (English) — gaišais smilškrāsas fons + zelta ķeksis; neizvēlētā
(Русский) — balta, bez fona; hover uz neizvēlētās — tikai bold, fons paliek balts. Rāmja nav (ekrānuzņēmuma rīka artefakts).

Checks (the «Аа» panel -> language list):
  desktop + mac-safari (pointer:fine):
    a) the mouse over the unchosen language: its fill does NOT change (= the same as before the hover, no fill)
    b) ... and is not the chosen row's fill
    c) ... its font-weight becomes bold (>= 600) and was lower before the hover
    d) the chosen language keeps the fill (not transparent) + the ✓ — also while the mouse is over the other row
  pixel7 + iphone14 (pointer:coarse): nothing changes — the rule does not apply (matchMedia false), the unchosen row at rest
    has no fill and normal weight.
Frames: env QA_SHOTS=<dir> -> <dir>/<device>_hover.png
usage: python s140_lang_hover_v68.py <base-url>
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
SHOTS = os.environ.get("QA_SHOTS")
PAGE = "offering-bhoga"
results = []


def check(dev, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else info}", flush=True)


ROW = """(code) => { const e = document.querySelector('[role=listbox] [role=option][data-lang="' + code + '"]');
  const cs = getComputedStyle(e); return {bg: cs.backgroundColor, w: parseInt(cs.fontWeight, 10), check: !!e.querySelector('[data-lang-check]')}; }"""


def open_list(pg, touch):
    if pg.locator(".reader-chrome[data-shown]").count() == 0:
        pt = pg.evaluate("""() => { const a = document.querySelector('.app-main article').getBoundingClientRect();
                                     return {x: a.left + 6, y: innerHeight / 2}; }""")
        (pg.touchscreen.tap if touch else pg.mouse.click)(pt["x"], pt["y"])
        pg.wait_for_timeout(400)
    aa = pg.locator("[data-reader-action=aa]")
    aa.tap() if touch else aa.click()
    pg.wait_for_timeout(600)
    lt = pg.locator(".reader-panel [data-lang-trigger]")
    lt.tap() if touch else lt.click()
    pg.wait_for_timeout(500)


def transparent(bg):
    return bg in ("rgba(0, 0, 0, 0)", "transparent")


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["desktop", "mac-safari", "pixel7", "iphone14"]):
        touch = opts.get("has_touch", False)
        br = getattr(p, eng).launch()
        ctx = br.new_context(service_workers="block", **opts)
        ctx.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
        pg = ctx.new_page()
        pg.goto(f"{BASE}/{PAGE}/", wait_until="networkidle")  # English = chosen
        pg.wait_for_timeout(1000)
        open_list(pg, touch)
        sel = pg.evaluate(ROW, "en")
        rest = pg.evaluate(ROW, "ru-iast")
        if not touch:
            box = pg.locator("[role=listbox] [data-lang=ru-iast]").bounding_box()
            pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            pg.wait_for_timeout(300)
            hov = pg.evaluate(ROW, "ru-iast")
            sel2 = pg.evaluate(ROW, "en")
            check(dev, f"a hover over the unchosen language: fill unchanged ({rest['bg']} -> {hov['bg']})", hov["bg"] == rest["bg"], hov)
            check(dev, f"b hover fill is not the chosen row's fill ({hov['bg']} vs {sel['bg']})", hov["bg"] != sel["bg"], hov)
            check(dev, f"c hover: font-weight {rest['w']} -> {hov['w']} (bold >= 600)", hov["w"] >= 600 and rest["w"] < 600, (rest, hov))
            check(dev, "d chosen language keeps fill + ✓ while the mouse is over the other row",
                  not transparent(sel2["bg"]) and sel2["bg"] == sel["bg"] and sel2["check"], sel2)
            if SHOTS:
                os.makedirs(SHOTS, exist_ok=True)
                pg.screenshot(path=os.path.join(SHOTS, f"{dev}_hover.png"))
        else:
            fine = pg.evaluate("() => matchMedia('(hover: hover) and (pointer: fine)').matches")
            check(dev, "e coarse pointer: the hover rule does not apply", not fine)
            check(dev, f"f unchosen row at rest: no fill, normal weight ({rest['bg']}, {rest['w']})",
                  transparent(rest["bg"]) and rest["w"] < 600, rest)
        ctx.close()
        br.close()
print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
