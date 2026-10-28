"""V60 — turning the phone (portrait -> landscape -> portrait) in the middle of a bhajan keeps the chapter and the place
(Vraja Lila 28.10.2026 18:23, msg 6949, as passed on by Satkirti; Android: «при повороте экрана в горизонталь во время
чтения бхаджана текст сам перескакивает к другой главе»; iPhone does not do it).
Criteria (register V60): the same chapter (URL) and the same reading place (the same text block at the reading line)
after the turn and after turning back; «Листать» and «Прокручивать».
# tehniskais slieksnis Lipikāra, nav S noteikums: same block text; settle 1500 ms; place measured at 20 % of the viewport height.
usage: python s100_rotation_keeps_place_v60.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["pixel7", "iphone14"])
LANG = "ru-iast"
CHAPTERS = ["mangala-arati-songs", "gaura-arati-songs"]
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:900]}", flush=True)


PLACE = """() => { const m = document.querySelector('.app-main'); const r = m.getBoundingClientRect();
  const line = r.top + m.clientHeight * 0.2;
  let b = document.elementsFromPoint(r.left + r.width / 2, line).find(e => m.contains(e) && e.closest('article')
    && !e.matches('article, section, [data-book-section], .continuous-book, .app-main'));
  while (b && (b.innerText || '').trim().length < 12 && b.parentElement && !b.parentElement.matches('article, section, [data-book-section]')) b = b.parentElement;
  const sec = b && b.closest('[data-book-section]');
  return {url: location.pathname.split('/').filter(Boolean).at(-1), section: sec ? sec.dataset.bookSection : null,
    text: b ? b.innerText.trim().slice(0, 40) : null, top: Math.round(m.scrollTop), vp: [innerWidth, innerHeight]}; }"""


def mid_scroll(pg, scroll):
    pg.evaluate("""() => { const m = document.querySelector('.app-main');
      const sec = document.querySelector('[data-reader-current]') || m;
      const start = sec === m ? 0 : m.scrollTop + sec.getBoundingClientRect().top - m.getBoundingClientRect().top;
      const h = sec === m ? m.scrollHeight - m.clientHeight : sec.scrollHeight - m.clientHeight;
      m.scrollTop = start + Math.max(0, h) * 0.5; m.dispatchEvent(new Event('scroll')); }""")
    pg.wait_for_timeout(1200)


def turn(pg):
    v = pg.viewport_size
    pg.set_viewport_size({"width": v["height"], "height": v["width"]})
    pg.wait_for_timeout(1500)


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        for layout in ("pages", "scroll"):
            for chap in CHAPTERS:
                c = b.new_context(service_workers="block", locale="ru-RU", **opts)
                c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');"
                                  f"{'localStorage.setItem(\"ap.readerLayout\",\"scroll\");' if layout == 'scroll' else ''}}}catch(e){{}}")
                pg = c.new_page()
                pg.goto(f"{BASE}/{LANG}/{chap}/", wait_until="networkidle")
                if layout == "scroll":
                    pg.wait_for_selector("[data-continuous-book]", state="attached", timeout=30000)
                    qa.wait_for_book_chapter(pg, chap)
                pg.wait_for_timeout(1000)
                mid_scroll(pg, layout == "scroll")
                a = pg.evaluate(f"({PLACE})()")
                turn(pg)
                l = pg.evaluate(f"({PLACE})()")
                turn(pg)
                r = pg.evaluate(f"({PLACE})()")
                # place: the same text block (±1) at the reading line
                same = lambda x: a["text"] and x["url"] == chap and (x["section"] in (None, chap)) and x["text"] == a["text"]
                check(dev, f"{layout} {chap}: portrait -> landscape keeps chapter and place", same(l), {"before": a, "landscape": l})
                check(dev, f"{layout} {chap}: back to portrait keeps chapter and place", same(r), {"before": a, "back": r})
                c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
