"""V65 — switching the language keeps the reading place: the same chapter, the same subsection, the same place in it.
Vraja Lila msg 7218 (01.11.2026), literally: «заметил что читая на одном языке при переключении на другой книга
откидывает тебя в совершенно другой раздел, а должна оставаться на том же месте и просто сменить язык».
Criteria (register V65): (1) after the language is changed through the «Аа» menu the same chapter / subsection / place
is open (the text block at the top of the screen = the same block of the chapter); (2) both languages of the book
(en, ru-iast), both directions, «Листать» and «Прокручивать», phone and desktop; (3) a place deep in a long chapter
stays there, it does not go to the start.
# tehniskais slieksnis Lipikāra, nav S noteikums: place = the text block at the top of the screen; block index must be equal (+-1
# for a block cut by the screen edge); settle 1800 ms.
usage: python s133_lang_switch_keeps_place_v65.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["pixel7", "iphone14", "desktop"])
LANGS = ["en", "ru-iast"]
CHAPTERS = ["offering-bhoga", "mangala-arati-songs", "gaura-arati-songs"]
FRACTIONS = [0.35, 0.8]   # a place in the middle and deep in the chapter
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:900]}", flush=True)


# the place: chapter (URL), subsection at the reading line, index of the text block at the line, how many blocks
PLACE = """() => { const m = document.querySelector('.app-main'); const mr = m.getBoundingClientRect();
  const line = mr.top + 4;   // the text block at the top of the screen, as the app itself takes a place (lib/readingMode.ts)
  const book = m.querySelector('[data-continuous-book]');
  const id = decodeURIComponent(location.pathname.split('/').filter(Boolean).at(-1) || '');
  const root = book ? book.querySelector('[data-book-section="' + CSS.escape(id) + '"]') : m;
  if (!root) return {url: id, lang: document.documentElement.lang, none: true};
  const blocks = [...root.querySelectorAll('article :is(h1,h2,h3,h4,p)')];
  let idx = -1;
  for (let i = 0; i < blocks.length; i++) { const r = blocks[i].getBoundingClientRect();
    if (r.height && r.bottom > line) { idx = i; break; } }
  const own = idx >= 0 ? blocks[idx].closest('section[id]') : null;
  const sub = own ? own.id : null;
  return {url: id, lang: location.pathname.split('/').filter(Boolean)[1] ? location.pathname.split('/').filter(Boolean)[1] : '',
    idx, n: blocks.length, sub, top: Math.round(m.scrollTop), text: idx >= 0 ? blocks[idx].innerText.trim().slice(0, 30) : null}; }"""


def lang_of(path):
    parts = [x for x in path.split("/") if x]
    parts = parts[1:] if parts and parts[0] == "arcana-paddhati" else parts
    return parts[0] if parts and parts[0] in LANGS else "en"


def scroll_to(pg, fraction):
    pg.evaluate("""f => { const m = document.querySelector('.app-main');
      const book = m.querySelector('[data-continuous-book]');
      const id = decodeURIComponent(location.pathname.split('/').filter(Boolean).at(-1) || '');
      const sec = book ? book.querySelector('[data-book-section="' + CSS.escape(id) + '"]') : m;
      const start = sec === m ? 0 : m.scrollTop + sec.getBoundingClientRect().top - m.getBoundingClientRect().top;
      const h = sec === m ? m.scrollHeight - m.clientHeight : sec.scrollHeight - m.clientHeight;
      m.scrollTop = start + Math.max(0, h) * f; m.dispatchEvent(new Event('scroll')); }""", fraction)
    pg.wait_for_timeout(1800)


def switch_lang(pg, touch, to):
    if pg.locator(".reader-chrome[data-shown]").count() == 0:
        pt = pg.evaluate("""() => { const a = document.querySelector('.app-main article').getBoundingClientRect();
                                     return {x: a.left + 6, y: innerHeight / 2}; }""")
        (pg.touchscreen.tap if touch else pg.mouse.click)(pt["x"], pt["y"])
        pg.wait_for_timeout(400)
    aa = pg.locator("[data-reader-action=aa]")
    aa.tap() if touch else aa.click()
    pg.wait_for_timeout(500)
    lt = pg.locator(".reader-panel [data-lang-trigger]")
    lt.tap() if touch else lt.click()
    pg.wait_for_timeout(400)
    opt = pg.locator(f"[role=listbox] [role=option][data-lang={to}]")
    opt.tap() if touch else opt.click()
    pg.wait_for_function(f"() => location.pathname.split('/').filter(Boolean).includes('{to}') || '{to}' === 'en' && !location.pathname.includes('/ru-iast/')", timeout=15000)
    pg.wait_for_timeout(2500)


def href(lang, chap):
    return f"{BASE}/{chap}/" if lang == "en" else f"{BASE}/{lang}/{chap}/"


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        touch = bool(opts.get("has_touch"))
        b = getattr(p, eng).launch()
        for layout in ("pages", "scroll"):
            for chap in CHAPTERS:
                for frac in FRACTIONS:
                    for src in LANGS:
                        dst = LANGS[1 - LANGS.index(src)]
                        tag = f"{layout} {chap} @{int(frac * 100)}% {src}->{dst}"
                        try:
                            c = b.new_context(service_workers="block", locale="ru-RU", **opts)
                            c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');"
                                              f"{'localStorage.setItem(\"ap.readerLayout\",\"scroll\");' if layout == 'scroll' else ''}}}catch(e){{}}")
                            pg = c.new_page()
                            pg.goto(href(src, chap), wait_until="networkidle")
                            if layout == "scroll":
                                pg.wait_for_selector("[data-continuous-book]", state="attached", timeout=30000)
                                qa.wait_for_book_chapter(pg, chap)
                            pg.wait_for_timeout(1000)
                            scroll_to(pg, frac)
                            a = pg.evaluate(f"({PLACE})()")
                            switch_lang(pg, touch, dst)
                            if layout == "scroll":
                                qa.wait_for_book_chapter(pg, chap)
                            pg.wait_for_timeout(1500)
                            z = pg.evaluate(f"({PLACE})()")
                            now = lang_of(pg.evaluate("location.pathname"))
                            ok = (not a.get("none") and not z.get("none") and now == dst and z["url"] == chap
                                  and a["sub"] == z["sub"] and a["idx"] >= 0 and abs(a["idx"] - z["idx"]) <= 1)
                            check(dev, tag, ok, {"before": a, "after": z, "lang_now": now})
                            c.close()
                        except Exception as e:  # noqa: BLE001
                            check(dev, tag, False, f"error: {e}")
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
