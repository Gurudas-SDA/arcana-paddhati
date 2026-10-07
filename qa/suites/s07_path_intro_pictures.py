"""Reader v7 (Satkirti 06.10.2026) — real behaviour on 7 device profiles.
usage: python v7_test.py <base-url> [shots-dir]   (ONLY=pixel,iphone ...)
A path highlight in «Содержание» + stepwise Back (‹ Назад button + system/browser back),
  part / Introduction headings highlight, lit row scrolled into view (rects), computed colours
B «Вперёд ›» steps forward (button), never a dead/disabled tap, note when no step, bars unselectable
C no «Начало главы» row
D Introduction = expandable group (Emblem, Vigraha-tattva, Maṅgalācaraṇa), no chapter numbers,
  second tap collapses; numbering 1.. from Part I; «След. глава ›» order; Introduction page list
E picture <-> list: tap on a picture part -> row highlighted (computed bg) + scrolled into view;
  tap on a row -> picture part highlighted; emblem, Tilak, Parafernalia
F cover: no «v.1», CA block (emblem left, text right, centred), cover fully on screen
G Maṅgalācaraṇa: title only, no subtitle, no explanatory headings; every verse has «пословно»
H «Праздники, обеты и песни арати» (+ English)
I every verse of the book (ru-iast, ru) has a «пословно» chip in the UI (241 = 180 + 61 verses of the ārati songs, v7.4)
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "lib"))
import qa
VERSES = 241  # 180 + 61 verses of the maṅgala-/gaura-ārati songs (Reader v7.4, Satkirti 07.10 13:07)
import io, json, os, sys, urllib.request
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/"); SHOTS = sys.argv[2] if len(sys.argv) > 2 else None
ONLY = None  # device filter: QA_DEVICES (qa/lib/qa.py)
HOST = urlparse(BASE).netloc
IOS_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
IPAD_UA = IOS_UA.replace("iPhone; CPU iPhone OS", "iPad; CPU OS")
PIXEL_UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36")
S23_UA = ("Mozilla/5.0 (Linux; Android 14; SM-S711B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36")
MAC_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15")
DEVICES = qa.devices(['pixel7', 's23fe', 'iphone14', 'ipad-portrait', 'ipad-landscape', 'desktop', 'mac-safari'])
L = "ru-iast"
LIT_BG = "rgb(250, 243, 232)"
res = []


def chk(d, n, ok, info=""):
    res.append((d, n, bool(ok), info)); print(f"  [{'PASS' if ok else 'FAIL'}] {d} {n} {'' if ok else info}", flush=True)


LIT = """() => { const nav = document.querySelector('.mobile-menu nav'); if (!nav) return {menu: false};
  const lits = [...nav.querySelectorAll('[data-toc-lit]')]; if (!lits.length) return {menu: true, n: 0};
  const el = lits[0]; const box = el.matches('[data-toc-group]') ? el.parentElement : el;
  const r = box.getBoundingClientRect(), nr = nav.getBoundingClientRect();
  const txt = el.querySelector('span') || el;
  return {menu: true, n: lits.length, group: el.getAttribute('data-toc-group'), chapter: el.getAttribute('data-toc-chapter'),
    href: el.getAttribute('href'), text: el.textContent.trim().slice(0, 70),
    inView: r.top >= nr.top - 1 && r.bottom <= nr.bottom + 1 && r.height > 0,
    bg: getComputedStyle(box).backgroundColor, color: getComputedStyle(txt).color}; }"""

EMPTY_PT = """() => { const main = document.querySelector('.app-main'); const art = document.querySelector('.app-main article');
  const H = innerHeight; const bad = (el) => !el || !!el.closest('a,button,input,select,label,[role=button],img,svg,.hs-text,.hs-figure,.verse-chips,.mood-toggle,[data-no-reader-tap]');
  if (!art) return {x: innerWidth / 2, y: H / 2};
  for (const p of art.querySelectorAll('p, h1')) { if (p.closest('[data-hs-row]') || p.querySelector('a,button,.hs-text')) continue;
    const r = p.getClientRects()[0]; if (!r || r.top < 90 || r.bottom > H - 160 || r.width < 60) continue;
    const pt = {x: r.left + Math.min(30, r.width / 3), y: r.top + r.height / 2}; if (!bad(document.elementFromPoint(pt.x, pt.y))) return pt; }
  const ar = art.getBoundingClientRect(); return {x: Math.max(4, ar.left - 6), y: H / 2}; }"""


def run(p, dev, eng, o):
    br = getattr(p, eng).launch()
    touch = o.get("has_touch", False)
    errs, foreign = [], []
    ctx = br.new_context(service_workers="block", **o)
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("request", lambda r: foreign.append(r.url) if urlparse(r.url).netloc not in (HOST, "") and not r.url.startswith(("data:", "blob:")) else None)
    n_shot = [0]

    def shot(name):
        if SHOTS:
            n_shot[0] += 1
            pg.screenshot(path=os.path.join(SHOTS, f"v7-{dev}-{n_shot[0]:02d}-{name}.png"))

    def tap_xy(x, y):
        (pg.touchscreen.tap if touch else pg.mouse.click)(x, y)

    def act(loc, wait=650, force=False):
        loc.scroll_into_view_if_needed()
        loc.tap(force=force) if touch else loc.click(force=force)
        pg.wait_for_timeout(wait)

    def bars():
        if pg.locator(".reader-chrome[data-shown]").count():
            return True
        pt = pg.evaluate(EMPTY_PT); tap_xy(pt["x"], pt["y"]); pg.wait_for_timeout(450)
        return pg.locator(".reader-chrome[data-shown]").count() > 0

    def contents():
        bars(); act(pg.locator("[data-reader-action=contents]"), 700)
        return pg.locator(".mobile-menu").count() > 0

    def lit():
        return pg.evaluate(LIT)

    def goto(path):
        pg.goto(f"{BASE}{path}", wait_until="networkidle"); pg.wait_for_timeout(700)

    goto(f"/{L}/daily-duties-brahma-muhurta/")
    pg.evaluate("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    goto(f"/{L}/daily-duties-brahma-muhurta/")
    P0 = pg.url

    # ---------- A + C + D: path through the contents ----------
    chk(dev, "A open «Содержание»", contents())
    g = lit()
    chk(dev, "A fresh contents: one row lit = current chapter, in view, beige band", g.get("n") == 1 and g.get("chapter") == "daily-duties-brahma-muhurta" and g["inView"] and g["bg"] == LIT_BG, str(g))
    chk(dev, "C no «Начало главы» row (open chapter list)", pg.locator(".mobile-menu [data-toc-chapter-start]").count() == 0 and "Начало главы" not in pg.locator(".mobile-menu nav").inner_text(), "")
    first = pg.locator(".mobile-menu #toc-ch-daily-duties-brahma-muhurta li").first.inner_text().strip()
    chk(dev, "C chapter list starts with subsection «1.1.»", first.startswith("1.1."), first)
    intro = pg.locator(".mobile-menu [data-toc-group=introduction]")
    chk(dev, "D «Введение» is a group heading without number", intro.count() == 1 and intro.inner_text().strip().upper() == "ВВЕДЕНИЕ", intro.inner_text() if intro.count() else "none")
    act(intro)
    g = lit()
    rows = pg.locator(".mobile-menu #toc-grp-introduction > li")
    names = [rows.nth(i).inner_text().strip() for i in range(rows.count())]
    chk(dev, "D tap «Введение» -> expands: Эмблема / Виграха-таттва (Мангалачарана before Введение — v7.1), no numbers", names == ["Эмблема Гаудия-матха", "Виграха-таттва"], str(names))
    chk(dev, "A «Введение» heading lit (like a subsection), in view, one highlight", g.get("n") == 1 and g.get("group") == "introduction" and g["inView"] and g["bg"] == LIT_BG and g["color"] == "rgb(184, 134, 11)", str(g))
    act(intro)
    chk(dev, "D second tap on «Введение» collapses it", intro.get_attribute("aria-expanded") == "false" and pg.locator(".mobile-menu #toc-grp-introduction").count() == 0)
    chk(dev, "A after collapse the heading stays lit", lit().get("group") == "introduction", str(lit()))
    act(intro)
    vig = pg.locator(".mobile-menu [data-toc-chapter=vigraha-tattva]")
    act(vig)
    g = lit()
    chk(dev, "A tap «Виграха-таттва» -> lit + its list open", g.get("chapter") == "vigraha-tattva" and g.get("n") == 1 and pg.locator(".mobile-menu #toc-ch-vigraha-tattva").count() == 1, str(g))
    tota = pg.locator('.mobile-menu a[href*="#vigraha-tota-gopinatha"]')
    tt = tota.inner_text().strip()
    chk(dev, "D subsection numbering inside the Introduction: «10. Тота Гопинатх…»", tt.startswith("10."), tt)
    act(tota)
    g = lit()
    chk(dev, "A first tap on «Тота Гопинатх» only highlights it", g.get("href", "").endswith("#vigraha-tota-gopinatha") and pg.url == P0 and pg.locator(".mobile-menu").count() == 1, str(g))
    shot("toc-path-tota")
    act(tota, 1100)
    chk(dev, "A second tap opens «Тота Гопинатх»", "/vigraha-tattva/" in pg.url and pg.url.endswith("#vigraha-tota-gopinatha") and pg.locator(".mobile-menu").count() == 0, pg.url)
    P1 = pg.url
    # ‹ Назад (the reader's own button)
    bars(); act(pg.locator("[data-reader-nav=back]"), 1100)
    g = lit()
    chk(dev, "A ‹ Назад -> contents, «Тота Гопинатх» still lit and in view (iPad case)", g.get("menu") and g.get("n") == 1 and (g.get("href") or "").endswith("#vigraha-tota-gopinatha") and g["inView"] and g["bg"] == LIT_BG, str(g))
    shot("back-1-tota-lit")
    # next steps back: system / browser back (Android)
    pg.go_back(); pg.wait_for_timeout(900)
    g = lit()
    # v7.1 (verifier item 17): every Back step shows the state the reader saw at
    # that step (no step with the same highlight twice): «Введение» lit, group
    # open, the Виграха-таттва list closed.
    chk(dev, "A Back step 2 -> «Введение» lit, group open, Виграха list closed (v7.1)", g.get("group") == "introduction" and g["inView"] and pg.locator(".mobile-menu #toc-grp-introduction").count() == 1 and pg.locator(".mobile-menu #toc-ch-vigraha-tattva").count() == 0, str(g))
    shot("back-2-vigraha-lit")
    pg.go_back(); pg.wait_for_timeout(900)
    g = lit()
    chk(dev, "A Back step 3 -> «Введение» lit, group closed", g.get("group") == "introduction" and pg.locator(".mobile-menu #toc-grp-introduction").count() == 0 and g["inView"], str(g))
    shot("back-3-intro-lit")
    pg.go_back(); pg.wait_for_timeout(900)
    chk(dev, "A Back step 4 -> menu closed, the page where the reader was", pg.locator(".mobile-menu").count() == 0 and pg.url == P0, pg.url)

    # ---------- B: «Вперёд ›» steps forward ----------
    bars()
    fw = pg.locator("[data-reader-nav=forward]")
    chk(dev, "B «Вперёд» is a live button (not disabled)", fw.get_attribute("disabled") is None and fw.get_attribute("aria-disabled") == "false", str(fw.get_attribute("aria-disabled")))
    act(fw, 1000)
    g = lit()
    chk(dev, "B «Вперёд» -> step forward: contents, «Введение» lit", g.get("menu") and g.get("group") == "introduction", str(g))
    for _ in range(2):
        pg.go_forward(); pg.wait_for_timeout(800)
    g = lit()
    chk(dev, "B forward steps retrace the path («Тота Гопинатх» lit)", (g.get("href") or "").endswith("#vigraha-tota-gopinatha"), str(g))
    pg.go_forward(); pg.wait_for_timeout(1000)
    chk(dev, "B forward -> «Тота Гопинатх» page again", pg.url == P1 and pg.locator(".mobile-menu").count() == 0, pg.url)

    # ---------- A: part headings highlight ----------
    contents()
    g = lit()
    chk(dev, "A contents on Тота Гопинатх page: that subsection lit by default", (g.get("href") or "").endswith("#vigraha-tota-gopinatha") and g["inView"], str(g))
    temple = pg.locator(".mobile-menu [data-toc-group=temple-worship]")
    act(temple)
    g = lit()
    chk(dev, "A tap «Храмовый стандарт» -> it is lit (only it)", g.get("group") == "temple-worship" and g.get("n") == 1 and g["bg"] == LIT_BG, str(g))
    fv = pg.locator(".mobile-menu [data-toc-group=festivals-vows]")
    chk(dev, "H part title «Праздники, обеты и песни арати»", "ПРАЗДНИКИ, ОБЕТЫ И ПЕСНИ АРАТИ" in fv.inner_text().upper(), fv.inner_text())
    act(fv)
    g = lit()
    chk(dev, "A tap «Праздники, обеты и песни арати» -> lit moves there", g.get("group") == "festivals-vows" and g.get("n") == 1 and g["inView"], str(g))
    shot("part-heading-lit")
    pre = pg.locator(".mobile-menu [data-toc-group=preaching-centres]")
    act(pre)
    chk(dev, "A tap «Стандарт для проповеднических центров» -> lit", lit().get("group") == "preaching-centres", str(lit()))
    # numbering of Part I
    act(temple) if pg.locator(".mobile-menu #toc-part-temple-worship").count() == 0 else None
    t1 = pg.locator(".mobile-menu [data-toc-chapter=daily-duties-brahma-muhurta]").inner_text().strip()
    chk(dev, "D Part I starts with chapter «1.»", t1.startswith("1."), t1)

    # ---------- B: no forward step -> note, no dead tap ----------
    goto(f"/{L}/offering-bhoga/")
    u0 = pg.url
    bars(); fw = pg.locator("[data-reader-nav=forward]")
    sel = pg.evaluate("(() => { const b = document.querySelector('.reader-bar-bottom'); const s = getComputedStyle(b); return s.userSelect || s.webkitUserSelect; })()")
    chk(dev, "B bars' text is not selectable (no look-up bar on Android)", sel == "none", str(sel))
    act(fw, 900, force=True)  # aria-disabled: Playwright would refuse a normal tap
    note = pg.locator("[data-reader-nav-note]")
    chk(dev, "B «Вперёд» with no step: stays, says ««Вперёд» — после «Назад»»", pg.url == u0 and note.count() == 1 and "после" in note.inner_text(), pg.url)
    if note.count():
        nb = note.bounding_box(); bb = pg.locator(".reader-bar-bottom").bounding_box()
        chk(dev, "B the note sits above the bottom bar, on screen", nb["y"] + nb["height"] <= bb["y"] + 1 and nb["x"] >= 0 and nb["x"] + nb["width"] <= o["viewport"]["width"] + 1, f"{nb} {bb}")
        shot("forward-note")
    # next chapter -> back -> forward with the buttons
    pg.evaluate("(() => { const m = document.querySelector('.app-main'); m.scrollTop = m.scrollHeight; })()"); pg.wait_for_timeout(500)
    act(pg.locator(".chapter-next-link"), 1100)
    u1 = pg.url
    chk(dev, "D «След. глава ›» after offering-bhoga -> 7. Мантры почитания чаранамриты", u1.rstrip("/").endswith("/mantras-honouring-caranamrita"), u1)
    bars(); act(pg.locator("[data-reader-nav=back]"), 1000)
    chk(dev, "B ‹ Назад -> previous chapter", pg.url == u0, pg.url)
    bars(); act(pg.locator("[data-reader-nav=forward]"), 1000)
    chk(dev, "B «Вперёд ›» -> next chapter again (Android case)", pg.url == u1, pg.url)

    # ---------- D: pages ----------
    goto(f"/{L}/introduction/")
    links = pg.locator(".group-contents a")
    chk(dev, "D Introduction page lists its 2 chapters (v7.1)", links.count() == 2, str(links.count()))
    nx = pg.locator(".chapter-next-title")
    chk(dev, "D Introduction «След. глава ›» -> «Эмблема Гаудия-матха» (no number)", nx.count() == 1 and nx.inner_text().strip() == "Эмблема Гаудия-матха", nx.inner_text() if nx.count() else "")
    goto(f"/{L}/mangalacarana/")
    nx = pg.locator(".chapter-next-title").inner_text().strip()
    chk(dev, "D Мангалачарана «След. глава ›» -> «Введение» (v7.1)", nx == "Введение", nx)
    goto(f"/{L}/vigraha-tattva/")
    h1 = pg.locator(".app-main article h1")
    chk(dev, "D Виграха-таттва page: no chapter number in the title", h1.locator(".heading-num").count() == 0, h1.inner_text())
    st = pg.locator(".reader-status").inner_text()
    chk(dev, "D status line names the chapter (no «Глава N»)", st.startswith("Виграха-таттва"), st)
    goto(f"/{L}/daily-deity-schedule/")
    st = pg.locator(".reader-status").inner_text()
    chk(dev, "D status line «Глава 2 · …»", st.startswith("Глава 2 "), st)

    # ---------- G: Maṅgalācaraṇa ----------
    goto(f"/{L}/mangalacarana/")
    head = pg.evaluate("(() => { const h = document.querySelector('.app-main article header'); return {h1: h.querySelector('h1').textContent.trim(), ps: h.querySelectorAll('p').length,"
                       " h2: [...document.querySelectorAll('.app-main article h2')].map(e => e.textContent.trim()),"
                       " verses: document.querySelectorAll('.app-main article .verse-chips').length,"
                       " wbw: [...document.querySelectorAll('.app-main article .verse-chips')].filter(c => /пословно/.test(c.textContent)).length}; })()")
    chk(dev, "G title only «Мангалачарана», no subtitle", head["h1"] == "Мангалачарана" and head["ps"] == 0, str(head)[:200])
    chk(dev, "G v7.1 no headings at all on the page", not head["h2"], str(head["h2"])[:120])
    bad = [h for h in head["h2"] if "Прославление" in h or "покровител" in h or "призывающ" in h]
    chk(dev, "G no explanatory headings (прославление / покровитель / призывающие)", not bad, str(bad))
    chk(dev, "G every verse has «пословно»", head["verses"] > 20 and head["verses"] == head["wbw"], f"{head['wbw']}/{head['verses']}")
    if dev in ("iphone14", "ipad-portrait", "desktop"):
        shot("mangalacarana")

    # ---------- E: picture <-> list ----------
    def spot_test(page, spots, label):
        goto(page)
        fig = pg.locator(".hs-figure").first
        for n in spots:
            # picture at the top of the screen, list below (off-screen on phones)
            pg.evaluate("(() => { const m = document.querySelector('.app-main'); const f = document.querySelector('.hs-figure'); m.scrollTop += f.getBoundingClientRect().top - 70; })()")
            pg.wait_for_timeout(400)
            if pg.locator(".hs-row[data-active]").count():
                pt = pg.evaluate(EMPTY_PT); tap_xy(pt["x"], pt["y"]); pg.wait_for_timeout(300)
                pg.evaluate("(() => { const m = document.querySelector('.app-main'); const f = document.querySelector('.hs-figure'); m.scrollTop += f.getBoundingClientRect().top - 70; })()")
                pg.wait_for_timeout(300)
            pt = pg.evaluate("""(n) => { const g = [...document.querySelectorAll('.hs-figure .hs-hit')].find(e => e.getAttribute('aria-label') === n);
                const cands = [...g.querySelectorAll('ellipse, circle')].map(e => e.getBoundingClientRect()).map(r => ({x: r.left + r.width / 2, y: r.top + r.height / 2}));
                for (const c of cands.reverse()) { const el = document.elementFromPoint(c.x, c.y); if (el && el.closest('.hs-hit') === g) return c; }
                return null; }""", n)
            if not pt:
                chk(dev, f"E {label} spot {n}: reachable tap point", False, "no point hits the spot"); continue
            tap_xy(pt["x"], pt["y"]); pg.wait_for_timeout(1300)
            r = pg.evaluate("""() => { const row = document.querySelector('.hs-row[data-active]'); if (!row) return null; const rr = row.getBoundingClientRect();
                const bar = document.querySelector('.reader-chrome[data-shown] .reader-bar-bottom'); const lim = bar ? bar.getBoundingClientRect().top : innerHeight;
                return {top: rr.top, bottom: rr.bottom, vh: innerHeight, lim, bg: getComputedStyle(row.querySelector('.hs-text')).backgroundColor,
                  text: row.textContent.trim().slice(0, 40), faded: !!document.querySelector('.hs-img-faded'), lit: !!document.querySelector('.hs-figure .hs-lit')}; }""")
            ok = bool(r) and r["top"] >= 0 and r["bottom"] <= r["lim"] + 1 and r["bg"].startswith("rgba(212, 168, 67") and r["faded"] and r["lit"]
            chk(dev, f"E {label}: tap picture part {n} -> part + row highlighted, list scrolled to the row", ok, str(r))
            if n == spots[0] and SHOTS and dev in ("pixel7", "s23fe", "iphone14", "ipad-portrait"):
                shot(f"emblem-row-{label}")
        # row -> picture
        pt = pg.evaluate(EMPTY_PT); tap_xy(pt["x"], pt["y"]); pg.wait_for_timeout(300)
        row = pg.locator(".hs-row .hs-text").nth(2)
        act(row, 700)
        r = pg.evaluate("(() => ({row: !!document.querySelector('.hs-row[data-active]'), bg: (document.querySelector('.hs-row[data-active] .hs-text')||document.body).style && getComputedStyle(document.querySelector('.hs-row[data-active] .hs-text')).backgroundColor, faded: !!document.querySelector('.hs-img-faded'), lit: document.querySelectorAll('.hs-lit').length}))()")
        chk(dev, f"E {label}: tap a list row -> row band + picture part highlighted", r["row"] and r["faded"] and r["lit"] >= 1 and r["bg"].startswith("rgba(212, 168, 67"), str(r))

    spot_test(f"/{L}/gaudiya-emblem/", ["3", "2.1", "10", "11", "12"], "emblem")
    spot_test(f"/{L}/daily-duties-brahma-muhurta/", ["5"], "tilak")
    spot_test(f"/{L}/worship-sixteen-articles/", ["7"], "paraphernalia")

    # ---------- F: cover ----------
    goto(f"/{L}/")
    c = pg.evaluate("(() => { const i = document.querySelector('img.home-cover'); const r = i.getBoundingClientRect(); return {l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, vw: innerWidth, vh: innerHeight, nw: i.naturalWidth, src: i.currentSrc}; })()")
    chk(dev, "F cover fully on screen", c["l"] >= 0 and c["t"] >= 0 and c["r"] <= c["vw"] + 0.5 and c["b"] <= c["vh"] + 0.5 and c["nw"] == 874, str(c))
    shot("cover")

    # ---------- H: English ----------
    goto("/vigraha-tattva/")
    contents()
    en = pg.locator(".mobile-menu [data-toc-group=festivals-vows]").inner_text().strip().upper()
    chk(dev, "H English part title «Festivals, Vows and Ārati Songs»", "FESTIVALS, VOWS AND ĀRATI SONGS" in en, en)
    chk(dev, "D English: «Introduction» group heading", pg.locator(".mobile-menu [data-toc-group=introduction]").inner_text().strip().upper() == "INTRODUCTION")

    # ---------- I: every verse has «пословно» (one profile per engine family is enough for data; all pages) ----------
    if dev in ("desktop", "iphone14"):
        ids = json.load(urllib.request.urlopen(f"{BASE}/search-index.{L}.json"))
        secs = sorted({e["section"] for e in ids})
        for lang in ("ru-iast", "ru"):
            tv = tw = 0; missing = []
            for sid in secs:
                pg.goto(f"{BASE}/{lang}/{sid}/", wait_until="domcontentloaded"); pg.wait_for_timeout(250)
                v = pg.evaluate("(() => { const c = [...document.querySelectorAll('.app-main article .verse-chips')]; return [c.length, c.filter(x => /пословно/.test(x.textContent)).length]; })()")
                tv += v[0]; tw += v[1]
                if v[0] != v[1]: missing.append(f"{sid}:{v[1]}/{v[0]}")
            chk(dev, f"I {lang}: every verse in the UI has «пословно» ({tw}/{tv}, {VERSES} expected)", tv == tw == VERSES, "; ".join(missing))

    chk(dev, "no requests to third-party hosts", not foreign, "; ".join(foreign[:5]))
    chk(dev, "no page errors", not errs, "; ".join(errs[:3]))
    ctx.close(); br.close()


def cover_pixels():
    from PIL import Image
    im = Image.open(io.BytesIO(urllib.request.urlopen(f"{BASE}/cover.jpg").read())).convert("RGB")
    W, H = im.size
    px = im.load()
    dark = lambda c: sum(c) < 330
    red = lambda c: c[0] > 170 and c[1] < 110 and c[2] < 110
    # «v.1» was at the top right inside the frame (x 760-820, y 80-110 at 874 px)
    v1 = sum(1 for x in range(740, 830) for y in range(75, 115) if dark(px[x, y]))
    chk("cover", "F no «v.1» mark at the top right", v1 == 0, f"{v1} dark px")
    reds = [(x, y) for x in range(W) for y in range(1040, 1200) if red(px[x, y])]
    darks = [(x, y) for x in range(W) for y in range(1040, 1200) if dark(px[x, y]) and not red(px[x, y])]
    rx = (min(p[0] for p in reds), max(p[0] for p in reds)); dx = (min(p[0] for p in darks), max(p[0] for p in darks))
    chk("cover", "F CA emblem LEFT of «CHAITÁNYA / ACADEMY»", rx[1] < dx[0], f"emblem x {rx}, text x {dx}")
    centre = (rx[0] + dx[1]) / 2
    chk("cover", "F CA block centred at the bottom", abs(centre - W / 2) < 12, f"centre {centre} vs {W/2}")
    chk("cover", "F CA block larger than before (emblem >= 80 px tall at 874 px)", max(p[1] for p in reds) - min(p[1] for p in reds) >= 80, "")
    ys = sorted({p[1] for p in darks})
    gaps = [b for a, b in zip(ys, ys[1:]) if b - a > 4]
    chk("cover", "F text in two lines", len(gaps) == 1, str(gaps))


def data_wbw():
    root = qa.DATA
    for f in ("book.ru-iast.json", "book.ru.json"):
        b = json.load(open(os.path.join(root, f), encoding="utf-8"))
        vs = []
        def walk(o):
            if isinstance(o, dict):
                if o.get("type") == "verse": vs.append(o)
                for v in o.values(): walk(v)
            elif isinstance(o, list):
                for v in o: walk(v)
        walk(b)
        chk("data", f"I {f}: {sum(1 for v in vs if v.get('wbw'))}/{len(vs)} verses with wbw", len(vs) == VERSES and all(v.get("wbw") for v in vs))
        s = json.dumps(b, ensure_ascii=False)
        chk("data", f"I {f}: no Bengali letters, no «Камадева » (gen.)", not any("\u0980" <= ch <= "\u09ff" for ch in s) and "Камадева " not in s and "Камадева (" not in s)


with sync_playwright() as p:
    if _os.environ.get("QA_DATA_CHECKS", "1") == "1":
        data_wbw(); cover_pixels()
    for dev, eng, o in DEVICES:
        if ONLY and dev not in ONLY.split(","):
            continue
        print(dev, flush=True)
        try:
            run(p, dev, eng, o)
        except Exception as e:
            chk(dev, "EXCEPTION", False, str(e)[:900])
fails = [r for r in res if not r[2]]
print(f"\n{len(res) - len(fails)}/{len(res)} passed")
for f in fails:
    print("FAILED:", f[0], f[1], f[3][:300])
