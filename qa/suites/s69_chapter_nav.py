"""V17 — chapter navigation (Vraja Lila msg 796, 20.10.2026 14:15; mock approved «всё верно», msg 5639;
labels «‹ Назад» / «Вперёд ›», msg 5635; saskarnes īpašnieks, «Стандарты» 0а; nodots-izpildei 20.10 14:15).

Task (verbatim, msg 796 as passed on): «1) нижняя выездная панель: УБРАТЬ строку «где мы / % прочтено»
(дубль — остаётся внизу страницы); 2) Back/Forward → предыдущая / следующая глава; 3) в Pages И Scroll —
переход к пред./след. главе (в Scroll — прыжок к началу главы); 4) на первой главе Previous ОТСУТСТВУЕТ
(не бледная), на последней — Next отсутствует; 5) Pages: блок «Next chapter» в конце глав убрать; долистал
до самого низа главы → 1 раз выезжают верхняя и нижняя панели (как при касании), при прокрутке вверх
уезжают; 6) собственный учёт истории шагов (подсказка «Вперёд — после Назад» и т.п.) — убрать.»

Checks, per device:
  A  the bottom bar has no «where we are / %» line; the faint status line at the bottom of the page stays;
  B  Pages: the order of «Вперёд ›» from the first page to the last is the order of the contents
     (data/book.json: chapters and parts, as the contents lists them — not a list in the app's code);
     every step opens the page at its top;  (desktop + pixel7: the whole walk; phones: a part of it)
  C  Pages: «‹ Назад» goes to the previous page in that order, at its top;
  D  first page: no «‹ Назад» at all (not pale); last page: no «Вперёд ›» at all;
  E  Pages: no «Next chapter» block at the end of a chapter; Scroll: none in the whole book;
  F  Pages: reading down to the very end of a chapter brings up the top and the bottom bar once;
     scrolling back up takes them away;
  G  Scroll: «Вперёд ›» / «‹ Назад» jump to the start of the next / previous chapter, the chapter's start
     at the same place as after a jump from the contents (scroll-margin of the section);
  H  no own history note («Вперёд — после Назад» etc.) after the buttons are used;
  I  «‹ Назад» / «Вперёд ›» are whole on screen (not cut, inside the viewport) — phones incl. iPhone SE.
Bars (Vraja Lila msg 5645, verbatim as passed on: «nodaļas SĀKUMĀ un tuvojoties BEIGĀM — augšējā un apakšējā
josla ir izbīdītas; pārslēdzot nodaļu ar Назад/Вперёд tās PALIEK uz vietas (nekustas, jaunā nodaļa sākas ar
izbīdītām joslām, nekas neraustās); virzoties pa nodaļu uz priekšu — joslas aiziet; atkal parādās tikai:
pieskāriens, nodaļas beigas, vai lietotājs atritina atpakaļ uz nodaļas sākumu»):
  J  Pages: a chapter opened at its start has both bars out (no tap) and they stay (no auto-hide);
  K  Pages and Scroll: «Вперёд ›» / «‹ Назад» — the bars never leave during the switch, the new chapter
     starts with them out;
  L  reading on (scrolling down) takes them away;
  M  scrolling up in the middle of the chapter does not bring them; back at the chapter's start does.
Vraja Lila msg 5784 «СРОЧНО ИСПРАВИТЬ» / 5786–5787 (mock «как надо»: «8. Маха-абхишека» whole right under the top bar):
  T  after «Вперёд ›» / «‹ Назад» (Pages and Scroll) the chapter's title is whole on screen below the shown top bar
     (title top ≥ top bar bottom, title bottom inside the screen).
usage: python s69_chapter_nav.py <base-url>
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
BOOK = json.load(open(os.path.join(HERE, "..", "..", "data", "book.json"), encoding="utf-8"))


def contents_order():
    """Chapters and parts in the order the contents lists them (lib/book.ts tocLayout, re-done here)."""
    ids = [s["id"] for s in BOOK["sections"]]
    parts = BOOK.get("parts", [])
    part_of = {sid: i for i, p in enumerate(parts) for sid in p["sections"]}
    out, emitted = [], 0
    for sid in ids:
        p = part_of.get(sid)
        if p is not None:
            while emitted <= p:
                out.append(parts[emitted]["id"]); emitted += 1
        elif emitted > 0:
            while emitted < len(parts) and not parts[emitted]["sections"]:
                out.append(parts[emitted]["id"]); emitted += 1
        out.append(sid)
    while emitted < len(parts):
        out.append(parts[emitted]["id"]); emitted += 1
    return out


ORDER = contents_order()
results = []


def check(device, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {device} {name} {info}", flush=True)


BAR_JS = """() => {
  const q = s => document.querySelector(s);
  const vis = e => !!e && getComputedStyle(e).display !== 'none' && getComputedStyle(e).visibility !== 'hidden' && e.getClientRects().length > 0;
  const box = e => { const r = e.getBoundingClientRect(); return {l: Math.round(r.left), r: Math.round(r.right), w: Math.round(r.width), sw: e.scrollWidth, cw: e.clientWidth, t: (e.innerText||'').trim()}; };
  const back = q('[data-reader-nav=back]'), fwd = q('[data-reader-nav=forward]');
  return {
    back: vis(back) ? box(back) : null, fwd: vis(fwd) ? box(fwd) : null,
    backInDom: !!back, fwdInDom: !!fwd,
    progress: !!q('.reader-bar-bottom .reader-progress-label'),
    status: vis(q('.reader-status')),
    shown: !!q('.reader-chrome[data-shown]'),
    vw: innerWidth,
    note: !!q('[data-reader-nav-note]'),
  };
}"""

SHOWN_JS = """() => ({shown: !!document.querySelector('.reader-chrome[data-shown]'),
    top: parseFloat(getComputedStyle(document.querySelector('.reader-bar-top')).opacity),
    bottom: parseFloat(getComputedStyle(document.querySelector('.reader-bar-bottom')).opacity)})"""
# counts frames in which the bars are not shown, from now on
WATCH_JS = """() => { window.__barsGone = 0; const t0 = performance.now();
  const tick = () => { if (!document.querySelector('.reader-chrome[data-shown]')) window.__barsGone++;
    if (performance.now() - t0 < 2500) requestAnimationFrame(tick); };
  requestAnimationFrame(tick); }"""
TOP_JS = """() => { const m = document.querySelector('.app-main'); return m ? m.scrollTop : -1; }"""
PAGE_ID_JS = """() => location.pathname.replace(/\\/$/, '').split('/').pop()"""
# the current chapter's visible title (Pages: the page's; Scroll: the section's) against the top bar
TITLE_JS = """id => { const scope = document.querySelector(`[data-book-section="${id}"]`) || document.querySelector('.app-main');
  const h = [...scope.querySelectorAll('h1')].find(e => !e.classList.contains('sr-only') && e.getClientRects().length);
  const bar = document.querySelector('.reader-chrome[data-shown] .reader-bar-top');
  if (!h) return null; const r = h.getBoundingClientRect();
  return {top: Math.round(r.top), bottom: Math.round(r.bottom), bar: bar ? Math.round(bar.getBoundingClientRect().bottom) : null,
          vh: innerHeight, text: h.textContent.trim().slice(0, 40)}; }"""


def run(browser, device, options, walk):
    context = browser.new_context(service_workers="block", **options)
    # no install banner (as on Vraja's iPhone, msg 5786): it would push the page down and hide a title under the bar
    context.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true')}catch(e){}")
    page = context.new_page()
    errors = []
    host = BASE.split("//")[1].split("/")[0]
    page.on("pageerror", lambda error: None if (str(error).rstrip().endswith("due to access control checks.") and host in str(error)) else errors.append(str(error)))
    touch = options.get("has_touch", False)
    vw, vh = options["viewport"]["width"], options["viewport"]["height"]

    def bars():
        for _ in range(4):
            if page.locator(".reader-chrome[data-shown]").count():
                return True
            pt = qa.reading_eval(page, """root => {
              const H = window.innerHeight;
              for (const p of root.querySelectorAll('article p, article h1')) {
                if (p.closest('a,button,[data-hs-row],.hs-text,[data-no-reader-tap]')) continue;
                const r = p.getClientRects()[0];
                if (!r || r.top < 90 || r.bottom > H - 160 || r.width < 60) continue;
                return {x: r.left + Math.min(30, r.width / 3), y: r.top + r.height / 2};
              }
              return {x: 8, y: H / 2};
            }""")
            (page.touchscreen.tap if touch else page.mouse.click)(pt["x"], pt["y"])
            page.wait_for_timeout(500)
        return bool(page.locator(".reader-chrome[data-shown]").count())

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
        page.wait_for_timeout(700)
        return page.url != before

    def title_check(label, pid):
        t = page.evaluate(TITLE_JS, pid)
        check(device, f"T {label}: the chapter title is whole on screen below the top bar", bool(t) and t["bar"] is not None
              and t["top"] >= t["bar"] and t["bottom"] <= t["vh"], t)

    def page_id():
        return page.evaluate(PAGE_ID_JS)

    def goto(pid, scroll=False):
        page.goto(f"{BASE}/{LANG}/{pid}/", wait_until="networkidle")
        if scroll:
            # «Лента»: the page switches to the whole-book export after it loads — wait for that first
            page.wait_for_selector("[data-continuous-book]", state="attached", timeout=30000)
            qa.wait_for_book_chapter(page, pid)
        page.wait_for_timeout(900)

    try:
        # ---------------- Pages (default) ----------------
        mid = ORDER.index("arcana-procedure")
        goto(ORDER[mid])
        page.wait_for_timeout(5000)
        st = page.evaluate(SHOWN_JS)
        check(device, "J Pages: the chapter opened at its start has both bars out without a tap, still after 5 s", st["shown"] and st["top"] > 0.9 and st["bottom"] > 0.9, st)
        bars()
        b = page.evaluate(BAR_JS)
        check(device, "A bottom bar: no «where we are / %» line", not b["progress"], b)
        check(device, "A the faint status line at the bottom of the page stays (reading mode)", page.locator(".reader-status").count() == 1)
        check(device, "I «‹ Назад» whole on screen", bool(b["back"]) and b["back"]["l"] >= 0 and b["back"]["r"] <= b["vw"] and b["back"]["sw"] <= b["back"]["cw"] + 1, b["back"])
        check(device, "I «Вперёд ›» whole on screen", bool(b["fwd"]) and b["fwd"]["l"] >= 0 and b["fwd"]["r"] <= b["vw"] and b["fwd"]["sw"] <= b["fwd"]["cw"] + 1, b["fwd"])
        check(device, "E Pages: no «Next chapter» block at the end of the chapter", page.locator(".chapter-next, .chapter-next-space").count() == 0)

        page.evaluate(WATCH_JS)
        ok = press("forward")
        gone = page.evaluate("() => window.__barsGone")
        st = page.evaluate(SHOWN_JS)
        check(device, "K Pages «Вперёд ›»: the bars never leave during the switch; the new chapter starts with them out", gone == 0 and st["shown"] and st["bottom"] > 0.9, {"gone": gone, **st})
        check(device, f"B Pages «Вперёд ›»: {ORDER[mid]} -> {ORDER[mid + 1]}", ok and page_id() == ORDER[mid + 1], page.url)
        check(device, "B Pages: the next page opens at its top", page.evaluate(TOP_JS) <= 2, page.evaluate(TOP_JS))
        title_check("Pages «Вперёд ›»", ORDER[mid + 1])
        ok = press("back")
        check(device, f"C Pages «‹ Назад»: {ORDER[mid + 1]} -> {ORDER[mid]}", ok and page_id() == ORDER[mid], page.url)
        check(device, "C Pages: the previous page opens at its top", page.evaluate(TOP_JS) <= 2, page.evaluate(TOP_JS))
        title_check("Pages «‹ Назад»", ORDER[mid])
        ok = press("back")
        check(device, f"C Pages «‹ Назад»: {ORDER[mid]} -> {ORDER[mid - 1]}", ok and page_id() == ORDER[mid - 1], page.url)
        b = page.evaluate(BAR_JS)
        check(device, "H no own history note after the buttons", not b["note"], b)

        # D first / last
        goto(ORDER[0]); bars()
        b = page.evaluate(BAR_JS)
        check(device, f"D first page ({ORDER[0]}): no «‹ Назад» at all", not b["backInDom"], b)
        check(device, f"D first page: «Вперёд ›» present", bool(b["fwd"]), b)
        goto(ORDER[-1]); bars()
        b = page.evaluate(BAR_JS)
        check(device, f"D last page ({ORDER[-1]}): no «Вперёд ›» at all", not b["fwdInDom"], b)
        check(device, f"D last page: «‹ Назад» present", bool(b["back"]), b)
        check(device, "E Pages (last chapter): no «Next chapter» block", page.locator(".chapter-next, .chapter-next-space").count() == 0)

        # B the whole order, page by page
        start, stop = (0, len(ORDER) - 1) if walk else (ORDER.index("vigraha-tattva"), ORDER.index("daily-duties-brahma-muhurta"))
        goto(ORDER[start])
        seen = [page_id()]
        for _ in range(stop - start):
            if not press("forward"):
                break
            seen.append(page_id())
        want = ORDER[start:stop + 1]
        check(device, f"B «Вперёд ›» follows the contents order ({len(want)} pages: {want[0]} … {want[-1]})", seen == want,
              "" if seen == want else f"seen {seen} want {want}")

        # L / M / F: reading on, scrolling up in the middle, back at the start, the end
        goto("daily-deity-schedule")
        m = "document.querySelector('.app-main')"

        def user_scroll(dy, steps=1):
            for _ in range(steps):
                page.evaluate(f"{m}.dispatchEvent(new Event('touchmove'))"); page.evaluate(f"{m}.dispatchEvent(new WheelEvent('wheel'))")
                page.evaluate(f"{m}.scrollBy(0, {dy})"); page.wait_for_timeout(120)
            page.wait_for_timeout(450)

        user_scroll(80, 4)
        st = page.evaluate(SHOWN_JS)
        check(device, "L reading on (down) from the start takes the bars away", not st["shown"], st)
        user_scroll(400, 3)
        user_scroll(-70, 3)
        st = page.evaluate(SHOWN_JS)
        check(device, "M scrolling up in the middle of the chapter does not bring the bars", not st["shown"], st)
        page.evaluate(f"{m}.dispatchEvent(new Event('touchmove'))"); page.evaluate(f"{m}.scrollTo(0, 0)"); page.wait_for_timeout(100)
        user_scroll(-10, 1)
        st = page.evaluate(SHOWN_JS)
        check(device, "M back at the chapter's start: both bars out", st["shown"] and st["top"] > 0.9 and st["bottom"] > 0.9, st)
        user_scroll(80, 4)
        page.evaluate(f"{m}.scrollTop = {m}.scrollHeight - {m}.clientHeight - 700"); page.wait_for_timeout(1200)
        bars_hidden_first = not page.evaluate(SHOWN_JS)["shown"]
        user_scroll(120, 8)
        st = page.evaluate(SHOWN_JS)
        check(device, "F Pages: at the very end of the chapter the top and the bottom bar come up", bars_hidden_first and st["shown"] and st["top"] > 0.9 and st["bottom"] > 0.9, {"hidden_before": bars_hidden_first, **st})
        page.wait_for_timeout(4500)
        st = page.evaluate(SHOWN_JS)
        check(device, "F Pages: at the end they stay (no auto-hide after 4 s)", st["shown"], st)
        user_scroll(-40, 3)
        st2 = page.evaluate("() => !!document.querySelector('.reader-chrome[data-shown]')")
        check(device, "F Pages: scrolling back up from the end takes the bars away", not st2, st2)

        # ---------------- Scroll («Лента») ----------------
        page.evaluate("try{localStorage.setItem('ap.readerLayout','scroll')}catch(e){}")
        goto("arcana-procedure", scroll=True)
        check(device, "E Scroll: the book has no «Next chapter» block", page.locator("[data-continuous-book]").count() == 1 and page.locator(".chapter-next, .chapter-next-space").count() == 0,
              page.locator(".chapter-next, .chapter-next-space").count())
        bars()
        b = page.evaluate(BAR_JS)
        check(device, "A Scroll: bottom bar has no «where we are / %» line", not b["progress"], b)
        GEO = """id => { const m = document.querySelector('.app-main'); const s = document.querySelector(`[data-book-section="${id}"]`);
            if (!m || !s) return null; const margin = parseFloat(getComputedStyle(s).scrollMarginTop) || 0;
            return {off: Math.round(s.getBoundingClientRect().top - m.getBoundingClientRect().top - margin), url: location.pathname}; }"""
        i = ORDER.index("arcana-procedure")
        page.evaluate(WATCH_JS)
        ok = press("forward")
        gone = page.evaluate("() => window.__barsGone")
        st = page.evaluate(SHOWN_JS)
        check(device, "K Scroll «Вперёд ›»: the bars never leave during the jump and are out at the new chapter", gone == 0 and st["shown"] and st["bottom"] > 0.9, {"gone": gone, **st})
        g = page.evaluate(GEO, ORDER[i + 1])
        check(device, f"G Scroll «Вперёд ›»: jump to the start of {ORDER[i + 1]}", ok and g and abs(g["off"]) <= 2 and g["url"].rstrip("/").endswith("/" + ORDER[i + 1]), g)
        title_check("Scroll «Вперёд ›»", ORDER[i + 1])
        ok = press("back")
        g = page.evaluate(GEO, ORDER[i])
        check(device, f"G Scroll «‹ Назад»: jump to the start of {ORDER[i]}", ok and g and abs(g["off"]) <= 2 and g["url"].rstrip("/").endswith("/" + ORDER[i]), g)
        title_check("Scroll «‹ Назад»", ORDER[i])
        ok = press("back")
        g = page.evaluate(GEO, ORDER[i - 1])
        check(device, f"G Scroll «‹ Назад» again: the start of {ORDER[i - 1]}", ok and g and abs(g["off"]) <= 2, g)
        b = page.evaluate(BAR_JS)
        check(device, "H Scroll: no own history note after the buttons", not b["note"], b)
        page.evaluate("try{localStorage.removeItem('ap.readerLayout')}catch(e){}")
        check(device, "no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(device, "scenario ran", False, str(error)[:300])
    finally:
        context.close()


with sync_playwright() as playwright:
    for device, engine, options in qa.devices(["pixel7", "iphone14", "iphone-se", "ipad-portrait", "desktop"]):
        browser = getattr(playwright, engine).launch()
        run(browser, device, options, walk=device in ("pixel7", "desktop"))
        browser.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
