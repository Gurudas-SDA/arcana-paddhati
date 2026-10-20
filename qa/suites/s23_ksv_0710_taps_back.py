"""Contents and history: one-tap actions (Satkirti 13.10.2026).
  1 Parampara portrait taps toggle the bars at every tested point.
  2 One cover tap opens home; reopening Contents shows the base view.
  3 Back / Forward restore every URL and open list, marking the reading place.
  4 Every group and chapter disclosure reacts over its full row on one tap;
    chapter opening navigates to its top, a second tap collapses its list.
Leaf rows: s24; reload / deep links / rapid taps: s25.
Devices: phones, tablets, computers; QA_DEVICES selects profiles.
usage: python3 s23_ksv_0710_taps_back.py <base-url> [shots-dir]"""
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

STATE = """() => { const nav = document.querySelector('.mobile-menu[data-open] nav');
  const r = {url: location.pathname + location.hash, menu: !!nav, lit: [], open: []};
  if (nav) {
    r.lit = [...nav.querySelectorAll('[data-toc-lit]')].map(e => e.hasAttribute('data-toc-cover') ? 'cover' : (e.getAttribute('data-toc-group') || e.getAttribute('data-toc-chapter') || e.getAttribute('href') || e.textContent.trim().slice(0, 30)));
    r.open = [...nav.querySelectorAll('[aria-expanded=true][data-toc-chapter],[aria-expanded=true][data-toc-group]')].map(e => e.getAttribute('data-toc-chapter') || e.getAttribute('data-toc-group')).sort();
  }
  return r; }"""


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} [toc={qa.TOC_MODE_NAME}] {'' if ok else info}", flush=True)


