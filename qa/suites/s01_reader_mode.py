"""Reader UI (Apple-Books-style reading mode) tests.
usage: python reader_test.py <base-url> [shots-dir]
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402  (device profiles, repo paths)
import os, sys, json
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/")
SHOTS = sys.argv[2] if len(sys.argv) > 2 else None
ONLY = None  # device filter: QA_DEVICES (qa/lib/qa.py)
LANGS = os.environ.get("LANGS", "ru-iast,en").split(",")

IOS_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
          "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
IPAD_UA = IOS_UA.replace("iPhone; CPU iPhone OS", "iPad; CPU OS")
PIXEL_UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Mobile Safari/537.36")
DEVICES = qa.devices(['iphone14', 'pixel7', 'ipad-portrait', 'ipad-landscape', 'ipad-mini', 'ipad-pro', 'desktop'])
PAGE = "daily-duties-brahma-muhurta"
QUERY = {"ru-iast": "тилака", "en": "tilaka"}

results = []
MATRIX = {}


def check(dev, name, ok, info=""):
    results.append((dev, name, bool(ok), info))
    MATRIX.setdefault(dev, [0, 0])[0 if ok else 1] += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {info if not ok else ''}")


JS_EMPTY_POINT = """() => {
  // A point on plain text (no interactive element) inside the viewport,
  // preferring true empty margin left of the reading column when wide enough.
  const main = document.querySelector('.app-main');
  const art = document.querySelector('.app-main article');
  const mr = main.getBoundingClientRect();
  const ar = art.getBoundingClientRect();
  const H = window.innerHeight;
  const bad = (el) => !el || !!el.closest('a,button,input,select,label,[role=button],img,svg,.hs-text,.hs-figure,.verse-chips,.mood-toggle,[data-no-reader-tap]');
  if (ar.left - mr.left > 80) {
    const p = {x: mr.left + 40, y: H / 2};
    const el = document.elementFromPoint(p.x, p.y);
    if (!bad(el) && main.contains(el)) return {...p, kind: 'margin'};
  }
  for (const p of art.querySelectorAll('p')) {
    if (p.closest('[data-hs-row]') || p.querySelector('a,button,.hs-text')) continue;
    const r = p.getClientRects()[0];
    if (!r || r.top < 90 || r.bottom > H - 160 || r.width < 120) continue;
    const pt = {x: r.left + Math.min(60, r.width / 3), y: r.top + r.height / 2};
    const el = document.elementFromPoint(pt.x, pt.y);
    if (!bad(el)) return {...pt, kind: 'text'};
  }
  // gap between paragraphs: left padding of the article
  const pt = {x: ar.left + 6, y: H / 2};
  return {...pt, kind: 'pad'};
}"""


def run(p, dev, engine, opts, lang):
    br = getattr(p, engine).launch()
    ctx = br.new_context(service_workers="block", **opts)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
    pg.on("console", lambda m: errs.append("console: " + m.text) if m.type == "error" else None)
    touch = opts.get("has_touch", False)
    prefix = "" if lang == "en" else f"/{lang}"
    url = f"{BASE}{prefix}/{PAGE}/"
    tag = f"{dev}-{lang}"

    def tap_pt(pt):
        if touch:
            pg.touchscreen.tap(pt["x"], pt["y"])
        else:
            pg.mouse.click(pt["x"], pt["y"])
        pg.wait_for_timeout(450)

    def act(loc):
        loc.tap() if touch else loc.click()
        pg.wait_for_timeout(450)

    def shown():
        return pg.locator(".reader-chrome[data-shown]").count() == 1

    def bars_visible():
        return pg.evaluate("""() => [...document.querySelectorAll('.reader-bar')].map(b => +getComputedStyle(b).opacity)""")

    def empty_point():
        return pg.evaluate(JS_EMPTY_POINT)

    def show_bars():
        if not shown():
            tap_pt(empty_point())

    def shot(name):
        if SHOTS:
            os.makedirs(SHOTS, exist_ok=True)
            pg.screenshot(path=os.path.join(SHOTS, f"{dev}-{lang}-{name}.png"))

    pg.goto(url, wait_until="networkidle")
    pg.wait_for_timeout(1100)
    # 0. one-time hint on the first chapter visit, never blocks taps
    check(tag, "hint shown once on first visit", pg.locator(".reader-hint").count() == 1)
    # 1. reading mode: no bars, faint status line
    op = bars_visible()
    status = pg.locator(".reader-status").inner_text() if pg.locator(".reader-status").count() else ""
    check(tag, "reading mode: no bars", not shown() and all(o < 0.05 for o in op), f"opacity={op}")
    check(tag, "faint status line «глава · %»", "%" in status and status.strip() != "", status)
    shot("1-reading")
    # 2. tap empty -> bars; again -> hidden
    pt = empty_point()
    tap_pt(pt)
    check(tag, f"tap empty ({pt['kind']}) -> bars visible", shown() and all(o > 0.95 for o in bars_visible()), f"{pt} {bars_visible()}")
    check(tag, "hint gone after tap", pg.locator(".reader-hint").count() == 0)
    shot("2-menu")
    tap_pt(empty_point())
    pg.wait_for_timeout(250)
    check(tag, "tap again -> bars hidden", not shown())
    # 3. list row <-> picture: no bars
    row_num = pg.locator("[data-hs-row] .hs-text[role=button]").first
    row_num.scroll_into_view_if_needed()
    pg.evaluate("document.querySelector('.app-main').scrollBy(0, -120)")
    pg.wait_for_timeout(1000)  # past the scroll quiet period
    if shown():
        tap_pt(empty_point()); pg.wait_for_timeout(200)
    b = row_num.bounding_box()
    tap_pt({"x": b["x"] + b["width"] / 2, "y": b["y"] + b["height"] / 2})
    hl = pg.locator("[data-hs-row][data-active]").count() == 1
    check(tag, "tap list row -> highlight, no bars", hl and not shown(), f"hl={hl} shown={shown()}")
    # 4. tap empty with highlight -> only clears
    pt = empty_point()
    tap_pt(pt)
    cleared = pg.locator("[data-hs-row][data-active]").count() == 0
    check(tag, "tap empty after highlight -> cleared, no bars", cleared and not shown(), f"cleared={cleared} shown={shown()} {pt}")
    # 5. next tap -> bars
    tap_pt(empty_point())
    check(tag, "next tap -> bars", shown())
    # 5b. picture tap does not toggle
    fig = pg.locator(".hs-figure").first
    if fig.count():
        tap_pt(empty_point())  # hide
        fig.scroll_into_view_if_needed(); pg.wait_for_timeout(900)
        fb = fig.bounding_box()
        before = shown()
        tap_pt({"x": fb["x"] + 4, "y": fb["y"] + fb["height"] - 6})
        # v7.1 (verifier item 19): the empty area of a numbered picture is page -> toggles
        check(tag, "tap on the empty area of a numbered picture -> menu toggles (v7.1)", shown() != before)
        if pg.locator("[data-hs-row][data-active]").count():
            tap_pt(empty_point())
    # 6. auto-hide after ~4 s
    pg.evaluate("document.querySelector('.app-main').scrollTop = 0"); pg.wait_for_timeout(1000)
    show_bars()
    seq = []
    for _ in range(12):
        seq.append(int(shown())); pg.wait_for_timeout(500)
    dbg = pg.evaluate("[document.querySelector('.app-main').scrollTop, document.querySelectorAll('[data-hs-row][data-active]').length, !!document.querySelector('.hs-peek'), document.activeElement && document.activeElement.className && String(document.activeElement.className.baseVal ?? document.activeElement.className)]")
    check(tag, "auto-hide after ~4 s", not shown(), str(dbg) + str(seq))
    # 7. small scroll up shows bars; scroll down hides
    m = "document.querySelector('.app-main')"
    pg.evaluate(f"{m}.scrollTop = 900"); pg.wait_for_timeout(1000)
    if touch:
        # v7.1 (item 13): only the reader's own scrolling shows the bars -> a finger on the page (touchmove) first
        pg.evaluate(f"{m}.dispatchEvent(new Event('touchmove'))"); pg.evaluate(f"{m}.scrollBy(0, -30)"); pg.wait_for_timeout(60); pg.evaluate(f"{m}.dispatchEvent(new Event('touchmove'))"); pg.evaluate(f"{m}.scrollBy(0, -40)")
    else:
        pg.mouse.move(700, 450); pg.mouse.wheel(0, -80)
    pg.wait_for_timeout(400)
    check(tag, "small scroll up -> bars", shown())
    if touch:
        pg.evaluate(f"{m}.dispatchEvent(new Event('touchmove'))"); pg.evaluate(f"{m}.scrollBy(0, 60)")
    else:
        pg.mouse.wheel(0, 120)
    pg.wait_for_timeout(400)
    check(tag, "scroll down -> bars hidden", not shown())
    # 8. end of chapter -> bars with next chapter
    pg.evaluate(f"{m}.scrollTop = {m}.scrollHeight - {m}.clientHeight - 300"); pg.wait_for_timeout(1000)
    pg.evaluate(f"{m}.dispatchEvent(new Event('touchmove'))"); pg.evaluate(f"{m}.scrollBy(0, 400)"); pg.wait_for_timeout(500)
    check(tag, "end of chapter -> bars", shown() and pg.locator("[data-reader-nav=back]").count() == 1)
    # 9. Esc hides (keyboard)
    if not touch:
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        check(tag, "Esc hides bars", not shown())
    # 10. v5: «‹ Назад» / «Вперёд ›» = history steps (no slider, no prev/next chapter)
    pg.goto(url, wait_until="networkidle"); pg.wait_for_timeout(800)
    other = BASE + prefix + "/arcana-procedure/"
    pg.goto(other, wait_until="networkidle"); pg.wait_for_timeout(1000)
    show_bars()
    check(tag, "no progress slider", pg.locator(".reader-slider, input[type=range]").count() == 0)
    act(pg.locator("[data-reader-nav=back]"))
    pg.wait_for_timeout(1200)
    check(tag, "«Назад» button = history back", pg.url == url, pg.url)
    check(tag, "page after back starts in reading mode", not shown())
    show_bars()
    act(pg.locator("[data-reader-nav=forward]"))
    pg.wait_for_timeout(1200)
    check(tag, "«Вперёд» button = history forward", pg.url == other, pg.url)
    pg.goto(url, wait_until="networkidle"); pg.wait_for_timeout(800)
    # 11. contents opens and navigates
    show_bars()
    act(pg.locator("[data-reader-action=contents]"))
    menu = pg.locator(".mobile-menu").count() == 1
    check(tag, "contents opens", menu)
    shot("3-contents")
    link = pg.locator(".mobile-menu nav a[href$='/temple-worship/']:visible").first
    if link.count() == 0:
        # part closed: open its group
        link = pg.locator(".mobile-menu nav a:visible").nth(3)
    href = link.get_attribute("href")
    act(link); pg.wait_for_timeout(500)
    check(tag, "contents: first tap only highlights (no navigation)", pg.locator(".mobile-menu").count() == 1 and pg.url == url, pg.url)
    act(link); pg.wait_for_timeout(1200)
    check(tag, "contents link navigates, menu closed", pg.url.endswith(href.replace("/arcana-paddhati", "", 1)) and pg.locator(".mobile-menu").count() == 0, f"{pg.url} {href}")
    # 12. search + back returns to search with query
    pg.goto(url, wait_until="networkidle"); pg.wait_for_timeout(1000)
    show_bars()
    act(pg.locator("[data-reader-action=search]"))
    inp = pg.locator(".mobile-menu input[type=search]")
    focused = pg.evaluate("document.activeElement && document.activeElement.type === 'search'")
    check(tag, "search opens with focused box", inp.count() == 1 and focused, f"focused={focused}")
    inp.fill(QUERY[lang])
    try:
        pg.locator(".mobile-menu nav a:visible mark").first.wait_for(timeout=15000)
    except Exception:
        pass
    inp.press("Enter"); pg.wait_for_timeout(300)
    n = pg.locator(".mobile-menu nav a:visible").count()
    check(tag, "search shows results", n > 0, f"n={n}")
    act(pg.locator(".mobile-menu nav a:visible").first); pg.wait_for_timeout(1500)
    went = pg.url
    pg.go_back(); pg.wait_for_timeout(1500)
    q = inp.input_value() if inp.count() else None
    check(tag, "back (Android) returns to search with query", pg.locator(".mobile-menu").count() == 1 and q == QUERY[lang], f"went={went} q={q} url={pg.url}")
    pg.go_back(); pg.wait_for_timeout(900)
    check(tag, "second back closes search, stays on page", pg.locator(".mobile-menu").count() == 0 and pg.url == url, pg.url)
    # 13. Аа: size + night persist after reload
    show_bars()
    act(pg.locator("[data-reader-action=aa]"))
    check(tag, "Аа panel opens", pg.locator(".reader-panel").count() == 1)
    act(pg.locator("[data-reader-size='+']"))
    act(pg.locator("[data-reader-size='+']"))
    act(pg.locator("[data-reader-theme-btn=night]"))
    shot("4-aa-night")
    th = pg.evaluate("document.documentElement.getAttribute('data-reader-theme')")
    z = pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--reader-zoom').trim()")
    check(tag, "night + size applied", th == "night" and z == "1.22", f"th={th} z={z}")
    still = shown()
    check(tag, "bars stay while panel open (>4 s)", (pg.wait_for_timeout(4500) or True) and shown() and still)
    pg.keyboard.press("Escape") if not touch else act(pg.locator(".reader-panel-close"))
    pg.wait_for_timeout(400)
    check(tag, "panel closes (✕/Esc), history entry popped", pg.locator(".reader-panel").count() == 0 and pg.url == url
          and not pg.evaluate("!!(history.state && history.state.apAa)"))
    pg.reload(wait_until="networkidle"); pg.wait_for_timeout(800)
    th = pg.evaluate("document.documentElement.getAttribute('data-reader-theme')")
    z = pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--reader-zoom').trim()")
    bg = pg.evaluate("getComputedStyle(document.querySelector('.app-main')).backgroundColor")
    check(tag, "night + size persist after reload", th == "night" and z == "1.22" and bg == "rgb(22, 19, 15)", f"th={th} z={z} bg={bg}")
    shot("5-night-reading")
    # Аа back button closes panel (phone back)
    show_bars()
    act(pg.locator("[data-reader-action=aa]"))
    pg.go_back(); pg.wait_for_timeout(700)
    check(tag, "back closes Аа panel, page stays", pg.locator(".reader-panel").count() == 0 and pg.url == url, pg.url)
    # reset to white
    show_bars()
    act(pg.locator("[data-reader-action=aa]"))
    act(pg.locator("[data-reader-theme-btn=white]"))
    check(tag, "white theme restores", pg.evaluate("document.documentElement.getAttribute('data-reader-theme')") is None)
    # 14. language switch from Аа keeps the chapter
    sel = pg.locator(".reader-panel select")
    other = "en" if lang != "en" else "ru-iast"
    sel.select_option(other); pg.wait_for_timeout(1500)
    exp = f"{BASE}{'' if other == 'en' else '/' + other}/{PAGE}/"
    check(tag, "language switch in Аа keeps chapter, closes panel", pg.url == exp and pg.locator(".reader-panel").count() == 0, pg.url)
    pg.go_back(); pg.wait_for_timeout(1200)
    # v3 (step-by-step Back): the step before was the Аа panel on the previous-language page
    check(tag, "back after language switch -> previous language page, Аа open", pg.url == url and pg.locator(".reader-panel").count() == 1, pg.url)
    pg.go_back(); pg.wait_for_timeout(700)
    check(tag, "back again -> Аа closed, same page", pg.url == url and pg.locator(".reader-panel").count() == 0, pg.url)
    # 15. mood block opens, no toggle
    pg.goto(f"{BASE}{prefix}/arcana-procedure/", wait_until="networkidle"); pg.wait_for_timeout(900)
    tog = pg.locator(".mood-toggle").first
    if tog.count():
        tog.scroll_into_view_if_needed(); pg.wait_for_timeout(900)
        before = shown()
        act(tog)
        opened = pg.locator(".mood-overlay").count() == 1
        pg.keyboard.press("Escape") if not touch else act(pg.locator(".mood-close"))
        pg.wait_for_timeout(500)
        check(tag, "«Настроение Гурудева» opens, menu not toggled", opened and shown() == before)
    # 16. verse chip: no toggle
    chip = pg.locator(".verse-chip").first
    if chip.count():
        chip.scroll_into_view_if_needed(); pg.wait_for_timeout(900)
        before = shown()
        act(chip)
        check(tag, "verse chip toggles panel only", shown() == before and chip.get_attribute("aria-expanded") == "true")
    # 17. text selection: a tap that ends a selection does not toggle
    pg.goto(url, wait_until="networkidle"); pg.wait_for_timeout(1000)
    pt = empty_point()
    pg.evaluate("""() => { const p = [...document.querySelectorAll('.app-main article p')].find(p => p.textContent.length > 40);
        const r = document.createRange(); r.selectNodeContents(p); const s = getSelection(); s.removeAllRanges(); s.addRange(r); }""")
    tap_pt(pt)
    check(tag, "tap ending a text selection -> no toggle", not shown())
    # home page: reading mode, next = first chapter
    pg.goto(f"{BASE}{prefix}/", wait_until="networkidle"); pg.wait_for_timeout(900)
    check(tag, "cover: no bars", not shown())
    # 18. no console errors
    check(tag, "no console / page errors", not errs, "; ".join(errs[:4]))
    br.close()


with sync_playwright() as p:
    for dev, engine, opts in DEVICES:
        if ONLY and dev not in ONLY.split(","):
            continue
        for lang in LANGS:
            print(dev, lang)
            try:
                run(p, dev, engine, opts, lang)
            except Exception as e:
                check(f"{dev}-{lang}", "EXCEPTION", False, str(e)[:1200])

fails = [r for r in results if not r[2]]
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
for f in fails:
    print("FAILED:", f[0], f[1], f[3][:300])
print("MATRIX (pass/fail):")
for k, (a, b) in MATRIX.items():
    print(f"  {k:22s} {a:3d} / {b}")
