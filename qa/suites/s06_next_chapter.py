"""V88 (Vraja Lila msg 7791/7792): the chapter-end cards «След. глава ›» / «‹ Пред. глава» are REMOVED, so this suite now checks that
at every chapter end there is NO next-chapter control (no [data-reader-nav], no .chapter-next, no «След. глава» / «Next chapter» text),
only the bottom bar «‹ Вернуться» / «Вперёд ›» (steps of the path) is there. The V17/V81 text below is the history of the suite.
Reader UI v6 (Satkirti 06.10.2026) «next chapter», rewritten for V17 (Vraja Lila msg 796 / 5635 / 5639,
20.10.2026; «Стандарты» 0а): the next chapter is the bottom bar's «Вперёд ›» (the block at the end of
every chapter is removed; the next chapter's title is not on the bar — «Название след. главы на панели — НЕ
нужно»).
usage: python s06_next_chapter.py <base-url> [shots-dir]
Checks per device: no block at the chapter end, «Вперёд ›» goes to the next page of the contents,
>= 44px target inside the screen, the bars are out at the chapter end with «Вперёд ›» on screen, opens the
next chapter at its top, browser Back / Forward history, «‹ Назад» = the previous chapter, last chapter has
no «Вперёд ›», theme colours, no third-party requests."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402  (device profiles, repo paths)
import os, sys
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
BASE = sys.argv[1].rstrip("/"); SHOTS = sys.argv[2] if len(sys.argv) > 2 else None
ONLY = None  # device filter: QA_DEVICES (qa/lib/qa.py)
HOST = urlparse(BASE).netloc
IOS_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
IPAD_UA = IOS_UA.replace("iPhone; CPU iPhone OS", "iPad; CPU OS")
PIXEL_UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36")
DEVICES = qa.devices(['iphone14', 'iphone-se', 'pixel7', 'ipad-portrait', 'ipad-landscape', 'desktop'])
LANG = "ru-iast"
import book_order  # noqa: E402  (V45: the order from the book's data)
# (chapter, expected next id, expected start of the title line) — the next id from the data (qa/lib/book_order.py):
# V45 (Vraja Lila msg 6178 / 1412, 22.10.2026) the parts' own pages are NOT in the order any more, nor a section
# without text of its own; «Назад» / «Вперёд» go through the text.
_NEXT = lambda cid: book_order.neighbours(LANG, cid)[1]
CASES = [(cid, _NEXT(cid), title0) for cid, title0 in [
    # v7 (Satkirti 06.10): Introduction group without numbers, Part I numbered from 1
    ("introduction", "Эмблема Гаудия-матха"),
    # v7.1 (Satkirti 06.10): Мангалачарана before Введение, outside the group
    ("mangalacarana", "Введение"),
    # V45: from the last chapter before Part I straight to its first chapter (no part page)
    ("vigraha-tattva", "1. "),
    ("offering-bhoga", "7. "),
    ("main-worship-sixteen-items", "11. "),
    ("guru-puja-vyasa-puja", "13. "),
    # v7.4 (appended last: the loop index decides which history checks run)
    # (Satkirti 07.10): Part IV ends with the ārati songs; 22.10 (msg 6180): parampara → «Джая-дхвани» → Мангалачарана
    ("parampara", "Джая-дхвани"),
    ("major-festivals", "14. "),
    # A121 (Satkirti 26.10 msg 6811–6818): part «Арати» = Мангала-арати 14, Раджа-бхога-арати 15, Гаура-арати 16,
    # Картика 17, Джхулана-ятра 18, Ямунаштака 19 (last chapter; A127 msg 6961)
    ("gaura-arati-songs", "17. "),
    ("kartika-bhajans", "18. "),
    # 22.10 (Satkirti msg 6065): «Заключение» after the parts, unnumbered — now the last page of the book
    ("gurudeva-mangalacarana", "Заключение"),   # A137 02.11 (msg 7293): «Мангалачарана Гурудева» is now the last chapter (after Ямунаштака)
] if cid in book_order.pages(LANG)]
LAST = "conclusion"
res = []


def chk(d, n, ok, info=""):
    res.append((d, n, bool(ok), info)); print(f"  [{'PASS' if ok else 'FAIL'}] {d} {n} {'' if ok else info}", flush=True)



def run(p, dev, eng, o):
    br = getattr(p, eng).launch()
    errs, foreign = [], []
    ctx = br.new_context(service_workers="block", **o)
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("request", lambda r: foreign.append(r.url) if urlparse(r.url).netloc not in (HOST, "") and not r.url.startswith(("data:", "blob:")) else None)
    pg.goto(f"{BASE}/{LANG}/{CASES[0][0]}/", wait_until="networkidle"); pg.wait_for_timeout(700)
    pg.evaluate("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    PROBE = """() => ({nav: document.querySelectorAll('[data-reader-nav]').length, block: document.querySelectorAll('.chapter-next, .chapter-next-link, .chapter-end-cards, .chapter-end-card').length,
      txt: /(След|Пред)\\. глава|Next chapter|Prev chapter/.test(document.querySelector('.app-main').innerText),
      steps: [...document.querySelectorAll('.reader-bar-bottom [data-reader-step]')].map(b => b.getAttribute('data-reader-step'))})"""
    pages = [c[0] for c in CASES] + [LAST]
    for cid in pages:
        pg.goto(f"{BASE}/{LANG}/{cid}/", wait_until="networkidle"); pg.wait_for_timeout(700)
        pg.evaluate("() => { const m = document.querySelector('.app-main'); m.scrollTop = m.scrollHeight; m.dispatchEvent(new Event('scroll')); }"); pg.wait_for_timeout(500)
        g = pg.evaluate(PROBE)
        chk(dev, f"V88 {cid}: no next/previous chapter control at the chapter end", g["nav"] == 0 and g["block"] == 0 and not g["txt"], str(g))
        chk(dev, f"V88 {cid}: the bottom bar still has «Вернуться» / «Вперёд»", g["steps"] == ["back", "forward"], str(g))
    pg.goto(f"{BASE}/vigraha-tattva/", wait_until="networkidle"); pg.wait_for_timeout(700)
    pg.evaluate("() => { const m = document.querySelector('.app-main'); m.scrollTop = m.scrollHeight; }"); pg.wait_for_timeout(500)
    g = pg.evaluate(PROBE)
    chk(dev, "V88 English page: no «Next chapter ›» either", g["nav"] == 0 and g["block"] == 0 and not g["txt"], str(g))
    chk(dev, "no requests to third-party hosts", not foreign, "; ".join(foreign[:5]))
    chk(dev, "no page errors", not errs, "; ".join(errs[:3]))
    ctx.close(); br.close()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        if ONLY and dev not in ONLY.split(","):
            continue
        print(dev, flush=True)
        try:
            run(p, dev, eng, o)
        except Exception as e:
            chk(dev, "EXCEPTION", False, str(e)[:900])
fails = [r for r in res if not r[2]]
print(f"\n{len(res) - len(fails)}/{len(res)} passed")
for f in fails:
    print("FAILED:", f[0], f[1], f[3][:300])
