"""The bottom bar does not flicker while «Содержание» slides out and back (Vraja Lila, 20.10.2026).

Task (Vraja Lila 20.10.2026, after V16 — iPhone video): «нижняя панель не должна мерцать при выдвижении боковой
панели и её задвижении». Seen in the video: on closing, the dimming of the slide-back covered the bottom bar
(grey flash fading out); on opening, «Вперёд ›» went pale at once (the menu's history step), and back on closing.
Checked on every animation frame, both ways (✕ / backdrop, and a chapter picked): the bottom bar stays where it was,
fully visible, never under the menu's dimming, and «‹ Назад» / «Вперёд ›» look exactly as before opening.
# tehniskais slieksnis Lipikāra, nav S noteikums: position ±0.5 px; opacity ≥ 0.99; recorded for 900 ms after the tap.
V35 (Vraja Lila msg 1226 / 1319, 21–22.10.2026, saskarnes autors): «при выдвижении боковой панели нижняя панель прячется
вниз — она там не нужна; боковая панель — на ПОЛНУЮ высоту». The bar no longer stays still: it slides down out of the
way while the menu opens and comes back while it closes. «Не мерцать» stays: one smooth movement each way (monotonic),
never faded, «‹ Назад» / «Вперёд ›» look the same; on closing never under the fading dimming.
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


def slide(fr, ref, down, buttons=True, covered_ok=False, vh=1e9):
    """V35: frames that break one smooth slide (down on opening / up on closing): a step against the direction,
    a fade, the dimming over it (closing), a nav button changed. Returns the bad frames."""
    bad = []
    for a, f in zip([ref] + fr, fr):
        back = (f[1] < a[1] - 0.5) if down else (f[1] > a[1] + 0.5)
        btn = buttons and (f[5] != ref[5] or f[6] != ref[6])
        # «under the dimming» only counts while the bar is on the screen (its top above the screen's bottom)
        covered = f[4] and f[1] < vh - 0.5
        if back or f[3] < 0.99 or (covered and not covered_ok) or btn:
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

        # 1. opening (V35): the bar slides down out of the screen in one smooth movement (under the one dimming)
        ref, fr = open_contents(pg)
        vh = pg.evaluate("innerHeight")
        bad = slide(fr, ref, down=True, covered_ok=True)
        check(dev, "opening «Содержание» (V35): bottom bar slides down off the screen — one smooth move, never faded, «Назад»/«Вперёд» unchanged",
              fr and fr[-1][7] and fr[-1][1] >= vh - 0.5 and not bad, {"ref": ref, "bad": bad[:4], "end": fr[-1] if fr else None, "frames": len(fr)})

        # 2. closing by the dimming (✕ / backdrop): the bar comes back up in one smooth move, above the fading dimming
        start = pg.evaluate(f"({SAMPLE})()")
        fr = record(pg, "document.querySelector('.mobile-menu[data-open] > .sidebar-backdrop').click()")
        bad = slide([f for f in fr if f[7]] + fr[-1:], start, down=False, vh=vh)
        check(dev, "closing «Содержание» (backdrop, V35): bottom bar comes back up to its place — one smooth move, never under the fading dimming, «Назад»/«Вперёд» unchanged",
              fr and not fr[-1][7] and not bad and abs(fr[-1][1] - ref[1]) <= 0.5,
              {"ref": ref, "bad": bad[:4], "end": fr[-1] if fr else None, "frames": len(fr), "menuSeen": any(f[7] for f in fr)})

        # 3. a chapter picked: new page, the panel slides back — the bar stays in place and above the dimming
        ref, _ = open_contents(pg)
        fr = record(pg, """(() => { const a = [...document.querySelectorAll('.mobile-menu[data-open] aside nav a')].find(x => x.textContent.includes(%s)); a.click(); })()"""
                    % json.dumps(PICK), 1800)
        menu_fr = [f for f in fr if f[7]]
        start = menu_fr[0] if menu_fr else ref
        bad = slide(menu_fr, start, down=False, buttons=False, covered_ok=False, vh=vh)
        check(dev, "chapter picked (V35): while the panel slides back, the bottom bar only comes back up — never faded, never dimmed",
              menu_fr and not fr[-1][7] and not bad, {"ref": ref, "bad": bad[:4], "frames": len(menu_fr)})
        c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
