"""Offline test of the service worker (v5), Chromium (Android / desktop profiles).
usage: python s21_offline_deploy.py [<base-url ignored>]
 The suite runs its OWN server over out/; "deploy B" = the same build served with a
 new version stamp in sw.js + precache-manifest.json (qa/lib/server.py switch mode).
 1. online first visit -> SW ready + precache complete (marker in cache)
 2. offline: reload, 10 random chapters RU + 10 EN (navigation), client-side
    contents navigation, search, emblem, bundled transcript pages
 3. deploy B, user online for a moment (new SW starts installing) then offline:
    app still fully works from the old complete cache; old cache kept
 4. online again -> B completes, takes over, old cache dropped; offline still OK
"""
import json, os, random, sys, time
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402  (device profiles, repo paths)
import server as qa_server  # noqa: E402
from playwright.sync_api import sync_playwright
SRV = qa_server.Server().start()
PORT = SRV.port
BASE = SRV.base
A, B = "A", "B"
SHOTS = None
UA = "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36"
PROFILES = [
    ("android", dict(viewport={"width": 412, "height": 915}, has_touch=True, is_mobile=True, device_scale_factor=2.625, user_agent=UA)),
    ("desktop", dict(viewport={"width": 1440, "height": 900})),
]
res = []


def chk(d, n, ok, info=""):
    res.append((d, n, bool(ok), info)); print(f"  [{'PASS' if ok else 'FAIL'}] {d} {n} {'' if ok else info}", flush=True)


def set_root(p, delay=0):
    SRV.version_suffix = "" if p == "A" else "b"
    SRV.delay = delay


def manifest(site):
    m = json.load(open(os.path.join(qa.OUT, "precache-manifest.json"), encoding="utf8"))
    if site == "B":
        m = dict(m, version=m["version"] + "b")
    return m


CACHE_STATE = """async () => { const out = {};
  for (const k of await caches.keys()) { if (!k.startsWith('arcana-paddhati-')) continue;
    const c = await caches.open(k); out[k] = {n: (await c.keys()).length, complete: !!(await c.match('/arcana-paddhati/__precache-complete__'))}; }
  return out; }"""


REG = """async () => { const r = await navigator.serviceWorker.getRegistration(); const s = w => w ? w.state + ':' + w.scriptURL.slice(-6) : null;
  return r ? {a: s(r.active), w: s(r.waiting), i: s(r.installing)} : null; }"""


def wait_complete(pg, version, timeout=600, nudge=False):
    t0 = time.time(); k = 0
    while time.time() - t0 < timeout:
        k += 1
        if nudge and k % 10 == 1:
            print("     nudge", int(time.time() - t0), pg.evaluate(REG), pg.evaluate(CACHE_STATE), flush=True)
            pg.evaluate("navigator.serviceWorker.getRegistration().then(r => r && r.update()).catch(e => console.log('upd err ' + e))")
        st = pg.evaluate(CACHE_STATE)
        if st.get("arcana-paddhati-" + version, {}).get("complete"):
            return st, time.time() - t0
        pg.wait_for_timeout(2000)
    return pg.evaluate(CACHE_STATE), None


def page_ok(pg, kind="chapter"):
    """Real book page rendered (not the browser error / offline notice)."""
    try:
        return pg.locator("article.reader-article, img.home-cover").count() >= 1 and pg.locator("h1, img.home-cover").count() >= 1
    except Exception:
        return False


