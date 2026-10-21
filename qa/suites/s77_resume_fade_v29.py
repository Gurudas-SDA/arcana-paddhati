"""V29 — «Продолжить чтение»: the right page opens with a soft quick fade, no jerk (Vraja Lila msg 5783, 21.10.2026;
saskarnes autors, «Стандарты» 0а; video not downloaded — the criterion follows the text).

Rule text (verbatim, Vraja Lila): «при продолжении чтения, когда книга отводит в нужный раздел появляется дёргание…
сделай так чтобы нужная страница открылась с мягким быстрым fade».
Criterion (Lipikāra, Vraja's words): after a tap on «Продолжить» the reader never sees the page jump — while the target
page is visible at all, the place being returned to stays where it ends; the page appears with a short fade;
prefers-reduced-motion → no animation (the page appears at once, already at its place).
  # tehniskais slieksnis Lipikāra, nav S noteikums: «short fade» = from first visible (opacity > 0.02) to full
  #   (≥ 0.99) 100–450 ms with at least one in-between frame (the CSS fade is 200 ms; a loaded test server
#   stretches frames — measured up to 371 ms); «stays» = the returned block's top within 2 px of its
  #   final place in every visible frame; sampled every animation frame for 2.5 s after the tap.
usage: python s77_resume_fade_v29.py <base-url>
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
CASES = [("vigraha-tattva", 24, 0), ("worship-sixteen-articles", 12, 0)]
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:900]}", flush=True)


SAMPLER = """([section, block]) => { window.__fs = []; const t0 = performance.now(); let on = true;
  const tick = () => { if (!on) return; const m = document.querySelector('.app-main');
    let top = null; const path = location.pathname;
    if (m && path.includes('/' + section + '/')) { const bl = m.querySelectorAll('article :is(h1,h2,h3,h4,p)')[block];
      if (bl) top = +(bl.getBoundingClientRect().top - m.getBoundingClientRect().top).toFixed(1); }
    const op = m ? +getComputedStyle(m).opacity : 1;
    window.__fs.push([+(performance.now() - t0).toFixed(1), path.includes('/' + section + '/') ? 1 : 0, op, top]);
    requestAnimationFrame(tick); };
  requestAnimationFrame(tick); window.__fsStop = () => { on = false; }; }"""

with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        for reduce in (False, True):
            for section, block, offset in CASES:
                tag = f"{section}{' (reduced motion)' if reduce else ''}"
                place = dict(v=1, section=section, anchor=None, block=block, offset=offset, lang="ru-iast", time=int(time.time() * 1000))
                c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce" if reduce else "no-preference", **opts)
                c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');"
                                  "localStorage.setItem('ap.offlineSave', %s);localStorage.setItem('ap.readingPlace', %s);"
                                  % (json.dumps(json.dumps({"s": "seen"})), json.dumps(json.dumps(place))))
                pg = c.new_page()
                pg.goto(f"{BASE}/ru-iast/", wait_until="networkidle")
                pg.wait_for_timeout(900)
                a = pg.locator("a.home-resume")
                if a.count() != 1:
                    check(dev, f"{tag}: «Продолжить» card on the cover", False, "no card")
                    c.close()
                    continue
                pg.evaluate(SAMPLER, [section, block])
                if opts.get("has_touch"):
                    a.tap()
                else:
                    a.click()
                pg.wait_for_timeout(2500)
                fs = pg.evaluate("window.__fsStop(), window.__fs")
                on_page = [f for f in fs if f[1] and f[3] is not None]
                if not on_page:
                    check(dev, f"{tag}: the target page opened", False, fs[-5:])
                    c.close()
                    continue
                final = on_page[-1][3]
                visible = [f for f in on_page if f[2] > 0.02]
                jumps = [f for f in visible if abs(f[3] - final) > 2]
                check(dev, f"{tag}: no jerk — while the page is visible the place stays put (final top {final})",
                      not jumps and abs(final - offset) <= 3, {"jumps": jumps[:6], "final": final, "want": offset})
                mids = [f for f in visible if f[2] < 0.99]
                first = visible[0][0] if visible else None
                full = next((f[0] for f in visible if f[2] >= 0.99), None)
                if reduce:
                    check(dev, f"{tag}: no animation — the page appears at once, fully",
                          not mids and full is not None, {"mids": mids[:6], "full": full})
                else:
                    dur = None if first is None or full is None else round(full - first, 1)
                    check(dev, f"{tag}: soft quick fade (100–450 ms, in-between frames)",
                          dur is not None and 100 <= dur <= 450 and len(mids) >= 1, {"dur": dur, "mids": len(mids), "sample": mids[:4]})
                check(dev, f"{tag}: the page ends fully visible", fs[-1][2] >= 0.99, fs[-1])
                c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
