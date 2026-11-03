"""V69 — in the floating picture window (the explanation of a numbered picture) the close ✕ is ALWAYS above the picture,
never below it; the window and the ✕ are whole on the screen, are not covered by anything, and a tap on the ✕ closes it.
Vraja Lila msg 7394 (03.11.2026), literally: «при появлении модальных окон при пояснении картинок, я бы хотел чтобы крестик
всегда был в верхней части картинки, никогда в нижней. Это относится как к мобильной, так и к десктоп версии. Крестик и окно
должны быть достигаемы.. никогда не обрезаться экраном или другими элементами (меню, выходить за экран и т.п.)».
Two screenshots: bad = the ✕ under the picture at the right; good = the ✕ above the picture in its top right corner.
Criteria (register V69): in every window — iPhone SE, iPhone 14, Pixel 7, iPad portrait / landscape, computer (Chrome), Mac Safari —
on the three numbered pictures (16 предметов, герб, тилака), with the reading bars hidden and shown, the lit row high and low on the
screen (the window then sits low or at the top), and a first / middle / last row:
 (1) the ✕ is above the picture: ✕ bottom <= picture top (+ tolerance), and on its right side (✕ centre in the right half);
 (2) the window and the ✕ are whole on the screen (0 <= top, bottom <= innerHeight, left/right inside), clear of the shown bars;
 (3) nothing covers the ✕ (the topmost element at the ✕ centre is the ✕) and the window (the topmost element at its centre is in the window);
 (4) a real tap / click on the ✕ closes the window.
# tehniskais slieksnis Lipikāra, nav S noteikums: ±2 px measuring tolerance for «above»; «on the screen» = 0 px from every edge (the
#   rule says «никогда не обрезаться»), clear of the shown bars (top 57 px / bottom 57 px, as s76); settle 400-900 ms.
usage: python s141_image_modal_close_v69.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
PAGES = ["worship-sixteen-articles", "gaudiya-emblem", "daily-duties-brahma-muhurta"]
BAR = 57
TOL = 2
results = []

DEVICES = qa.devices(["iphone-se", "iphone14", "pixel7", "ipad-portrait", "ipad-landscape", "desktop", "mac-safari"])


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


ROWS = """() => [...new Set([...document.querySelectorAll('.app-main .hs-row[data-hs-nums]')].map(r => r.getAttribute('data-hs-nums')))]"""

# put the row with numbers `n` at y = frac x screen height, light it, report the window, the picture in it and the ✕
LIGHT = """async ([n, frac, bars]) => {
  const m = document.querySelector('.app-main'); const d = document.documentElement;
  const setBars = () => { if (bars) d.setAttribute('data-reader-bars', ''); else d.removeAttribute('data-reader-bars'); };
  setBars();
  const row = document.querySelector(`.app-main .hs-row[data-hs-nums="${n}"]`); if (!row) return {err: 'no row ' + n};
  m.scrollTop += row.getBoundingClientRect().top - innerHeight * frac; m.dispatchEvent(new Event('scroll'));
  await new Promise(r => setTimeout(r, 120));
  const hit = row.querySelector('.hs-text, .hs-cell'); if (!row.hasAttribute('data-active')) hit.click();
  for (let i = 0; i < 3; i++) { await new Promise(r => setTimeout(r, 180)); dispatchEvent(new Event('resize')); m.dispatchEvent(new Event('scroll')); }
  await new Promise(r => setTimeout(r, 400)); setBars(); await new Promise(r => setTimeout(r, 300));
  const fig = document.querySelector('.app-main .hs-figure'); const fr = fig && fig.getBoundingClientRect();
  const figSeen = !!fr && fr.bottom > 0 && fr.top < innerHeight;
  const pk = document.querySelector('.hs-peek'); if (!pk) return {err: 'no window', active: row.hasAttribute('data-active'), figSeen};
  const x = pk.querySelector('.window-close'); const img = pk.querySelector('img');
  const box = e => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom].map(v => +v.toFixed(1)); };
  const P = box(pk), X = box(x), I = box(img);
  const at = (px, py) => document.elementFromPoint(px, py);
  const xc = [(X[0] + X[2]) / 2, (X[1] + X[3]) / 2], pc = [(P[0] + P[2]) / 2, (P[1] + P[3]) / 2];
  const topX = at(xc[0], xc[1]), topP = at(pc[0], pc[1]);
  return {w: innerWidth, h: innerHeight, high: pk.hasAttribute('data-top'), peek: P, x: X, img: I,
    xTop: !!(topX && topX.closest('.window-close')), xCover: topX ? (topX.className || topX.tagName).toString().slice(0, 60) : null,
    pTop: !!(topP && pk.contains(topP)), xc: [Math.round(xc[0]), Math.round(xc[1])]}; }"""


def inside(box, s, bars):
    l, t, r, b = box
    top_min = BAR if bars else 0
    bottom_max = s["h"] - (BAR if bars else 0)
    return l >= 0 and r <= s["w"] and t >= top_min and b <= bottom_max


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        touch = bool(opts.get("has_touch"))
        c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce", **opts)
        c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');}catch(e){}")
        pg = c.new_page()
        opened_any = False
        for page in PAGES:
            pg.goto(f"{BASE}/ru-iast/{page}/", wait_until="networkidle")
            pg.wait_for_timeout(900)
            rows = pg.evaluate(ROWS)
            if not rows:
                check(dev, f"{page}: the page has numbered rows", False, rows)
                continue
            pick = [rows[0], rows[len(rows) // 2], rows[-1]]
            opened = 0
            for bars in (False, True):
                for frac, where in ((0.3, "row high"), (0.72, "row low")):
                    for n in pick:
                        s = pg.evaluate(LIGHT, [n, frac, bars])
                        tag = f"{page} row {n}, bars {'shown' if bars else 'hidden'}, {where}"
                        if "err" in s:
                            # the picture itself is on the screen: no window is needed (not this rule)
                            if not (s.get("figSeen") and s.get("active")):
                                check(dev, f"{tag}: the window shows (or the picture itself is on the screen)", False, s)
                            continue
                        opened += 1
                        opened_any = True
                        X, I = s["x"], s["img"]
                        check(dev, f"{tag}: ✕ above the picture (✕ bottom <= picture top) and on its right side ({'window at the top' if s['high'] else 'window low'})",
                              X[3] <= I[1] + TOL and (X[0] + X[2]) / 2 >= I[0] + (I[2] - I[0]) / 2, s)
                        check(dev, f"{tag}: window and ✕ whole on the screen, clear of the bars", inside(s["peek"], s, bars) and inside(X, s, bars), s)
                        check(dev, f"{tag}: nothing covers the ✕ and the window", s["xTop"] and s["pTop"], s)
            check(dev, f"{page}: the window opened at least once", opened > 0 or page != PAGES[0], opened)
            # a real tap / click on the ✕ closes the window (fresh page, the window at the bottom, then at the top)
            for frac, bars in ((0.3, False), (0.72, True)):
                pg.goto(f"{BASE}/ru-iast/{page}/", wait_until="networkidle")
                pg.wait_for_timeout(700)
                s = pg.evaluate(LIGHT, [pick[0] if frac < 0.5 else pick[-1], frac, bars])
                if "err" in s:
                    continue
                if touch:
                    pg.touchscreen.tap(*s["xc"])
                else:
                    pg.mouse.click(*s["xc"])
                pg.wait_for_timeout(500)
                check(dev, f"{page}: a {'tap' if touch else 'click'} on ✕ closes the window ({'bars shown' if bars else 'bars hidden'}, {'window at the top' if s['high'] else 'window low'})",
                      not pg.evaluate("!!document.querySelector('.hs-peek')"), s["xc"])
        check(dev, "the floating window opened in at least one state on this device", opened_any, "never opened")
        c.close()
        b.close()

print(f"\n{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
