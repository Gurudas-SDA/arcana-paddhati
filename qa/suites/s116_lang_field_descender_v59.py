"""V59 — Враджа Лила 24.10 (msg 1789 + 6650/6651): on the phone, in the language field («🌐 English ⌄» in the «Аа» panel)
the word «English» has its «g» cut off at the bottom (descender). Cause: .lang-field-value has overflow:hidden (for the
ellipsis) and line-height 1.2 — the box (18 px at 15 px) is lower than the font's own ascent+descent, so the tail of «g» is clipped.

Criterion (Satkirti words): «English» in the language field is not cut off (frames iPhone / Pixel before / after).
Checks (en, iPhone 14 + Pixel 7, «Аа» panel):
  a) the text's own box (Range = ascent+descent of the font) lies inside the clipping box of .lang-field-value: bottom edge
     not cut, top edge not cut;
  b) .lang-field-value line-height >= 1.3 x font-size   # tehniskais slieksnis Lipikāra, nav S noteikums
Frames: env QA_SHOTS=<dir> -> <dir>/<device>_lang-field.png
usage: python s116_lang_field_descender_v59.py <base-url>
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
SHOTS = os.environ.get("QA_SHOTS")
PAGE = "offering-bhoga"
results = []


def check(dev, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else info}", flush=True)


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "pixel7"]):
        touch = opts.get("has_touch", False)
        br = getattr(p, eng).launch()
        ctx = br.new_context(service_workers="block", **opts)
        ctx.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
        pg = ctx.new_page()
        pg.goto(f"{BASE}/{PAGE}/", wait_until="networkidle")
        pg.wait_for_timeout(1000)
        pt = pg.evaluate("""() => { const a = document.querySelector('.app-main article').getBoundingClientRect();
                                     return {x: a.left + 6, y: innerHeight / 2}; }""")
        if pg.locator(".reader-chrome[data-shown]").count() == 0:
            (pg.touchscreen.tap if touch else pg.mouse.click)(pt["x"], pt["y"]); pg.wait_for_timeout(400)
        aa = pg.locator("[data-reader-action=aa]")
        aa.tap() if touch else aa.click()
        pg.wait_for_timeout(600)
        m = pg.evaluate("""() => {
            const el = document.querySelector('.reader-panel .lang-field-value');
            if (!el) return null;
            const r = document.createRange(); r.selectNodeContents(el);
            const t = r.getBoundingClientRect(), b = el.getBoundingClientRect(), cs = getComputedStyle(el);
            return {text: el.textContent.trim(), textTop: t.top, textBottom: t.bottom, boxTop: b.top, boxBottom: b.bottom,
                    lh: parseFloat(cs.lineHeight), fs: parseFloat(cs.fontSize), clip: cs.overflow}; }""")
        if not m:
            check(dev, "a language field found in the «Аа» panel", False, "no .reader-panel .lang-field-value")
            br.close()
            continue
        check(dev, f"a «{m['text']}»: font box inside the clipping box (bottom {m['textBottom']:.1f} <= {m['boxBottom']:.1f}, "
                   f"top {m['textTop']:.1f} >= {m['boxTop']:.1f})",
              m["textBottom"] <= m["boxBottom"] + 0.5 and m["textTop"] >= m["boxTop"] - 0.5, m)
        check(dev, f"b line-height {m['lh']:.1f}px >= 1.3 x {m['fs']:.0f}px  # tehniskais slieksnis Lipikāra, nav S noteikums",
              m["lh"] >= 1.3 * m["fs"] - 0.01, m)
        if SHOTS:
            os.makedirs(SHOTS, exist_ok=True)
            pg.locator(".reader-panel .lang-field").screenshot(path=os.path.join(SHOTS, f"{dev}_lang-field.png"))
        ctx.close()
        br.close()
print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
