"""Reader v7.6.1 (Codex review of v7.5) — «Содержание» and history across reload, deep links and fast taps
(UI §10, Satkirti 07.10.2026: «Назад» = exactly the forward steps with the same highlights and open lists).
  A  Reload keeps what the reader collapsed: /ru-iast/introduction/ → Содержание → «Введение» ×2 (collapsed)
     → reload → still collapsed, «Введение» lit; «Назад» → the step before (open, lit); «Вперёд» → collapsed.
     (v7.5 bug: the current group's «collapsed» was deleted on mount — it re-expanded after reload.)
  B  Reload in the middle of history: 6 steps forward, 3 × «Назад», reload → the same step (URL, highlight,
     open lists); then «Назад» and «Вперёд» ×2 → each step exactly as recorded going forward.
  C  Deep link straight to a subsection: the heading is at the top; Содержание shows that subsection lit (its
     chapter open); another subsection ×2 → opens it; «Назад» → contents with it lit; «Назад» → the step
     before; «Назад» → contents closed, on the deep-linked subsection.
  D  Rapid double taps (no wait between them) never skip the highlight step: a group → expanded and lit,
     «Назад» → lit but not expanded, «Назад» → before; a subsection → opens it, «Назад» → contents with it lit,
     «Назад» → before the first tap.
usage: python s25_contents_reload_history.py <base-url>   devices: QA_DEVICES"""
import os
import sys
from urllib.parse import unquote, urlsplit

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
L = "ru-iast"
DEVICES = qa.devices(["pixel7", "iphone14", "ipad-portrait", "ipad-landscape", "desktop", "mac-safari"])
res = []

