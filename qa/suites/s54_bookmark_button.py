"""Bookmark button, variant A (Vraja Lila msg 5380, 20.10.2026; plan «Закладки» B4, «Цена вариантов раздела 5» A).

Rule text (plan 2026.10.19 «План на ночь — закладки и исправления», B4 + variant A, verbatim):
 A. «4-я кнопка в верхней строке ReaderChrome.tsx (~60 строк + тост). Риск: в 12 языках подписи
    «Содержание»/«Поиск» длинные — на 320–390 px проверить переносы (s13). Правила: 10.1, 10.2.»
 B4. «кнопка/метка/строка + «Закладка поставлена · Отменить» | постановка/снятие закладки |
    s48 +8: повторное касание снимает (10.1), шаг истории не создаётся (10.2: history.length и «Назад»
    не трогают закладку), офлайн»
 (the plan's «s48» became s52 for the list and this suite for the button)
Picture: Vraja_Lila/faili/2026.10.20_Закладка — вариант А.png — ribbon icon between «Поиск» and «Аа»,
filled after the tap; dark toast «Закладка поставлена · Отменить» («Отменить» in gold).
usage: python s54_bookmark_button.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from toc import Contents  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
CH = "arcana-procedure"
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
LANGS = ["ru-iast", "ru", "", "lv", "de", "fr", "es", "it", "uk", "hu", "pt", "lt"]
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


def items(pg):
    return pg.evaluate("(JSON.parse(localStorage.getItem('ap.bookmarks') || 'null') || {items: []}).items")


BTN = "[data-reader-action=bookmark]"
TOAST = "[data-bookmark-toast]"

BAR = """() => { const bar = document.querySelector('.reader-bar-top .reader-bar-inner');
  const W = document.documentElement.clientWidth;
  const btns = [...bar.querySelectorAll('button')].map(b => { const r = b.getBoundingClientRect();
    return {a: b.dataset.readerAction, top: Math.round(r.top), h: Math.round(r.height), l: Math.round(r.left), r: Math.round(r.right),
            cut: [...b.querySelectorAll('span')].some(s => s.scrollWidth > s.clientWidth + 1)}; });
  return {W, btns}; }"""


def tap(pg, loc, touch):
    (loc.tap if touch else loc.click)()
    pg.wait_for_timeout(350)


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        touch = opts.get("has_touch", False)
        c = b.new_context(service_workers="block", locale="ru-RU", **opts)
        c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');")
        pg = c.new_page()
        pg.goto(f"{BASE}/ru-iast/", wait_until="networkidle")
        pg.wait_for_timeout(500)
        check(dev, "A no bookmark button on the cover", pg.locator(BTN).count() == 0, pg.locator(BTN).count())

        # cover -> chapter (one real step), so «Назад» has a step to go to
        pg.goto(f"{BASE}/ru-iast/{CH}/#11-gandha", wait_until="networkidle")
        pg.wait_for_timeout(1500)
        flow = Contents(pg, qa.TocMode("default"), touch)
        flow.bars()
        btn = pg.locator(BTN)
        check(dev, "A 4th button in the top bar", btn.count() == 1 and pg.locator(f".reader-bar-top {BTN}").count() == 1, btn.count())
        if not btn.count():
            c.close(); b.close()
            continue
        bar = pg.evaluate(BAR)
        order = [x["a"] for x in bar["btns"]]
        check(dev, "A order: Содержание · Поиск · закладка · Аа", order == ["contents", "search", "bookmark", "aa"], order)
        check(dev, "A not pressed before", btn.get_attribute("aria-pressed") == "false", btn.get_attribute("aria-pressed"))

        h0 = pg.evaluate("history.length")
        url0 = pg.url
        tap(pg, btn, touch)
        it = items(pg)
        toast = pg.locator(TOAST)
        ttxt = toast.inner_text() if toast.count() else ""
        check(dev, "B4 tap sets a bookmark here (chapter + subsection)", len(it) == 1 and it[0]["section"] == CH and it[0]["anchor"], it)
        check(dev, "B4 toast «Закладка поставлена · Отменить»", "Закладка поставлена" in ttxt and pg.locator(f"{TOAST} button").count() == 1
              and "Отменить" in pg.locator(f"{TOAST} button").inner_text(), ttxt)
        check(dev, "A icon filled (pressed) after the tap", btn.get_attribute("aria-pressed") == "true", btn.get_attribute("aria-pressed"))
        check(dev, "10.2 no history step: history.length and URL unchanged", pg.evaluate("history.length") == h0 and pg.url == url0,
              {"h0": h0, "h1": pg.evaluate("history.length"), "url": pg.url})

        # «Отменить» takes it back
        tap(pg, pg.locator(f"{TOAST} button"), touch)
        check(dev, "B4 «Отменить» removes the bookmark just set", items(pg) == [] and btn.get_attribute("aria-pressed") == "false", items(pg))

        # 10.1: a second tap removes
        flow.bars()
        tap(pg, btn, touch)
        n1 = len(items(pg))
        flow.bars()
        tap(pg, btn, touch)
        check(dev, "10.1 repeated tap removes the bookmark", n1 == 1 and items(pg) == [] and btn.get_attribute("aria-pressed") == "false",
              {"after1": n1, "after2": items(pg)})
        check(dev, "10.2 set + remove: still no history step", pg.evaluate("history.length") == h0, pg.evaluate("history.length"))

        # 10.2: «Назад» does not touch the bookmark
        flow.bars()
        tap(pg, btn, touch)
        flow.nav("back")
        check(dev, "10.2 «Назад» leaves the chapter, bookmark stays", f"/{CH}/" not in pg.url and len(items(pg)) == 1,
              {"url": pg.url, "items": items(pg)})

        # the «Закладки» tab shows it
        pg.goto(f"{BASE}/ru-iast/{CH}/", wait_until="networkidle")
        pg.wait_for_timeout(800)
        flow.contents()
        tab = pg.locator("[data-sidebar-tab=bookmarks]")
        if tab.count():
            tap(pg, tab, touch)
        rows = pg.locator("[data-bookmark-row]")
        check(dev, "B4 the «Закладки» tab lists it (Гандха)", rows.count() == 1 and "Гандха" in rows.first.inner_text(),
              rows.first.inner_text() if rows.count() else "")
        c.close()

        # offline: setting works without the network
        c = b.new_context(service_workers="block", locale="ru-RU", **opts)
        c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');")
        pg = c.new_page()
        pg.goto(f"{BASE}/ru-iast/{CH}/#2-svagata", wait_until="networkidle")
        pg.wait_for_timeout(1200)
        c.set_offline(True)
        flow = Contents(pg, qa.TocMode("default"), touch)
        flow.bars()
        if pg.locator(BTN).count():
            tap(pg, pg.locator(BTN), touch)
        check(dev, "B4 offline: the bookmark is set, toast shown", len(items(pg)) == 1 and pg.locator(TOAST).count() == 1, items(pg))
        c.set_offline(False)
        c.close()

        # A risk: 12 languages on 320–390 px — the top bar stays one row, nothing cut off
        if touch:
            for w in (320, 360, 390):
                o = dict(opts, viewport={"width": w, "height": 740})
                c = b.new_context(service_workers="block", **o)
                c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');")
                pg = c.new_page()
                bad = []
                for lang in LANGS:
                    pg.goto(f"{BASE}/{lang + '/' if lang else ''}{CH}/", wait_until="domcontentloaded")
                    pg.wait_for_selector(".reader-bar-top button", state="attached")
                    s = pg.evaluate(BAR)
                    bt = s["btns"]
                    one_row = len({x["top"] for x in bt}) == 1 and all(x["h"] <= 48 for x in bt)
                    inside = all(x["l"] >= 0 and x["r"] <= s["W"] for x in bt)
                    no_overlap = all(bt[i]["r"] <= bt[i + 1]["l"] for i in range(len(bt) - 1))
                    if not (len(bt) == 4 and one_row and inside and no_overlap and not any(x["cut"] for x in bt)):
                        bad.append({"lang": lang or "en", "btns": bt})
                check(dev, f"A {w} px: top bar one row, 4 buttons inside the screen, no cut labels (12 languages)", not bad, bad[:2])
                c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
