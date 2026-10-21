"""One-tap navigation for EVERY leaf row of Contents (Satkirti 13.10.2026).
Every chapter without subsections, subsection and empty part opens immediately.
Back restores the previous URL and open lists, marking the reading place;
the same row opens again on one tap, regardless of the current mark.
Desktop: all rows. Phone / iPad: at least 30 rows, every chapter's first and
last subsection and every leaf chapter; QA_ALL_ROWS=1 tests every row.
usage: python3 s24_two_tap_all_rows.py <base-url>   devices: QA_DEVICES"""
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

LIT = "() => [...document.querySelectorAll('.mobile-menu[data-open] nav [data-toc-lit]')].map(e => e.getAttribute('data-toc-row'))"


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} [toc={qa.TOC_MODE_NAME}] {'' if ok else info}", flush=True)


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


def run(p, dev, eng, o, mode):
    from toc import Contents, history_roundtrip, marks_place
    b = getattr(p, eng).launch()
    c = b.new_context(locale="ru-RU", service_workers="block", **o)
    c.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
    pg = c.new_page(); flow = Contents(pg, mode, o.get("has_touch", False))
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    try:
        mode.start(pg, f"{BASE}/{L}/")
        flow.contents()
        for attr in ("data-toc-toggle", "data-toc-chapter"):  # V37: a group expands by its arrow
            ids = pg.locator(f".mobile-menu[data-open] [{attr}]").evaluate_all("es=>es.map(e=>e.getAttribute('"+attr+"'))")
            for id in ids:
                loc = pg.locator(f".mobile-menu[data-open] [{attr}='{id}']")
                if loc.get_attribute("aria-expanded") != "true": flow.activate(loc)
        rows = pg.locator(".mobile-menu[data-open] nav a[data-toc-row]").evaluate_all("es=>es.map(e=>e.dataset.tocRow).filter(r=>r!=='cover')")
        n_sub = sum(r.startswith("sub:") for r in rows)
        chk(dev, f"setup: all lists open ({len(rows)} leaf rows, {n_sub} subsections)", len(rows)>=100 and n_sub>=100)
        todo = rows if dev in FULL_ON or os.environ.get("QA_ALL_ROWS")=="1" else sample(rows)
        bad1, bad2, bad3 = [], [], []
        for r in todo:
            loc = flow.row(r); href = here(loc.get_attribute("href")); before = flow.state()
            flow.tap(loc, wait=100)
            first = flow.state()
            if mode.one:
                if first['menu'] or here(pg.url)!=href: bad1.append((r,first))
            else:
                if not (first['menu'] and first['lit']==[r] and first['url']==before['url']): bad1.append((r,first))
                flow.tap(loc,wait=100)
            pg.wait_for_function("!document.querySelector('.mobile-menu[data-open]')",timeout=12000)
            opened = flow.state()
            if here(pg.url)!=href: bad2.append((r,href,opened))
            # Back restores the place before the jump, not the tapped row.
            flow.nav('back',native=True);back = flow.state()
            if not (back['menu'] and marks_place(back) and back['url']==before['url'] and back['open']==before['open']): bad3.append((r,back,before))
            if mode.one:
                # Every row opens again on one tap, regardless of the mark.
                flow.tap(flow.row(r),wait=100)
                if flow.state()['menu'] or here(pg.url)!=href: bad2.append((r,'row did not reopen on one tap'))
                flow.nav('back',native=True)
        what = f"{len(todo)} of {len(rows)} leaf rows"
        chk(dev, f"1st tap on a leaf row: {'opens immediately' if mode.one else 'only highlights, URL unchanged'} ({what})",len(todo)>=30 and not bad1,str(bad1[:3]))
        chk(dev, f"Leaf row opens and reopens on one tap after Back ({what})",not bad2,str(bad2[:3]))
        chk(dev, f"Назад from the opened row: contents, reading place marked, URL and open lists before ({what})",not bad3,str(bad3[:3]))
        chk(dev,"no page errors",not errs,str(errs[:3]))
    except Exception as error:
        # A broken setup cannot silently omit the leaf-row checks. Report
        # each blocked acceptance check, then run history in a fresh context.
        for name in ['setup: all lists open','1st tap on a leaf row','Leaf row opens and reopens on one tap after Back','Назад from the opened row: contents, reading place marked, URL and open lists before','no page errors']:
            chk(dev,name,False,'Blocked by the all-lists failure: '+str(error)[:220])
    finally:
        try:history_roundtrip(b,o,mode,lambda n,ok,i='':chk(dev,n,ok,i),BASE)
        finally:c.close();b.close()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        print(f"== {dev}", flush=True)
        try:
            qa.run_toc_modes(lambda mode: run(p, dev, eng, o, mode), on_error=lambda e: chk(dev, "suite crashed", False, repr(e)[:300]))
        except Exception as e:  # a crash is a failure, with its message
            chk(dev, "suite crashed", False, repr(e)[:300])
print(f"s24: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
