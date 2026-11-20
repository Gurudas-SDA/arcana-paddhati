"""V105 Vraja Lila msg 8549 + kadri 3122-3127 (un 8550-8562): atlase augšējā pusē → izvēlne zem → panelis virs; apakšējā → panelis zem.
Real iPhone (19 frames): iOS menu UNDER a selection whose top is in the upper half of the screen, OVER it in the lower half (line count does not matter). V105 aizstāj rindu skaita likumu (V104).
Criteria: (1) selection top in the upper half of the visual viewport -> panel near ABOVE it (14..32 px), iOS menu zone (16..60 px under the selection) free; lower half -> panel near UNDER it,
 menu zone over the selection free; (2) no room on the free side -> panel beyond the menu zone (>= 60 px), never inside it; (3) the panel never covers the selection; Android and desktop unchanged.
# tehniskais slieksnis Lipikāra, nav S noteikums: menu zone 16..60 px (43 px menu), free-side gap 14..32 px, beyond-zone gap 60..90 px; half = 0.5 (assumption from the frames)
usage: python s_v105_ios_menu_half.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7", "ipad-portrait"])
results = []
PAGE = "daily-duties-brahma-muhurta"


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


SELECT = """([n, a, b, frac]) => {
  document.querySelectorAll('[data-hl-gap]').forEach(g => g.remove()); document.querySelectorAll('.app-main article p').forEach(p => p.normalize());
  const nodes = [];
  for (const p of document.querySelectorAll('.app-main article p')) {
    if (!p.getClientRects().length || p.closest('button,table,[hidden],.mood-panel')) continue;
    const w = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
    for (let x = w.nextNode(); x; x = w.nextNode()) if ((x.data.match(/\\S+/g) || []).length >= 14 && x.parentElement.getClientRects().length) nodes.push(x);
  }
  // cause of the earlier misses: a node near the top of the page cannot be scrolled DOWN the screen (scrollY >= 0), so only nodes whose document top >= the wanted screen position are usable
  const vv0 = window.visualViewport; const want = vv0.offsetTop + vv0.height * frac;
  const usable = nodes.filter(x => x.parentElement.getBoundingClientRect().top + window.scrollY >= want + 4);
  const node = usable[n]; if (!node) return {unreachable: true, usable: usable.length, nodes: nodes.length};
  const d = node.data; const ws = [...d.matchAll(/\\S+/g)];
  const s = ws[a].index, e = ws[b - 1].index + ws[b - 1][0].length;
  const r = document.createRange(); r.setStart(node, s); r.setEnd(node, e);
  const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
  const vv = window.visualViewport; window.scrollBy(0, r.getBoundingClientRect().top - want);
  const rs = [...r.getClientRects()].map(q => ({t: q.top, b: q.bottom, l: q.left, r: q.right}));
  const f = rs[0], l = rs[rs.length - 1], bb = r.getBoundingClientRect();
  return {vvh: vv.height, vvtop: vv.offsetTop, scrollY: window.scrollY, wantTop: want, rects: rs, top: Math.min(...rs.map(q => q.t)), bottom: Math.max(...rs.map(q => q.b)), left: bb.left, right: bb.right}; }"""
MENU = "() => { const m = document.querySelector('[data-hl-menu]'); const b = m.getBoundingClientRect(); return {t: b.top, b: b.bottom, l: b.left, r: b.right}; }"


def overlaps(m, rects):
    return [q for q in rects if m["t"] < q["b"] and m["b"] > q["t"] and m["l"] < q["r"] and m["r"] > q["l"]]


def run(p, dev, eng, opts):
    try:
        b = getattr(p, eng).launch()
    except Exception:  # WebKit libs missing
        b = p.chromium.launch()
        opts = {k: v for k, v in opts.items() if k != "user_agent"}
    c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce", **opts)
    c.add_init_script("try{localStorage.removeItem('ap.highlights');localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');}catch(e){}")
    pg = c.new_page()
    pg.goto(f"{BASE}/ru-iast/{PAGE}/", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    pg.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important}")
    vh = pg.evaluate("innerHeight")
    ios = pg.evaluate("/iPhone|iPad|iPod/.test(navigator.userAgent)")
    if not ios:
        check(dev, "skipped (not iOS: V104 concerns iOS only)", True)
        b.close()
        return

    def show(args):
        # tehniskais slieksnis/gaidīšana Lipikāra, nav S noteikums (19.11, V104): the previous selection's panel is cleared first, so the menu read below is the NEW selection's (a stale panel was read on a loaded iPad)
        pg.evaluate("() => getSelection().removeAllRanges()")
        try:
            pg.wait_for_selector("[data-hl-menu]", state="hidden", timeout=2500)
        except Exception:  # noqa: BLE001
            pass
        s = pg.evaluate(SELECT, args)
        if s is None or s.get("unreachable"):
            raise AssertionError(f"placement not reached: no text node can be placed at {args[3]:.0%} of the screen ({s})")
        if abs(s["top"] - s["wantTop"]) > 6:
            raise AssertionError(f"placement not reached: wanted selection top {s['wantTop']:.0f}, got {s['top']:.0f} (vv.height {s['vvh']:.0f})")
        pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
        pg.wait_for_timeout(500)
        return s, pg.evaluate(MENU)

    def zone(t, b_):
        return {"t": t, "b": b_, "l": -1e6, "r": 1e6}

    # (name, selection args [text node, first word, last word, selection top as a share of the viewport], lines wanted, expected panel side)
    CASES = (
        ("1 line, upper (25%)", [0, 0, 2, 0.25], 1, "above"),
        ("1 line, upper-middle (42%)", [0, 0, 2, 0.42], 1, "above"),
        ("1 line, lower-middle (58%)", [0, 0, 2, 0.58], 1, "under"),
        ("1 line, bottom (92%)", [0, 0, 2, 0.92], 1, "beyond-above"),
        ("2 lines, upper (25%)", [1, 0, 12, 0.25], 2, "above"),
        ("2 lines, lower (65%)", [1, 0, 12, 0.65], 2, "under"),
        ("2 lines, bottom (90%)", [1, 0, 12, 0.90], 2, "beyond-above"),
    )
    SHOTS = {"1 line, upper (25%)": "1 строка вверху", "1 line, lower-middle (58%)": "1 строка внизу", "2 lines, upper (25%)": "2 строки вверху", "2 lines, lower (65%)": "2 строки внизу"}
    seen = set()
    for name, args, want, exp0 in CASES:
        s, m = show(args)
        n = len(s["rects"])
        shot = os.environ.get("QA_SHOT_DIR")  # tehniskais: ekrānuzņēmumi pēc pieprasījuma
        if shot and dev == "iphone14" and name in SHOTS:
            pg.screenshot(path=os.path.join(shot, f"2026.11.20_V105_iPhone_{SHOTS[name]}.png"))
        ev = {"menu": m, "sel": {k: s[k] for k in ("top", "bottom", "left", "right")}, "rects": n, "vh": vh}
        check(dev, f"{name}: the selection really is {'one line' if want == 1 else 'several lines'}", (n == 1) == (want == 1), ev)
        check(dev, f"{name}: the panel covers no selection rect", not overlaps(m, s["rects"]), ev)
        zb = zone(s["bottom"] + 16, s["bottom"] + 60)
        za = zone(s["top"] - 60, s["top"] - 16)
        half = s["vvtop"] + s["vvh"] / 2
        upper = s["top"] < half
        h = m["b"] - m["t"]
        room_under = s["bottom"] + 16 + h <= s["vvtop"] + s["vvh"] - 8  # same room test as the code (bottom bar ignored: page has none on this route when it is not shown)
        exp = "above" if upper else ("under" if room_under else "beyond-above")
        seen.add((want, exp))
        if (upper and exp != "above") or (not upper and exp == "above"):
            check(dev, f"{name}: expectation from the actual top", False, ev)
        if exp == "above":  # upper half: iOS menu under -> panel near above
            d = s["top"] - m["b"]
            check(dev, f"{name}: iOS menu UNDER the selection does not touch the panel", not overlaps(m, [zb]), ev)
            check(dev, f"{name}: the panel is near ABOVE the selection (14..32 px)", 14 <= d <= 32, dict(ev, d=d))
        elif exp == "under":  # lower half: iOS menu over -> panel near under
            d = m["t"] - s["bottom"]
            check(dev, f"{name}: iOS menu OVER the selection does not touch the panel", not overlaps(m, [za]), ev)
            check(dev, f"{name}: the panel is near UNDER the selection (14..32 px)", 14 <= d <= 32, dict(ev, d=d))
        else:  # bottom: menu over, no room under -> panel above, beyond the menu zone
            check(dev, f"{name}: no room under -> the panel is above, beyond the menu zone (>= 60 px)", s["top"] - m["b"] >= 60, ev)
    # both halves, 1 and 2 lines, actually reached (computed from the real selection top vs vv.height/2)
    check(dev, "cases cover upper and lower half with 1 and 2 lines", {(1, "above"), (2, "above")} <= seen and any(w == 1 and e != "above" for w, e in seen) and any(w == 2 and e != "above" for w, e in seen), sorted(seen))
    b.close()


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        try:
            run(p, dev, eng, opts)
        except Exception as e:  # noqa: BLE001
            check(dev, "scenario ran to the end", False, repr(e)[:500])

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
