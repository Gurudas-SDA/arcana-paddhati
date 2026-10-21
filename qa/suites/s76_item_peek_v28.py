"""V28 — the floating picture copy in «16 предметов» (gl. 3.1) is always on the screen, its ✕ can be pressed
(Vraja Lila msg 5782, 21.10.2026, iPhone screenshot; saskarnes autors, «Стандарты» 0а).

Rule text (verbatim, Vraja Lila): «при выборе видно окошко с выбранным парафирналием, но оно уходит за предел
доступа и крестик невозможно нажать».
Criterion (Lipikāra, Vraja's words): the window is always whole on the screen and its ✕ can be pressed —
iPhone 14, Pixel 7, iPad, desktop; portrait and landscape; with the reading bars shown and hidden; the window
low (under the lit row) and high (above it).
  # tehniskais slieksnis Lipikāra, nav S noteikums: «on the screen» = window and ✕ ≥ 4 px inside every edge and
  #   clear of the shown bars (top 57 px / bottom 57 px); «can be pressed» = the topmost element at the ✕'s centre is
  #   the ✕, and a tap there closes the window.
usage: python s76_item_peek_v28.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
PAGE = "worship-sixteen-articles"
EDGE = 4
BAR = 57
results = []


def turned(name, eng, opts):
    o = dict(opts)
    v = o["viewport"]
    o["viewport"] = {"width": v["height"], "height": v["width"]}
    return (name + "-landscape", eng, o)


DEVICES = qa.devices(["iphone14", "pixel7", "ipad-portrait", "ipad-landscape", "desktop"])
DEVICES += [turned(n, e, o) for n, e, o in DEVICES if n in ("iphone14", "pixel7")]


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


# put row `n` at y = frac × screen height, light it, report the window and its ✕
LIGHT = """async ([n, frac, bars]) => {
  const m = document.querySelector('.app-main'); const d = document.documentElement;
  if (bars) d.setAttribute('data-reader-bars', ''); else d.removeAttribute('data-reader-bars');
  const row = document.querySelector(`.app-main .hs-row[data-hs-nums="${n}"]`); if (!row) return {err: 'no row ' + n};
  const want = innerHeight * frac; m.scrollTop += row.getBoundingClientRect().top - want;
  m.dispatchEvent(new Event('scroll'));
  await new Promise(r => setTimeout(r, 120));
  const hit = row.querySelector('.hs-text, .hs-cell'); if (!row.hasAttribute('data-active')) hit.click();
  for (let i = 0; i < 3; i++) { await new Promise(r => setTimeout(r, 180)); dispatchEvent(new Event('resize')); m.dispatchEvent(new Event('scroll')); }
  await new Promise(r => setTimeout(r, 400));
  if (bars) d.setAttribute('data-reader-bars', ''); else d.removeAttribute('data-reader-bars');
  await new Promise(r => setTimeout(r, 300));
  const fig = document.querySelector('.app-main .hs-figure'); const fr = fig && fig.getBoundingClientRect();
  const figSeen = !!fr && fr.bottom > 0 && fr.top < innerHeight;
  const pk = document.querySelector('.hs-peek'); if (!pk) return {err: 'no window', active: row.hasAttribute('data-active'), figSeen};
  const x = pk.querySelector('.hs-peek-close'); const p = pk.getBoundingClientRect(), c = x.getBoundingClientRect();
  const cx = (c.left + c.right) / 2, cy = (c.top + c.bottom) / 2; const top = document.elementFromPoint(cx, cy);
  const rr = row.getBoundingClientRect();
  return {w: innerWidth, h: innerHeight, high: pk.hasAttribute('data-top'),
    peek: [p.left, p.top, p.right, p.bottom].map(v => +v.toFixed(1)), x: [c.left, c.top, c.right, c.bottom].map(v => +v.toFixed(1)),
    xTop: !!(top && top.closest('.hs-peek-close')), xc: [Math.round(cx), Math.round(cy)],
    rowCovered: rr.bottom > p.top && rr.top < p.bottom && rr.right > p.left && rr.left < p.right}; }"""


def inside(box, s, bars):
    l, t, r, b = box
    top_min = EDGE + (BAR if bars else 0)
    bottom_max = s["h"] - EDGE - (BAR if bars else 0)
    return l >= EDGE and r <= s["w"] - EDGE and t >= top_min and b <= bottom_max


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        c = b.new_context(service_workers="block", locale="ru-RU", **opts)
        c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');")
        pg = c.new_page()
        pg.goto(f"{BASE}/ru-iast/{PAGE}/", wait_until="networkidle")
        pg.wait_for_timeout(900)
        for bars in (False, True):
            for frac, where in ((0.3, "row high on the screen"), (0.72, "row low on the screen")):
                n = 14 if frac < 0.5 else 12
                s = pg.evaluate(LIGHT, [n, frac, bars])
                tag = f"bars {'shown' if bars else 'hidden'}, {where}"
                if "err" in s:
                    # the picture itself on the screen: no floating copy is needed (not this rule)
                    check(dev, f"{tag}: the window shows (or the picture itself is on the screen)", s.get("figSeen") and s.get("active"), s)
                    continue
                check(dev, f"{tag}: the window whole on the screen ({'high' if s['high'] else 'low'})", inside(s["peek"], s, bars), s)
                check(dev, f"{tag}: ✕ on the screen and on top (can be pressed)", inside(s["x"], s, bars) and s["xTop"], s)
                if (bars, frac) == (True, 0.72):
                    # a real tap on the ✕ closes the window
                    if opts.get("has_touch"):
                        pg.touchscreen.tap(*s["xc"])
                    else:
                        pg.mouse.click(*s["xc"])
                    pg.wait_for_timeout(400)
                    check(dev, f"{tag}: a tap on ✕ closes the window", not pg.evaluate("!!document.querySelector('.hs-peek')"), s["xc"])
        c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
