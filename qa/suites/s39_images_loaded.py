"""Every picture actually loads (Satkirti КСВ 14.10.2026: «после загрузки книги картинки не загрузились»).

Opens the cover and a picture-heavy chapter, scrolls the reader from top to bottom (the
whole document, so lazily rendered parts get their turn), waits for the network to settle
and then requires every <img> in the document to be complete with naturalWidth > 0.
Repeats once after a reload. usage: python s39_images_loaded.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
PAGES = ["", "daily-duties-brahma-muhurta/", "gaudiya-emblem/"]
DEVICES = qa.devices(["ipad-portrait", "iphone14", "pixel7"])
results = []

SCROLL_STEP = """() => { const m = document.querySelector('.app-main');
  const s = m && m.scrollHeight > m.clientHeight + 4 ? m : document.scrollingElement;
  const before = s.scrollTop; s.scrollTop = before + s.clientHeight * 0.9;
  return {top: s.scrollTop, max: s.scrollHeight - s.clientHeight, moved: s.scrollTop !== before}; }"""
TO_TOP = """() => { const m = document.querySelector('.app-main'); if (m) m.scrollTop = 0; document.scrollingElement.scrollTop = 0; }"""
BROKEN = """() => { const all = [...document.querySelectorAll('img')];
  const bad = all.filter(i => !(i.complete && i.naturalWidth > 0)).map(i => (i.currentSrc || i.src || '(no src)').replace(location.origin, ''));
  return {total: all.length, bad: [...new Set(bad)]}; }"""


def check(dev, name, ok, evidence):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


def settle(pg, ms=1500):
    try:
        pg.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    pg.wait_for_timeout(ms)


def walk(pg):
    """Scroll the reader to the end in screen steps; return the number of steps."""
    steps = 0
    for _ in range(4000):
        st = pg.evaluate(SCROLL_STEP)
        steps += 1
        pg.wait_for_timeout(40)
        if not st["moved"] or st["top"] >= st["max"] - 2:
            break
    pg.evaluate(TO_TOP)
    return steps


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        print(dev, flush=True)
        br = getattr(p, eng).launch()
        try:
            ctx = br.new_context(service_workers="block", **opts)
            ctx.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
            pg = ctx.new_page()
            for path in PAGES:
                label = path.rstrip("/") or "cover"
                pg.goto(f"{BASE}/ru-iast/{path}", wait_until="domcontentloaded")
                settle(pg)
                steps = walk(pg)
                settle(pg)
                r = pg.evaluate(BROKEN)
                check(dev, f"{label}: every <img> loaded after load + scroll", r["total"] > 0 and not r["bad"],
                      {"imgs": r["total"], "not_loaded": len(r["bad"]), "examples": r["bad"][:5], "scroll_steps": steps})
                pg.reload(wait_until="domcontentloaded")
                settle(pg)
                walk(pg)
                settle(pg)
                r = pg.evaluate(BROKEN)
                check(dev, f"{label}: every <img> loaded after reload + scroll", r["total"] > 0 and not r["bad"],
                      {"imgs": r["total"], "not_loaded": len(r["bad"]), "examples": r["bad"][:5]})
            ctx.close()
        except Exception as e:
            check(dev, "EXCEPTION", False, str(e)[:600])
        br.close()

fails = [r for r in results if not r]
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
