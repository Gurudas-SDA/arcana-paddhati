"""«Содержание» never stays half-way out (Vraja Lila, 20.10.2026, msg 5605 — iPhone screenshot: panel half off-screen).

After any sequence of taps — closing while it is still sliding out, opening again while it slides back, quick
repeated taps, the screen turned (viewport width/height swapped) in the middle — the panel ends either fully out
(left edge at 0, dimming fully on, the menu open) or gone from the page. Never in between, never a «closing» panel
left behind; and while the panel is on screen the bottom bar is never under the dimming (msg 5606).
# tehniskais slieksnis Lipikāra, nav S noteikums: settled = checked 900 ms after the last tap; left edge ±0.5 px;
#   dimming opacity ≥ 0.99; taps 40–90 ms apart.
usage: python s67_menu_never_halfway.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
PAGE = "vigraha-tattva"
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


STATE = """() => { const ms = [...document.querySelectorAll('.mobile-menu')];
  const m = ms[0], a = m && m.querySelector(':scope > .sidebar-transition'), d = m && m.querySelector(':scope > .sidebar-backdrop');
  const bb = document.querySelector('.reader-bar-bottom');
  return {menus: ms.length, open: !!(m && m.hasAttribute('data-open')), closing: !!(m && m.hasAttribute('data-closing')),
    left: a ? +a.getBoundingClientRect().left.toFixed(1) : null, dim: d ? +(+getComputedStyle(d).opacity).toFixed(3) : null,
    barZ: +getComputedStyle(bb).zIndex || 0, menuZ: m ? +getComputedStyle(m).zIndex || 0 : 0}; }"""
OPEN = "document.querySelector('[data-reader-action=contents]').click()"
CLOSE = "(() => { const d = document.querySelector('.mobile-menu[data-open] > .sidebar-backdrop'); if (d) d.click(); })()"


def settled_ok(s):
    if s["menus"] == 0:
        return True
    return (s["menus"] == 1 and s["open"] and not s["closing"] and s["left"] is not None and abs(s["left"]) <= 0.5
            and s["dim"] is not None and s["dim"] >= 0.99 and s["barZ"] > s["menuZ"])


def show_bars(pg):
    for _ in range(3):
        if pg.evaluate("!!document.querySelector('.reader-chrome[data-shown]')"):
            return
        pg.mouse.click(200, 430)
        pg.wait_for_timeout(450)


def run(pg, steps, expect):
    """steps: [(js, wait ms)]; expect: 'open' / 'gone' / None (either, but clean)."""
    show_bars(pg)
    for js, wait in steps:
        if js == "ROTATE":
            v = pg.viewport_size
            pg.set_viewport_size({"width": v["height"], "height": v["width"]})
        else:
            pg.evaluate(js)
        pg.wait_for_timeout(wait)
    pg.wait_for_timeout(900)
    s = pg.evaluate(f"({STATE})()")
    ok = settled_ok(s) and (expect is None or (expect == "open") == (s["menus"] == 1))
    return ok, s


def reset(pg):
    pg.evaluate(CLOSE)
    pg.wait_for_timeout(700)
    v = pg.viewport_size
    if v["width"] > v["height"] and v["width"] < 1000:
        pg.set_viewport_size({"width": v["height"], "height": v["width"]})
        pg.wait_for_timeout(300)


CASES = [
    ("closed while still sliding out", [(OPEN, 60), (CLOSE, 0)], "gone"),
    ("opened again while sliding back", [(OPEN, 450), (CLOSE, 90), (OPEN, 0)], "open"),
    ("opened again at once after closing (before the slide-back starts)", [(OPEN, 450), (CLOSE, 20), (OPEN, 0)], "open"),
    ("quick repeated taps (open/close ×3)", [(OPEN, 40), (CLOSE, 40), (OPEN, 40), (CLOSE, 40), (OPEN, 40), (CLOSE, 0)], "gone"),
    ("screen turned while sliding out", [(OPEN, 70), ("ROTATE", 0)], "open"),
    ("screen turned while sliding back", [(OPEN, 450), (CLOSE, 80), ("ROTATE", 0)], "gone"),
]

with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        c = b.new_context(service_workers="block", locale="ru-RU", **opts)
        c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');")
        pg = c.new_page()
        pg.goto(f"{BASE}/ru-iast/{PAGE}/", wait_until="networkidle")
        pg.wait_for_timeout(900)
        for name, steps, expect in CASES:
            if "ROTATE" in [s[0] for s in steps] and dev == "desktop":
                continue
            ok, s = run(pg, steps, expect)
            check(dev, f"{name}: ends fully {'out' if expect == 'open' else 'gone'}, never half-way, bottom bar above the dimming", ok, s)
            reset(pg)
        c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
