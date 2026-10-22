"""V43 p.3 — panels close as smoothly as they open (Vraja Lila 22.10.2026; saskarnes autors, «Стандарты» 0а).

Vraja Lila's words (verbatim): «при клике панели выдвигаются с хорошей плавностью ease, но при повторном клике
задвигаются обратно дёргано и мерцают — исправь (уже говорили об этом)».

Measured on the live book (22.10, before): closing «Содержание» (the dimming, Esc) keeps the page busy 150–250 ms (the
history step back); the panel was removed by a timer counted from the START of closing, so its 220 ms slide-back ran
only 25 ms (iPhone 14) / 66 ms (Pixel 7) and the panel vanished halfway; the slide-back was the opening played in
reverse (the ease reversed too: slow start, abrupt end).
 # tehniskais slieksnis Lipikāra, nav S noteikums: frames read every animation frame (~16 ms) for 900 ms; a step
 #   against the direction > 0.5 px (bars) / 0.5 % (panel) = a jerk; «finished» = the closing animation's
 #   animationend of the closing animations before the panel leaves the DOM, ≥ 150 ms after their animationstart
 #   (events arrive late on a busy page).

Checks, per device:
  A  top / bottom bar (tap on the page, tap again): hiding uses the same property, duration and ease as showing;
     every frame moves one way (no step back), opacity one way, never display:none half way;
  B  «Содержание» closed by the dimming and by Esc: the slide-back is its own animation played forwards with the
     opening's duration and ease (ap-menu-out, normal, ease, 220 ms);
  C  the panel leaves the DOM only after its slide-back has FINISHED (no vanishing half way), the dimming too;
  D  the frames of the slide-back move one way (no step back, no jump back in);
  E  the bottom bar comes back once, smoothly, and does not go down again (no flicker) after closing.
usage: python s94_panels_close_smooth_v43.py <base-url>
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
CH = "arcana-procedure"
results = []

REC = """(ms) => { window.__f = []; const t0 = performance.now();
  const g = (s) => { const e = document.querySelector(s); if (!e) return null; const c = getComputedStyle(e);
    const m = new DOMMatrix(c.transform === 'none' ? undefined : c.transform); const r = e.getBoundingClientRect();
    return [+m.m41.toFixed(2), +m.m42.toFixed(2), +(+c.opacity).toFixed(3), c.display === 'none' ? 0 : 1, +r.width.toFixed(1)]; };
  const f = () => { window.__f.push([Math.round(performance.now() - t0), g('.reader-bar-top'), g('.reader-bar-bottom'),
      g('.mobile-menu > .sidebar-transition'), g('.mobile-menu > .sidebar-backdrop')]);
    if (performance.now() - t0 < ms) requestAnimationFrame(f); }; requestAnimationFrame(f); }"""

# Closing events: animation start (name, direction, easing, duration) and, at removal, how far it had run.
OBS = """() => { if (window.__evOff) window.__evOff(); window.__ev = {start: [], end: [], removed: null}; const t0 = performance.now(); const now = () => Math.round(performance.now() - t0);
  const ours = (el) => el.matches && el.matches('.mobile-menu > .sidebar-transition, .mobile-menu > .sidebar-backdrop');
  const onStart = (e) => { const el = e.target; if (!ours(el)) return;
    const a = el.getAnimations().find((x) => x.animationName === e.animationName); const t = a ? a.effect.getTiming() : {};
    window.__ev.start.push({name: e.animationName, dir: t.direction, ease: getComputedStyle(el).animationTimingFunction, dur: t.duration,
                            panel: el.classList.contains('sidebar-transition'), at: now()}); };
  const onEnd = (e) => { if (ours(e.target)) window.__ev.end.push({name: e.animationName, at: now()}); };
  document.addEventListener('animationstart', onStart, true); document.addEventListener('animationend', onEnd, true);
  window.__evOff = () => { document.removeEventListener('animationstart', onStart, true); document.removeEventListener('animationend', onEnd, true); };
  const mo = new MutationObserver((ms) => { for (const m of ms) for (const n of m.removedNodes)
    if (n.classList && n.classList.contains('mobile-menu')) { window.__ev.removed = now(); mo.disconnect(); } });
  mo.observe(document.body, {subtree: true, childList: true}); }"""

TIMING = """(s) => { const c = getComputedStyle(document.querySelector(s)); return [c.transitionProperty, c.transitionDuration, c.transitionTimingFunction]; }"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:900]}", flush=True)


def rec(pg, action, ms=900):
    pg.evaluate(f"({REC})({ms})")
    action()
    pg.wait_for_timeout(ms + 200)
    return pg.evaluate("window.__f")


