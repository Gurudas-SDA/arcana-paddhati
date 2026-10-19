"""«Видимая загрузка книги на телефон» (Vraja Lila msg 5317/5318, 19.10.2026) — the saving state under the cover.

Vraja Lila, «Проверки» (verbatim): «блок появляется при незавершённой загрузке и исчезает при завершённой; при
отсутствии сети показывается состояние 2 и счёт не обнуляется; при неудачах показывается состояние 4; обложка не
прыгает при появлении блока (s38_cover_load не хуже прежнего); строка в «Содержании» и блок на обложке показывают
одно и то же число.»

The worker's messages are delivered to the page's own listener (navigator.serviceWorker 'message' event, the
same object the real worker posts to); the stored state of an earlier visit is put into localStorage before load.
usage: python s49_offline_save_card.py <base-url>
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from toc import Contents  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
COVER = f"{BASE}/ru-iast/"
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


def post(pg, msg):
    pg.evaluate("m => navigator.serviceWorker.dispatchEvent(new MessageEvent('message', {data: m}))",
                {"type": "precache-progress", "version": "t", **msg})
    pg.wait_for_timeout(300)


CARD = """() => { const c = document.querySelector('.home-save'); const i = document.querySelector('img.home-cover');
  const r = i ? i.getBoundingClientRect() : null;
  return {card: !!c && c.offsetHeight > 0, text: c ? c.innerText : '', view: (document.querySelector('.home-save-slot') || {}).dataset?.homeSaveView || null,
          reserved: document.documentElement.hasAttribute('data-home-save'),
          cover: r ? [Math.round(r.top), Math.round(r.height)] : null,
          stored: localStorage.getItem('ap.offlineSave')}; }"""


def ctx_with(b, opts, stored=None):
    c = b.new_context(service_workers="block", locale="ru-RU", **opts)
    init = "localStorage.setItem('ap.readerHintSeen','1');"
    if stored is not None:
        init += f"if(!sessionStorage.getItem('s49'))localStorage.setItem('ap.offlineSave',{json.dumps(json.dumps(stored))});sessionStorage.setItem('s49','1');"
    c.add_init_script(init)
    return c


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()

        # 1) unfinished download from an earlier visit: place reserved before first paint, no jump, count kept
        c = ctx_with(b, opts, {"s": "loading", "d": 84, "t": 214, "f": 0, "k": {}})
        pg = c.new_page()
        pg.goto(COVER, wait_until="commit")
        pg.wait_for_selector("img.home-cover", state="attached")
        first = pg.evaluate(CARD)
        pg.wait_for_load_state("networkidle")
        pg.wait_for_timeout(800)
        s1 = pg.evaluate(CARD)
        check(dev, "1 unfinished download: block shown on the cover", s1["card"] and s1["view"] == "loading", s1)
        check(dev, "1 count in parts «84 из 214», no percent", re.search(r"84\D+214", s1["text"]) and "%" not in s1["text"], s1["text"])
        # the cover's size is final at first paint (its top may move only with the install banner, which is older)
        check(dev, "1 place reserved before first paint, cover does not jump", first["reserved"] and first["cover"][1] == s1["cover"][1],
              {"first": first["cover"], "after": s1["cover"]})

        # 5) the line in «Содержание» shows the same count
        post(pg, {"done": 90, "total": 214, "complete": False, "failed": 0, "failedKinds": {}, "final": False})
        s5 = pg.evaluate(CARD)
        Contents(pg, qa.TocMode("default"), opts.get("has_touch", False)).contents()
        pg.wait_for_timeout(400)
        side = pg.evaluate("(() => { const e = document.querySelector('[data-offline-progress]'); return e ? e.textContent : null; })()")
        check(dev, "5 cover and «Содержание» show the same number", re.search(r"90\D+214", s5["text"] or "") and side and re.search(r"90\D+214", side) and "%" not in side,
              {"cover": s5["text"], "contents": side})

        pg.goto(COVER, wait_until="networkidle")
        pg.wait_for_timeout(500)

        # 2) no network: «приостановлена», count not reset
        c.set_offline(True)
        pg.evaluate("window.dispatchEvent(new Event('offline'))")
        pg.wait_for_timeout(300)
        s2 = pg.evaluate(CARD)
        check(dev, "2 offline: paused state, count kept", s2["view"] == "paused" and re.search(r"90\D+214", s2["text"]), s2)
        c.set_offline(False)
        pg.evaluate("window.dispatchEvent(new Event('online'))")
        pg.wait_for_timeout(300)

        # 4) failures: «Сохранено не всё», what is missing, text kept
        post(pg, {"done": 207, "total": 214, "complete": False, "failed": 7, "failedKinds": {"images": 7}, "final": True})
        s4 = pg.evaluate(CARD)
        check(dev, "4 failures: state 4 with the count and what is missing", s4["view"] == "partial" and re.search(r"207\D+214", s4["text"]) and re.search(r"\b7\b", s4["text"]), s4)

        # 3) finished: shown once, then the cover is clean on the next visit
        post(pg, {"done": 214, "total": 214, "complete": True, "failed": 0, "failedKinds": {}, "final": True})
        s3 = pg.evaluate(CARD)
        check(dev, "3 finished: «done» shown", s3["view"] == "done" and s3["card"], s3)
        pg.reload(wait_until="networkidle")
        pg.wait_for_timeout(800)
        s3b = pg.evaluate(CARD)
        check(dev, "3 next visit: cover clean, nothing reserved", not s3b["card"] and not s3b["reserved"], s3b)
        c.close()

        # no stored state and the service worker blocked (nothing will be saved): no block
        c = ctx_with(b, opts)
        pg = c.new_page()
        pg.goto(COVER, wait_until="networkidle")
        pg.wait_for_timeout(1500)
        s0 = pg.evaluate(CARD)
        check(dev, "0 no service worker: no block, cover full height", not s0["card"] and not s0["reserved"], s0)
        # a chapter never shows the block
        pg.goto(f"{BASE}/ru-iast/introduction/", wait_until="networkidle")
        post(pg, {"done": 10, "total": 214, "complete": False, "failed": 0, "failedKinds": {}, "final": False})
        check(dev, "never inside a chapter", pg.locator(".home-save").count() == 0, "")
        c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
