"""Reader UI v3: tap anywhere on the cover shows the menu; step-by-step Back.
usage: python v3_test.py <base-url> [shots-dir]   (ONLY=pixel,iphone ...)"""
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
P = f"{BASE}/{LANG}/daily-duties-brahma-muhurta/"
COVER = f"{BASE}/{LANG}/"
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
    br = getattr(p, eng).launch(); ctx = br.new_context(service_workers="block", **o); pg = ctx.new_page()
    errs = []
    if eng == "chromium":
        # Chrome (Android) skips entries pushed without a user gesture on Back:
        # record the activation state of every pushState.
        pg.add_init_script("""(() => { const o = history.pushState.bind(history); window.__noAct = [];
          history.pushState = function (s, t, u) { if (!(navigator.userActivation && navigator.userActivation.isActive)) window.__noAct.push(String(u)); return o(s, t, u); }; })()""")
    pg.on("pageerror", lambda e: errs.append(str(e)))
    touch = o.get("has_touch", False)

    def tap_pt(x, y):
        (pg.touchscreen.tap if touch else pg.mouse.click)(x, y); pg.wait_for_timeout(450)

    def act(loc):
        loc.tap() if touch else loc.click(); pg.wait_for_timeout(500)

    shown = lambda: pg.locator(".reader-chrome[data-shown]").count() == 1
    menu = lambda: pg.locator(".mobile-menu").count() == 1
    top = lambda: pg.evaluate("document.querySelector('.app-main').scrollTop")

    def show_bars():
        if not shown():
            pt = pg.evaluate(EMPTY); tap_pt(pt["x"], pt["y"])

    def shot(n):
        if SHOTS and dev in ("pixel7", "iphone14"):
            pg.screenshot(path=os.path.join(SHOTS, f"v3-{dev}-{n}.png"))

    pg.goto(P, wait_until="networkidle"); pg.wait_for_timeout(800)
    pg.evaluate("try{localStorage.setItem('ap.readerHintSeen','1'); sessionStorage.removeItem('toc-parts-open')}catch(e){}")

    # (a) cover: tap at the picture centre -> menu bars; again -> hidden
    pg.goto(COVER, wait_until="networkidle"); pg.wait_for_timeout(1000)
    b = pg.locator("img.home-cover").bounding_box()
    tap_pt(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    chk(dev, "(a) cover: tap image centre -> bars", shown())
    shot("a-cover-menu")
    tap_pt(b["x"] + b["width"] / 2, b["y"] + b["height"] * 0.3)
    chk(dev, "(a) cover: tap image again -> bars hidden", not shown())
    tap_pt(b["x"] + 10, b["y"] + b["height"] - 10)
    chk(dev, "(a) cover: tap image corner -> bars", shown())
    chk(dev, "(a) cover: bottom bar has «Назад» / «Вперёд»", pg.locator("[data-reader-nav=back]").count() == 1 and pg.locator("[data-reader-nav=forward]").count() == 1)

    # (e) bars span the full width: buttons at the screen edges, >= 44x44
    pg.goto(P, wait_until="networkidle"); pg.wait_for_timeout(900)
    show_bars()
    g = pg.evaluate("""() => { const r = s => { const e = document.querySelector(s); const b = e.getBoundingClientRect(); return {l: b.left, r: b.right, w: b.width, h: b.height}; };
      return {vw: innerWidth, c: r('[data-reader-action=contents]'), s: r('[data-reader-action=search]'), aa: r('[data-reader-action=aa]'),
              p: r('[data-reader-nav=back]'), n: r('[data-reader-nav=forward]')}; }""")
    vw = g["vw"]
    chk(dev, "(e) «Содержание» at left edge (<=24px)", g["c"]["l"] <= 24, str(g["c"]))
    chk(dev, "(e) «Аа» at right edge (>= vw-24)", g["aa"]["r"] >= vw - 24, f"{g['aa']} vw={vw}")
    chk(dev, "(e) «Назад» left / «Вперёд» right edge", g["p"]["l"] <= 24 and g["n"]["r"] >= vw - 24, f"{g['p']} {g['n']}")
    chk(dev, "(e) hit targets >= 44x44", all(g[k]["w"] >= 44 and g[k]["h"] >= 44 for k in "c s aa p n".split()), str(g))
    shot("e-bars-edges")
    if SHOTS and dev == "ipad-landscape":
        pg.screenshot(path=os.path.join(SHOTS, "v3-ipad-landscape-e-bars-edges.png"))
    show_bars(); act(pg.locator("[data-reader-action=aa]"))
    pb = pg.evaluate("(() => { const b = document.querySelector('.reader-panel').getBoundingClientRect(); const t = document.querySelector('.reader-bar-top').getBoundingClientRect(); return [b.top, t.bottom]; })()")
    chk(dev, "(e) Аа panel below the top bar", pb[0] >= pb[1], str(pb))
    pg.go_back(); pg.wait_for_timeout(600)

    # (b) step-by-step back
    pg.goto(P, wait_until="networkidle"); pg.wait_for_timeout(1000)
    pg.evaluate("document.querySelector('.app-main').scrollTop = 1500"); pg.wait_for_timeout(1000)
    y0 = top()
    show_bars(); act(pg.locator("[data-reader-action=contents]"))
    chk(dev, "(b) 1 contents opens", menu())
    part_btn = pg.locator(".mobile-menu nav button[aria-expanded=false]", has_text="Праздники").first
    part_name = part_btn.inner_text().strip()
    act(part_btn); act(part_btn)   # [v7.5 law, Satkirti 07.10: 1st tap highlights, 2nd expands]
    exp = lambda: pg.locator(".mobile-menu nav button[aria-expanded=true]", has_text=part_name).count() == 1
    chk(dev, "(b) 2 part expanded", exp(), part_name)
    shot("b2-part-expanded")
    # v7.5 (Satkirti 07.10): a chapter with subsections — 1st tap highlights, 2nd expands
    # (each a Back step); the chapter is opened through its subsections.
    chbtn = pg.locator(".mobile-menu nav button[aria-expanded=true]", has_text=part_name).locator("xpath=ancestor::li[1]//ul//button[@data-toc-chapter]").first
    chid = chbtn.get_attribute("data-toc-chapter")
    act(chbtn)
    chexp = lambda: pg.locator(f".mobile-menu nav button[data-toc-chapter='{chid}'][aria-expanded=true]").count() == 1
    chk(dev, "(b) 2a v7.5: first tap on the chapter only highlights", not chexp() and pg.url == P, chid)
    act(chbtn)
    chk(dev, "(b) 2b chapter expanded on the second tap", chexp() and pg.url == P, chid)
    first_sub = pg.locator(f".mobile-menu #toc-ch-{chid} a").first
    act(first_sub); act(first_sub); pg.wait_for_timeout(1200)
    C = pg.url.split("#")[0]
    chk(dev, "(b) 3 chapter opened (first subsection), menu closed", f"/{chid}/" in C and not menu(), pg.url)
    show_bars(); act(pg.locator("[data-reader-action=contents]"))
    subs = pg.locator(".mobile-menu nav a[data-toc-row^=\"sub:\"]")
    nsub = subs.count()
    if nsub >= 2:
        act(subs.nth(1)); act(subs.nth(1)); pg.wait_for_timeout(900)
        S = pg.url
        chk(dev, "(b) 4 sub-section opened", "#" in S and not menu() and top() > 100, f"{S} top={top()}")
        shot("b4-subsection")
        # v7.5: every tap in the contents is a Back step (Satkirti 07.10: «назад — теми же шагами»)
        steps = [
            ("back1 -> chapter with contents open (sub 2 lit)", lambda: pg.url.split("#")[0] == C and menu()),
            ("back1b -> chapter, contents as opened", lambda: pg.url.split("#")[0] == C and menu()),
            ("back2 -> chapter (first subsection), contents closed", lambda: pg.url.split("#")[0] == C and not menu()),
            ("back3 -> previous page, contents open, part + chapter expanded (sub 1 lit)", lambda: pg.url == P and menu() and exp() and chexp()),
            ("back3b -> part + chapter expanded (chapter lit)", lambda: pg.url == P and menu() and exp() and chexp()),
            ("back4 -> chapter collapsed, part expanded", lambda: pg.url == P and menu() and exp() and not chexp()),
            ("back4b -> part expanded (part lit)", lambda: pg.url == P and menu() and exp() and not chexp()),
            ("back5 -> part collapsed (part lit), contents still open", lambda: pg.url == P and menu() and not exp()),
            ("back5b -> contents as opened", lambda: pg.url == P and menu() and not exp()),
            ("back6 -> previous page, contents closed, scroll restored", lambda: pg.url == P and not menu() and abs(top() - y0) < 40),
        ]
    else:
        chk(dev, "(b) chapter has >=2 subsections", False, f"n={nsub} {C}")
        steps = []
    for i, (name, f) in enumerate(steps):
        pg.go_back(); pg.wait_for_timeout(1300)
        ok = f()
        chk(dev, f"(b) {name}", ok and pg.url != COVER, f"url={pg.url} menu={menu()} top={top()} y0={y0}")
        if i in (0, 3, 9):
            shot(f"b-back{i+1}")
    chk(dev, "(b) never on cover", pg.url != COVER)
    if eng == "chromium":
        na = pg.evaluate("window.__noAct")
        chk(dev, "(b) every pushState had a user gesture (no skippable entries)", na == [], str(na))

    # (b2) closing the contents (✕) after expanding pops all its steps
    show_bars(); act(pg.locator("[data-reader-action=contents]"))
    act(pg.locator(".mobile-menu nav button[aria-expanded=false]").first)
    act(pg.locator(".mobile-menu button[aria-label]").first)  # ✕ close
    pg.wait_for_timeout(600)
    st = pg.evaluate("history.state && history.state.apMenu === true")
    chk(dev, "(b) ✕ after expanding -> menu closed, no menu entry left", not menu() and not st and pg.url == P, pg.url)

    # (c) Аа -> back closes; Аа -> next chapter -> back -> Аа open -> back -> closed
    show_bars(); act(pg.locator("[data-reader-action=aa]"))
    chk(dev, "(c) Аа opens", pg.locator(".reader-panel").count() == 1)
    pg.go_back(); pg.wait_for_timeout(800)
    chk(dev, "(c) back closes Аа, page stays", pg.locator(".reader-panel").count() == 0 and pg.url == P, pg.url)
    show_bars(); act(pg.locator("[data-reader-action=aa]"))
    chk(dev, "(c) Аа opens again", pg.locator(".reader-panel").count() == 1)
    shot("c-back-aa-open")
    act(pg.locator("[data-reader-nav=back]")); pg.wait_for_timeout(900)
    chk(dev, "(c) «‹ Назад» button closes Аа (a history step)", pg.url == P and pg.locator(".reader-panel").count() == 0, pg.url)

    # (d) search -> result -> back -> search with query -> back -> closed
    show_bars(); act(pg.locator("[data-reader-action=search]"))
    inp = pg.locator(".mobile-menu input[type=search]")
    inp.fill("тилака")
    try:
        pg.locator(".mobile-menu nav a:visible mark").first.wait_for(timeout=15000)
    except Exception:
        pass
    inp.press("Enter"); pg.wait_for_timeout(300)
    act(pg.locator(".mobile-menu nav a:visible").nth(1)); pg.wait_for_timeout(1300)
    R = pg.url
    pg.go_back(); pg.wait_for_timeout(1300)
    q = inp.input_value() if inp.count() else None
    chk(dev, "(d) result -> back -> search with query", menu() and q == "тилака", f"{R} q={q}")
    shot("d-back-search")
    pg.go_back(); pg.wait_for_timeout(800)
    chk(dev, "(d) back again -> search closed, same page", not menu() and pg.url == P, pg.url)
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
