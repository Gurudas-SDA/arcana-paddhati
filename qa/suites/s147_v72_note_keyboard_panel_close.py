"""V72 — Vraja Lila 04.11 msg 2406–2407 and 2409 (corrections to V71; Vraja Lila is responsible for the interface: her words are the decision)
# V72 — Vraja Lila 04.11 msg 2406–2407 (дословно): «отлично, одно замечание, смотри как сейчас и как надо» + 2 скриншота iPhone:
#   КАК СЕЙЧАС: окно «Заметка» остаётся внизу, клавиатура и системная полоска закрывают поле «Ваша заметка» и кнопки «Удалить / Отмена / Сохранить».
#   КАК НАДО: окно при клавиатуре поднято вверх экрана, видны название, цитата, цвета, поле с вводимым текстом и все три кнопки.
# msg 2409 (дословно): «так де когда нажимаю на закладку или заметку в боковой панели, оно перемптывает куда надо, но панельне закрывается
#   и мне самому приходится её закрывать»
Criteria (register V72):
 (1) with the keyboard open (visualViewport shorter) the window «Заметка» lies WHOLLY inside the visible part: title, quote, colours, the field,
     «Удалить / Отмена / Сохранить» and ✕ are not cut and not under the keyboard; the window is scrollable only when it cannot fit; without the
     keyboard the window is where it was (centred, whole);
 (2) a tap on a bookmark or on a note in the side panel goes to the place AND the panel closes by itself — phone and computer alike.
# tehniskais slieksnis Lipikāra, nav S noteikums: the keyboard is imitated by overriding window.visualViewport height/offsetTop and firing its
# resize event (Playwright has no real soft keyboard); keyboard height 336 px (iPhone) / 300 px (Android); settle 600-1500 ms.
usage: python s147_v72_note_keyboard_panel_close.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
results = []
PAGE = "daily-duties-brahma-muhurta"
OTHER = "introduction"
KB = {"iphone14": 336, "pixel7": 300}


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
# keyboard imitation: the layout viewport stays (as on iOS), only visualViewport shrinks
KEYBOARD = """(kb) => { const vv = window.visualViewport; if (!window.__vvfake) { window.__vvfake = {h: null, top: 0};
  Object.defineProperty(vv, 'height', {get: () => window.__vvfake.h == null ? window.innerHeight : window.__vvfake.h, configurable: true});
  Object.defineProperty(vv, 'offsetTop', {get: () => window.__vvfake.top, configurable: true}); }
  window.__vvfake.h = kb ? window.innerHeight - kb : null; window.__vvfake.top = 0;
  vv.dispatchEvent(new Event('resize')); vv.dispatchEvent(new Event('scroll')); }"""
PARTS = """() => { const r = e => { if (!e) return null; const b = e.getBoundingClientRect(); return {t: Math.round(b.top), b: Math.round(b.bottom), l: Math.round(b.left), r: Math.round(b.right)}; };
  const card = document.querySelector('[data-hl-modal=editor] [role=dialog]');
  return {vvh: window.visualViewport.height, iw: innerWidth, card: r(card), close: r(card && card.querySelector('[aria-label]')),
    title: r(card && card.querySelector('h2')), quote: r(document.querySelector('[data-hl-editor-quote]')),
    colors: [...card.querySelectorAll('[data-hl-color]')].map(r), field: r(card.querySelector('textarea')),
    del: r(card.querySelector('[data-hl-editor-delete]')), cancel: r(card.querySelector('[data-hl-cancel]')), save: r(card.querySelector('[data-hl-save]'))}; }"""


def inside(b, vvh, iw):
    return b is not None and b["t"] >= -1 and b["b"] <= vvh + 1 and b["l"] >= -1 and b["r"] <= iw + 1


def open_page(c, page=PAGE):
    pg = c.new_page()
    pg.goto(f"{BASE}/ru-iast/{page}/", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    pg.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important}")
    return pg


def open_panel(pg, tab):
    pg.evaluate("() => { if (!document.querySelector('[data-sidebar-tabs]')) document.querySelector('[data-reader-action=contents]').click(); }")
    pg.wait_for_selector("[data-sidebar-tab]", timeout=8000)
    pg.wait_for_timeout(500)
    pg.evaluate("(k) => document.querySelector(`[data-sidebar-tab=${k}]`).click()", tab)
    pg.wait_for_timeout(400)


PANEL_OPEN = "() => { const t = document.querySelector('[data-sidebar-tabs]'); return !!t && t.getBoundingClientRect().width > 0 && !t.closest('[inert]'); }"


def run(p, dev, eng, opts, layout="page"):
    dev0 = dev
    dev = f"{dev0}/{layout}"
    b = getattr(p, eng).launch()
    c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce", **opts)
    c.add_init_script("try{if(!sessionStorage.getItem('v72seed')){sessionStorage.setItem('v72seed','1');localStorage.removeItem('ap.highlights');"
                      "localStorage.setItem('ap.bookmarks',JSON.stringify({v:1,items:[{id:'bk1',section:'introduction',anchor:null,block:0,lang:'ru-iast',time:5},"
                      "{id:'bk2',section:'daily-duties-brahma-muhurta',anchor:null,block:0,lang:'ru-iast',time:6}]}));}"
                      f"localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('ap.readerLayout','{layout}');}}catch(e){{}}")
    pg = open_page(c)
    quote = pg.evaluate(SELECT, [0, 2, 9])
    pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    pg.locator("[data-hl-menu] [data-hl-color='1']").click()
    pg.wait_for_timeout(400)
    # a note to open (so that «Удалить» is in the window as well)
    pg.evaluate(SELECT, [1, 1, 8])
    pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    pg.locator("[data-hl-menu] [data-hl-note]").click()
    pg.wait_for_selector("[data-hl-editor] textarea", state="visible", timeout=4000)
    pg.locator("[data-hl-editor] textarea").fill("Тестовая заметка V72")
    pg.locator("[data-hl-editor] [data-hl-save]").click()
    pg.wait_for_timeout(500)

    # (1) the window «Заметка» over the keyboard
    if dev0 in KB and layout == "page":
        open_panel(pg, "notes")
        pg.locator("[data-note-row] [data-note-edit]").first.click()
        pg.wait_for_selector("[data-hl-editor] textarea", state="visible", timeout=4000)
        pg.wait_for_timeout(500)
        calm = pg.evaluate(PARTS)
        check(dev, "no keyboard: the window is whole and centred as before", inside(calm["card"], calm["vvh"], calm["iw"])
              and abs((calm["card"]["t"] + calm["card"]["b"]) / 2 - calm["vvh"] / 2) < 60, calm)
        pg.evaluate(KEYBOARD, KB[dev0])
        pg.wait_for_timeout(900)
        k = pg.evaluate(PARTS)
        names = ["card", "close", "title", "quote", "field", "del", "cancel", "save"]
        bad = [n for n in names if not inside(k[n], k["vvh"], k["iw"])] + [f"color{i}" for i, x in enumerate(k["colors"]) if not inside(x, k["vvh"], k["iw"])]
        check(dev, "keyboard open: title, quote, colours, field, «Удалить / Отмена / Сохранить» and ✕ are all above the keyboard", not bad and len(k["colors"]) == 4, [bad, k])
        pg.evaluate(KEYBOARD, 0)
        pg.wait_for_timeout(700)
        back = pg.evaluate(PARTS)
        check(dev, "keyboard closed again: the window is back to where it was", abs(back["card"]["t"] - calm["card"]["t"]) <= 2 and abs(back["card"]["b"] - calm["card"]["b"]) <= 2, [calm["card"], back["card"]])
        pg.locator("[data-hl-editor] [data-hl-cancel]").click()
        pg.wait_for_timeout(400)

    # real bookmarks and notes carry the subsection (anchor / sub): the link then has a #hash
    anchor = pg.evaluate("""() => { const h = [...document.querySelectorAll('.app-main article [id]')].find(e => /^H[1-4]$/.test(e.tagName) || e.querySelector('h2,h3')); return h ? h.id : null; }""")
    check(dev, "the chapter has a subsection with an id (to test links with #hash)", bool(anchor), anchor)
    pg.evaluate("""(a) => { const o = JSON.parse(localStorage.getItem('ap.highlights')); o.items.forEach(i => { i.sub = a; }); localStorage.setItem('ap.highlights', JSON.stringify(o));
      const bm = JSON.parse(localStorage.getItem('ap.bookmarks')); bm.items.push({id: 'bk3', section: 'daily-duties-brahma-muhurta', anchor: a, block: 0, lang: 'ru-iast', time: 7}); localStorage.setItem('ap.bookmarks', JSON.stringify(bm)); }""", anchor)
    pg.reload(wait_until="networkidle")
    pg.wait_for_timeout(1200)

    # (2) the panel closes by itself after a tap on a bookmark / a note (the same page and another page)
    cases = [("bookmarks", "[data-bookmark-row][data-bookmark-id=bk2] a", "bookmark, same page"),
             ("bookmarks", "[data-bookmark-row][data-bookmark-id=bk3] a", "bookmark with a subsection (#hash), same page"),
             ("notes", "[data-note-row] [data-note-open]", "note with a subsection (#hash), same page"),
             ("bookmarks", "[data-bookmark-row][data-bookmark-id=bk1] a", "bookmark, other page")]
    for tab, sel, name in cases:
        open_panel(pg, tab)
        pg.evaluate("() => { const m = document.querySelector('.app-main'); if (m) m.scrollTop = 0; }") if "same" in name else None
        pg.locator(sel).first.click()
        pg.wait_for_timeout(2200)
        check(dev, f"{name}: the panel closed by itself", not pg.evaluate(PANEL_OPEN), name)
    # a note on another page
    pg.goto(f"{BASE}/ru-iast/{OTHER}/", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    open_panel(pg, "notes")
    pg.locator("[data-note-row] [data-note-open]").first.click()
    pg.wait_for_timeout(3000)
    check(dev, "note, other page: the panel closed by itself", not pg.evaluate(PANEL_OPEN))
    b.close()


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        for layout in ("page", "scroll"):
            try:
                run(p, dev, eng, opts, layout)
            except Exception as e:  # noqa: BLE001
                check(f"{dev}/{layout}", "scenario ran to the end", False, repr(e)[:500])

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
