"""V46 — the one-time hint «Tap empty space to show the menu» lies wholly ABOVE the bottom bar
(Vraja Lila msg 6321, 22.10.2026; saskarnes autors, «Стандарты» 0а).

Vraja Lila (msg 6321, screenshot 1792697323929-AQAD9hBrG5X20VJ8.jpg, iPhone, en, «Maṅgalācaraṇa», bar «‹ Back /
Forward ›» out): the hint at the bottom of the reading page is under the bottom bar — only its top edge shows
(RU and the other languages the same).
Criteria (register V46): the hint in its full height above the bottom bar on every device, in «Страницы» and «Лента»,
with the bar out and hidden; no panel covers it; design-system/README.md «Solid while moving».

Before (0caabd3): .reader-hint `position: fixed; bottom: 40px; z-index: 25` — the bar (z 30, opaque, 57 px high)
lies over its lower part: iPhone 14 hint 771–804, bar top 787.
 # tehniskais slieksnis Lipikāra, nav S noteikums: «above» = hint bottom ≤ bar top + 0.5 px; «covered» = any overlap
 #   (> 0.5 px) with an on-screen bar, or with the status strip when that strip's z-index ≥ the hint's; frames read every
 #   animation frame for 700 ms while the bar hides; «solid while moving» = effective opacity ≥ 0.99 and background
 #   alpha 1 in every frame in which the hint is not at its resting position.

Checks, per device × reading mode («Страницы», «Лента») × language (en «Maṅgalācaraṇa» as in the screenshot;
ru-iast «arcana-procedure»):
  A  at load (the bar out or hidden, as the app shows it there): the hint visible, fully in the viewport, its bottom
     above the bar's top, no bar / status strip over it;
  B  (bar out at load) the bar hides (reading on, down) while the hint is shown: in every frame no overlap with the
     bar; while the hint moves it is solid; after: the hint fully visible, nothing over it;
  C  (bar hidden at load — every way to bring the bar out also removes the hint) the «bar out» look probed by setting
     the state attribute [data-shown]: the hint above the bar, nothing over it.
  Over the matrix both states occur in both modes (iPhone 14 / desktop: «Страницы» bar out at load; «Лента» en hidden,
  ru-iast out).
usage: python s98_hint_above_bottom_bar_v46.py <base-url>
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
SHOTS = os.environ.get("V46_SHOTS")
SHOT_PREFIX = os.environ.get("V46_SHOT_PREFIX", "2026.10.22_V46_")
results = []

GEO = """() => {
  const eff = (e) => { let o = 1; for (let x = e; x && x.nodeType === 1; x = x.parentElement) o *= +getComputedStyle(x).opacity; return o; };
  const alpha = (bg) => { const m = bg.match(/rgba?\\(([^)]*)\\)/); if (!m) return bg === 'transparent' ? 0 : 1;
    const p = m[1].split(/[ ,\\/]+/).filter(Boolean); return p.length > 3 ? +p[3] : 1; };
  const g = (s) => { const e = document.querySelector(s); if (!e) return null; const c = getComputedStyle(e);
    const r = e.getBoundingClientRect();
    const on = c.display !== 'none' && c.visibility !== 'hidden' && r.height > 0 && r.bottom > 0.5 && r.top < innerHeight - 0.5;
    return {top: +r.top.toFixed(1), bottom: +r.bottom.toFixed(1), left: +r.left.toFixed(1), right: +r.right.toFixed(1),
            on, z: parseInt(c.zIndex) || 0, op: +eff(e).toFixed(3), a: alpha(c.backgroundColor)}; };
  return {t: performance.now(), vh: innerHeight, vw: innerWidth, hint: g('.reader-hint'), bar: g('.reader-bar-bottom'),
          topbar: g('.reader-bar-top'), status: g('.reader-status'),
          shown: !!document.querySelector('.reader-chrome[data-shown]')}; }"""

REC = "(ms) => { window.__h = []; const t0 = performance.now(); const G = " + GEO + """;
  const f = () => { window.__h.push(G()); if (performance.now() - t0 < ms) requestAnimationFrame(f); }; requestAnimationFrame(f); }"""


def check(tag, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {tag} {name} {json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


def overlap(a, b):
    return min(a["bottom"], b["bottom"]) - max(a["top"], b["top"]) > 0.5 and min(a["right"], b["right"]) - max(a["left"], b["left"]) > 0.5


def covered_by(s):
    """Which on-screen panels lie over the hint in state s."""
    h = s["hint"]
    out = []
    for k in ("bar", "topbar"):
        p = s[k]
        if p and p["on"] and overlap(h, p):
            out.append(k)
    st = s["status"]
    if st and st["on"] and overlap(h, st) and st["z"] >= h["z"]:
        out.append("status")
    return out


def resting(pg, tag, what):
    s = pg.evaluate(GEO)
    h = s["hint"]
    if not (h and h["on"]):
        check(tag, f"{what}: the hint is on screen", False, s)
        return s
    inside = h["top"] >= -0.5 and h["bottom"] <= s["vh"] + 0.5 and h["left"] >= -0.5 and h["right"] <= s["vw"] + 0.5
    bar = s["bar"]
    above = not (bar and bar["on"]) or h["bottom"] <= bar["top"] + 0.5
    cov = covered_by(s)
    check(tag, f"{what}: the hint in its full height in the viewport and above the bottom bar, no panel over it",
          inside and above and not cov,
          {"hint": [h["top"], h["bottom"]], "barTop": bar and bar["on"] and bar["top"], "vh": s["vh"], "coveredBy": cov,
           "barOut": s["shown"]})
    return s


def shot(pg, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        pg.screenshot(path=os.path.join(SHOTS, f"{SHOT_PREFIX}{name}.png"))


def run(browser, dev, opts, mode, lang, ch):
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    init = "try{localStorage.removeItem('ap.readerHintSeen');localStorage.setItem('installDismissed','true');"
    init += ("localStorage.setItem('ap.readerLayout','scroll')" if mode == "scroll" else "localStorage.removeItem('ap.readerLayout')")
    c.add_init_script(init + "}catch(e){}")
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    tag = f"{dev}/{'Лента' if mode == 'scroll' else 'Страницы'}/{lang or 'en'}"
    try:
        pg.goto(f"{BASE}/{lang + '/' if lang else ''}{ch}/", wait_until="networkidle")
        pg.wait_for_selector(".reader-hint", timeout=6000)
        pg.wait_for_timeout(500)                      # its 220 ms entrance is over
        s = pg.evaluate(GEO)
        at_load = "bar out" if s["shown"] else "bar hidden"
        resting(pg, tag, f"A at load ({at_load}, as the app shows it)")
        shot(pg, f"{dev}_{mode}_{lang or 'en'}_load")
        if s["shown"]:
            # B: reading on (down) takes the bar away; the hint stays (only a tap removes it)
            pg.evaluate(f"({REC})(1600)")
            for _ in range(4):
                pg.evaluate("""() => { const m = document.querySelector('.app-main');
                    m.dispatchEvent(new WheelEvent('wheel', {deltaY: 200, bubbles: true}));
                    m.scrollTop += 200; m.dispatchEvent(new Event('scroll')); }""")
                pg.wait_for_timeout(350)
                if not pg.evaluate("!!document.querySelector('.reader-chrome[data-shown]')"):
                    break
            pg.wait_for_timeout(500)
            fr = [f for f in pg.evaluate("window.__h") if f["hint"] and f["hint"]["on"]]
            hidden = not pg.evaluate("!!document.querySelector('.reader-chrome[data-shown]')")
            check(tag, "B the bar hid on reading down (scenario ran)", hidden and len(fr) > 5, {"hidden": hidden, "frames": len(fr)})
            rest_top = fr[-1]["hint"]["top"] if fr else None
            bad_cov = [[round(f["t"]), f["hint"]["bottom"], f["bar"]["top"]] for f in fr if covered_by(f)]
            check(tag, "B in every frame of the bar hiding the hint is not under the bar", not bad_cov, {"t,hintBottom,barTop": bad_cov[:8]})
            bad_solid = [[round(f["t"]), f["hint"]["top"], f["hint"]["op"], f["hint"]["a"]] for f in fr
                         if abs(f["hint"]["top"] - rest_top) > 0.5 and (f["hint"]["op"] < 0.99 or f["hint"]["a"] < 1)]
            moved = len({f["hint"]["top"] for f in fr})
            check(tag, "B «Solid while moving»: while the hint moves it is opaque", not bad_solid,
                  {"t,top,opacity,bgAlpha": bad_solid[:8], "positions": moved})
            resting(pg, tag, "B bar hidden")
            shot(pg, f"{dev}_{mode}_{lang or 'en'}_bar_hidden")
        else:
            # C: here the app keeps the bar in at load, and every way to bring it out (tap, back at the start) also
            # removes the hint — so the «bar out» look is probed by the state attribute alone (CSS geometry only).
            pg.evaluate("() => document.querySelector('.reader-chrome').setAttribute('data-shown', '')")
            pg.wait_for_timeout(500)
            resting(pg, tag, "C bar out (probe: [data-shown] set on the page)")
            shot(pg, f"{dev}_{mode}_{lang or 'en'}_bar_out_probe")
        check(tag, "no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(tag, "scenario ran", False, str(error)[:300])
    finally:
        c.close()


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "pixel7", "desktop"]):
        b = getattr(p, eng).launch()
        for mode in ("pages", "scroll"):
            run(b, dev, opts, mode, "", "mangalacarana")      # Vraja Lila's screenshot: en, «Maṅgalācaraṇa»
            run(b, dev, opts, mode, "ru-iast", "arcana-procedure")
        b.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