def run(p, dev, eng, o, mode):
    from toc import Contents, history_roundtrip, marks_place, marks_chapter_top
    b = getattr(p, eng).launch()
    c = b.new_context(locale="ru-RU", service_workers="block", **o)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    pg = c.new_page()
    touch = o.get("has_touch", False)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    flow=Contents(pg,mode,touch)

    def tap_xy(x, y):
        (pg.touchscreen.tap if touch else pg.mouse.click)(x, y)

    def act(loc, ms=550, force=False):
        loc.scroll_into_view_if_needed()
        loc.tap(force=force) if touch else loc.click(force=force)
        pg.wait_for_timeout(ms)

    shown = lambda: pg.locator(".reader-chrome[data-shown]").count() == 1
    menu = lambda: pg.locator(".mobile-menu[data-open]").count() == 1
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

    # V17: the bottom bar's buttons are the previous / next chapter; history steps = system Back / Forward
    def back():
        pg.go_back(); pg.wait_for_timeout(1100)

    def forward():
        pg.go_forward(); pg.wait_for_timeout(1100)

    # ---------- 1: tap on every parampara portrait toggles the bars ----------
    mode.start(pg,f"{BASE}/{L}/parampara/");pg.wait_for_timeout(700)
    qa.load_portraits(pg)   # 19.10.2026: portraits 2–9 load lazily, as the reader reaches them
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

    # 4: every disclosure row uses the chosen model across its full band.
    pg.close();pg=c.new_page();pg.on('pageerror',lambda e:errs.append(str(e)));flow=Contents(pg,mode,touch)
    mode.start(pg,f'{BASE}/{L}/');flow.contents()
    groups=pg.locator('.mobile-menu[data-open] [data-toc-group]').evaluate_all('es=>es.map(e=>e.dataset.tocGroup)')
    bad1,bad2,bad3=[],[],[];tested=0
    for gid in groups:
        loc=flow.group(gid);before=flow.state();rid=loc.get_attribute('data-toc-row');flow.tap(loc,right=True);first=flow.state()
        if not (first['lit']==(before['lit'] if mode.one else [rid]) and first['url']==before['url'] and (gid in first['open'])==mode.one and first['pushes']==before['pushes']+1):bad1.append((gid,first))
        flow.tap(loc,right=True);second=flow.state()
        if not ((gid in second['open'])!=mode.one and second['url']==before['url'] and second['lit']==(before['lit'] if mode.one else [rid])):bad2.append((gid,second))
        if mode.one:flow.tap(loc,right=True)
        chapters=pg.locator(f'#toc-part-{gid} [data-toc-chapter],#toc-grp-{gid} [data-toc-chapter]').evaluate_all('es=>es.map(e=>e.dataset.tocChapter)')
        for cid in chapters:
            cl=flow.chapter(cid);before=flow.state();flow.tap(cl,right=True);first=flow.state();tested+=1
            ok=(marks_chapter_top(pg,first,cid) if mode.one else first['lit']==['sec:'+cid]) and first['pushes']==before['pushes']+1
            ok=ok and (cid in first['open'] and first['url'].endswith('/'+cid+'/') and abs(pg.evaluate(qa.READING_POSITION_JS)['top'])<2 if mode.one else cid not in first['open'] and first['url']==before['url'])
            if not ok:bad1.append((cid,first))
            if mode.one and pg.locator(f'#toc-ch-{cid} a').count()<1:bad3.append((cid,'list missing'))
            flow.tap(cl,right=True);second=flow.state()
            if not ((cid in second['open'])!=mode.one and second['url']==first['url'] and second['lit']==['sec:'+cid]):bad2.append((cid,second))
            if not mode.one:flow.tap(cl,right=True)
    chk(dev,f'4 first tap follows the model — parts, Введение, every chapter ({len(groups)} groups, {tested} chapters)',tested>=15 and not bad1,str(bad1[:3]))
    chk(dev,'4 second tap: default collapses / legacy expands, highlight stays, no navigation',not bad2,str(bad2[:3]))
    chk(dev,'4 default subsection lists visible without another tap',not bad3,str(bad3[:3]))
    # 2: cover function and trace in both modes.
    goto('daily-deity-schedule/');flow.contents()
    for gid in ['introduction','festivals-vows']:
        if gid not in flow.state()['open']:flow.activate(flow.group(gid))
    before=flow.state();chk(dev,'2 setup: groups and a chapter list open',len(before['open'])>=3,str(before))
    flow.tap(pg.locator('.mobile-menu[data-open] [data-toc-cover]'),right=True,wait=350);first=flow.state()
    chk(dev,'2 first tap «Обложка»: default opens; legacy resets + highlights',not first['menu'] and first['url'].rstrip('/').endswith('/'+L) if mode.one else first['menu'] and first['open']==[] and first['lit']==['cover'] and first['url']==before['url'],str(first))
    if not mode.one:flow.tap(pg.locator('.mobile-menu[data-open] [data-toc-cover]'),wait=350)
    chk(dev,'2 action tap «Обложка» opens the cover',not flow.state()['menu'] and pg.url.rstrip('/').endswith('/'+L))
    flow.contents();state=flow.state();chk(dev,'2 contents reopened on the cover: base view, «Обложка» lit',state['open']==[] and state['lit']==['cover'],str(state))
    # 3: the original multi-chapter path, with actual action counts and exact states.
    pg.close();pg=c.new_page();flow=Contents(pg,mode,touch);pg.on('pageerror',lambda e:errs.append(str(e)));mode.start(pg,f'{BASE}/{L}/introduction/')
    states=[flow.state()];flow.contents();states.append(flow.state())
    for kind,id in [('group','temple-worship'),('chapter','daily-duties-brahma-muhurta'),('chapter','daily-deity-schedule')]:
        loc=flow.group(id) if kind=='group' else flow.chapter(id)
        flow.tap(loc,wait=250);states.append(flow.state())
        if not mode.one:flow.tap(loc,wait=250);states.append(flow.state())
    sub='sub:daily-deity-schedule#morning-bhoga-arati'
    before=flow.state()
    if not mode.one:flow.tap(flow.row(sub));states.append(flow.state())
    chk(dev,'3 forward: 2.5 selected, chapters 1 and 2 open','daily-duties-brahma-muhurta' in before['open'] and 'daily-deity-schedule' in before['open'] and flow.row(sub).is_visible())
    flow.tap(flow.row(sub),wait=350);page25=flow.state();states.append(page25)
    chk(dev,'3 action tap opens 2.5',not page25['menu'] and page25['url'].endswith('/daily-deity-schedule/#morning-bhoga-arati'))
    flow.contents();flow.nav('back');chk(dev,'3 Назад 1: contents closed, back on 2.5',not flow.state()['menu'] and flow.state()['url']==page25['url'])
    bad=[]
    for i,want in enumerate(reversed(states[1:-1])):
        flow.nav('back',native=i%2==1);got=flow.state()
        if any(got[k]!=want[k] for k in ['url','menu','open']) or not marks_place(got):bad.append((got,want))
    chk(dev,'3 every further Назад = the preceding action (same URL + open lists, reading place marked)',not bad,str(bad[:2]))
    flow.nav('back');got=flow.state();chk(dev,'3 last Назад closes the contents (the page where we started)',not got['menu'] and got['url']==states[0]['url'])
    bad=[]
    for want in states[1:]:
        flow.nav('forward');got=flow.state()
        if any(got[k]!=want[k] for k in ['url','menu','open']) or not marks_place(got):bad.append((got,want))
    chk(dev,'3 «Вперёд» replays the same steps (every URL and open list, reading place marked)',not bad,str(bad[:2]))
    chk(dev,'3 path has only its real actions or legacy taps',len(states)-1==(5 if mode.one else 9))
    history_roundtrip(b,o,mode,lambda n,ok,i='':chk(dev,n,ok,i),BASE)
    chk(dev, "no page errors", not errs, str(errs[:3]))
    b.close()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        print(f"== {dev}", flush=True)
        try:
            qa.run_toc_modes(lambda mode:run(p,dev,eng,o,mode),on_error=lambda e:chk(dev,"suite crashed",False,repr(e)[:300]))
        except Exception as e:  # a crash is a failure, with its message
            chk(dev, "suite crashed", False, repr(e)[:300])
print(f"s23: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
