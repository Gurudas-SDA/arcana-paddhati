"""Windows: dimming black 60 % without blur, bottom bar never dimmed; ✕ on the top line (Vraja Lila V18, 20.10.2026).

Task (maket approved: msg 5603 «идеально», 5610 «подтверждаю с ходу»; 5606, 5608):
1) the page behind «Настроение Гурудева», the install window and «Содержание» is dimmed the same — black 60 %,
   no blur; while «Содержание» is open the bottom bar (‹ Назад · chapter % · Вперёд ›) is not dimmed (5606);
2) the window's ✕ sits on the level of the top line («НАСТРОЕНИЕ ГУРУДЕВА · 2»): phone — at the right edge, the
   header's top padding as before (10 px); desktop (≥ 1024 px) — header top padding 20 px, ✕ 6 px in from the
   edge (maket: margin-right 6 px); the «Аа» panel's ✕ on its top line at the right.
# tehniskais slieksnis Lipikāra, nav S noteikums: «on the level» = the ✕ glyph's centre within 6 px of the top
#   line's centre; dimming edge = bar top ±1 px; colour read as computed rgba.
usage: python s68_dim_close_x.py <base-url>
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
DIM = "rgba(0, 0, 0, 0.6)"
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


DIMMING = """(sel) => { const d = document.querySelector(sel); if (!d) return null; const c = getComputedStyle(d);
  return {bg: c.backgroundColor, filter: c.backdropFilter || c.webkitBackdropFilter || 'none', bottom: d.getBoundingClientRect().bottom}; }"""
# ✕ glyph (the svg) against the top line and the box it sits in
XPOS = """([box, line, x]) => { const b = document.querySelector(box), l = document.querySelector(line), s = document.querySelector(x);
  if (!b || !l || !s) return null; const rb = b.getBoundingClientRect(), rl = l.getBoundingClientRect(), rs = s.getBoundingClientRect();
  const h = s.closest('header, .reader-panel-head'); const hc = h && getComputedStyle(h);
  return {lineMid: +((rl.top + rl.bottom) / 2).toFixed(1), xMid: +((rs.top + rs.bottom) / 2).toFixed(1),
    rightGap: +(rb.right - s.closest('button').getBoundingClientRect().right).toFixed(1), headPadTop: hc && hc.paddingTop,
    closeMarginRight: getComputedStyle(s.closest('button')).marginRight, w: innerWidth}; }"""


def show_bars(pg):
    for _ in range(3):
        if pg.evaluate("!!document.querySelector('.reader-chrome[data-shown]')"):
            return
        pg.mouse.click(200, 430)
        pg.wait_for_timeout(450)


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        c = b.new_context(service_workers="block", locale="ru-RU", **opts)
        c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');")
        pg = c.new_page()
        pg.goto(f"{BASE}/ru-iast/{PAGE}/", wait_until="networkidle")
        pg.wait_for_timeout(900)
        desk = pg.viewport_size["width"] >= 1024

        # 1. «Содержание»: dimming black 60 %, no blur, ends at the bottom bar's top; the bar not under it
        show_bars(pg)
        pg.evaluate("document.querySelector('[data-reader-action=contents]').click()")
        pg.wait_for_timeout(600)
        d = pg.evaluate(f"({DIMMING})('.mobile-menu[data-open] > .sidebar-backdrop')")
        bar_top = pg.evaluate("document.querySelector('.reader-bar-bottom').getBoundingClientRect().top")
        hit = pg.evaluate("""() => { const r = document.querySelector('.reader-bar-bottom').getBoundingClientRect();
          const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!(e && e.closest('.reader-bar-bottom')); }""")
        check(dev, "«Содержание»: dimming black 60 %, no blur", d and d["bg"] == DIM and d["filter"] in ("none", ""), d)
        # V35 (Vraja Lila msg 1226 / 1319, replaces 5606 here): the bottom bar slides away and the dimming is one layer
        # down to the screen's bottom.
        vh = pg.viewport_size["height"]
        check(dev, "«Содержание»: V35 — the dimming reaches the screen's bottom, the bottom bar slid away", d and abs(d["bottom"] - vh) <= 1 and not hit and bar_top >= vh - 1,
              {"dimBottom": d and d["bottom"], "barTop": bar_top, "barOnTop": hit, "vh": vh})
        pg.evaluate("document.querySelector('.mobile-menu[data-open] > .sidebar-backdrop').click()")
        pg.wait_for_timeout(700)

        # 2. «Настроение Гурудева»: dimming and ✕ on the top line
        pg.locator(".mood-toggle").first.scroll_into_view_if_needed()
        pg.locator(".mood-toggle").first.click()
        pg.wait_for_timeout(600)
        d = pg.evaluate(f"({DIMMING})('.mood-backdrop')")
        check(dev, "«Настроение»: dimming black 60 %, no blur", d and d["bg"] == DIM and d["filter"] in ("none", ""), d)
        x = pg.evaluate(f"({XPOS})(['.mood-dialog', '.mood-dialog-head .mood-label', '.mood-close svg'])")
        level = x and abs(x["xMid"] - x["lineMid"]) <= 6
        if desk:
            ok = level and x["headPadTop"] == "20px" and x["closeMarginRight"] == "6px"
            check(dev, "«Настроение» (desktop): ✕ on the top line, 6 px in from the edge, header top padding 20 px", ok, x)
        else:
            ok = level and x["headPadTop"] == "10px" and x["closeMarginRight"] == "-8px"
            check(dev, "«Настроение» (phone): ✕ on the top line at the right edge, header top padding still 10 px", ok, x)
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(500)

        # 3. «Аа» panel: ✕ on its top line at the right
        show_bars(pg)
        pg.evaluate("document.querySelector('[data-reader-action=aa]').click()")
        pg.wait_for_timeout(500)
        x = pg.evaluate(f"({XPOS})(['.reader-panel', '.reader-panel-title', '.reader-panel-close svg'])")
        check(dev, "«Аа» panel: ✕ on the top line, at the right", x and abs(x["xMid"] - x["lineMid"]) <= 6 and x["closeMarginRight"] == "-14px", x)

        # 4. install window: same dimming (opened by its own button where the page offers one)
        if pg.evaluate("!!document.querySelector('.install-backdrop')") is False:
            # the window is only in the DOM while open; check the rule itself
            got = pg.evaluate("""() => { const e = document.createElement('div'); e.className = 'install-backdrop'; document.body.appendChild(e);
              const c = getComputedStyle(e); const r = [c.backgroundColor, c.backdropFilter || 'none']; e.remove(); return r; }""")
        else:
            got = pg.evaluate("() => { const c = getComputedStyle(document.querySelector('.install-backdrop')); return [c.backgroundColor, c.backdropFilter || 'none']; }")
        check(dev, "install window: dimming black 60 %, no blur", got[0] == DIM and got[1] in ("none", ""), got)
        c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
