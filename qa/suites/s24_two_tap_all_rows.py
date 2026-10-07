"""Reader v7.6.1 (Codex review of v7.5) — the two-tap rule (UI §10, Satkirti 06.10 / 07.10.2026) for
EVERY leaf row of «Содержание»: every chapter without subsections, every subsection, every empty part.
  1st tap: only highlights it (exactly one row lit = this one), the URL does not change, the contents stay;
  2nd tap: opens it (the URL becomes the row's link; a subsection of the page shown: its anchor);
  «Назад» from there: the contents again, this row lit, at the same URL as before.
Desktop (Windows Chromium): all rows. Phone / iPad: a representative sample (≥30 rows, every chapter's
first and last subsection, every leaf chapter), all rows with QA_ALL_ROWS=1.
usage: python s24_two_tap_all_rows.py <base-url>   devices: QA_DEVICES"""
import os
import sys
from urllib.parse import unquote, urlsplit

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
L = "ru-iast"
DEVICES = qa.devices(["desktop", "pixel7", "iphone14", "ipad-portrait", "ipad-landscape", "mac-safari"])
FULL_ON = {"desktop"}
res = []

LIT = "() => [...document.querySelectorAll('.mobile-menu nav [data-toc-lit]')].map(e => e.getAttribute('data-toc-row'))"


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else info}", flush=True)


def here(url):
    u = urlsplit(url)
    return unquote(u.path) + (("#" + unquote(u.fragment)) if u.fragment else "")


def sample(rows):
    """≥30 rows: every leaf chapter / empty part, first + last subsection of every chapter (+ every 3rd row up to 30)."""
    keep = set()
    by_ch = {}
    for r in rows:
        if r.startswith("sub:"):
            by_ch.setdefault(r.split("#")[0], []).append(r)
        else:
            keep.add(r)
    for subs in by_ch.values():
        keep.update([subs[0], subs[-1]])
    for r in rows[::3]:
        if len(keep) >= 30:
            break
        keep.add(r)
    return [r for r in rows if r in keep]


def run(p, dev, eng, o):
    b = getattr(p, eng).launch()
    c = b.new_context(locale="ru-RU", service_workers="block", **o)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    pg = c.new_page()
    touch = o.get("has_touch", False)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    menu = lambda: pg.locator(".mobile-menu").count() == 1
    lit = lambda: pg.evaluate(LIT)

    def tap(loc, ms=250):
        loc.scroll_into_view_if_needed()
        loc.tap() if touch else loc.click()
        pg.wait_for_timeout(ms)

    def open_contents():
        btn = pg.locator("[data-reader-action=contents]")
        for _ in range(4):
            if menu():
                return
            if pg.locator(".reader-chrome[data-shown]").count() == 0:
                vw = pg.viewport_size
                (pg.touchscreen.tap if touch else pg.mouse.click)(vw["width"] - 6, vw["height"] / 2)
                pg.wait_for_timeout(450)
            try:
                btn.tap(timeout=3000) if touch else btn.click(timeout=3000)
            except Exception:
                pass
            pg.wait_for_timeout(800)

    def recover():
        pg.goto(f"{BASE}/{L}/introduction/", wait_until="networkidle")
        pg.wait_for_timeout(700)
        open_contents()

    pg.goto(f"{BASE}/{L}/introduction/", wait_until="networkidle")
    pg.wait_for_timeout(700)
    open_contents()
    # base view, then every group and every chapter list opened (two taps each)
    tap(pg.locator(".mobile-menu [data-toc-cover]"))
    for tag, attr in (("", "data-toc-group"), ("button", "data-toc-chapter")):
        for gid in pg.evaluate(f"() => [...document.querySelectorAll('.mobile-menu {tag}[{attr}]')].map(e => e.getAttribute('{attr}'))"):
            loc = pg.locator(f".mobile-menu {tag}[{attr}='{gid}']")
            for _ in range(3):
                if loc.get_attribute("aria-expanded") == "true":
                    break
                tap(loc)
    rows = pg.evaluate("""() => [...document.querySelectorAll('.mobile-menu nav a[data-toc-row]')]
        .map(e => e.getAttribute('data-toc-row')).filter(r => r !== 'cover')""")
    n_sub = sum(1 for r in rows if r.startswith("sub:"))
    chk(dev, f"setup: all lists open ({len(rows)} leaf rows, {n_sub} subsections)", len(rows) >= 100 and n_sub >= 100, str(len(rows)))
    todo = rows if (dev in FULL_ON or os.environ.get("QA_ALL_ROWS") == "1") else sample(rows)
    bad1, bad2, bad3 = [], [], []
    for r in todo:
        loc = pg.locator(f".mobile-menu nav a[data-toc-row='{r}']")
        if loc.count() != 1:
            bad1.append((r, "row not shown"))
            continue
        href = unquote(loc.get_attribute("href") or "")
        u0 = here(pg.url)
        tap(loc)
        got = lit()
        if not (menu() and got == [r] and here(pg.url) == u0):
            bad1.append((r, got, here(pg.url)))
            if not menu():
                recover()
            continue
        # 2nd tap: opens it
        tap(loc, 0)
        try:
            # the menu gone AND the URL settled on the row's link (the live site commits the URL a moment
            # after the menu closes; the page shown at its top: the URL stays)
            pg.wait_for_function("""(want) => !document.querySelector('.mobile-menu') &&
                decodeURI(location.pathname) + decodeURIComponent(location.hash) === want""",
                                 arg=u0 if href.rstrip("/") == u0.rstrip("/") else href, timeout=12000)
        except Exception:
            pass
        pg.wait_for_timeout(150)
        u1 = here(pg.url)
        same_top = href.rstrip("/") == u0.rstrip("/")   # the page shown, at its top: the menu just closes
        if menu() or not (u1 == href or (same_top and u1 == u0)):
            bad2.append((r, href, u1, "menu" if menu() else ""))
            recover()
            continue
        if same_top and u1 == u0:
            open_contents()       # nothing to go back from: reopen
            continue
        # «Назад»: the contents again, this row lit, the URL before
        pg.go_back()
        try:
            pg.wait_for_function("() => !!document.querySelector('.mobile-menu nav [data-toc-lit]')", timeout=8000)
        except Exception:
            pass
        pg.wait_for_timeout(450)   # the list's offset of this step is put back (Sidebar: 60/160/320 ms)
        if not (menu() and lit() == [r] and here(pg.url) == u0):
            bad3.append((r, menu(), lit(), here(pg.url)))
            recover()
    what = f"{len(todo)} of {len(rows)} leaf rows" + (" — all" if len(todo) == len(rows) else " (sample)")
    chk(dev, f"1st tap on a leaf row only highlights, URL unchanged ({what})", len(todo) >= 30 and not bad1, str(bad1[:3]))
    chk(dev, f"2nd tap on the highlighted leaf row opens it ({what})", not bad2, str(bad2[:3]))
    chk(dev, f"Назад from the opened row: contents, the row lit, URL before ({what})", not bad3, str(bad3[:3]))
    chk(dev, "no page errors", not errs, str(errs[:3]))
    b.close()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        print(f"== {dev}", flush=True)
        try:
            run(p, dev, eng, o)
        except Exception as e:  # a crash is a failure, with its message
            chk(dev, "suite crashed", False, repr(e)[:300])
print(f"s24: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
