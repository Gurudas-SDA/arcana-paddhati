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



# These original IDs require a pending fetch, absent in either continuous mode.
PENDING_FETCH_CHECKS = ['1 at once (≤100 ms) after the 2nd tap: loading bar at the top',
 '1 at once (≤100 ms) after the 2nd tap: the tapped row says «загружается…»',
 'setup: the network delay really intercepted the page data (counter > 0)',
 'G a11y: «загружается» in a live region (role=status) outside aria-busy, ≤100 ms, present before '
 'the tap',
 '2 repeated taps while loading: loading signs stay (navigation not restarted / not broken)',
 'B 9.5 s into a 12 s load: still the contents with the loading signs (not the old page)',
 'B 3 slow load: the old page never flashed; contents closed together with the new page',
 'C repeated tap after 8 s: the loading signs stay (nothing restarted, menu not unlocked)',
 'C repeated tap after 8 s: no second navigation (no new page-data request, page came with the 1st '
 'load)',
 'C repeated tap after 8 s: history +1 only, final URL = the tapped (last) target',
 'C 3 the old page never flashed',
 'F «Назад» while loading: loading signs cleared at once, the step before (contents) shown',
 'F «Назад» while loading: the cancelled page never opens later (URL, history unchanged)',
 'F 3 no flash of the old page after «Назад» (contents stay)',
 'F2 fast «Назад»→«Вперёд» while loading: contents (the highlighted step), no loading signs, '
 'nothing busy',
 'F2 the cancelled page never opens later (URL, history unchanged)',
 'C2 setup: a second contents row linking to another page',
 'C2 another row after 8 s: history +1 only, the LAST choice opened and stays (the replaced load '
 'never lands)',
 'C2 3 the old page never flashed',
 'C2 «Назад» from it: the contents on the page before',
 'D page data failed: the loading state is cleared (page opened another way, or menu not busy)',
 'D2 setup: page data and document aborted — the loading signs are shown first',
 'D2 page data + page load failed: after 25 s the loading state is cleared (no bar, no row sign, '
 'nothing busy)',
 'D2 the row says «не удалось загрузить — коснитесь ещё раз» (and the live region)',
 'F3 «Вперёд» while loading: the forward page shown, contents closed, no loading signs, nothing '
 'busy',
 'F3 the pending load adds no history entry later and nothing reopens']

def run(p, dev, eng, o, mode):
    from toc import Contents, history_roundtrip
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
        if mode.one:chk(dev,f'setup: 1st tap on {rid} navigates immediately and records its trace',not now['menu'] and now['url']==target)
        chk(dev,'1 navigation completes within the unchanged 100 ms budget',record['closedAt'] is not None and record['closedAt']-record['click']<=100,str(record['closedAt']))
        chk(dev,'setup: continuous target is already present, no chapter fetch intercepted',page.evaluate('window.__a65slowed || 0')==0)
        chk(dev,'2 the tapped page opened, contents closed, loading bar gone',now['url']==target and not now['menu'] and not page.locator('[data-nav-progress]').count())
        chk(dev,'G a11y: nothing stays aria-busy after the page opened',page.locator('[aria-busy="true"]').count()==0)
        chk(dev,'2 one navigation only: one new history entry, one pushState',now['history']-record['hist0']==1 and record['push']==1,str(record['push']))
        chk(dev,'3 contents closed only together with the new page (URL and heading new at that moment)',record['closedAt'] is not None and record['closedPath']==target and record['closedH1']!=record['oldH1'],str(record['flash'][:2]))
        chk(dev,'3 the old page never flashed (no frame / mutation with contents closed and old page shown)',not record['flash'],str(record['flash'][:2]))
        chk(dev,'C2 after the page opened: the live region is empty (no «загружается» left)',page.locator('[data-nav-live]').inner_text().strip()=='')
        flow.nav('back',native=True);back=flow.state()
        chk(dev,'2 «Назад» after it: the contents again, on the page before',back['menu'] and back['url']==before['url'] and back['lit']==[rid],str(back))
        page.reload(wait_until='domcontentloaded');qa.wait_for_book_chapter(page,'introduction');page.wait_for_timeout(500)
        chk(dev,'F3 setup: «Назад» from the page → contents (reloaded) with the row highlighted (forward = the page)',flow.state()['menu'] and flow.state()['lit']==[rid])
        flow.nav('forward',native=True);flow.contents();current=flow.row(rid)
        chk(dev,'C2 contents opened again on the new page: no loading bar, no «загружается», nothing busy',flow.state()['menu'] and not page.locator('[data-nav-progress],[data-toc-loading],[aria-busy="true"]').count() and page.locator('[data-nav-live]').inner_text().strip()=='')
        for id in ['D setup: the row is there','D2 setup: the row is there','E setup: the row of the shown page is in the contents']:chk(dev,id,current.count()==1)

        if not mode.one:flow.tap(current)
        previous=flow.state();flow.tap(current,wait=300);same=flow.state()
        chk(dev,'E same page: no loading bar / «загружается», no navigation, nothing busy',same['url']==target and same['pushes']==previous['pushes'] and not page.locator('[data-nav-progress],[aria-busy="true"]').count(),str(same))
        for name in PENDING_FETCH_CHECKS:
            print(f'  [SKIP] {dev} {name} [toc={mode.name}] — continuous target is already in the DOM; no pending chapter fetch to delay, fail or cancel.',flush=True)
        history_roundtrip(browser,o,mode,lambda n,ok,i='':chk(dev,n,ok,i),BASE)
        chk(dev,'no page errors',not errors,str(errors[:3]))
    finally:context.close();browser.close()


with sync_playwright() as p:
    for dev,eng,o in DEVICES:
        qa.run_toc_modes(lambda mode:run(p,dev,eng,o,mode),on_error=lambda e:chk(dev,'suite crashed',False,repr(e)[:300]))
print(f's30: {sum(res)}/{len(res)} passed')
sys.exit(0 if res and all(res) else 1)
