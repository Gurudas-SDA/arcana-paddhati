"""Cards under the cover as wide as the cover (Vraja Lila, 20.10.2026, «ДА» msg 5520).

Task (mockup «2026.10.20_Обложка — карточки по ширине обложки, …» — iPhone SE, iPhone 14, iPad portrait/landscape,
desktop): «Продолжить чтение» and «Сохраняется на телефон» under the cover take exactly the cover's width — their
left and right edges coincide with the cover's (before: at most 26rem, narrower or wider than the cover).
# tehniskais slieksnis Lipikāra, nav S noteikums: edges equal ±1 px; reserved --home-resume-h = drawn slot ±1 px.
usage: python s64_cover_cards_width.py <base-url>
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone-se", "iphone14", "ipad-portrait", "ipad-landscape", "desktop"])
results = []

PLACE = {"v": 1, "section": "worship-sixteen-articles", "anchor": "guru-pankti-namaskara", "block": 0, "offset": 0, "lang": "ru-iast"}
LOADING = {"s": "loading", "d": 40, "t": 120}
CASES = [
    ("both cards", PLACE, LOADING),
    ("«Продолжить» only", PLACE, {"s": "seen"}),
    ("save card only", None, LOADING),
]

STATE = """() => { const box = (q) => { const e = document.querySelector(q); if (!e) return null;
    const r = e.getBoundingClientRect(); return r.width > 0 ? {l: Math.round(r.left * 10) / 10, r: Math.round(r.right * 10) / 10, w: Math.round(r.width * 10) / 10} : null; };
  const s = document.getElementById('home-resume');
  const v = getComputedStyle(document.documentElement).getPropertyValue('--home-resume-h').trim();
  return {cover: box('img.home-cover'), resume: box('a.home-resume'), save: box('.home-save'),
    reserved: v ? parseFloat(v) * (v.endsWith('rem') ? 16 : 1) : null, slotH: s ? Math.round(s.getBoundingClientRect().height * 10) / 10 : null}; }"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


def same(a, b):
    return bool(a and b and abs(a["l"] - b["l"]) <= 1 and abs(a["r"] - b["r"]) <= 1)


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        for name, place, save in CASES:
            c = b.new_context(service_workers="block", locale="ru-RU", **opts)
            init = "localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');"
            init += "localStorage.setItem('ap.offlineSave', %s);" % json.dumps(json.dumps(save))
            if place:
                init += "localStorage.setItem('ap.readingPlace', %s);" % json.dumps(json.dumps(dict(place, time=int(time.time() * 1000))))
            c.add_init_script(init)
            pg = c.new_page()
            pg.goto(f"{BASE}/ru-iast/", wait_until="networkidle")
            pg.wait_for_timeout(800)
            st = pg.evaluate(STATE)
            if place:
                check(dev, f"{name}: «Продолжить» edges = cover edges (±1 px)", same(st["cover"], st["resume"]), st)
                check(dev, f"{name}: reserved place = drawn card", st["reserved"] is not None and st["slotH"] is not None
                      and abs(st["reserved"] - st["slotH"]) <= 1, {"reserved": st["reserved"], "slot": st["slotH"]})
            if save.get("s") == "loading":
                check(dev, f"{name}: «Сохраняется» edges = cover edges (±1 px)", same(st["cover"], st["save"]), st)
            c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
