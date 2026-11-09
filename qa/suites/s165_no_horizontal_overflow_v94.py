"""V94 — Vraja Lila msg 7952 (09.11.2026, verbatim): «на телефоне иной раз ширина не фиксирована, юзер почему-то может мотать страницу вбок...
за пределы ширины».
Criteria (Vraja's words, task V94 c): on a phone the width of the page is fixed — the reader CANNOT drag a page sideways beyond the screen's width.
For EVERY page of the book (the cover, every chapter, in both languages, in both layouts) on the phones (Pixel 7, Samsung S23 FE, iPhone 14):
 (1) the document is not wider than the screen (documentElement.scrollWidth <= clientWidth) and the reading area (.app-main) has no horizontal scroll
     (scrollWidth <= clientWidth); window.scrollX stays 0 after a sideways scroll attempt (the content itself must fit: a hidden-overflow area could still be moved by script, so the content width is what is checked);
 (2) no element sticks out past the screen's right edge unless something between it and the page clips it (an own horizontal scroller of a table
     is allowed: overflow-x auto/scroll/hidden/clip on an ancestor that itself lies inside the screen). The offenders are printed (tag, class, text).
# tehniskais slieksnis Lipikāra, nav S noteikums: 1 px tolerance for rounding (> vw + 1); closed drawers (.mobile-menu without data-open) and elements
# that are not rendered are not checked.
usage: python s165_no_horizontal_overflow_v94.py <base-url> [device ...]   (env S165_ONLY=<chapter id>)
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEV_NAMES = [a for a in sys.argv[2:] if a in qa.DEVICES] or ["pixel7", "s23fe", "iphone14"]
ONLY = os.environ.get("S165_ONLY")
results = []

MEASURE = """() => {
  const vw = document.documentElement.clientWidth; const m = document.querySelector('.app-main');
  const before = window.scrollX; window.scrollTo(60, 0); const sx = window.scrollX; window.scrollTo(0, 0);
  let mx = 0; if (m) { m.scrollLeft = 60; mx = m.scrollLeft; m.scrollLeft = 0; }
  const clip = (cs) => ['auto', 'scroll', 'hidden', 'clip'].includes(cs.overflowX);
  const off = [];
  for (const e of document.body.querySelectorAll('*')) {
    if (off.length >= 12) break;
    const tn = e.tagName; if (tn === 'SCRIPT' || tn === 'STYLE' || tn === 'NOSCRIPT' || tn === 'HEAD') continue;
    const mm = e.closest('.mobile-menu'); if (mm && !mm.hasAttribute('data-open')) continue;
    const b = e.getBoundingClientRect(); const cs = getComputedStyle(e);
    // reach = the right edge of the element's box or of its own overflowing content (a nowrap / unbreakable line wider than its box)
    const reach = Math.max(b.right, clip(cs) ? 0 : b.left + e.scrollWidth);
    if (b.width === 0 || b.height === 0 || reach <= vw + 1) continue; if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    // a clipping ancestor that lies inside the screen contains it
    let contained = false;
    for (let a = e.parentElement; a && a !== document.documentElement; a = a.parentElement) {
      if (a === m) break;   // the reading area itself scrolls sideways when something is wider: it does not contain
      const ac = getComputedStyle(a); if (a === document.body && !clip(ac)) continue;
      if (clip(ac) && a.getBoundingClientRect().right <= vw + 1) { contained = true; break; }
      if (ac.display === 'none') { contained = true; break; }
    }
    if (contained) continue;
    off.push({tag: tn.toLowerCase(), cls: (e.getAttribute('class') || '').slice(0, 60), right: Math.round(reach), w: Math.round(b.width), text: (e.textContent || '').trim().slice(0, 50)});
  }
  return {vw, docSW: document.documentElement.scrollWidth, bodySW: document.body.scrollWidth, mainSW: m ? m.scrollWidth : null, mainCW: m ? m.clientWidth : null,
          sx, mx, off, before};
}"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    if not ok:
        print(f"  [FAIL] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


def pages(lang):
    f = {"en": "book.json", "ru-iast": "book.ru-iast.json"}[lang]
    d = json.load(open(os.path.join(qa.DATA, f), encoding="utf-8"))
    ids = [s["id"] for s in d["sections"]]
    if ONLY:
        ids = [i for i in ids if i == ONLY]
    return ([""] if not ONLY else []) + ids


ZOOMS = ["1", "1.35"]   # the «Аа» steps: normal and the largest (lib/readerPrefs.ts SIZES)


def run(p, dev, lang, mode, zoom):
    eng, opts = qa.DEVICES[dev]
    b = getattr(p, eng).launch()
    c = b.new_context(service_workers="block", locale="ru-RU" if lang == "ru-iast" else "en-US", reduced_motion="reduce", **opts)
    c.add_init_script("try{localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('ap.readerLayout','%s');localStorage.setItem('ap.readerSize','%s');}catch(e){}" % (mode, zoom))
    pg = c.new_page()
    tag = f"{dev}/{lang}/{mode}/zoom{zoom}"
    bad = 0
    # one page-load per chapter in the page layout; in the scroll layout the whole book is one page, so it is measured once per chapter route
    # (every route renders the same book) at its start and then the whole book at once
    for pid in pages(lang):
        pg.goto(f"{BASE}{qa.lang_prefix(lang)}/{pid + '/' if pid else ''}", wait_until="networkidle")
        pg.wait_for_function("!!document.querySelector('.app-main')", timeout=20000)
        pg.wait_for_timeout(900)
        r = pg.evaluate(MEASURE)
        ok = (r["docSW"] <= r["vw"] and (r["mainSW"] is None or r["mainSW"] <= r["mainCW"]) and r["sx"] == 0 and not r["off"])
        check(tag, f"{pid or 'cover'}: width is fixed", ok, r)
        bad += 0 if ok else 1
        if mode == "scroll" and pid:   # the whole book is in this page: a second chapter route adds nothing but time
            break
    print(f"  [{'PASS' if not bad else 'FAIL'}] {tag}: {bad} pages wider than the screen", flush=True)
    b.close()


with sync_playwright() as p:
    for dev in DEV_NAMES:
        for lang in qa.ACTIVE_LANGS:
            for mode in ("page", "scroll"):
              for zoom in ZOOMS:
                try:
                    run(p, dev, lang, mode, zoom)
                except Exception as e:  # noqa: BLE001
                    results.append(False)
                    print(f"  [FAIL] {dev}/{lang}/{mode}/{zoom}: exception {type(e).__name__}: {str(e)[:300]}", flush=True)

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
