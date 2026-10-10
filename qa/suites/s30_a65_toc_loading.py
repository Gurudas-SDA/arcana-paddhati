"""A65 (КСВ-dublieris 07.10.2026): «Содержание» — the page opened by the 2nd tap took 0–7 s (sometimes 19 s)
with no sign of loading; a repeated tap could break it; 1 time of 3 the contents closed ~100 ms before the URL
changed, so the OLD page flashed before the new one.
Acceptance (Satkirti's words):
  1) коснулся пункта в содержании — СРАЗУ (≤100 ms) видно, что страница загружается:
     a progress bar at the top ([data-nav-progress]) and the tapped row marked «загружается…» ([data-toc-loading]);
  2) повторное касание во время загрузки ничего не ломает: one navigation only (one history entry, one
     pushState), the loading signs stay, the right page opens, «Назад» returns to the contents;
  3) старая страница не мигает перед новой: at no moment (DOM mutation or animation frame) is the contents
     closed while the old page (URL or heading) is still shown.
The page data (RSC .txt) is slowed in the page (fetch wrapper, 5 s, also the prefetch started when the contents open) so that the loading is long enough to see
on a fast test machine — like Satkirti's phone on a slow network.
usage: python s30_a65_toc_loading.py <base-url>   devices: QA_DEVICES"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
L = "ru-iast"
DEVICES = qa.devices(["pixel7", "iphone14", "ipad-portrait", "desktop", "mac-safari"])
DELAY_MS = 5000
SLOW_MS = 12000   # B: longer than AppShell's 8 s safety net (КСВ: sometimes 19 s)
res = []

# Slows the page data of client-side navigations (RSC payload, *.txt) while window.__a65delay is set.
SLOW_FETCH = """(() => { const f = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const u = typeof input === 'string' ? input : (input && input.url) || String(input);
    const d = window.__a65delay || 0;
    if (d && /\\.txt(\\?|$)/.test(u)) return new Promise(r => setTimeout(r, d)).then(() => f(input, init));
    return f(input, init);
  }; })();"""

# In-page recorder, installed after the 1st tap (the highlight step) and before the 2nd.
RECORDER = """() => {
  const h1 = () => ((document.querySelector('main h1') || {}).textContent || '').trim();
  const R = window.__a65 = {click: null, clicks: 0, ind: null, rowInd: null, flash: [], push: 0, closedAt: null,
    closedPath: null, closedH1: null, oldPath: location.pathname, oldH1: h1(), hist0: history.length, frames: 0};
  const ps = history.pushState;
  history.pushState = function (...a) { R.push++; return ps.apply(this, a); };
  document.addEventListener('click', () => { R.clicks++; if (R.click === null) R.click = performance.now(); }, true);
  const vis = el => { if (!el) return false; const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity > 0; };
  const check = () => {
    if (R.click === null) return;
    const now = performance.now();
    if (R.ind === null && vis(document.querySelector('[data-nav-progress]'))) R.ind = now;
    if (R.rowInd === null) { const r = document.querySelector('.mobile-menu [data-toc-loading]');
      if (r && vis(r) && /загружа/i.test(r.textContent)) R.rowInd = now; }
    const menu = !!document.querySelector('.mobile-menu');
    if (!menu) {
      if (R.closedAt === null) { R.closedAt = now; R.closedPath = location.pathname; R.closedH1 = h1(); }
      if (location.pathname === R.oldPath || h1() === R.oldH1)
        R.flash.push({ms: Math.round(now - R.click), path: decodeURI(location.pathname), h1: h1().slice(0, 40)});
    }
  };
  new MutationObserver(check).observe(document.documentElement, {subtree: true, childList: true, attributes: true, characterData: true});
  const loop = () => { check(); if (++R.frames < 3000) requestAnimationFrame(loop); };
  requestAnimationFrame(loop);
}"""

# A contents row that is a link to ANOTHER page (a chapter without subsections), shown in the open contents.
PICK = """() => { const here = location.pathname.replace(/\\/+$/, '');
  const rows = [...document.querySelectorAll('.mobile-menu nav a[data-toc-row^="sec:"]')]
    .filter(a => new URL(a.href).pathname.replace(/\\/+$/, '') !== here);
  return rows.length ? rows[0].getAttribute('data-toc-row') : null; }"""


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else info}", flush=True)


def run(p, dev, eng, o):
    b = getattr(p, eng).launch()
    c = b.new_context(locale="ru-RU", service_workers="block", **o)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    c.add_init_script(SLOW_FETCH)
    touch = o.get("has_touch", False)
    errs = []
    pg = c.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))

    def menu():
        return pg.locator(".mobile-menu").count() == 1

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

    def tap_at(loc):
        """A tap at the row's point (the same point every time), without Playwright's waiting."""
        box = loc.bounding_box()
        x, y = box["x"] + min(box["width"] / 2, 80), box["y"] + box["height"] / 2
        (pg.touchscreen.tap if touch else pg.mouse.click)(x, y)

    pg.goto(f"{BASE}/{L}/introduction/", wait_until="networkidle")
    pg.wait_for_timeout(700)
    pg.evaluate(f"() => {{ window.__a65delay = {DELAY_MS}; }}")   # before the contents open: their prefetch is slow too
    contents()
    rid = pg.evaluate(PICK)
    if not rid:
        chk(dev, "setup: a contents row linking to another page", False, "none found in the open contents")
        b.close()
        return
    row = pg.locator(f".mobile-menu nav [data-toc-row='{rid}']")
    target = pg.evaluate(f"() => new URL(document.querySelector(\".mobile-menu nav [data-toc-row='{rid}']\").href).pathname")
    row.scroll_into_view_if_needed()
    tap_at(row)                      # 1st tap: highlight only
    pg.wait_for_timeout(500)
    chk(dev, f"setup: 1st tap on {rid} only highlights (contents open, same page)",
        menu() and pg.locator(f".mobile-menu [data-toc-row='{rid}'][data-toc-lit]").count() == 1)
    pg.evaluate(RECORDER)
    tap_at(row)                      # 2nd tap: opens the page (slowed)
    pg.wait_for_timeout(150)
    r1 = pg.evaluate("() => window.__a65")
    d_ind = None if r1["ind"] is None else round(r1["ind"] - r1["click"])
    d_row = None if r1["rowInd"] is None else round(r1["rowInd"] - r1["click"])
    chk(dev, "1 at once (≤100 ms) after the 2nd tap: loading bar at the top", d_ind is not None and d_ind <= 100,
        f"bar after {d_ind} ms (None = never); menu={menu()}")
    chk(dev, "1 at once (≤100 ms) after the 2nd tap: the tapped row says «загружается…»",
        d_row is not None and d_row <= 100, f"row sign after {d_row} ms (None = never)")
    pg.wait_for_timeout(450)
    still_loading = menu() and pg.evaluate("() => location.pathname") != target
    if menu():
        tap_at(row)                  # repeated tap while loading
        pg.wait_for_timeout(120)
        tap_at(row)                  # and once more
        pg.wait_for_timeout(120)
    r2 = pg.evaluate("""() => ({bar: !!document.querySelector('[data-nav-progress]'),
        row: !!document.querySelector('.mobile-menu [data-toc-loading]'), menu: !!document.querySelector('.mobile-menu')})""")
    chk(dev, "2 repeated taps while loading: loading signs stay (navigation not restarted / not broken)",
        still_loading and r2["bar"] and r2["row"] and r2["menu"], f"was loading={still_loading} after taps {r2}")
    try:
        pg.wait_for_function(f"() => location.pathname === {target!r} && !document.querySelector('.mobile-menu')", timeout=15000)
    except Exception:
        pass
    pg.wait_for_timeout(900)
    r = pg.evaluate("() => window.__a65")
    now = pg.evaluate("""() => ({path: location.pathname, menu: !!document.querySelector('.mobile-menu'),
        bar: !!document.querySelector('[data-nav-progress]'), hist: history.length})""")
    chk(dev, "2 the tapped page opened, contents closed, loading bar gone",
        now["path"] == target and not now["menu"] and not now["bar"], f"{now} want {target}")
    chk(dev, "2 one navigation only: one new history entry, one pushState",
        now["hist"] - r["hist0"] == 1 and r["push"] == 1, f"history +{now['hist'] - r['hist0']}, pushState ×{r['push']}, clicks {r['clicks']}")
    chk(dev, "3 contents closed only together with the new page (URL and heading new at that moment)",
        r["closedAt"] is not None and r["closedPath"] == target and r["closedH1"] != r["oldH1"],
        f"closed at path={r['closedPath']} h1={(r['closedH1'] or '')[:40]!r} (old h1 {r['oldH1'][:40]!r})")
    chk(dev, "3 the old page never flashed (no frame / mutation with contents closed and old page shown)",
        not r["flash"], str(r["flash"][:3]))
    pg.evaluate("() => { window.__a65delay = 0; }")
    pg.go_back()
    pg.wait_for_timeout(1200)
    back = pg.evaluate("() => ({path: location.pathname, menu: !!document.querySelector('.mobile-menu')})")
    chk(dev, "2 «Назад» after it: the contents again, on the page before", back["menu"] and back["path"] == r["oldPath"],
        f"{back} want menu on {r['oldPath']}")

    # ---------- B: a very slow page (like the 19 s on the КСВ phone): longer than the menu's 8 s safety net ----------
    pg.close()
    pg = c.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"{BASE}/{L}/introduction/", wait_until="networkidle")
    pg.wait_for_timeout(700)
    pg.evaluate(f"() => {{ window.__a65delay = {SLOW_MS}; }}")
    contents()
    row = pg.locator(f".mobile-menu nav [data-toc-row='{rid}']")
    row.scroll_into_view_if_needed()
    tap_at(row)
    pg.wait_for_timeout(500)
    pg.evaluate(RECORDER)
    tap_at(row)
    pg.wait_for_timeout(9500)
    mid = pg.evaluate("""() => ({path: location.pathname, menu: !!document.querySelector('.mobile-menu'),
        bar: !!document.querySelector('[data-nav-progress]'), row: !!document.querySelector('.mobile-menu [data-toc-loading]')})""")
    chk(dev, "B 9.5 s into a 12 s load: still the contents with the loading signs (not the old page)",
        mid["path"] != target and mid["menu"] and mid["bar"] and mid["row"], str(mid))
    try:
        pg.wait_for_function(f"() => location.pathname === {target!r} && !document.querySelector('.mobile-menu')", timeout=20000)
    except Exception:
        pass
    pg.wait_for_timeout(900)
    r = pg.evaluate("() => window.__a65")
    chk(dev, "B 3 slow load: the old page never flashed; contents closed together with the new page",
        not r["flash"] and r["closedPath"] == target and r["closedH1"] != r["oldH1"],
        f"flash={r['flash'][:2]} closed at path={r['closedPath']}")
    chk(dev, "no page errors", not errs, str(errs[:3]))
    b.close()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        print(f"== {dev}", flush=True)
        try:
            run(p, dev, eng, o)
        except Exception as e:  # a crash is a failure, with its message
            chk(dev, "suite crashed", False, repr(e)[:300])
print(f"s30: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
