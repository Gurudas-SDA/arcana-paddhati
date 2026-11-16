"""V99 Враджа Лила msg 2980: «более компактное меню, но только когда речь идёт о низких экранах... в остальном оно должно оставаться как сейчас».
Vraja's criteria: (1) on a LOW screen (by height; older Android phones) the «Аа» window is more compact and fits without scrolling,
the last button «Свернуть содержание» included; (2) iPhone 14, iPad, desktop, Pixel 7 look exactly as before;
(3) every item and the button work as before; light and night themes.
# tehniskais slieksnis Lipikāra, nav S noteikums: low = viewport height <= 700 px (CSS @media max-height: 700px); fixed tall-device sizes = V98 main (+-1 px);
# tehniskais slieksnis Lipikāra, nav S noteikums: no font shrinks in the compact window (smallest = 12 px, as on tall screens; caps labels 11 px as before)
usage: python s_v99_compact_aa_short_screens.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
LANG = "ru-iast"
CHAP = "mangala-arati-songs"
SHOTS = os.environ.get("V99_SHOTS")  # optional dir for screenshots
TAG = os.environ.get("V99_TAG", "")
results = []

LOW = [("low-360x640", 360, 640), ("low-360x600", 360, 600), ("low-320x568", 320, 568)]
# tall devices: expected panel size on main (V98) — measured before the change
TALL_EXPECT = json.loads(os.environ.get("V99_TALL_EXPECT") or open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s_v99_tall_expect.json")).read())

MEASURE = """() => { const p = document.querySelector('.reader-panel'); const r = p.getBoundingClientRect();
  const last = document.querySelector('.reader-reset'); const lr = last.getBoundingClientRect();
  const labs = [...p.querySelectorAll('.reader-panel-label')].map(e => getComputedStyle(e).marginTop + '/' + getComputedStyle(e).marginBottom);
  return {top: r.top, bottom: r.bottom, w: r.width, h: r.height, vh: window.innerHeight,
    scrollH: p.scrollHeight, clientH: p.clientHeight, lastBottom: lr.bottom, lastTop: lr.top,
    fontMin: Math.min(...[...p.querySelectorAll('button span, button, .reader-panel-title, .reader-size-value, .lang-field-value')].map(e => parseFloat(getComputedStyle(e).fontSize))),
    pad: ['Top','Right','Bottom','Left'].map(s => getComputedStyle(p)['padding'+s]).join(' '), labs: labs.join('|'), sepM: getComputedStyle(p.querySelector('.reader-reset-sep')).marginTop}; }"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:900]}", flush=True)


def open_panel(pg):
    pg.evaluate("document.querySelector('[data-reader-action=\"aa\"]').click()")
    pg.wait_for_selector(".reader-panel", timeout=10000)
    pg.wait_for_timeout(600)


def run(p, dev, eng, opts, theme, low):
    try:
        b = getattr(p, eng).launch()
    except Exception:  # WebKit libs missing on this server: same viewport + touch in Chromium (CSS layout is what is measured)
        b = p.chromium.launch()
        opts = {k: v for k, v in opts.items() if k != "user_agent"}
    c = b.new_context(service_workers="block", locale="ru-RU", **opts)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');"
                      f"localStorage.setItem('ap.readerTheme','{theme}');localStorage.setItem('ap.readerLayout','page');}}catch(e){{}}")
    pg = c.new_page()
    pg.goto(f"{BASE}/{LANG}/{CHAP}/", wait_until="networkidle")
    pg.wait_for_timeout(1000)
    open_panel(pg)
    m = pg.evaluate(f"({MEASURE})()")
    name = f"{dev} {theme}"
    if SHOTS:
        pg.screenshot(path=os.path.join(SHOTS, f"{TAG}_{dev}_{theme}.png"))
    if low:
        check(name, "window fits: bottom <= viewport, no inner scroll, last button visible",
              m["bottom"] <= m["vh"] + 0.5 and m["scrollH"] <= m["clientH"] + 1 and m["lastBottom"] <= m["bottom"] + 0.5 and m["lastTop"] >= m["top"], m)
        check(name, "compact window: no font smaller than on tall screens (>= 12 px)", m["fontMin"] >= 12, m["fontMin"])
        # the button still works: tap folds contents and goes to the cover
        pg.evaluate("document.querySelector('.reader-reset').click()")
        pg.wait_for_timeout(2500)
        check(name, "«Свернуть содержание» works — reader on the cover", pg.evaluate("location.pathname").rstrip("/").endswith(f"/{LANG}"), pg.evaluate("location.pathname"))
    else:
        exp = TALL_EXPECT[dev]
        # engine-neutral: the @media block must NOT be active — computed spacing equals the base CSS values exactly (padding 10px 14px 14px,
        # label margins, separator margin); the height is a Chromium measurement of main, other engines/fonts differ by a few px
        # tehniskais slieksnis Lipikāra, nav S noteikums: height tolerance ±3 px
        ok = (abs(m["h"] - exp["h"]) <= 3 and abs(m["w"] - exp["w"]) <= 1 and abs(m["top"] - exp["top"]) <= 1 and m["labs"] == exp["labs"]
              and m["sepM"] == exp["sepM"] and m["pad"] == "10px 14px 14px 14px")
        check(name, "tall device: window size/spacing identical to main", ok, {"now": m, "main": exp})
    b.close()


with sync_playwright() as p:
    for theme in ("white", "night"):
        for dev, w, h in LOW:
            eng, opts = qa.DEVICES["pixel7"]
            opts = dict(opts, viewport={"width": w, "height": h})
            run(p, dev, eng, opts, theme, True)
    for dev in ("iphone14", "ipad-portrait", "desktop", "pixel7"):
        eng, opts = qa.DEVICES[dev]
        for theme in ("white", "night"):
            run(p, dev, eng, dict(opts), theme, False)

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
