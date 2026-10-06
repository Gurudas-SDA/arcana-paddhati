"""Reader UI v5 (Satkirti 06.10.2026): two-tap contents + highlight follows the tap,
Back/Forward bar (no slider), large mood window, sub-number alignment, no translate,
no third-party requests.
usage: python v5_test.py <base-url> [shots-dir]   (ONLY=pixel,iphone ...)"""
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
DEVICES = qa.devices(['iphone14', 'pixel7', 'ipad-portrait', 'ipad-landscape', 'ipad-mini', 'ipad-pro', 'desktop'])
LANG = "ru-iast"
EMB = f"{BASE}/{LANG}/gaudiya-emblem/"
VIG = "vigraha-tattva"
EMPTY = """() => {
  const main = document.querySelector('.app-main'); const art = document.querySelector('.app-main article');
  const mr = main.getBoundingClientRect(); const ar = art.getBoundingClientRect(); const H = innerHeight;
  const bad = (el) => !el || !!el.closest('a,button,input,select,label,[role=button],img,svg,.hs-text,.hs-figure,.verse-chips,.mood-toggle,[data-no-reader-tap]');
  if (ar.left - mr.left > 80) { const p = {x: mr.left + 40, y: H / 2}; const el = document.elementFromPoint(p.x, p.y); if (!bad(el) && main.contains(el)) return p; }
  for (const p of art.querySelectorAll('p')) {
    if (p.closest('[data-hs-row]') || p.querySelector('a,button,.hs-text')) continue;
    const r = p.getClientRects()[0]; if (!r || r.top < 90 || r.bottom > H - 160 || r.width < 120) continue;
    const pt = {x: r.left + Math.min(60, r.width / 3), y: r.top + r.height / 2};
    if (!bad(document.elementFromPoint(pt.x, pt.y))) return pt;
  }
  return {x: ar.left + 6, y: H / 2};
}"""
res = []


def chk(d, n, ok, info=""):
    res.append((d, n, bool(ok), info)); print(f"  [{'PASS' if ok else 'FAIL'}] {d} {n} {'' if ok else info}")


