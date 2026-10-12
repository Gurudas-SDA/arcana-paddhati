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
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} [toc={qa.TOC_MODE_NAME}] {'' if ok else info}", flush=True)


def run(p, dev, eng, o, mode):
    from toc import Contents, history_roundtrip
    browser=getattr(p,eng).launch();context=browser.new_context(locale='ru-RU',service_workers='block',**o)
    context.add_init_script("localStorage.setItem('ap.readerHintSeen','1')");errors=[]
    def fresh(path):
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));flow=Contents(page,mode,o.get('has_touch',False));mode.start(page,f'{BASE}/{L}/{path}');page.wait_for_timeout(400);return page,flow
    def same(a,b):return all(a[k]==b[k] for k in ['url','menu','lit','open'])
    def reload(page,chapter):
        page.reload(wait_until='domcontentloaded');qa.wait_for_book_chapter(page,chapter);page.wait_for_timeout(500)
    # A: collapsed state survives reload, Back and Forward.
    pg,f=fresh('introduction/');f.contents();s0=f.state();f.tap(f.group('introduction'));s1=f.state()
    if not mode.one:f.tap(f.group('introduction'))
    collapsed=f.state();previous=s0 if mode.one else s1
    chk(dev,'A setup: «Введение» open → collapse by the selected model','introduction' in s0['open'] and 'introduction' not in collapsed['open'] and collapsed['lit']==['grp:introduction'] and (mode.one or 'introduction' in s1['open']),str(collapsed))
    reload(pg,'introduction');chk(dev,'A after reload: «Введение» still collapsed, lit, contents open, same URL',same(f.state(),collapsed),str(f.state()))
    f.nav('back');chk(dev,'A Назад after reload: the step before (open, same highlight)',same(f.state(),previous),str([f.state(),previous]))
    f.nav('forward');chk(dev,'A Вперёд: collapsed again',same(f.state(),collapsed));pg.close()
    # B: six steps, then reload in the middle, with the same exact states.
    pg,f=fresh('introduction/');f.contents();states=[f.state()]
    if mode.one:
        f.tap(f.group('temple-worship'));states.append(f.state())
        ids=pg.locator('#toc-part-temple-worship [data-toc-chapter],#toc-grp-temple-worship [data-toc-chapter]').evaluate_all('es=>es.slice(0,5).map(e=>e.dataset.tocChapter)')
        for id in ids:
            states[-1]['lit']=['sec:'+id];f.tap(f.chapter(id));states.append(f.state())
    else:
        for kind,id in [('group','temple-worship'),('chapter','daily-duties-brahma-muhurta'),('chapter','daily-deity-schedule')]:
            loc=f.group(id) if kind=='group' else f.chapter(id)
            for _ in range(2):f.tap(loc);states.append(f.state())
    chk(dev,'B setup: 6 steps, each a different state',len(states)==7 and len({str({k:s[k] for k in ['url','menu','lit','open']}) for s in states})==7,str(states))
    for _ in range(3):f.nav('back')
    midpoint=f.state();chapter=midpoint['url'].rstrip('/').split('/')[-1];reload(pg,chapter)
    chk(dev,'B reload after 3 × Назад: the same step (URL, highlight, open lists)',same(midpoint,states[3]) and same(f.state(),states[3]),str([f.state(),states[3]]))
    f.nav('back');bad=[] if same(f.state(),states[2]) else [(f.state(),states[2])]
    for k in [3,4,5,6]:
        f.nav('forward')
        if not same(f.state(),states[k]):bad.append((f.state(),states[k]))
    chk(dev,'B Назад, then Вперёд ×4 after the reload: each step as recorded (to the last one)',not bad,str(bad[:2]));pg.close()
    # C: a direct subsection link and the model's two/three steps Back.
    pg,f=fresh('daily-deity-schedule/#morning-bhoga-arati');pg.wait_for_timeout(500)
    top=qa.reading_eval(pg,"root=>root.querySelector('#morning-bhoga-arati').getBoundingClientRect().top-document.querySelector('.app-main').getBoundingClientRect().top")
    chk(dev,'C deep link: the subsection heading is at the top',-2<=top<=140,str(top))
    deep=f.state();f.contents();original=f.state();sub_deep='sub:daily-deity-schedule#morning-bhoga-arati'
    chk(dev,'C contents: that subsection lit, its chapter open',original['lit']==[sub_deep] and 'daily-deity-schedule' in original['open'],str(original))
    other=pg.locator('#toc-ch-daily-deity-schedule a').last.get_attribute('data-toc-row');before=f.state();f.tap(f.row(other),wait=350);first=f.state()
    if not mode.one:f.tap(f.row(other),wait=350)
    target=f.state();chk(dev,'C another subsection: default one action / legacy highlight then action',not target['menu'] and target['url'].endswith('#'+other.split('#')[1]) and (mode.one or first['lit']==[other] and first['url']==deep['url']),str([first,target]))
    f.nav('back');restored=f.state();expected=before.copy();expected['lit']=[other]
    bad=[] if same(restored,expected) else [(restored,expected)]
    if not mode.one:
        f.nav('back')
        if not same(f.state(),original):bad.append((f.state(),original))
    f.nav('back')
    if not same(f.state(),deep):bad.append((f.state(),deep))
    chk(dev,'C Назад: contents (row lit) → earlier real action → closed on the deep-linked subsection',not bad,str(bad[:2]))
    chk(dev,'C Back presses equal the model count',(2 if mode.one else 3)==target['pushes']-deep['pushes']);pg.close()
    # D: rapid taps are two functions by default, highlight+function in legacy.
    pg,f=fresh('introduction/');f.contents();d0=f.state()
    def double(loc):
        loc.scroll_into_view_if_needed();box=loc.bounding_box();x=box['x']+min(60,box['width']/2);y=box['y']+box['height']/2
        if mode.one and loc.get_attribute('data-toc-group'):
            tap=loc.tap if o.get('has_touch') else loc.click;tap();tap()
        else:
            tap=pg.touchscreen.tap if o.get('has_touch') else pg.mouse.click;tap(x,y);tap(x,y)
        pg.wait_for_timeout(450)
    double(f.group('temple-worship'));d1=f.state()
    chk(dev,'D double tap on a group: default expands then collapses / legacy highlights then expands',('temple-worship' in d1['open'])!=mode.one and d1['lit']==['grp:temple-worship'] and d1['url']==d0['url'] and d1['pushes']==d0['pushes']+2,str(d1))
    f.nav('back');previous=f.state()
    chk(dev,'D Назад: preceding action / legacy highlight step',previous['lit']==['grp:temple-worship'] and ('temple-worship' in previous['open'])==mode.one and previous['url']==d0['url'],str(previous))
    f.nav('back');chk(dev,'D Назад: the step before the first tap',same(f.state(),d0))
    f.nav('forward');f.nav('forward')
    if mode.one:f.tap(f.group('temple-worship'))
    before_ch=f.state();f.activate(f.chapter('daily-deity-schedule'));d2=f.state();sub='sub:daily-deity-schedule#morning-bhoga-arati';double(f.row(sub));opened=f.state()
    chk(dev,'D double tap on a subsection: opens it',not opened['menu'] and opened['url'].endswith('#morning-bhoga-arati'),str(opened))
    chk(dev,'D rapid subsection taps push only the selected model actions',opened['pushes']-d2['pushes']==(1 if mode.one else 2),str(opened))
    f.nav('back');state=f.state();chk(dev,'D Назад from rapid subsection taps: contents with that row lit',state['menu'] and state['lit']==[sub] and state['url']==d2['url'],str(state))
    f.nav('back');expected=before_ch.copy() if mode.one else d2.copy()
    if mode.one:expected['lit']=['sec:daily-deity-schedule']
    chk(dev,'D Назад again: the preceding real action / before the legacy highlight tap',same(f.state(),expected),str([f.state(),expected]))
    history_roundtrip(browser,o,mode,lambda n,ok,i='':chk(dev,n,ok,i),BASE)
    chk(dev,'no page errors',not errors,str(errors[:3]));context.close();browser.close()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        print(f"== {dev}", flush=True)
        try:
            qa.run_toc_modes(lambda mode:run(p,dev,eng,o,mode),on_error=lambda e:chk(dev,"suite crashed",False,repr(e)[:300]))
        except Exception as e:  # a crash is a failure, with its message
            chk(dev, "suite crashed", False, repr(e)[:300])
print(f"s25: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
