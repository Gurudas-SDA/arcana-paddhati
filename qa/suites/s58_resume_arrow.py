"""«Продолжить чтение» on the cover: arrow › and full title (Vraja Lila msg 5430, 20.10.2026).

Rule text (msg 5430, verbatim): «делай, стрелку ›»
Task (mockup «2026.10.20_Продолжить чтение — стрелка (макет).png», variant ›): arrow › in the book's gold
(#8B6508) in the card's bottom-right corner; the text does not run under the arrow (right padding ~34 px);
long titles wrap onto 2–3 lines instead of «…» — the card grows with its content; the cover's place is reserved
before first paint for the taller card, so the cover does not jump.
# tehniskais slieksnis Lipikāra, nav S noteikums: arrow within 18 px of the card's right/bottom edge;
#   text right edge >= 26 px left of the card's right edge; cover/card position equal in every early frame (±1 px).
usage: python s58_resume_arrow.py <base-url>
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
CH = "worship-sixteen-articles"
DEVICES = qa.devices(["iphone14", "ipad-portrait", "pixel7"])
results = []

# (name, page language path, stored place) — short title, the longest RU (3.4, 91 chars), the longest in the book (DE, 104)
CASES = [
    ("short", "ru-iast/", {"section": "arcana-procedure", "anchor": "11-gandha"}),
    ("long RU 3.4", "ru-iast/", {"section": CH, "anchor": "guru-pankti-namaskara"}),
    ("longest DE 3.4", "de/", {"section": CH, "anchor": "guru-pankti-namaskara"}),
]


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


# Every animation frame from the start: [cover height, card top - cover bottom, card height, install banner]
# (a jump = any change after the card exists). The browser-tab install banner (--install-banner-h, not shown in
# the installed app) appears after start-up and moves the page down / shortens a height-limited cover by its own
# height — that is not this card's jump (same on the live book before this change).
FRAMES = """(() => { window.__fr = []; let n = 0; const tick = () => {
  const i = document.querySelector('img.home-cover'), a = document.querySelector('a.home-resume');
  if (i && a) { const ri = i.getBoundingClientRect(), ra = a.getBoundingClientRect();
    const ib = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--install-banner-h')) || 0;
    window.__fr.push([Math.round(ri.height), Math.round(ra.top - ri.bottom), Math.round(ra.height), Math.round(ib)]); }
  if (++n < 240) requestAnimationFrame(tick); };
  requestAnimationFrame(tick); })();"""

STATE = """() => { const a = document.querySelector('a.home-resume'); if (!a) return null;
  const l = a.querySelector('.home-resume-line'), s = document.getElementById('home-resume'), ar = a.querySelector('.home-resume-arrow');
  const r = a.getBoundingClientRect(), lr = l.getBoundingClientRect(), sr = s.getBoundingClientRect();
  const range = document.createRange(); range.selectNodeContents(l);
  const rects = Array.from(range.getClientRects()); const textRight = Math.max(...rects.map(x => x.right));
  const lh = parseFloat(getComputedStyle(l).lineHeight) || 20;
  const v = getComputedStyle(document.documentElement).getPropertyValue('--home-resume-h').trim();
  const o = {reserved: v.endsWith('rem') ? parseFloat(v) * 16 : parseFloat(v), slotH: Math.round(sr.height * 10) / 10, text: l.textContent, lines: Math.round(lr.height / lh), cardH: Math.round(r.height),
    clipped: l.scrollWidth > l.clientWidth + 1 || l.scrollHeight > l.clientHeight + 1 || a.scrollHeight > a.clientHeight + 1 || r.bottom > sr.bottom + 0.5,
    ellipsis: getComputedStyle(l).textOverflow === 'ellipsis' && getComputedStyle(l).whiteSpace === 'nowrap',
    textGap: Math.round(r.right - textRight), arrow: null};
  if (ar) { const q = ar.getBoundingClientRect(); const cs = getComputedStyle(ar);
    o.arrow = {txt: ar.textContent, color: cs.color, visible: q.width > 0 && q.height > 0 && cs.visibility !== 'hidden',
      right: Math.round(r.right - q.right), bottom: Math.round(r.bottom - q.bottom), overlapsText: rects.some(x => x.right > q.left && x.bottom > q.top && x.top < q.bottom)}; }
  return o; }"""

with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        for name, path, pl in CASES:
            place = dict(v=1, block=0, offset=0, lang=path.rstrip("/"), time=int(time.time() * 1000), **pl)
            c = b.new_context(service_workers="block", locale="ru-RU", **opts)
            # offline-save card already «seen» (s49 covers it): only the «Продолжить» card under the cover
            c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('ap.offlineSave', %s);" % json.dumps(json.dumps({"s": "seen"})) +
                              "localStorage.setItem('ap.readingPlace', %s);"
                              % json.dumps(json.dumps(place)) + FRAMES)
            pg = c.new_page()
            pg.goto(f"{BASE}/{path}", wait_until="networkidle")
            pg.wait_for_timeout(900)
            st = pg.evaluate(STATE)
            fr = pg.evaluate("window.__fr || []")
            if not st:
                check(dev, f"{name}: card drawn", False, "no a.home-resume")
                c.close()
                continue
            ar = st["arrow"] or {}
            check(dev, f"{name}: arrow › visible, gold --ap-gold #965700 (V33)",
                  ar.get("visible") and ar.get("txt", "").strip() == "›" and ar.get("color") == "rgb(150, 87, 0)", ar)
            check(dev, f"{name}: arrow in the bottom-right corner",
                  ar and 0 <= ar.get("right", 99) <= 18 and 0 <= ar.get("bottom", 99) <= 18, ar)
            check(dev, f"{name}: text not under the arrow (right padding)",
                  ar and not ar.get("overlapsText") and st["textGap"] >= 26, {"textGap": st["textGap"], "arrow": ar})
            check(dev, f"{name}: title whole — no «…», not clipped", not st["clipped"] and not st["ellipsis"], st)
            if name != "short":
                check(dev, f"{name}: wraps onto 2–3 lines", 2 <= st["lines"] <= 3 if dev.startswith("iphone") else 1 <= st["lines"] <= 3, st)
            check(dev, f"{name}: reserved place = drawn card (--home-resume-h = slot height)",
                  abs(st["reserved"] - st["slotH"]) <= 1, {"reserved": st["reserved"], "slot": st["slotH"]})
            if dev.startswith("iphone") and name != "short":
                # rotation: the line re-wraps, the reserved place follows (ResizeObserver)
                pg.set_viewport_size({"width": opts["viewport"]["height"], "height": opts["viewport"]["width"]})
                pg.wait_for_timeout(500)
                r2 = pg.evaluate(STATE)
                check(dev, f"{name}: after rotation reserved place = drawn card",
                      r2 and abs(r2["reserved"] - r2["slotH"]) <= 1 and not r2["clipped"], r2 and {"reserved": r2["reserved"], "slot": r2["slotH"], "lines": r2["lines"]})
            first = fr[0] if fr else None
            moved = [f for f in fr if first and (abs(f[1] - first[1]) > 1 or abs(f[2] - first[2]) > 1 or
                                                 (abs(f[0] - first[0]) > 1 and abs(f[0] + f[3] - first[0] - first[3]) > 1))]
            check(dev, f"{name}: place reserved before paint — cover and card do not move (frames)",
                  first and not moved, {"first": first, "moved": moved[:3], "frames": len(fr)})
            c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
