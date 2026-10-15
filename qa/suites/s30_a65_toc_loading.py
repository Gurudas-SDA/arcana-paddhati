"""A65 (КСВ-dublieris 07.10.2026): «Содержание» — a tap on a row must answer at once, a repeated tap must not
break anything, and the old page must never flash before the new one.

Since the continuous book (V1) every chapter is already in the page, so a Contents tap loads nothing: the
states «загружается», «не удалось загрузить» and «Назад» while loading cannot occur. Rule KSV-A65 item 1 now
reads «opens the place within 100 ms; if the chapter is not loaded yet, the loading sign shows at once».
Checked here:
  setup — the slowed page-data fetch intercepts NOTHING (the premise of this file; if chapters are ever loaded
          over the network again, e.g. lazy chapters in V1.1, this check turns red and the loading scenarios
          B, C, C2, D, D2, F, F2, F3 must come back — their last full version is in 4a972ab);
  1) within 100 ms of the tap the loading sign or the new page shows (the rule's second half); how long the
     page took is only recorded: chapter by chapter (Vraja PR 2, 15.10) the next chapter is another page;
  2) one navigation only (one history entry, one pushState), «Назад» returns to the contents;
  3) the contents close only together with the new page; the old page never flashes;
  E — the row of the page already shown: no navigation, no loading signs; G — nothing stays aria-busy.
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

# In-page recorder, installed before the tap that navigates.
RECORDER = """() => {
  const h1 = () => ((__READING_ROOT__.querySelector('h1') || {}).textContent || '').trim();
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
RECORDER = RECORDER.replace("__READING_ROOT__", qa.READING_ROOT_JS)

PICK = """() => { const here = location.pathname.replace(/\\/+$/, '');
  const rows = [...document.querySelectorAll('.mobile-menu nav a[data-toc-row^="sec:"]')]
    .filter(a => new URL(a.href).pathname.replace(/\\/+$/, '') !== here);
  return rows.length ? rows[0].getAttribute('data-toc-row') : null; }"""


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} [toc={qa.TOC_MODE_NAME}] {'' if ok else info}", flush=True)



def run(p, dev, eng, o, mode):
    from toc import Contents, history_roundtrip, marks_place
    browser=getattr(p,eng).launch();context=browser.new_context(locale='ru-RU',service_workers='block',**o)
    context.add_init_script("localStorage.setItem('ap.readerHintSeen','1')");context.add_init_script(SLOW_FETCH)
    page=context.new_page();flow=Contents(page,mode,o.get('has_touch',False));errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    try:
        mode.start(page,f'{BASE}/{L}/introduction/');page.wait_for_timeout(500);flow.contents();rid=page.evaluate(PICK)
        chk(dev,'setup: a contents row linking to another page',bool(rid))
        row=flow.row(rid);target=page.evaluate('(href)=>new URL(href,location.href).pathname',row.get_attribute('href'));before=flow.state()
        if not mode.one:
            flow.tap(row)
            chk(dev,f'setup: 1st tap on {rid} only highlights (contents open, same page)',flow.state()['menu'] and flow.state()['url']==before['url'] and flow.state()['lit']==[rid])
        # Slow-fetch instrumentation remains installed: assert navigation uses no fetch.
        page.evaluate(f'window.__a65delay={DELAY_MS}')
        page.evaluate(RECORDER);row.scroll_into_view_if_needed();flow.tap(row,wait=200);record=page.evaluate('window.__a65');now=flow.state()
        if mode.one:chk(dev,f'setup: 1st tap on {rid} navigates immediately',not now['menu'] and now['url']==target)
        ms=lambda k:None if record[k] is None or record['click'] is None else round(record[k]-record['click'])
        print(f"  [INFO] {dev} 1 timings after the tap (ms): page opened {ms('closedAt')}, loading bar {ms('ind')}, row «загружается» {ms('rowInd')}, live region {ms('live')} [toc={qa.TOC_MODE_NAME}]",flush=True)
        first=[v for v in (ms('closedAt'),ms('ind'),ms('rowInd')) if v is not None]
        chk(dev,'1 within 100 ms of the tap the loading sign (bar or row «загружается») or the new page shows',bool(first) and min(first)<=100,
            f"page opened {ms('closedAt')} ms, loading bar {ms('ind')} ms, row sign {ms('rowInd')} ms")
        chk(dev,'setup: continuous target is already present, no chapter fetch intercepted',page.evaluate('window.__a65slowed || 0')==0)
        chk(dev,'2 the tapped page opened, contents closed, loading bar gone',now['url']==target and not now['menu'] and not page.locator('[data-nav-progress]').count())
        chk(dev,'G a11y: nothing stays aria-busy after the page opened',page.locator('[aria-busy="true"]').count()==0)
        chk(dev,'2 one navigation only: one new history entry, one pushState',now['history']-record['hist0']==1 and record['push']==1,str(record['push']))
        chk(dev,'3 contents closed only together with the new page (URL and heading new at that moment)',record['closedAt'] is not None and record['closedPath']==target and record['closedH1']!=record['oldH1'],str(record['flash'][:2]))
        chk(dev,'3 the old page never flashed (no frame / mutation with contents closed and old page shown)',not record['flash'],str(record['flash'][:2]))
        chk(dev,'C2 after the page opened: the live region is empty (no «загружается» left)',page.locator('[data-nav-live]').inner_text().strip()=='')
        flow.nav('back',native=True);back=flow.state()
        chk(dev,'2 «Назад» after it: the contents again, on the page before, reading place marked',back['menu'] and back['url']==before['url'] and back['open']==before['open'] and marks_place(back),str(back))
        page.reload(wait_until='domcontentloaded');qa.wait_for_book_chapter(page,'introduction');page.wait_for_timeout(500)
        chk(dev,'F3 setup: «Назад» from the page → contents (reloaded) marking the reading place (forward = the page)',flow.state()['menu'] and flow.state()['url']==before['url'] and flow.state()['open']==before['open'] and marks_place(flow.state()))
        flow.nav('forward',native=True);flow.contents();current=flow.row(rid)
        chk(dev,'C2 contents opened again on the new page: no loading bar, no «загружается», nothing busy',flow.state()['menu'] and not page.locator('[data-nav-progress],[data-toc-loading],[aria-busy="true"]').count() and page.locator('[data-nav-live]').inner_text().strip()=='')
        for id in ['D setup: the row is there','D2 setup: the row is there','E setup: the row of the shown page is in the contents']:chk(dev,id,current.count()==1)

        if not mode.one:flow.tap(current)
        previous=flow.state();flow.tap(current,wait=300);same=flow.state()
        chk(dev,'E same page: no loading bar / «загружается», no navigation, nothing busy',same['url']==target and same['pushes']==previous['pushes'] and not page.locator('[data-nav-progress],[aria-busy="true"]').count(),str(same))
        history_roundtrip(browser,o,mode,lambda n,ok,i='':chk(dev,n,ok,i),BASE)
        chk(dev,'no page errors',not errors,str(errors[:3]))
    finally:context.close();browser.close()


with sync_playwright() as p:
    for dev,eng,o in DEVICES:
        qa.run_toc_modes(lambda mode:run(p,dev,eng,o,mode),on_error=lambda e:chk(dev,'suite crashed',False,repr(e)[:300]))
print(f's30: {sum(res)}/{len(res)} passed')
sys.exit(0 if res and all(res) else 1)
