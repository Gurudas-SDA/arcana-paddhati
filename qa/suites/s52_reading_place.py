"""Reading place, «Продолжить», «Закладки» (Vraja Lila msg 5316 pp. 5–7; plan «Закладки» B1–B3, 20.10.2026).

Rule text (msg 5316, verbatim):
 5. «Место чтения — молча, без видимых изменений. Сохранённый язык прогонять через liveLang (ru снят → ru-iast,
    replacedBy в lib/languages.json).»
 6. «Карточка «Продолжить» на обложке, как в макете; рисовать встроенным скриптом до первой отрисовки (как
    READER_PREFS_SCRIPT), чтобы обложка не дёргалась.»
 7. «Вкладка «Закладки» в меню. Вторую строку НЕ хранить текстом — хранить якорь, строку брать из данных текущего
    языка при показе.»  НЕ делать: кнопку постановки закладки — снято: Vraja Lila msg 5380 выбрал
    вариант А (кнопка в верхней строке, qa s54); проверка «no [data-bookmark-add]» ниже остаётся (в списке нет кнопки).
usage: python s52_reading_place.py <base-url>
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from toc import Contents  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
CH = "arcana-procedure"
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


def ctx(b, opts, init=""):
    c = b.new_context(service_workers="block", locale="ru-RU", **opts)
    c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');" + init)
    return c


def place(pg):
    return pg.evaluate("JSON.parse(localStorage.getItem('ap.readingPlace') || 'null')")


COVER = """() => { const i = document.querySelector('img.home-cover'); const a = document.querySelector('a.home-resume');
  return {h: i ? Math.round(i.getBoundingClientRect().height) : null, card: !!a && a.offsetHeight > 0,
          text: a ? a.innerText : '', href: a ? a.getAttribute('href') : null,
          reserved: document.documentElement.hasAttribute('data-home-resume')}; }"""

with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        touch = opts.get("has_touch", False)

        # first visit: no card, cover clean
        c = ctx(b, opts)
        pg = c.new_page()
        pg.goto(f"{BASE}/ru-iast/", wait_until="networkidle")
        pg.wait_for_timeout(600)
        s0 = pg.evaluate(COVER)
        check(dev, "6 first visit: no «Продолжить» card", not s0["card"] and not s0["reserved"], s0)

        # 5: reading writes the place silently
        pg.goto(f"{BASE}/ru-iast/{CH}/#11-gandha", wait_until="networkidle")
        pg.wait_for_timeout(2500)
        pl = place(pg)
        check(dev, "5 place stored: chapter + subsection anchor + block, language ru-iast",
              pl and pl.get("section") == CH and pl.get("anchor") and pl.get("lang") == "ru-iast" and isinstance(pl.get("block"), int), pl)
        pg.reload(wait_until="networkidle")
        pg.wait_for_timeout(500)
        check(dev, "5 place survives a reload", (place(pg) or {}).get("section") == CH, place(pg))

        # 6: the cover shows «Продолжить» before first paint, no jump
        pg.goto(f"{BASE}/ru-iast/", wait_until="commit")
        pg.wait_for_selector("img.home-cover", state="attached")
        first = pg.evaluate(COVER)
        pg.wait_for_load_state("networkidle")
        pg.wait_for_timeout(800)
        s1 = pg.evaluate(COVER)
        sub_title = "Гандха"
        check(dev, "6 card on the cover with the subsection in this language", s1["card"] and sub_title in s1["text"], s1)
        check(dev, "6 drawn before first paint, cover does not jump", first["reserved"] and first["card"] and first["h"] == s1["h"],
              {"first": first, "after": s1["h"]})
        check(dev, "5 «Обложка» does not erase the place", (place(pg) or {}).get("section") == CH, place(pg))
        a = pg.locator("a.home-resume")
        (a.tap if touch else a.click)()
        pg.wait_for_timeout(1500)
        check(dev, "6 tap opens the chapter at the place", f"/{CH}/" in pg.url, pg.url)

        # language: the line comes from the current language's contents (anchor stored, not text)
        pg.goto(f"{BASE}/", wait_until="networkidle")
        pg.wait_for_timeout(600)
        s2 = pg.evaluate(COVER)
        en_line = json.load(open(os.path.join(qa.REPO, "data", "book.json"), encoding="utf-8"))
        en_sub = next(u["title"] for s in en_line["sections"] if s["id"] == CH for u in s.get("subsections", []) if u["id"] == pl["anchor"]) if pl else "?"
        check(dev, "6 another language: same place, line in that language", s2["card"] and en_sub in s2["text"] and f"/{CH}/" in (s2["href"] or ""), s2)
        c.close()

        # retired language stored (ru) -> liveLang ru-iast
        c = ctx(b, opts, "localStorage.setItem('ap.readingPlace', JSON.stringify({v:1,section:'%s',anchor:'2-svagata',block:3,offset:0,lang:'ru',time:%d}));" % (CH, int(time.time() * 1000)))
        pg = c.new_page()
        pg.goto(f"{BASE}/ru-iast/", wait_until="networkidle")
        pg.wait_for_timeout(500)
        s3 = pg.evaluate(COVER)
        check(dev, "5 stored language «ru» read as ru-iast (liveLang): exact place kept", s3["card"] and pg.locator("a.home-resume[data-same-lang]").count() == 1, s3)

        # 7: «Закладки» tab — list from storage, second line from the current language
        bm = [{"id": "b1", "section": CH, "anchor": "2-svagata", "block": 0, "lang": "ru-iast", "time": int(time.time() * 1000)}]
        pg.evaluate("v => localStorage.setItem('ap.bookmarks', JSON.stringify({v: 1, items: v}))", bm)
        pg.goto(f"{BASE}/ru-iast/{CH}/", wait_until="networkidle")
        pg.wait_for_timeout(800)
        flow = Contents(pg, qa.TocMode("default"), touch)
        flow.contents()
        tab = pg.locator("[data-sidebar-tab=bookmarks]")
        check(dev, "7 tab «Закладки» in the menu", tab.count() == 1, "")
        if tab.count():
            (tab.tap if touch else tab.click)()
            pg.wait_for_timeout(400)
            rows = pg.locator("[data-bookmark-row]")
            txt = rows.first.inner_text() if rows.count() else ""
            check(dev, "7 bookmark row: chapter + second line from the contents (Свагата)", rows.count() == 1 and "Свагата" in txt, txt)
            check(dev, "7 no «set a bookmark» button", pg.locator("[data-bookmark-add]").count() == 0, "")
            stored = pg.evaluate("localStorage.getItem('ap.bookmarks')")
            check(dev, "7 second line not stored as text (anchor only)", "Свагата" not in stored, stored)
        c.close()

        # no storage: no errors, cover clean
        c = ctx(b, opts, "Object.defineProperty(window,'localStorage',{get(){throw new Error('blocked')}});")
        pg = c.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"{BASE}/ru-iast/{CH}/", wait_until="networkidle")
        pg.wait_for_timeout(1800)
        pg.goto(f"{BASE}/ru-iast/", wait_until="networkidle")
        check(dev, "5 no storage: no page errors", not errs, errs[:3])
        c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
