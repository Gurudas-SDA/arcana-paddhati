"""V40 — the toggle chip as ONE master element of fixed size (Vraja Lila msg 6091–6094 / 6103, 22.10.2026 01:43–02:05;
saskarnes autors, «Стандарты» 0а).

Rule text (as passed on by Lipikāra, verbatim): «при нажатии кнопка меняет свою ширину и размер… надо фиксированный
 размер и меняется только интенсивность цвета и заливка… иконка стрелочки внутри дёргается неправильно при открытии»;
 «Относится ко всем подобным элементам — нужно сделать master element и использовать его»; «начни собирать их в папке
 design-system». (Screenshots: the «translation» chip under a verse, closed / open.)
 # tehniskais slieksnis Lipikāra, nav S noteikums: «фиксированный размер» = width and height equal before / after a
 # tap (±0.5 px); the arrow's centre does not move (±0.5 px) at the end and in the middle of its turn; «не дёргается» =
 # the turn is a running transform transition (100–300 ms), not a jump.

Checks, per device:
  A  every chip of its kind is the master element: the verse chips («пословно» / «перевод»), «Настроение Гурудева» (the mantra chip
     «пословно» of the same Chip, when present) carry data-ds-pill (design-system/Pill.tsx);
  B  verse chips «перевод» and «пословно»: same width / height closed and open; font weight, frame and padding
     the same — only colour / fill differ (and they do differ);
  C  their arrow: its centre stays put (end and mid-turn), the turn is a smooth transform transition;
  D  «Настроение Гурудева»: the same size with its window open and closed.
usage: python s89_pill_master_v40.py <base-url>
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
VERSE_CH = "gaudiya-emblem"
MANTRA_CH = "daily-duties-brahma-muhurta"
results = []

LOOK = """(el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); const svg = el.querySelector('svg');
  const s = svg && svg.getBoundingClientRect();
  return {w: +r.width.toFixed(2), h: +r.height.toFixed(2), weight: cs.fontWeight, border: cs.borderTopWidth, pad: cs.paddingLeft + ' ' + cs.paddingTop,
          size: cs.fontSize, bg: cs.backgroundColor, color: cs.color, frame: cs.borderTopColor, open: el.getAttribute('aria-expanded'),
          cx: s ? +(s.left + s.width / 2 - r.left).toFixed(2) : null, cy: s ? +(s.top + s.height / 2 - r.top).toFixed(2) : null}; }"""
# Tap, then read the arrow mid-turn (~60 ms) and its running transitions.
TAP_MID = """(el) => new Promise((done) => { el.click(); setTimeout(() => { const r = el.getBoundingClientRect(); const svg = el.querySelector('svg');
  const s = svg.getBoundingClientRect(); const an = (svg.getAnimations ? svg.getAnimations() : []).map((a) => ({prop: a.transitionProperty,
    dur: a.effect && a.effect.getTiming().duration}));
  done({cx: +(s.left + s.width / 2 - r.left).toFixed(2), cy: +(s.top + s.height / 2 - r.top).toFixed(2), anim: an}); }, 60); })"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


def same_box(a, b):
    return abs(a["w"] - b["w"]) <= 0.5 and abs(a["h"] - b["h"]) <= 0.5


def chip_case(pg, dev, what, loc):
    loc.scroll_into_view_if_needed()
    pg.wait_for_timeout(300)
    el = loc.element_handle()
    a = pg.evaluate(LOOK, el)
    mid = pg.evaluate(TAP_MID, el)
    pg.wait_for_timeout(500)
    b = pg.evaluate(LOOK, el)
    check(dev, f"B {what}: fixed size closed / open (±0.5 px)", a["open"] != b["open"] and same_box(a, b), {"closed": a, "open": b})
    check(dev, f"B {what}: same weight, frame and padding; only colour / fill change",
          a["weight"] == b["weight"] and a["border"] == b["border"] and a["pad"] == b["pad"] and a["size"] == b["size"]
          and (a["bg"] != b["bg"] or a["color"] != b["color"] or a["frame"] != b["frame"]), {"closed": a, "open": b})
    still = a["cx"] is not None and all(abs(p[k] - a[k]) <= 0.5 for p in (mid, b) for k in ("cx", "cy"))
    smooth = any(x.get("prop") == "transform" and x.get("dur") and 100 <= x["dur"] <= 300 for x in mid["anim"])
    check(dev, f"C {what}: the arrow turns smoothly around its centre (no jump, no shift)", still and smooth,
          {"closed": [a["cx"], a["cy"]], "mid": mid, "open": [b["cx"], b["cy"]]})
    pg.evaluate("(el) => el.click()", el)   # back to closed
    pg.wait_for_timeout(400)


def run(browser, dev, opts):
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true')}catch(e){}")
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        pg.goto(f"{BASE}/{LANG}/{VERSE_CH}/", wait_until="networkidle")
        pg.wait_for_timeout(1000)
        kinds = pg.evaluate("""() => { const root = document.querySelector('.app-main [data-reader-current]') || document.querySelector('.app-main');
          const all = [...root.querySelectorAll('.verse-chip, .mood-toggle')];
          return {n: all.length, master: all.filter((e) => e.hasAttribute('data-ds-pill')).length}; }""")
        tr = qa.reading_locator(pg, ".verse-chips .verse-chip").filter(has_text="перевод").first
        if not tr.count():
            tr = qa.reading_locator(pg, ".verse-chips .verse-chip").first
        chip_case(pg, dev, "verse chip «перевод»", tr)
        pg.goto(f"{BASE}/{LANG}/{MANTRA_CH}/", wait_until="networkidle")
        pg.wait_for_timeout(1000)
        k2 = pg.evaluate("""() => { const root = document.querySelector('.app-main [data-reader-current]') || document.querySelector('.app-main');
          const all = [...root.querySelectorAll('.verse-chip, .mood-toggle')];
          return {n: all.length, master: all.filter((e) => e.hasAttribute('data-ds-pill')).length, mood: root.querySelectorAll('.mood-toggle').length}; }""")
        check(dev, "A every verse / mantra chip and «Настроение Гурудева» is the master Pill",
              kinds["n"] > 0 and kinds["master"] == kinds["n"] and k2["mood"] > 0 and k2["n"] > 0 and k2["master"] == k2["n"], {"emblem": kinds, "1": k2})
        vc = qa.reading_locator(pg, ".verse-chips .verse-chip").filter(has_text="пословно").first
        if not vc.count():
            vc = qa.reading_locator(pg, ".verse-chips .verse-chip").first
        chip_case(pg, dev, "verse chip «пословно»", vc)
        mood = qa.reading_locator(pg, ".mood-toggle").first
        if mood.count():
            mood.scroll_into_view_if_needed()
            el = mood.element_handle()
            a = pg.evaluate(LOOK, el)
            pg.evaluate("(el) => el.click()", el)
            pg.wait_for_timeout(600)
            b = pg.evaluate(LOOK, el)
            check(dev, "D «Настроение Гурудева»: the same size with its window open", b["open"] == "true" and same_box(a, b), {"closed": a, "open": b})
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(500)
        else:
            check(dev, "D «Настроение Гурудева» present on the page", False)

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
