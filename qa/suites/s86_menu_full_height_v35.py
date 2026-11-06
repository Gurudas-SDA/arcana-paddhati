"""V82 (Vraja Lila msg 7768, variant A, 06.11.2026; saskarnes autors) — Vraja msg 7768, atceļ V35 daļu: the bottom bar no
longer hides while «Содержание» is open; the side menu and the dimming end ABOVE the full-width bottom bar
(«Вернуться / Вперёд»), which stays visible, undimmed and tappable. Checks A–C below now say that; D (the bar slides
down) is cancelled, E (the bar is back after closing) stays. Original V35 text follows.

V35 — «Содержание» opens over the whole height; the bottom bar slides away (Vraja Lila msg 1226, 21.10.2026 15:11;
again msg 1319, 22.10.2026 ~00:08 on the cover; saskarnes autors, «Стандарты» 0а).

Rule text (as passed on — nodots-izpildei 21.10 15:11, verbatim):
 «при выдвижении боковой панели («Содержание»/«Закладки») нижняя панель прячется вниз — она там не нужна; боковая
  панель — на ПОЛНУЮ высоту экрана. Как развести две анимации лучшим образом — решает Липикара»
 «Затемнение 60 % — одним слоем на всё за меню (вкл. верхнюю панель)»
Rule text (nodots-izpildei 22.10 00:20 п.2, verbatim): «„Contents“ на обложке: нижняя панель НЕ выезжает, боковая панель
 на ПОЛНУЮ высоту (= V35)».
Criteria (verbatim): «1) меню на всю высоту, нижней панели не видно; 2) обе анимации плавные, без рывка»;
 «обложка + Contents: нижней панели нет, меню на всю высоту».
 # tehniskais slieksnis Lipikāra, nav S noteikums: «без рывка» = the bar's top, sampled every frame while the menu
 # opens, moves down monotonically through ≥ 3 intermediate positions (the 220 ms ease of the menu); «на всю высоту» =
 # the panel and the dimming reach the screen's bottom (±1 px).

Checks, per device, on the cover, a chapter page («Страницы») and in «Лента»:
  A  the menu panel spans the whole height (top 0, bottom = screen's bottom);
  B  the dimming reaches the bottom too (one layer behind the menu);
  C  the bottom bar is not on screen while the menu is open;
  D  (chapter page) the bar slides down smoothly while the menu slides in;
  E  (chapter page) the menu closed: the bottom bar is back with the top bar.
usage: python s86_menu_full_height_v35.py <base-url>
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

STATE = """() => { const vh = innerHeight; const m = document.querySelector('.mobile-menu[data-open]');
  const box = (e) => { if (!e) return null; const r = e.getBoundingClientRect(); return {top: Math.round(r.top), bottom: Math.round(r.bottom)}; };
  const b = document.querySelector('.reader-bar-bottom'); const cs = b && getComputedStyle(b); const br = b && b.getBoundingClientRect();
  const t = document.querySelector('.reader-bar-top'); const tr = t && t.getBoundingClientRect(); const tcs = t && getComputedStyle(t);
  return {vh, menu: !!m, panel: box(m && m.querySelector(':scope > .sidebar-transition')), dim: box(m && m.querySelector(':scope > .sidebar-backdrop')),
          bar: b ? {display: cs.display, opacity: +(+cs.opacity).toFixed(2), top: Math.round(br.top), bottom: Math.round(br.bottom),
                    on: cs.display !== 'none' && +cs.opacity > 0.05 && br.height > 0 && br.top < vh - 0.5 && br.bottom > 0.5} : null,
          topOn: !!t && +tcs.opacity > 0.05 && tr.bottom > 0.5}; }"""
# The bottom bar's top every frame for 450 ms after «Содержание» is pressed.
SAMPLE = """() => new Promise((done) => { const b = document.querySelector('.reader-bar-bottom'); const out = [];
  const t0 = performance.now(); document.querySelector('[data-reader-action=contents]').click();
  // WebKit headless paints few frames: also read the running CSS transition of the bar (Web Animations).
  setTimeout(() => { window.__barAnim = (b.getAnimations ? b.getAnimations() : []).filter((a) => a.transitionProperty === 'transform')
    .map((a) => ({prop: a.transitionProperty, dur: a.effect && a.effect.getTiming().duration, ease: a.effect && a.effect.getTiming().easing})); }, 20);
  const step = () => { const cs = getComputedStyle(b); out.push([Math.round(performance.now() - t0), +b.getBoundingClientRect().top.toFixed(1), +(+cs.opacity).toFixed(2)]);
    if (performance.now() - t0 < 450) requestAnimationFrame(step); else done(out); }; requestAnimationFrame(step); })"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


