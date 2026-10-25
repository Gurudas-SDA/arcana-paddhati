"""V53 Враджа Лила msg 6433: красное лого заставки на мобильной на 15 % меньше (×0,85), пропорции и центр те же;
компьютер/планшет не менять. (23.10.2026, nodots-izpildei msg 1696; Vraja 25.10 msg 1800 «заверши до V59»)

Splash logo = `#ap-splash .ca-loader` (Vraja Lila's CA sign, was 200 px). To measure it before the app signals
"ready" (the layer then fades out), the page's own scripts (/_next/*.js) are blocked: the server-rendered splash stays.
Per device:
  a) mobile (viewport < 640 px: iphone14, pixel7) logo width = height = 200 * 0.85 = 170 px (was 200);
  b) tablet / computer (ipad-portrait 820, desktop 1440) logo stays 200 px;
  c) the logo is centred in the viewport and not cut off (fully inside it);
  d) the animation is not broken: the orbit group and all 24 dots still carry running CSS animations.
usage: python s110_splash_logo_smaller_v53.py <base-url>
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
WAS = 200.0  # px, Vraja Lila's --ca-size before V53
TOL = 1.0  # tehniskais slieksnis Lipikāra, nav S noteikums (±1 px: sub-pixel layout tolerance)
results = []

MEASURE_JS = """() => {
  const e = document.querySelector('#ap-splash .ca-loader');
  if (!e) return null;
  const r = e.getBoundingClientRect();
  const vw = document.documentElement.clientWidth, vh = document.documentElement.clientHeight;
  const dots = [...document.querySelectorAll('#ap-splash .ca-dot')];
  const orbit = document.querySelector('#ap-splash .ca-orbit');
  return {w: r.width, h: r.height, cx: r.left + r.width / 2, cy: r.top + r.height / 2, left: r.left, top: r.top,
          right: r.right, bottom: r.bottom, vw, vh, dots: dots.length,
          dotsAnim: dots.filter(d => getComputedStyle(d).animationName === 'ca-trail').length,
          orbitAnim: getComputedStyle(orbit).animationName === 'ca-spin'};
}"""


def check(device, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {device} {name} {'' if ok else info}", flush=True)


with sync_playwright() as p:
    for device, engine, options in qa.devices(["iphone14", "pixel7", "ipad-portrait", "desktop"]):
        browser = getattr(p, engine).launch()
        context = browser.new_context(service_workers="block", **options)
        page = context.new_page()
        page.route("**/_next/**/*.js", lambda route: route.abort())
        page.goto(f"{BASE}/", wait_until="commit")
        page.wait_for_selector("#ap-splash .ca-loader", state="attached", timeout=15000)
        m = page.evaluate(MEASURE_JS)
        mobile = m["vw"] < 640
        want = WAS * 0.85 if mobile else WAS
        print(f"  {device}: viewport {m['vw']}x{m['vh']}, logo {m['w']:.2f}x{m['h']:.2f} px (want {want:.0f})", flush=True)
        check(device, f"{'mobile' if mobile else 'tablet/computer'}: logo {want:.0f} px"
              + (" (-15 % from 200)" if mobile else " (unchanged)"),
              abs(m["w"] - want) <= TOL and abs(m["h"] - want) <= TOL, m)
        check(device, "logo is square, proportions kept", abs(m["w"] - m["h"]) <= 0.01, m)
        check(device, "logo centred and not cut off",
              abs(m["cx"] - m["vw"] / 2) <= TOL and abs(m["cy"] - m["vh"] / 2) <= TOL
              and m["left"] >= 0 and m["top"] >= 0 and m["right"] <= m["vw"] and m["bottom"] <= m["vh"], m)
        check(device, "animation intact (orbit spin + 24 dots trail)",
              m["orbitAnim"] and m["dots"] == 24 and m["dotsAnim"] == 24, m)
        context.close()
        browser.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
