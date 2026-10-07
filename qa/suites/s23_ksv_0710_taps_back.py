"""Reader v7.5 — КСВ Satkirti 07.10.2026 15:39–15:45 (each check reproduces the remark exactly).
  1  Parampara: a tap ON the portrait shows / hides the bars like empty space — every portrait; v7.6.1 (Codex
     review): also near each edge of the picture, on the caption and on the ornament.
  2  «Обложка» = home: 1st tap resets the contents to the base view (every group and chapter list
     closed) with «Обложка» lit, no navigation; 2nd tap opens the cover; contents reopened there
     stays in the base view.
  3  «Назад» retraces exactly the forward steps with the same highlights and open lists
     (Satkirti's path: Храмовый стандарт → 1 (has subsections) → 2 → 2.5 → open → Содержание → Назад…),
     then «Вперёд» replays them — v7.6.1: EVERY forward step, URL + highlight + open lists each time.
  (Leaf rows: s24; reload / deep link / rapid double taps: s25.)
  4  Two taps in «Содержание»: a part / the Introduction / a chapter with subsections — 1st tap only
     highlights (nothing expands, no navigation), 2nd tap expands; for EVERY such row of the book.
Devices: phone (Android + iPhone), tablet (iPad portrait + landscape), computer (Windows + Mac) —
also in the fast pre-push run (run_all.py fast_devices).
usage: python s23_ksv_0710_taps_back.py <base-url> [shots-dir]   devices: QA_DEVICES"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
SHOTS = sys.argv[2] if len(sys.argv) > 2 else None
L = "ru-iast"
DEVICES = qa.devices(["pixel7", "iphone14", "ipad-portrait", "ipad-landscape", "desktop", "mac-safari"])
res = []

STATE = """() => { const nav = document.querySelector('.mobile-menu nav');
  const r = {url: location.pathname + location.hash, menu: !!nav, lit: [], open: []};
  if (nav) {
    r.lit = [...nav.querySelectorAll('[data-toc-lit]')].map(e => e.hasAttribute('data-toc-cover') ? 'cover' : (e.getAttribute('data-toc-group') || e.getAttribute('data-toc-chapter') || e.getAttribute('href') || e.textContent.trim().slice(0, 30)));
    r.open = [...nav.querySelectorAll('[aria-expanded=true][data-toc-chapter],[aria-expanded=true][data-toc-group]')].map(e => e.getAttribute('data-toc-chapter') || e.getAttribute('data-toc-group')).sort();
  }
  return r; }"""


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else info}", flush=True)


def run(p, dev, eng, o):
    b = getattr(p, eng).launch()
    c = b.new_context(locale="ru-RU", service_workers="block", **o)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    pg = c.new_page()
    touch = o.get("has_touch", False)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    def tap_xy(x, y):
        (pg.touchscreen.tap if touch else pg.mouse.click)(x, y)

    def act(loc, ms=550, force=False):
        loc.scroll_into_view_if_needed()
        loc.tap(force=force) if touch else loc.click(force=force)
        pg.wait_for_timeout(ms)

    shown = lambda: pg.locator(".reader-chrome[data-shown]").count() == 1
    menu = lambda: pg.locator(".mobile-menu").count() == 1
    st = lambda: pg.evaluate(STATE)

    def shot(n):
        if SHOTS:
            os.makedirs(SHOTS, exist_ok=True)
            pg.screenshot(path=os.path.join(SHOTS, f"s23-{dev}-{n}.png"))

    def goto(path):
        try:
            pg.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        pg.goto(f"{BASE}/{L}/{path}", wait_until="networkidle"); pg.wait_for_timeout(700)

    def bars():
        if not shown():
            vw = pg.viewport_size
            # the right margin of the page: empty space on every page
            tap_xy(vw["width"] - 6, vw["height"] / 2); pg.wait_for_timeout(450)

    def contents():
        bars(); act(pg.locator("[data-reader-action=contents]"), 800)

    def back():
        if not menu():
            bars()
        act(pg.locator("[data-reader-nav=back]"), 1100, force=True)

    def forward():
        if not menu():
            bars()
        act(pg.locator("[data-reader-nav=forward]"), 1100, force=True)

    # ---------- 1: tap on every parampara portrait toggles the bars ----------
    goto("parampara/")
    pg.wait_for_function("[...document.querySelectorAll('.app-main img.portrait-img')].every(i => i.complete && i.naturalWidth > 0)", timeout=20000)
    n = pg.locator(".app-main figure.portrait-page").count()
    bad = []
    npts = 0
    # Every portrait: its centre; near each edge of the picture (6 px inside), its caption and the
    # ornament under it (v7.6.1, Codex review) — all portraits in the full run, the first / middle / last in
    # the fast one. Each point is first brought to the middle band of the screen (never under a bar).
    # Each tap toggles the bars, the next one toggles them back.
    POINT = """([k, name]) => { const f = document.querySelectorAll('.app-main figure.portrait-page')[k];
        const m = document.querySelector('.app-main'), H = innerHeight;
        const box = () => ({i: f.querySelector('img.portrait-img').getBoundingClientRect(),
                            c: f.querySelector('.portrait-caption').getBoundingClientRect(),
                            o: f.querySelector('.portrait-ornament').getBoundingClientRect()});
        const at = (b) => ({centre: [b.i.left + b.i.width / 2, b.i.top + b.i.height / 2, 0.5],
          left: [b.i.left + 6, b.i.top + b.i.height / 2, 0.5], right: [b.i.right - 6, b.i.top + b.i.height / 2, 0.5],
          top: [b.i.left + b.i.width / 2, b.i.top + 6, 0.3], bottom: [b.i.left + b.i.width / 2, b.i.bottom - 6, 0.7],
          caption: [b.c.left + b.c.width / 2, b.c.top + b.c.height / 2, 0.5],
          ornament: [b.o.left + b.o.width / 2, b.o.top + b.o.height / 2, 0.5]})[name];
        const [, y0, band] = at(box());
        m.scrollTop += y0 - H * band;
        const [x, y] = at(box());
        const e = document.elementFromPoint(x, y);
        return {x, y, on: e ? (e.closest('.portrait-ornament') ? 'ornament' : e.closest('.portrait-caption') ? 'caption'
                               : e.closest('.portrait-img') ? 'img' : e.tagName + '.' + e.className) : null}; }"""
    want_on = {"centre": "img", "left": "img", "right": "img", "top": "img", "bottom": "img", "caption": "caption", "ornament": "ornament"}
    every = set(range(n)) if not qa.fast() else {0, n // 2, n - 1}
    for k in range(n):
        for name in (want_on if k in every else ["centre"]):
            pt = pg.evaluate(POINT, [k, name])
            pg.wait_for_timeout(300)
            pt = pg.evaluate(POINT, [k, name])   # after the scroll has settled
            if pt["on"] != want_on[name]:
                bad.append((k + 1, name, "point is on", pt["on"]))
                continue
            npts += 1
            s0 = shown()
            tap_xy(pt["x"], pt["y"]); pg.wait_for_timeout(400)
            s1 = shown()
            tap_xy(pt["x"], pt["y"]); pg.wait_for_timeout(400)
            s2 = shown()
            if not (s1 != s0 and s2 == s0):
                bad.append((k + 1, name, s0, s1, s2))
    chk(dev, f"1 tap on the portrait toggles the bars (all {n} portraits; centre, 4 edges, caption, ornament on "
             f"{len(every)} — {npts} points)", n >= 8 and not bad and npts == n + 6 * len(every), f"n={n} bad={bad[:4]}")
    shot("1-portrait")

    # ---------- 4: two taps — every group and every chapter with subsections ----------
    goto("introduction/")
    contents()
    # start from the base view (nothing open, nothing tapped yet): «Обложка» once
    act(pg.locator(".mobile-menu [data-toc-cover]"))
    rows = pg.evaluate("""() => [...document.querySelectorAll('.mobile-menu [data-toc-group]')].map(e => 'g:' + e.getAttribute('data-toc-group'))""")
    bad1, bad2 = [], []
    for r in rows:
        gid = r[2:]
        loc = pg.locator(f".mobile-menu [data-toc-group='{gid}']")
        u0 = pg.url
        act(loc)
        s = st()
        if not (s["lit"] == [gid] and gid not in s["open"] and pg.url == u0 and menu()):
            bad1.append((gid, s))
        act(loc)
        s = st()
        if not (gid in s["open"] and s["lit"] == [gid]):
            bad2.append((gid, s))
        # its chapters with subsections
        for cid in pg.evaluate(f"() => [...document.querySelectorAll('.mobile-menu #toc-part-{gid} [data-toc-chapter], .mobile-menu #toc-grp-{gid} [data-toc-chapter]')].map(e => e.getAttribute('data-toc-chapter'))"):
            cl = pg.locator(f".mobile-menu button[data-toc-chapter='{cid}']")
            if cl.get_attribute("aria-expanded") == "true":
                act(cl); act(cl)
            act(cl)
            s = st()
            if not (s["lit"] == [cid] and cid not in s["open"] and pg.url == u0 and menu()):
                bad1.append((cid, s))
            act(cl)
            s = st()
            if not (cid in s["open"] and s["lit"] == [cid] and pg.url == u0):
                bad2.append((cid, s))
            if not menu() or pg.url != u0:   # the tap left the contents (a wrong behaviour): record, come back
                goto("introduction/"); contents()
                break
            act(cl)  # lit already: collapses again (keeps the list short)
    chk(dev, f"4 first tap only highlights — parts, Введение, chapters with subsections ({len(rows)} groups)", not bad1, str(bad1[:3]))
    chk(dev, "4 second tap on the highlighted row expands it", not bad2, str(bad2[:3]))
    shot("4-two-tap")

    # ---------- 2: «Обложка» = home ----------
    goto("daily-deity-schedule/")
    contents()
    for gid in ["introduction", "festivals-vows"]:
        loc = pg.locator(f".mobile-menu [data-toc-group='{gid}']")
        while loc.get_attribute("aria-expanded") != "true":
            act(loc)
    u0 = pg.url
    s = st()
    chk(dev, "2 setup: groups and a chapter list open", len(s["open"]) >= 3, str(s))
    act(pg.locator(".mobile-menu [data-toc-cover]"))
    s = st()
    chk(dev, "2 first tap «Обложка»: base view (all closed), «Обложка» lit, no navigation",
        s["menu"] and s["open"] == [] and s["lit"] == ["cover"] and pg.url == u0, str(s))
    shot("2-cover-first-tap")
    act(pg.locator(".mobile-menu [data-toc-cover]"), 1300)
    chk(dev, "2 second tap «Обложка» opens the cover", not menu() and pg.url.rstrip("/").endswith(f"/{L}"), pg.url)
    contents()
    s = st()
    chk(dev, "2 contents reopened on the cover: base view, «Обложка» lit", s["open"] == [] and s["lit"] == ["cover"], str(s))

    # ---------- 3: «Назад» mirrors the forward steps (Satkirti's path) ----------
    pg.close()
    pg = c.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    goto("introduction/")
    contents()
    fwd = [st()]
    steps = [("group", "temple-worship"), ("group", "temple-worship"),
             ("chapter", "daily-duties-brahma-muhurta"), ("chapter", "daily-duties-brahma-muhurta"),
             ("chapter", "daily-deity-schedule"), ("chapter", "daily-deity-schedule")]
    for kind, i in steps:
        sel = f".mobile-menu [data-toc-group='{i}']" if kind == "group" else f".mobile-menu button[data-toc-chapter='{i}']"
        act(pg.locator(sel)); fwd.append(st())
    s25 = pg.locator(".mobile-menu #toc-ch-daily-deity-schedule a").nth(4)
    act(s25); fwd.append(st())
    chk(dev, "3 forward: 2.5 lit, chapters 1 and 2 open", (fwd[-1]["lit"][0] or "").endswith("#morning-bhoga-arati")
        and "daily-duties-brahma-muhurta" in fwd[-1]["open"] and "daily-deity-schedule" in fwd[-1]["open"], str(fwd[-1]))
    act(s25, 1300)
    page25 = st()
    chk(dev, "3 second tap opens 2.5", not page25["menu"] and page25["url"].endswith("/daily-deity-schedule/#morning-bhoga-arati"), str(page25))
    contents()
    back()
    s = st()
    chk(dev, "3 Назад 1: contents closed, back on 2.5", not s["menu"] and s["url"] == page25["url"], str(s))
    bad = []
    for k, want in enumerate(reversed(fwd)):
        (pg.go_back() if (dev == "pixel7" and k % 2) else back())  # Android: system back too
        pg.wait_for_timeout(900)
        s = st()
        if not (s["menu"] and s["lit"] == want["lit"] and s["open"] == want["open"] and s["url"] == want["url"]):
            bad.append((k + 2, "got", s, "want", want))
        if k == 1:
            shot("3-back-step3")
    chk(dev, f"3 every further Назад = the forward step before it ({len(fwd)} steps, same highlight + open lists)", not bad, str(bad[:2]))
    back()
    s = st()
    chk(dev, "3 last Назад closes the contents (the page where we started)", not s["menu"] and s["url"].endswith("/introduction/"), str(s))
    bad = []
    # «Вперёд» replays EVERY forward step (v7.6.1, Codex review): URL + highlight + open lists each time,
    # up to the page of 2.5 itself
    for k, want in enumerate(fwd + [page25]):
        forward()
        s = st()
        if not (s["menu"] == want["menu"] and s["lit"] == want["lit"] and s["open"] == want["open"] and s["url"] == want["url"]):
            bad.append((k + 1, "got", s, "want", want))
    chk(dev, f"3 «Вперёд» replays the same steps (all {len(fwd) + 1}: URL, highlight, open lists)", not bad, str(bad[:2]))
    chk(dev, "no page errors", not errs, str(errs[:3]))
    b.close()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        print(f"== {dev}", flush=True)
        try:
            run(p, dev, eng, o)
        except Exception as e:  # a crash is a failure, with its message
            chk(dev, "suite crashed", False, repr(e)[:300])
print(f"s23: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
