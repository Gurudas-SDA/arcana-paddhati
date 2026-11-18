"""iOS placement changed in V102 (Vraja msg 3069, 18.11): on iOS (iPhone, iPad) the panel is 14..30 px ABOVE the selection, clear of the native menu zone UNDER it (16..60 px); the V101 «under the selection» asserts below are kept for Android only.
V101 Vraja Lila msg 8393 «делаем так»: на iPhone панель цветов сразу под выделением; нет места — над, выше системного меню; Android/компьютер — как было.
V101b Vraja Lila msg 8395/8396 «да, конечно рядом… смысл кидать её так низко и далеко»: то же самое на Android (Chrome) и iPad; компьютер (мышь) — как было.
Vraja 8394 «не будет ли она загораживать выделение»: панель не накрывает ни прямоугольники выделения (все строки), ни нижний маркер выделения.
Criteria (register V101):
 (1) iPhone/Android/iPad, selection mid-page: panel top - selection.bottom is between 14 and 32 px (right under; room for the lower handle); the panel overlaps no selection rect; horizontally centred at the selection, 16 px side margins kept;
 (2) iPhone/Android/iPad, selection at the bottom of the screen: the panel is ABOVE the selection, panel.bottom <= selection.top - 48 (the system bar sits right above the selection), no overlap with the rects;
 (3) Android (pixel7) and iPad (V101b, Vraja 8395/8396): the same two scenarios as on iPhone; desktop (mouse): placement as in V100 (above the selection, left edge at the selection).
# tehniskais slieksnis Lipikāra, nav S noteikums: gap 14..32 px (handle ~12 px), 48 px system bar reserve, 16 px side margins
usage: python s_v101_ios_panel_under_selection.py <base-url>
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
    vw = pg.evaluate("innerWidth")
    vh = pg.evaluate("innerHeight")
    ios = True  # V101b (Vraja 8395/8396): the same placement on iPhone, Android and iPad
    is_ios = pg.evaluate("/iPhone|iPad|iPod/.test(navigator.userAgent)")  # V102: iOS differs

    def show(args):
        s = pg.evaluate(SELECT, args)
        pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
        pg.wait_for_timeout(500)
        return s, pg.evaluate(MENU)

    # mid-page selection (two lines, several rects)
    s, m = show([1, 0, 12, "center"])
    ev = {"menu": m, "sel": {k: s[k] for k in ("top", "bottom", "left", "right")}, "vh": vh}
    if ios:
        gap = m["t"] - s["bottom"]
        if is_ios:  # V102 (Vraja msg 3069)
            d = s["top"] - m["b"]
            check(dev, "mid-page (V102 iOS): the panel is NEAR ABOVE the selection (14..30 px)", 14 <= d <= 30, dict(ev, d=d))
            check(dev, "mid-page (V102 iOS): the panel covers no selection rect and not the native menu zone under the selection (16..60 px)", not overlaps(m, s["rects"]) and not overlaps(m, [{"t": s["bottom"] + 16, "b": s["bottom"] + 60, "l": -1e6, "r": 1e6}]), ev)
        else:
            check(dev, "mid-page: the panel is right under the selection (gap 14..32 px)", 14 <= gap <= 32, ev)
            check(dev, "mid-page: the panel covers no selection rect and not the lower handle (>= 14 px below)", not overlaps(m, s["rects"]) and m["t"] >= s["bottom"] + 14, ev)
        w = m["r"] - m["l"]
        f0, l0 = s["rects"][0], s["rects"][-1]  # the app takes the selection span from the first line's left to the last line's right
        exp = max(16, min((min(f0["l"], l0["l"]) + l0["r"]) / 2 - w / 2, vw - 16 - w))
        check(dev, "mid-page: centred at the selection, inside the screen with 16 px margins", abs(m["l"] - exp) <= 2 and m["l"] >= 15.5 and m["r"] <= vw - 15.5, dict(ev, exp=exp))
    else:
        # as in V100: a phone — fixed at the bottom of the screen
        check(dev, "mid-page (V100 unchanged): the panel is at the bottom of the screen", m["b"] >= vh - 24 and m["t"] > s["bottom"], ev)

    # selection low on the screen
    s, m = show([2, 0, 12, "end"])
    ev = {"menu": m, "sel": {k: s[k] for k in ("top", "bottom", "left", "right")}, "vh": vh}
    check(dev, "low: the selection really is low on the screen", s["bottom"] > vh - 200, ev)
    if ios:
        if is_ios:  # V102 (Vraja msg 3069)
            d = s["top"] - m["b"]
            check(dev, "low (V102 iOS): the panel is NEAR ABOVE the selection (14..30 px)", 14 <= d <= 30, dict(ev, d=d))
        else:
            check(dev, "low: the panel is ABOVE the selection, above the system bar (panel.bottom <= selection.top - 48)", m["b"] <= s["top"] - 48, ev)
        check(dev, "low: the panel covers no selection rect", not overlaps(m, s["rects"]), ev)
    else:
        check(dev, "low (V100 unchanged): the panel is at the top of the screen", m["t"] <= 16 and m["b"] <= vh, ev)
    b.close()


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        try:
            run(p, dev, eng, opts)
        except Exception as e:  # noqa: BLE001
            check(dev, "scenario ran to the end", False, repr(e)[:500])
    # desktop: as in V100 — above the selection, left edge at the selection
    try:
        b = p.chromium.launch()
        c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce", viewport={"width": 1280, "height": 800})
        c.add_init_script("try{localStorage.removeItem('ap.highlights');localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');}catch(e){}")
        pg = c.new_page()
        pg.goto(f"{BASE}/ru-iast/{PAGE}/", wait_until="networkidle")
        pg.wait_for_timeout(1200)
        pg.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important}")
        s = pg.evaluate(SELECT, [1, 2, 8, "center"])
        pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
        pg.wait_for_timeout(500)
        m = pg.evaluate(MENU)
        check("desktop", "panel above the selection, left edge at the selection (V100 unchanged)", m["b"] <= s["top"] and abs(m["l"] - s["left"]) <= 2, {"menu": m, "sel": s})
        b.close()
    except Exception as e:  # noqa: BLE001
        check("desktop", "scenario ran to the end", False, repr(e)[:500])

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
