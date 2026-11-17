"""V100b — Vraja Lila msg 8357: palette 1 «Kindle чистая» + a 5th colour ORANGE; a note without a colour is shown by the sign at the end of the fragment (variant B).
Criteria (register V100b):
 (1) the colour panel (menu and note window) has FIVE colours; each paints its own highlight (hl-0..hl-4), the fifth is orange;
 (2) taking the colour off a fragment that has a note keeps the note (the text) and shows the sign; taking it off a fragment without a note removes the highlight;
 (3) the sign of a note covers NO letter: the line keeps a room of its own for it (the sign's box meets no letter's box), the book's text is unchanged;
 (4) deleting such a note works as before (the card's «Удалить»).
# tehniskais slieksnis Lipikāra, nav S noteikums: overlap tolerance 0.5 px between the sign's box and a letter's box
usage: python s_v100b_palette1_orange_note_sign.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7"])
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
STORE = "() => { try { return JSON.parse(localStorage.getItem('ap.highlights') || 'null'); } catch (e) { return 'bad'; } }"
PAINTED = "() => [0,1,2,3,4].map(n => { const h = CSS.highlights.get('hl-' + n); return h ? h.size : 0; })"
# every letter's box near the sign against the sign's box
OVERLAP = """() => {
  const out = []; const art = document.querySelector('.app-main article');
  for (const m of document.querySelectorAll('[data-hl-marker]')) {
    const b = m.getBoundingClientRect(); const hits = []; let near = 0;
    const w = document.createTreeWalker(art, NodeFilter.SHOW_TEXT);
    for (let x = w.nextNode(); x; x = w.nextNode()) {
      if (x.parentElement.closest('[hidden],button,svg') || !x.parentElement.getClientRects().length) continue;
      const nr = document.createRange(); nr.selectNodeContents(x); const q = nr.getBoundingClientRect();
      if (q.bottom < b.top - 40 || q.top > b.bottom + 40) continue;
      for (let i = 0; i < x.data.length; i++) {
        if (!x.data[i].trim()) continue;
        const r = document.createRange(); r.setStart(x, i); r.setEnd(x, i + 1); const c = r.getBoundingClientRect();
        if (!c.width) continue; near++;
        if (c.left < b.right - 0.5 && c.right > b.left + 0.5 && c.top < b.bottom - 0.5 && c.bottom > b.top + 0.5) hits.push(x.data[i] + '@' + Math.round(c.left) + ',' + Math.round(c.top));
      }
    }
    out.push({box: [Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)], hits, near});
  }
  return out; }"""
TEXT = "() => document.querySelector('.app-main article').textContent"


def items(pg):
    s = pg.evaluate(STORE)
    return (s or {}).get("items", []) if isinstance(s, dict) else []


def pick(pg, args, color):
    q = pg.evaluate(SELECT, args)
    pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    pg.wait_for_timeout(250)
    pg.locator(f"[data-hl-menu] [data-hl-color='{color}']").click()
    pg.wait_for_timeout(400)
    return q


def run(p, dev, eng, opts):
    try:
        b = getattr(p, eng).launch()
    except Exception:  # WebKit libs missing: same viewport + touch in Chromium
        b = p.chromium.launch()
        opts = {k: v for k, v in opts.items() if k != "user_agent"}
    c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce", **opts)
    c.add_init_script("try{if(!sessionStorage.getItem('v100bseed')){sessionStorage.setItem('v100bseed','1');localStorage.removeItem('ap.highlights');}"
                      "localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');}catch(e){}")
    pg = c.new_page()
    pg.goto(f"{BASE}/ru-iast/{PAGE}/", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    pg.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important}")
    text0 = pg.evaluate(TEXT)

    # (1) five colours
    pg.evaluate(SELECT, [0, 1, 7])
    pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    n_menu = pg.locator("[data-hl-menu] [data-hl-color]").count()
    check(dev, "the menu has FIVE colours", n_menu == 5, n_menu)
    pg.keyboard.press("Escape")
    for i in range(5):
        pick(pg, [i, 1, 7], i)
    painted = pg.evaluate(PAINTED)
    check(dev, "each of the five colours paints its own highlight (hl-0..hl-4, one each)", painted == [1, 1, 1, 1, 1], painted)
    its = items(pg)
    check(dev, "five fragments, five colours stored (0..4)", sorted(x["color"] for x in its) == [0, 1, 2, 3, 4], its)

    # (2) a note with a colour, then the colour taken off in the card
    pg.evaluate(SELECT, [5, 1, 7])
    pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    pg.locator("[data-hl-menu] [data-hl-note]").click()
    pg.wait_for_selector("[data-hl-editor] textarea", state="visible", timeout=4000)
    n_ed = pg.locator("[data-hl-editor] [data-hl-color-kind='editor']").count()
    check(dev, "the note window has FIVE colours", n_ed == 5, n_ed)
    pg.locator("[data-hl-editor] textarea").fill("Заметка V100b")
    pg.locator("[data-hl-editor] [data-hl-color='4']").click()
    pg.locator("[data-hl-editor] [data-hl-save]").click()
    pg.wait_for_timeout(500)
    noted = [x for x in items(pg) if x.get("note")]
    check(dev, "note on an orange fragment stored", len(noted) == 1 and noted[0]["color"] == 4, noted)
    pg.wait_for_selector("[data-hl-marker]", timeout=4000)
    pg.locator("[data-hl-marker]").first.click()
    pg.wait_for_selector("[data-hl-card]", state="visible", timeout=4000)
    pg.locator("[data-hl-card] [data-hl-color='4']").click()  # the current colour again = take it off
    pg.wait_for_timeout(500)
    noted = [x for x in items(pg) if x.get("note")]
    check(dev, "colour taken off: the note (the text) stays, the colour is none", len(noted) == 1 and noted[0]["color"] == -1 and noted[0]["note"] == "Заметка V100b", noted)
    check(dev, "the highlight is not painted any more (orange back to one fragment), the sign is there", pg.evaluate(PAINTED) == [1, 1, 1, 1, 1] and pg.locator("[data-hl-marker][data-hl-nocolor]").count() == 1, pg.evaluate(PAINTED))
    pg.keyboard.press("Escape")
    pg.reload(wait_until="networkidle")
    pg.wait_for_timeout(1500)
    noted = [x for x in items(pg) if x.get("note")]
    check(dev, "after reload the note without colour is still there and shows the sign", len(noted) == 1 and noted[0]["color"] == -1 and pg.locator("[data-hl-marker][data-hl-nocolor]").count() >= 1, noted)

    # (3) the sign covers no letter; the book's text is unchanged
    pg.evaluate("() => document.querySelector('[data-hl-gap]').scrollIntoView({block: 'center'})")
    pg.wait_for_timeout(600)
    ov = pg.evaluate(OVERLAP)
    check(dev, "the sign covers no letter (its box meets no letter's box)", len(ov) >= 1 and all(not o["hits"] and o["near"] > 0 for o in ov), ov)
    gaps = pg.locator("[data-hl-gap]").count()
    check(dev, "the line keeps a room for each sign (one room per note)", gaps == pg.locator("[data-hl-marker]").count() and gaps >= 1, gaps)
    check(dev, "the book's text is unchanged by the room (same text)", pg.evaluate(TEXT) == text0)
    # a coloured note too (the same room)
    pick(pg, [6, 2, 8], 2)
    pg.evaluate(SELECT, [6, 2, 8])
    pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    pg.locator("[data-hl-menu] [data-hl-note]").click()
    pg.wait_for_selector("[data-hl-editor] textarea", state="visible", timeout=4000)
    pg.locator("[data-hl-editor] textarea").fill("Вторая заметка, с цветом")
    pg.locator("[data-hl-editor] [data-hl-save]").click()
    pg.wait_for_timeout(600)
    ov = pg.evaluate(OVERLAP)
    check(dev, "with two notes (the coloured one in view): no sign covers a letter", len(ov) >= 1 and pg.locator("[data-hl-gap]").count() == 2 and all(not o["hits"] for o in ov), ov)

    # (2b) colour taken off a fragment WITHOUT a note: the highlight goes
    before = len(items(pg))
    pg.evaluate(SELECT, [3, 1, 7])
    pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    pg.locator("[data-hl-menu] [data-hl-note]").click()
    pg.wait_for_selector("[data-hl-editor] textarea", state="visible", timeout=4000)
    pg.locator("[data-hl-editor] [data-hl-color='3']").click()  # the current colour again: none
    pg.locator("[data-hl-editor] textarea").fill("")
    pg.locator("[data-hl-editor] [data-hl-save]").click()
    pg.wait_for_timeout(600)
    its = items(pg)
    check(dev, "no colour and no note: the highlight is removed (nothing to keep)", len(its) == before - 1 and all(x["color"] != 3 for x in its), its)

    # (4) deleting a note without a colour works
    pg.evaluate("() => document.querySelector('[data-hl-gap]').scrollIntoView({block: 'center'})")
    pg.wait_for_timeout(500)
    n0 = len(items(pg))
    pg.locator("[data-hl-marker][data-hl-nocolor]").first.click()
    pg.wait_for_selector("[data-hl-card]", state="visible", timeout=4000)
    pg.locator("[data-hl-card] [data-hl-card-delete]").click()
    pg.wait_for_timeout(500)
    check(dev, "delete removes the note without a colour completely", len(items(pg)) == n0 - 1 and pg.locator("[data-hl-marker][data-hl-nocolor]").count() == 0, items(pg))
    b.close()


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        try:
            run(p, dev, eng, opts)
        except Exception as e:  # noqa: BLE001
            check(dev, "scenario ran to the end", False, repr(e)[:500])

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