def one_way(vals, tol):
    """True when the values never step against the overall direction by more than tol."""
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return True
    sign = 1 if vals[-1] >= vals[0] else -1
    return all((b - a) * sign >= -tol for a, b in zip(vals, vals[1:]))


def shown(pg):
    return pg.evaluate("!!document.querySelector('.reader-chrome[data-shown]')")


def tap_page(pg, dev, touch):
    (pg.touchscreen.tap if touch else pg.mouse.click)(200, 430)


def bars_case(pg, dev, touch):
    if shown(pg):
        tap_page(pg, dev, touch)
        pg.wait_for_timeout(700)
    open_t = pg.evaluate(TIMING, ".reader-bar-top")
    fr_in = rec(pg, lambda: tap_page(pg, dev, touch), 700)
    on_t = pg.evaluate(TIMING, ".reader-bar-top")
    fr_out = rec(pg, lambda: tap_page(pg, dev, touch), 700)
    check(dev, "A bars: hiding uses the same property / duration / ease as showing", open_t == on_t and "transform" in on_t[0], {"hidden": open_t, "shown": on_t})
    for k, name in ((1, "top"), (2, "bottom")):
        for fr, way in ((fr_in, "showing"), (fr_out, "hiding")):
            ys = [f[k][1] for f in fr if f[k]]
            ops = [f[k][2] for f in fr if f[k]]
            gone = [f[0] for f in fr if f[k] and not f[k][3]]
            moved = len(set(ys)) > 1
            check(dev, f"A {name} bar {way}: one smooth movement (one way, opacity one way, never display:none)",
                  moved and one_way(ys, 0.5) and one_way(ops, 0.01) and not gone,
                  {"y": ys[:16], "op": ops[:16], "displayNone": gone[:3]})


def menu_case(pg, dev, how, touch):
    if not shown(pg):
        tap_page(pg, dev, touch)
        pg.wait_for_timeout(600)
    pg.locator("[data-reader-action=contents]").evaluate("b => b.click()")
    pg.wait_for_timeout(900)
    open_anim = pg.evaluate("""() => { const a = document.querySelector('.mobile-menu > .sidebar-transition');
      const c = getComputedStyle(a); return [c.animationName, c.animationDuration, c.animationTimingFunction]; }""")
    pg.evaluate(OBS)
    vw = pg.viewport_size["width"]

    def act():
        if how == "dimming":
            (pg.touchscreen.tap if touch else pg.mouse.click)(vw - 12, 430)
        else:
            pg.keyboard.press("Escape")
    fr = rec(pg, act, 1100)
    ev = pg.evaluate("window.__ev")
    starts = [s for s in ev["start"] if s["panel"]]
    out = starts[-1] if starts else None
    check(dev, f"B closing by {how}: own slide-back played forwards, the opening's duration and ease",
          out is not None and out["name"] == "ap-menu-out" and out["dir"] == "normal" and out["ease"] == "ease"
          and open_anim[1] in ("0.22s", "220ms") and out["dur"] == 220 and open_anim[2] == "ease",
          {"opening": open_anim, "closing": ev["start"]})
    rm = ev["removed"]
    closing = [s for s in ev["start"] if s["name"] in ("ap-menu-out", "ap-menu-fade-out") or s["dir"] == "reverse"]
    ran = {s["name"]: (rm - s["at"]) if rm is not None else None for s in closing}
    ended = {e["name"] for e in ev["end"] if rm is not None and e["at"] <= rm}
    check(dev, f"C closing by {how}: the panel and the dimming leave only after the slide-back finished",
          rm is not None and len(closing) >= 2 and all(s["name"] in ended for s in closing)
          and all(v is not None and v >= 150 for v in ran.values()),
          {"removedAt": rm, "ranMs": ran, "endedBefore": sorted(ended), "start": closing})
    xs = [f[3][0] / f[3][4] * 100 for f in fr if f[3] and f[3][4]]
    check(dev, f"D closing by {how}: the panel moves one way (no step back, no jump back in)", one_way(xs, 0.5),
          [round(x, 1) for x in xs][:20])
    by = [f[2][1] for f in fr if f[2]]
    check(dev, f"E closing by {how}: the bottom bar comes back once and stays (no going down again)",
          one_way(by, 0.5) and (not by or abs(by[-1]) <= 0.5), by[:24])
    pg.wait_for_timeout(500)


def run(browser, dev, opts):
    touch = opts.get("has_touch", False)
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true')}catch(e){}")
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        pg.goto(f"{BASE}/{LANG}/{CH}/", wait_until="networkidle")
        pg.wait_for_timeout(2000)
        qa.scroll_chapter(pg, 0.3)            # not the chapter's start (the bars stay there)
        pg.wait_for_timeout(1500)
        bars_case(pg, dev, touch)
        for how in ("dimming", "Esc"):
            menu_case(pg, dev, how, touch)
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
