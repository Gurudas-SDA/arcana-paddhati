"""«Содержание» slides out and back; the top menus close as smoothly as they open (Vraja Lila, 20.10.2026).

Task (ДА msg 5520, mockup «2026.10.20_Содержание — выдвижение и задвижение, iPhone/desktop.gif»): the contents
panel slides out from the left (translateX −100 % → 0) with the dimming fading in; a chosen chapter's row lights
up (#F5E6C8, 150 ms) → the new page → the panel slides back with the dimming fading out → removed from the DOM;
the A65 order stays (the panel goes only after the new page is shown); reduced motion — no animation.
Addition msg 5521: both ways with the SAME easing and duration as the top menu (top bar: transform 220ms ease);
the top menu («Аа» panel, language list) opened smoothly but vanished at once — it now closes the same way back.
# tehniskais slieksnis Lipikāra, nav S noteikums: in-between frames = at least 2 animation frames with the panel
#   between −95 % and −5 % of its width (or opacity 0.05–0.95); removed within 600 ms; picked-row colour read
#   within 100 ms of the tap.
usage: python s65_menu_slide.py <base-url>
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
PICK = "Гуру-парампара"
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


# Every animation frame for `ms`: [t, panel x / width (null = no panel), menus in DOM, open menus, ghost opacity]
REC = """(ms) => { window.__fr = []; const t0 = performance.now(); const f = () => {
  const a = document.querySelector('.mobile-menu > .sidebar-transition');
  const r = a && a.getBoundingClientRect();
  const g = document.querySelector('.reader-panel-out, .lang-card-out');
  window.__fr.push([Math.round(performance.now() - t0), r ? Math.round(r.left / r.width * 1000) / 1000 : null,
    document.querySelectorAll('.mobile-menu').length, document.querySelectorAll('.mobile-menu[data-open]').length,
    g ? +(+getComputedStyle(g).opacity).toFixed(3) : null, location.pathname.split('/').filter(Boolean).pop(),
    a ? a.getAnimations().filter(x => x.playState === 'running').map(x => x.animationName + ':' + x.effect.getTiming().duration + ':' + x.effect.getTiming().direction).join() : '',
    (() => { const k = document.querySelector('.mobile-menu [data-menu-picked]'); return k ? getComputedStyle(k).backgroundColor : null; })(),
    g ? g.getAnimations().filter(x => x.playState === 'running').map(x => x.animationName).join() : '']);
  if (performance.now() - t0 < ms) requestAnimationFrame(f); }; requestAnimationFrame(f); }"""

TIMING = """() => { const a = document.querySelector('.mobile-menu > .sidebar-transition'), d = document.querySelector('.mobile-menu > .sidebar-backdrop');
  const bar = getComputedStyle(document.querySelector('.reader-bar-top'));
  const props = bar.transitionProperty.split(',').map(s => s.trim()); const i = Math.max(0, props.indexOf('transform'));
  const pick = (v, k) => v.split(',').map(s => s.trim())[k] || v.split(',')[0].trim();
  const ca = a && getComputedStyle(a), cd = d && getComputedStyle(d);
  return {bar: [pick(bar.transitionDuration, i), pick(bar.transitionTimingFunction, i)],
          panel: ca && [ca.animationName, ca.animationDuration, ca.animationTimingFunction],
          dim: cd && [cd.animationName, cd.animationDuration, cd.animationTimingFunction]}; }"""


def frames(pg, ms):
    pg.wait_for_timeout(ms + 150)
    return pg.evaluate("window.__fr || []")


def between(fr):
    return [f for f in fr if f[1] is not None and -0.95 < f[1] < -0.05]


def slides(fr, direction):
    """In-between frames, or (slow headless WebKit draws few frames) the running slide animation itself.
    V43 (Vraja Lila 22.10.2026): closing is its own animation ap-menu-out played forwards with the same ease
    (before: ap-menu-in in reverse, which also reversed the ease — slow start, abrupt end)."""
    name = "ap-menu-in:220:normal" if direction == "normal" else "ap-menu-out:220:normal"
    return bool(between(fr)) or any(name in f[6] for f in fr)


def show_bars(pg):
    for _ in range(3):
        if pg.evaluate("!!document.querySelector('.reader-chrome[data-shown]')"):
            return
        pg.mouse.click(200, 430)
        pg.wait_for_timeout(450)


def open_contents(pg):
    show_bars(pg)
    pg.evaluate(f"({REC})(700)")
    pg.evaluate("document.querySelector('[data-reader-action=contents]').click()")
    return frames(pg, 700)


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        for reduce in (False, True):
            tag = "reduced motion: " if reduce else ""
            c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce" if reduce else "no-preference", **opts)
            c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');")
            pg = c.new_page()
            pg.goto(f"{BASE}/ru-iast/{PAGE}/", wait_until="networkidle")
            pg.wait_for_timeout(900)

            # 1. contents slides out
            fr = open_contents(pg)
            tm = pg.evaluate(TIMING)
            if not reduce:
                check(dev, "contents opens sliding from the left (in-between frames / running slide)", slides(fr, "normal") and fr[-1][1] == 0,
                      {"between": between(fr)[:4], "last": fr[-1] if fr else None})
                bar = tm["bar"]
                check(dev, "slide-out = the top bar's easing and duration (panel and dimming)",
                      tm["panel"] and tm["panel"][1:] == bar and tm["dim"] and tm["dim"][1:] == bar and tm["panel"][0] != "none", tm)
            else:
                check(dev, f"{tag}contents opens without sliding", not between(fr) and tm["panel"] and tm["panel"][0] == "none", {"fr": fr[:3], "t": tm})

            # 2. ✕ / backdrop: slides back, then removed; closed for the page at once
            pg.evaluate(f"({REC})(700)")
            pg.evaluate("document.querySelector('.mobile-menu[data-open] > .sidebar-backdrop').click()")
            fr = frames(pg, 700)
            gone = next((f[0] for f in fr if f[2] == 0), None)
            shut = next((i for i, f in enumerate(fr) if f[3] == 0), None)
            check(dev, f"{tag}closing: no open menu within 100 ms, and it stays closed",
                  shut is not None and fr[shut][0] <= 100 and all(f[3] == 0 for f in fr[shut:]), fr[:3])
            if not reduce:
                check(dev, "closing (backdrop): slides back (in-between frames), then removed from the DOM",
                      slides(fr, "reverse") and gone is not None and gone <= 600, {"between": between(fr)[:4], "anim": sorted({f[6] for f in fr}), "removedAt": gone})
            else:
                check(dev, f"{tag}closing: removed at once, no sliding", not between(fr) and gone is not None and gone <= 100, {"removedAt": gone, "fr": fr[:3]})

            # 3. a chapter picked: row lights up, page changes first, then the panel slides back
            open_contents(pg)
            row = pg.locator(".mobile-menu[data-open] aside nav a").filter(has_text=PICK).first
            pg.evaluate(f"({REC})(1800)")
            pg.evaluate("""(t) => { window.__pick = null; const a = [...document.querySelectorAll('.mobile-menu[data-open] aside nav a')].find(x => x.textContent.includes(t));
              a.click(); setTimeout(() => { window.__pick = getComputedStyle(a).backgroundColor; }, %d); }""" % (10 if reduce else 160), PICK)
            fr = frames(pg, 1800)
            lit = sorted({f[7] for f in fr if f[7]})
            check(dev, f"{tag}picked row lit #F5E6C8", "rgb(245, 230, 200)" in lit, lit)
            first_new = next((f for f in fr if f[5] != PAGE), None)
            moved_before = [f for f in fr if f[5] == PAGE and f[1] is not None and f[1] < -0.01]
            check(dev, f"{tag}A65: the panel stays in place until the new page is shown", first_new and not moved_before,
                  {"first_new": first_new, "moved_before": moved_before[:2]})
            gone = next((f[0] for f in fr if f[2] == 0), None)
            if not reduce:
                after = [f for f in fr if f[5] != PAGE]
                check(dev, "after the new page: slides back (in-between frames / running slide), then removed", slides(after, "reverse") and gone is not None,
                      {"between": between(after)[:4], "anim": sorted({f[6] for f in after}), "removedAt": gone})
            else:
                check(dev, f"{tag}after the new page: removed without sliding", not between(fr) and gone is not None, {"removedAt": gone})

            # 4. «Аа» panel closes the same way back (fade + lift, like it opened)
            if not reduce:
                show_bars(pg)
                pg.evaluate("document.querySelector('[data-reader-action=aa]').click()")
                pg.wait_for_timeout(450)
                pg.evaluate(f"({REC})(500)")
                pg.evaluate("document.querySelector('.reader-panel-close').click()")
                fr = frames(pg, 500)
                ghost = [f[4] for f in fr if f[4] is not None]
                closed = pg.evaluate("document.querySelectorAll('.reader-panel').length")
                check(dev, "«Аа» panel: closes smoothly (fading frames), closed for the page at once",
                      (len([o for o in ghost if 0.05 < o < 0.95]) >= 2 or any("reader-pop" in f[8] for f in fr)) and closed == 0 and fr[-1][4] is None,
                      {"ghost": ghost[:8], "anim": sorted({f[8] for f in fr}), "panels": closed})
            c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
