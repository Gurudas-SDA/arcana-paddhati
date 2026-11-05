"""V73 — Vraja Lila msg 2415 + 7546 (Vraja Lila is responsible for the interface: her words are the decision)
# msg 2415: the bookmarks can be saved to a file and loaded from it, like the notes. msg 7546 (дословно): «1) заменять все 2) да 3) да 4) так, то же место, как и в заметках»
#   1) «Загрузить закладки» REPLACES all the bookmarks with the file's (does not add);
#   2) a bookmark of the file that finds no place in the book is skipped and «не найдено: N» is shown;
#   3) the file keeps each bookmark's name / quote; on loading, if the link (id) is not found, the place is looked for by the name; only then «не найдено»;
#   4) the button and the menu are as on the screenshot, in the same place as in the notes (tab «Закладки»: file icon → «Скачать закладки» / «Загрузить закладки»).
Criteria (register V73):
 (a) the export gives a file «Арчана-паддхати — закладки YYYY-MM-DD.json» of its own kind with the bookmarks (+ name, chapter title);
 (b) loading replaces all (an old bookmark that is not in the file is gone);
 (c) an unknown place is skipped, the message says «не найдено: 1»;
 (d) an unknown id with the right title is found by the title;
 (e) the file icon sits where it sits in «Заметки» (right edge, same distance under the tabs); the menu has the two items;
 (f) a broken file changes nothing; the notes file does not take a bookmarks file.
# tehniskais slieksnis Lipikāra, nav S noteikums: 8 px tolerance for the icon's right edge (the notes row's two chips push it ~5 px out), 2 px for size.
usage: python s151_bookmarks_file.py <base-url>
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
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
results = []
A, B = "introduction", "daily-duties-brahma-muhurta"


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


def open_panel(pg, tab):
    pg.evaluate("() => { if (!document.querySelector('[data-sidebar-tabs]')) document.querySelector('[data-reader-action=contents]').click(); }")
    pg.wait_for_selector("[data-sidebar-tab]", timeout=8000)
    pg.wait_for_timeout(500)
    pg.evaluate("(k) => document.querySelector(`[data-sidebar-tab=${k}]`).click()", tab)
    pg.wait_for_timeout(400)


def ids(pg):
    return pg.evaluate("() => (JSON.parse(localStorage.getItem('ap.bookmarks') || '{\"items\":[]}').items || []).map(b => b.id).sort()")


def toast(pg, want="Закладки загружены"):
    pg.wait_for_function("(w) => { const e = document.querySelector('[data-hl-toast]'); return !!e && e.textContent.includes(w); }", arg=want, timeout=5000)
    return pg.evaluate("() => document.querySelector('[data-hl-toast]').textContent")


def load(pg, path):
    if not pg.locator("[data-bookmarks-load]").is_visible():
        pg.locator("[data-bookmarks-file]").click()
    pg.wait_for_selector("[data-bookmarks-load]", timeout=3000)
    pg.set_input_files("input[data-bookmarks-import]", path)
    pg.wait_for_timeout(700)


def tmpjson(obj, raw=None):
    path = os.path.join(tempfile.mkdtemp(), "b.json")
    open(path, "w", encoding="utf-8").write(raw if raw is not None else json.dumps(obj, ensure_ascii=False))
    return path


def run(p, dev, eng, opts):
    b = getattr(p, eng).launch()
    c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce", accept_downloads=True, **opts)
    c.add_init_script("try{if(!sessionStorage.getItem('v73seed')){sessionStorage.setItem('v73seed','1');localStorage.removeItem('ap.highlights');"
                      f"localStorage.setItem('ap.bookmarks',JSON.stringify({{v:1,items:[{{id:'bk1',section:'{A}',anchor:null,block:0,lang:'ru-iast',time:5,name:'Моё имя V73'}},"
                      f"{{id:'bk2',section:'{B}',anchor:null,block:0,lang:'ru-iast',time:6,quote:'цитата места'}}]}}));}}"
                      "localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');}catch(e){}")
    pg = c.new_page()
    pg.goto(f"{BASE}/ru-iast/{B}/", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    pg.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important}")

    # (e) position as in the notes
    open_panel(pg, "notes")
    n = pg.evaluate("() => { const e = document.querySelector('[data-notes-file]'); if (!e) return null; const r = e.getBoundingClientRect(), t = document.querySelector('[data-sidebar-tabs]').getBoundingClientRect(); return {right: r.right, w: r.width, h: r.height, top: r.top - t.bottom}; }")
    open_panel(pg, "bookmarks")
    k = pg.evaluate("() => { const e = document.querySelector('[data-bookmarks-file]'); if (!e) return null; const r = e.getBoundingClientRect(), t = document.querySelector('[data-sidebar-tabs]').getBoundingClientRect(); return {right: r.right, w: r.width, h: r.height, top: r.top - t.bottom}; }")
    check(dev, "tab «Закладки» has the file icon, same size and right edge as in «Заметки»", bool(n and k) and abs(n["right"] - k["right"]) <= 8 and abs(n["w"] - k["w"]) <= 2 and abs(n["h"] - k["h"]) <= 2, [n, k])
    check(dev, "the icon is in the first row under the tabs, like the notes' one", bool(n and k) and abs(n["top"] - k["top"]) <= 6, [n, k])
    pg.locator("[data-bookmarks-file]").click()
    pg.wait_for_timeout(200)
    items = pg.evaluate("() => [...document.querySelectorAll('[data-bookmarks-file-menu] [role=menuitem]')].map(e => e.textContent.trim())")
    check(dev, "menu: «Скачать закладки» / «Загрузить из файла» (V78, Vraja msg 7621–7623)", items == ["Скачать закладки", "Загрузить из файла"], items)

    # (a) export
    with pg.expect_download(timeout=8000) as dl:
        pg.locator("[data-bookmarks-save]").click()
    d = dl.value
    path = os.path.join(tempfile.mkdtemp(), "x.json")
    d.save_as(path)
    data = json.load(open(path, encoding="utf-8"))
    check(dev, "file name «Арчана-паддхати — закладки YYYY-MM-DD.json»", re.fullmatch(r"Арчана-паддхати — закладки \d{4}-\d{2}-\d{2}\.json", d.suggested_filename), d.suggested_filename)
    its = {x["id"]: x for x in data.get("items", [])}
    check(dev, "file is of kind «bookmarks» with both bookmarks, their names / quote / chapter title",
          data.get("kind") == "bookmarks" and set(its) == {"bk1", "bk2"} and its["bk1"].get("name") == "Моё имя V73" and its["bk2"].get("quote") == "цитата места"
          and bool(its["bk1"].get("title")) and bool(its["bk2"].get("title")), data)

    # (b) load replaces all
    pg.evaluate("""() => { const o = JSON.parse(localStorage.getItem('ap.bookmarks')); o.items = [{id: 'old', section: 'introduction', anchor: null, block: 0, lang: 'ru-iast', time: 1}]; localStorage.setItem('ap.bookmarks', JSON.stringify(o)); }""")
    pg.reload(wait_until="networkidle")
    pg.wait_for_timeout(900)
    open_panel(pg, "bookmarks")
    load(pg, path)
    check(dev, "load REPLACES all: the old one is gone, the file's two are there", ids(pg) == ["bk1", "bk2"], ids(pg))
    check(dev, "the list shows two rows", pg.locator("[data-bookmark-row]").count() == 2)

    # (c) unknown place skipped; (d) found by the title when the id changed
    crafted = {"app": "arcana-paddhati", "kind": "bookmarks", "v": 1, "items": [
        {"id": "k1", "section": A, "anchor": None, "block": 0, "lang": "ru-iast", "time": 3, "title": its["bk1"]["title"]},
        {"id": "k2", "section": "old-renamed-id", "anchor": None, "block": 0, "lang": "ru-iast", "time": 2, "title": its["bk2"]["title"], "name": "Найдено по названию"},
        {"id": "k3", "section": "gone-section", "anchor": None, "block": 0, "lang": "ru-iast", "time": 1, "title": "Такой главы нет нигде"}]}
    load(pg, tmpjson(crafted))
    msg = toast(pg, "не найдено")
    store = pg.evaluate("() => JSON.parse(localStorage.getItem('ap.bookmarks')).items.map(b => [b.id, b.section, b.name || null])")
    check(dev, "unknown place skipped: 2 loaded, message «не найдено: 1»", ids(pg) == ["k1", "k2"] and "не найдено: 1" in msg, [store, msg])
    check(dev, "the changed id is found by the title (-> the chapter «%s»), name kept" % B, ["k2", B, "Найдено по названию"] in store, store)

    # (f) broken file: nothing changes; notes do not take a bookmarks file
    before = ids(pg)
    load(pg, tmpjson(None, raw="{ not json"))
    check(dev, "a broken file: message «не файл закладок», nothing changed", ids(pg) == before and "не файл закладок" in toast(pg, "не файл закладок"), ids(pg))
    open_panel(pg, "notes")
    pg.locator("[data-notes-file]").click()
    pg.set_input_files("input[data-notes-import]", path)
    pg.wait_for_selector("[data-hl-import-error]", state="visible", timeout=4000)
    check(dev, "the notes file refuses a bookmarks file", True)
    b.close()


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        try:
            run(p, dev, eng, opts)
        except Exception as e:  # noqa: BLE001
            check(dev, "scenario ran to the end", False, repr(e)[:500])

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
