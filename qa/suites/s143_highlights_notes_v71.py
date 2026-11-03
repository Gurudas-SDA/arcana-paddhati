"""V71 — Vraja Lila 04.11 msg 2360/2362 (утверждаю; в файл только заметки)
# V71 — Vraja Lila 04.11 msg 2360/2362 (утверждаю; в файл только заметки)
Text highlighting and notes in the book (variant A of V70, with the corrections 04.11 / правки 2-5; Vraja Lila msg 7425: the header, ✕ and
the search field of the side panel stay as they are, the tab row gets a third tab «Заметки»).
Criteria (register V71):
 (1) a selection in the text shows the menu: 4 colour buttons (>= 48x44), «Заметка» and «Копировать» (>= 44 high); a tap on a colour
     paints it (CSS Custom Highlight, ::highlight(hl-N)), stores it in localStorage `ap.highlights`, hides the menu, clears the selection;
 (2) «Заметка» opens the editor, «Сохранить» stores the note; both survive a page reload (painted again);
 (3) the side panel has three tabs «Содержание · Закладки · Заметки» that fit the panel (no overflow), header ✕ and search stay;
     the list has rows with the quote, the note, the place; filters «Все N» / «С заметкой N» (fixed width) and 4 colours work;
     the search field filters the notes (placeholder «Поиск по заметкам»);
 (4) a tap on a row opens the place (the highlight is on the screen); the bin removes it with the toast «Отменить», which brings it back;
 (5) «Сохранить в файл» gives a .json with ONLY notes (no bookmarks) named «Арчана-паддхати — заметки YYYY-MM-DD.json»;
     «Загрузить из файла» shows a preview, adds only the new ones, a broken file changes nothing and says so; bookmarks never touched;
 (6) all three themes: the colours are the checked tones (faili/V70_проверка_цветов/kontrasts_palette.json), night green alpha 0.32.
# tehniskais slieksnis Lipikāra, nav S noteikums: settle 300-900 ms; «fits the panel» = tab right edge <= panel right edge + 1 px
usage: python s143_highlights_notes_v71.py <base-url>
"""
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7", "ipad-portrait", "desktop"])
results = []
PAGE = "introduction"
PALETTE = {"day": ["#9F6F06", "#45A28A", "#0D7DEC", "#7C2339"], "sepia": ["#9D6C08", "#319476", "#1A4BBA", "#7C2348"],
           "night": ["#EDB135", "#A7ECD4", "#66B1F6", "#D4466F"]}


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else json.dumps(evidence, ensure_ascii=False)[:600]}", flush=True)


# select words [a, b) of the n-th long visible paragraph of the chapter; returns the selected text
SELECT = """([n, a, b]) => {
  const ps = [...document.querySelectorAll('.app-main article p')].filter(p => p.textContent.trim().length > 140 && p.getClientRects().length && !p.closest('button,table,[hidden]'));
  const p = ps[n]; if (!p) return null;
  p.scrollIntoView({block: 'center'});
  const w = document.createTreeWalker(p, NodeFilter.SHOW_TEXT); const nodes = []; for (let x = w.nextNode(); x; x = w.nextNode()) nodes.push(x);
  const node = nodes.find(x => x.data.trim().length > 60); if (!node) return null;
  const d = node.data; const ws = [...d.matchAll(/\\S+/g)];
  const s = ws[a].index, e = ws[b - 1].index + ws[b - 1][0].length;
  const r = document.createRange(); r.setStart(node, s); r.setEnd(node, e);
  const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
  return d.slice(s, e); }"""
STORE = "() => { try { return JSON.parse(localStorage.getItem('ap.highlights') || 'null'); } catch (e) { return 'bad'; } }"
HLSIZE = "(n) => { const h = CSS.highlights && CSS.highlights.get('hl-' + n); return h ? h.size : 0; }"
BOX = """(sel) => [...document.querySelectorAll(sel)].map(e => { const b = e.getBoundingClientRect(); return {w: Math.round(b.width), h: Math.round(b.height), l: b.left, r: b.right, t: b.top, b: b.bottom, txt: e.textContent.trim()}; })"""


def items(pg):
    s = pg.evaluate(STORE)
    return (s or {}).get("items", []) if isinstance(s, dict) else []


