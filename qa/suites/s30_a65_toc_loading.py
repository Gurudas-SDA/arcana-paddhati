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
A65 fix (Codex review 10.10): C — a repeated tap AFTER the 8 s safety time on the same row never starts a second
navigation; C2 — another row (two taps) after 8 s replaces the load: history +1, the last choice wins; D — the page
data fails: no endless «busy»; E — the row of the page already shown: no loading signs; F — «Назад» while loading
cancels the load (it never lands later); G — a11y: «загружается» in a live region outside aria-busy.
A65 fix 2 (Codex review 10.10, 2nd): D2 — the page data AND the full page load (Next.js's fallback) both fail
(.txt and the document request aborted): after AppShell's NAV_FAIL_MS (25 s) the loading state is cleared (no
bar, no «загружается», nothing aria-busy) and the row says «не удалось загрузить — коснитесь ещё раз»; F waits for
the state (no fixed 400 ms); F2 — fast «Назад»→«Вперёд» while loading; F3 — «Вперёд» while loading.
Timings are measured in the page (performance.now from the click event); the delay must really intercept requests.
usage: python s30_a65_toc_loading.py <base-url>   devices: QA_DEVICES"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
ORIGIN = "/".join(BASE.split("/")[:3])
L = "ru-iast"
DEVICES = qa.devices(["pixel7", "iphone14", "ipad-portrait", "desktop", "mac-safari"])
DELAY_MS = 5000
SLOW_MS = 12000   # B: longer than AppShell's 8 s safety net (КСВ: sometimes 19 s)
FAIL_MS = 25000   # AppShell NAV_FAIL_MS: a page not come by then is given up
res = []

# Slows the page data of client-side navigations (RSC payload, *.txt) while window.__a65delay is set.
SLOW_FETCH = """(() => { const f = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const u = typeof input === 'string' ? input : (input && input.url) || String(input);
    const d = window.__a65delay || 0;
    if (d && /\\.txt(\\?|$)/.test(u)) { window.__a65slowed = (window.__a65slowed || 0) + 1;
      window.__a65fetches = (window.__a65fetches || []).concat([{t: performance.now(), u: u.split('?')[0]}]);
      return new Promise(r => setTimeout(r, d)).then(() => f(input, init)); }
    return f(input, init);
  }; })();"""

