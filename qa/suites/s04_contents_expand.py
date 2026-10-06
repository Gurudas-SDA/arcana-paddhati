"""Reader UI v4: chapters with subsections expand in the Contents (Satkirti).
usage: python v4_test.py <base-url> [shots-dir]   (ONLY=pixel,iphone ...)"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402  (device profiles, repo paths)
import os, sys
from playwright.sync_api import sync_playwright
BASE = sys.argv[1].rstrip("/"); SHOTS = sys.argv[2] if len(sys.argv) > 2 else None
ONLY = None  # device filter: QA_DEVICES (qa/lib/qa.py)
IOS_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
IPAD_UA = IOS_UA.replace("iPhone; CPU iPhone OS", "iPad; CPU OS")
PIXEL_UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36")
DEVICES = qa.devices(['pixel7', 'iphone14', 'ipad-portrait', 'ipad-landscape', 'ipad-mini', 'ipad-pro', 'desktop'])
LANG = "ru-iast"
CH5 = "daily-duties-brahma-muhurta"          # 5. Ежедневные обязанности
P = f"{BASE}/{LANG}/daily-deity-schedule/"   # 6. (same part) - the reader's page
COVER = f"{BASE}/{LANG}/"
# v7.1: Мангалачарана has no subsections any more (no headings — Satkirti 06.10)
FRONT = ["gaudiya-emblem", "vigraha-tattva"]
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
    errs = []
    state = {}

    def new_page():
        ctx = br.new_context(service_workers="block", **o); pg = ctx.new_page()
        if eng == "chromium":
            pg.add_init_script("""(() => { const o = history.pushState.bind(history); window.__noAct = [];
              history.pushState = function (s, t, u) { if (!(navigator.userActivation && navigator.userActivation.isActive)) window.__noAct.push(String(u)); return o(s, t, u); }; })()""")
        pg.on("pageerror", lambda e: errs.append(str(e)))
        state["pg"] = pg
        return pg

    pg = new_page()
    cur = lambda: state["pg"]

    def act(loc):
        loc.scroll_into_view_if_needed()
        loc.tap() if touch else loc.click(); cur().wait_for_timeout(550)

    def tap_pt(x, y):
        (cur().touchscreen.tap if touch else cur().mouse.click)(x, y); cur().wait_for_timeout(450)

    shown = lambda: cur().locator(".reader-chrome[data-shown]").count() == 1
    menu = lambda: cur().locator(".mobile-menu").count() == 1
    top = lambda: cur().evaluate("document.querySelector('.app-main').scrollTop")
    chap = lambda sid: cur().locator(f".mobile-menu nav button[data-toc-chapter='{sid}']")
    expanded = lambda sid: chap(sid).count() == 1 and chap(sid).get_attribute("aria-expanded") == "true"
    sublinks = lambda sid: cur().locator(f".mobile-menu #toc-ch-{sid} a")

    def show_bars():
        if not shown():
            pt = cur().evaluate(EMPTY); tap_pt(pt["x"], pt["y"])

    def open_contents():
        show_bars(); act(cur().locator("[data-reader-action=contents]"))

    def shot(n):
        if SHOTS and dev in ("pixel7", "iphone14", "ipad-portrait"):
            cur().screenshot(path=os.path.join(SHOTS, f"v4-{dev}-{n}.png"))

    # (a) chapter 5 expands, 5.3 opens, step-by-step Back
    pg.goto(P, wait_until="networkidle"); pg.wait_for_timeout(800)
    pg.evaluate("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    pg.evaluate("document.querySelector('.app-main').scrollTop = 900"); pg.wait_for_timeout(900)
    y0 = top()
    open_contents()
    chk(dev, "(a) contents open", menu())
    chk(dev, "(a) current chapter 6 auto-expanded", expanded("daily-deity-schedule"))
    chk(dev, "(a) chapter 5 collapsed, is a disclosure button", chap(CH5).count() == 1 and not expanded(CH5))
    act(chap(CH5))
    n = sublinks(CH5).count()
    first = sublinks(CH5).first.inner_text().strip() if n else ""
    chk(dev, "(a) tap chapter 1 -> subsections 1.x visible", expanded(CH5) and n >= 4 and "1.1" in sublinks(CH5).nth(0).inner_text(), f"n={n}")  # [v7 law C/D, Satkirti 06.10: no «Начало главы»; Introduction group; Part I numbered from 1]
    chk(dev, "(a) v7: list starts with the first subsection «1.1» (no «Начало главы»)", first.startswith("1.1"), first)
    chk(dev, "(a) page did not change, contents still open", pg.url == P and menu(), pg.url)
    h = pg.evaluate(f"""() => [document.querySelector("button[data-toc-chapter='{CH5}']").getBoundingClientRect().height,
        ...[...document.querySelectorAll('#toc-ch-{CH5} a')].map(a => a.getBoundingClientRect().height)]""")
    chk(dev, "(a) chapter + subsection rows >= 44px", min(h) >= 43.5, str(h))
    shot("a1-chapter5-expanded")
    sub3 = sublinks(CH5).nth(2)  # [v7 law C/D, Satkirti 06.10: no «Начало главы»; Introduction group; Part I numbered from 1]
    label3 = sub3.inner_text().strip()
    href = sub3.get_attribute("href"); anchor = href.split("#", 1)[1]
    act(sub3)
    chk(dev, "(a) v5: first tap on 5.3 only highlights it", menu() and pg.url == P and sub3.get_attribute("data-toc-lit") is not None, pg.url)
    act(sub3); pg.wait_for_timeout(900)
    S = pg.url
    chk(dev, "(a) tap 5.3 -> URL at 5.3, drawer closed", label3.startswith("1.3") and f"/{CH5}/" in S and S.endswith("#" + anchor) and not menu(), f"{label3} {S}")
    vis = pg.evaluate("(id) => { const e = document.getElementById(id); return e ? e.getBoundingClientRect().top : null; }", anchor)
    chk(dev, "(a) 5.3 heading at top of the screen", vis is not None and -5 <= vis < 250, str(vis))
    shot("a2-at-5.3")
    steps = [
        ("back1 -> Contents open, chapter 5 expanded, original page", lambda: pg.url == P and menu() and expanded(CH5)),
        ("back2 -> chapter 5 collapsed, Contents open", lambda: pg.url == P and menu() and not expanded(CH5)),
        ("back3 -> Contents closed, original page + scroll", lambda: pg.url == P and not menu() and abs(top() - y0) < 40),
    ]
    for i, (name, f) in enumerate(steps):
        pg.go_back(); pg.wait_for_timeout(1300)
        chk(dev, f"(a) {name}", f() and pg.url != COVER, f"url={pg.url} menu={menu()} top={top()} y0={y0}")
        shot(f"a-back{i+1}")
    if eng == "chromium":
        na = pg.evaluate("window.__noAct")
        chk(dev, "(a) every pushState had a user gesture", na == [], str(na))

    # (b) reading a subsection: Contents opens with its chapter expanded + subsection highlighted
    pg.goto(f"{BASE}/{LANG}/{CH5}/#{anchor}", wait_until="networkidle"); pg.wait_for_timeout(1300)
    open_contents()
    cl = pg.locator(f".mobile-menu #toc-ch-{CH5} a[aria-current=location]")
    chk(dev, "(b) reading 5.3: chapter 5 auto-expanded, 5.3 highlighted",
        expanded(CH5) and cl.count() == 1 and cl.get_attribute("href") == href, f"{cl.count()}")
    shot("b-current-highlighted")
    act(chap(CH5)); act(chap(CH5)); pg.wait_for_timeout(900)  # [v7 law C/D, Satkirti 06.10: no «Начало главы»; Introduction group; Part I numbered from 1]
    chk(dev, "(b) v7: chapter row, second tap -> chapter top, drawer closed", not menu() and top() < 120 and f"/{CH5}/" in pg.url, f"{pg.url} {top()}")

    # (d) Satkirti (Android): scroll the Contents down to a low item, tap it,
    # Back -> the drawer reopens at the same scroll offset, item still visible.
    pg.goto(P, wait_until="networkidle"); pg.wait_for_timeout(1000)
    open_contents()
    LONG = "arcana-procedure"          # 8. Порядок арчаны (17 subsections)
    act(chap(LONG))
    nav_top = lambda: pg.evaluate("document.querySelector('.mobile-menu nav').scrollTop")
    low = sublinks(LONG).last
    low_href = low.get_attribute("href")
    # the reader's own scroll: the low item near the bottom of the list's view
    pg.evaluate("""(h) => { const nav = document.querySelector('.mobile-menu nav');
        const a = [...nav.querySelectorAll('a')].find(x => x.getAttribute('href') === h);
        nav.scrollTop += a.getBoundingClientRect().bottom - nav.getBoundingClientRect().bottom + 30; }""", low_href)
    pg.wait_for_timeout(400)
    t0 = nav_top()
    pos = lambda: pg.evaluate("""(h) => { const a = [...document.querySelectorAll('.mobile-menu nav a')].find(x => x.getAttribute('href') === h);
        return a ? a.getBoundingClientRect().top : null; }""", low_href)
    p0 = pos()
    chk(dev, "(d) drawer scrolled down to a low item", t0 > 200, f"scrollTop={t0}")
    shot("d1-drawer-scrolled")
    act(low); act(low); pg.wait_for_timeout(1000)
    chk(dev, "(d) low item opened, drawer closed", not menu() and low_href.split("#")[1] in pg.url, pg.url)
    pg.go_back(); pg.wait_for_timeout(1300)
    t1 = nav_top() if menu() else None
    p1 = pos() if menu() else None
    chk(dev, "(d) Back -> drawer at the same scrollTop (±10px), item in place",
        menu() and pg.url == P and t1 is not None and abs(t1 - t0) <= 10 and p1 is not None and abs(p1 - p0) <= 10,
        f"t0={t0} t1={t1} p0={p0} p1={p1} url={pg.url}")
    shot("d2-back-same-scroll")
    pg.go_back(); pg.wait_for_timeout(1000)
    chk(dev, "(d) Back -> chapter collapsed, Contents open", menu() and not expanded(LONG) and pg.url == P, pg.url)
    pg.go_back(); pg.wait_for_timeout(1000)
    chk(dev, "(d) Back -> Contents closed, same page", not menu() and pg.url == P, pg.url)
    pg.context.close()

    # (c) Satkirti: fresh session, FIRST tap on a front chapter expands it (no navigation)
    for sid in FRONT:
        pg = new_page()
        pg.goto(COVER, wait_until="networkidle"); pg.wait_for_timeout(1000)
        pg.evaluate("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
        b = pg.locator("img.home-cover").bounding_box()
        tap_pt(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
        act(pg.locator("[data-reader-action=contents]"))
        before = pg.url
        act(pg.locator(".mobile-menu [data-toc-group=introduction]"))  # [v7 law C/D, Satkirti 06.10: no «Начало главы»; Introduction group; Part I numbered from 1]
        chk(dev, f"(c) {sid}: fresh session, collapsed at start", chap(sid).count() == 1 and not expanded(sid))
        act(chap(sid))
        chk(dev, f"(c) {sid}: FIRST tap expands, no navigation", expanded(sid) and sublinks(sid).count() >= 2 and pg.url == before and menu(), pg.url)
        if sid == "vigraha-tattva":
            shot("c-vigraha-first-tap")
        pg.context.close()
    chk(dev, "no page errors", not errs, "; ".join(errs[:3]))
    br.close()


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
