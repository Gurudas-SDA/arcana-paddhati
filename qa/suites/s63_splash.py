"""Start screen with the CA sign (Vraja Lila, 20.10.2026, ДА msg 5520; code msg 762 «CA-loader v2»).

Task: a white full-screen layer with the sign 200 px in the middle from the first paint; when the first page is
ready (hydrated + drawn) the sign leaves in 450 ms ease-out (opacity 1→0, scale 1→1.6), the layer fades and is
removed — no artificial delay; iOS startup pictures for the main iPhone/iPad sizes and orientations (white + the
sign at the same place and size = the first frame); manifest background_color #ffffff; reduced motion — the sign
stays still, only fades; never holds the page: if the script is late or missing, the layer goes after 4 s.
V53 (Враджа Лила 23.10 msg 6433): на телефоне знак 170 px (200 × 0,85); планшет и компьютер — 200 px.
# tehniskais slieksnis Lipikāra, nav S noteikums: sign 200 ± 1 px, centre ± 1 px; leaving starts ≤ 1500 ms
#   after DOMContentLoaded locally; layer gone ≤ 800 ms after leaving starts; startup picture: sign box
#   200 × dpr ± 4 px, centred ± 3 px.
usage: python s63_splash.py <base-url>
"""
import io
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "ipad-portrait", "desktop"])
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


# From the very start of the document: every frame [t, layer present+shown, class, opacity, sign rect, sign anims]
REC = """(() => { window.__sp = []; window.__dcl = 0; document.addEventListener('DOMContentLoaded', () => { window.__dcl = Math.round(performance.now()); });
  const f = () => { const s = document.getElementById('ap-splash');
    if (s) { const g = s.querySelector('svg'); const r = g && g.getBoundingClientRect(); const cs = getComputedStyle(s);
      const sign = s.querySelector('.ap-splash-sign');
      window.__sp.push([Math.round(performance.now()), !s.hidden && cs.display !== 'none' && cs.visibility !== 'hidden', s.className, +(+cs.opacity).toFixed(3),
        r ? [Math.round(r.left * 10) / 10, Math.round(r.top * 10) / 10, Math.round(r.width * 10) / 10, Math.round(r.height * 10) / 10] : null,
        sign ? sign.getAnimations().map(a => a.animationName + ':' + a.effect.getTiming().duration + ':' + a.effect.getTiming().easing) .join() : '',
        cs.backgroundColor, cs.pointerEvents, innerWidth, innerHeight]); }
    else window.__sp.push([Math.round(performance.now()), null]);
    if (performance.now() < 6000) requestAnimationFrame(f); };
  requestAnimationFrame(f);
  // The leaving itself, seen by the page (frames may be few while the page hydrates; CSS animations run on):
  // [t, 'out' | 'gone', sign animations name:duration:timing-function, layer animations, loader dot animations]
  window.__ev = []; const watch = () => { const s = document.getElementById('ap-splash'); if (!s) return setTimeout(watch, 5);
    new MutationObserver(() => { const sign = s.querySelector('.ap-splash-sign'), dot = s.querySelector('.ca-dot');
      const an = (e) => e ? e.getAnimations().map(a => a.animationName + ':' + a.effect.getTiming().duration + ':' + getComputedStyle(e).animationTimingFunction).join() : '';
      window.__ev.push([Math.round(performance.now()), s.hidden ? 'gone' : s.className, an(sign), an(s), an(dot)]); })
      .observe(s, {attributes: true, attributeFilter: ['class', 'hidden']}); };
  watch(); })();"""


