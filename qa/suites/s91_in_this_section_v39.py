"""V39 — «В этом разделе» under a section's page (Vraja Lila msg 1324 / 1326, 22.10.2026 01:37–01:41, variant Б; and
msg 6090: every section built the same way; saskarnes autors, «Стандарты» 0а).

Problem (as passed on — nodots-izpildei 22.10 01:40, verbatim): «под текстом раздела — список глав … „кликабельные, но
 непонятно, что их можно кликать, и как с ними поступить“».
Chosen (verbatim): «✅ ВАРИАНТ Б — блок «В этом разделе» (заголовок + строки глав со ›, как в боковом меню), ПОСЛЕ
 перечисления внизу — линия-разделитель (сепаратор), потом следующий текст; в «Ленте» не показывать».
Criteria (verbatim): «1) видно, что строки — ссылки; 2) разделитель после списка; 3) в Ленте блока нет».
Addition (Vraja Lila msg 6090, passed on by Lipikāra, verbatim): «так же в подобных случаях впредь и в разделах, которые
 структурированы так же» — the block for EVERY section whose page lists its chapters (a general component), not only
 the Introduction; checked on ≥ 2 sections.
 Change (Vraja Lila msg 6096, 22.10.2026, passed on by Lipikāra, verbatim): «может таки положить „В этом разделе“ в
 бокс… по цвету светлозолотистый как тот цвет, с которым ты чередуешь белый в таблицах (см. пример)… форма и ширина
 такая же, только высота во весь список с отступами от краёв; тогда сепаратор не нужен будет; строки как и говорили со
 стрелкой».
 Sample (Vraja Lila msg 6097 «вот пример бокса, его ширины и скругления краёв», msg 6098 «и цвета»): the even (banded)
 row «2) Bhagavān’s six opulences at the points of the yantra» of a numbered list (.hs-row / .pl-row band).
 # tehniskais slieksnis Lipikāra, nav S noteikums: a row is a link when it is an <a href> to the chapter, ≥ 44 px high,
 # with the › arrow at its right end (right of the title); «бокс» = the block's own background equals the tables'
 # alternating band (--rd-row-stripe, as an even .pl-row/.hs-row paints it), radius 4 px like the band, the width of the
 # text column, every row inside it with ≥ 6 px inner margin; no separator line in or after the block.

Checks, per device, on the Introduction (own text + its chapters) and on the parts' pages with chapters
(«Храмовый стандарт», «Праздники, обеты и песни арати») — «Страницы»:
  A  the block is there with its heading «В этом разделе», one row per chapter of the section, in the contents' order;
  B  every row is a link to its chapter, ≥ 44 px, its › at the right of the title;
  C  the block is a box: background = the tables' alternating band colour, radius = the band's, the text column's
     width, the heading and all rows inside it with inner margins; no separator (msg 6096);
  D  a tap on a row opens that chapter;
  E  «Лента»: no such block in the book (the Introduction and the parts).
usage: python s91_in_this_section_v39.py <base-url>
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
LANG = "ru-iast"
HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = json.load(open(os.path.join(HERE, "..", "..", "data", f"book.{LANG}.json"), encoding="utf-8"))
# = lib/book.ts frontGroup(): the sections BEFORE the first chapter of a part («Заключение» after the parts is not a
# chapter of the Introduction)
_IN_PART = {i for p in BOOK["parts"] for i in p["sections"]}
FRONT = []
for _s in BOOK["sections"]:
    if _s["id"] in _IN_PART:
        break
    FRONT.append(_s["id"])
INTRO = "introduction"
# Sections whose page lists chapters: the Introduction (chapters = the front matter after it) and each part with chapters.
CASES = [(INTRO, FRONT[FRONT.index(INTRO) + 1:])] + [(p["id"], p["sections"]) for p in BOOK["parts"] if p["sections"]]
TITLES = {s["id"]: s["title"] for s in BOOK["sections"]}
results = []

BLOCK = """() => { const root = document.querySelector('.app-main [data-reader-current]') || document.querySelector('.app-main');
  const navs = [...root.querySelectorAll('nav')].filter((n) => /В этом разделе/.test(n.textContent) || n.matches('[data-section-chapters]'));
  const nav = navs[0]; if (!nav) return {found: false, navs: 0};
  const head = [...nav.querySelectorAll('p,h2,h3,h4')].map((e) => e.textContent.trim()).find(Boolean) || '';
  const rows = [...nav.querySelectorAll('li')].map((li) => { const a = li.querySelector('a[href]'); const r = (a || li).getBoundingClientRect();
    const svg = a && a.querySelector('svg'); const sr = svg && svg.getBoundingClientRect();
    const name = a && [...a.childNodes].map((n) => n.textContent).join('').trim();
    const txt = a && (a.querySelector('span') || a); const tr = txt && txt.getBoundingClientRect();
    return {href: a ? a.getAttribute('href') : null, text: name, h: Math.round(r.height),
            arrowRight: !!(sr && tr) && sr.left >= tr.right - 1 && sr.right <= r.right + 1 && sr.right >= r.right - 24}; });
  const cs = getComputedStyle(nav); const nr = nav.getBoundingClientRect();
  const probe = document.createElement('div'); probe.style.background = 'var(--rd-row-stripe)'; nav.parentElement.appendChild(probe);
  const stripe = getComputedStyle(probe).backgroundColor; probe.remove();
  const pcs = getComputedStyle(nav.parentElement);
  const col = {width: nav.parentElement.clientWidth - (parseFloat(pcs.paddingLeft) || 0) - (parseFloat(pcs.paddingRight) || 0)};
  const inner = [...nav.querySelectorAll('li a, p')].map((e) => e.getBoundingClientRect());
  const pad = inner.length ? Math.min(...inner.map((r) => Math.min(r.left - nr.left, nr.right - r.right))) : -1;
  const vpad = inner.length ? Math.min(inner[0].top - nr.top, nr.bottom - inner[inner.length - 1].bottom) : -1;
  const seps = [...nav.querySelectorAll('hr, [data-section-chapters-sep]')].length
    + (nav.nextElementSibling && nav.nextElementSibling.matches('hr') ? 1 : 0)
    + ((parseFloat(cs.borderBottomWidth) || 0) > 0 && cs.borderBottomStyle !== 'none' && cs.borderBottomColor !== 'rgba(0, 0, 0, 0)' ? 1 : 0);
  const box = {bg: cs.backgroundColor, stripe, radius: cs.borderTopLeftRadius, width: Math.round(nr.width), column: Math.round(col.width),
               pad: Math.round(pad), vpad: Math.round(vpad), seps};
  return {found: true, navs: navs.length, head, rows, box}; }"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


