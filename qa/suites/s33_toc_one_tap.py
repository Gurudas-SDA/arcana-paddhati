"""Contents rules 9.2, 9.3, 10.1 and 10.2: place, actions, cover and search.

Seven variants retain all themes and historical query flags; every row now
performs its function on one tap (the two-tap mode was removed on 13.10).
Usage: python s33_toc_one_tap.py <base-url>   devices: QA_DEVICES
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from toc import marks_chapter_top, marks_place  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
CHAPTER = "arcana-procedure"
SUBSECTION = "2-svagata"
GROUP = "temple-worship"
STATE = """() => {
  const nav = document.querySelector('.mobile-menu[data-open] nav');
  return {
    url: location.pathname + location.hash,
    menu: !!nav,
    lit: nav ? [...nav.querySelectorAll('[data-toc-lit]')]
      .map(e => e.dataset.tocRow || e.dataset.result) : [],
    open: nav ? [...nav.querySelectorAll('[aria-expanded=true][data-toc-group], [aria-expanded=true][data-toc-toggle], [aria-expanded=true][data-toc-chapter]')]
      .map(e => e.dataset.tocGroup || e.dataset.tocToggle || e.dataset.tocChapter).sort() : [],
    length: history.length,
    scroll: (() => {
      const main = document.querySelector('.app-main');
      const id = location.pathname.split('/').filter(Boolean).at(-1);
      const section = document.querySelector(`[data-book-section="${id}"]`);
      return section ? main.getBoundingClientRect().top - section.getBoundingClientRect().top : main.scrollTop;
    })(),
  };
}"""
results = []


def run(browser, device, options, mode, theme):
    context = browser.new_context(service_workers="block", **options)
    context.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    url = f"{BASE}/ru-iast/" + (f"?toc={mode}" if mode != "default" else "")
    page.goto(url, wait_until="networkidle")
    page.evaluate("t => document.documentElement.setAttribute('data-reader-theme', t)", theme)
    touch = options.get("has_touch", False)
    state = lambda: page.evaluate(STATE)

    def tap(locator, right=False, wait=350):
        chapter_id = locator.get_attribute("data-toc-chapter")
        if right and chapter_id:
            toggle = page.locator(f"[data-toc-toggle='{chapter_id}']")
            if toggle.count():
                # The approved mode already has a chevron button on this
                # edge. Tap its actual hit box; the proposal has one button.
                locator = toggle
        locator.scroll_into_view_if_needed()
        box = locator.bounding_box()
        position = {"x": box["width"] - 9 if right else 5, "y": box["height"] / 2}
        (locator.tap if touch else locator.click)(position=position)
        page.wait_for_timeout(wait)

    def bars():
        # Search highlighting clears on its own tap before bars can appear.
        for _ in range(3):
            if state()["menu"] or page.locator(".reader-chrome[data-shown]").count():
                return
            (page.touchscreen.tap if touch else page.mouse.click)(options["viewport"]["width"] - 6, 400)
            page.wait_for_timeout(250)

    def contents():
        bars()
        tap(page.locator("[data-reader-action=contents]"))

    def back():
        # V17 (Vraja Lila msg 796): the app's «‹ Назад» is the previous chapter; a history step is the system Back
        page.go_back(); page.wait_for_timeout(700)

    group = lambda: page.locator(f"[data-toc-toggle='{GROUP}']")  # V37: the group expands by its arrow
    chapter = lambda: page.locator(f"[data-toc-chapter='{CHAPTER}']")
    subsection = lambda: page.locator(f"[data-toc-row='sub:{CHAPTER}#{SUBSECTION}']")
    close = lambda: page.locator(".mobile-menu[data-open] button[aria-label='Закрыть меню']")
    try:
        contents()
        for locator in (group, chapter):
            step_before = state()
            tap(locator(), wait=700)
            assert marks_place(state())
            assert locator().get_attribute("aria-expanded") == "true"
            assert state()["length"] == step_before["length"] + 1
        assert state()["url"].endswith(f"/{CHAPTER}/") and state()["scroll"] < 2
        assert chapter().locator("..").locator("button").count() == 1
        before_subsection = state()
        tap(subsection(), wait=800)
        assert state()["length"] == before_subsection["length"] + 1
        assert state()["url"].endswith(f"/{CHAPTER}/#{SUBSECTION}") and not state()["menu"]
        back()
        assert marks_chapter_top(page, state(), CHAPTER)
        assert CHAPTER in state()["open"]
        count = 1
        while state()["menu"]:
            back()
            count += 1
            assert count <= 7
        # Rule 9.3: cover → 4.2 is four steps, independently of the observed count.
        assert count == 4
        assert state()["url"].rstrip("/").endswith("/ru-iast")

        contents()
        for locator in (group, chapter):
            tap(locator(), wait=700)
        opened = state()
        tap(chapter(), right=True)
        assert CHAPTER not in state()["open"]
        assert state()["url"] == opened["url"] and state()["length"] == opened["length"] + 1
        back()
        assert state()["open"] == opened["open"]
        tap(close())
        assert not state()["menu"] and state()["url"] == opened["url"] and state()["scroll"] < 2
        contents()
        tap(page.locator("[data-toc-cover]"), right=True, wait=800)
        assert not state()["menu"] and not state()["open"] and state()["lit"] == []
        assert not state()["menu"] and state()["url"].rstrip("/").endswith("/ru-iast")

        contents()
        field = page.locator(".mobile-menu[data-open] input[type=search]")
        field.fill("Свагата")
        result = page.locator(f"[data-result='{CHAPTER}#{SUBSECTION}']")
        result.wait_for(state="visible")
        before = state()
        tap(result, right=True, wait=800)
        assert not state()["menu"] and state()["length"] == before["length"] + 1
        back()
        assert state()["menu"] and field.input_value() == "Свагата"
        # Rule 9.2: Back returns to the cover's search, not to the clicked
        # chapter. None of these result rows stands for that reading place.
        assert state()["url"] == before["url"] and state()["lit"] == [], state()
        assert not errors, errors
        results.append(True)
        print(f"  [PASS] {device} {mode}/{theme}: chapter, Back, collapse, cover, search and full-width taps", flush=True)
    except Exception as error:
        traceback.print_exc()
        results.append(False)
        print(f"  [FAIL] {device} {mode}/{theme}: {error}", flush=True)
    finally:
        context.close()


with sync_playwright() as playwright:
    for device, engine, options in qa.devices(["s23fe", "iphone14", "pixel7", "desktop", "mac-safari"]):
        browser = getattr(playwright, engine).launch()
        for theme in ("white", "sepia", "night"):
            for mode in ("two", "one"):
                run(browser, device, options, mode, theme)
        run(browser, device, options, "default", "white")
        browser.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
