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
EMPTY = """root => {
  const main = document.querySelector('.app-main'); const art = root.querySelector('article');
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
    res.append((d, n, bool(ok), info)); print(f"  [{'PASS' if ok else 'FAIL'}] {d} {n} [toc={qa.TOC_MODE_NAME}] {'' if ok else info}")


def run(p, dev, eng, o, mode):
    from toc import Contents, history_roundtrip, marks_place
    br = getattr(p, eng).launch()
    touch = o.get("has_touch", False)
    errs, foreign = [], []
    ctx = br.new_context(service_workers="block", **o)
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("request", lambda r: foreign.append(r.url) if urlparse(r.url).netloc not in (HOST, "") and not r.url.startswith(("data:", "blob:")) else None)

    flow=Contents(pg,mode,touch)

    def act(loc):
        loc.scroll_into_view_if_needed()
        loc.tap() if touch else loc.click(); pg.wait_for_timeout(550)

    def tap_pt(x, y):
        (pg.touchscreen.tap if touch else pg.mouse.click)(x, y); pg.wait_for_timeout(450)

    shown = lambda: pg.locator(".reader-chrome[data-shown]").count() == 1
    menu = lambda: pg.locator(".mobile-menu[data-open]").count() == 1
    chap = lambda sid: pg.locator(f".mobile-menu[data-open] nav button[data-toc-chapter='{sid}']")
    lit = lambda loc: loc.count() == 1 and loc.get_attribute("data-toc-lit") is not None
    lit_in_emb_now = lambda: pg.locator(".mobile-menu[data-open] nav [data-toc-lit][href$='/gaudiya-emblem/'], .mobile-menu[data-open] nav [data-toc-lit][data-toc-chapter='gaudiya-emblem'], .mobile-menu[data-open] nav li:has(> div > button[data-toc-chapter='gaudiya-emblem']) [data-toc-lit]").count() >= 1
    nlit = lambda: pg.locator(".mobile-menu[data-open] nav [data-toc-lit]").count()

    def show_bars():
        if not shown():
            pt = qa.reading_eval(pg, EMPTY); tap_pt(pt["x"], pt["y"])

    def open_contents():
        show_bars(); act(pg.locator("[data-reader-action=contents]"))

    def shot(n):
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, f"v5-{dev}-{n}.png"))

    mode.start(pg,EMB);pg.wait_for_timeout(600);open_contents()
    chk(dev,'(1) contents opens with exactly one highlight, on the open chapter (Эмблема)',nlit()==1 and lit_in_emb_now())
    before=flow.state();flow.tap(chap(VIG),right=True,wait=350);first=flow.state()
    chk(dev,'(1) tap «Виграха-таттва» -> highlight moves to it (only one lit)',first['lit']==['sec:'+VIG])
    chk(dev,'(2) first tap: default opens chapter top + list; legacy highlights only',first['menu'] and ((VIG in first['open'] and first['url'].endswith('/'+VIG+'/') and abs(pg.evaluate(qa.READING_POSITION_JS)['top'])<2) if mode.one else VIG not in first['open'] and pg.url==EMB),str(first))
    flow.tap(chap(VIG),right=True,wait=350);second=flow.state()
    chk(dev,'(2) second tap on the same chapter: collapses default / expands legacy, no navigation',(VIG in second['open'])!=mode.one and second['url']==first['url'] and second['lit']==['sec:'+VIG],str(second))
    flow.nav('back',native=True);state=flow.state()
    chk(dev,'(2) Back -> the preceding chapter state, still lit',(VIG in state['open'])==mode.one and state['lit']==['sec:'+VIG] and state['url']==first['url'],str(state))
    flow.nav('back',native=True);state=flow.state()
    chk(dev,'(2) Back -> contents as opened, reading place marked',state['menu'] and pg.url==EMB and (state['open']==before['open'] and marks_place(state) if mode.one else state['lit']==before['lit']),str(state))
    flow.nav('back',native=True)
    chk(dev,'(2) Back -> contents closed, emblem page',not menu() and pg.url==EMB)
    open_contents();plain=pg.locator('.mobile-menu[data-open] [data-toc-row="sec:mangalacarana"]');u0=flow.state()['url'];flow.tap(plain,wait=350)
    chk(dev,'(2) plain chapter: first tap follows the mode',not menu() and pg.url.endswith('/mangalacarana/') if mode.one else menu() and pg.url==EMB and lit(plain) and nlit()==1,pg.url)
    if mode.one:flow.nav('back',native=True)
    flow.activate(chap(VIG));sub=pg.locator(f'#toc-ch-{VIG} a').nth(2);shref=sub.get_attribute('href');anchor=shref.split('#')[1];before_sub=flow.state();u0=before_sub['url']
    flow.tap(sub,wait=350)
    chk(dev,'(2) subsection: first tap follows the mode',not menu() and pg.url.endswith('#'+anchor) if mode.one else menu() and lit(sub) and nlit()==1 and flow.state()['url']==u0,pg.url)
    if not mode.one:flow.tap(sub,wait=350)
    chk(dev,'(2) subsection: action tap opens it',not menu() and pg.url.endswith('#'+anchor),pg.url)
    flow.nav('back',native=True)
    chk(dev,'(2) Back -> preceding Contents action, reading place marked',menu() and flow.state()['url']==before_sub['url'] and flow.state()['open']==before_sub['open'] and marks_place(flow.state()))
    u0=flow.state()['url'];flow.tap(chap(VIG),right=True)
    chk(dev,'(2) chapter row: first tap follows the mode',(VIG in flow.state()['open'])!=mode.one and flow.state()['lit']==['sec:'+VIG] and flow.state()['url']==u0)
    flow.tap(chap(VIG),right=True)
    chk(dev,'(2) chapter row: second tap toggles its list without leaving the chapter',(VIG in flow.state()['open'])==mode.one and flow.state()['url']==u0)

    # Finish the menu scenario before measuring unrelated reading controls.
    if menu():
        flow.tap(pg.locator('.mobile-menu[data-open] button[aria-label="Закрыть меню"]'),wait=700)
    chk(dev,'(2) menu scenario closes before reader geometry checks',not menu())
    # ---- (3) bottom bar ----
    pg.goto(f"{BASE}/{LANG}/{VIG}/", wait_until="networkidle"); pg.wait_for_timeout(900)
    show_bars()
    g = pg.evaluate("""() => { const r = s => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); return {l: b.left, r: b.right, w: b.width, h: b.height, t: e.textContent.trim()}; };
      return {vw: innerWidth, b: r('[data-reader-nav=back]'), f: r('[data-reader-nav=forward]'), lab: r('.reader-bar-bottom .reader-progress-label'), status: r('.reader-status'),
              slider: document.querySelectorAll('.reader-slider, .reader-bar input[type=range]').length}; }""")
    vw = g["vw"]
    chk(dev, "(3) no chapter slider", g["slider"] == 0, str(g["slider"]))
    chk(dev, "(3) «‹ Назад» at left edge, «Вперёд ›» at right edge", g["b"] and g["f"] and g["b"]["l"] <= 24 and g["f"]["r"] >= vw - 24, str(g))
    chk(dev, "(3) both >= 44x44", g["b"]["w"] >= 44 and g["b"]["h"] >= 44 and g["f"]["w"] >= 44 and g["f"]["h"] >= 44, str(g))
    # V17 (Vraja Lila msg 796): no «where we are / %» line in the bar; the faint status line at the bottom stays
    chk(dev, "(3) labels «Назад» / «Вперёд»; no «глава · %» in the bar, faint status line «глава · %» stays", "Назад" in g["b"]["t"] and "Вперёд" in g["f"]["t"] and g["lab"] is None and g["status"] and g["status"]["t"].startswith("Виграха-таттва") and "%" in g["status"]["t"], str(g))
    shot("3-bottom-bar")

    # ---- (4) large mood / translation window ----
    pg.goto(f"{BASE}/{LANG}/{VIG}/", wait_until="networkidle"); pg.wait_for_timeout(900)
    act(qa.reading_locator(pg,".mood-toggle").first); pg.wait_for_timeout(500)
    d = pg.evaluate("""() => { const dl = document.querySelector('.mood-dialog').getBoundingClientRect();
      const q = document.querySelector('.mood-dialog .mood-quote p'); const c = document.querySelector('.mood-close').getBoundingClientRect();
      return {w: dl.width, h: dl.height, l: dl.left, t: dl.top, vw: innerWidth, vh: innerHeight, fs: parseFloat(getComputedStyle(q).fontSize), cw: c.width, ch: c.height,
              sc: getComputedStyle(document.querySelector('.mood-scroll')).overflowY}; }""")
    want_w = 0.9 if d["vw"] < 640 else (0.85 if d["vw"] < 1024 else 0.68)
    chk(dev, f"(4) window wide (>= {int(want_w*100)}% of screen) with margins", d["w"] >= want_w * d["vw"] - 1 and d["l"] >= 4, str(d))
    chk(dev, "(4) window tall enough (>= 50% height) and fits screen", d["h"] >= 0.5 * d["vh"] - 1 and d["t"] >= 0 and d["t"] + d["h"] <= d["vh"] + 1, str(d))
    chk(dev, "(4) comfortable font (>= 17px) and scrollable", d["fs"] >= 17 and d["sc"] in ("auto", "scroll"), str(d))
    chk(dev, "(4) ✕ close >= 44x44", d["cw"] >= 44 and d["ch"] >= 44, str(d))
    # «Стандарты» 21а (Satkirti 18.10 msg 4527): quotes in the opened block numbered 1 … N; Satkirti 18.10
    # msg 4497–4519: no «машинный перевод» mark at the quotes.
    nm = pg.evaluate("""() => ({nums: [...document.querySelectorAll('.mood-dialog .mood-num')].map(e => e.textContent.trim()),
      quotes: document.querySelectorAll('.mood-dialog .mood-quote').length,
      machine: /машинн/i.test(document.querySelector('.mood-dialog').textContent)})""")
    chk(dev, "(4) 21а: quotes numbered 1 … N in the opened block", nm["quotes"] >= 1 and nm["nums"] == [f"{i}." for i in range(1, nm["quotes"] + 1)], str(nm))
    chk(dev, "(4) no «машинный перевод» mark at the quotes", not nm["machine"], str(nm))
    shot("4-mood-window")
    act(pg.locator(".mood-close")); pg.wait_for_timeout(400)
    chk(dev, "(4) ✕ closes", pg.locator(".mood-overlay").count() == 0)
    # follows «Аа»
    pg.evaluate("try{localStorage.setItem('ap.readerSize','1.22')}catch(e){}")
    fs0 = d["fs"]
    pg.evaluate("document.documentElement.style.setProperty('--reader-zoom','1.22')")
    act(qa.reading_locator(pg,".mood-toggle").first); pg.wait_for_timeout(400)
    fs1 = pg.evaluate("parseFloat(getComputedStyle(document.querySelector('.mood-dialog .mood-quote p')).fontSize)")
    chk(dev, "(4) window text follows «Аа»", fs1 > fs0 * 1.15, f"{fs0} -> {fs1}")
    act(pg.locator(".mood-close"))
    pg.evaluate("document.documentElement.style.removeProperty('--reader-zoom')")

    # ---- (5) numbering next to the emblem: 2.1 … 2.6 not left of the main numbers ----
    pg.goto(EMB, wait_until="networkidle"); pg.wait_for_timeout(900)
    nl = qa.reading_eval(pg,"""root => { const out = [];
      for (const ol of root.querySelectorAll('ol.numbered-list')) {
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
    sub21 = qa.reading_locator(pg,"ol.numbered-list .nl-sub").first
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
            qa.run_toc_modes(lambda mode:run(p,dev,eng,o,mode),on_error=lambda e:chk(dev,"EXCEPTION",False,str(e)[:900]))
        except Exception as e:
            chk(dev, "EXCEPTION", False, str(e)[:900])
fails = [r for r in res if not r[2]]
print(f"\n{len(res) - len(fails)}/{len(res)} passed")
for f in fails:
    print("FAILED:", f[0], f[1], f[3][:300])
