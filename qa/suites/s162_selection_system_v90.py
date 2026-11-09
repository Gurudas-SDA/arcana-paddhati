"""V90 — Vraja Lila 09.11 msg 2838/7939/7945 («вариант d»): while the text is only SELECTED (before a colour is chosen) the book does not
override the selection colour: no ::selection rule in the book's CSS, the system colour of the device shows (as on iPhone). Our colour
appears only after a colour is chosen (::highlight(hl-N), painted and stored).
# tehniskais slieksnis Lipikāra, nav S noteikums: settle 300-900 ms
usage: python s162_selection_system_v90.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
results = []
RULES = """() => { const hits = []; const walk = (rules, sheet) => { for (const r of rules) {
    if (r.selectorText && /::selection/.test(r.selectorText)) hits.push(r.selectorText);
    if (r.cssRules) walk(r.cssRules, sheet); } };
  for (const sh of document.styleSheets) { try { walk(sh.cssRules, sh); } catch (e) { hits.push('unreadable sheet'); } }
  return hits; }"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else json.dumps(evidence, ensure_ascii=False)[:600]}", flush=True)


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        for theme in ("day", "night"):
            try:
                b = getattr(p, eng).launch()
                c = b.new_context(service_workers="block", locale="ru-RU", **opts)
                c.add_init_script("try{localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');"
                                  + ("localStorage.setItem('ap.readerTheme','night');" if theme == "night" else "") + "}catch(e){}")
                pg = c.new_page()
                pg.goto(f"{BASE}/ru-iast/daily-duties-brahma-muhurta/", wait_until="networkidle")
                pg.wait_for_timeout(800)
                hits = pg.evaluate(RULES)
                check(f"{dev}/{theme}", "the book's CSS has no ::selection rule (the system selection colour shows)", hits == [], hits)
                b.close()
            except Exception as ex:  # noqa: BLE001
                check(f"{dev}/{theme}", "scenario ran to the end", False, repr(ex)[:300])

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