STATE = """() => { const nav = document.querySelector('.mobile-menu nav');
  const r = {url: decodeURI(location.pathname) + decodeURIComponent(location.hash), menu: !!nav, lit: [], open: []};
  if (nav) {
    r.lit = [...nav.querySelectorAll('[data-toc-lit]')].map(e => e.getAttribute('data-toc-row'));
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
    touch = o.get("has_touch", False)
    errs = []
    pg = None

    def new_page():
        nonlocal pg
        if pg:
            pg.close()
        pg = c.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))

    def st():
        return pg.evaluate(STATE)

    def menu():
        return pg.locator(".mobile-menu").count() == 1

    def act(loc, ms=550):
        loc.scroll_into_view_if_needed()
        loc.tap() if touch else loc.click()
        pg.wait_for_timeout(ms)

    def double(loc):
        """Two taps as fast as a finger: no wait between them."""
        loc.scroll_into_view_if_needed()
        box = loc.bounding_box()
        x, y = box["x"] + min(box["width"] / 2, 60), box["y"] + box["height"] / 2
        if touch:
            pg.touchscreen.tap(x, y); pg.touchscreen.tap(x, y)
        else:
            pg.mouse.click(x, y); pg.mouse.click(x, y)
        pg.wait_for_timeout(1200)

    def goto(path):
        pg.goto(f"{BASE}/{L}/{path}", wait_until="networkidle")
        pg.wait_for_timeout(700)

    def bars():
        if pg.locator(".reader-chrome[data-shown]").count() == 0:
            vw = pg.viewport_size
            (pg.touchscreen.tap if touch else pg.mouse.click)(vw["width"] - 6, vw["height"] / 2)
            pg.wait_for_timeout(450)

    def contents():
        btn = pg.locator("[data-reader-action=contents]")
        for _ in range(4):
            if menu():
                return
            bars()
            try:
                btn.tap(timeout=3000) if touch else btn.click(timeout=3000)
            except Exception:
                pass
            pg.wait_for_timeout(800)

    def nav(which):
        if not menu():
            bars()
        loc = pg.locator(f"[data-reader-nav={which}]")
        loc.tap(force=True) if touch else loc.click(force=True)
        pg.wait_for_timeout(1100)

    def reload():
        pg.reload(wait_until="load")   # not networkidle: the live site keeps loading the offline copy
        pg.wait_for_timeout(2000)

    def same(a, b):
        return a["menu"] == b["menu"] and a["lit"] == b["lit"] and a["open"] == b["open"] and a["url"] == b["url"]

    grp = lambda g: pg.locator(f".mobile-menu [data-toc-group='{g}']")
    chap = lambda ch: pg.locator(f".mobile-menu button[data-toc-chapter='{ch}']")
    row = lambda r: pg.locator(f".mobile-menu nav [data-toc-row='{r}']")

    # ---------- A: reload keeps a collapsed group collapsed (the reported repro) ----------
    new_page()
    goto("introduction/")
    contents()
    s0 = st()
    act(grp("introduction")); s1 = st()
    act(grp("introduction")); s2 = st()
    chk(dev, "A setup: «Введение» open → 1st tap lit → 2nd tap collapsed",
        "introduction" in s0["open"] and "introduction" in s1["open"] and s1["lit"] == ["grp:introduction"]
        and "introduction" not in s2["open"] and s2["lit"] == ["grp:introduction"], str([s0, s1, s2]))
    reload()
    s = st()
    chk(dev, "A after reload: «Введение» still collapsed, lit, contents open, same URL", same(s, s2), f"got {s} want {s2}")
    nav("back"); s = st()
    chk(dev, "A Назад after reload: the step before (open, lit)", same(s, s1), f"got {s} want {s1}")
    nav("forward"); s = st()
    chk(dev, "A Вперёд: collapsed again", same(s, s2), f"got {s} want {s2}")

    # ---------- B: reload in the middle of history ----------
    new_page()
    goto("introduction/")
    contents()
    fwd = [st()]
    for loc in (lambda: grp("temple-worship"), lambda: grp("temple-worship"),
                lambda: chap("daily-duties-brahma-muhurta"), lambda: chap("daily-duties-brahma-muhurta"),
                lambda: chap("daily-deity-schedule"), lambda: chap("daily-deity-schedule")):
        act(loc()); fwd.append(st())
    chk(dev, "B setup: 6 steps, each a different state", len({str(x) for x in fwd}) == 7, str(fwd[-1]))
    for _ in range(3):
        nav("back")
    s = st()
    ok_mid = same(s, fwd[3])
    reload()
    s = st()
    chk(dev, "B reload after 3 × Назад: the same step (URL, highlight, open lists)", ok_mid and same(s, fwd[3]), f"got {s} want {fwd[3]}")
    nav("back"); s = st()
    bad = [] if same(s, fwd[2]) else [("back", s, fwd[2])]
    for k in (3, 4, 5, 6):
        nav("forward"); s = st()
        if not same(s, fwd[k]):
            bad.append(("fwd", k, s, fwd[k]))
    chk(dev, "B Назад, then Вперёд ×4 after the reload: each step as recorded (to the last one)", not bad, str(bad[:2]))

    # ---------- C: deep link straight to a subsection ----------
    new_page()
    goto("daily-deity-schedule/#morning-bhoga-arati")
    pg.wait_for_timeout(800)
    top = pg.evaluate("""() => { const h = document.getElementById('morning-bhoga-arati'), m = document.querySelector('.app-main');
        return h && m ? h.getBoundingClientRect().top - m.getBoundingClientRect().top : 1e9; }""")
    chk(dev, "C deep link: the subsection heading is at the top", -2 <= top <= 140, f"top={top}")
    deep = st()
    contents()
    s_c0 = st()
    sub_deep = "sub:daily-deity-schedule#morning-bhoga-arati"
    chk(dev, "C contents: that subsection lit, its chapter open",
        s_c0["lit"] == [sub_deep] and "daily-deity-schedule" in s_c0["open"], str(s_c0))
    other = "sub:daily-deity-schedule#" + pg.evaluate(
        "() => [...document.querySelectorAll('.mobile-menu #toc-ch-daily-deity-schedule a')].map(a => a.getAttribute('href').split('#')[1]).filter(h => h !== 'morning-bhoga-arati').pop()")
    act(row(other)); s_c1 = st()
    act(row(other), 1300); s_c2 = st()
    chk(dev, "C another subsection ×2: lit, then opened", s_c1["lit"] == [other] and s_c1["url"] == deep["url"]
        and not s_c2["menu"] and s_c2["url"].endswith("#" + other.split("#")[1]), str([s_c1, s_c2]))
    nav("back"); s = st()
    bad = [] if same(s, s_c1) else [("1", s, s_c1)]
    nav("back"); s = st()
    if not same(s, s_c0):
        bad.append(("2", s, s_c0))
    nav("back"); s = st()
    if not (not s["menu"] and s["url"] == deep["url"]):
        bad.append(("3", s, deep))
    chk(dev, "C Назад ×3: contents (row lit) → the step before → closed on the deep-linked subsection", not bad, str(bad[:2]))

    # ---------- D: rapid double taps never skip the highlight step ----------
    new_page()
    goto("introduction/")
    contents()
    d0 = st()
    double(grp("temple-worship"))
    d1 = st()
    chk(dev, "D double tap on a group: expanded and lit", "temple-worship" in d1["open"] and d1["lit"] == ["grp:temple-worship"]
        and d1["url"] == d0["url"], str(d1))
    nav("back"); s = st()
    chk(dev, "D Назад: the highlight step (lit, not expanded)", s["menu"] and s["lit"] == ["grp:temple-worship"]
        and "temple-worship" not in s["open"] and s["url"] == d0["url"], str(s))
    nav("back"); s = st()
    chk(dev, "D Назад: the step before the first tap", same(s, d0), f"got {s} want {d0}")
    nav("forward"); nav("forward")
    act(chap("daily-deity-schedule")); act(chap("daily-deity-schedule"))
    d2 = st()
    sub = "sub:daily-deity-schedule#morning-bhoga-arati"
    double(row(sub))
    try:   # another page: the menu stays until it is shown (slow network: the live site)
        pg.wait_for_function("() => !document.querySelector('.mobile-menu')", timeout=12000)
    except Exception:
        pass
    pg.wait_for_timeout(500)
    d3 = st()
    chk(dev, "D double tap on a subsection: opens it", not d3["menu"] and d3["url"].endswith("/daily-deity-schedule/#morning-bhoga-arati"), str(d3))
    nav("back"); s = st()
    chk(dev, "D Назад: contents with the subsection lit (its highlight step kept)", s["menu"] and s["lit"] == [sub]
        and s["url"] == d2["url"], str(s))
    nav("back"); s = st()
    chk(dev, "D Назад: the step before the first tap", same(s, d2), f"got {s} want {d2}")
    chk(dev, "no page errors", not errs, str(errs[:3]))
    b.close()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        print(f"== {dev}", flush=True)
        try:
            run(p, dev, eng, o)
        except Exception as e:  # a crash is a failure, with its message
            chk(dev, "suite crashed", False, repr(e)[:300])
print(f"s25: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
