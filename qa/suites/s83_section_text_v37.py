"""V37 — a section's own text from the contents (Vraja Lila msg 1306 / 1308, 21.10.2026 21:12–21:17; saskarnes
autors, «Стандарты» 0а; ‼️ priority, msg 1310).

Problem (verbatim, msg 1306): «есть разделы, такие как Введение, Храмовый стандарт и т.п. в которые самих по себе есть
контент/содержание, но я не могу в них никак попасть из бокового меню, т.е. нажимая на них мне открывается содержание
главы, где самого "Введения" нет или "Храмового стандарта" а сразу же есть внутренние главы... я могу попасть туда только
включив режим лента и отмотав наверх с 1 главы раздела».
Approved (verbatim, msg 1308, to the assistant's points 1–4):
  «1) да, единственное что тогда при нажатии на название раздела он должен быть подсвечен
   2) да... но так же они автоматом раскрываются при нажатии раздела (он выбирается - открывается), т.е. если я снова
      открою меню будучи на этом разделе, в боковом меню условно "Введение" будет подсвечено, но так же будет видно что
      внуьтри главы и я уже смогу навигировать так же и по внутренним главам
   3) да
   4) да»
  points (the assistant's, msg 1306 reply): «1. В боковом меню нажатие на само название раздела («Введение», «Храмовый
  стандарт» и т. п.) открывает его собственный текст. 2. Раскрыть или свернуть внутренние главы — отдельной стрелкой ▸
  справа от названия. 3. «Назад» с первой главы раздела ведёт на текст раздела, «Вперёд» с текста раздела — на первую
  главу. То же в «Страницах» и в «Ленте». 4. Пока раздел открыт, он подсвечен в меню как текущий.»
  and: «в самой книге внизу контента она [строка «Введение · N %»] должна быть» — it stays.

Checks, per device, for every section heading of the contents (the Introduction and each part):
  A  Pages: a tap on the section's NAME opens its own page (URL /<id>/, its heading on screen, at the top); the menu closes;
  B  the menu opened again there: the section's row is lit (the only lit row) and its chapters are listed under it;
  C  the arrow ▸ is a separate control at the right of the name; a tap on it collapses / expands the chapters and does
     not leave the page;
  D  Pages: «‹ Назад» from the section's first chapter -> the section's page; «Вперёд ›» from it -> the first chapter;
  E  Scroll («Лента»): a tap on the name jumps to the section's own text (its start at the top), the row is lit and open;
     «‹ Назад» / «Вперёд ›» go through the section's text the same way;
  F  the faint line «Введение · N %» at the bottom of the page stays (not removed).
usage: python s83_section_text_v37.py <base-url>
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
LANG = "ru-iast"
HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = json.load(open(os.path.join(HERE, "..", "..", "data", f"book.{LANG}.json"), encoding="utf-8"))
SECTIONS = {s["id"]: s for s in BOOK["sections"]}
# The section headings of the contents: the Introduction (its chapters = the front matter after it) and every part.
FRONT = [s["id"] for s in BOOK["sections"] if not any(s["id"] in p["sections"] for p in BOOK["parts"])]
INTRO = "introduction"
GROUPS = [(INTRO, SECTIONS[INTRO]["title"], FRONT[FRONT.index(INTRO) + 1:])] + [
    (p["id"], p["title"], p["sections"]) for p in BOOK["parts"]]
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:600]}", flush=True)


MENU_JS = """() => {
  const nav = document.querySelector('.mobile-menu[data-open] nav');
  const vis = e => !!e && e.getClientRects().length > 0;
  return {
    menu: !!nav,
    url: location.pathname + location.hash,
    lit: nav ? [...nav.querySelectorAll('[data-toc-lit]')].map(e => e.dataset.tocRow) : [],
    rows: nav ? [...nav.querySelectorAll('[data-toc-row]')].filter(vis).map(e => e.dataset.tocRow) : [],
  };
}"""
# the page's (Pages) / the section's (Scroll) own heading and where it stands
HEAD_JS = """id => {
  const m = document.querySelector('.app-main');
  const scope = document.querySelector(`[data-book-section="${id}"]`) || m;
  const h = [...scope.querySelectorAll('h1')].find(e => !e.classList.contains('sr-only') && e.getClientRects().length);
  const r = h ? h.getBoundingClientRect() : null;
  const margin = scope !== m ? (parseFloat(getComputedStyle(scope).scrollMarginTop) || 0) : 0;
  return {text: h ? h.textContent.trim() : null, top: r ? Math.round(r.top) : null, vh: innerHeight,
          off: scope !== m ? Math.round(scope.getBoundingClientRect().top - m.getBoundingClientRect().top - margin) : Math.round(m.scrollTop),
          status: (document.querySelector('.reader-status')?.textContent || '').trim()};
}"""
PAGE_ID_JS = """() => location.pathname.replace(/\\/$/, '').split('/').pop()"""


def run(browser, device, options):
    context = browser.new_context(service_workers="block", **options)
    context.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true')}catch(e){}")
    page = context.new_page()
    errors = []
    host = BASE.split("//")[1].split("/")[0]
    page.on("pageerror", lambda e: None if (str(e).rstrip().endswith("due to access control checks.") and host in str(e)) else errors.append(str(e)))
    touch = options.get("has_touch", False)
    state = lambda: page.evaluate(MENU_JS)

    def tap(locator, right=False, wait=400):
        locator.scroll_into_view_if_needed()
        box = locator.bounding_box()
        pos = {"x": box["width"] - 9 if right else 8, "y": box["height"] / 2}
        (locator.tap if touch else locator.click)(position=pos)
        page.wait_for_timeout(wait)

    def bars():
        for _ in range(4):
            if state()["menu"] or page.locator(".reader-chrome[data-shown]").count():
                return
            pt = qa.reading_eval(page, """root => {
              const H = window.innerHeight;
              for (const p of root.querySelectorAll('article p, article h1, article li')) {
                if (p.closest('a,button,[data-hs-row],.hs-text,[data-no-reader-tap]')) continue;
                const r = p.getClientRects()[0];
                if (!r || r.top < 90 || r.bottom > H - 160 || r.width < 60) continue;
                return {x: r.left + Math.min(30, r.width / 3), y: r.top + r.height / 2};
              }
              return {x: 8, y: H / 2};
            }""")
            (page.touchscreen.tap if touch else page.mouse.click)(pt["x"], pt["y"])
            page.wait_for_timeout(450)

    def contents():
        bars()
        tap(page.locator("[data-reader-action=contents]"), wait=700)
        page.wait_for_selector(".mobile-menu[data-open] nav", timeout=5000)
        page.wait_for_timeout(300)

    def wait_menu_closed():
        for _ in range(40):
            if not state()["menu"]:
                break
            page.wait_for_timeout(150)
        page.wait_for_timeout(600)

    def goto(pid, scroll=False):
        page.goto(f"{BASE}/{LANG}/{pid}/", wait_until="networkidle")
        if scroll:
            page.wait_for_selector("[data-continuous-book]", state="attached", timeout=30000)
            qa.wait_for_book_chapter(page, pid)
        page.wait_for_timeout(900)

    def press(direction):
        bars()
        loc = page.locator(f"[data-reader-nav={direction}]")
        if not loc.count():
            return False
        before = page.url
        (loc.tap if touch else loc.click)()
        for _ in range(40):
            page.wait_for_timeout(150)
            if page.url != before:
                break
        page.wait_for_timeout(800)
        return page.url != before

    def close_menu():
        for _ in range(8):
            if not state()["menu"]:
                break
            page.go_back(); page.wait_for_timeout(500)

    page_id = lambda: page.evaluate(PAGE_ID_JS)
    name = lambda gid: page.locator(f".mobile-menu[data-open] [data-toc-group='{gid}']")
    arrow = lambda gid: page.locator(f".mobile-menu[data-open] [data-toc-toggle='{gid}']")

    def name_tap(gid, title, mode):
        """A (or E): tap on the section's name; then B: the menu again."""
        before = state()
        tap(name(gid), wait=300)
        for _ in range(40):
            if page_id() == gid:
                break
            page.wait_for_timeout(150)
        wait_menu_closed()
        h = page.evaluate(HEAD_JS, gid)
        st = state()
        check(device, f"A/{mode} «{title}»: a tap on its name opens its own page", page_id() == gid and not st["menu"]
              and h["text"] and title in h["text"] and 0 <= (h["top"] or -1) < h["vh"] and abs(h["off"]) <= 2,
              {"from": before["url"], "url": st["url"], "menu": st["menu"], **h})
        if st["menu"]:
            close_menu()   # (before V37 the name only toggled: the menu stayed open)
        contents()
        st = state()
        kids = [f"sec:{c}" for c in kids_of[gid]] or [f"part:{gid}"]
        check(device, f"B/{mode} «{title}»: menu again — the section lit (only it) and its chapters shown",
              st["lit"] == [f"grp:{gid}"] and all(k in st["rows"] for k in kids), {"lit": st["lit"], "missing": [k for k in kids if k not in st["rows"]]})
        return st, kids

    kids_of = {gid: members for gid, _, members in GROUPS}
    try:
        # ---------------- Pages ----------------
        goto("arcana-procedure")
        for gid, title, members in GROUPS:
            contents()
            if not name(gid).count():
                check(device, f"A «{title}»: its row in the contents", False)
                continue
            st, kids = name_tap(gid, title, "Pages")
            # C — the arrow at the right of the name, a control of its own
            a = arrow(gid)
            nb = name(gid).bounding_box()
            ab = a.bounding_box() if a.count() else None
            check(device, f"C «{title}»: a separate arrow ▸ at the right of the name (44 px target)",
                  ab is not None and ab["x"] >= nb["x"] + nb["width"] - 2 and ab["width"] >= 43 and ab["height"] >= 43
                  and a.get_attribute("aria-expanded") == "true", {"name": nb, "arrow": ab})
            if ab is None:
                close_menu()
                continue
            url = state()["url"]
            tap(a, wait=500)
            st2 = state()
            check(device, f"C «{title}»: the arrow collapses its chapters, stays on the page",
                  st2["menu"] and st2["url"] == url and not any(k in st2["rows"] for k in kids) and a.get_attribute("aria-expanded") == "false",
                  {"url": st2["url"], "rows": [k for k in kids if k in st2["rows"]]})
            tap(a, wait=500)
            st3 = state()
            check(device, f"C «{title}»: the arrow expands them again",
                  st3["menu"] and st3["url"] == url and all(k in st3["rows"] for k in kids) and a.get_attribute("aria-expanded") == "true",
                  {"url": st3["url"]})
            close_menu()   # system Back over the menu's steps, for the next section

        # F — the faint status line at the bottom of the Introduction stays
        goto(INTRO)
        h = page.evaluate(HEAD_JS, INTRO)
        check(device, "F the faint line «Введение · N %» at the bottom of the page stays", page.locator(".reader-status").count() == 1
              and SECTIONS[INTRO]["title"] in h["status"] and "%" in h["status"], h["status"])

        # D — «Назад» / «Вперёд» through the section's page
        for gid, title, members in GROUPS:
            if not members:
                continue
            goto(members[0])
            ok = press("back")
            check(device, f"D Pages «‹ Назад» {members[0]} -> «{title}»", ok and page_id() == gid, page.url)
            ok = press("forward")
            check(device, f"D Pages «Вперёд ›» «{title}» -> {members[0]}", ok and page_id() == members[0], page.url)

        # ---------------- Scroll («Лента») ----------------
        page.evaluate("try{localStorage.setItem('ap.readerLayout','scroll')}catch(e){}")
        for gid, title, members in GROUPS[:2]:
            goto("arcana-procedure", scroll=True)
            contents()
            name_tap(gid, title, "Scroll")
            close_menu()
            if members:
                goto(members[0], scroll=True)
                ok = press("back")
                h = page.evaluate(HEAD_JS, gid)
                check(device, f"E Scroll «‹ Назад» {members[0]} -> the start of «{title}»", ok and page_id() == gid and abs(h["off"]) <= 2, h)
                ok = press("forward")
                h = page.evaluate(HEAD_JS, members[0])
                check(device, f"E Scroll «Вперёд ›» «{title}» -> the start of {members[0]}", ok and page_id() == members[0] and abs(h["off"]) <= 2, h)
        page.evaluate("try{localStorage.removeItem('ap.readerLayout')}catch(e){}")
        check(device, "no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(device, "scenario ran", False, str(error)[:300])
    finally:
        context.close()


with sync_playwright() as playwright:
    for device, engine, options in qa.devices(["iphone14", "pixel7", "desktop"]):
        browser = getattr(playwright, engine).launch()
        run(browser, device, options)
        browser.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