def run(browser, dev, opts):
    touch = opts.get("has_touch", False)
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true')}catch(e){}")
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        for sid, kids in CASES:
            pg.goto(f"{BASE}/{LANG}/{sid}/", wait_until="networkidle")
            pg.wait_for_timeout(1000)
            b = pg.evaluate(BLOCK)
            hrefs = [(r["href"] or "").rstrip("/").split("/")[-1] for r in b.get("rows", [])]
            check(dev, f"A «{sid}»: block «В этом разделе», a row per chapter in order",
                  b["found"] and b["head"] == "В этом разделе" and hrefs == kids, {"head": b.get("head"), "hrefs": hrefs, "want": kids})
            rows = b.get("rows", [])
            check(dev, f"B «{sid}»: every row a link to its chapter, ≥ 44 px, › at its right",
                  bool(rows) and all(r["href"] and r["h"] >= 44 and r["arrowRight"] for r in rows)
                  and all(TITLES[k] in (r["text"] or "") for k, r in zip(kids, rows)), rows)
            bx = b.get("box") or {}
            check(dev, f"C «{sid}»: a box in the tables' band colour, their shape and width, inner margins, no separator",
                  b["found"] and bx.get("bg") == bx.get("stripe") and bx.get("bg") not in (None, "rgba(0, 0, 0, 0)") and bx.get("radius") == "4px"
                  and abs(bx.get("width", 0) - bx.get("column", -9)) <= 2 and bx.get("pad", -1) >= 6 and bx.get("vpad", -1) >= 4 and bx.get("seps") == 0, bx)
            if rows and rows[0]["href"]:
                link = pg.locator(f".app-main a[href='{rows[0]['href']}']").first
                link.scroll_into_view_if_needed()
                (link.tap if touch else link.click)()
                for _ in range(40):
                    pg.wait_for_timeout(150)
                    if pg.url.rstrip("/").endswith("/" + kids[0]):
                        break
                pg.wait_for_timeout(500)
                check(dev, f"D «{sid}»: a tap on the first row opens «{kids[0]}»", pg.url.rstrip("/").endswith("/" + kids[0]), pg.url)

        # E — «Лента»: no block anywhere in the book
        pg.evaluate("try{localStorage.setItem('ap.readerLayout','scroll')}catch(e){}")
        pg.goto(f"{BASE}/{LANG}/{INTRO}/", wait_until="networkidle")
        pg.wait_for_selector("[data-continuous-book]", state="attached", timeout=30000)
        qa.wait_for_book_chapter(pg, INTRO)
        pg.wait_for_timeout(900)
        found = pg.evaluate("""(ids) => { const book = document.querySelector('[data-continuous-book]'); if (!book) return 'no book';
          return ids.map((id) => { const s = book.querySelector(`[data-book-section="${id}"]`);
            return [id, !!s && ([...s.querySelectorAll('nav')].some((n) => /В этом разделе/.test(n.textContent)) || !!s.querySelector('[data-section-chapters], .group-contents'))]; }); }""",
                            [sid for sid, _ in CASES])
        check(dev, "E «Лента»: no «В этом разделе» block (Introduction, parts)", isinstance(found, list) and not any(v for _, v in found), found)
        pg.evaluate("try{localStorage.removeItem('ap.readerLayout')}catch(e){}")
        check(dev, "no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(dev, "scenario ran", False, str(error)[:300])
    finally:
        c.close()


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "pixel7", "desktop"]):
        b = getattr(p, eng).launch()
        run(b, dev, opts)
        b.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
