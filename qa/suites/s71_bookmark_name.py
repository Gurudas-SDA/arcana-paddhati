"""«Закладки»: the bookmark's name and its exact place (V34, Satkirti msg 5866, Vraja Lila msg 5869 / 5872, 21.10.2026).

Rule text (Vraja Lila msg 5869, verbatim):
 «при добавлении закладки по центру экрана появляется модальное окно, на котором по умолчанию как название стоит
  default название главы, но в том же окне её можно переименовать и нажать подтвердить... с этим названием оно
  отобразится в закладках»
 «в боковом меню, в закладках, с правой части от закладки есть кнопка убирания её из этого раздела, а слева от этой
  кнопки поставь иконку карандашика (та же толщина иконки), где можно будет переименовать закладку (так же в том же
  модальном окне)»
 «название закладок не должно рябить в глазах, поэтому нужно ограничить видимую часть… после скольки-то символов
  идёт „...“»
 «не показывается вовсе, если сделано переименование... никаких мелких шрифтов»
Rule text (Vraja Lila msg 5881, verbatim):
 «если я в разделе закладок с открытым боковым меню, модальное окно при „изменить“ открывается НЕ закрывая панель,
  я переименовал, подтвердил и вижу закладку с новым названием»; «ДА, в разделе может быть несколько закладок»
Rule text (Vraja Lila msg 5882, verbatim):
 «повторное нажатие на ленточку при учёте, что я примерно на том же месте, снимет закладку»
 (Purohita's reading, msg to Mantrī: a bookmark's block on screen between the bars, or ±1 block from the top one)
Rule text (Vraja Lila msg 5883, verbatim):
 «скорее можем померить определённой порцией скролла... если закладка стоит на определённом стихе или разделе, то при
  открытии он будет на самом верху практически... (как „продолжить“ открывало главу и она была видна)»
 # tehniskais slieksnis Lipikāra, nav S noteikums: «примерно на том же месте» = the bookmark's block ≤ ½ of the reading
 # area's height from the reading line (lib/bookmarks.ts NEAR_SCREEN_PART); opened block 0–24 px below the top bar.
Rule text (Vraja Lila msg 5872, verbatim):
 «хочу иметь возможность делать закладку на конкретном месте в главе... если я листаю и там мантра, которую я учу...
  поставить закладку там и назвать „Мантра при пробуждении“... и тогда легко вернуться конкретно к этому месту»

Checks: the window in the middle, black 60 % dimming without blur (V18), ✕, default name = the subsection's name,
Enter confirms, «Отмена» sets nothing; the stored name; the row shows only the name (one line, «…», no small date);
the pencil left of the remove icon (44 px); the pencil opens the same window with the name; old
bookmarks (no name) show as before; the exact block — opened from another chapter it stands just below the top and
is lit, in «Страницы» and «Лента».
V34 fix (Vraja Lila msg 5897, passed on by Lipikāra): the pencil's line thinner, like the other thin icons (~1.5 px),
and the pencil a little closer to the bookmark (remove) icon.
# tehniskais slieksnis Lipikāra, nav S noteikums: pencil stroke-width 1.5; «closer» = gap between the two drawn icons
# 8–18 px (before: 26 px); both 44 px tap targets stay and do not overlap.
# tehniskais slieksnis Lipikāra, nav S noteikums: the opened block 40–140 px below the reading area's top; «…» =
# text-overflow ellipsis with scrollWidth > clientWidth.
usage: python s71_bookmark_name.py <base-url> [--shots <dir>]
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from toc import Contents  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
SHOTS = sys.argv[sys.argv.index("--shots") + 1] if "--shots" in sys.argv else None
CH = "daily-duties-brahma-muhurta"
OTHER = "arcana-procedure"
NAME = "Мантра при пробуждении"
LONG = "Очень длинное название закладки, которое никак не помещается в одну строку бокового меню"
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
T0 = 1792000000000
SEED = [{"id": "b-svagata", "section": OTHER, "anchor": "2-svagata", "block": 0, "lang": "ru-iast", "time": T0 + 3},
        {"id": "b-long", "section": OTHER, "anchor": "11-gandha", "block": 0, "lang": "ru-iast", "time": T0 + 2, "name": LONG},
        {"id": "b-acamana", "section": OTHER, "anchor": "5-acamana", "block": 0, "lang": "ru-iast", "time": T0 + 1}]
MENU = ".mobile-menu[data-open]"
DLG = "[data-bookmark-dialog]"
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


def stored(pg):
    return pg.evaluate("(JSON.parse(localStorage.getItem('ap.bookmarks') || 'null') || {items: []}).items")


def shot(pg, dev, n, what):
    if SHOTS and dev in ("iphone14", "desktop"):
        path = os.path.join(SHOTS, f"2026.10.21_V34 Закладки — {n} {what} ({'iPhone 14' if dev == 'iphone14' else 'компьютер'}).png")
        pg.screenshot(path=path)
        print(f"  shot {path}", flush=True)


def tap(pg, loc, touch, wait=400):
    (loc.tap if touch else loc.click)()
    pg.wait_for_timeout(wait)


# The 3rd verse of 1.1 «Утренние молитвы» (udgāyatīnām…): its index among the place blocks, put at the top.
TO_VERSE = """([sub, n]) => { const m = document.querySelector('.app-main');
  const sec = document.querySelector('[data-continuous-book]') ? document.querySelector('[data-book-section="%s"]') : m;
  const verses = [...sec.querySelectorAll('#' + sub + ' .verse-text p')];
  const v = verses[n]; const blocks = [...sec.querySelectorAll('article :is(h1,h2,h3,h4,p)')];
  m.scrollTop += v.getBoundingClientRect().top - m.getBoundingClientRect().top - 90;
  return {index: blocks.indexOf(v), text: v.textContent.slice(0, 20), count: verses.length}; }""" % CH
SEEN = """(i) => { const m = document.querySelector('.app-main');
  const sec = document.querySelector('[data-continuous-book]') ? document.querySelector('[data-book-section="%s"]') : m;
  const b = sec.querySelectorAll('article :is(h1,h2,h3,h4,p)')[i]; const r = b.getBoundingClientRect(); const s = m.getBoundingClientRect();
  return r.bottom > s.top && r.top < s.bottom; }""" % CH
LONG_SUB = "sadhararana-acamana"
# Two blocks of 1.5 far apart: its first visible paragraph and one ≥ 2 screens below it; each put at the top.
FAR_PAIR = """(sub) => { const m = document.querySelector('.app-main');
  const sec = document.querySelector('[data-continuous-book]') ? document.querySelector('[data-book-section="%s"]') : m;
  const blocks = [...sec.querySelectorAll('article :is(h1,h2,h3,h4,p)')]; const box = sec.querySelector('#' + sub);
  const mine = blocks.map((b, i) => [b, i]).filter(([b]) => box.contains(b) && b.tagName === 'P' && b.getClientRects().length);
  const a = mine[0]; const y0 = a[0].getBoundingClientRect().top;
  const b = mine.find(([el]) => el.getBoundingClientRect().top - y0 > 2 * m.clientHeight);
  return [a[1], b ? b[1] : null]; }""" % CH
TO_BLOCK = """(i) => { const m = document.querySelector('.app-main'); const bar = document.querySelector('.reader-bar-top').offsetHeight;
  const sec = document.querySelector('[data-continuous-book]') ? document.querySelector('[data-book-section="%s"]') : m;
  const b = sec.querySelectorAll('article :is(h1,h2,h3,h4,p)')[i];
  m.scrollTop += b.getBoundingClientRect().top - m.getBoundingClientRect().top - bar - 20; return i; }""" % CH
DIST = """(i) => { const m = document.querySelector('.app-main'); const bar = document.querySelector('.reader-bar-top').offsetHeight;
  const sec = document.querySelector('[data-continuous-book]') ? document.querySelector('[data-book-section="%s"]') : m;
  const b = sec.querySelectorAll('article :is(h1,h2,h3,h4,p)')[i]; const s = m.getBoundingClientRect();
  return Math.abs(b.getBoundingClientRect().top - s.top - bar) / (s.height - bar); }""" % CH
DIALOG = """() => { const d = document.querySelector('[data-bookmark-dialog]'); if (!d) return null;
  const card = d.querySelector('[role=dialog]'); const r = card.getBoundingClientRect();
  const bd = getComputedStyle(d.querySelector('.bookmark-name-backdrop'));
  const inp = d.querySelector('[data-bookmark-dialog-input]');
  return {mode: d.getAttribute('data-bookmark-dialog'), cx: Math.round(r.left + r.width / 2 - innerWidth / 2),
          cy: Math.round(r.top + r.height / 2 - innerHeight / 2), bg: bd.backgroundColor,
          blur: bd.backdropFilter || bd.webkitBackdropFilter || 'none', x: !!d.querySelector('[data-bookmark-dialog-close] svg line'),
          value: inp && inp.value, confirm: !!d.querySelector('[data-bookmark-dialog-confirm]'), cancel: !!d.querySelector('[data-bookmark-dialog-cancel]')}; }"""
ROW = """(row) => { const t = row.querySelector('[data-bookmark-title]'); const cs = getComputedStyle(t);
  const pen = row.querySelector('[data-bookmark-rename]'); const rm = row.querySelector('[data-bookmark-remove]');
  const pr = pen && pen.getBoundingClientRect(); const rr = rm && rm.getBoundingClientRect(); const tr = t.getBoundingClientRect();
  const small = [...row.querySelectorAll('a span')].filter((s) => s.getClientRects().length && parseFloat(getComputedStyle(s).fontSize) < 13).length;
  const sw = (el) => el && el.querySelector('svg') && el.querySelector('svg').getAttribute('stroke-width');
  return {title: t.textContent, lines: Math.round(tr.height / parseFloat(cs.lineHeight || '20')), ellipsis: cs.textOverflow === 'ellipsis' && cs.whiteSpace === 'nowrap',
          cut: t.scrollWidth > t.clientWidth, second: !!row.querySelector('[data-bookmark-second]'), small,
          pen: !!pen, penLeftOfRemove: !!(pr && rr) && pr.right <= rr.left + 1 && Math.abs((pr.top + pr.height / 2) - (rr.top + rr.height / 2)) < 2,
          penSize: pr ? [Math.round(pr.width), Math.round(pr.height)] : null, stroke: [sw(pen), sw(rm)],
          gap: (pen && rm) ? Math.round(rm.querySelector('svg').getBoundingClientRect().left - pen.querySelector('svg').getBoundingClientRect().right) : null,
          textClear: !!pr && tr.right <= pr.left + 1,
          nested: !!(pen && pen.closest('a'))}; }"""
PLACED = """(i) => { const m = document.querySelector('.app-main'); const bar = document.querySelector('.reader-bar-top').offsetHeight;
  const sec = document.querySelector('[data-continuous-book]') ? document.querySelector('[data-book-section="%s"]') : m;
  const b = sec && sec.querySelectorAll('article :is(h1,h2,h3,h4,p)')[i]; if (!b) return null;
  return {top: Math.round(b.getBoundingClientRect().top - m.getBoundingClientRect().top - bar), lit: b.classList.contains('bookmark-flash'),
          text: b.textContent.slice(0, 20), path: location.pathname}; }""" % CH


def open_bookmarks(pg, touch, flow):
    pg.evaluate("document.querySelector('.app-main').scrollTop = 0")
    pg.wait_for_timeout(400)
    flow.contents()
    tab = pg.locator(f"{MENU} [data-sidebar-tab=bookmarks]")
    if tab.count() and tab.get_attribute("aria-selected") != "true":
        tap(pg, tab, touch)


def press_ribbon(pg, touch, flow):
    flow.bars()
    btn = pg.locator("[data-reader-action=bookmark]")
    if pg.locator(".reader-chrome[data-shown]").count():
        tap(pg, btn, touch, wait=500)
    else:
        btn.evaluate("b => b.click()")
        pg.wait_for_timeout(500)


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        for layout in ("page", "scroll"):
            b = getattr(p, eng).launch()
            touch = opts.get("has_touch", False)
            c = b.new_context(service_workers="block", locale="ru-RU", **opts)
            init = ("if (!sessionStorage.getItem('qaSeeded')) { localStorage.setItem('ap.readerHintSeen','1');"
                    f"localStorage.setItem('ap.readerLayout', '{layout}');"
                    f"localStorage.setItem('ap.bookmarks', JSON.stringify({json.dumps({'v': 1, 'items': SEED}, ensure_ascii=False)}));"
                    "sessionStorage.setItem('qaSeeded','1'); }")
            c.add_init_script(init)
            pg = c.new_page()
            tag = f"{dev}/{layout}"
            pg.goto(f"{BASE}/ru-iast/{CH}/", wait_until="networkidle")
            pg.wait_for_timeout(2500 if layout == "scroll" else 1500)
            flow = Contents(pg, qa.TocMode("default"), touch)
            verse = pg.evaluate(TO_VERSE, ["morning-prayers", 2])
            pg.wait_for_timeout(900)

            # 1. the window on a new bookmark, default name = the subsection's name
            press_ribbon(pg, touch, flow)
            d = pg.evaluate(DIALOG)
            check(tag, "1 a tap on the ribbon opens the name window (no bookmark yet)",
                  d is not None and d["mode"] == "add" and len(stored(pg)) == 3, d)
            if d is None:
                c.close(); b.close()
                continue
            check(tag, "1 window in the middle of the screen", abs(d["cx"]) <= 2 and abs(d["cy"]) <= 40, d)
            check(tag, "1 dimming black 60 %, no blur (V18); ✕; «Подтвердить» + «Отмена»",
                  d["bg"] == "rgba(0, 0, 0, 0.6)" and d["blur"] in ("none", "") and d["x"] and d["confirm"] and d["cancel"], d)
            check(tag, "1 default name = the subsection's name «1.1. Утренние молитвы»", d["value"] == "1.1. Утренние молитвы", d["value"])
            if layout == "page":
                shot(pg, dev, 1, "окно при добавлении, название по умолчанию")

            # «Отмена» sets nothing
            tap(pg, pg.locator("[data-bookmark-dialog-cancel]"), touch)
            check(tag, "«Отмена» closes the window and sets nothing", pg.locator(DLG).count() == 0 and len(stored(pg)) == 3, len(stored(pg)))

            # 2. renamed in the window, Enter confirms
            press_ribbon(pg, touch, flow)
            inp = pg.locator("[data-bookmark-dialog-input]")
            inp.fill(NAME)
            pg.wait_for_timeout(200)
            if layout == "page":
                shot(pg, dev, 2, "окно с новым названием")
            inp.press("Enter")
            pg.wait_for_timeout(500)
            new = [x for x in stored(pg) if x["section"] == CH]
            check(tag, "2 Enter confirms: stored with the name and the exact block of the verse",
                  pg.locator(DLG).count() == 0 and len(new) == 1 and new[0].get("name") == NAME and new[0]["block"] == verse["index"],
                  {"new": new, "verse": verse})
            block = new[0]["block"] if new else verse["index"]
            toast = pg.locator("[data-bookmark-toast]")
            check(tag, "2 toast «Закладка поставлена»", toast.count() == 1 and "Закладка поставлена" in toast.inner_text(), toast.count())
            pg.wait_for_timeout(4300)

            # 2b. «примерно на том же месте» (msg 5882): a little above the verse, it still on screen — filled, a tap removes
            ribbon = pg.locator("[data-reader-action=bookmark]")
            check(tag, "2b ribbon filled on the bookmarked verse", ribbon.get_attribute("aria-pressed") == "true", ribbon.get_attribute("aria-pressed"))
            pg.evaluate(TO_VERSE, ["morning-prayers", 1])
            pg.wait_for_timeout(900)
            near = pg.evaluate(DIST, block)
            check(tag, "2b about the same place (≤ ½ screen from the verse): ribbon filled", near <= 0.5 and ribbon.get_attribute("aria-pressed") == "true",
                  {"dist": round(near, 2), "pressed": ribbon.get_attribute("aria-pressed")})
            press_ribbon(pg, touch, flow)
            gone = [x for x in stored(pg) if x["section"] == CH]
            check(tag, "2b a tap there removes it (no window), toast «Закладка убрана»", pg.locator(DLG).count() == 0 and gone == []
                  and "Закладка убрана" in (pg.locator("[data-bookmark-toast]").inner_text() if pg.locator("[data-bookmark-toast]").count() else ""), gone)
            if pg.locator("[data-bookmark-toast] button").count():
                tap(pg, pg.locator("[data-bookmark-toast] button"), touch)
            check(tag, "2b «Отменить» brings it back", [x.get("name") for x in stored(pg) if x["section"] == CH] == [NAME], stored(pg))
            pg.wait_for_timeout(500)

            # 2c. several bookmarks in one subsection (msg 5881): two verses of 1.5, far apart
            pair = pg.evaluate(FAR_PAIR, LONG_SUB)
            pg.evaluate(TO_BLOCK, pair[0])
            pg.wait_for_timeout(900)
            check(tag, "2c away from it: ribbon not filled", ribbon.get_attribute("aria-pressed") == "false", ribbon.get_attribute("aria-pressed"))
            press_ribbon(pg, touch, flow)
            if pg.locator(DLG).count():
                tap(pg, pg.locator("[data-bookmark-dialog-confirm]"), touch)
            pg.wait_for_timeout(4300)
            pg.evaluate(TO_BLOCK, pair[1])
            pg.wait_for_timeout(900)
            far = [x for x in stored(pg) if x.get("anchor") == LONG_SUB]
            dist = pg.evaluate(DIST, far[0]["block"]) if far else None
            check(tag, "2c second place in the same subsection, > ½ screen away: ribbon not filled",
                  len(far) == 1 and dist > 0.5 and ribbon.get_attribute("aria-pressed") == "false",
                  {"far": far, "dist": dist, "pair": pair, "pressed": ribbon.get_attribute("aria-pressed")})
            press_ribbon(pg, touch, flow)
            d2 = pg.evaluate(DIALOG)
            check(tag, "2c the ribbon opens «Новая закладка» (the other one stays)", d2 is not None and d2["mode"] == "add", d2)
            if d2 is not None:
                tap(pg, pg.locator("[data-bookmark-dialog-confirm]"), touch)
            two = [x for x in stored(pg) if x.get("anchor") == LONG_SUB]
            check(tag, "2c two bookmarks in subsection 1.5, each with its own block",
                  len(two) == 2 and {x["block"] for x in two} == set(pair), {"two": two, "pair": pair})
            pg.wait_for_timeout(4300)

            # 3. «Закладки»: the renamed row only its name, one line, «…»; the pencil left of the remove icon
            open_bookmarks(pg, touch, flow)
            rows = pg.locator(f"{MENU} [data-bookmark-row]")
            looks = {rows.nth(i).get_attribute("data-bookmark-id"): rows.nth(i).evaluate(ROW) for i in range(rows.count())}
            mine = next((v for v in looks.values() if v["title"] == NAME), None)
            check(tag, "3 six rows (two in 1.5); the new one titled «Мантра при пробуждении»", rows.count() == 6 and mine is not None, list(looks))
            if mine is None:
                c.close(); b.close()
                continue
            check(tag, "3 renamed: only the name — no chapter line, no small date", not mine["second"] and mine["small"] == 0
                  and not looks["b-long"]["second"] and looks["b-long"]["small"] == 0, [mine, looks["b-long"]])
            check(tag, "3 long name: one line with «…»", looks["b-long"]["ellipsis"] and looks["b-long"]["cut"] and looks["b-long"]["lines"] == 1, looks["b-long"])
            check(tag, "3 old bookmark (no name): chapter + subsection + date as before",
                  looks["b-svagata"]["second"] and looks["b-svagata"]["small"] == 1 and looks["b-svagata"]["title"].startswith("4."), looks["b-svagata"])
            check(tag, "3 pencil left of the remove icon, thin line 1.5, close to it (icon gap 8–18 px, Vraja 5897), 44 px, not in the row link",
                  all(v["pen"] and v["penLeftOfRemove"] and v["stroke"] == ["1.5", "2"] and v["gap"] is not None and 8 <= v["gap"] <= 18 and v["penSize"][0] >= 44 and v["penSize"][1] >= 44
                      and v["textClear"] and not v["nested"] for v in looks.values()), list(looks.values()))
            if layout == "page":
                shot(pg, dev, 3, "боковое меню Закладки")
                shot(pg, dev, 6, "две закладки в одном разделе")

            # 4. the pencil opens the same window with the name
            tap(pg, pg.locator(f"{MENU} [data-bookmark-id=b-long] [data-bookmark-rename]"), touch)
            d = pg.evaluate(DIALOG)
            check(tag, "4 pencil opens the same window with the bookmark's name", d is not None and d["mode"] == "rename" and d["value"] == LONG, d)
            if layout == "page":
                shot(pg, dev, 4, "окно переименования из карандаша")
            if d is not None:
                inp = pg.locator("[data-bookmark-dialog-input]")
                inp.fill("Гандха")
                tap(pg, pg.locator("[data-bookmark-dialog-confirm]"), touch)
                renamed = next((x for x in stored(pg) if x["id"] == "b-long"), {})
                row = pg.locator(f"{MENU} [data-bookmark-id=b-long] [data-bookmark-title]")
                check(tag, "4 «Подтвердить» renames (storage and row), menu stays open",
                      renamed.get("name") == "Гандха" and row.count() == 1 and row.inner_text() == "Гандха" and pg.locator(MENU).count() == 1,
                      renamed)
                # the default name again = no own name (shows as before)
                tap(pg, pg.locator(f"{MENU} [data-bookmark-id=b-acamana] [data-bookmark-rename]"), touch)
                v0 = pg.locator("[data-bookmark-dialog-input]").input_value() if pg.locator(DLG).count() else None
                if pg.locator(DLG).count():
                    pg.keyboard.press("Escape")
                    pg.wait_for_timeout(300)
                check(tag, "4 unnamed bookmark: the window shows its subsection's name; Esc closes, menu stays",
                      (v0 or "").startswith("4.5. Ачаман") and pg.locator(DLG).count() == 0 and pg.locator(MENU).count() == 1, v0)

            # 4b. rename with the side menu open (msg 5881): the window over the open panel, the list updated at once
            other = next((x["id"] for x in stored(pg) if x.get("anchor") == LONG_SUB and not x.get("name")), None)
            if other:
                tap(pg, pg.locator(f"{MENU} [data-bookmark-id='{other}'] [data-bookmark-rename]"), touch)
                d = pg.evaluate(DIALOG)
                check(tag, "4b pencil: window over the open side menu (menu not closed)",
                      d is not None and d["mode"] == "rename" and (d["value"] or "").startswith("1.5.") and pg.locator(MENU).count() == 1, d)
                pg.locator("[data-bookmark-dialog-input]").fill("Вторая мантра")
                pg.wait_for_timeout(200)
                if layout == "page":
                    shot(pg, dev, 7, "переименование при открытом боковом меню")
                tap(pg, pg.locator("[data-bookmark-dialog-confirm]"), touch)
                t2 = pg.locator(f"{MENU} [data-bookmark-id='{other}'] [data-bookmark-title]")
                check(tag, "4b after «Подтвердить»: menu still open, the row shows the new name",
                      pg.locator(MENU).count() == 1 and pg.locator(DLG).count() == 0 and t2.count() == 1 and t2.inner_text() == "Вторая мантра",
                      t2.inner_text() if t2.count() else None)
                if layout == "page":
                    shot(pg, dev, 8, "список после переименования")
            else:
                check(tag, "4b second bookmark of 1.1 present", False, stored(pg))

            # 5. the exact place: from another chapter, the bookmark opens at the verse, lit
            row = pg.locator(f"{MENU} [data-bookmark-row]").filter(has_text=NAME)
            tap(pg, row.locator("[data-bookmark-title]"), touch, wait=300)
            pg.locator(".mobile-menu[data-open]").wait_for(state="detached", timeout=4000)
            pg.wait_for_timeout(500)
            pg.wait_for_timeout(1200)
            at = pg.evaluate(PLACED, block)
            check(tag, "5 the bookmark opens at the verse itself, right below the top bar", at is not None and 0 <= at["top"] <= 24
                  and at["text"] == verse["text"]
                  and CH in at["path"], {"at": at, "verse": verse})
            # from another chapter
            if layout == "page":
                pg.goto(f"{BASE}/ru-iast/{OTHER}/", wait_until="networkidle")
                pg.wait_for_timeout(1500)
                open_bookmarks(pg, touch, flow)
                row = pg.locator(f"{MENU} [data-bookmark-row]").filter(has_text=NAME)
                tap(pg, row.locator("[data-bookmark-title]"), touch, wait=300)
                lit = False
                for _ in range(25):
                    at = pg.evaluate(PLACED, block) if CH in pg.url else None
                    if at and at["lit"]:
                        lit = True
                        pg.wait_for_timeout(250)
                        shot(pg, dev, 5, "открытие из другой главы — мантра на месте, подсвечена")
                        break
                    pg.wait_for_timeout(100)
                pg.wait_for_timeout(1800)
                at = pg.evaluate(PLACED, block)
                check(tag, "5 from another chapter: the verse right below the top bar, lit for a moment",
                      lit and at is not None and 0 <= at["top"] <= 24 and at["text"] == verse["text"], at)
            c.close()
            b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