def full_height(s):
    """V82: the panel and the dimming start at the screen's top and END AT THE BOTTOM BAR's top (not at the screen's bottom)."""
    top = s["bar"]["top"] if s["bar"] else None
    return (s["panel"] is not None and top is not None and s["panel"]["top"] <= 1 and abs(s["panel"]["bottom"] - top) <= 1,
            s["dim"] is not None and top is not None and abs(s["dim"]["bottom"] - top) <= 1)


def run(browser, dev, opts):
    touch = opts.get("has_touch", False)
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true')}catch(e){}")
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    flow = Contents(pg, qa.TocMode("default"), touch)
    state = lambda: pg.evaluate(STATE)
    try:
        for where, url, layout in (("cover", f"{BASE}/{LANG}/", "page"), ("chapter", f"{BASE}/{LANG}/{CH}/", "page"),
                                   ("Лента", f"{BASE}/{LANG}/{CH}/", "scroll")):
            pg.evaluate(f"try{{localStorage.setItem('ap.readerLayout','{layout}')}}catch(e){{}}")
            pg.goto(url, wait_until="networkidle")
            if layout == "scroll":
                pg.wait_for_selector("[data-continuous-book]", state="attached", timeout=30000)
            pg.wait_for_timeout(1200)
            flow.bars()
            pg.wait_for_timeout(400)
            if where == "chapter":
                flow.contents()
                pg.wait_for_timeout(700)
            else:
                flow.contents()
                pg.wait_for_timeout(700)
            s = state()
            fh, dim = full_height(s)
            check(dev, f"A {where}: «Содержание» open — the panel spans from the top to the bottom bar", s["menu"] and fh, {"vh": s["vh"], "panel": s["panel"]})
            check(dev, f"B {where}: the dimming ends at the bottom bar", s["menu"] and dim, {"vh": s["vh"], "dim": s["dim"]})
            hit = pg.evaluate("""() => { const b = document.querySelector('.reader-bar-bottom'); const r = b.getBoundingClientRect();
              const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!(e && e.closest('.reader-bar-bottom')); }""")
            check(dev, f"C {where}: the bottom bar is on screen, full width, not dimmed and on top of the menu while it is open",
                  s["menu"] and (s["bar"] or {}).get("on") and hit and (s["bar"] or {}).get("opacity", 0) >= 0.99, {"bar": s["bar"], "hit": hit})
            if where == "chapter":
                pg.evaluate("document.querySelector('.mobile-menu[data-open] > .sidebar-backdrop').click()")
                pg.wait_for_timeout(900)
                s = state()
                check(dev, f"E {where}: menu closed — the bottom bar is back together with the top bar",
                      not s["menu"] and (s["bar"] or {}).get("on") == s["topOn"], {"bar": s["bar"], "topOn": s["topOn"]})
            else:
                pg.evaluate("(() => { const d = document.querySelector('.mobile-menu[data-open] > .sidebar-backdrop'); if (d) d.click(); })()")
                pg.wait_for_timeout(700)
        pg.evaluate("try{localStorage.removeItem('ap.readerLayout')}catch(e){}")
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
