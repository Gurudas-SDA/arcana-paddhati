"""UI elements never cover a picture, above all a Deity picture (V61 step 4 fix).

Rule text (Vraja Lila msg 7168, 31.10.2026): «элементы UI не перекрывают картины, особенно изображения Божеств».
In the floating picture copy (.hs-peek, a Deity picture shown while its row is off-screen) the master ✕ sits in a header strip
outside the card (variant Б, msg 7172), not over the picture: the ✕ box and every other control of the window have 0 px of overlap with the picture's box.
Checks (iPhone 14 + desktop, day + night): the ✕ is 44x44 with its centre 30/30 from the card's corner (V61 question 2 «А», unchanged);
the picture starts below the ✕ box; ✕ bbox ∩ picture bbox = 0 px; no visible button of the window (outside the picture's own
hotspot layer) meets the picture; the picture keeps its proportion (rendered ratio = natural ratio, ±1 %); the ✕ has no disc under it.
# tehniskais slieksnis Lipikāra, nav S noteikums: ±1 px measuring tolerance, ±1 % proportion tolerance.
usage: python s129_ui_not_over_images.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
results = []


def check(where, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {where} {name} {'' if ok else json.dumps(info, ensure_ascii=False)[:900]}", flush=True)


OPEN = """async () => { const mn = document.querySelector('.app-main');
  const row = document.querySelector('.app-main .hs-row[data-hs-nums="14"]'); if (!row) return 'no row';
  mn.scrollTop += row.getBoundingClientRect().top - innerHeight * 0.3; mn.dispatchEvent(new Event('scroll'));
  await new Promise(r => setTimeout(r, 150)); row.querySelector('.hs-text, .hs-cell').click();
  for (let i = 0; i < 3; i++) { await new Promise(r => setTimeout(r, 180)); dispatchEvent(new Event('resize')); mn.dispatchEvent(new Event('scroll')); }
  await new Promise(r => setTimeout(r, 600)); return !!document.querySelector('.hs-peek'); }"""

MEASURE = """() => {
  const pk = document.querySelector('.hs-peek'); const img = pk && pk.querySelector('img'); const x = pk && pk.querySelector('.window-close');
  if (!pk || !img || !x) return {err: 'missing ' + (!pk ? 'peek' : !img ? 'img' : 'x')};
  const r = e => { const b = e.getBoundingClientRect(); return {l: b.left, t: b.top, r: b.right, b: b.bottom, w: b.width, h: b.height}; };
  const ov = (a, b) => Math.max(0, Math.min(a.r, b.r) - Math.max(a.l, b.l)) * Math.max(0, Math.min(a.b, b.b) - Math.max(a.t, b.t));
  const I = r(img), X = r(x), C = r(pk); const xs = getComputedStyle(x);
  const layer = img.parentElement;  // the picture's own layer (its hotspot marks belong to the picture)
  const others = [...pk.querySelectorAll('button, a, [role=button]')].filter(e => !layer.contains(e) && e !== x)
    .filter(e => { const b = e.getBoundingClientRect(); const s = getComputedStyle(e); return b.width > 0 && b.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; })
    .map(e => ({cls: e.className, ov: ov(r(e), I)}));
  return {xImg: +ov(X, I).toFixed(2), others, imgTopMinusXBottom: +(I.t - X.b).toFixed(2), xW: +X.w.toFixed(2), xH: +X.h.toFixed(2),
    cx: +((X.t + X.h / 2) - C.t).toFixed(2), cr: +(C.r - (X.l + X.w / 2)).toFixed(2), ratio: I.w / I.h, nat: img.naturalWidth / img.naturalHeight,
    xBg: xs.backgroundColor, xBorder: xs.borderTopWidth, xShadow: xs.boxShadow, xr: X, xCard: +ov(X, C).toFixed(2), xBelowCard: +(Math.max(C.t - X.b, X.t - C.b)).toFixed(2), xRightGap: +(C.r - X.r).toFixed(2), contrast: (() => { const p = s => s.match(/[\d.]+/g).slice(0, 3).map(Number); const L = c => { const [r, g, b] = c.map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; }; const a = L(p(xs.color)), b = L(p(xs.backgroundColor)); return +((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)).toFixed(2); })(), card: C, img: I, vw: innerWidth, vh: innerHeight};
}"""


def app():
    devs = qa.devices(["iphone14", "desktop"])
    with sync_playwright() as p:
        for dev, eng, opts in devs:
            b = getattr(p, eng).launch()
            for theme in ("day", "night"):
                c = b.new_context(service_workers="block", locale="ru-RU", **opts)
                init = "localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');"
                if theme == "night":
                    init += "localStorage.setItem('ap.readerTheme','night');"
                c.add_init_script("try{" + init + "}catch(e){}")
                pg = c.new_page()
                pg.goto(f"{BASE}/ru-iast/worship-sixteen-articles/", wait_until="networkidle")
                pg.wait_for_timeout(1200)
                r = pg.evaluate(OPEN)
                tag = f"{dev}/{theme}"
                if r is not True:
                    check(tag, "floating picture copy opens", False, r)
                    c.close()
                    continue
                pg.wait_for_timeout(500)
                m = pg.evaluate(MEASURE)
                if "err" in m:
                    check(tag, "peek measurable", False, m)
                    c.close()
                    continue
                check(tag, "✕ 44x44, outside the card (above it; below it when the card is at the top), right edge on the card's right edge (variant Б, msg 7172)",
                      abs(m["xW"] - 44) <= 1 and abs(m["xH"] - 44) <= 1 and m["xBelowCard"] >= -1 and abs(m["xRightGap"]) <= 1, m)
                check(tag, "✕ box ∩ picture box = 0 px", m["xImg"] == 0, m)
                check(tag, "✕ box ∩ card box = 0 px", m["xCard"] == 0, m)
                check(tag, "no other visible button of the window meets the picture", all(o["ov"] == 0 for o in m["others"]), m["others"])
                check(tag, "the picture keeps its proportion (not cropped)", abs(m["ratio"] / m["nat"] - 1) <= 0.01, m)
                check(tag, "the ✕ has the light disc (opaque card background) and a 1 px hairline", m["xBg"] not in ("rgba(0, 0, 0, 0)", "transparent") and m["xBorder"] == "1px", m)
                check(tag, "the ✕ is whole on the screen", m["xr"]["t"] >= -1 and m["xr"]["b"] <= m["vh"] + 1
                      and m["xr"]["l"] >= -1 and m["xr"]["r"] <= m["vw"] + 1, m)
                check(tag, "the card is whole on the screen", m["card"]["t"] >= -1 and m["card"]["b"] <= m["vh"] + 1
                      and m["card"]["l"] >= -1 and m["card"]["r"] <= m["vw"] + 1, m)
                check(tag, "✕ gold on its disc: contrast >= 3 (night too)", m["contrast"] >= 3, m)
                c.close()
            b.close()


app()
n = sum(results)
print(f"\n{n}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
