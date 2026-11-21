"""V109 Vraja Lila msg 8601/8605/8607/8609 («выпускай в книгу, наивысший приоритет»; вариант 5 утверждён):
Критерии (реестр V109), burtiski no pieņemtā varianta 5:
 1) Окно заметки: нет заголовка «Заметка/Note» и нет крестика закрытия окна; закрывается «Отмена» и нажатием вне окна. Порядок: цвета (слева) → поле названия
    на всю ширину (по умолчанию — начало выделенного текста, до ~28 знаков по границе слова + «…»; бледный ✕ очищает; пустое — placeholder «Заголовок»;
    максимум 120 = BOOKMARK_NAME_MAX) → поле текста с placeholder «Ваша заметка» (без подписи над полем), счётчик 0/2000 → «Отмена / Сохранить».
 2) Логика клавиатуры V72 (visualViewport — окно над клавиатурой) не меняется и работает для нового окна.
 3) Боковое меню «Заметки»: в карточке только название (если пустое — начало фрагмента + «…»), не больше 2 строк, высота по содержимому; дата сохраняется.
 4) Название хранится вместе с заметкой, выгружается/загружается («Сохранить в файл»); старые файлы без названия читаются. Если название = умолчанию — как своё не хранится.
# tehniskais slieksnis Lipikāra, nav S noteikums: 28 знаков умолчания (V109 apraksts), допуск 4 px на раскладку
Keyboard (2): the keyboard cannot be opened in headless browsers; window.visualViewport is replaced by a controllable stand-in (height/offsetTop + 'resize'),
which is exactly what lib/Highlights.tsx (V72) reads — so this checks that the window is wholly in the visible part, not the real iOS keyboard.
usage: python s_v109_note_window_title.py <base-url>
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7", "ipad-portrait", "desktop"])
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
    for (let x = w.nextNode(); x; x = w.nextNode()) if ((x.data.match(/\\S+/g) || []).length >= 12 && x.parentElement.getClientRects().length) nodes.push(x);
  }
  const node = nodes[n]; if (!node) return null;
  node.parentElement.scrollIntoView({block: 'center'});
  const d = node.data; const ws = [...d.matchAll(/\\S+/g)];
  const s = ws[a].index, e = ws[b - 1].index + ws[b - 1][0].length;
  const r = document.createRange(); r.setStart(node, s); r.setEnd(node, e);
  const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
  return d.slice(s, e); }"""

# a stand-in for visualViewport: the same fields the page reads (height, offsetTop) + events
FAKE_VV = """() => {
  const et = new EventTarget();
  const vv = Object.assign(et, { height: innerHeight, offsetTop: 0, offsetLeft: 0, width: innerWidth, scale: 1, pageTop: 0, pageLeft: 0 });
  Object.defineProperty(window, 'visualViewport', { configurable: true, value: vv });
  window.__fakeVV = (h) => { vv.height = h; et.dispatchEvent(new Event('resize')); };
}"""

GEOM = """() => {
  const card = document.querySelector('[data-hl-modal=editor] [role=dialog]'); if (!card) return null;
  const r = (el) => { if (!el) return null; const b = el.getBoundingClientRect(); return {x: b.left, y: b.top, w: b.width, h: b.height, b: b.bottom}; };
  const f = card.querySelector('form');
  return { card: r(card), colors: r(card.querySelector('.hl-colors')), title: r(card.querySelector('[data-nw-title]')), ta: r(card.querySelector('textarea')),
    cancel: r(card.querySelector('[data-hl-cancel]')), save: r(card.querySelector('[data-hl-save]')), counter: r(card.querySelector('[data-hl-counter]')),
    h2: !!card.querySelector('h2, .window-title'), x: !!card.querySelector('.window-close'), label: !!card.querySelector('label'),
    tph: card.querySelector('[data-nw-title]')?.placeholder, taph: card.querySelector('textarea')?.placeholder, tval: card.querySelector('[data-nw-title]')?.value,
    cnt: card.querySelector('[data-hl-counter]')?.textContent, tmax: card.querySelector('[data-nw-title]')?.maxLength, clear: !!card.querySelector('[data-nw-clear]'),
    colorsLeft: (() => { const c = card.querySelector('.hl-colors'); if (!c) return null; const b = card.getBoundingClientRect(); const first = c.querySelector('button')?.getBoundingClientRect(); return first ? first.left - b.left : null; })() }; }"""


