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
    res.append((d, n, bool(ok), info)); print(f"  [{'PASS' if ok else 'FAIL'}] {d} {n} [toc={qa.TOC_MODE_NAME}] {'' if ok else info}")


def run(p, dev, eng, o, mode):
    from toc import Contents, history_roundtrip
    br=getattr(p,eng).launch();errs=[]
    ctx=br.new_context(service_workers="block",**o)
    ctx.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
    pg=ctx.new_page();flow=Contents(pg,mode,o.get('has_touch',False))
    pg.on('pageerror',lambda e:errs.append(str(e)))
    mode.start(pg,P);pg.wait_for_timeout(600)
    pg.evaluate(f"document.querySelector('.app-main').scrollTop={qa.READING_POSITION_JS}.start+900")
    pg.wait_for_timeout(400);y0=pg.locator('.app-main').evaluate('e=>e.scrollTop')
    flow.contents();initial=flow.state()
    chk(dev,'(a) contents open',initial['menu'])
    chk(dev,'(a) current chapter 6 auto-expanded','daily-deity-schedule' in initial['open'])
    chk(dev,'(a) chapter 5 collapsed, is a disclosure button',flow.chapter(CH5).count()==1 and CH5 not in initial['open'])
    before=flow.state();flow.tap(flow.chapter(CH5),right=True,wait=300);first=flow.state()
    chk(dev,'(a) v7.5: first chapter tap follows the selected model',first['lit']==['sec:'+CH5] and first['menu'] and ((CH5 in first['open'] and first['url'].endswith('/'+CH5+'/') and abs(pg.evaluate(qa.READING_POSITION_JS)['top'])<2) if mode.one else (CH5 not in first['open'] and first['url']==before['url'])),str(first))
    chk(dev,'(a) first tap creates only the action or legacy highlight entry',first['pushes']==before['pushes']+1)
    if not mode.one:flow.tap(flow.chapter(CH5),right=True)
    n=pg.locator(f'#toc-ch-{CH5} a').count();first_text=pg.locator(f'#toc-ch-{CH5} a').first.inner_text()
    chk(dev,'(a) second tap on chapter 1 -> subsections 1.x visible (legacy); first in default',n>=4 and CH5 in flow.state()['open'] and '1.1' in first_text)
    chk(dev,'(a) v7: list starts with the first subsection «1.1» (no «Начало главы»)',first_text.startswith('1.1'))
    chk(dev,'(a) page follows the model, contents still open',flow.state()['menu'] and (flow.state()['url'].endswith('/'+CH5+'/') if mode.one else pg.url==P))
    h=pg.locator(f'[data-toc-chapter="{CH5}"],#toc-ch-{CH5} a').evaluate_all('es=>es.map(e=>e.getBoundingClientRect().height)')
    chk(dev,'(a) chapter + subsection rows >= 44px',min(h)>=43.5,str(h))
    sub=pg.locator(f'#toc-ch-{CH5} a').nth(2);label=sub.inner_text();href=sub.get_attribute('href');anchor=href.split('#')[1]
    before=flow.state();flow.tap(sub,wait=400);first=flow.state()
    chk(dev,'(a) v5: first tap on 5.3 follows the model',not first['menu'] and first['url'].endswith('#'+anchor) if mode.one else first['menu'] and first['lit']==['sub:'+CH5+'#'+anchor] and first['url']==before['url'],str(first))
    if not mode.one:flow.tap(sub,wait=400)
    chk(dev,'(a) tap 5.3 -> URL at 5.3, drawer closed',label.startswith('1.3') and not flow.state()['menu'] and pg.url.endswith('#'+anchor))
    top=qa.reading_eval(pg,'(root,id)=>root.querySelector(`[id="${CSS.escape(id)}"]`).getBoundingClientRect().top',anchor)
    chk(dev,'(a) 5.3 heading at top of the screen',-5<=top<250,str(top))
    back_presses=0
    flow.nav('back',native=True);back_presses+=1;back=flow.state()
    chk(dev,'(a) back1 -> Contents open, chapter 5 expanded, 5.3 lit, original page',back['menu'] and CH5 in back['open'] and back['lit']==['sub:'+CH5+'#'+anchor] and back['url']==before['url'],str(back))
    flow.nav('back',native=True);back_presses+=1;second=flow.state()
    chk(dev,'(a) back2 -> preceding real action / chapter 1 lit and expanded in legacy',second['menu'] and pg.url==P and second['lit']==['sec:'+CH5] and ((CH5 not in second['open']) if mode.one else CH5 in second['open']),str(second))
    if not mode.one:
        flow.nav('back',native=True);back_presses+=1;third=flow.state()
        chk(dev,'(a) back3 -> chapter 1 lit, collapsed (the 1st-tap step)',third['menu'] and CH5 not in third['open'] and third['lit']==['sec:'+CH5] and pg.url==P,str(third))
        flow.nav('back',native=True);back_presses+=1;fourth=flow.state()
        chk(dev,'(a) back4 -> Contents as opened (chapter 1 collapsed, not lit)',fourth['menu'] and CH5 not in fourth['open'] and fourth['lit']==initial['lit'] and pg.url==P,str(fourth))
    else:
        for id in ['(a) back3 -> chapter 1 lit, collapsed (the 1st-tap step)','(a) back4 -> Contents as opened (chapter 1 collapsed, not lit)']:
            print(f'  [SKIP] {dev} {id} [toc=default] — the highlight updates the original menu entry; there is no separate highlight-only predecessor.',flush=True)
    flow.nav('back',native=True);back_presses+=1
    chk(dev,'(a) back5 -> Contents closed, original page + scroll',not flow.state()['menu'] and pg.url==P and abs(pg.locator('.app-main').evaluate('e=>e.scrollTop')-y0)<40)
    chk(dev,'(a) Back presses to the original chapter match the model',back_presses==(3 if mode.one else 5) and pg.url==P)
    # B keeps the original deep-link selection AND its two-tap legacy toggle checks.
    pg.goto(f'{BASE}/{LANG}/{CH5}/#{anchor}',wait_until='networkidle');pg.wait_for_timeout(600);flow.contents()
    selected=pg.locator(f'#toc-ch-{CH5} a[aria-current=location]')
    chk(dev,'(b) reading 5.3: chapter 5 auto-expanded, 5.3 highlighted',CH5 in flow.state()['open'] and selected.count()==1 and selected.get_attribute('href')==href)
    u0=flow.state()['url'];flow.tap(flow.chapter(CH5),right=True)
    chk(dev,'(b) v7.5: chapter row, first tap follows the model',flow.state()['url']==u0 and flow.state()['lit']==['sec:'+CH5] and (CH5 in flow.state()['open'])!=mode.one)
    if not mode.one:flow.tap(flow.chapter(CH5),right=True)
    chk(dev,'(b) v7.5: chapter row, second tap collapses legacy / first collapses default, no navigation',flow.state()['url']==u0 and CH5 not in flow.state()['open'] and flow.state()['lit']==['sec:'+CH5])
    pg.goto(P,wait_until='networkidle');pg.wait_for_timeout(500);flow.contents();long='arcana-procedure';flow.activate(flow.chapter(long))
    low=pg.locator(f'#toc-ch-{long} a').last;low_href=low.get_attribute('href');low.scroll_into_view_if_needed();pg.wait_for_timeout(400)
    t0=pg.locator('.toc-scroll').evaluate('e=>e.scrollTop');p0=low.bounding_box()['y'];u0=flow.state()['url'];flow.activate(low,wait=400)
    chk(dev,'(d) drawer scrolled down to a low item',t0>200,str(t0))
    chk(dev,'(d) low item opened, drawer closed',not flow.state()['menu'] and pg.url.endswith('#'+low_href.split('#')[1]))
    flow.nav('back',native=True);t1=pg.locator('.toc-scroll').evaluate('e=>e.scrollTop');p1=pg.locator(f'#toc-ch-{long} a').last.bounding_box()['y']
    chk(dev,'(d) Back -> drawer at the same scrollTop (±10px), item in place',flow.state()['menu'] and flow.state()['url']==u0 and abs(t1-t0)<=10 and abs(p1-p0)<=10,str([t0,t1,p0,p1]))
    chk(dev,'(d) Back -> the selected low row stays highlighted',flow.state()['lit']==['sub:'+long+'#'+low_href.split('#')[1]])
    flow.nav('back',native=True)
    if not mode.one:
        chk(dev,'(d) Back -> chapter 8 lit and expanded (the step before the low item)',long in flow.state()['open'] and flow.state()['lit']==['sec:'+long])
        flow.nav('back',native=True)
    chk(dev,'(d) Back -> chapter collapsed, Contents open',flow.state()['menu'] and long not in flow.state()['open'])
    if not mode.one:flow.nav('back',native=True)
    flow.nav('back',native=True)
    chk(dev,'(d) Back -> Contents closed, same page',not flow.state()['menu'] and pg.url==P)
    ctx.close()
    for sid in FRONT:
        c=br.new_context(service_workers='block',**o);c.add_init_script("localStorage.setItem('ap.readerHintSeen','1')");page=c.new_page();f=Contents(page,mode,o.get('has_touch',False));mode.start(page,COVER);f.contents();f.activate(f.group('introduction'))
        chk(dev,f'(c) {sid}: fresh session, collapsed at start',sid not in f.state()['open'])
        before=f.state();f.tap(f.chapter(sid),right=True);a=f.state()
        chk(dev,f'(c) {sid}: v7.5 first tap follows the model',a['lit']==['sec:'+sid] and ((sid in a['open'] and a['url'].endswith('/'+sid+'/') and abs(page.evaluate(qa.READING_POSITION_JS)['top'])<2) if mode.one else sid not in a['open'] and a['url']==before['url']),str(a))
        opened_url=a['url'];f.tap(f.chapter(sid),right=True);a=f.state()
        chk(dev,f'(c) {sid}: second tap expands legacy / collapses default without navigation',(sid in a['open'])!=(mode.one) and a['url']==opened_url,str(a))
        c.close()
    history_roundtrip(br,o,mode,lambda n,ok,i='':chk(dev,n,ok,i),BASE)
    chk(dev,'no page errors',not errs,str(errs[:3]));br.close()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        if ONLY and dev not in ONLY.split(","):
            continue
        print(dev)
        try:
            qa.run_toc_modes(lambda mode: run(p, dev, eng, o, mode), on_error=lambda e: chk(dev,"EXCEPTION",False,str(e)[:900]))
        except Exception as e:
            chk(dev, "EXCEPTION", False, str(e)[:900])
fails = [r for r in res if not r[2]]
print(f"\n{len(res) - len(fails)}/{len(res)} passed")
for f in fails:
    print("FAILED:", f[0], f[1], f[3][:300])
