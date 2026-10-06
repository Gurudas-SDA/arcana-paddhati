"""Nothing of the book text runs off the right edge of a phone (Satkirti 06.10 KSV: the «Гуру-пурнима»
card of the festivals table on Pixel 7 / S23 FE 360 px — «полнолуние месяца Ашадха» went out to the
right). Checked on EVERY chapter page (КСВ: the whole book, not only the found place), at the normal
and the largest «Аа» text size: every element inside the reading column must end inside the screen,
unless it sits in a box that is meant to scroll sideways (overflow-x: auto/scroll — the wide table).
Elements hidden by an overflow:hidden parent count as overflowing (the text is cut off = not readable).
usage: python s13_cards_no_overflow.py <base-url>   devices: QA_DEVICES
full: RU books every page + other languages' pages with tables; QA_FAST=1: RU pages with tables + 4 others"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
ZOOMS = ["1", "1.35"]  # normal and the largest «Аа» step (lib/readerPrefs.ts SIZES)
res = []


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else info}", flush=True)


def pages():
    """(lang dir, section id, has a table block) for the books under test."""
    out = []
    langs = ["ru-iast", "ru"] if qa.fast() else ["ru-iast", "ru", "", "lv", "de", "fr", "es", "it", "uk", "hu"]
    for lang in langs:
        fn = os.path.join(qa.DATA, f"book.{lang}.json" if lang else "book.json")
        b = json.load(open(fn, encoding="utf-8"))
        for s in b["sections"]:
            txt = json.dumps(s, ensure_ascii=False)
            out.append((lang, s["id"], '"type": "table"' in txt))
    if qa.fast():
        tables = [p for p in out if p[2]]
        others = [p for p in out if not p[2] and p[0] == "ru-iast"][::6][:4]
        out = tables + others
    else:
        # all pages of Satkirti's RU books; in the other languages the pages with tables (cards on phones)
        out = [p for p in out if p[0] in ("ru-iast", "ru") or p[2]]
    return out


JS = """() => {
  const W = document.documentElement.clientWidth;
  const root = document.querySelector('.app-main article') || document.querySelector('.app-main');
  if (!root) return {W, n: -1, items: []};
  const bad = [];
  for (const e of root.querySelectorAll('*')) {
    const r = e.getBoundingClientRect();
    if (r.width === 0 || r.height === 0 || r.right <= W + 1) continue;
    const cs = getComputedStyle(e);
    if (cs.visibility === 'hidden' || cs.position === 'fixed') continue;
    let p = e.parentElement, scroller = false;
    while (p && p !== document.body) {
      const ox = getComputedStyle(p).overflowX;
      if ((ox === 'auto' || ox === 'scroll') && p.scrollWidth > p.clientWidth + 1 && !p.classList.contains('app-main')) { scroller = true; break; }
      p = p.parentElement;
    }
    if (scroller) continue;
    // report the innermost overflowing element only
    if ([...e.children].some(ch => ch.getBoundingClientRect().right > W + 1)) continue;
    bad.push({tag: e.tagName, right: Math.round(r.right), txt: (e.innerText || e.textContent || '').trim().slice(0, 50)});
  }
  return {W, n: bad.length, items: bad.slice(0, 4)};
}"""


def run(p, dev, eng, o, plist):
    b = getattr(p, eng).launch()
    for z in ZOOMS:
        c = b.new_context(locale="ru-RU", service_workers="block", **o)
        c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('ap.readerSize','%s')}catch(e){}" % z)
        pg = c.new_page()
        for lang, sid, has_table in plist:
            url = f"{BASE}/{lang + '/' if lang else ''}{sid}/"
            try:
                pg.goto(url, wait_until="load")
                pg.wait_for_timeout(500)
                r = pg.evaluate(JS)
                where = f"{lang or 'en'}/{sid}"
                chk(dev, f"§5 текст и карточки не выходят за правый край ({where}, «Аа» ×{z})",
                    r["n"] == 0, f"ширина {r['W']}px; {r['n']} эл.: {r['items']}")
            except Exception as e:
                chk(dev, f"§5 текст и карточки не выходят за правый край ({lang}/{sid}, «Аа» ×{z})", False, "ERR " + str(e)[:160])
        c.close()
    b.close()


with sync_playwright() as p:
    plist = pages()
    for dev, eng, o in qa.devices(["s23fe", "pixel7", "iphone-se", "iphone14"]):
        print(dev, flush=True)
        run(p, dev, eng, o, plist)

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
