"""V107 Vraja Lila msg 8567–8579, kadri 8571/8574: atlases augša tieši zem vidus — izvēlne un panelis abi virs.
Real iPhone (31 frames): the iOS menu is always <= ~60 px from the selection (above or under); it changes side between 0.44 and 0.53 of the screen. In the grey zone (0.40..0.56 of the visual viewport)
the panel must stand >= 60 px from the selection (outside the menu zone on both sides), never 14..32 px; outside the zone V105 is unchanged (14..32 px on the free side).
# tehniskais slieksnis Lipikāra, nav S noteikums: menu zone 16..60 px, grey zone 0.40..0.56 (31 frames: 0.44–0.53 + spare)
usage: python s_v107_ios_grey_zone.py <base-url>
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


SELECT = """async ([n, a, b, frac]) => {
  const main = document.querySelector('.app-main'); const raf = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));  // the reader scrolls inside .app-main, not window
  document.querySelectorAll('[data-hl-gap]').forEach(g => g.remove()); document.querySelectorAll('.app-main article p').forEach(p => p.normalize());
  const nodes = [];
  for (const p of document.querySelectorAll('.app-main article p')) {
    if (!p.getClientRects().length || p.closest('button,table,[hidden],.mood-panel')) continue;
    const w = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
    for (let x = w.nextNode(); x; x = w.nextNode()) if ((x.data.match(/\\S+/g) || []).length >= 14 && x.parentElement.getClientRects().length) nodes.push(x);
  }
  // cause of the earlier misses: a node near the top of the page cannot be scrolled DOWN the screen (scrollY >= 0), so only nodes whose document top >= the wanted screen position are usable
  const vv0 = window.visualViewport; const want = vv0.offsetTop + vv0.height * frac;
  const usable = nodes.filter(x => x.parentElement.getBoundingClientRect().top - main.getBoundingClientRect().top + main.scrollTop + main.getBoundingClientRect().top >= want + 4);
  const node = usable[n]; if (!node) return {unreachable: true, usable: usable.length, nodes: nodes.length};
  const d = node.data; const ws = [...d.matchAll(/\\S+/g)];
  const s = ws[a].index, e = ws[b - 1].index + ws[b - 1][0].length;
  const r = document.createRange(); r.setStart(node, s); r.setEnd(node, e);
  const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
  const vv = window.visualViewport; main.scrollTop += r.getBoundingClientRect().top - want; main.dispatchEvent(new Event('scroll')); await raf();
  const rs = [...r.getClientRects()].map(q => ({t: q.top, b: q.bottom, l: q.left, r: q.right}));
  const f = rs[0], l = rs[rs.length - 1], bb = r.getBoundingClientRect();
  return {vvh: vv.height, vvtop: vv.offsetTop, scrollY: main.scrollTop, wantTop: want, rects: rs, top: Math.min(...rs.map(q => q.t)), bottom: Math.max(...rs.map(q => q.b)), left: bb.left, right: bb.right}; }"""
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

    CASES = (
        ("1 line, 42%", [0, 0, 2, 0.42], 1, True),
        ("1 line, 47%", [0, 0, 2, 0.47], 1, True),
        ("1 line, 53%", [0, 0, 2, 0.53], 1, True),
        ("1 line, 55%", [0, 0, 2, 0.55], 1, True),
        ("2 lines, 42%", [1, 0, 12, 0.42], 2, True),
        ("2 lines, 47%", [1, 0, 12, 0.47], 2, True),
        ("2 lines, 53%", [1, 0, 12, 0.53], 2, True),
        ("2 lines, 55%", [1, 0, 12, 0.55], 2, True),
        ("1 line, 25% (outside the zone: as V105)", [0, 0, 2, 0.25], 1, False),
        ("1 line, 70% (outside the zone: as V105)", [0, 0, 2, 0.70], 1, False),
    )
    SHOTS = {"1 line, 47%": "0.47 1 строка", "2 lines, 53%": "0.53 2 строки", "1 line, 70% (outside the zone: as V105)": "0.70"}
    for name, args, want, grey in CASES:
        s, m = show(args)
        n = len(s["rects"])
        shot = os.environ.get("QA_SHOT_DIR")
        if shot and dev == "iphone14" and name in SHOTS:
            pg.screenshot(path=os.path.join(shot, f"2026.11.20_V107_iPhone_{SHOTS[name]}.png"))
        ev = {"menu": m, "sel": {k: s[k] for k in ("top", "bottom", "left", "right")}, "rects": n, "vh": vh}
        check(dev, f"{name}: the selection really is {'one line' if want == 1 else 'several lines'}", (n == 1) == (want == 1), ev)
        check(dev, f"{name}: the panel covers no selection rect", not overlaps(m, s["rects"]), ev)
        dist = (m["t"] - s["bottom"]) if m["t"] >= s["bottom"] else (s["top"] - m["b"])
        if grey:
            check(dev, f"{name}: grey zone -> the panel is >= 60 px from the selection (outside the iOS menu zone on both sides)", dist >= 60, dict(ev, dist=dist))
        else:
            check(dev, f"{name}: outside the zone -> V105 (14..32 px on the free side)", 14 <= dist <= 32, dict(ev, dist=dist))
    b.close()


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        try:
            run(p, dev, eng, opts)
        except Exception as e:  # noqa: BLE001
            check(dev, "scenario ran to the end", False, repr(e)[:500])

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
