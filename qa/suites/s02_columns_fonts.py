"""Reader UI v2 measurements: column width, body/verse font size, A+/A- and persistence.
usage: python v2_test.py <base-url> [shots-dir] [prefix]"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402  (device profiles, repo paths)
import os, sys
from playwright.sync_api import sync_playwright
BASE = sys.argv[1].rstrip("/"); SHOTS = sys.argv[2] if len(sys.argv) > 2 else None
PFX = sys.argv[3] if len(sys.argv) > 3 else "v2"
IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
IPAD = IOS.replace("iPhone; CPU iPhone OS", "iPad; CPU OS")
PIX = "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36"
MIN_COL_FONT = {"iphone14": (0.92, 18), "pixel7": (0.92, 18), "ipad-portrait": (0.85, 20), "ipad-landscape": (0.85, 21), "desktop": (0.0, 21)}
DEV = [(n, e, o, *MIN_COL_FONT[n]) for n, e, o in qa.devices(list(MIN_COL_FONT))]
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
ONLY = None  # device filter: QA_DEVICES (qa/lib/qa.py)
URL = f"{BASE}/ru-iast/daily-duties-brahma-muhurta/"
M = """() => { const a = document.querySelector('.app-main article'); const ar = a.getBoundingClientRect();
 const cs = getComputedStyle(a); const inner = ar.width - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
 const body = [...a.querySelectorAll('p')].find(p => p.className.includes('text-[15px]'));
 const verse = a.querySelector('.sanskrit');
 const h1 = a.querySelector('h1');
 const fs = e => e ? parseFloat(getComputedStyle(e).fontSize) : null;
 return {w: window.innerWidth, col: inner, ratio: inner / window.innerWidth, body: fs(body), verse: fs(verse), h1: fs(h1),
   vAlign: verse ? getComputedStyle(verse).textAlign : null, cpl: body ? inner / (fs(body) * 0.5) : null}; }"""
res = []
def chk(d, n, ok, info=""):
    res.append(ok); print(f"  [{'PASS' if ok else 'FAIL'}] {d} {n} {info}")
with sync_playwright() as p:
    for dev, eng, o, minr, minfs in DEV:
        if ONLY and dev not in ONLY.split(","): continue
        br = getattr(p, eng).launch(); ctx = br.new_context(service_workers="block", **o); pg = ctx.new_page()
        touch = o.get("has_touch", False)
        act = lambda l: (l.tap() if touch else l.click(), pg.wait_for_timeout(400))
        pg.goto(URL, wait_until="networkidle"); pg.wait_for_timeout(1200)
        pg.evaluate("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
        pg.reload(wait_until="networkidle"); pg.wait_for_timeout(1000)
        m0 = pg.evaluate(M); print(dev, "default", m0)
        if SHOTS: pg.screenshot(path=os.path.join(SHOTS, f"{PFX}-{dev}-default.png"))
        if minr: chk(dev, f"column >= {minr:.0%} of viewport", m0["ratio"] >= minr, f"{m0['ratio']:.3f}")
        chk(dev, f"body font >= {minfs}px", (m0["body"] or 0) >= minfs, m0["body"])
        if not os.environ.get("MEASURE_ONLY"):
            chk(dev, "verse centred", m0["vAlign"] == "center", m0["vAlign"])
            # A+ x2
            pg.evaluate("document.querySelector('.app-main').click()") if False else None
            ep = pg.evaluate(JS_EMPTY_POINT)
            (pg.touchscreen.tap if touch else pg.mouse.click)(ep["x"], ep["y"]); pg.wait_for_timeout(500); print("tap", ep, pg.url)
            if pg.locator(".reader-chrome[data-shown]").count() == 0:
                ep = pg.evaluate(JS_EMPTY_POINT); (pg.touchscreen.tap if touch else pg.mouse.click)(ep["x"], ep["y"]); pg.wait_for_timeout(500); print("tap", ep, pg.url)
            act(pg.locator("[data-reader-action=aa]"))
            act(pg.locator("[data-reader-size='+']")); act(pg.locator("[data-reader-size='+']"))
            if SHOTS: pg.screenshot(path=os.path.join(SHOTS, f"{PFX}-{dev}-aa-panel.png"))
            m2 = pg.evaluate(M); print(dev, "A+x2", m2)
            chk(dev, "A+x2 body >= +15%", m2["body"] >= m0["body"] * 1.15, f"{m0['body']}->{m2['body']}")
            chk(dev, "A+x2 verse >= +15%", m2["verse"] >= m0["verse"] * 1.15, f"{m0['verse']}->{m2['verse']}")
            chk(dev, "A+x2 h1 scales", m2["h1"] > m0["h1"] * 1.15, f"{m0['h1']}->{m2['h1']}")
            act(pg.locator("[data-reader-size='-']"))
            m1 = pg.evaluate(M); chk(dev, "A- reduces", m1["body"] < m2["body"], f"{m2['body']}->{m1['body']}")
            act(pg.locator("[data-reader-size='+']"))
            pg.keyboard.press("Escape") if not touch else act(pg.locator(".reader-panel-close"))
            pg.reload(wait_until="networkidle"); pg.wait_for_timeout(1000)
            m3 = pg.evaluate(M); chk(dev, "size persists after reload", abs(m3["body"] - m2["body"]) < 0.2, f"{m3['body']}")
            if SHOTS: pg.screenshot(path=os.path.join(SHOTS, f"{PFX}-{dev}-aplus2.png"))
            # sepia contrast
            pg.evaluate("localStorage.setItem('ap.readerTheme','sepia'); localStorage.removeItem('ap.readerSize')")
            pg.reload(wait_until="networkidle"); pg.wait_for_timeout(800)
            bg = pg.evaluate("getComputedStyle(document.querySelector('.app-main')).backgroundColor")
            chk(dev, "sepia bg #EFE6D2", bg == "rgb(239, 230, 210)", bg)
            if SHOTS and dev in ("ipad-landscape", "iphone14"): pg.screenshot(path=os.path.join(SHOTS, f"{PFX}-{dev}-sepia.png"))
            pg.evaluate("localStorage.removeItem('ap.readerTheme')")
        br.close()
print(f"\n{sum(res)}/{len(res)} passed")
