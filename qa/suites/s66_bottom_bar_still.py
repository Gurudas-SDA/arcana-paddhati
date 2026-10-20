"""The bottom bar does not flicker while «Содержание» slides out and back (Vraja Lila, 20.10.2026).

Task (Vraja Lila 20.10.2026, after V16 — iPhone video): «нижняя панель не должна мерцать при выдвижении боковой
панели и её задвижении». Seen in the video: on closing, the dimming of the slide-back covered the bottom bar
(grey flash fading out); on opening, «Вперёд ›» went pale at once (the menu's history step), and back on closing.
Checked on every animation frame, both ways (✕ / backdrop, and a chapter picked): the bottom bar stays where it was,
fully visible, never under the menu's dimming, and «‹ Назад» / «Вперёд ›» look exactly as before opening.
# tehniskais slieksnis Lipikāra, nav S noteikums: position ±0.5 px; opacity ≥ 0.99; recorded for 900 ms after the tap.
usage: python s66_bottom_bar_still.py <base-url>
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
NEXT = "daily-duties-brahma-muhurta"
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:900]}", flush=True)


# One sample of the bottom bar: [t, top, bottom, opacity, covered by the dimming?, back opacity, forward opacity, menu in DOM]
SAMPLE = """() => { const b = document.querySelector('.reader-bar-bottom'); const r = b.getBoundingClientRect(); const cb = getComputedStyle(b);
  const m = document.querySelector('.mobile-menu'), d = m && m.querySelector(':scope > .sidebar-backdrop');
  const dz = m ? +getComputedStyle(m).zIndex || 0 : 0, bz = +cb.zIndex || 0;
  const dimOn = !!d && +getComputedStyle(d).opacity > 0.01;
  const op = (s) => { const e = b.querySelector(s); return e ? +(+getComputedStyle(e).opacity).toFixed(2) : null; };
  return [Math.round(performance.now()), +r.top.toFixed(1), +r.bottom.toFixed(1), +(+cb.opacity).toFixed(3), dimOn && bz <= dz,
          op('[data-reader-nav=back]'), op('[data-reader-nav=forward]'), !!m]; }"""
REC = """(ms) => { window.__bb = []; const s = %s; const t0 = performance.now(); const f = () => { const x = s(); x[0] -= Math.round(t0);
  window.__bb.push(x); if (performance.now() - t0 < ms) requestAnimationFrame(f); }; requestAnimationFrame(f); }""" % SAMPLE


def show_bars(pg):
    for _ in range(3):
        if pg.evaluate("!!document.querySelector('.reader-chrome[data-shown]')"):
            return
        pg.mouse.click(200, 430)
        pg.wait_for_timeout(450)


def record(pg, action, ms=900):
    pg.evaluate(f"({REC})({ms})")
    pg.evaluate(action)
    pg.wait_for_timeout(ms + 150)
    return pg.evaluate("window.__bb || []")


def still(fr, ref, buttons=True):
    """Frames where the bar moved, faded, was covered, or (buttons) a nav button changed its look."""
    bad = []
    for f in fr:
        moved = abs(f[1] - ref[1]) > 0.5 or abs(f[2] - ref[2]) > 0.5
        faded = f[3] < 0.99
        btn = buttons and (f[5] != ref[5] or f[6] != ref[6])
        if moved or faded or f[4] or btn:
            bad.append(f)
    return bad


def open_contents(pg):
    show_bars(pg)
    pg.wait_for_timeout(300)
    ref = pg.evaluate(f"({SAMPLE})()")
    fr = record(pg, "document.querySelector('[data-reader-action=contents]').click()")
    return ref, fr


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        c = b.new_context(service_workers="block", locale="ru-RU", **opts)
        c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');")
        pg = c.new_page()
        # as in the video: «‹ Назад» and «Вперёд ›» both have a step (the page was reached by a step back)
        pg.goto(f"{BASE}/ru-iast/", wait_until="networkidle")
        pg.goto(f"{BASE}/ru-iast/{PAGE}/", wait_until="networkidle")
        pg.goto(f"{BASE}/ru-iast/{NEXT}/", wait_until="networkidle")
        pg.go_back(wait_until="networkidle")
        pg.wait_for_timeout(900)

        # 1. opening: the bar does not change at all
        ref, fr = open_contents(pg)
        bad = still(fr, ref)
        check(dev, "opening «Содержание»: bottom bar still — same place, fully visible, not dimmed, «Назад»/«Вперёд» unchanged",
              fr and fr[-1][7] and not bad, {"ref": ref, "bad": bad[:4], "frames": len(fr)})

        # 2. closing by the dimming (✕ / backdrop): the bar does not change at all
        fr = record(pg, "document.querySelector('.mobile-menu[data-open] > .sidebar-backdrop').click()")
        bad = still([f for f in fr if f[7]] + fr[-1:], ref)
        check(dev, "closing «Содержание» (backdrop): bottom bar still — never under the fading dimming, «Назад»/«Вперёд» unchanged",
              fr and not fr[-1][7] and not bad, {"ref": ref, "bad": bad[:4], "frames": len(fr), "menuSeen": any(f[7] for f in fr)})

        # 3. a chapter picked: new page, the panel slides back — the bar stays in place and above the dimming
        ref, _ = open_contents(pg)
        fr = record(pg, """(() => { const a = [...document.querySelectorAll('.mobile-menu[data-open] aside nav a')].find(x => x.textContent.includes(%s)); a.click(); })()"""
                    % json.dumps(PICK), 1800)
        menu_fr = [f for f in fr if f[7]]
        bad = still(menu_fr, ref, buttons=False)
        check(dev, "chapter picked: while the panel slides back, the bottom bar stays in place, fully visible, never dimmed",
              menu_fr and not fr[-1][7] and not bad, {"ref": ref, "bad": bad[:4], "frames": len(menu_fr)})
        c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