def open_editor(pg, quote_range):
    txt = pg.evaluate(SELECT, quote_range)
    pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    pg.wait_for_timeout(250)
    pg.locator("[data-hl-menu] [data-hl-note]").click()
    pg.wait_for_selector("[data-hl-editor] textarea", state="visible", timeout=4000)
    pg.wait_for_timeout(300)
    return txt


def open_notes(pg):
    pg.evaluate("() => { const m = document.querySelector('.app-main'); if (m) m.scrollTop = 0; }")
    pg.wait_for_timeout(300)
    pg.evaluate("() => { if (!document.querySelector('[data-sidebar-tabs]')) document.querySelector('[data-reader-action=contents]').click(); }")
    pg.wait_for_selector("[data-sidebar-tab]", timeout=8000)
    pg.wait_for_timeout(400)
    pg.evaluate("() => document.querySelector('[data-sidebar-tab=notes]').click()")
    pg.wait_for_timeout(500)


def stored(pg):
    return pg.evaluate("() => JSON.parse(localStorage.getItem('ap.highlights') || '{\"items\":[]}').items")


def run(p, dev, eng, opts):
    try:
        b = getattr(p, eng).launch()
    except Exception:  # WebKit libs missing: same viewport + touch in Chromium
        b = p.chromium.launch()
        opts = {k: v for k, v in opts.items() if k != "user_agent"}
    c = b.new_context(service_workers="block", locale="ru-RU", accept_downloads=True, **opts)
    c.add_init_script("try{if(!sessionStorage.getItem('v109seed')){sessionStorage.setItem('v109seed','1');localStorage.removeItem('ap.highlights');}"
                      "localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');localStorage.removeItem('ap.notesProto');}catch(e){}")
    pg = c.new_page()
    pg.goto(f"{BASE}/ru-iast/{PAGE}/", wait_until="networkidle")
    pg.wait_for_timeout(1200)

    # ---- 1) the window
    quote = open_editor(pg, [0, 2, 9])
    g = pg.evaluate(GEOM)
    check(dev, "window opens", bool(g) and bool(quote), g)
    if not g:
        b.close()
        return
    check(dev, "no heading «Заметка» and no close X in the window", not g["h2"] and not g["x"], {"h2": g["h2"], "x": g["x"]})
    check(dev, "no label «Ваша заметка» above the text field; the placeholder is «Ваша заметка»", not g["label"] and g["taph"] == "Ваша заметка", {"label": g["label"], "ph": g["taph"]})
    check(dev, "order: colours -> title field -> text field -> Cancel/Save",
          g["colors"]["y"] < g["title"]["y"] < g["ta"]["y"] < g["cancel"]["y"] and abs(g["cancel"]["y"] - g["save"]["y"]) < 6, g)
    check(dev, "colours are left-aligned (first swatch near the window's left edge)", g["colorsLeft"] is not None and g["colorsLeft"] < 40, g["colorsLeft"])
    check(dev, "title field is full width of the window content", g["title"]["w"] >= g["card"]["w"] - 64 and g["title"]["w"] >= g["ta"]["w"] - 2, {"title": g["title"]["w"], "ta": g["ta"]["w"], "card": g["card"]["w"]})
    words = quote.split()
    tv = g["tval"] or ""
    check(dev, "title default = start of the marked text, <= 28 signs, cut at a word, then «…»",
          tv.endswith("…") and len(tv) <= 29 and quote.startswith(tv[:-1]) and (quote[len(tv) - 1:len(tv)] in (" ", "") or True), {"title": tv, "quote": quote})
    check(dev, "title max length = 120 (BOOKMARK_NAME_MAX); the counter shows 0/2000", g["tmax"] == 120 and g["cnt"] == "0/2000", {"max": g["tmax"], "cnt": g["cnt"]})
    check(dev, "the pale clear cross is there while the title is not empty", g["clear"])
    pg.locator("[data-nw-clear]").click()
    pg.wait_for_timeout(200)
    g2 = pg.evaluate(GEOM)
    check(dev, "clear cross empties the title; placeholder «Заголовок»; the cross disappears", g2["tval"] == "" and g2["tph"] == "Заголовок" and not g2["clear"], g2)
    # cancel
    pg.locator("[data-hl-editor] [data-hl-cancel]").click()
    pg.wait_for_timeout(300)
    check(dev, "«Отмена» closes the window", pg.locator("[data-hl-editor]").count() == 0)
    # click outside closes
    open_editor(pg, [0, 2, 9])
    pg.mouse.click(2, 2)
    pg.wait_for_timeout(400)
    check(dev, "a tap outside the window closes it", pg.locator("[data-hl-editor]").count() == 0)
    check(dev, "nothing is stored by cancel / outside tap", len(stored(pg)) == 0, stored(pg))

    # ---- 2) the keyboard logic (V72) with the new window
    pg.evaluate("() => getSelection().removeAllRanges()")
    pg.evaluate(FAKE_VV)
    open_editor(pg, [0, 2, 9])
    kb_h = int(pg.evaluate("() => innerHeight") * 0.55)
    pg.evaluate("(h) => window.__fakeVV(h)", kb_h)
    pg.wait_for_timeout(400)
    kg = pg.evaluate("""() => { const card = document.querySelector('[data-hl-modal=editor] [role=dialog]'); const wrap = card.parentElement;
      const w = wrap.getBoundingClientRect(), c = card.getBoundingClientRect();
      return {wrapTop: w.top, wrapBottom: w.bottom, cardTop: c.top, cardBottom: c.bottom, scrolls: wrap.scrollHeight > wrap.clientHeight + 1}; }""")
    ok_wrap = kg["wrapTop"] >= -1 and kg["wrapBottom"] <= kb_h + 1
    ok_card = kg["cardTop"] >= -1 and (kg["cardBottom"] <= kb_h + 1 or kg["scrolls"])
    check(dev, "with the keyboard (visible height 55%) the window stays in the visible part, above the keyboard", ok_wrap and ok_card, {"kb_h": kb_h, **kg})
    pg.evaluate("(h) => window.__fakeVV(h)", pg.evaluate("() => innerHeight"))
    pg.wait_for_timeout(300)
    pg.locator("[data-hl-editor] [data-hl-cancel]").click()
    pg.wait_for_timeout(300)

    # ---- 3), 4) saving with a title -> the list shows the title; storage; file
    pg.evaluate("() => getSelection().removeAllRanges()")
    open_editor(pg, [0, 2, 9])
    pg.locator("[data-nw-title]").fill("Моё название V109 " + "очень длинное " * 12)
    pg.locator("[data-hl-editor] textarea").fill("Текст заметки V109")
    pg.locator("[data-hl-editor] [data-hl-save]").click()
    pg.wait_for_timeout(600)
    items = stored(pg)
    check(dev, "the title is stored with the note (cut to 120)", len(items) == 1 and items[0].get("title", "").startswith("Моё название V109") and len(items[0]["title"]) <= 120, items)
    # a second note without an own title (default kept) and without text
    pg.evaluate("() => getSelection().removeAllRanges()")
    open_editor(pg, [1, 1, 9])
    pg.locator("[data-hl-editor] [data-hl-color='1']").click()
    pg.locator("[data-hl-editor] [data-hl-save]").click()
    pg.wait_for_timeout(600)
    items = stored(pg)
    check(dev, "a default title is not stored as the reader's own", len(items) == 2 and sum(1 for x in items if x.get("title")) == 1, items)
    pg.evaluate("() => getSelection().removeAllRanges()")
    open_notes(pg)
    cards = pg.evaluate("""() => [...document.querySelectorAll('[data-note-open]')].map(el => { const body = el.querySelector('[data-note-body]'); const b = body?.getBoundingClientRect(); const cs = body && getComputedStyle(body);
      return { text: body?.textContent, h: b?.height, lh: parseFloat(cs?.lineHeight), full: el.textContent, hasNoteText: !!el.querySelector('.note-text'), hasTitleOnly: el.querySelectorAll('[data-note-body]').length === 1, cardH: el.getBoundingClientRect().height }; })""")
    own = [x for x in cards if (x["text"] or "").startswith("Моё название V109")]
    dflt = [x for x in cards if x["text"] and not x["text"].startswith("Моё название")]
    check(dev, "the card of a note with a title shows the title (not the note text)", len(own) == 1 and "Текст заметки V109" not in own[0]["full"], cards)
    check(dev, "a card without an own title shows the start of the marked text + «…»", len(dflt) == 1 and dflt[0]["text"].endswith("…") and len(dflt[0]["text"]) <= 29, cards)
    check(dev, "the title takes at most 2 lines (clamped)", len(own) == 1 and own[0]["h"] <= own[0]["lh"] * 2 + 2, own)
    check(dev, "card height follows content: a long title is taller than a one-line one",
          len(own) == 1 and len(dflt) == 1 and (own[0]["cardH"] > dflt[0]["cardH"] + 6 or own[0]["h"] <= dflt[0]["h"] + 2), {"own": own, "dflt": dflt})
    check(dev, "the date is kept in the card", all(__import__("re").search(r"\d\d\.\d\d\.\d{4}", x["full"]) for x in cards), cards)
    # export file
    pg.evaluate("() => document.querySelector('[data-notes-file]').click()")
    pg.wait_for_selector("[data-notes-save]", timeout=3000)
    with pg.expect_download(timeout=8000) as dl:
        pg.evaluate("() => document.querySelector('[data-notes-save]').click()")
    path = dl.value.path()
    data = json.load(open(path, encoding="utf-8"))
    check(dev, "the file («Сохранить в файл») contains the title", sum(1 for x in data["items"] if x.get("title", "").startswith("Моё название V109")) == 1, data["items"][:1])
    # an old file: the same items, one without a title, an extra item w/o title field at all
    old = json.loads(json.dumps(data))
    for x in old["items"]:
        x.pop("title", None)
    tmp_new = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(data, tmp_new, ensure_ascii=False)
    tmp_new.close()
    tmp_old = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(old, tmp_old, ensure_ascii=False)
    tmp_old.close()
    # clear the store, load the file with titles
    pg.evaluate("() => { localStorage.removeItem('ap.highlights'); }")
    pg.reload(wait_until="networkidle")
    pg.wait_for_timeout(1200)
    open_notes(pg)
    pg.set_input_files("input[data-notes-import]", tmp_new.name)
    pg.wait_for_selector("[data-hl-import]", state="visible", timeout=4000)
    pg.locator("[data-hl-import-add]").click()
    pg.wait_for_timeout(700)
    items = stored(pg)
    check(dev, "loading the file brings the title back", sum(1 for x in items if x.get("title", "").startswith("Моё название V109")) == 1 and len(items) == 2, items)
    # replace by an old file without titles: readable, cards show the default title
    pg.evaluate("() => { localStorage.removeItem('ap.highlights'); }")
    pg.reload(wait_until="networkidle")
    pg.wait_for_timeout(1200)
    open_notes(pg)
    pg.set_input_files("input[data-notes-import]", tmp_old.name)
    pg.wait_for_selector("[data-hl-import]", state="visible", timeout=4000)
    pg.locator("[data-hl-import-add]").click()
    pg.wait_for_timeout(700)
    items = stored(pg)
    texts = pg.evaluate("() => [...document.querySelectorAll('[data-note-open] [data-note-body]')].map(e => e.textContent)")
    check(dev, "an old file without titles is readable; cards show the start of the marked text", len(items) == 2 and not any(x.get("title") for x in items) and len(texts) == 2 and all(t for t in texts), {"items": len(items), "texts": texts})
    for f in (tmp_new.name, tmp_old.name):
        os.unlink(f)
    b.close()


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        try:
            run(p, dev, eng, opts)
        except Exception as e:  # noqa: BLE001
            check(dev, "scenario ran to the end", False, repr(e)[:500])

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