def open_page(c):
    pg = c.new_page()
    pg.goto(f"{BASE}/ru-iast/{PAGE}/", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    pg.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important}")
    return pg


def open_panel(pg, tab):
    pg.evaluate("() => { if (!document.querySelector('[data-sidebar-tabs]')) document.querySelector('[data-reader-action=contents]').click(); }")
    pg.wait_for_selector("[data-sidebar-tab]", timeout=8000)
    pg.wait_for_timeout(500)
    pg.evaluate("(k) => document.querySelector(`[data-sidebar-tab=${k}]`).click()", tab)
    pg.wait_for_timeout(400)


def run_theme(p, dev, eng, opts, theme):
    tag = f"{dev}/{theme}"
    b = getattr(p, eng).launch()
    c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce", accept_downloads=True, **opts)
    c.add_init_script("try{if(!sessionStorage.getItem('v71seed')){sessionStorage.setItem('v71seed','1');localStorage.removeItem('ap.highlights');"
                      "localStorage.setItem('ap.bookmarks',JSON.stringify({v:1,items:[{id:'bk1',section:'introduction',anchor:null,block:0,lang:'ru-iast',time:5}]}));}"
                      "localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');"
                      + (f"localStorage.setItem('ap.readerTheme','{theme}');" if theme != "day" else "") + "}catch(e){}")
    pg = open_page(c)
    bm_before = pg.evaluate("() => localStorage.getItem('ap.bookmarks')")

    # (1) menu
    txt1 = pg.evaluate(SELECT, [0, 2, 7])
    check(tag, "selected a stretch of the text", bool(txt1), txt1)
    try:
        pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    except Exception:
        check(tag, "the menu shows on a selection", False, "no [data-hl-menu]")
        b.close()
        return
    colors = pg.evaluate(BOX, "[data-hl-menu] [data-hl-color]")
    check(tag, "menu: 4 colour buttons >= 48x44", len(colors) == 4 and all(x["w"] >= 48 and x["h"] >= 44 for x in colors), colors)
    acts = pg.evaluate(BOX, "[data-hl-menu] [data-hl-note], [data-hl-menu] [data-hl-copy]")
    check(tag, "menu: «Заметка» and «Копировать» >= 44 high with a caption", len(acts) == 2 and all(x["h"] >= 44 and x["txt"] for x in acts), acts)
    vp = pg.evaluate("() => [innerWidth, innerHeight]")
    mb = pg.evaluate(BOX, "[data-hl-menu]")[0]
    check(tag, "menu is whole on the screen", mb["l"] >= 0 and mb["r"] <= vp[0] and mb["t"] >= 0 and mb["b"] <= vp[1], [mb, vp])
    pg.locator("[data-hl-menu] [data-hl-color='1']").click()
    pg.wait_for_timeout(500)
    its = items(pg)
    check(tag, "colour tap stores a highlight (colour 1, the quote)", len(its) == 1 and its[0].get("color") == 1 and its[0].get("quote") == txt1, its)
    check(tag, "painted with ::highlight(hl-1)", pg.evaluate(HLSIZE, 1) == 1, pg.evaluate(HLSIZE, 1))
    check(tag, "menu hidden, selection cleared", pg.evaluate("() => !document.querySelector('[data-hl-menu]') && getSelection().isCollapsed"))
    tone = pg.evaluate("(n) => getComputedStyle(document.documentElement).getPropertyValue('--hl-' + n + '-tone').trim().toUpperCase()", 2)
    check(tag, "colour tone = the checked palette", tone == PALETTE[theme][1].upper(), [tone, PALETTE[theme][1]])
    if theme == "night":
        al = pg.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--hl-2-alpha').trim()")
        check(tag, "night green alpha 0.32", al in ("0.32", ".32"), al)

    # (2) note
    txt2 = pg.evaluate(SELECT, [1, 1, 6])
    pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    pg.locator("[data-hl-menu] [data-hl-note]").click()
    pg.wait_for_selector("[data-hl-editor] textarea", state="visible", timeout=4000)
    pg.locator("[data-hl-editor] textarea").fill("Тестовая заметка Арчана")
    pg.locator("[data-hl-editor] [data-hl-save]").click()
    pg.wait_for_timeout(500)
    its = items(pg)
    check(tag, "note stored with the highlight", len(its) == 2 and any(i.get("note") == "Тестовая заметка Арчана" and i.get("quote") == txt2 for i in its), its)
    pg.reload(wait_until="networkidle")
    pg.wait_for_timeout(1500)
    painted = sum(pg.evaluate(HLSIZE, n) for n in range(4))
    check(tag, "after a reload both highlights are painted again", painted == 2 and len(items(pg)) == 2, [painted, len(items(pg))])

    # (3) panel
    open_panel(pg, "notes")
    tabs = pg.evaluate(BOX, "[data-sidebar-tab]")
    panel = pg.evaluate(BOX, "[data-sidebar-tabs]")[0]
    check(tag, "three tabs fit the panel", len(tabs) == 3 and all(x["r"] <= panel["r"] + 1 and x["l"] >= panel["l"] - 1 for x in tabs)
          and pg.evaluate("() => { const t = document.querySelector('[data-sidebar-tabs]'); return t.scrollWidth <= t.clientWidth + 1; }"), [tabs, panel])
    check(tag, "tab names «Содержание · Закладки · Заметки»", [x["txt"] for x in tabs] == ["Содержание", "Закладки", "Заметки"], [x["txt"] for x in tabs])
    check(tag, "header ✕ and search field stay above the tabs",
          pg.evaluate("() => { const s = document.querySelector('input[type=search]'); const t = document.querySelector('[data-sidebar-tabs]');"
                      " return !!s && s.getBoundingClientRect().height > 0 && s.getBoundingClientRect().bottom <= t.getBoundingClientRect().top + 1"
                      " && !!document.querySelector('.sidebar-close, [data-sidebar-close], .mobile-menu button[aria-label]'); }"))
    ph = pg.evaluate("() => document.querySelector('input[type=search]').placeholder")
    check(tag, "search placeholder «Поиск по заметкам»", ph == "Поиск по заметкам", ph)
    rows = pg.evaluate(BOX, "[data-note-row]")
    check(tag, "list: 2 rows", len(rows) == 2, rows)
    allc = pg.evaluate(BOX, "[data-notes-filter=all]")[0]
    notedc = pg.evaluate(BOX, "[data-notes-filter=noted]")[0]
    check(tag, "filters «Все 2» / «С заметкой 1»", re.search(r"Все\s*2", allc["txt"]) and re.search(r"С заметкой\s*1", notedc["txt"]), [allc, notedc])
    pg.locator("[data-notes-filter=noted]").click()
    pg.wait_for_timeout(300)
    check(tag, "«С заметкой» shows 1 row", len(pg.evaluate(BOX, "[data-note-row]")) == 1)
    pg.locator("[data-notes-filter=noted]").click()
    pg.locator("[data-notes-color='1']").click()
    pg.wait_for_timeout(300)
    check(tag, "colour filter shows 1 row", len(pg.evaluate(BOX, "[data-note-row]")) == 1)
    pg.locator("[data-notes-color='1']").click()
    pg.fill("input[type=search]", "Тестовая")
    pg.wait_for_timeout(400)
    check(tag, "search filters the notes by the note's text", len(pg.evaluate(BOX, "[data-note-row]")) == 1)
    pg.fill("input[type=search]", "")
    pg.wait_for_timeout(300)

    # (3b) moving a card (Vraja Lila msg 7426): the same handle as the bookmarks', the order is kept after a reload and in the file
    ids0 = pg.evaluate("() => [...document.querySelectorAll('[data-note-row]')].map(r => r.dataset.noteId)")
    check(tag, "cards have the bookmarks' handle (6 dots, >= 44 wide)",
          pg.evaluate("() => [...document.querySelectorAll('[data-note-row] [data-bookmark-handle]')].every(h => h.querySelectorAll('circle').length === 6 && h.getBoundingClientRect().width >= 44)"))
    pg.locator("[data-note-row]").nth(1).locator("[data-bookmark-handle]").focus()
    pg.keyboard.press("ArrowUp")
    pg.wait_for_timeout(400)
    ids1 = pg.evaluate("() => [...document.querySelectorAll('[data-note-row]')].map(r => r.dataset.noteId)")
    check(tag, "a card moved up", len(ids1) == 2 and ids1 == ids0[::-1], [ids0, ids1])
    pg.reload(wait_until="networkidle")
    pg.wait_for_timeout(1000)
    open_panel(pg, "notes")
    ids2 = pg.evaluate("() => [...document.querySelectorAll('[data-note-row]')].map(r => r.dataset.noteId)")
    check(tag, "the order is kept after a reload", ids2 == ids1, [ids1, ids2])
    check(tag, "the order is kept in the stored list (pos)", [i["id"] for i in sorted(items(pg), key=lambda i: i.get("pos", 99))] == ids1)

    # (4) open the place, delete + undo
    pg.evaluate("() => { const m = document.querySelector('.app-main'); if (m) m.scrollTop = 0; }")
    pg.locator("[data-note-row] [data-note-open]").first.click()
    pg.wait_for_timeout(1500)
    seen = pg.evaluate("() => { const m = document.querySelector('.app-main'); const mr = m.getBoundingClientRect(); const out = [];"
                       " for (let n = 0; n < 4; n++) { const h = CSS.highlights.get('hl-' + n); if (h) for (const r of h) { const b = r.getBoundingClientRect(); out.push(b.top >= mr.top - 2 && b.bottom <= mr.bottom + 2); } } return out; }")
    check(tag, "a tap on a row opens the place: the highlight is on the screen", any(seen), seen)
    open_panel(pg, "notes")
    pg.locator("[data-note-row] [data-note-delete]").first.click()
    pg.wait_for_timeout(400)
    check(tag, "bin: removed, toast «Отменить»", len(items(pg)) == 1 and pg.locator("[data-hl-toast] button").count() == 1)
    pg.locator("[data-hl-toast] button").click()
    pg.wait_for_timeout(400)
    check(tag, "«Отменить» brings it back", len(items(pg)) == 2)

    # (5) file: only notes, load with preview
    open_panel(pg, "notes")
    pg.locator("[data-notes-file]").click()
    with pg.expect_download(timeout=8000) as dl:
        pg.locator("[data-notes-save]").click()
    d = dl.value
    path = os.path.join(tempfile.mkdtemp(), "x.json")
    d.save_as(path)
    data = json.load(open(path, encoding="utf-8"))
    check(tag, "file name «Арчана-паддхати — заметки YYYY-MM-DD.json»", re.fullmatch(r"Арчана-паддхати — заметки \d{4}-\d{2}-\d{2}\.json", d.suggested_filename), d.suggested_filename)
    check(tag, "file holds only notes (2 items, no bookmarks)", len(data.get("items", [])) == 2 and "bookmarks" not in json.dumps(data), list(data))
    pg.wait_for_timeout(300)
    pg.evaluate("() => localStorage.setItem('ap.highlights', JSON.stringify({v: 1, items: []}))")
    pg.reload(wait_until="networkidle")
    pg.wait_for_timeout(800)
    open_panel(pg, "notes")
    pg.locator("[data-notes-file]").click()
    pg.set_input_files("input[data-notes-import]", path)
    pg.wait_for_selector("[data-hl-import]", state="visible", timeout=4000)
    pv = pg.evaluate("() => document.querySelector('[data-hl-import]').textContent")
    check(tag, "preview says 2 notes in the file", "2" in pv, pv)
    check(tag, "nothing changes before «Добавить»", len(items(pg)) == 0)
    pg.locator("[data-hl-import-add]").click()
    pg.wait_for_timeout(500)
    check(tag, "«Добавить» restores the notes", len(items(pg)) == 2, items(pg))
    pg.locator("[data-notes-file]").click()
    bad = os.path.join(tempfile.mkdtemp(), "bad.json")
    open(bad, "w", encoding="utf-8").write("{ not json")
    pg.set_input_files("input[data-notes-import]", bad)
    pg.wait_for_selector("[data-hl-import-error]", state="visible", timeout=4000)
    check(tag, "a broken file: message, nothing changed", len(items(pg)) == 2)
    check(tag, "bookmarks untouched", pg.evaluate("() => localStorage.getItem('ap.bookmarks')") == bm_before)
    b.close()


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        themes = ["day", "sepia", "night"] if dev in ("iphone14", "desktop") else ["day"]
        for th in themes:
            try:
                run_theme(p, dev, eng, opts, th)
            except Exception as e:  # noqa: BLE001
                check(f"{dev}/{th}", "scenario ran to the end", False, repr(e)[:400])

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
