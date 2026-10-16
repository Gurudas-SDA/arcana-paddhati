"""A89: continuous reading as an option of the «Аа» panel (Gurudas reading standard A3).

Pagination by default MUST; a scroll-mode option SHOULD, and if present the
mode is kept and switching keeps the position. Checks, per device:
  1. default: «Листать» pressed, the chapter is its own page (no continuous book);
  2. «Прокручивать»: the whole book in one scroll, the same chapter and the same
     words at the top of the screen;
  3. reload: still «Прокручивать» (stored), the same chapter and words;
  4. scrolling on crosses into the next chapter without a tap (continuous);
  5. «Листать» again: the chapter page, the same words at the top;
  6. reload: still «Листать».
usage: python s45_scroll_option.py <base-url>
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
LANG = "ru-iast"
CHAPTER = "daily-duties-brahma-muhurta"
# Words at the top of the screen may move by a line after a reflow of the
# other export (pictures, padding) — never by a paragraph.
TOL_PX = 60

TOP_BLOCK_JS = """root => {
  // The first text block (heading or paragraph) whose bottom is below the top
  // of the reading area: its text and its distance from that top.
  const main = document.querySelector('.app-main');
  const top = main.getBoundingClientRect().top;
  for (const el of root.querySelectorAll('article :is(h1,h2,h3,h4,p)')) {
    const r = el.getBoundingClientRect();
    if (!r.height || r.bottom <= top + 4) continue;
    return {text: (el.textContent || '').trim().slice(0, 80), delta: Math.round(r.top - top)};
  }
  return null;
}"""

EMPTY_POINT_JS = """root => {
  const H = window.innerHeight;
  const bad = (el) => !el || !!el.closest('a,button,input,select,label,[role=button],img,svg,.hs-text,.hs-figure,.verse-chips,.mood-toggle,[data-no-reader-tap]');
  for (const p of root.querySelectorAll('article p')) {
    if (p.closest('[data-hs-row]') || p.querySelector('a,button,.hs-text')) continue;
    const r = p.getClientRects()[0];
    if (!r || r.top < 90 || r.bottom > H - 160 || r.width < 120) continue;
    const pt = {x: r.left + Math.min(60, r.width / 3), y: r.top + r.height / 2};
    if (!bad(document.elementFromPoint(pt.x, pt.y))) return pt;
  }
  const a = root.querySelector('article').getBoundingClientRect();
  return {x: a.left + 6, y: H / 2};
}"""

results = []


def check(device, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {device} {name} {info}", flush=True)


def run(browser, device, options):
    context = browser.new_context(service_workers="block", **options)
    context.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    page = context.new_page()
    errors = []
    host = BASE.split("//")[1].split("/")[0]
    # WebKit names a link prefetch cut off by the test's own navigation
    # «… due to access control checks» (same origin) — not a page error (as s071).
    page.on("pageerror", lambda error: None if (str(error).rstrip().endswith("due to access control checks.") and host in str(error)) else errors.append(str(error)))
    touch = options.get("has_touch", False)

    def act(locator):
        (locator.tap if touch else locator.click)()
        page.wait_for_timeout(400)

    def continuous():
        return page.locator("[data-continuous-book]").count() > 0

    def open_panel():
        for _ in range(3):
            if page.locator(".reader-chrome[data-shown]").count():
                break
            pt = qa.reading_eval(page, EMPTY_POINT_JS)
            (page.touchscreen.tap if touch else page.mouse.click)(pt["x"], pt["y"])
            page.wait_for_timeout(500)
        act(page.locator("[data-reader-action=aa]"))
        page.wait_for_selector(".reader-panel")

    def pressed(mode):
        return page.locator(f"[data-reader-layout-btn={mode}]").get_attribute("aria-pressed") == "true"

    def close_panel():
        if page.locator(".reader-panel").count():
            act(page.locator(".reader-panel-close"))
            # The close is a "back": its place keeper runs for 600 ms.
            page.wait_for_timeout(700)

    def choose(mode):
        open_panel()
        act(page.locator(f"[data-reader-layout-btn={mode}]"))

    def settle():
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1800)

    def chapter_url():
        return page.url.split("#")[0].rstrip("/").endswith(f"/{LANG}/{CHAPTER}")

    def same_place(before, after):
        return bool(before and after and before["text"] == after["text"] and abs(before["delta"] - after["delta"]) <= TOL_PX)

    try:
        page.goto(f"{BASE}/{LANG}/{CHAPTER}/", wait_until="networkidle")
        page.wait_for_timeout(1200)
        # 1. Default: page by page («Листать»).
        check(device, "default: the chapter is its own page", not continuous() and chapter_url(), page.url)
        open_panel()
        has_row = page.locator("[data-reader-layout-btn]").count() == 2
        check(device, "«Аа» has «Листать» / «Прокручивать»", has_row)
        if not has_row:
            return
        check(device, "default: «Листать» pressed", pressed("page") and not pressed("scroll"))
        close_panel()

        # A place in the middle of the chapter.
        qa.scroll_chapter(page, 0.45)
        page.wait_for_timeout(700)
        place = qa.reading_eval(page, TOP_BLOCK_JS)
        check(device, "a place in the middle of the chapter", place and place["delta"] < 0 or page.locator(".app-main").evaluate("e => e.scrollTop") > 1000, place)

        # 2. «Прокручивать»: the whole book, the same words.
        choose("scroll")
        settle()
        here = qa.reading_eval(page, TOP_BLOCK_JS)
        check(device, "«Прокручивать»: the whole book in one scroll", continuous() and page.locator("[data-book-section]").count() > 20)
        check(device, "«Прокручивать»: the same chapter", chapter_url(), page.url)
        check(device, "«Прокручивать»: the same words at the top", same_place(place, here), f"{place} -> {here}")

        # 3. Reload keeps the mode and the place.
        page.reload(wait_until="networkidle")
        page.wait_for_selector("[data-continuous-book]", timeout=15000)
        page.wait_for_timeout(1800)
        again = qa.reading_eval(page, TOP_BLOCK_JS)
        check(device, "reload: still «Прокручивать»", continuous() and page.evaluate("localStorage.getItem('ap.readerLayout')") == "scroll")
        check(device, "reload: the same chapter and words", chapter_url() and same_place(place, again), f"{page.url} {place} -> {again}")
        open_panel()
        check(device, "reload: «Прокручивать» pressed", pressed("scroll") and not pressed("page"))
        close_panel()

        # 4. Continuous: scrolling past the chapter's end enters the next one.
        nxt = page.locator(f"[data-book-section='{CHAPTER}'] + [data-book-section]").first
        next_id = nxt.get_attribute("data-book-section")
        nxt.evaluate("e => e.scrollIntoView({block: 'start'})")
        page.locator(".app-main").evaluate("e => e.scrollBy(0, 120)")
        page.wait_for_timeout(1200)
        check(device, "scrolling enters the next chapter", page.url.split("#")[0].rstrip("/").endswith("/" + next_id), page.url)
        # Back to the place for the switch.
        place2 = qa.reading_eval(page, TOP_BLOCK_JS)

        # 5. «Листать» again: that chapter's page, the same words.
        choose("page")
        settle()
        back = qa.reading_eval(page, TOP_BLOCK_JS)
        check(device, "«Листать»: the chapter is its own page", not continuous() and page.url.split("#")[0].rstrip("/").endswith("/" + next_id), page.url)
        check(device, "«Листать»: the same words at the top", same_place(place2, back), f"{place2} -> {back}")

        # 6. Reload keeps «Листать».
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(1800)
        check(device, "reload: still «Листать»", not continuous() and page.evaluate("localStorage.getItem('ap.readerLayout')") == "page")
        open_panel()
        check(device, "reload: «Листать» pressed", pressed("page") and not pressed("scroll"))
        close_panel()
        check(device, "no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(device, "scenario ran", False, str(error)[:300])
    finally:
        context.close()


with sync_playwright() as playwright:
    for device, engine, options in qa.devices(["iphone14", "ipad-portrait", "pixel7", "desktop"]):
        browser = getattr(playwright, engine).launch()
        run(browser, device, options)
        browser.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