def run(b, opts, reduce=False, js=True):
    c = b.new_context(service_workers="block", locale="ru-RU", java_script_enabled=js,
                      reduced_motion="reduce" if reduce else "no-preference", **opts)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}" + REC)
    pg = c.new_page()
    pg.goto(f"{BASE}/ru-iast/", wait_until="load")
    if not js:
        pg.wait_for_timeout(5200)
        st = pg.evaluate("""() => { const s = document.getElementById('ap-splash'); if (!s) return null; const cs = getComputedStyle(s);
          return {vis: cs.visibility, op: +cs.opacity, pe: cs.pointerEvents}; }""")
        c.close()
        return st
    pg.wait_for_timeout(3000)
    ev = pg.evaluate("window.__ev")
    fr = [f if len(f) > 2 else f + [None, None, None, "", None, None, None, None] for f in pg.evaluate("window.__sp")]
    dcl = pg.evaluate("window.__dcl")
    c.close()
    return fr, dcl, ev


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        fr, dcl, ev = run(b, opts)
        shown = [f for f in fr if f[1]]
        first = shown[0] if shown else None
        check(dev, "white layer with the sign from the first frame", fr and fr[0][1] is True and first[6] == "rgb(255, 255, 255)", fr[:1])
        if first:
            l, t, w, h = first[4]
            vw, vh = first[8], first[9]
            want_px = 170 if vw < 640 else 200  # V53: phone (viewport < 640 px, as in lib/caSplash.ts) 170 px
            check(dev, f"sign {want_px} px, in the middle (±1 px)", abs(w - want_px) <= 1 and abs(h - want_px) <= 1 and abs(l + w / 2 - vw / 2) <= 1 and abs(t + h / 2 - vh / 2) <= 1,
                  {"rect": first[4], "vw": vw, "vh": vh})
            check(dev, "never takes a tap (pointer-events none)", first[7] == "none", first[7])
        out = next((e for e in ev if e[1] == "ap-splash-out"), None)
        gone = next((e for e in ev if e[1] == "gone"), None)
        check(dev, "leaves when the page is ready — no artificial delay (≤ 1500 ms after DOMContentLoaded)", out and out[0] - dcl <= 1500,
              {"out": out and out[0], "dcl": dcl})
        check(dev, "sign leaves 450 ms ease-out (opacity 1→0, scale 1→1.6), layer fades with it",
              out and "ap-splash-sign:450:ease-out" in out[2] and "ap-splash-bg:450:ease-out" in out[3], out)
        check(dev, "layer removed when the leaving ends (400–800 ms after it starts)", out and gone and 400 <= gone[0] - out[0] <= 800,
              {"out": out and out[0], "gone": gone and gone[0]})
        # reduced motion: the sign stays still, only the layer fades
        fr2, _, ev2 = run(b, opts, reduce=True)
        out2 = next((e for e in ev2 if e[1] == "ap-splash-out"), None)
        gone2 = next((e for e in ev2 if e[1] == "gone"), None)
        check(dev, "reduced motion: sign still (no scale, no loader motion), layer fades and goes",
              out2 and gone2 and "ap-splash-sign" not in out2[2] and "ca-trail" not in out2[4] and "ap-splash-bg:450" in out2[3], {"out": out2, "gone": gone2 and gone2[0]})
        # no JavaScript at all: CSS alone removes the layer after 4 s
        st = run(b, opts, js=False)
        check(dev, "script missing: the layer is gone after 4 s (CSS safety)", st and st["vis"] == "hidden" and st["op"] == 0, st)
        b.close()

    # iOS startup pictures: every size and orientation, white with the sign 200 CSS px in the middle; manifest white
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto(f"{BASE}/ru-iast/", wait_until="load")
    links = pg.evaluate("[...document.querySelectorAll('link[rel=apple-touch-startup-image]')].map(l => [l.href, l.media])")
    capable = pg.evaluate("!!document.querySelector('meta[name=apple-mobile-web-app-capable][content=yes]')")
    man = pg.evaluate(f"fetch('{BASE}/manifest.json').then(r => r.json())")
    b.close()
    check("ios", "manifest background_color #ffffff", (man.get("background_color") or "").lower() == "#ffffff", man.get("background_color"))
    check("ios", "apple-mobile-web-app-capable", capable)
    want = {("portrait", "390", "844", "3"), ("landscape", "390", "844", "3"), ("portrait", "375", "667", "2"), ("portrait", "820", "1180", "2"),
            ("landscape", "820", "1180", "2"), ("portrait", "1024", "1366", "2"), ("landscape", "1024", "1366", "2"), ("portrait", "430", "932", "3")}
    have = set()
    bad = []
    from PIL import Image  # noqa: E402
    for href, media in links:
        m = re.search(r"device-width: (\d+)px\) and \(device-height: (\d+)px\) and \(-webkit-device-pixel-ratio: (\d+)\) and \(orientation: (\w+)", media or "")
        if not m:
            bad.append([href, media, "media"])
            continue
        w, h, d, o = m.groups()
        have.add((o, w, h, d))
        try:
            im = Image.open(io.BytesIO(urllib.request.urlopen(href, timeout=30).read())).convert("RGB")
        except Exception as e:  # noqa: BLE001
            bad.append([href, str(e)])
            continue
        W, H = (int(w) * int(d), int(h) * int(d)) if o == "portrait" else (int(h) * int(d), int(w) * int(d))
        bb = im.point(lambda v: 255 if v < 200 else 0).convert("L").getbbox()
        size = (170 if (int(w) if o == "portrait" else int(h)) < 640 else 200) * int(d)  # V53: phone 170, tablet 200
        ok = im.size == (W, H) and im.getpixel((2, 2)) == (255, 255, 255) and bb and abs((bb[2] - bb[0]) - size) <= 4 and \
            abs((bb[0] + bb[2]) / 2 - W / 2) <= 3 and abs((bb[1] + bb[3]) / 2 - H / 2) <= 3
        if not ok:
            bad.append([href.rsplit("/", 1)[-1], im.size, (W, H), bb])
    check("ios", f"startup pictures for the main iPhone/iPad sizes, both orientations ({len(links)})", len(links) >= 40 and want <= have, sorted(want - have))
    check("ios", "every startup picture: white, sign 170 CSS px (phone, < 640 px wide) or 200 (tablet) in the middle, exact screen size", links and not bad, bad[:5])

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
