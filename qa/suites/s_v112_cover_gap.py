"""V112 Vraja Lila msg 8621 (21.11.2026), verbatim: «заметил что на главном экране у окна обновления нет отступа от блока продолжить..,
понимаю что сделано так… чтобы при нажатии отрывшееся вверху и меню панели меню не перекрывали, но в данном случае отступ может быть и не
страшно если он наедет на меню обновления… может можно сделать что обложка с этими блоками продолжить и обновления при нажатии выезда
меню чутка уедет вверх с ease in and out и при нажатии и закрытии выдвижных панелей так же встанет на место».
Criteria (register V112), on the cover with the V110 «new version» strip («Загружается новая версия — 53 %», as in Vraja Lila's photo):
  a   a gap >= --space-8 (8 px) between the lower edge of the last card and the strip; a2 the strip's edges = the card's edges
  d   bars closed: the cover's top is not under the top bar; f nothing cut (no card's content clipped), no blocks overlap
  b   after a tap (bars out): the block's last lower edge + 8 px <= the bottom bar's upper edge (when the page scrolls — at the end of
      the scroll); the cover's top still not under the top bar; the block moves with a transform transition, ease-in-out, ~0.28 s
  c   bars closed again: back in place (+-2 px);  e  prefers-reduced-motion: no animation
The progress message is the one the new worker posts (public/sw.js «sw-update-progress»), dispatched on the page's
navigator.serviceWorker: the strip stays at 53 % for the measurements (lib/swUpdate.ts accepts it on a controlled page).
The suite runs its OWN server over out/. usage: python s_v112_cover_gap.py [<ignored>]
V112_SHOTS=<dir> — also save screenshots (iPhone 14 / Pixel 7, short card, bars closed / open, light + night)
# tehniskais slieksnis Lipikāra, nav S noteikums: 8 px gap (a design-system token), tolerance 0.5 px (edges 1 px, back in place 2 px),
# settle 700 ms
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
import server as qa_server  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

SHOTS = os.environ.get("V112_SHOTS", "")
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
LANG = "ru-iast"
PLACE_SHORT = {"v": 1, "section": "worship-sixteen-articles", "anchor": "patra-sthapana", "block": 0, "offset": 0, "lang": "ru-iast"}  # a 1-row card
PLACE_LONG = {"v": 1, "section": "worship-sixteen-articles", "anchor": "guru-pankti-namaskara", "block": 0, "offset": 0, "lang": "ru-iast"}  # 3 rows
CASES = [
    ("short card (Vraja Lila's photo)", PLACE_SHORT, {"s": "seen"}),
    ("3-row card", PLACE_LONG, {"s": "seen"}),
    ("save card + 3-row card", PLACE_LONG, {"s": "loading", "d": 40, "t": 120}),
]
SRV = qa_server.Server().start()
BASE = SRV.base
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


GEOM = """() => { const vis = (e) => { if (!e) return null; const b = e.getBoundingClientRect(); return b.height > 0 && b.width > 0 ? b : null; };
  const strips = [...document.querySelectorAll('[data-update-banner]')].map(vis).filter(Boolean);
  const s = strips[0] || null, c = vis(document.querySelector('a.home-resume')), v = vis(document.querySelector('img.home-cover'));
  const top = document.querySelector('.reader-bar-top'), bot = document.querySelector('.reader-bar-bottom');
  const m = document.querySelector('main.app-main'), hp = document.querySelector('.home-page'), cs = hp ? getComputedStyle(hp) : null;
  const blocks = [['cover', 'img.home-cover'], ['resume', 'a.home-resume'], ['save', '.home-save'], ['strip', null]].map(([n, q]) => {
    const e = q ? document.querySelector(q) : null; const b = q ? vis(e) : s; if (!b) return null;
    return {n, top: b.top, bottom: b.bottom}; }).filter(Boolean).sort((x, y) => x.top - y.top);
  const cut = ['a.home-resume', '.home-save', '.home-save-slot', '.update-banner-inline'].map((q) => { const e = document.querySelector(q);
    if (!vis(e)) return null; return e.scrollHeight > e.clientHeight + 1 ? q : null; }).filter(Boolean);
  const save = vis(document.querySelector('.home-save')), slot = vis(document.querySelector('.home-save-slot'));
  if (save && slot && save.bottom > slot.bottom + 0.5) cut.push('.home-save outside its slot');
  return {strip: s && {top: s.top, bottom: s.bottom, left: s.left, right: s.right, n: strips.length}, resume: c && {top: c.top, bottom: c.bottom, left: c.left, right: c.right},
    cover: v && {top: v.top, bottom: v.bottom, h: v.height}, blocks, cut, last: blocks.length ? blocks[blocks.length - 1] : null,
    topBar: top ? top.offsetHeight : 0, barTop: bot ? window.innerHeight - bot.offsetHeight : window.innerHeight, vh: window.innerHeight,
    shown: !!document.querySelector('.reader-chrome[data-shown]'), fits: !m || m.scrollHeight <= m.clientHeight + 1,
    tr: cs && {prop: cs.transitionProperty, fn: cs.transitionTimingFunction, dur: cs.transitionDuration}}; }"""
PROGRESS = "() => navigator.serviceWorker.dispatchEvent(new MessageEvent('message', {data: {type: 'sw-update-progress', done: 53, total: 100}}))"
SHOT_NAMES = {"iphone14": "iPhone 14", "pixel7": "Pixel 7"}


def new_page(p, eng, o, place, save):
    b = getattr(p, eng).launch()
    c = b.new_context(service_workers="allow", **o)
    c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');"
                      "localStorage.setItem('ap.readingPlace', %s);" % json.dumps(json.dumps(dict(place, time=int(time.time() * 1000)))))
    pg = c.new_page()
    pg.goto(f"{BASE}/{LANG}/", wait_until="load")
    pg.wait_for_function("navigator.serviceWorker.controller !== null", timeout=90000)
    pg.wait_for_timeout(1500)
    pg.evaluate("s => localStorage.setItem('ap.offlineSave', s)", json.dumps(save))
    pg.reload(wait_until="load")
    pg.wait_for_function("navigator.serviceWorker.controller !== null", timeout=60000)
    pg.wait_for_timeout(1200)
    pg.evaluate("s => localStorage.setItem('ap.offlineSave', s)", json.dumps(save))
    pg.evaluate(PROGRESS)
    pg.wait_for_timeout(700)
    return b, c, pg


def shot(pg, dev, name):
    if not SHOTS or dev not in SHOT_NAMES:
        return
    os.makedirs(SHOTS, exist_ok=True)
    for theme, suf in (("", ""), ("night", " (тёмная тема)")):
        pg.evaluate("t => t ? document.documentElement.setAttribute('data-reader-theme', t) : document.documentElement.removeAttribute('data-reader-theme')", theme)
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(SHOTS, f"2026.11.21_V112_{SHOT_NAMES[dev]}_обложка {name}{suf}.png"))
    pg.evaluate("document.documentElement.removeAttribute('data-reader-theme')")


def at_end(pg):
    pg.evaluate("() => { const m = document.querySelector('main.app-main'); if (m) m.scrollTop = m.scrollHeight; window.scrollTo(0, document.documentElement.scrollHeight); }")
    pg.wait_for_timeout(400)
    return pg.evaluate(GEOM)


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        print(dev, flush=True)
        touch = o.get("has_touch", False)
        for cname, place, save in CASES:
            name = f"{dev} [{cname}]"
            try:
                b, c, pg = new_page(p, eng, o, place, save)
                tap = (lambda x, y: pg.touchscreen.tap(x, y)) if touch else (lambda x, y: pg.mouse.click(x, y))
                g0 = pg.evaluate(GEOM)
                txt = pg.evaluate("() => [...document.querySelectorAll('[data-update-banner]')].map(e => e.textContent).join(' | ')")
                check(name, "0 the strip «… 53 %» is on the cover", g0["strip"] and "53" in txt, txt)
                if not g0["strip"] or not g0["resume"]:
                    check(name, "0b the card «Продолжить» is on the cover", False, g0)
                    c.close(); b.close(); continue
                if cname.startswith("short") and dev in SHOT_NAMES:
                    shot(pg, dev, "панели закрыты")
                prev = [x for x in g0["blocks"] if x["n"] != "strip" and x["top"] < g0["strip"]["top"]]
                gap = g0["strip"]["top"] - (prev[-1]["bottom"] if prev else 0)
                check(name, "a a gap >= 8 px between the last card and the strip", gap >= 7.5, {"gap": round(gap, 2), "above": prev[-1]["n"] if prev else None, "blocks": g0["blocks"]})
                check(name, "a2 the strip's left / right edges = the card's (+-1 px)",
                      abs(g0["strip"]["left"] - g0["resume"]["left"]) <= 1 and abs(g0["strip"]["right"] - g0["resume"]["right"]) <= 1, {"strip": g0["strip"], "resume": g0["resume"]})
                ovl = [(x["n"], y["n"]) for x, y in zip(g0["blocks"], g0["blocks"][1:]) if x["bottom"] > y["top"] + 0.5]
                check(name, "f bars closed: nothing cut, no blocks overlap", not g0["cut"] and not ovl, {"cut": g0["cut"], "overlap": ovl})
                check(name, "d bars closed: the cover's top is not under the top bar", g0["cover"]["top"] >= g0["topBar"] - 0.5, {"cover": g0["cover"]["top"], "topBar": g0["topBar"]})
                check(name, "g bars closed: the strip is on the screen (or the page scrolls)", g0["strip"]["bottom"] <= g0["vh"] + 0.5 or not g0["fits"], {"strip": g0["strip"]["bottom"], "vh": g0["vh"], "fits": g0["fits"]})
                cx = (g0["resume"]["left"] + g0["resume"]["right"]) / 2
                cy = (g0["cover"]["top"] + g0["cover"]["bottom"]) / 2
                tap(cx, cy)
                pg.wait_for_timeout(700)
                g1 = pg.evaluate(GEOM)
                check(name, "b1 the bars are out after the tap", g1["shown"])
                if cname.startswith("short") and dev in SHOT_NAMES:
                    shot(pg, dev, "панели открыты")
                if g1["fits"]:
                    check(name, "b2 bars out: the last block's lower edge + 8 px <= the bottom bar's upper edge",
                          g1["last"]["bottom"] + 8 <= g1["barTop"] + 0.5, {"last": g1["last"], "barTop": g1["barTop"], "before": g0["last"]})
                    check(name, "b5 bars out: the cover's top is not under the top bar", g1["cover"]["top"] >= g1["topBar"] - 0.5, {"cover": g1["cover"]["top"], "topBar": g1["topBar"]})
                    check(name, "b4 the block rose when it had to (or had room)", g0["last"]["bottom"] + 8 <= g0["barTop"] + 0.5 or g1["last"]["bottom"] < g0["last"]["bottom"] - 0.5,
                          {"before": g0["last"]["bottom"], "after": g1["last"]["bottom"]})
                else:
                    ge = at_end(pg)
                    check(name, "b2 the page scrolls: at its end the last block's lower edge + 8 px <= the bottom bar's upper edge",
                          ge["last"]["bottom"] + 8 <= ge["barTop"] + 0.5, {"last": ge["last"], "barTop": ge["barTop"]})
                    pg.evaluate("() => { const m = document.querySelector('main.app-main'); if (m) m.scrollTop = 0; window.scrollTo(0, 0); }")
                    pg.wait_for_timeout(300)
                ovl1 = [(x["n"], y["n"]) for x, y in zip(g1["blocks"], g1["blocks"][1:]) if x["bottom"] > y["top"] + 0.5]
                check(name, "f2 bars out: nothing cut, no blocks overlap", not g1["cut"] and not ovl1, {"cut": g1["cut"], "overlap": ovl1})
                tr = g1["tr"] or {}
                check(name, "b3 the block moves with a transform transition, ease-in-out, 0.28 s",
                      "transform" in (tr.get("prop") or "") and "ease-in-out" in (tr.get("fn") or "") and "0.28s" in (tr.get("dur") or ""), tr)
                tap(cx, cy)
                pg.wait_for_timeout(700)
                g2 = pg.evaluate(GEOM)
                check(name, "c bars closed again: back in place (+-2 px)",
                      (not g2["shown"]) and abs(g2["strip"]["top"] - g0["strip"]["top"]) <= 2 and abs(g2["cover"]["top"] - g0["cover"]["top"]) <= 2,
                      {"shown": g2["shown"], "strip": [g0["strip"]["top"], g2["strip"]["top"]], "cover": [g0["cover"]["top"], g2["cover"]["top"]]})
                pg.emulate_media(reduced_motion="reduce")
                d = pg.evaluate("() => getComputedStyle(document.querySelector('.home-page')).transitionDuration")
                check(name, "e prefers-reduced-motion: no animation", set(d.replace(" ", "").split(",")) <= {"0s"}, d)
                c.close()
                b.close()
            except Exception as e:  # noqa: BLE001
                check(name, "EXCEPTION", False, str(e)[:600])

SRV.stop()
print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
