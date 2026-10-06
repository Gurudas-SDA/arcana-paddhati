"""One Russian only (Satkirti 05.10.2026): ru (Cyrillic Sanskrit) retired -> ru-iast.
usage: python ru_test.py <base-url>"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402  (device profiles, repo paths)
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/")
IOS_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
          "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
DEVICES = qa.devices(['iphone14', 'pixel7', 'desktop'])
results = []


def check(dev, name, ok, info=""):
    results.append((dev, name, bool(ok), info))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else info}")


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        br = getattr(p, eng).launch()
        ctx = br.new_context(service_workers="block", **opts)
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        touch = opts.get("has_touch", False)
        # 1. old /ru/ URL (with anchor) -> same place in ru-iast, no 404
        resp = pg.goto(f"{BASE}/ru/offering-bhoga/#x", wait_until="networkidle")
        pg.wait_for_timeout(800)
        check(dev, "old /ru/<chapter>/ -> /ru-iast/<chapter>/ (hash kept)",
              pg.url == f"{BASE}/ru-iast/offering-bhoga/#x" and pg.locator("article h1").count() == 1, pg.url)
        pg.goto(f"{BASE}/ru/", wait_until="networkidle"); pg.wait_for_timeout(600)
        check(dev, "old /ru/ home -> /ru-iast/", pg.url == f"{BASE}/ru-iast/", pg.url)
        # 2. saved Cyrillic Russian is migrated
        pg.evaluate("localStorage.setItem('arcanaLang', 'ru')")
        pg.goto(f"{BASE}/", wait_until="networkidle"); pg.wait_for_timeout(1200)
        saved = pg.evaluate("localStorage.getItem('arcanaLang')")
        check(dev, "saved 'ru' migrated to 'ru-iast', start page opens it",
              saved == "ru-iast" and pg.url == f"{BASE}/ru-iast/", f"saved={saved} url={pg.url}")
        # 3. switcher: one Russian, label «Русский», value ru-iast
        pg.goto(f"{BASE}/ru-iast/offering-bhoga/", wait_until="networkidle"); pg.wait_for_timeout(800)
        b = pg.evaluate("""() => { const a = document.querySelector('.app-main article').getBoundingClientRect(); return {x: a.left + 6, y: innerHeight / 2}; }""")
        (pg.touchscreen.tap if touch else pg.mouse.click)(b["x"], b["y"]); pg.wait_for_timeout(400)
        c = pg.locator("[data-reader-action=contents]")
        c.tap() if touch else c.click()
        pg.wait_for_timeout(500)
        opts_ = pg.locator(".mobile-menu select option").evaluate_all("os => os.map(o => [o.value, o.textContent.trim()])")
        rus = [o for o in opts_ if o[0].startswith("ru")]
        check(dev, "contents-panel language menu: one Russian «Русский» = ru-iast", rus == [["ru-iast", "Русский"]], str(opts_))
        pg.go_back(); pg.wait_for_timeout(500)
        # open the Аа panel too
        if pg.locator(".reader-chrome[data-shown]").count() == 0:
            (pg.touchscreen.tap if touch else pg.mouse.click)(b["x"], b["y"]); pg.wait_for_timeout(400)
        aa = pg.locator("[data-reader-action=aa]")
        aa.tap() if touch else aa.click()
        pg.wait_for_timeout(400)
        vals = pg.locator(".reader-panel select option").evaluate_all("os => os.map(o => [o.value, o.textContent.trim()])")
        check(dev, "Аа language menu: one Russian «Русский»", [v for v in vals if v[0].startswith("ru")] == [["ru-iast", "Русский"]], str(vals))
        # 4. Russian search uses the IAST index
        reqs = []
        pg.on("request", lambda r: reqs.append(r.url) if "search-index" in r.url else None)
        pg.goto(f"{BASE}/ru-iast/offering-bhoga/", wait_until="networkidle"); pg.wait_for_timeout(800)
        (pg.touchscreen.tap if touch else pg.mouse.click)(b["x"], b["y"]); pg.wait_for_timeout(400)
        s = pg.locator("[data-reader-action=search]")
        s.tap() if touch else s.click()
        pg.wait_for_timeout(400)
        pg.locator(".mobile-menu input[type=search]").fill("тилака")
        try:
            pg.locator(".mobile-menu nav a:visible mark").first.wait_for(timeout=15000)
        except Exception:
            pass
        n = pg.locator(".mobile-menu nav a:visible").count()
        check(dev, "Russian search loads search-index.ru-iast.json, has results",
              any(u.endswith("search-index.ru-iast.json") for u in reqs) and not any(u.endswith("search-index.ru.json") for u in reqs) and n > 0,
              f"{reqs} n={n}")
        # 5. no EPUB/PDF link to the Cyrillic Russian in the UI
        bad = pg.evaluate("""() => [...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href'))
            .filter(h => /\\.(epub|pdf)(\\?|#|$)/i.test(h) || /\\/ru\\//.test(h))""")
        check(dev, "no links to Cyrillic-Russian pages / files in UI", not bad, str(bad))
        check(dev, "no page errors", not errs, "; ".join(errs[:3]))
        br.close()

fails = [r for r in results if not r[2]]
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
for f in fails:
    print("FAILED:", f)