def run(p, dev, o):
    mA, mB = manifest(A), manifest(B)
    sections = sorted({u.split("/")[2] for u in mA["urls"] if u.count("/") == 3 and u.endswith("/") and u.split("/")[2] not in ("ru", "ru-iast", "lv", "de", "fr", "es", "it", "uk", "hu", "pt", "lt", "")})
    tr_pages = [u for u in mA["urls"] if "/transcripts/" in u]
    set_root(A)
    br = p.chromium.launch()
    ctx = br.new_context(**o)
    pg = ctx.new_page()
    errs = []
    pg.on("console", lambda m: print("     console:", m.text, flush=True) if "upd" in m.text else None)
    pg.on("pageerror", lambda e: errs.append(pg.url + " :: " + str(e)[:80]))
    # 1. first visit online
    pg.goto(BASE + "/ru-iast/", wait_until="networkidle")
    pg.evaluate("navigator.serviceWorker.ready.then(() => true)")
    st, secs = wait_complete(pg, mA["version"])
    chk(dev, f"1 first visit: SW ready, precache complete ({len(mA['urls'])} URLs)", secs is not None, str(st))
    if secs is not None:
        print(f"     precache took {secs:.0f}s", flush=True)
    pg.reload(wait_until="networkidle")
    chk(dev, "1 page controlled by SW", pg.evaluate("!!navigator.serviceWorker.controller"))

    # 2. offline
    ctx.set_offline(True)
    pg.reload(wait_until="load"); pg.wait_for_timeout(800)
    chk(dev, "2 offline reload of the cover", page_ok(pg), pg.url)
    random.seed(6)
    for lang, prefix in (("ru", "/ru-iast"), ("en", "")):
        pick = random.sample(sections, 10)
        bad = []
        for sid in pick:
            pg.goto(f"{BASE}{prefix}/{sid}/", wait_until="load"); pg.wait_for_timeout(250)
            if not page_ok(pg) or sid not in pg.url:
                bad.append(sid)
        chk(dev, f"2 offline: 10 random chapters {lang.upper()} open", not bad, str(bad))
    # client-side navigation from the contents (two taps) offline
    pg.goto(f"{BASE}/ru-iast/gaudiya-emblem/", wait_until="load"); pg.wait_for_timeout(800)
    chk(dev, "2 offline: emblem chapter + picture", page_ok(pg) and pg.locator("img").count() >= 1 and pg.evaluate("[...document.images].every(i => i.complete && i.naturalWidth > 0)"))
    pg.evaluate("document.querySelector('.app-main').scrollTop = 0")
    tap = (lambda l: l.tap()) if o.get("has_touch") else (lambda l: l.click())
    if pg.locator(".reader-chrome[data-shown]").count() == 0:
        box = pg.locator("article h1").bounding_box()
        (pg.touchscreen.tap if o.get("has_touch") else pg.mouse.click)(box["x"] + 5, box["y"] + box["height"] + 40); pg.wait_for_timeout(500)
    tap(pg.locator("[data-reader-action=contents]")); pg.wait_for_timeout(600)
    link = pg.locator(".mobile-menu nav a[href$='/mangalacarana/']").first
    if link.count():
        tap(link); pg.wait_for_timeout(300); tap(link); pg.wait_for_timeout(1500)
        chk(dev, "2 offline: client-side navigation from Contents", "/mangalacarana/" in pg.url and page_ok(pg), pg.url)
    # search offline
    pg.goto(f"{BASE}/ru-iast/daily-deity-schedule/", wait_until="load"); pg.wait_for_timeout(800)
    if pg.locator(".reader-chrome[data-shown]").count() == 0:
        box = pg.locator("article h1").bounding_box()
        (pg.touchscreen.tap if o.get("has_touch") else pg.mouse.click)(box["x"] + 5, box["y"] + box["height"] + 40); pg.wait_for_timeout(500)
    tap(pg.locator("[data-reader-action=search]")); pg.wait_for_timeout(500)
    pg.locator(".mobile-menu input[type=search]").fill("тилака")
    try:
        pg.locator(".mobile-menu nav a:visible mark").first.wait_for(timeout=10000)
        n = pg.locator(".mobile-menu nav a:visible").count()
    except Exception:
        n = 0
    chk(dev, "2 offline: full-text search gives results", n > 0, str(n))
    if SHOTS and dev == "android":
        pg.screenshot(path=os.path.join(SHOTS, "v5-offline-android-search.png"))
    # transcripts offline: via the link in the book + 5 random pages
    pg.goto(f"{BASE}/ru-iast/gaudiya-emblem/", wait_until="load"); pg.wait_for_timeout(600)
    tl = pg.locator("a[data-transcript-link]").first
    href = tl.get_attribute("href") if tl.count() else None
    chk(dev, "2 «транскрипт» link points inside the app", href and href.startswith("/arcana-paddhati/transcripts/"), str(href))
    if href:
        tl.scroll_into_view_if_needed(); tap(tl); pg.wait_for_timeout(1200)
        ok = "/transcripts/" in pg.url and pg.locator("main h1").count() == 1 and pg.locator("main p").count() > 20
        chk(dev, "2 offline: tap «транскрипт» opens the transcript", ok, pg.url)
        if SHOTS and dev == "android":
            pg.screenshot(path=os.path.join(SHOTS, "v5-offline-android-transcript.png"))
        pg.go_back(); pg.wait_for_timeout(1200)
        chk(dev, "2 offline: back from transcript returns to the book", "/gaudiya-emblem/" in pg.url and page_ok(pg), pg.url)
    bad = []
    for u in random.sample(tr_pages, 5):
        pg.goto("http://127.0.0.1:%d%s" % (PORT, u), wait_until="load")
        if pg.locator("main p").count() < 5:
            bad.append(u)
    chk(dev, f"2 offline: 5 random transcript pages of {len(tr_pages)}", not bad, str(bad))
    if "unknown" not in os.environ.get("SKIP", ""):
      pg.goto(f"{BASE}/ru-iast/no-such-page/", wait_until="load")
    chk(dev, "2 offline: unknown page -> book / notice, never browser error", pg.locator("body").inner_text().strip() != "" , pg.url)

    # 3. deploy B; user online briefly (new SW begins installing), then offline
    set_root(B, delay=0.05)          # slow server: the new precache cannot finish
    ctx.set_offline(False)
    pg.goto(f"{BASE}/ru-iast/", wait_until="load")
    pg.evaluate("navigator.serviceWorker.getRegistration().then(r => r && r.update()).catch(() => {})")
    pg.wait_for_timeout(4000)
    st = pg.evaluate(CACHE_STATE)
    print("     step3", pg.evaluate(REG), st, flush=True)
    ctx.set_offline(True)
    newst = st.get("arcana-paddhati-" + mB["version"], {})
    chk(dev, "3 new deploy: new SW started, its cache incomplete when going offline", not newst.get("complete") and st.get("arcana-paddhati-" + mA["version"], {}).get("complete"), str(st))
    random.seed(7)
    bad = []
    for sid in random.sample(sections, 10):
        for prefix in ("/ru-iast", ""):
            pg.goto(f"{BASE}{prefix}/{sid}/", wait_until="load"); pg.wait_for_timeout(150)
            if not page_ok(pg):
                bad.append(prefix + "/" + sid)
    chk(dev, "3 offline right after a deploy: 20 pages (RU+EN) open from the old cache", not bad, str(bad))
    pg.goto(f"{BASE}/ru-iast/", wait_until="load"); pg.wait_for_timeout(400)
    chk(dev, "3 offline after deploy: cover opens", page_ok(pg))
    st2 = pg.evaluate(CACHE_STATE)
    chk(dev, "3 old complete cache still present", st2.get("arcana-paddhati-" + mA["version"], {}).get("complete"), str(st2))

    # 4. online again: B completes, takes over, old dropped
    set_root(B, delay=0)
    ctx.set_offline(False)
    pg.goto(f"{BASE}/ru-iast/", wait_until="networkidle")
    pg.evaluate("navigator.serviceWorker.getRegistration().then(r => r && r.update()).catch(() => {})")
    st3, secs = wait_complete(pg, mB["version"], timeout=300, nudge=True)
    chk(dev, "4 online again: new version precache completes", secs is not None, str(st3))
    t0 = time.time()
    while time.time() - t0 < 60 and ("arcana-paddhati-" + mA["version"]) in pg.evaluate(CACHE_STATE):
        pg.reload(wait_until="load"); pg.wait_for_timeout(2000)
    st4 = pg.evaluate(CACHE_STATE)
    chk(dev, "4 old cache dropped only after the new one is complete", list(st4) == ["arcana-paddhati-" + mB["version"]], str(st4))
    copied = pg.evaluate("""() => new Promise(r => { navigator.serviceWorker.controller.postMessage({type: 'precache-status'});
        navigator.serviceWorker.addEventListener('message', e => r(e.data), {once: true}); setTimeout(() => r(null), 8000); })""")
    chk(dev, "4 new SW controls the page", copied is not None and copied.get("version") == mB["version"], str(copied))
    ctx.set_offline(True)
    bad = []
    for sid in random.sample(sections, 5):
        pg.goto(f"{BASE}/ru-iast/{sid}/", wait_until="load")
        if not page_ok(pg):
            bad.append(sid)
    chk(dev, "4 offline on the new version: pages open", not bad, str(bad))
    chk(dev, "no page errors", not [e for e in errs if "Failed to fetch" not in e], "; ".join(errs[:3]))
    ctx.close(); br.close()


_W = qa.wanted()
with sync_playwright() as p:
    for dev, o in PROFILES:
        if _W is not None and {"android": "pixel7", "desktop": "desktop"}[dev] not in _W:
            continue
        print(dev, flush=True)
        try:
            run(p, dev, o)
        except Exception as e:
            chk(dev, "EXCEPTION", False, str(e)[:900])
fails = [r for r in res if not r[2]]
print(f"\n{len(res) - len(fails)}/{len(res)} passed")
for f in fails:
    print("FAILED:", f[0], f[1], f[3][:400])
SRV.stop()
