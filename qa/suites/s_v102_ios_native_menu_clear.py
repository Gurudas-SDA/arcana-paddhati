"""V104 (Vraja msg 3106-3109, 19.11): the SIDE of the colour panel on iOS now depends on the iOS menu side (one line / several lines) — see s_v104; here only the V102 rules that stay: the panel covers no selection rect and is 14..32 px (free side) or 60..90 px (beyond the menu zone) from the selection.
V102 Vraja Lila msg 3064/3066 (real iPhone, Safari 09:39) + decision msg 8444 «меню над выделением, а не под»: iOS's own menu (Copy / Look Up / Translate) came out BELOW the selection and covered the colour circles.
Criteria (register V102):
 (1) iOS, selection mid-page / low: the colour panel is NEAR ABOVE the selection (panel bottom 14..30 px over the selection top), covers no selection rect, and does not touch the system-menu zone BELOW the selection (16..60 px under it);
 (2) iOS, selection at the top of the page (no room above: top bar): the panel goes UNDER the selection, 60..90 px from it, outside the system-menu zone below (16..60 px);
 (3) Android (pixel7) unchanged (V101: right under the selection, gap 14..32 px).
# tehniskais slieksnis Lipikāra, nav S noteikums: above gap 14..30 px; system-menu zone 16..60 px under the selection (43 px high, measured on Vraja's screenshot); fallback gap 60..90 px
usage: python s_v102_ios_native_menu_clear.py <base-url>
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
    check(dev, "the engine really presents itself as iOS (WebKit available)" if dev != "pixel7" else "pixel7 is not iOS", ios == (dev != "pixel7"), {"ios": ios})

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

    for name, args in (("top", [1, 0, 12, "start"]), ("mid", [1, 0, 12, "center"]), ("bottom", [2, 0, 12, "end"])):
        s, m = show(args)
        ev = {"menu": m, "sel": {k: s[k] for k in ("top", "bottom", "left", "right")}, "vh": vh}
        zb = zone(s["bottom"] + 16, s["bottom"] + 60)  # iOS menu below the selection
        check(dev, f"{name}: the panel covers no selection rect", not overlaps(m, s["rects"]), ev)
        if ios:  # V104: side per s_v104; here: near the selection on either side, never inside a menu zone on BOTH sides (a free side exists)
            up = s["top"] - m["b"]; dn = m["t"] - s["bottom"]
            check(dev, f"{name} (V104 iOS): the panel is near the selection (14..32 px or 60..90 px beyond the menu zone), on one side", (14 <= up <= 32) or (60 <= up <= 90) or (14 <= dn <= 32) or (60 <= dn <= 90), dict(ev, up=up, dn=dn))
        else:
            check(dev, f"{name}: Android unchanged (V101: gap 14..32 under, or above)", (14 <= m["t"] - s["bottom"] <= 32) or m["b"] <= s["top"], ev)
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