def run(p, dev, eng, o):
    br = getattr(p, eng).launch()
    touch = o.get("has_touch", False)
    errs, foreign = [], []
    ctx = br.new_context(service_workers="block", **o)
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("request", lambda r: foreign.append(r.url) if urlparse(r.url).netloc not in (HOST, "") and not r.url.startswith(("data:", "blob:")) else None)

    def act(loc):
        loc.scroll_into_view_if_needed()
        loc.tap() if touch else loc.click(); pg.wait_for_timeout(550)

    def tap_pt(x, y):
        (pg.touchscreen.tap if touch else pg.mouse.click)(x, y); pg.wait_for_timeout(450)

    shown = lambda: pg.locator(".reader-chrome[data-shown]").count() == 1
    menu = lambda: pg.locator(".mobile-menu").count() == 1
    chap = lambda sid: pg.locator(f".mobile-menu nav button[data-toc-chapter='{sid}']")
    lit = lambda loc: loc.count() == 1 and loc.get_attribute("data-toc-lit") is not None
    nlit = lambda: pg.locator(".mobile-menu nav [data-toc-lit]").count()

    def show_bars():
        if not shown():
            pt = pg.evaluate(EMPTY); tap_pt(pt["x"], pt["y"])

    def open_contents():
        show_bars(); act(pg.locator("[data-reader-action=contents]"))

    def shot(n):
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, f"v5-{dev}-{n}.png"))

    # ---- (1)(2) contents: highlight follows the tap; two taps open ----
    pg.goto(EMB, wait_until="networkidle"); pg.wait_for_timeout(900)
    pg.evaluate("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    open_contents()
    emb = chap("gaudiya-emblem") if chap("gaudiya-emblem").count() else pg.locator(".mobile-menu nav a[href$='/gaudiya-emblem/']").first
    lit_in_emb = pg.locator(".mobile-menu nav li:has(> div > button[data-toc-chapter='gaudiya-emblem']) [data-toc-lit], .mobile-menu nav li:has(> a[href$='/gaudiya-emblem/']) [data-toc-lit], .mobile-menu nav [data-toc-lit][href$='/gaudiya-emblem/']").count()
    chk(dev, "(1) contents opens with exactly one highlight, on the open chapter (Эмблема)", nlit() == 1 and lit_in_emb >= 1, f"nlit={nlit()} in_emb={lit_in_emb}")
    act(chap(VIG))
    chk(dev, "(1) tap «Виграха-таттва» -> highlight moves to it (only one lit)", lit(chap(VIG)) and not lit(emb) and nlit() == 1, f"nlit={nlit()}")
    chk(dev, "(2) first tap: expands, no navigation, drawer open",
        chap(VIG).get_attribute("aria-expanded") == "true" and pg.url == EMB and menu(), pg.url)
    shot("1-contents-first-tap")
    act(chap(VIG)); pg.wait_for_timeout(900)
    chk(dev, "(2) second tap on the same chapter opens it", f"/{VIG}/" in pg.url and not menu(), pg.url)
    pg.go_back(); pg.wait_for_timeout(1200)
    chk(dev, "(2) Back -> contents open, chapter expanded, emblem page", menu() and pg.url == EMB and chap(VIG).get_attribute("aria-expanded") == "true", pg.url)
    pg.go_back(); pg.wait_for_timeout(1000)
    chk(dev, "(2) Back -> chapter collapsed", menu() and chap(VIG).get_attribute("aria-expanded") == "false", pg.url)
    pg.go_back(); pg.wait_for_timeout(1000)
    chk(dev, "(2) Back -> contents closed, emblem page", not menu() and pg.url == EMB, pg.url)
    # a chapter WITHOUT subsections + a subsection + «Начало главы»
    open_contents()
    plain = pg.locator(".mobile-menu nav a[href$='/mangalacarana/']").first
    if plain.count() == 0:
        plain = pg.locator(".mobile-menu nav li > a.sidebar-link:not([data-toc-cover])").first
    href = plain.get_attribute("href")
    act(plain)
    chk(dev, "(2) plain chapter: first tap highlights only", lit(plain) and menu() and pg.url == EMB and nlit() == 1, pg.url)
    act(chap(VIG))
    sub = pg.locator(f".mobile-menu #toc-ch-{VIG} a").nth(2)
    act(sub)
    chk(dev, "(2) subsection: first tap highlights only", lit(sub) and menu() and pg.url == EMB and nlit() == 1, pg.url)
    shref = sub.get_attribute("href")
    act(sub); pg.wait_for_timeout(1000)
    chk(dev, "(2) subsection: second tap opens it", not menu() and shref.split("#")[1] in pg.url, pg.url)
    pg.go_back(); pg.wait_for_timeout(1200)
    start = chap(VIG)  # [v7 law C/D, Satkirti 06.10: no «Начало главы»; Introduction group; Part I numbered from 1]
    if menu() and start.count() == 1:
        chk(dev, "(2) v7: Back -> the subsection is still lit (path)", lit(sub) and nlit() == 1, pg.url)
        act(start)
        chk(dev, "(2) chapter row: first tap highlights only", lit(start) and menu() and pg.url == EMB, pg.url)
        act(start); pg.wait_for_timeout(1000)
        chk(dev, "(2) chapter row: second tap opens chapter top", not menu() and f"/{VIG}/" in pg.url, pg.url)
    else:
        chk(dev, "(2) Back after subsection -> contents open", False, f"menu={menu()} url={pg.url}")

    # ---- (3) bottom bar ----
    pg.goto(f"{BASE}/{LANG}/{VIG}/", wait_until="networkidle"); pg.wait_for_timeout(900)
    show_bars()
    g = pg.evaluate("""() => { const r = s => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); return {l: b.left, r: b.right, w: b.width, h: b.height, t: e.textContent.trim()}; };
      return {vw: innerWidth, b: r('[data-reader-nav=back]'), f: r('[data-reader-nav=forward]'), lab: r('.reader-progress-label'),
              slider: document.querySelectorAll('.reader-slider, .reader-bar input[type=range]').length}; }""")
    vw = g["vw"]
    chk(dev, "(3) no chapter slider", g["slider"] == 0, str(g["slider"]))
    chk(dev, "(3) «‹ Назад» at left edge, «Вперёд ›» at right edge", g["b"] and g["f"] and g["b"]["l"] <= 24 and g["f"]["r"] >= vw - 24, str(g))
    chk(dev, "(3) both >= 44x44", g["b"]["w"] >= 44 and g["b"]["h"] >= 44 and g["f"]["w"] >= 44 and g["f"]["h"] >= 44, str(g))
    chk(dev, "(3) labels «Назад» / «Вперёд», faint «Глава N из M · %»", "Назад" in g["b"]["t"] and "Вперёд" in g["f"]["t"] and ("Глава" in g["lab"]["t"] or g["lab"]["t"].startswith("Виграха-таттва")) and "%" in g["lab"]["t"], str(g))
    shot("3-bottom-bar")

    # ---- (4) large mood / translation window ----
    pg.goto(f"{BASE}/{LANG}/{VIG}/", wait_until="networkidle"); pg.wait_for_timeout(900)
    act(pg.locator(".mood-toggle").first); pg.wait_for_timeout(500)
    d = pg.evaluate("""() => { const dl = document.querySelector('.mood-dialog').getBoundingClientRect();
      const q = document.querySelector('.mood-dialog .mood-quote p'); const c = document.querySelector('.mood-close').getBoundingClientRect();
      return {w: dl.width, h: dl.height, l: dl.left, t: dl.top, vw: innerWidth, vh: innerHeight, fs: parseFloat(getComputedStyle(q).fontSize), cw: c.width, ch: c.height,
              sc: getComputedStyle(document.querySelector('.mood-scroll')).overflowY}; }""")
    want_w = 0.9 if d["vw"] < 640 else (0.85 if d["vw"] < 1024 else 0.68)
    chk(dev, f"(4) window wide (>= {int(want_w*100)}% of screen) with margins", d["w"] >= want_w * d["vw"] - 1 and d["l"] >= 4, str(d))
    chk(dev, "(4) window tall enough (>= 50% height) and fits screen", d["h"] >= 0.5 * d["vh"] - 1 and d["t"] >= 0 and d["t"] + d["h"] <= d["vh"] + 1, str(d))
    chk(dev, "(4) comfortable font (>= 17px) and scrollable", d["fs"] >= 17 and d["sc"] in ("auto", "scroll"), str(d))
    chk(dev, "(4) ✕ close >= 44x44", d["cw"] >= 44 and d["ch"] >= 44, str(d))
    shot("4-mood-window")
    act(pg.locator(".mood-close")); pg.wait_for_timeout(400)
    chk(dev, "(4) ✕ closes", pg.locator(".mood-overlay").count() == 0)
    # follows «Аа»
    pg.evaluate("try{localStorage.setItem('ap.readerSize','1.22')}catch(e){}")
    fs0 = d["fs"]
    pg.evaluate("document.documentElement.style.setProperty('--reader-zoom','1.22')")
    act(pg.locator(".mood-toggle").first); pg.wait_for_timeout(400)
    fs1 = pg.evaluate("parseFloat(getComputedStyle(document.querySelector('.mood-dialog .mood-quote p')).fontSize)")
    chk(dev, "(4) window text follows «Аа»", fs1 > fs0 * 1.15, f"{fs0} -> {fs1}")
    act(pg.locator(".mood-close"))
    pg.evaluate("document.documentElement.style.removeProperty('--reader-zoom')")

    # ---- (5) numbering next to the emblem: 2.1 … 2.6 not left of the main numbers ----
    pg.goto(EMB, wait_until="networkidle"); pg.wait_for_timeout(900)
    nl = pg.evaluate("""() => { const out = [];
      for (const ol of document.querySelectorAll('ol.numbered-list')) {
        const rows = [...ol.children]; const main = rows.filter(r => !r.classList.contains('nl-sub')); const subs = rows.filter(r => r.classList.contains('nl-sub'));
        if (!subs.length) continue;
        const numL = r => r.querySelector('.nl-num .hs-text, .nl-num').getBoundingClientRect().left;
        const numR = r => r.querySelector('.nl-num').getBoundingClientRect().right;
        const txtL = r => r.children[1].getBoundingClientRect().left;
        out.push({mainNumL: Math.min(...main.map(numL)), mainNumR: Math.max(...main.map(numR)), mainTxtL: Math.min(...main.map(txtL)),
                  subNumL: Math.min(...subs.map(numL)), labels: subs.map(r => r.querySelector('.nl-num').textContent.trim())});
      } return out; }""")
    ok = len(nl) >= 1 and all(x["subNumL"] >= x["mainNumR"] - 2 and x["subNumL"] >= x["mainTxtL"] - 6 for x in nl)
    chk(dev, "(5) sub-numbers 2.1–2.6 INDENTED right of their parent «2)» (at its text line)", ok, str(nl))
    sub21 = pg.locator("ol.numbered-list .nl-sub").first
    if sub21.count():
        sub21.scroll_into_view_if_needed(); pg.evaluate("document.querySelector('.app-main').scrollBy(0, -200)"); pg.wait_for_timeout(300)
        shot("5-numbering")

    # ---- (6) no translation offers, lang attributes, no third-party hosts ----
    t6 = pg.evaluate("""async () => ({html: document.documentElement.getAttribute('translate'), body: document.body.getAttribute('translate'),
      meta: !!document.querySelector('meta[name=google][content=notranslate]'), lang: document.documentElement.lang,
      sa: document.querySelectorAll('[lang=sa-Latn]').length,
      callout: (await Promise.all([...document.querySelectorAll('link[rel=stylesheet]')].map(l => fetch(l.href).then(r => r.text()))))
        .some(t => /\.sanskrit[^{]*\{-webkit-touch-callout:none/.test(t)) ? 'none' : 'missing' })""")
    chk(dev, "(6) translate=no on <html> and <body> + google notranslate meta", t6["html"] == "no" and t6["body"] == "no" and t6["meta"], str(t6))
    chk(dev, "(6) lang: page ru, Sanskrit sa-Latn", t6["lang"] == "ru" and t6["sa"] > 5, str(t6))
    if True:
        chk(dev, "(6) no iOS callout on Sanskrit (CSS rule present)", t6["callout"] == "none", str(t6))
    chk(dev, "(6) no requests to third-party hosts", not foreign, "; ".join(foreign[:5]))
    chk(dev, "no page errors", not errs, "; ".join(errs[:3]))
    ctx.close(); br.close()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        if ONLY and dev not in ONLY.split(","):
            continue
        print(dev)
        try:
            run(p, dev, eng, o)
        except Exception as e:
            chk(dev, "EXCEPTION", False, str(e)[:900])
fails = [r for r in res if not r[2]]
print(f"\n{len(res) - len(fails)}/{len(res)} passed")
for f in fails:
    print("FAILED:", f[0], f[1], f[3][:300])
