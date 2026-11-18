"""V103 Vraja Lila msg 8446: «сейчас при нажатии на обложку открывается эпиграф — убери эту функцию… при нажатии в любом месте и на обложку просто выезжает нижнее и верхнее меню, как до этого».
Criteria (register V103):
 (1) a tap on the cover does not open «Эпиграф» (no navigation; the cover is no button; no fade overlay);
 (2) a tap on the cover and a tap elsewhere on the page only show / hide the top and the bottom bar, as before;
 (3) all devices: iPhone, Android, iPad, computer.
usage: python s_v103_cover_tap_toggles_bars.py <base-url>   (QA_DEVICES filters devices)
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7", "ipad-portrait", "desktop"])
LANG = "ru-iast"
res = []


def chk(d, n, ok, info=""):
    res.append(bool(ok)); print(f"  [{'PASS' if ok else 'FAIL'}] {d} {n} {'' if ok else info}", flush=True)


def run(p, dev, eng, o):
    br = getattr(p, eng).launch()
    touch = o.get("has_touch", False)
    ctx = br.new_context(service_workers="block", **o)
    pg = ctx.new_page()
    pg.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true')}catch(e){}")
    pg.goto(f"{BASE}/{LANG}/", wait_until="networkidle"); pg.wait_for_timeout(900)
    path0 = pg.evaluate("location.pathname")
    tap = (lambda x, y: pg.touchscreen.tap(x, y)) if touch else (lambda x, y: pg.mouse.click(x, y))
    shown = lambda: pg.locator(".reader-chrome[data-shown]").count() == 1
    box = pg.locator("img.home-cover").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    vw, vh = o["viewport"]["width"], o["viewport"]["height"]
    chk(dev, "the cover is no button and there is no fade overlay", pg.locator(".home-cover-btn, .cover-fade, button:has(img.home-cover)").count() == 0)
    chk(dev, "bars hidden at the start", not shown())
    tap(cx, cy); pg.wait_for_timeout(700)
    chk(dev, "a tap on the cover: stays on the cover (no «Эпиграф»)", pg.evaluate("location.pathname") == path0, pg.evaluate("location.pathname"))
    chk(dev, "a tap on the cover: the top and the bottom bar come out", shown() and pg.locator(".reader-bar-top").count() == 1 and pg.locator(".reader-bar-bottom").count() == 1)
    tap(cx, cy); pg.wait_for_timeout(700)
    chk(dev, "a second tap on the cover hides the bars; still the cover", (not shown()) and pg.evaluate("location.pathname") == path0)
    # a tap elsewhere on the page (the field beside / below the cover)
    ex, ey = (8, vh / 2) if box["x"] > 20 else (vw / 2, min(vh - 8, box["y"] + box["height"] + 6))
    tap(ex, ey); pg.wait_for_timeout(700)
    chk(dev, "a tap elsewhere on the page: the bars come out; still the cover", shown() and pg.evaluate("location.pathname") == path0, str((ex, ey)))
    tap(cx, cy); pg.wait_for_timeout(700)
    chk(dev, "then a tap on the cover hides them again; still the cover", (not shown()) and pg.evaluate("location.pathname") == path0)
    br.close()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        print(dev, flush=True)
        try:
            run(p, dev, eng, o)
        except Exception as e:  # noqa: BLE001
            chk(dev, "EXCEPTION", False, str(e)[:600])
print(f"{sum(res)}/{len(res)} PASS")
sys.exit(0 if res and all(res) else 1)
