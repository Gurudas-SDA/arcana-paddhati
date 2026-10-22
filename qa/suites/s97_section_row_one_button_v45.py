"""V45 — a section's row in «Содержание» is ONE button; no section pages; the cover's bottom bar has «Вперёд ›»
(Vraja Lila msg 6178 / 6185 / 6188 / 6191, 22.10.2026; nodots-izpildei 22.10 17:10 msg 1412 + 1419/1422;
saskarnes autors, «Стандарты» 0а).

Rule text (Vraja Lila msg 6178, verbatim):
 «Должно стать: вся полоса - одна кнопка (так было раньше). Нажатие в любое её место раскрывает список глав, повторное
  сворачивает. Никуда не уводит, место чтения не меняет. Стрелка ▸ остаётся значком состояния внутри строки, отдельной
  целью нажатия быть перестаёт - как у главы с подразделами сегодня.»
 «Разделов пока пять: Введение, Храмовый стандарт, Домашний стандарт, Стандарт для проповеднических центров,
  Праздники, обеты и песни арати.»
 «ЧТО ОСТАЁТСЯ КАК ЕСТЬ: «Назад» и «Вперёд» проходят через текст раздела; подсвечена ровно одна строка - та, где
  читатель; подложка выделенной строки сплошная, без стыка между именем и стрелкой; … строка «Введение · N %» внизу
  контента книги.»
 «Так же мы добавляли содержание раздела при нажатии на раздел... в контейнере со стрелочками, где можно было
  переходить на главы... т.к. больше Раздел не является кнопкой которая открывает отдельную страницу Раздела, то это
  тоже нужно убрать»
Rule text (Vraja Lila msg 6191, verbatim): «на первой странице при клике нижняя панель должна выезжать с кнопкой
 вперёд, так мы сможем перейти в Посвящение … и там уже будет и Вперёд и Назад»
Criteria (register V45, verbatim): «строка раздела только раскрывает главы; страниц разделов нет; с обложки «Вперёд»
 ведёт на страницу после обложки; Назад/Вперёд проходят по порядку Содержания в обоих режимах».

Checks, per device (iPhone 14, desktop) × reading mode («Страницы», «Лента»):
  A  (п.1) each of the section rows is ONE control: one <button>, no link inside, the arrow ▸ is not a target of its own
     (the point on the arrow hits the row); a tap on the name and a tap on the arrow each open / fold the chapters;
     neither leaves the page nor moves the reading place (URL and scroll position unchanged);
  B  (п.2) no section page: no «В этом разделе» box (Страницы: the Introduction and a part's old address); «Назад» /
     «Вперёд» around every section (a part, a section without text) go chapter → chapter, never to the section;
  C  (п.3) exactly one lit row, where the reader is (also when his section is folded: then the section's row, one
     background name + arrow); the faint line «… · N %» at the bottom stays;
  D  (п.4) cover: a tap brings out the bottom bar with ONLY «Вперёд ›» → the first page after the cover; there both
     «‹ Назад» (→ the cover) and «Вперёд ›»;
  E  walking «Вперёд ›» from the cover to the end visits exactly the pages of the contents in order (cover first);
  F  «Лента»: the order of the text is the order of «Содержание» (all sections expanded).
Optional: V45_SHOTS=<dir> — screenshots «2026.10.22_V45 … — в книге (<режим>, <устройство>).png»;
          V45_REPORT=<file.json> — what was seen, per mode × device (for the report to Vraja Lila).
usage: python s97_section_row_one_button_v45.py <base-url>
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
import book_order  # noqa: E402
from toc import STATE, marks_place  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
LANG = "ru-iast"
CH = "daily-deity-schedule"          # a chapter inside «Храмовый стандарт» (its section is open by default)
GROUPS = book_order.groups(LANG)
PAGES = book_order.pages(LANG)
LAYOUT = [i for _, i in book_order.layout(LANG)]
SHOTS = os.environ.get("V45_SHOTS")
REPORT = os.environ.get("V45_REPORT")
MODES = [("pages", "Страницы"), ("scroll", "Лента")]
DEV_RU = {"iphone14": "iPhone 14", "desktop": "компьютер", "pixel7": "Pixel 7"}
results = []
report = {}

# The pages around each run of non-pages (parts' headings, sections without text) in the contents' order.
BOUNDS = []
for k, i in enumerate(LAYOUT):
    if i in PAGES or k == 0:
        continue
    if LAYOUT[k - 1] in PAGES:
        before = LAYOUT[k - 1]
        after = next((x for x in LAYOUT[k + 1:] if x in PAGES), None)
        if after:
            BOUNDS.append((before, after, i))

BAR = """(sel) => { const b = document.querySelector(sel); if (!b) return {on: false};
  const cs = getComputedStyle(b); const r = b.getBoundingClientRect();
  const inView = r.height > 0 && r.bottom > 0.5 && r.top < innerHeight - 0.5;
  return {display: cs.display, top: Math.round(r.top), bottom: Math.round(r.bottom), vh: innerHeight,
          on: cs.display !== 'none' && +cs.opacity > 0.05 && inView && r.bottom <= innerHeight + 1}; }"""
NAV = """() => { const t = (d) => { const b = document.querySelector(`[data-reader-nav=${d}]`);
    return b ? b.getAttribute('data-chapter-target') : null; };
  return {back: t('back'), forward: t('forward')}; }"""
ROW = """(gid) => { const row = document.querySelector(`.mobile-menu[data-open] [data-toc-group-row="${gid}"]`);
  if (!row) return null;
  // the row may lie below the fold of the menu (an open section above it): elementFromPoint only sees the viewport
  row.scrollIntoView({block: 'nearest'});
  const r = row.getBoundingClientRect();
  const atArrow = document.elementFromPoint(r.right - 22, r.top + r.height / 2);
  const atName = document.elementFromPoint(r.left + 30, r.top + r.height / 2);
  const ctl = (e) => e && e.closest('button, a[href]');
  const paint = (e) => { for (let n = e; n && n !== document.body; n = n.parentElement) { const c = getComputedStyle(n).backgroundColor;
      if (c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent') return c; } return 'none'; };
  const svg = row.querySelector('svg');
  return {tag: row.tagName, inner: row.querySelectorAll('a[href], button').length, inLink: !!row.closest('a[href]'),
          arrowHitsRow: ctl(atArrow) === row, nameHitsRow: ctl(atName) === row, expanded: row.getAttribute('aria-expanded'),
          lit: row.hasAttribute('data-toc-lit'), namePaint: paint(row.firstElementChild || row), arrowPaint: paint(svg || row),
          text: row.textContent.trim(), top: Math.round(r.top), vh: innerHeight}; }"""
ROWS_ORDER = """() => [...document.querySelectorAll('.mobile-menu[data-open] nav [data-toc-row]')]
  .map(e => e.dataset.tocRow).filter(r => r.startsWith('grp:') || r.startsWith('sec:')).map(r => r.slice(4))"""
FEED_ORDER = """() => [...document.querySelectorAll('[data-continuous-book] [data-book-section]')].map(e => e.dataset.bookSection).filter(Boolean)"""
SCROLL = """() => Math.round(document.querySelector('.app-main').scrollTop)"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:500]}", flush=True)


def run(browser, dev, opts, mode, mode_ru):
    touch = opts.get("has_touch", False)
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    init = "try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');"
    init += ("localStorage.setItem('ap.readerLayout','scroll')" if mode == "scroll" else "localStorage.removeItem('ap.readerLayout')")
    c.add_init_script(init + "}catch(e){}")
    pg = c.new_page()
    errors = []
    host = BASE.split("//")[1].split("/")[0]
    pg.on("pageerror", lambda e: None if (str(e).rstrip().endswith("due to access control checks.") and host in str(e)) else errors.append(str(e)))
    tag = f"{dev}/{mode_ru}"
    rep = report.setdefault(f"{mode_ru} × {DEV_RU.get(dev, dev)}", {})
    state = lambda: pg.evaluate(STATE)
    page_id = lambda: pg.evaluate("() => location.pathname.replace(/\\/$/, '').split('/').pop()")
    at_cover = lambda: page_id() == LANG

    def shot(what):
        if SHOTS:
            os.makedirs(SHOTS, exist_ok=True)
            pg.screenshot(path=os.path.join(SHOTS, f"2026.10.22_V45 {what} — в книге ({mode_ru}, {DEV_RU.get(dev, dev)}).png"))

    def goto(pid):
        pg.goto(f"{BASE}/{LANG}/{pid + '/' if pid else ''}", wait_until="networkidle")
        if pid and mode == "scroll":
            pg.wait_for_selector("[data-continuous-book]", state="attached", timeout=30000)
            qa.wait_for_book_chapter(pg, pid)
        pg.wait_for_timeout(900)

    def bars():
        for _ in range(4):
            if state()["menu"] or pg.locator(".reader-chrome[data-shown]").count():
                return
            cover = pg.locator("img.home-cover")
            if at_cover() and cover.count():
                (cover.first.tap if touch else cover.first.click)()
            else:
                pt = qa.reading_eval(pg, """root => {
                  const H = window.innerHeight;
                  for (const p of root.querySelectorAll('article p, article h1, article li, figure')) {
                    if (p.closest('a,button,[data-hs-row],.hs-text,[data-no-reader-tap]')) continue;
                    const r = p.getClientRects()[0];
                    if (!r || r.top < 90 || r.bottom > H - 160 || r.width < 60) continue;
                    return {x: r.left + Math.min(30, r.width / 3), y: r.top + Math.min(r.height / 2, 20)};
                  }
                  return {x: 8, y: H / 2};
                }""")
                (pg.touchscreen.tap if touch else pg.mouse.click)(pt["x"], pt["y"])
            pg.wait_for_timeout(450)

    def tap(locator, x=None, right=False, wait=450):
        locator.scroll_into_view_if_needed()
        box = locator.bounding_box()
        pos = {"x": box["width"] - 22 if right else (x if x is not None else 30), "y": box["height"] / 2}
        (locator.tap if touch else locator.click)(position=pos)
        pg.wait_for_timeout(wait)

    def contents():
        bars()
        tap(pg.locator("[data-reader-action=contents]"), x=10, wait=700)
        pg.wait_for_selector(".mobile-menu[data-open] nav", timeout=5000)
        pg.wait_for_timeout(300)

    def close_menu():
        for _ in range(12):
            if not state()["menu"]:
                break
            pg.go_back()
            pg.wait_for_timeout(450)
        pg.wait_for_timeout(500)

    def press(direction):
        bars()
        loc = pg.locator(f"[data-reader-nav={direction}]")
        if not loc.count():
            return False
        before = pg.url
        (loc.tap if touch else loc.click)()
        for _ in range(50):
            pg.wait_for_timeout(120)
            if pg.url != before:
                break
        pg.wait_for_timeout(700)
        return pg.url != before

    try:
        # ---------- D: the cover ----------
        goto(None)
        bars()
        pg.wait_for_timeout(400)
        bottom = pg.evaluate(BAR, ".reader-bar-bottom")
        nav = pg.evaluate(NAV)
        check(tag, "D cover: a tap brings out the bottom bar", bottom["on"], bottom)
        check(tag, f"D cover: in it ONLY «Вперёд ›» → {PAGES[0]} (the page after the cover)",
              nav == {"back": None, "forward": PAGES[0]}, nav)
        rep["обложка: нижняя панель"] = "выезжает" if bottom["on"] else "НЕ выезжает"
        rep["обложка: кнопки"] = nav
        shot("обложка, нижняя панель")
        ok = press("forward")
        check(tag, f"D cover «Вперёд ›» opens {PAGES[0]}", ok and page_id() == PAGES[0], pg.url)
        bars()
        nav = pg.evaluate(NAV)
        check(tag, "D the page after the cover: «‹ Назад» → cover and «Вперёд ›» → the next page",
              nav == {"back": "cover", "forward": PAGES[1]}, nav)
        rep["страница после обложки"] = {"id": page_id(), "title": book_order.title(LANG, page_id()), "кнопки": nav}
        shot("страница после обложки, обе кнопки")
        ok = press("back")
        check(tag, "D «‹ Назад» there returns to the cover", ok and at_cover(), pg.url)

        # ---------- A + C: the section rows of «Содержание» ----------
        goto(CH)
        pg.evaluate("() => { const m = document.querySelector('.app-main'); m.scrollTop += 300; m.dispatchEvent(new Event('scroll')); }")
        pg.wait_for_timeout(700)
        url0, top0 = pg.url, pg.evaluate(SCROLL)
        contents()
        st = state()
        check(tag, "C menu on a chapter: exactly one lit row — the reader's place", marks_place(st), st["lit"])
        rows_seen = {}
        for gid, title, members in GROUPS:
            r = pg.evaluate(ROW, gid)
            if r is None:
                check(tag, f"A «{title}»: its row in «Содержание»", False)
                continue
            one = r["tag"] == "BUTTON" and r["inner"] == 0 and not r["inLink"] and r["arrowHitsRow"] and r["nameHitsRow"]
            check(tag, f"A «{title}»: the whole row is ONE button, ▸ only an icon inside it", one, r)
            row = pg.locator(f".mobile-menu[data-open] [data-toc-group-row='{gid}']")
            seen = []
            for where, right in (("name", False), ("arrow", True)):
                was = r["expanded"] if where == "name" else seen[-1]
                tap(row, right=right)
                st2 = state()
                now = row.get_attribute("aria-expanded") if row.count() else None
                kids_shown = pg.evaluate("""(ids) => ids.map(id => document.querySelector(`.mobile-menu[data-open] [data-toc-row="sec:${id}"]`))
                    .filter(e => e && e.getClientRects().length).length""", members)
                empty_line = pg.locator(f".mobile-menu[data-open] [data-toc-empty-part='{gid}']").count()
                opened_ok = (kids_shown == len(members) and (members or empty_line == 1)) if now == "true" else kids_shown == 0
                stay = st2["menu"] and pg.url == url0 and abs(pg.evaluate(SCROLL) - top0) <= 2
                check(tag, f"A «{title}»: a tap on the {where} {'opens' if was == 'false' else 'folds'} the chapters, stays in place",
                      now is not None and now != was and opened_ok and stay,
                      {"was": was, "now": now, "kids": kids_shown, "of": len(members), "url": pg.url, "scroll": pg.evaluate(SCROLL), "top0": top0})
                if not st2["menu"] or pg.url != url0:   # before V45 the name led to the section's page
                    goto(CH)
                    pg.evaluate("() => { const m = document.querySelector('.app-main'); m.scrollTop += 300; m.dispatchEvent(new Event('scroll')); }")
                    pg.wait_for_timeout(700)
                    url0, top0 = pg.url, pg.evaluate(SCROLL)
                    contents()
                    row = pg.locator(f".mobile-menu[data-open] [data-toc-group-row='{gid}']")
                    seen.append(row.get_attribute("aria-expanded") if row.count() else None)
                    break
                seen.append(now)
                st3 = state()
                check(tag, f"C «{title}» {where}: still exactly one lit row, the reader's place", marks_place(st3), st3["lit"])
            rows_seen[title] = "раскрывает/сворачивает, никуда не уводит" if len(seen) == 2 and seen[0] != r["expanded"] and seen[1] == r["expanded"] else f"иначе: {seen}"
        rep["строка раздела"] = rows_seen
        # the reader's section folded: its row is the lit one, one background over name + arrow
        home = next((g for g in GROUPS if CH in g[2]), None)
        if home:
            row = pg.locator(f".mobile-menu[data-open] [data-toc-group-row='{home[0]}']")
            if row.count() and row.get_attribute("aria-expanded") == "true":
                tap(row)
            pg.mouse.move(1, 1)
            pg.wait_for_timeout(300)
            r = pg.evaluate(ROW, home[0])
            st = state()
            check(tag, f"C «{home[1]}» folded with the reader inside: its row is the one lit row, one background",
                  r is not None and r["lit"] and st["lit"] == [f"grp:{home[0]}"] and r["namePaint"] == r["arrowPaint"]
                  and r["namePaint"] not in ("none", "rgb(255, 255, 255)"), {"row": r, "lit": st["lit"]})
            shot("Содержание, строка раздела")
            if row.count():
                tap(row)
        # F: every section expanded — the contents' order
        for gid, _, _ in GROUPS:
            row = pg.locator(f".mobile-menu[data-open] [data-toc-group-row='{gid}']")
            if row.count() and row.get_attribute("aria-expanded") == "false":
                tap(row, wait=300)
        toc_order = pg.evaluate(ROWS_ORDER)
        goto(CH)   # (the menu's steps are history entries: a fresh page instead of many Backs)
        status = (pg.locator(".reader-status").first.text_content() or "").strip() if pg.locator(".reader-status").count() else ""
        check(tag, "C the faint line «… · N %» at the bottom stays", "%" in status, status)
        if mode == "scroll":
            feed = pg.evaluate(FEED_ORDER)
            check(tag, "F «Лента»: the order of the text = the order of «Содержание»", feed == toc_order == LAYOUT,
                  {"feed": feed[:12], "toc": toc_order[:12], "data": LAYOUT[:12]})
            rep["порядок «Ленты» = «Содержание»"] = feed == toc_order
        else:
            check(tag, "F «Содержание» lists the sections and chapters in the book's order", toc_order == LAYOUT, toc_order[:12])

        # ---------- B: no section pages ----------
        if mode == "pages":
            for gid in ("introduction", GROUPS[1][0]):
                goto(gid)
                n = pg.locator("[data-section-chapters], .section-chapters, .group-contents").count()
                check(tag, f"B /{gid}/: no «В этом разделе» box", n == 0, n)
        for before, after, between in BOUNDS:
            goto(before)
            bars()
            nav = pg.evaluate(NAV)
            check(tag, f"B «Вперёд ›» from {before} → {after} (over «{between}», not to it)", nav["forward"] == after, nav)
            goto(after)
            bars()
            nav = pg.evaluate(NAV)
            check(tag, f"B «‹ Назад» from {after} → {before}", nav["back"] == before, nav)

        # ---------- E: walk «Вперёд ›» from the cover through the whole book ----------
        goto(None)
        visited = []
        for _ in range(len(PAGES) + 3):
            if not press("forward"):
                break
            if mode == "scroll" and page_id() != LANG:
                try:
                    qa.wait_for_book_chapter(pg, page_id())
                except Exception:
                    pass
            visited.append(page_id())
        check(tag, "E «Вперёд ›» from the cover visits exactly the contents' pages, in order", visited == PAGES,
              {"visited": visited, "want": PAGES})
        rep["Вперёд от обложки до конца"] = "все страницы по порядку «Содержания»" if visited == PAGES else {"visited": visited}
        back = []
        for _ in range(3):
            if not press("back"):
                break
            back.append(page_id())
        check(tag, "E «‹ Назад» from the last page goes back through the same pages", back == PAGES[-2:-5:-1], back)
        check(tag, "no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(tag, "scenario ran", False, str(error)[:300])
    finally:
        c.close()


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "desktop"]):
        b = getattr(p, eng).launch()
        for mode, mode_ru in MODES:
            run(b, dev, opts, mode, mode_ru)
        b.close()

if REPORT:
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump({"pages": PAGES, "layout": LAYOUT, "seen": report}, f, ensure_ascii=False, indent=1)
print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
