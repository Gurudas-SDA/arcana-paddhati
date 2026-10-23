"""s109 — the book in two languages only: English and Russian with IAST.

Noteikums (S 23.10.2026, Padomnieka grupa, msg 934–941, burtiski):
  934 «Буквально сейчас нам не нужны остальные языки, когда мы работаем»
  937 «Оставляю два языка: английский и русский»
  939 «Их убрать»
  941 «Оставить версию с IAST»
(Padomnieks 2026.10.23_1555: убрать, но сохранить — the data files stay; old links must not break.)

Checks
  a) the «Аа» language menu offers exactly English + «Русский» (ru-iast); no other language;
  b) old addresses redirect to the same place: /ru/<x>/ -> /ru-iast/<x>/ (hash kept), /de/ -> / (English),
     /de/<x>/#y -> /<x>/#y, /lv/, /uk/<x>/ -> English; an old saved language (localStorage arcanaLang) of a
     removed language becomes en / ru-iast;
  c) build: no search index of a removed language; the offline book (precache-manifest) has no page of a
     removed language; the redirect pages are real pages (200) of their own, not the built book;
     404.html carries the same mapping (an address this build does not know).
  d) data kept: data/book.<lang>.json of every removed language is still in the repo.

usage: python s109_two_languages.py <base-url>
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
LOCAL = BASE.startswith("http://127.0.0.1") or BASE.startswith("http://localhost")
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
REMOVED = ["ru", "lv", "de", "fr", "es", "it", "uk", "hu", "pt", "lt"]
PAGE = "offering-bhoga"
results = []


def check(dev, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else info}", flush=True)


def status(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""


def path(url):
    return url[len(BASE):] if url.startswith(BASE) else url


# ---------- c / d: build and data (no browser) ----------
code, body = status(BASE + "/precache-manifest.json")
man = json.loads(body) if code == 200 else {"urls": [], "groups": []}
pref = qa.PREFIX + "/"
bad_urls = [u for u in man["urls"] if u.startswith(pref) and u[len(pref):].split("/")[0] in REMOVED]
check("build", "c offline book (precache-manifest) has no page of a removed language",
      code == 200 and not bad_urls, f"http {code}, {len(bad_urls)} url(s), e.g. {bad_urls[:3]}")
check("build", "c precache groups only shell / en / ru-iast / transcripts",
      code == 200 and set(man["groups"]) <= {"shell", "en", "ru-iast", "transcripts"}, sorted(set(man["groups"])))
idx = {l: status(f"{BASE}/search-index.{l}.json")[0] for l in ["en", "ru-iast"] + REMOVED}
check("build", "c search index only en + ru-iast",
      idx["en"] == 200 and idx["ru-iast"] == 200 and all(idx[l] == 404 for l in REMOVED), idx)
code, body = status(f"{BASE}/de/{PAGE}/")
html = body.decode("utf-8", "replace")
check("build", "c /de/<chapter>/ is a redirect page of its own (200, refresh to the English chapter), not the built book",
      code == 200 and f'url={qa.PREFIX}/{PAGE}/"' in html and "app-main" not in html, f"http {code} {html[:160]!r}")
rsc = status(f"{BASE}/de/{PAGE}/index.txt")[0]
check("build", "c no RSC payload of a removed language (not built)", rsc == 404, f"http {rsc}")
if LOCAL:
    f404 = os.path.join(qa.OUT, "404.html")
    raw = open(f404, encoding="utf-8").read() if os.path.isfile(f404) else ""
    check("build", "c 404.html maps unknown /de/… to English and /ru/… to /ru-iast/",
          '"de":""' in raw and '"ru":"ru-iast/"' in raw, f"404.html {'present' if raw else 'missing'}")
missing = [l for l in REMOVED if not os.path.isfile(os.path.join(qa.DATA, f"book.{l}.json"))]
check("data", "d data/book.<lang>.json of the removed languages kept (убрать, но сохранить)", not missing, missing)

# ---------- a / b: in the browser ----------
with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        touch = opts.get("has_touch", False)
        br = getattr(p, eng).launch()
        ctx = br.new_context(service_workers="block", **opts)
        ctx.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))

        # a) language menu
        pg.goto(f"{BASE}/ru-iast/{PAGE}/", wait_until="networkidle")
        pg.wait_for_timeout(1000)
        pt = pg.evaluate("""() => { const a = document.querySelector('.app-main article').getBoundingClientRect();
                                     return {x: a.left + 6, y: innerHeight / 2}; }""")
        if pg.locator(".reader-chrome[data-shown]").count() == 0:
            (pg.touchscreen.tap if touch else pg.mouse.click)(pt["x"], pt["y"]); pg.wait_for_timeout(400)
        aa = pg.locator("[data-reader-action=aa]")
        aa.tap() if touch else aa.click()
        pg.wait_for_timeout(500)
        lt = pg.locator(".reader-panel [data-lang-trigger]")
        if lt.count():
            lt.tap() if touch else lt.click()
            pg.wait_for_timeout(400)
        vals = pg.evaluate("""() => [...document.querySelectorAll('[role=listbox] [role=option]')]
            .map(o => [o.getAttribute('data-lang'), o.querySelector('.lang-option-name').textContent.trim()])""")
        pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
        check(dev, "a language menu = English + «Русский» (ru-iast) only",
              vals == [["en", "English"], ["ru-iast", "Русский"]], vals)
        check(dev, "a no page errors on the Russian page with the menu", not errs, errs[:3])

        # b) old addresses
        for old, want, h1 in [
            (f"/ru/{PAGE}/#x", f"/ru-iast/{PAGE}/#x", True),
            ("/ru/", "/ru-iast/", False),
            ("/de/", "/", False),
            (f"/de/{PAGE}/#x", f"/{PAGE}/#x", True),
            ("/lv/", "/", False),
            ("/uk/introduction/", "/introduction/", True),
        ]:
            pg.goto(BASE + old, wait_until="networkidle")
            pg.wait_for_timeout(900)
            ok = path(pg.url) == want and (not h1 or pg.locator("article h1").count() >= 1)
            check(dev, f"b {old} -> {want}", ok, path(pg.url))
        if not LOCAL:
            pg.goto(f"{BASE}/de/no-such-page-s109/", wait_until="networkidle")
            pg.wait_for_timeout(900)
            check(dev, "b unknown /de/… (404 page) -> English address", "/de/" not in path(pg.url), path(pg.url))

        # b) saved language of a removed language
        for saved, want_saved, want_url in [("de", "en", "/"), ("ru", "ru-iast", "/ru-iast/"), ("pt", "en", "/")]:
            pg.goto(f"{BASE}/", wait_until="networkidle")
            pg.evaluate(f"localStorage.setItem('arcanaLang', '{saved}')")
            pg.goto(f"{BASE}/", wait_until="networkidle")
            pg.wait_for_timeout(1500)
            now = pg.evaluate("localStorage.getItem('arcanaLang')")
            check(dev, f"b saved '{saved}' -> '{want_saved}', start page {want_url}",
                  now == want_saved and path(pg.url) == want_url, f"saved={now} url={path(pg.url)}")
        br.close()

print(f"\n{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