# In-page recorder, installed after the 1st tap (the highlight step) and before the 2nd.
RECORDER = """() => {
  const h1 = () => ((document.querySelector('main h1') || {}).textContent || '').trim();
  const R = window.__a65 = {click: null, clicks: 0, ind: null, rowInd: null, flash: [], push: 0, closedAt: null,
    closedPath: null, closedH1: null, oldPath: location.pathname, oldH1: h1(), hist0: history.length, frames: 0,
    live: null, livePre: null, fetch0: (window.__a65fetches || []).length};
  // a11y: the status regions present BEFORE the tap (a live region must exist before its text changes)
  document.querySelectorAll('[role=status],[aria-live]').forEach(el => { el.__a65pre = true; });
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
    if (R.live === null) {
      // «загружается» announced: a status / live region with the text, NOT inside an aria-busy="true" container
      const lr = [...document.querySelectorAll('[role=status],[aria-live=polite],[aria-live=assertive]')]
        .find(el => /загружа/i.test(el.textContent || '') && !el.closest('[aria-busy="true"]'));
      if (lr) { R.live = now; R.livePre = !!lr.__a65pre; }
    }
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
    for _ in range(3):               # a slow WebKit tablet: the contents may still be opening
        if rid:
            break
        pg.wait_for_timeout(800)
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
    slowed = pg.evaluate("() => window.__a65slowed || 0")
    chk(dev, "setup: the network delay really intercepted the page data (counter > 0)", slowed > 0,
        "the fetch wrapper slowed NO request — the test would measure nothing (has Next.js changed how it loads pages?)")
    d_live = None if r1["live"] is None else round(r1["live"] - r1["click"])
    chk(dev, "G a11y: «загружается» in a live region (role=status) outside aria-busy, ≤100 ms, present before the tap",
        d_live is not None and d_live <= 100 and r1["livePre"], f"live after {d_live} ms (None = never / only inside aria-busy), existed before={r1['livePre']}")
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
    busy = pg.evaluate("() => document.querySelectorAll('[aria-busy=\"true\"]').length")
    chk(dev, "G a11y: nothing stays aria-busy after the page opened", busy == 0, f"{busy} aria-busy elements")
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
    STATE = """() => ({path: location.pathname, menu: !!document.querySelector('.mobile-menu'),
        bar: !!document.querySelector('[data-nav-progress]'), row: !!document.querySelector('.mobile-menu [data-toc-loading]'),
        busy: document.querySelectorAll('[aria-busy="true"]').length, hist: history.length})"""

    def fresh(delay, start=f"{L}/introduction/", errors=True, abort=False, fail_doc=False):
        """A new page at `start`, page data slowed by `delay` ms (or aborted), contents open, row `rid` tapped once
        (highlighted), the recorder installed. Returns the row locator (None if the row is not there)."""
        nonlocal pg
        pg.close()
        pg = c.new_page()
        if errors:
            pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"{BASE}/{start}" if not start.startswith("/") else ORIGIN + start, wait_until="networkidle")
        pg.wait_for_timeout(700)
        if abort:
            pg.route(lambda u: ".txt" in u, lambda route: route.abort())
        if fail_doc:
            # the full page load (Next.js's fallback after the page data failed) fails too; ERR_ABORTED keeps
            # the old document (no browser error page) — like a load the network dropped
            pg.route("**/*", lambda route: route.abort("aborted") if route.request.resource_type == "document"
                     else route.fallback())
        pg.evaluate(f"() => {{ window.__a65delay = {delay}; }}")
        contents()
        rw = pg.locator(f".mobile-menu nav [data-toc-row='{rid}']")
        if rw.count() == 0:
            return None
        rw.scroll_into_view_if_needed()
        tap_at(rw)
        pg.wait_for_timeout(500)
        pg.evaluate(RECORDER)
        return rw

    # ---------- C: a repeated tap AFTER the 8 s safety time (Codex A65 HIGH): still one navigation ----------
    row = fresh(SLOW_MS)
    tap_at(row)                      # 2nd tap: the page starts loading (12 s)
    pg.wait_for_timeout(9000)
    t_retry = pg.evaluate("() => performance.now()")
    if menu():
        tap_at(row)                  # the reader taps again after 8 s
        pg.wait_for_timeout(120)
        tap_at(row)
        pg.wait_for_timeout(150)
    mid = pg.evaluate(STATE)
    chk(dev, "C repeated tap after 8 s: the loading signs stay (nothing restarted, menu not unlocked)",
        mid["path"] != target and mid["menu"] and mid["bar"] and mid["row"], str(mid))
    try:
        pg.wait_for_function(f"() => location.pathname === {target!r} && !document.querySelector('.mobile-menu')", timeout=25000)
    except Exception:
        pass
    pg.wait_for_timeout(900)
    r = pg.evaluate("() => Object.assign({}, window.__a65, {fetches: window.__a65fetches || []})")
    now = pg.evaluate(STATE)
    took = None if r["closedAt"] is None else round(r["closedAt"] - r["click"])
    # page-data requests of the TARGET page started by the repeated tap (= a second navigation)
    # (index.txt = a navigation's page payload; the segment files may still be streaming for the 1st load)
    refetch = [f for f in r["fetches"] if f["t"] > t_retry and f["u"].endswith(target + "index.txt")
               and (r["closedAt"] is None or f["t"] < r["closedAt"])]
    chk(dev, "C repeated tap after 8 s: no second navigation (no new page-data request, page came with the 1st load)",
        not refetch and took is not None and took <= SLOW_MS + 2500,
        f"page after {took} ms (1st load {SLOW_MS} ms); requests after the repeated tap: {[f['u'][-60:] for f in refetch][:3]}")
    chk(dev, "C repeated tap after 8 s: history +1 only, final URL = the tapped (last) target",
        now["hist"] - r["hist0"] == 1 and r["push"] <= 1 and now["path"] == target and not now["menu"],
        f"history +{now['hist'] - r['hist0']}, pushState ×{r['push']}, now {now}, want {target}")
    chk(dev, "C 3 the old page never flashed", not r["flash"], str(r["flash"][:2]))

    # ---------- C2: after 8 s the reader chooses ANOTHER row (two taps): it replaces the load — history +1, last wins ----------
    row = fresh(SLOW_MS)
    other = pg.evaluate("""(rid) => { const here = location.pathname.replace(/\\/+$/, '');
      const a = [...document.querySelectorAll('.mobile-menu nav a[data-toc-row^="sec:"]')]
        .find(a => a.getAttribute('data-toc-row') !== rid && new URL(a.href).pathname.replace(/\\/+$/, '') !== here);
      return a ? [a.getAttribute('data-toc-row'), new URL(a.href).pathname] : null; }""", rid)
    if not other:
        chk(dev, "C2 setup: a second contents row linking to another page", False)
    else:
        rid2, target2 = other
        tap_at(row)                  # 2nd tap on row 1: its page starts loading (12 s)
        pg.wait_for_timeout(9000)
        row2 = pg.locator(f".mobile-menu nav [data-toc-row='{rid2}']")
        if menu():
            pg.evaluate(f"() => document.querySelector(\".mobile-menu nav [data-toc-row='{rid2}']\").scrollIntoView({{block: 'center'}})")
            pg.wait_for_timeout(300)
            tap_at(row2)             # another row after 8 s: 1st tap highlights
            pg.wait_for_timeout(400)
            tap_at(row2)             # 2nd tap: its page replaces the pending one
        try:
            pg.wait_for_function(f"() => location.pathname === {target2!r} && !document.querySelector('.mobile-menu')", timeout=25000)
        except Exception:
            pass
        pg.wait_for_timeout(SLOW_MS)  # long enough for the replaced load to come — it must not
        r = pg.evaluate("() => window.__a65")
        st = pg.evaluate(STATE)
        chk(dev, "C2 another row after 8 s: history +1 only, the LAST choice opened and stays (the replaced load never lands)",
            st["hist"] - r["hist0"] == 1 and st["path"] == target2 and not st["menu"] and not st["bar"] and st["busy"] == 0,
            f"history +{st['hist'] - r['hist0']}, pushState ×{r['push']}, now {st}, want {target2} (first target {target})")
        chk(dev, "C2 3 the old page never flashed", not r["flash"], str(r["flash"][:2]))
        # Claude verifier 11.10 (MED): the loading state must not stay on after the page came — the live region
        # kept «загружается» and every reopened contents showed a loading bar with nothing loading
        live = pg.evaluate("() => (document.querySelector('[data-nav-live]') || {}).textContent || ''")
        chk(dev, "C2 after the page opened: the live region is empty (no «загружается» left)", live.strip() == "", repr(live))
        contents()
        pg.wait_for_timeout(600)
        st2 = pg.evaluate(STATE)
        live2 = pg.evaluate("() => (document.querySelector('[data-nav-live]') || {}).textContent || ''")
        chk(dev, "C2 contents opened again on the new page: no loading bar, no «загружается», nothing busy",
            st2["menu"] and not st2["bar"] and not st2["row"] and st2["busy"] == 0 and live2.strip() == "",
            f"{st2} live={live2!r}")
        pg.evaluate("() => history.back()")
        pg.wait_for_timeout(600)
        pg.evaluate("() => { window.__a65delay = 0; }")
        pg.evaluate("() => history.back()")
        pg.wait_for_timeout(1200)
        back = pg.evaluate(STATE)
        chk(dev, "C2 «Назад» from it: the contents on the page before", back["menu"] and back["path"] == r["oldPath"],
            f"{back} want menu on {r['oldPath']}")

    # ---------- D: the page data fails (network error): no endless «busy» ----------
    row = fresh(0, errors=False, abort=True)
    if row is None:
        chk(dev, "D setup: the row is there", False)
    else:
        tap_at(row)
        pg.wait_for_timeout(8000)
        st = pg.evaluate(STATE)
        opened = st["path"] == target and not st["menu"] and not st["bar"]
        cleared = st["menu"] and not st["bar"] and not st["row"] and st["busy"] == 0
        chk(dev, "D page data failed: the loading state is cleared (page opened another way, or menu not busy)",
            (opened or cleared) and st["busy"] == 0, str(st))

    # ---------- D2: page data AND the full page load fail: after NAV_FAIL_MS nothing is busy, a quiet note ----------
    row = fresh(0, errors=False, abort=True, fail_doc=True)
    if row is None:
        chk(dev, "D2 setup: the row is there", False)
    else:
        tap_at(row)
        pg.wait_for_timeout(1500)
        st0 = pg.evaluate(STATE)
        chk(dev, "D2 setup: page data and document aborted — the loading signs are shown first",
            st0["menu"] and st0["bar"] and st0["row"], str(st0))
        try:
            pg.wait_for_function("() => !document.querySelector('[data-nav-progress]')", timeout=FAIL_MS + 5000)
        except Exception:
            pass
        st = pg.evaluate(STATE)
        note = pg.evaluate("""() => { const n = document.querySelector('.mobile-menu [data-toc-failed]');
            const live = document.querySelector('[data-nav-live]');
            return {note: n ? n.textContent : null, live: live ? live.textContent : null}; }""")
        chk(dev, f"D2 page data + page load failed: after {FAIL_MS // 1000} s the loading state is cleared (no bar, no row sign, nothing busy)",
            st["menu"] and not st["bar"] and not st["row"] and st["busy"] == 0 and st["path"] != target, str(st))
        chk(dev, "D2 the row says «не удалось загрузить — коснитесь ещё раз» (and the live region)",
            bool(note["note"]) and "не удалось" in note["note"] and "не удалось" in (note["live"] or ""), str(note))

    # ---------- E: the row of the page already shown: no loading signs at all ----------
    row = fresh(DELAY_MS, start=target)
    if row is None:
        chk(dev, "E setup: the row of the shown page is in the contents", False)
    else:
        tap_at(row)                  # 2nd tap on the row of the page being read
        pg.wait_for_timeout(700)
        r = pg.evaluate("() => window.__a65")
        st = pg.evaluate(STATE)
        chk(dev, "E same page: no loading bar / «загружается», no navigation, nothing busy",
            r["ind"] is None and r["rowInd"] is None and st["path"] == target and not st["bar"] and st["busy"] == 0
            and st["hist"] - r["hist0"] <= 1, f"bar at {r['ind']}, row at {r['rowInd']}, {st}")

    # ---------- F: «Назад» while the page loads: the load is cancelled, it never comes later ----------
    row = fresh(DELAY_MS)
    tap_at(row)
    pg.wait_for_timeout(1000)
    h_before = pg.evaluate("() => history.length")
    pg.evaluate("() => history.back()")
    try:   # the state, not a fixed time (Codex LOW 10.10)
        pg.wait_for_function("""(old) => location.pathname === old && !!document.querySelector('.mobile-menu')
            && !document.querySelector('[data-nav-progress]')""", arg=pg.evaluate("() => window.__a65.oldPath"), timeout=5000)
    except Exception:
        pass
    st = pg.evaluate(STATE)
    r = pg.evaluate("() => window.__a65")
    chk(dev, "F «Назад» while loading: loading signs cleared at once, the step before (contents) shown",
        st["path"] == r["oldPath"] and st["menu"] and not st["bar"] and not st["row"] and st["busy"] == 0, str(st))
    pg.wait_for_timeout(DELAY_MS + 2500)
    st = pg.evaluate(STATE)
    r = pg.evaluate("() => window.__a65")
    chk(dev, "F «Назад» while loading: the cancelled page never opens later (URL, history unchanged)",
        st["path"] == r["oldPath"] and st["hist"] == h_before and not st["bar"] and st["busy"] == 0,
        f"{st}, history before back {h_before}, want path {r['oldPath']}")
    chk(dev, "F 3 no flash of the old page after «Назад» (contents stay)", not r["flash"] and st["menu"], f"{r['flash'][:2]} menu={st['menu']}")


    # ---------- F2: fast «Назад» → «Вперёд» while loading: nothing busy, the cancelled page never comes ----------
    def settled(timeout=5000):
        try:
            pg.wait_for_function("""() => !document.querySelector('[data-nav-progress]')
                && !document.querySelector('[aria-busy="true"]')""", timeout=timeout)
        except Exception:
            pass

    row = fresh(DELAY_MS)
    tap_at(row)
    pg.wait_for_timeout(1000)
    h_before = pg.evaluate("() => history.length")
    pg.evaluate("() => { history.back(); setTimeout(() => history.forward(), 60); }")
    settled()
    pg.wait_for_timeout(300)
    st = pg.evaluate(STATE)
    r = pg.evaluate("() => window.__a65")
    chk(dev, "F2 fast «Назад»→«Вперёд» while loading: contents (the highlighted step), no loading signs, nothing busy",
        st["path"] == r["oldPath"] and st["menu"] and not st["bar"] and not st["row"] and st["busy"] == 0, str(st))
    pg.wait_for_timeout(DELAY_MS + 2500)
    st = pg.evaluate(STATE)
    chk(dev, "F2 the cancelled page never opens later (URL, history unchanged)",
        st["path"] == r["oldPath"] and st["hist"] == h_before and not st["bar"] and st["busy"] == 0,
        f"{st}, history before {h_before}, want path {r['oldPath']}")

    # ---------- F3: «Вперёд» while a page loads: the forward entry is shown, nothing busy, no extra entry ----------
    pg.evaluate("() => { window.__a65delay = 0; }")
    row = fresh(0)
    tap_at(row)                      # 2nd tap: opens the target (fast)
    try:
        pg.wait_for_function(f"() => location.pathname === {target!r} && !document.querySelector('.mobile-menu')", timeout=10000)
    except Exception:
        pass
    pg.evaluate("() => history.back()")   # back to the contents step: the row is highlighted, target is «forward»
    try:
        pg.wait_for_function("() => !!document.querySelector('.mobile-menu')", timeout=5000)
    except Exception:
        pass
    pg.wait_for_timeout(500)
    # reload on the contents step, page data slowed from the start (also the contents' prefetch): the
    # router's cache is empty, so the next load really waits
    pg.add_init_script(f"window.__a65delay = {DELAY_MS};")
    pg.reload(wait_until="load")
    pg.wait_for_timeout(900)
    rw = pg.locator(f".mobile-menu nav [data-toc-row='{rid}']")
    ok_setup = rw.count() == 1 and pg.locator(f".mobile-menu [data-toc-row='{rid}'][data-toc-lit]").count() == 1
    chk(dev, "F3 setup: «Назад» from the page → contents (reloaded) with the row highlighted (forward = the page)", ok_setup)
    if ok_setup:
        pg.evaluate(f"() => {{ window.__a65delay = {DELAY_MS}; }}")
        pg.evaluate(RECORDER)
        h_before = pg.evaluate("() => history.length")
        rw.scroll_into_view_if_needed()
        tap_at(rw)                   # the highlighted row: one tap loads it (slowed)
        pg.wait_for_timeout(800)
        st0 = pg.evaluate(STATE)
        pg.evaluate("() => history.forward()")
        try:
            pg.wait_for_function(f"""() => location.pathname === {target!r} && !document.querySelector('.mobile-menu')
                && !document.querySelector('[data-nav-progress]')""", timeout=8000)
        except Exception:
            pass
        st = pg.evaluate(STATE)
        chk(dev, "F3 «Вперёд» while loading: the forward page shown, contents closed, no loading signs, nothing busy",
            st0["bar"] and st["path"] == target and not st["menu"] and not st["bar"] and st["busy"] == 0,
            f"loading before={st0['bar']}, now {st}, want {target}")
        pg.wait_for_timeout(DELAY_MS + 2500)
        st = pg.evaluate(STATE)
        chk(dev, "F3 the pending load adds no history entry later and nothing reopens",
            st["path"] == target and st["hist"] == h_before and not st["menu"] and st["busy"] == 0,
            f"{st}, history before {h_before}")

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
