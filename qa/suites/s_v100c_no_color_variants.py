"""V100c — Vraja Lila msg 8358: a note without a colour = the sign in a circle (variant B) + a light dotted underline under the fragment; two ways to choose «без цвета» (flag `ap.hlNoColor`):
 variant 1: a struck-through circle before the five colours (card and note window) = «без цвета»; variant 2: the pressed colour is tapped again to take it off,
 a new note with text and no colour chosen has none. In both: taking the colour off KEEPS the note (the text); the underline is there; the sign covers no letter.
# tehniskais slieksnis Lipikāra, nav S noteikums: overlap tolerance 0.5 px between the sign's box and a letter's box
usage: python s_v100c_no_color_variants.py <base-url>
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



UNDER = "() => { const h = CSS.highlights.get('hl-nc'); return h ? h.size : 0; }"


def run(p, dev, eng, opts, variant):
    try:
        b = getattr(p, eng).launch()
    except Exception:
        b = p.chromium.launch()
        opts = {k: v for k, v in opts.items() if k != "user_agent"}
    c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce", **opts)
    c.add_init_script("try{if(!sessionStorage.getItem('v100cseed')){sessionStorage.setItem('v100cseed','1');localStorage.removeItem('ap.highlights');}"
                      f"localStorage.setItem('ap.hlNoColor','{variant}');localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');}}catch(e){{}}")
    pg = c.new_page()
    pg.goto(f"{BASE}/ru-iast/{PAGE}/", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    pg.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important}")
    tag = f"{dev} v{variant}"
    text0 = pg.evaluate(TEXT)

    # a coloured note, then the colour taken off
    pg.evaluate(SELECT, [0, 1, 7])
    pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    pg.locator("[data-hl-menu] [data-hl-note]").click()
    pg.wait_for_selector("[data-hl-editor] textarea", state="visible", timeout=4000)
    pg.locator("[data-hl-editor] textarea").fill("Заметка V100c")
    pg.locator("[data-hl-editor] [data-hl-color='2']").click()
    pg.locator("[data-hl-editor] [data-hl-save]").click()
    pg.wait_for_timeout(500)
    check(tag, "coloured note stored", [x["color"] for x in items(pg)] == [2], items(pg))
    pg.wait_for_selector("[data-hl-marker]", timeout=4000)
    pg.locator("[data-hl-marker]").first.click()
    pg.wait_for_selector("[data-hl-card]", state="visible", timeout=4000)
    nbtn = pg.locator("[data-hl-card] [data-hl-nocolor-btn]").count()
    check(tag, "card: the struck-through circle is there only in variant 1", nbtn == (1 if variant == "1" else 0), nbtn)
    if variant == "1":
        pg.locator("[data-hl-card] [data-hl-nocolor-btn]").click()
    else:
        pg.locator("[data-hl-card] [data-hl-color='2']").click()  # the same colour again
    pg.wait_for_timeout(500)
    its = items(pg)
    check(tag, "colour off: the note (text) stays, no colour", len(its) == 1 and its[0]["color"] == -1 and its[0]["note"] == "Заметка V100c", its)
    check(tag, "the dotted underline is there (hl-nc), no colour painted", pg.evaluate(UNDER) == 1 and pg.evaluate(PAINTED) == [0, 0, 0, 0, 0], [pg.evaluate(UNDER), pg.evaluate(PAINTED)])
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)
    pg.evaluate("() => document.querySelector('[data-hl-gap]').scrollIntoView({block: 'center'})")
    pg.wait_for_timeout(500)
    ov = pg.evaluate(OVERLAP)
    check(tag, "the sign covers no letter", len(ov) >= 1 and all(not o["hits"] and o["near"] > 0 for o in ov), ov)
    check(tag, "the book's text is unchanged", pg.evaluate(TEXT) == text0)

    # a new note with text and no colour chosen
    pg.evaluate(SELECT, [2, 1, 7])
    pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    pg.locator("[data-hl-menu] [data-hl-note]").click()
    pg.wait_for_selector("[data-hl-editor] textarea", state="visible", timeout=4000)
    en = pg.locator("[data-hl-editor] [data-hl-nocolor-btn]").count()
    check(tag, "note window: the struck-through circle only in variant 1", en == (1 if variant == "1" else 0), en)
    pg.locator("[data-hl-editor] textarea").fill("Новая без цвета")
    if variant == "1":
        pg.locator("[data-hl-editor] [data-hl-nocolor-btn]").click()
    pg.locator("[data-hl-editor] [data-hl-save]").click()
    pg.wait_for_timeout(500)
    new = [x for x in items(pg) if x.get("note") == "Новая без цвета"]
    check(tag, "a new note with text and no colour chosen has no colour", len(new) == 1 and new[0]["color"] == -1, items(pg))
    check(tag, "both notes underlined", pg.evaluate(UNDER) == 2, pg.evaluate(UNDER))
    b.close()


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        for v in ("1", "2"):
            try:
                run(p, dev, eng, opts, v)
            except Exception as e:  # noqa: BLE001
                check(f"{dev} v{v}", "scenario ran to the end", False, repr(e)[:500])

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
