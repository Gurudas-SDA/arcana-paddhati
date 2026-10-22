"""V44 — the bars' background is never see-through while they slide (Vraja Lila 22.10.2026; saskarnes autors, «Стандарты» 0а).

Vraja Lila (msg 6163–6168, screen recording on iPhone, en, «Maṅgalācaraṇa»): while the bottom bar slides out / back
its background is half transparent — the next verse shows through «‹ Back / Forward ›» and the line
«Maṅgalācaraṇa · 0 %». Asked: the panel's background opaque during the whole animation (transform only, no
opacity on the background; a fade, if any, only for the content); the same for the top bar and every such panel —
one master element in the design system.
Criteria (register V44): on iPhone, in no frame of sliding out / back does the book text show through a bar; both bars.

Before (live 68e9192): .reader-bar had `opacity: 0` hidden and `transition: transform 220ms, opacity 200ms` — every
frame of the movement had 0 < opacity < 1 (the whole bar, background included, see-through).
 # tehniskais slieksnis Lipikāra, nav S noteikums: frames read every animation frame (~16 ms) for 700 ms; «opaque» =
 #   effective opacity (the bar × its ancestors) ≥ 0.99 and background alpha = 1 in every frame in which any part of
 #   the bar is on screen.

Checks, per device:
  A  top / bottom bar showing and hiding (tap on the page): every frame with the bar on screen — opaque;
     the bar still moves (transform), so it is a slide, not a pop;
  B  «Содержание» opening and closing: the panel opaque in every frame; the bottom bar coming back after closing opaque.
usage: python s96_bars_opaque_while_moving_v44.py <base-url>
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
results = []

REC = """(ms) => { window.__f = []; const t0 = performance.now();
  const eff = (e) => { let o = 1; for (let x = e; x && x.nodeType === 1; x = x.parentElement) o *= +getComputedStyle(x).opacity; return o; };
  const alpha = (bg) => { const m = bg.match(/rgba?\\(([^)]*)\\)/); if (!m) return bg === 'transparent' ? 0 : 1;
    const p = m[1].split(/[ ,\\/]+/).filter(Boolean); return p.length > 3 ? +p[3] : 1; };
  const g = (s) => { const e = document.querySelector(s); if (!e) return null; const c = getComputedStyle(e);
    const r = e.getBoundingClientRect(); const on = c.display !== 'none' && r.height > 0 && r.bottom > 0.5 && r.top < innerHeight - 0.5
      && r.right > 0.5 && r.left < innerWidth - 0.5;
    return [Math.round(r.top), +eff(e).toFixed(3), alpha(c.backgroundColor), on ? 1 : 0, Math.round(r.left)]; };
  const f = () => { window.__f.push([Math.round(performance.now() - t0), g('.reader-bar-top'), g('.reader-bar-bottom'),
      g('.mobile-menu > .sidebar-transition')]);
    if (performance.now() - t0 < ms) requestAnimationFrame(f); }; requestAnimationFrame(f); }"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:900]}", flush=True)


def rec(pg, action, ms=700):
    pg.evaluate(f"({REC})({ms})")
    action()
    pg.wait_for_timeout(ms + 200)
    return pg.evaluate("window.__f")


def shown(pg):
    return pg.evaluate("!!document.querySelector('.reader-chrome[data-shown]')")


def tap_page(pg, touch):
    (pg.touchscreen.tap if touch else pg.mouse.click)(200, 430)


def see_through(fr, k):
    """Frames (t, opacity, bg alpha) in which element k is on screen and not opaque."""
    return [[f[0], f[k][1], f[k][2]] for f in fr if f[k] and f[k][3] and (f[k][1] < 0.99 or f[k][2] < 1)]


def bars_case(pg, dev, touch):
    if shown(pg):
        tap_page(pg, touch)
        pg.wait_for_timeout(700)
    fr_in = rec(pg, lambda: tap_page(pg, touch))
    fr_out = rec(pg, lambda: tap_page(pg, touch))
    for k, name in ((1, "top"), (2, "bottom")):
        for fr, way in ((fr_in, "showing"), (fr_out, "hiding")):
            bad = see_through(fr, k)
            ys = {f[k][0] for f in fr if f[k] and f[k][3]}
            onscreen = sum(1 for f in fr if f[k] and f[k][3])
            check(dev, f"A {name} bar {way}: opaque in every frame on screen (book text never shows through), and it slides",
                  not bad and len(ys) > 2 and onscreen > 0,
                  {"seeThrough[t,opacity,bgAlpha]": bad[:8], "positions": len(ys), "framesOnScreen": onscreen})


def menu_case(pg, dev, touch):
    if not shown(pg):
        tap_page(pg, touch)
        pg.wait_for_timeout(600)
    fr_open = rec(pg, lambda: pg.locator("[data-reader-action=contents]").evaluate("b => b.click()"), 600)
    pg.wait_for_timeout(300)
    fr_close = rec(pg, lambda: pg.keyboard.press("Escape"), 900)
    bad_open, bad_close = see_through(fr_open, 3), see_through(fr_close, 3)
    xs = {f[3][4] for f in fr_open + fr_close if f[3] and f[3][3]}
    check(dev, "B «Содержание» opening and closing: the panel opaque in every frame, and it slides",
          not bad_open and not bad_close and len(xs) > 2, {"open": bad_open[:6], "close": bad_close[:6], "positions": len(xs)})
    bad_bar = see_through(fr_close, 2)
    check(dev, "B the bottom bar coming back after «Содержание» closes: opaque in every frame", not bad_bar, bad_bar[:8])


def run(browser, dev, opts, lang, ch):
    touch = opts.get("has_touch", False)
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true')}catch(e){}")
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    tag = f"{dev} {lang or 'en'}"
    try:
        pg.goto(f"{BASE}/{lang + '/' if lang else ''}{ch}/", wait_until="networkidle")
        pg.wait_for_timeout(2000)
        qa.scroll_chapter(pg, 0.3)            # not the chapter's start (the bars stay there)
        pg.wait_for_timeout(1500)
        bars_case(pg, tag, touch)
        menu_case(pg, tag, touch)
        check(tag, "no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(tag, "scenario ran", False, str(error)[:300])
    finally:
        c.close()


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "pixel7", "desktop"]):
        b = getattr(p, eng).launch()
        run(b, dev, opts, "", "mangalacarana")   # Vraja Lila's recording: en, «Maṅgalācaraṇa»
        if dev == "iphone14":
            run(b, dev, opts, "ru-iast", "arcana-procedure")
        b.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
