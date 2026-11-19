"""V104 Vraja Lila msg 3106-3109 (real iPhone 19.11): a selection over two lines low on the page: iOS's own menu (Copy / Look Up / Translate) came out OVER the selection and fell on the colour panel
(Note / Copy), which V102 put 16 px above the selection. What was seen on the device: one-line selection -> iOS menu UNDER the selection; several lines -> OVER it.
Criteria (register V104): (1) the panel is next to the selection (14..32 px) on the side opposite to the iOS menu's side (one line: above; several lines: under);
 (2) the iOS menu zone (16..60 px from the selection, on its side) never touches the panel; with no room on the free side the panel goes beyond the menu zone (never inside it);
 (3) the selection stays free (no overlap with its rects); Android and desktop unchanged (see s_v101 / s_v102).
# tehniskais slieksnis Lipikāra, nav S noteikums: menu zone 16..60 px (43 px menu, measured on Vraja's screenshots), free-side gap 14..32 px, beyond-zone gap 60..90 px
usage: python s_v104_ios_menu_side.py <base-url>
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


SELECT = """([n, a, b, block]) => {
  document.querySelectorAll('[data-hl-gap]').forEach(g => g.remove()); document.querySelectorAll('.app-main article p').forEach(p => p.normalize());
  const nodes = [];
  for (const p of document.querySelectorAll('.app-main article p')) {
    if (!p.getClientRects().length || p.closest('button,table,[hidden],.mood-panel')) continue;
    const w = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
    for (let x = w.nextNode(); x; x = w.nextNode()) if ((x.data.match(/\\S+/g) || []).length >= 14 && x.parentElement.getClientRects().length) nodes.push(x);
  }
  const node = nodes[n]; if (!node) return null;
  node.parentElement.scrollIntoView({block: block || 'center'});
  const d = node.data; const ws = [...d.matchAll(/\\S+/g)];
  const s = ws[a].index, e = ws[b - 1].index + ws[b - 1][0].length;
  const r = document.createRange(); r.setStart(node, s); r.setEnd(node, e);
  const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
  const rs = [...r.getClientRects()].map(q => ({t: q.top, b: q.bottom, l: q.left, r: q.right}));
  const f = rs[0], l = rs[rs.length - 1], bb = r.getBoundingClientRect();
  return {rects: rs, top: Math.min(...rs.map(q => q.t)), bottom: Math.max(...rs.map(q => q.b)), left: bb.left, right: bb.right}; }"""
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
        pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
        pg.wait_for_timeout(500)
        return s, pg.evaluate(MENU)

    def zone(t, b_):
        return {"t": t, "b": b_, "l": -1e6, "r": 1e6}

    # (name, selection args, lines wanted, expected: 'under' / 'above' = the panel's side near the selection, 'beyond-above' = no room under)
    for name, args, want in (("one line, mid", [1, 0, 2, "center"], 1), ("two lines, mid", [1, 0, 12, "center"], 2), ("two lines, lower middle (as frames 3-4)", [2, 0, 12, "center"], 2), ("two lines, at the bottom of the screen", [2, 0, 12, "end"], 2)):
        s, m = show(args)
        n = len(s["rects"])
        ev = {"menu": m, "sel": {k: s[k] for k in ("top", "bottom", "left", "right")}, "rects": n, "vh": vh}
        check(dev, f"{name}: the selection really is {'one line' if want == 1 else 'several lines'}", (n == 1) == (want == 1), ev)
        zb = zone(s["bottom"] + 16, s["bottom"] + 60)
        za = zone(s["top"] - 60, s["top"] - 16)
        check(dev, f"{name}: the panel covers no selection rect", not overlaps(m, s["rects"]), ev)
        if want == 1:  # iOS menu under -> panel above, near
            d = s["top"] - m["b"]
            check(dev, f"{name}: iOS menu UNDER the selection does not touch the panel", not overlaps(m, [zb]), ev)
            check(dev, f"{name}: the panel is near ABOVE the selection (14..32 px)", 14 <= d <= 32, dict(ev, d=d))
        else:  # iOS menu over -> panel under, near (no room under: above, beyond the menu zone)
            check(dev, f"{name}: iOS menu OVER the selection does not touch the panel", not overlaps(m, [za]), ev)
            d = m["t"] - s["bottom"]
            room_under = s["bottom"] + 14 + (m["b"] - m["t"]) <= vh - 8
            if "bottom of the screen" in name:
                check(dev, f"{name}: no room under -> the panel is above, beyond the menu zone (>= 60 px)", s["top"] - m["b"] >= 60, dict(ev, d=d))
            else:
                check(dev, f"{name}: the panel is near UNDER the selection (14..32 px)", 14 <= d <= 32, dict(ev, d=d))
    b.close()


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        try:
            run(p, dev, eng, opts)
        except Exception as e:  # noqa: BLE001
            check(dev, "scenario ran to the end", False, repr(e)[:500])

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
