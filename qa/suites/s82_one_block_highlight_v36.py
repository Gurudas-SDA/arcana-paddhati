"""V36 — a marked list row is ONE block: the number and its text inside one rectangle with rounded corners
(Vraja Lila msg 5962, 21.10.2026; saskarnes autors, «Стандарты» 0а).

Rule text (verbatim, Vraja Lila, on a screenshot of «11) асана для Божества;» — the number and the text lit apart):
  «такого рода выделения в таких и подобных местах, а также на будущее делай одним блоком/подложкой — цифру + текст
  одним прямоугольником со скруглёнными краями».
Places checked (every list row linked to a picture): the numbered list of the 16 articles (ch. 3.1, item 11
«асана для Божества») and the tilak list (number / place / mantra, ch. 1).
Check (iPhone 14, desktop): after a tap on the row's number, exactly ONE element of the row carries the marking band;
that band contains the number and the whole text of the row, and its corners are rounded.
# tehniskais slieksnis Lipikāra, nav S noteikums: «band» = background alpha ≥ 0.2 (the alternating stripe is 0.065);
#   «contains» = ±1 px; «rounded» = border-radius ≥ 4 px.
usage: python s82_one_block_highlight_v36.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "desktop"])
CASES = [("worship-sixteen-articles", "асана для Божества", "16 articles, 11) асана для Божества"),
         ("daily-duties-brahma-muhurta", None, "tilak list, row 2")]
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:900]}", flush=True)


FIND = """([text]) => { const rows = [...document.querySelectorAll('.app-main [data-hs-row]')]
    .filter(r => r.tagName !== 'SPAN' && (text ? r.textContent.includes(text) : r.querySelector('.hs-cell-first')));
  const r = text ? rows[0] : rows[1]; if (!r) return null;
  r.scrollIntoView({block: 'center'});
  const num = r.querySelector('.hs-cell-first') || r.querySelector('.nl-num .hs-text');
  const b = num.getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; }"""

MEASURE = """([text]) => { const rows = [...document.querySelectorAll('.app-main [data-hs-row]')]
    .filter(r => r.tagName !== 'SPAN' && (text ? r.textContent.includes(text) : r.querySelector('.hs-cell-first')));
  const r = text ? rows[0] : rows[1];
  const alpha = (c) => { const m = c.match(/rgba?\\(([^)]+)\\)/); if (!m) return 0; const p = m[1].split(',').map(Number);
    return p.length > 3 ? p[3] : 1; };
  const painted = [r, ...r.querySelectorAll('*')].filter(e => e.getClientRects().length && alpha(getComputedStyle(e).backgroundColor) >= 0.2);
  // the row's content: every text node's boxes
  const w = document.createTreeWalker(r, NodeFilter.SHOW_TEXT); const boxes = [];
  for (let n = w.nextNode(); n; n = w.nextNode()) { if (!n.textContent.trim()) continue; const rg = document.createRange();
    rg.selectNodeContents(n); for (const b of rg.getClientRects()) if (b.width && b.height) boxes.push(b); }
  const box = (b) => [Math.round(b.left), Math.round(b.top), Math.round(b.right), Math.round(b.bottom)];
  const band = painted.length === 1 ? painted[0].getBoundingClientRect() : null;
  const inside = !!band && boxes.every(b => b.left >= band.left - 1 && b.right <= band.right + 1 && b.top >= band.top - 1 && b.bottom <= band.bottom + 1);
  return {active: r.hasAttribute('data-active'), painted: painted.map(e => e.tagName.toLowerCase() + '.' + (e.className || '').toString().split(' ')[0]),
          radius: painted.length === 1 ? parseFloat(getComputedStyle(painted[0]).borderTopLeftRadius) : null,
          band: band && box(band), text: boxes.length && [Math.round(Math.min(...boxes.map(b => b.left))), Math.round(Math.max(...boxes.map(b => b.right)))], inside}; }"""

with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        for section, text, label in CASES:
            c = b.new_context(service_workers="block", locale="ru-RU", **opts)
            c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');")
            pg = c.new_page()
            pg.goto(f"{BASE}/ru-iast/{section}/", wait_until="networkidle")
            pg.wait_for_timeout(1200)
            pt = pg.evaluate(FIND, [text])
            if not pt:
                check(dev, f"{label}: the row is there", False, "not found")
                c.close()
                continue
            pg.wait_for_timeout(500)
            pt = pg.evaluate(FIND, [text])
            (pg.touchscreen.tap if opts.get("has_touch") else pg.mouse.click)(pt[0], pt[1])
            pg.wait_for_timeout(600)
            m = pg.evaluate(MEASURE, [text])
            check(dev, f"{label}: one band around number + text, rounded corners",
                  m["active"] and len(m["painted"]) == 1 and m["inside"] and (m["radius"] or 0) >= 4, m)
            c.close()
        b.close()

n = sum(results)
print(f"\n{n}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
