"""Reader v7.1 regression: items 1-11 (Satkirti 06.10). usage: python v71_test.py <base>"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402  (device profiles, repo paths)
import sys, os, time
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip('/')
IOS = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
IPAD = IOS.replace("iPhone; CPU iPhone OS", "iPad; CPU OS")
DEV = qa.devices(["pixel7", "s23fe", "iphone14", "ipad-portrait", "ipad-landscape", "desktop", "mac-safari"])
ONLY = None  # device filter: QA_DEVICES (qa/lib/qa.py)
res = []
MOB = {}


def ck(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} [toc={qa.TOC_MODE_NAME}] {info}", flush=True)


def click_xy(pg, x, y):
    if MOB['m']:
        pg.touchscreen.tap(x, y)
    else:
        pg.mouse.click(x, y)


def tap(pg, loc):
    loc.evaluate("e=>e.scrollIntoView({block:'center'})")
    pg.wait_for_timeout(250)
    b = loc.bounding_box()
    click_xy(pg, b['x'] + min(b['width'] / 2, 60), b['y'] + b['height'] / 2)


def reveal(pg):
    if pg.evaluate("document.querySelector('[data-reader-action=contents]').getBoundingClientRect().top") < 0:
        click_xy(pg, 8, pg.viewport_size['height'] // 2)
        pg.wait_for_timeout(600)


def open_contents(pg):
    reveal(pg)
    tap(pg, pg.locator('[data-reader-action=contents]'))
    pg.wait_for_timeout(800)


def row(pg, text):
    loc = pg.locator('aside nav').locator('a,button').filter(has_text=text)
    for i in range(loc.count()):
        if loc.nth(i).is_visible():
            return loc.nth(i)
    raise Exception('row ' + text)


def go_row(pg, text, part):
    tap(pg, row(pg, text))
    pg.wait_for_timeout(500)
    if part not in pg.url and not pg.evaluate("!!document.querySelector('.mobile-menu[data-open][data-leaving]')"):
        tap(pg, row(pg, text))
    wait_url(pg, part)


def wait_url(pg, part, t=10):
    t0 = time.time()
    while part not in pg.url and time.time() - t0 < t:
        pg.wait_for_timeout(100)


OPEN_PANELS = "root => root.querySelectorAll('.verse-panel:not([hidden])').length"
BREAKS = r"""root=>{const bad=[];for(const d of root.querySelectorAll('.verse-text p')){
const w=document.createTreeWalker(d,NodeFilter.SHOW_TEXT);let n;let prevTop=null;let prevCh='';
while(n=w.nextNode()){const t=n.textContent;prevTop=null;for(let i=0;i<t.length;i++){const r=document.createRange();r.setStart(n,i);r.setEnd(n,i+1);
const rc=r.getClientRects()[0];if(!rc||t[i]==='\n')continue;
if(prevTop!==null&&rc.top>prevTop+3&&!/[ \n-]/.test(t.slice(Math.max(0,i-2),i+1)))bad.push(t.slice(Math.max(0,i-12),i+8));
prevTop=rc.top;prevCh=t[i]}}
prevTop=null}return bad.slice(0,5)}"""

L = BASE + "/ru-iast/"
def run(p,dev,eng,kw,mode):
    from toc import Contents, STATE, history_roundtrip, marks_place
    print('==',dev,mode.name,flush=True)
    b = getattr(p, eng).launch()
    c = b.new_context(locale='ru-RU', service_workers='block', **kw)
    MOB['m'] = kw.get('has_touch', False)
    pg = c.new_page()
    flow = Contents(pg,mode,MOB['m'])
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    mode.start(pg,L)
    pg.wait_for_timeout(800)
    # 3: contents order
    open_contents(pg)
    order = pg.evaluate("[...document.querySelectorAll('aside nav [data-toc-cover], aside nav .toc-scroll > ul > li')].map(l=>l.innerText.trim().split('\\n')[0].trim()).filter(Boolean).slice(0,4)")
    # v7.4 (Satkirti 06.10 / 07.10.2026): the parampara stands between the cover and the Maṅgalācaraṇa
    ck(dev, '3 contents: Обложка → Гуру-парампара → Мангалачарана → ВВЕДЕНИЕ', order[:4] == ['Обложка', 'Гуру-парампара', 'Мангалачарана', 'ВВЕДЕНИЕ'], order)
    # 1: nav bar on screen and on top while the menu is open
    fb = pg.locator('[data-reader-nav=forward]').bounding_box()
    vh = pg.viewport_size['height']
    hit = pg.evaluate(f"(()=>{{const e=document.elementFromPoint({fb['x'] + fb['width'] / 2},{fb['y'] + fb['height'] / 2});return !!(e&&e.closest('[data-reader-nav=forward]'))}})()")
    ck(dev, '1/2 Вперёд on screen and on top with menu open', fb['y'] + fb['height'] <= vh and hit, fb)
    go_row(pg, 'Мангалачарана', 'mangalacarana')
    pg.wait_for_timeout(1200)
    h1 = qa.reading_eval(pg, "root => root.querySelector('h1').innerText.trim()")
    h2 = qa.reading_eval(pg, "root => root.querySelectorAll('article h2, article h3').length")
    sub = qa.reading_eval(pg, "root => !!root.querySelector('header p')")
    orn = qa.reading_eval(pg, "root => root.querySelectorAll('.verse-ornament').length")
    verses = qa.reading_eval(pg, "root => root.querySelectorAll('.verse-chips').length")
    wbw = qa.reading_eval(pg, "root => [...root.querySelectorAll('.verse-chips')].filter(c=>/пословно/i.test(c.innerText)).length")
    ck(dev, '3 Мангалачарана: title only, no headings, ornaments, 30 verses all with пословно',
       h1 == 'Мангалачарана' and h2 == 0 and not sub and orn == 20 and verses == 30 and wbw == 30, (h1, h2, sub, orn, verses, wbw))
    ck(dev, '6d «Молитва Шри Радхе-Говинде» gone', 'Радхе-Говинде' not in qa.reading_eval(pg, "root => root.innerText"))
    nxt = qa.reading_eval(pg, "root=>{const a=root.querySelector('.chapter-next');return a?a.innerText.replace(/\\s+/g,' '):''}")
    ck(dev, '3 «След. глава ›» after Мангалачарана = Введение', 'ВВЕДЕНИЕ' in nxt.upper(), nxt)
    # 8: verse panels closed by default; no carry-over
    # Centering the first chip can move the reading line into Parampara on a
    # tall viewport. Keep the action and its assertion in the chapter opened
    # above, rather than re-resolving [data-reader-current] after scrolling.
    verse_root = pg.locator('.app-main [data-book-section="mangalacarana"], .app-main:not(:has([data-continuous-book]))')
    ck(dev, '8 all verse panels closed on open', verse_root.locator('.verse-panel:not([hidden])').count() == 0)
    tap(pg, verse_root.locator('.verse-chip').nth(1))
    pg.wait_for_timeout(400)
    ck(dev, '8 chip opens its own panel', verse_root.locator('.verse-panel:not([hidden])').count() == 1)
    # 6a
    pg.goto(L + 'caturmasya-purusottama-masa/', wait_until='networkidle')
    pg.wait_for_timeout(600)
    raw = qa.reading_eval(pg, "root => root.textContent")
    ck(dev, '6a no ⟦⟧ on screen, āmiṣa translated', '⟦' not in raw and '⟧' not in raw and 'от мясной пищи' in raw)
    # 9: status line one line
    for sec in ['daily-deity-schedule', 'vigraha-tattva', 'gaudiya-emblem']:
        pg.goto(L + sec + '/', wait_until='networkidle')
        pg.wait_for_timeout(600)
        qa.scroll_chapter(pg, .82)
        pg.wait_for_timeout(400)
        reveal(pg)
        pg.wait_for_timeout(300)
        lab = pg.evaluate("""() => {const p=document.querySelector('.reader-progress-label'),cs=getComputedStyle(p),r=p.getBoundingClientRect();
          const clone=p.cloneNode(true);Object.assign(clone.style,{position:'fixed',left:'-2000px',top:'0',width:'max-content',maxWidth:'none',flex:'none',whiteSpace:'nowrap',font:cs.font,visibility:'hidden'});
          document.body.appendChild(clone);const natural=clone.getBoundingClientRect().width;clone.remove();
          return {t:p.innerText,h:Math.round(r.height),sw:p.scrollWidth,cw:p.clientWidth,natural,sh:p.scrollHeight,ch:p.clientHeight};}""")
        fits=lab['natural'] <= lab['cw'] + .5
        ck(dev, f'9 status one line when it fits, wraps intact when needed ({sec})', (lab['h'] <= 20 if fits else lab['h'] > 20) and lab['sw'] <= lab['cw'] + 1 and lab['sh'] <= lab['ch'] + 1 and '…' not in lab['t'], lab)
    # 10: Sanskrit breaks only at a space or a hyphen
    for sec in ['mangalacarana', 'daily-deity-schedule', 'offering-bhoga']:
        pg.goto(L + sec + '/', wait_until='networkidle')
        pg.wait_for_timeout(500)
        bad = qa.reading_eval(pg, BREAKS)
        ck(dev, f'10 Sanskrit breaks only at space/hyphen ({sec})', not bad, bad)
    # 11: subsection heading at top 3 s after a jump (direct load with #hash)
    worst = []
    for sec in ['gaudiya-emblem', 'vigraha-tattva', 'daily-deity-schedule']:
        pg.goto(L + sec + '/', wait_until='networkidle')
        ids = pg.evaluate(f"[...{qa.READING_ROOT_JS}.querySelectorAll('section[data-subsection]')].map(s=>s.id)")
        for sid in ids:
            pg.goto(L + 'introduction/', wait_until='domcontentloaded')
            qa.wait_for_book_chapter(pg, 'introduction')
            pg.goto(L + sec + '/#' + sid, wait_until='domcontentloaded')
            qa.wait_for_book_chapter(pg, sec)
            pg.wait_for_timeout(3000)
            top = pg.evaluate(f"(()=>{{const e=document.getElementById('{sid}');const m=document.querySelector('.app-main');return Math.round(e.getBoundingClientRect().top-m.getBoundingClientRect().top)}})()")
            atmax = pg.evaluate("(()=>{const m=document.querySelector('.app-main');return m.scrollTop>=m.scrollHeight-m.clientHeight-2})()")
            if not (-2 <= top <= 80) and not (atmax and top > 0):
                worst.append((sec, sid, top))
    ck(dev, '11 heading at top after 3 s (all subsections, direct load)', not worst, worst[:4])
    # 11 + 5: from the contents (client navigation): Эмблема → «Святое имя …»
    pg.goto(L + 'vigraha-tattva/', wait_until='networkidle')
    pg.wait_for_timeout(600)
    open_contents(pg)
    try:
        if not pg.evaluate("[...document.querySelectorAll('aside nav [aria-expanded=true]')].some(e=>/Эмблема/.test(e.innerText))"):
            if not pg.evaluate("[...document.querySelectorAll('aside nav [aria-expanded=true]')].some(e=>/ВВЕДЕНИЕ/.test(e.innerText))"):
                flow.activate(flow.group('introduction'))
            flow.activate(flow.chapter('gaudiya-emblem'))
        r2 = row(pg, 'Святое имя')
        tap(pg, r2)
        pg.wait_for_timeout(200)
        if 'gaudiya-emblem' not in pg.url and pg.locator('.mobile-menu[data-open]').count() and not pg.evaluate("!!document.querySelector('.mobile-menu[data-open][data-leaving]')"):
            tap(pg, row(pg, 'Святое имя'))  # two-tap contents
        frames = []
        t0 = time.time()
        while time.time() - t0 < 4:
            frames.append(qa.reading_eval(pg,"root=>[location.pathname,!!document.querySelector('.mobile-menu[data-open]'),(root.querySelector('h1')||{innerText:'(cover)'}).innerText.slice(0,20)]"))
            pg.wait_for_timeout(80)
        flash = [f for f in frames if not f[1] and 'gaudiya-emblem' not in f[0]]
        shown = next((i for i, f in enumerate(frames) if 'gaudiya-emblem' in f[0] and not f[1]), None)
        ck(dev, '5 no old page between menu and target', not flash and shown is not None, (flash[:2], 'target after ~%s ms' % (None if shown is None else shown * 100)))
        pg.wait_for_timeout(2500)
        sid = pg.evaluate("decodeURIComponent(location.hash.slice(1))")
        top = pg.evaluate(f"(()=>{{const e=document.getElementById('{sid}');const m=document.querySelector('.app-main');return e?Math.round(e.getBoundingClientRect().top-m.getBoundingClientRect().top):null}})()")
        ck(dev, '11 contents → «Святое имя» heading at top', top is not None and -2 <= top <= 80, (sid, top))
    except Exception as e:
        ck(dev, '11/5 contents path', False, str(e)[:160])
    BARS = "document.documentElement.hasAttribute('data-reader-bars')"
    # 13: tap a picture part whose row is above -> programmatic scroll up, menu stays hidden
    pg.goto(L + 'daily-duties-brahma-muhurta/', wait_until='networkidle')
    pg.wait_for_timeout(800)
    fig = qa.reading_locator(pg, '.hs-figure').first
    fig.evaluate("e=>e.scrollIntoView({block:'end'})")
    pg.wait_for_timeout(700)
    opened = []
    for n in ['1', '5', '9']:
        h = qa.reading_locator(pg, f'.hs-figure .hs-hit[aria-label="{n}"] ellipse').first
        if not h.count():
            continue
        bb = h.bounding_box()
        if not bb:
            continue
        fig.evaluate("e=>e.scrollIntoView({block:'end'})")
        pg.wait_for_timeout(500)
        bb = h.bounding_box()
        click_xy(pg, bb['x'] + bb['width'] / 2, bb['y'] + bb['height'] / 2)
        pg.wait_for_timeout(1500)
        if pg.evaluate(BARS):
            opened.append(n)
            click_xy(pg, 8, pg.viewport_size['height'] // 2)
            pg.wait_for_timeout(500)
    ck(dev, '13 picture part tap (scroll to row) does not open the menu (Tilak)', not opened, opened)
    # 19: empty corner of the emblem picture acts as empty page
    pg.goto(L + 'gaudiya-emblem/', wait_until='networkidle')
    pg.wait_for_timeout(800)
    fig = qa.reading_locator(pg, '.hs-figure').first
    fig.evaluate("e=>e.scrollIntoView({block:'center'})")
    pg.wait_for_timeout(600)
    bb = fig.bounding_box()
    before = pg.evaluate(BARS)
    click_xy(pg, bb['x'] + 4, bb['y'] + 4)
    pg.wait_for_timeout(700)
    ck(dev, '19 tap on the empty corner of the emblem toggles the menu', pg.evaluate(BARS) != before)
    # 14: numbers drawn on the emblem
    tags = qa.reading_eval(pg, "root => [...root.querySelectorAll('.hs-figure .hs-tag')].map(t=>t.textContent)")
    # (20.10.2026, Vraja Lila msg 5429/5432: the app draws ALL numbers — the picture has none burned in; s54)
    ck(dev, '14 emblem shows numbers 1–12, 2.1–2.6', sorted(tags) == sorted(['1', '2', '2.1', '2.2', '2.3', '2.4', '2.5', '2.6', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']), tags)
    # 18 (v7.8, Satkirti 07.10.2026 вечер): the short Tilak / ācamana mantras («oṁ keśavāya namaḥ») have
    # NO «пословно» any more; the mantras themselves are all still there
    pg.goto(L + 'daily-duties-brahma-muhurta/', wait_until='networkidle')
    pg.wait_for_timeout(600)
    n = pg.locator('#applying-tilaka .mantra-chips .verse-chip').count()
    # (the section's longer verse mantras keep their «пословно» — s26 item 7 checks every short one)
    n2 = pg.locator('#sadhararana-acamana .mantra-chips .verse-chip').count()
    m1 = pg.evaluate("[...document.querySelectorAll('#applying-tilaka .hs-row .sa-inline')].filter(e=>/namaḥ/.test(e.textContent)).length")
    m2 = pg.evaluate("[...document.querySelectorAll('#sadhararana-acamana .sanskrit')].filter(e=>/namaḥ/.test(e.textContent)).length")
    ok = m1 >= 12 and m2 >= 24
    ck(dev, '18 Tilak (12) + ācamana short mantras shown WITHOUT «пословно» (v7.8)', n == 0 and n2 == 0 and ok, (n, n2, m1, m2))
    # 17: preserve the full path; the mark is derived from the reading place.
    pg.goto(L+'daily-duties-brahma-muhurta/',wait_until='networkidle');pg.wait_for_timeout(500)
    states=[flow.state()];flow.contents();states.append(flow.state())
    for kind,id in [('group','introduction'),('chapter','vigraha-tattva')]:
        loc=flow.group(id) if kind=='group' else flow.chapter(id)
        flow.tap(loc);states.append(flow.state())
        if not mode.one:flow.tap(loc);states.append(flow.state())
    sub=pg.locator('#toc-ch-vigraha-tattva a').first;rid=sub.get_attribute('data-toc-row')
    if not mode.one:flow.tap(sub);states.append(flow.state())
    flow.tap(sub,wait=400);states.append(flow.state());bad=[];back_count=0
    for want in reversed(states[:-1]):
        flow.nav('back');back_count+=1;got=flow.state()
        if any(got[k]!=want[k] for k in ['url','menu','open']) or not marks_place(got):bad.append((got,want))
    ck(dev,'17 Back mirrors the forward steps, no repeated step',not bad and not flow.state()['menu'],bad[:2])
    ck(dev,'17 Back counts exactly the mode actions',back_count==(4 if mode.one else 7),back_count)
    bad=[];forward_count=0
    for want in states[1:]:
        flow.nav('forward');forward_count+=1;got=flow.state()
        if any(got[k]!=want[k] for k in ['url','menu','open']) or not marks_place(got):bad.append((got,want))
    ck(dev,'17 Forward mirrors every URL and open list, marking the reading place',not bad and forward_count==(4 if mode.one else 7),bad[:2])
    history_roundtrip(b,kw,mode,lambda n,ok,i='':ck(dev,n,ok,i),BASE)
    # WebKit reports a link prefetch cut off by the test's own goto() as «… due to access control checks»
    # (same-origin page URL; the test's doing, not the reader's — as in s07/s22, A65 gate 10.10)
    host = BASE.split('//', 1)[-1].split('/', 1)[0]
    errs = [e for e in errs if not (e.rstrip().endswith('due to access control checks.') and host in e)]
    ck(dev, 'no page errors', not errs, errs[:2])
    b.close()

with sync_playwright() as p:
    for dev,eng,kw in DEV:
        qa.run_toc_modes(lambda mode:run(p,dev,eng,kw,mode),on_error=lambda e:ck(dev,'EXCEPTION',False,str(e)[:900]))

print(f"\n{sum(res)}/{len(res)} passed")
