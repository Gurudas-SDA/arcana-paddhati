"""V106 Vraja Lila msg 8544/8545: «когда я перехожу на неё с бокового меню, то происходит наложение цветов»
Criteria (register V106): a note opened from the side menu keeps its own colour: while the place is shown (and after the
arrival flash is over) the note's visible background is the same as before the jump, no second colour is laid over it.
Cause before the fix: ::highlight(hl-flash) (gold, translucent) was painted over ::highlight(hl-N) (the note colour) for 1.8 s.
# tehniskais slieksnis Lipikāra, nav S noteikums: colour distance <= 6 per channel (rendering rounding), flash window 1.8 s
usage: python s_v106_note_flash_no_color_overlay.py <base-url>
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from PIL import Image  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
SHOTS = os.environ.get("V106_SHOTS", "")  # dir for before/after screenshots (optional)
results = []
PAGE = "daily-duties-brahma-muhurta"


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


SELECT = """([n, a, b]) => {
  const nodes = [];
  for (const p of document.querySelectorAll('.app-main article p')) {
    if (!p.getClientRects().length || p.closest('button,table,[hidden],.mood-panel')) continue;
    const w = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
    for (let x = w.nextNode(); x; x = w.nextNode()) if ((x.data.match(/\\S+/g) || []).length >= 9 && x.parentElement.getClientRects().length) nodes.push(x);
  }
  const node = nodes[n]; if (!node) return null;
  node.parentElement.scrollIntoView({block: 'center'});
  const d = node.data; const ws = [...d.matchAll(/\\S+/g)];
  const s = ws[a].index, e = ws[b - 1].index + ws[b - 1][0].length;
  const r = document.createRange(); r.setStart(node, s); r.setEnd(node, e);
  const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
  return d.slice(s, e); }"""
# the first line box of the painted note highlight (the Highlight holds the live Range)
RECT = """(n) => { const h = CSS.highlights.get('hl-' + n); if (!h) return null;
  const r = [...h][0]; if (!r) return null; const b = r.getClientRects()[0]; if (!b) return null;
  return {x: b.left, y: b.top, w: b.width, h: b.height, vh: innerHeight, vw: innerWidth}; }"""


def mode_color(png, rect):
    """The most frequent colour inside the note's first line box = its background (text pixels are the minority)."""
    im = Image.open(io.BytesIO(png)).convert("RGB")
    sx = im.width / rect["vw"]
    box = (int(rect["x"] * sx) + 2, int(rect["y"] * sx) + 1, int((rect["x"] + rect["w"]) * sx) - 2, int((rect["y"] + rect["h"]) * sx) - 1)
    cols = im.crop(box).getcolors(maxcolors=1 << 20)
    return max(cols)[1]


def near(a, b, tol=6):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def shot(pg, rect):
    return pg.screenshot()


def run(p, dev, eng, opts):
    try:
        b = getattr(p, eng).launch()
    except Exception:  # WebKit libs missing: same viewport + touch in Chromium
        b = p.chromium.launch()
        opts = {k: v for k, v in opts.items() if k != "user_agent"}
    c = b.new_context(service_workers="block", locale="ru-RU", **opts)
    c.add_init_script("try{if(!sessionStorage.getItem('v106seed')){sessionStorage.setItem('v106seed','1');localStorage.removeItem('ap.highlights');}"
                      "localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');}catch(e){}")
    pg = c.new_page()
    pg.goto(f"{BASE}/ru-iast/{PAGE}/", wait_until="networkidle")
    pg.wait_for_timeout(1200)

    # a note with a colour (colour 1)
    txt = pg.evaluate(SELECT, [0, 2, 7])
    pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    pg.wait_for_timeout(250)
    pg.locator("[data-hl-menu] [data-hl-color='1']").click()
    pg.wait_for_timeout(400)
    pg.evaluate(SELECT, [0, 2, 7])
    pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    pg.locator("[data-hl-menu] [data-hl-note]").click()
    pg.wait_for_selector("[data-hl-editor] textarea", state="visible", timeout=4000)
    pg.locator("[data-hl-editor] textarea").fill("Заметка V106")
    pg.locator("[data-hl-editor] [data-hl-save]").click()
    pg.wait_for_timeout(600)
    pg.evaluate("() => getSelection().removeAllRanges()")
    pg.wait_for_timeout(300)

    # before: the note's own colour, no flash
    pg.evaluate("() => document.querySelector('.app-main article p')?.scrollIntoView({block: 'center'})")
    pg.wait_for_timeout(2300)
    rect0 = pg.evaluate(RECT, 1)
    check(dev, "note is painted in colour 1", bool(rect0) and txt, rect0)
    if not rect0:
        b.close()
        return
    before = mode_color(pg.screenshot(), rect0)
    if SHOTS:
        pg.screenshot(path=os.path.join(SHOTS, f"{dev}_pirms_note.png"))

    # go to the top, open the side menu → notes → the note
    pg.evaluate("() => { const m = document.querySelector('.app-main'); if (m) m.scrollTop = 0; }")
    pg.wait_for_timeout(500)
    pg.evaluate("() => { if (!document.querySelector('[data-sidebar-tabs]')) document.querySelector('[data-reader-action=contents]').click(); }")
    pg.wait_for_selector("[data-sidebar-tab]", timeout=8000)
    pg.wait_for_timeout(500)
    pg.evaluate("() => document.querySelector('[data-sidebar-tab=notes]').click()")
    pg.wait_for_timeout(500)
    pg.locator("[data-note-open]").first.click()

    # right after the jump (the flash window), then after the flash is over
    samples = []
    for wait in (500, 700):
        pg.wait_for_timeout(wait)
        rect = pg.evaluate(RECT, 1)
        if rect and 0 <= rect["y"] and rect["y"] + rect["h"] <= rect["vh"]:
            png = pg.screenshot()
            samples.append((wait, mode_color(png, rect)))
            if SHOTS and len(samples) == 1:
                pg.screenshot(path=os.path.join(SHOTS, f"{dev}_pec_note.png"))
    pg.wait_for_timeout(1500)
    rect = pg.evaluate(RECT, 1)
    late = mode_color(pg.screenshot(), rect) if rect and 0 <= rect["y"] and rect["y"] + rect["h"] <= rect["vh"] else None
    check(dev, "the note is shown after the jump from the side menu", len(samples) >= 1 and late is not None, [samples, late])
    for wait, col in samples:
        check(dev, f"during the arrival the note keeps its own colour (no second colour over it), +{wait} ms", near(col, before), {"before": before, "now": col})
    check(dev, "after the arrival flash the note colour is the same as before the jump", late is not None and near(late, before), {"before": before, "late": late})
    b.close()


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        try:
            run(p, dev, eng, opts)
        except Exception as e:  # noqa: BLE001
            check(dev, "scenario ran to the end", False, repr(e)[:500])

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
