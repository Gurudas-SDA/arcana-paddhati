"""Language menu in the book's style (Vraja Lila msg 5418, 20.10.2026: «1 — сделай его», variant 1).

Task text (verbatim, mockup «Меню языка в стиле книги — вариант 1»): closed field «🌐 Русский ⌄» like the other
«Аа» panel buttons; a tap opens a card above the field with all 11 languages (rows ≥ 44 px, thin dividers),
the current one on a cream base with a gold ✓; it closes on a tap outside the list or on choosing a language.
Language switching itself (URL, liveLang, history) does not change.
Vraja msg 5423 (verbatim): «можно так же затемнить всё на фоне, под выборкой языка, как на варианте 2».
Checks: no native <select>; dimmed page behind the open list; ARIA listbox/option; opens; rows ≥ 44 px; current = aria-selected + ✓;
choosing a language changes the URL and keeps the chapter; Esc and a tap outside close it, focus back on the field;
arrow keys + Enter choose; small landscape screen — the list scrolls inside the viewport; Тёмный — readable colours.
# tehniskais slieksnis Lipikāra, nav S noteikums: contrast ≥ 4.5 (WCAG AA) for option text in Тёмный / Бежевый.
usage: python s56_lang_menu.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from toc import Contents  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
# small horizontal phone (iPhone SE landscape)
DEVICES.append(("phone-landscape", "webkit", dict(viewport={"width": 667, "height": 375}, has_touch=True, is_mobile=True,
                                                    device_scale_factor=2, user_agent=qa.IOS_UA)))
PAGE = "arcana-procedure"
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:400]}", flush=True)


CONTRAST = """() => {
  const lum = c => { const m = c.match(/[\\d.]+/g).map(Number); const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(m[0]) + 0.7152 * f(m[1]) + 0.0722 * f(m[2]); };
  const bg = el => { for (let e = el; e; e = e.parentElement) { const c = getComputedStyle(e).backgroundColor; const a = (c.match(/[\\d.]+/g) || []).map(Number);
    if (a.length >= 3 && (a.length < 4 || a[3] > 0.5)) return c; } return 'rgb(255,255,255)'; };
  const out = [];
  for (const o of document.querySelectorAll('[role=listbox] [role=option]')) {
    const a = lum(getComputedStyle(o).color), b = lum(bg(o));
    out.push(Math.round(((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)) * 100) / 100);
  }
  return out; }"""


def open_panel(pg, flow, touch):
    flow.bars()
    aa = pg.locator("[data-reader-action=aa]")
    (aa.tap if touch else aa.click)()
    pg.wait_for_timeout(500)


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        touch = opts.get("has_touch", False)
        b = getattr(p, eng).launch()
        c = b.new_context(service_workers="block", locale="ru-RU", **opts)
        c.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
        pg = c.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        url = f"{BASE}/ru-iast/{PAGE}/"
        pg.goto(url, wait_until="networkidle")
        pg.wait_for_timeout(800)
        flow = Contents(pg, qa.TocMode("default"), touch)
        open_panel(pg, flow, touch)
        st = pg.evaluate("""() => { const p = document.querySelector('.reader-panel'); if (!p) return null;
          const t = p.querySelector('[data-lang-trigger]');
          return {select: p.querySelectorAll('select').length, trigger: !!t,
                  haspopup: t && t.getAttribute('aria-haspopup'), expanded: t && t.getAttribute('aria-expanded'),
                  text: t && t.innerText.trim(), h: t && t.getBoundingClientRect().height}; }""")
        check(dev, "closed: a book-style field, no native <select>", st and st["select"] == 0 and st["trigger"], st)
        check(dev, "closed: field «Русский», aria-haspopup=listbox, aria-expanded=false, ≥ 44 px",
              st and st["text"] == "Русский" and st["haspopup"] == "listbox" and st["expanded"] == "false" and st["h"] >= 44, st)
        if not (st and st["trigger"]):
            c.close(); b.close(); continue
        trig = pg.locator(".reader-panel [data-lang-trigger]")
        (trig.tap if touch else trig.click)()
        pg.wait_for_timeout(400)
        lb = pg.evaluate("""() => { const l = document.querySelector('[role=listbox]'); if (!l) return null;
          const r = l.getBoundingClientRect(); const os = [...l.querySelectorAll('[role=option]')];
          const cur = os.find(o => o.getAttribute('aria-selected') === 'true');
          return {n: os.length, minH: Math.min(...os.map(o => o.getBoundingClientRect().height)),
                  names: os.map(o => o.innerText.trim()), cur: cur && cur.getAttribute('data-lang'), check: cur && !!cur.querySelector('[data-lang-check]'),
                  top: r.top, bottom: r.bottom, vh: innerHeight, scrollable: l.scrollHeight > l.clientHeight + 1,
                  overflow: getComputedStyle(l).overflowY,
                  expanded: document.querySelector('[data-lang-trigger]').getAttribute('aria-expanded'),
                  focusIn: l.contains(document.activeElement) || document.activeElement === l}; }""")
        check(dev, "open: listbox with 11 languages, rows ≥ 44 px", lb and lb["n"] == 11 and lb["minH"] >= 44, lb)
        check(dev, "open: current = ru-iast, aria-selected, gold ✓", lb and lb["cur"] == "ru-iast" and lb["check"], lb)
        check(dev, "open: aria-expanded=true, keyboard focus in the list", lb and lb["expanded"] == "true" and lb["focusIn"], lb)
        check(dev, "open: card inside the screen (scrolls if it does not fit)",
              lb and lb["top"] >= 0 and lb["bottom"] <= lb["vh"] + 0.5 and (not lb["scrollable"] or lb["overflow"] in ("auto", "scroll")), lb)
        dim = pg.evaluate("""() => { const d = document.querySelector('[data-lang-backdrop]'); if (!d) return null;
          const r = d.getBoundingClientRect(); const a = (getComputedStyle(d).backgroundColor.match(/[\\d.]+/g) || []).map(Number);
          return {cover: r.width >= innerWidth - 1 && r.height >= innerHeight - 1, alpha: a.length === 4 ? a[3] : (a.length ? 1 : 0)}; }""")
        check(dev, "open: the page behind is dimmed (Vraja msg 5423, like variant 2)", dim and dim["cover"] and 0.2 <= dim["alpha"] <= 0.7, dim)
        if dev == "phone-landscape":
            check(dev, "small landscape: the list scrolls", lb and lb["scrollable"], lb)
        # Esc closes the list (not the panel), focus back on the field
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        e = pg.evaluate("""() => ({list: !!document.querySelector('[role=listbox]'), panel: !!document.querySelector('.reader-panel'),
          focus: !!(document.activeElement && document.activeElement.matches('[data-lang-trigger]'))})""")
        check(dev, "Esc closes the list, panel stays, focus on the field", e == {"list": False, "panel": True, "focus": True}, e)
        # tap outside closes it
        (trig.tap if touch else trig.click)(); pg.wait_for_timeout(400)
        vw = pg.viewport_size
        (pg.touchscreen.tap if touch else pg.mouse.click)(6, vw["height"] - 6); pg.wait_for_timeout(400)
        o = pg.evaluate("""() => ({list: !!document.querySelector('[role=listbox]'), url: location.pathname})""")
        check(dev, "tap on the dimmed page outside the list closes it, language unchanged", not o["list"] and o["url"].endswith(f"/ru-iast/{PAGE}/"), o)
        # Тёмный: colours readable
        if pg.locator(".reader-panel").count() == 0:
            open_panel(pg, flow, touch)
        nb = pg.locator("[data-reader-theme-btn=night]")
        (nb.tap if touch else nb.click)(); pg.wait_for_timeout(300)
        trig = pg.locator(".reader-panel [data-lang-trigger]")
        (trig.tap if touch else trig.click)(); pg.wait_for_timeout(400)
        cr = pg.evaluate(CONTRAST)
        check(dev, "Тёмный: option text contrast ≥ 4.5", cr and min(cr) >= 4.5, cr)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
        sb = pg.locator("[data-reader-theme-btn=sepia]")
        (sb.tap if touch else sb.click)(); pg.wait_for_timeout(300)
        (trig.tap if touch else trig.click)(); pg.wait_for_timeout(400)
        cr = pg.evaluate(CONTRAST)
        check(dev, "Бежевый: option text contrast ≥ 4.5", cr and min(cr) >= 4.5, cr)
        # choose English: URL changes, chapter kept, panel closed
        if dev == "desktop":
            # keyboard: Home → English (first), Enter
            pg.keyboard.press("Home"); pg.keyboard.press("Enter")
        else:
            en = pg.locator("[role=listbox] [role=option][data-lang=en]")
            en.scroll_into_view_if_needed()
            (en.tap if touch else en.click)()
        pg.wait_for_timeout(1500)
        r = pg.evaluate("""() => ({url: location.pathname, list: !!document.querySelector('[role=listbox]'),
          panel: !!document.querySelector('.reader-panel'), saved: localStorage.getItem('arcanaLang')})""")
        check(dev, "choosing English changes the language, keeps the chapter, closes list + panel",
              r["url"].endswith(f"/{PAGE}/") and "/ru-iast/" not in r["url"] and not r["list"] and not r["panel"] and r["saved"] == "en", r)
        pg.go_back(); pg.wait_for_timeout(1200)
        check(dev, "Back returns to the Russian page with «Аа» open (unchanged behaviour)",
              pg.url == url and pg.locator(".reader-panel").count() == 1, pg.url)
        # reset theme
        wb = pg.locator("[data-reader-theme-btn=white]")
        if wb.count():
            (wb.tap if touch else wb.click)()
        check(dev, "no page errors", not errs, errs[:3])
        c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
