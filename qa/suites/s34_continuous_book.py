"""Continuous cover-to-book reading, deep links, reloads and native history."""
import os
import sys
import traceback
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
CHAPTER = "arcana-procedure"
ANCHOR = "2-svagata"
results = []


def run(browser, device, options, theme):
    context = browser.new_context(service_workers="block", **options)
    context.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
    context.add_init_script("localStorage.setItem('ap.readerTheme', " + json.dumps(theme) + ")")
    page = context.new_page()
    errors = []
    external = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: external.append(request.url) if not request.url.startswith(BASE.split(qa.PREFIX)[0]) else None)
    try:
        page.goto(f"{BASE}/ru-iast/", wait_until="networkidle")
        page.evaluate("t => document.documentElement.setAttribute('data-reader-theme',t)", theme)
        main = page.locator(".app-main")
        def scroll(amount):
            if options.get("is_mobile") and device.startswith("iphone"):
                # Playwright cannot send wheel/drag gestures to mobile WebKit.
                main.evaluate("(e, n) => e.scrollBy(0, n)", amount)
            else:
                page.mouse.move(options["viewport"]["width"] / 2, 400)
                page.mouse.wheel(0, amount)
        length = page.evaluate("history.length")
        assert page.locator("[data-book-section]").count() > 20
        # Real wheel input crosses the cover, without opening any panel.
        scroll(options["viewport"]["height"] + 100)
        page.wait_for_timeout(1300)
        assert page.url.rstrip("/").endswith("/parampara")
        assert page.evaluate("history.length") == length
        assert not page.locator(".mobile-menu").count()
        assert main.evaluate("e => e.scrollTop") > 500
        # The reading indicator names the part and follows subsection
        # numbers even without a URL anchor. Scrolling adds no Back steps.
        for section, anchor, number in (
            ("daily-duties-brahma-muhurta", None, "1"),
            ("daily-duties-brahma-muhurta", "morning-prayers", "1.1"),
            ("daily-duties-brahma-muhurta", "taking-bath", "1.2"),
            ("daily-deity-schedule", None, "2"),
            ("worship-sixteen-articles", "asana-sthapana", "3.2"),
        ):
            target = page.locator(f"[id='{anchor}']" if anchor else f"[data-book-section='{section}']")
            target.evaluate("e => e.scrollIntoView({block: 'start'})")
            page.wait_for_timeout(300)
            status = page.locator(".reader-status")
            assert status.locator(".reader-location-group").text_content() == "Храмовый стандарт: "
            assert f"Глава {number} ·" in status.inner_text()
            assert status.evaluate("e => e.scrollWidth <= e.clientWidth")
            assert page.evaluate("history.length") == length
        # The same paraphernalia image occurs in two chapters. Selection
        # stays local to the tapped chapter, with a single floating copy.
        scopes = [page.locator(f"[data-book-section='{id}']") for id in ("worship-sixteen-articles", "main-worship-sixteen-items")]
        for index, scope in enumerate(scopes):
            row = scope.locator(".hs-row .hs-text[role=button]").first
            row.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            (row.tap if options.get("has_touch") else row.click)()
            page.wait_for_timeout(400)
            assert scope.locator(".hs-row[data-active]").count() == 1
            assert scopes[1 - index].locator(".hs-row[data-active]").count() == 0
            assert page.locator(".hs-peek").count() <= 1
            (row.tap if options.get("has_touch") else row.click)()
            assert not scope.locator(".hs-row[data-active]").count()

        # Existing URLs can be opened and reloaded directly. The full book
        # arrives at the same subsection without adding a history entry.
        target = f"{BASE}/ru-iast/{CHAPTER}/#{ANCHOR}"
        page.goto(target, wait_until="networkidle")
        page.wait_for_selector("[data-continuous-book]")
        page.wait_for_timeout(1400)
        assert page.url == target
        def aligned():
            return page.locator(f"[id='{ANCHOR}']").evaluate("e => Math.abs(e.getBoundingClientRect().top - document.querySelector('.app-main').getBoundingClientRect().top - (parseFloat(getComputedStyle(e).scrollMarginTop)||0)) < 4")
        assert aligned(), "deep-link heading alignment"
        assert "Храмовый стандарт: Глава 4.2" in page.locator(".reader-status").inner_text()
        length = page.evaluate("history.length")
        page.reload(wait_until="networkidle")
        page.wait_for_selector("[data-continuous-book]")
        page.wait_for_timeout(1400)
        assert page.url == target and page.evaluate("history.length") == length
        assert aligned(), "reload heading alignment"
        main.dispatch_event("wheel")
        main.evaluate("e => e.scrollBy(0, 500)")
        page.wait_for_timeout(500)
        saved = main.evaluate("e => e.scrollTop")
        page.reload(wait_until="networkidle")
        page.wait_for_selector("[data-continuous-book]")
        page.wait_for_timeout(1500)
        assert abs(main.evaluate("e => e.scrollTop") - saved) < 4, "reload after reading beyond anchor"

        # Stop the deep-link anchor keeper as a reader scroll gesture would,
        # then reach the end of this chapter before clicking its link.
        main.dispatch_event("wheel")
        # Chapter links and next-chapter controls use one native history
        # entry, with Back/Forward restoring the exact reading position.
        before_url = page.url
        before_scroll = main.evaluate("e => e.scrollTop")
        next_link = page.locator(f"[data-book-section='{CHAPTER}'] [data-chapter-next]").first
        next_link.scroll_into_view_if_needed()
        page.wait_for_timeout(1200)
        before_scroll = main.evaluate("e => e.scrollTop")
        before_url = page.url
        next_id = next_link.get_attribute("data-chapter-next")
        (next_link.tap if options.get("has_touch") else next_link.click)()
        page.wait_for_timeout(1200)
        assert page.url.rstrip("/").endswith("/" + next_id)
        section = page.locator(f"[data-book-section='{next_id}']")
        assert abs(section.bounding_box()["y"] - main.bounding_box()["y"]) < 4
        assert page.evaluate("history.length") == length + 1
        after_scroll = main.evaluate("e => e.scrollTop")
        page.go_back(wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        assert page.url == before_url
        assert abs(main.evaluate("e => e.scrollTop") - before_scroll) < 4
        page.go_forward(wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        assert abs(main.evaluate("e => e.scrollTop") - after_scroll) < 4

        # The complete book already rendered locally can continue scrolling
        # with networking disabled; no runtime service supplies its text.
        context.set_offline(True)
        scroll(options["viewport"]["height"])
        page.wait_for_timeout(500)
        assert main.evaluate("e => e.scrollTop") > after_scroll + 100
        assert not errors, errors
        assert not external, external
        results.append(True)
        print(f"  [PASS] {device}/{theme}: cover scroll, deep link, reload, next chapter, Back/Forward, offline", flush=True)
    except Exception as error:
        traceback.print_exc()
        results.append(False)
        print(f"  [FAIL] {device}/{theme}: {error}", flush=True)
    finally:
        context.close()


with sync_playwright() as playwright:
    for device, engine, options in qa.devices(["s23fe", "iphone14", "desktop", "mac-safari"]):
        browser = getattr(playwright, engine).launch()
        for theme in ("white", "sepia", "night"):
            run(browser, device, options, theme)
        browser.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
