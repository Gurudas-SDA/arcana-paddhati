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
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {info}", flush=True)


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
    if part not in pg.url and not pg.evaluate("!!document.querySelector('.mobile-menu[data-leaving]')"):
        tap(pg, row(pg, text))
    wait_url(pg, part)


def wait_url(pg, part, t=10):
    t0 = time.time()
    while part not in pg.url and time.time() - t0 < t:
        pg.wait_for_timeout(100)


OPEN_PANELS = "document.querySelectorAll('.app-main .verse-panel:not([hidden])').length"
BREAKS = r"""(()=>{const bad=[];for(const d of document.querySelectorAll('.app-main .verse-text p')){
const w=document.createTreeWalker(d,NodeFilter.SHOW_TEXT);let n;let prevTop=null;let prevCh='';
while(n=w.nextNode()){const t=n.textContent;prevTop=null;for(let i=0;i<t.length;i++){const r=document.createRange();r.setStart(n,i);r.setEnd(n,i+1);
const rc=r.getClientRects()[0];if(!rc||t[i]==='\n')continue;
if(prevTop!==null&&rc.top>prevTop+3&&!/[ \n-]/.test(t.slice(Math.max(0,i-2),i+1)))bad.push(t.slice(Math.max(0,i-12),i+8));
prevTop=rc.top;prevCh=t[i]}}
prevTop=null}return bad.slice(0,5)})()"""

L = BASE + "/ru-iast/"
with sync_playwright() as p:
    for dev, eng, kw in DEV:
        if ONLY and dev not in ONLY.split(','):
            continue
        print('==', dev, flush=True)
        b = getattr(p, eng).launch()
        c = b.new_context(locale='ru-RU', **kw)
        MOB['m'] = kw.get('has_touch', False)
        pg = c.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(L, wait_until='networkidle')
        pg.wait_for_timeout(800)
        # 3: contents order
        open_contents(pg)
        order = pg.evaluate("[...document.querySelectorAll('aside nav > ul > li')].map(l=>l.innerText.trim().split('\\n')[0].trim()).filter(Boolean).slice(0,4)")
        # v7.4 (Satkirti 06.10 / 07.10.2026): the parampara stands between the cover and the Maṅgalācaraṇa
        ck(dev, '3 contents: Обложка → Гуру-парампара → Мангалачарана → ВВЕДЕНИЕ', order[:4] == ['Обложка', 'Гуру-парампара', 'Мангалачарана', 'ВВЕДЕНИЕ'], order)
        # 1: nav bar on screen and on top while the menu is open
        fb = pg.locator('[data-reader-nav=forward]').bounding_box()
        vh = pg.viewport_size['height']
        hit = pg.evaluate(f"(()=>{{const e=document.elementFromPoint({fb['x'] + fb['width'] / 2},{fb['y'] + fb['height'] / 2});return !!(e&&e.closest('[data-reader-nav=forward]'))}})()")
        ck(dev, '1/2 Вперёд on screen and on top with menu open', fb['y'] + fb['height'] <= vh and hit, fb)
        go_row(pg, 'Мангалачарана', 'mangalacarana')
        pg.wait_for_timeout(1200)
        h1 = pg.evaluate("document.querySelector('.app-main h1').innerText.trim()")
        h2 = pg.evaluate("document.querySelectorAll('.app-main article h2, .app-main article h3').length")
        sub = pg.evaluate("!!document.querySelector('.app-main header p')")
        orn = pg.evaluate("document.querySelectorAll('.app-main .verse-ornament').length")
        verses = pg.evaluate("document.querySelectorAll('.app-main .verse-chips').length")
        wbw = pg.evaluate("[...document.querySelectorAll('.app-main .verse-chips')].filter(c=>/пословно/i.test(c.innerText)).length")
        ck(dev, '3 Мангалачарана: title only, no headings, ornaments, 30 verses all with пословно',
           h1 == 'Мангалачарана' and h2 == 0 and not sub and orn == 20 and verses == 30 and wbw == 30, (h1, h2, sub, orn, verses, wbw))
        ck(dev, '6d «Молитва Шри Радхе-Говинде» gone', 'Радхе-Говинде' not in pg.evaluate("document.querySelector('.app-main').innerText"))
        nxt = pg.evaluate("(()=>{const a=document.querySelector('.chapter-next');return a?a.innerText.replace(/\\s+/g,' '):''})()")
        ck(dev, '3 «След. глава ›» after Мангалачарана = Введение', 'ВВЕДЕНИЕ' in nxt.upper(), nxt)
        # 8: verse panels closed by default; no carry-over
        ck(dev, '8 all verse panels closed on open', pg.evaluate(OPEN_PANELS) == 0)
        tap(pg, pg.locator('.app-main .verse-chip').nth(1))
        pg.wait_for_timeout(400)
        ck(dev, '8 chip opens its own panel', pg.evaluate(OPEN_PANELS) == 1)
        # 6a
        pg.goto(L + 'caturmasya-purusottama-masa/', wait_until='networkidle')
        pg.wait_for_timeout(600)
        raw = pg.evaluate("document.querySelector('.app-main').textContent")
        ck(dev, '6a no ⟦⟧ on screen, āmiṣa translated', '⟦' not in raw and '⟧' not in raw and 'от мясной пищи' in raw)
        # 9: status line one line
        for sec in ['daily-deity-schedule', 'vigraha-tattva', 'gaudiya-emblem']:
            pg.goto(L + sec + '/', wait_until='networkidle')
            pg.wait_for_timeout(600)
            pg.locator('.app-main').evaluate("e=>e.scrollTop=e.scrollHeight*0.82")
            pg.wait_for_timeout(400)
            reveal(pg)
            pg.wait_for_timeout(300)
            lab = pg.evaluate("(()=>{const p=document.querySelector('.reader-progress-label');const r=p.getBoundingClientRect();return {t:p.innerText,h:Math.round(r.height),sw:p.scrollWidth,cw:p.clientWidth}})()")
            ck(dev, f'9 status one line, not cut ({sec})', lab['h'] <= 20 and lab['sw'] <= lab['cw'] + 1 and '…' not in lab['t'], lab)
        # 10: Sanskrit breaks only at a space or a hyphen
        for sec in ['mangalacarana', 'daily-deity-schedule', 'offering-bhoga']:
            pg.goto(L + sec + '/', wait_until='networkidle')
            pg.wait_for_timeout(500)
            bad = pg.evaluate(BREAKS)
            ck(dev, f'10 Sanskrit breaks only at space/hyphen ({sec})', not bad, bad)
        # 11: subsection heading at top 3 s after a jump (direct load with #hash)
        worst = []
        for sec in ['gaudiya-emblem', 'vigraha-tattva', 'daily-deity-schedule']:
            pg.goto(L + sec + '/', wait_until='networkidle')
            ids = pg.evaluate("[...document.querySelectorAll('.app-main section[data-subsection]')].map(s=>s.id)")
            for sid in ids:
                pg.goto(L + 'introduction/', wait_until='domcontentloaded')
                pg.goto(L + sec + '/#' + sid)
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
                    tap(pg, row(pg, 'ВВЕДЕНИЕ'))
                    pg.wait_for_timeout(500)
                tap(pg, row(pg, 'Эмблема'))
                pg.wait_for_timeout(600)
            r2 = row(pg, 'Святое имя')
            tap(pg, r2)
            pg.wait_for_timeout(200)
            if 'gaudiya-emblem' not in pg.url and pg.locator('.mobile-menu').count() and not pg.evaluate("!!document.querySelector('.mobile-menu[data-leaving]')"):
                tap(pg, row(pg, 'Святое имя'))  # two-tap contents
            frames = []
            t0 = time.time()
            while time.time() - t0 < 4:
                frames.append(pg.evaluate("[location.pathname, !!document.querySelector('.mobile-menu'), (document.querySelector('.app-main h1')||{innerText:'(cover)'}).innerText.slice(0,20)]"))
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
        fig = pg.locator('.app-main .hs-figure').first
        fig.evaluate("e=>e.scrollIntoView({block:'end'})")
        pg.wait_for_timeout(700)
        opened = []
        for n in ['1', '5', '9']:
            h = pg.locator(f'.app-main .hs-figure .hs-hit[aria-label="{n}"] ellipse').first
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
        fig = pg.locator('.app-main .hs-figure').first
        fig.evaluate("e=>e.scrollIntoView({block:'center'})")
        pg.wait_for_timeout(600)
        bb = fig.bounding_box()
        before = pg.evaluate(BARS)
        click_xy(pg, bb['x'] + 4, bb['y'] + 4)
        pg.wait_for_timeout(700)
        ck(dev, '19 tap on the empty corner of the emblem toggles the menu', pg.evaluate(BARS) != before)
        # 14: numbers drawn on the emblem
        tags = pg.evaluate("[...document.querySelectorAll('.app-main .hs-figure .hs-tag')].map(t=>t.textContent)")
        ck(dev, '14 emblem shows numbers 1, 2.1–2.6, 10–12', sorted(tags) == sorted(['1', '2.1', '2.2', '2.3', '2.4', '2.5', '2.6', '10', '11', '12']), tags)
        # 18: Tilak / ācamana mantras have «пословно»
        pg.goto(L + 'daily-duties-brahma-muhurta/', wait_until='networkidle')
        pg.wait_for_timeout(600)
        chips = pg.locator('#applying-tilaka .mantra-chips .verse-chip')
        n = chips.count()
        ok = False
        if n:
            tap(pg, chips.first)
            pg.wait_for_timeout(400)
            ok = 'Кешаве' in pg.evaluate("[...document.querySelectorAll('#applying-tilaka .verse-panel:not([hidden])')].map(p=>p.innerText).join(' ')")
        n2 = pg.locator('#sadhararana-acamana .mantra-chips .verse-chip').count()
        ck(dev, '18 Tilak (12) + ācamana mantras have «пословно», opens «… keśavāya — Кешаве»', n >= 12 and n2 >= 24 and ok, (n, n2, ok))
        # 17: Back retraces without a repeated step
        pg.goto(L + 'daily-duties-brahma-muhurta/', wait_until='networkidle')
        pg.wait_for_timeout(600)
        open_contents(pg)
        LIT = "(()=>{const e=document.querySelector('aside nav [data-toc-lit]');const ex=[...document.querySelectorAll('aside nav [aria-expanded=true]')].map(x=>x.innerText.trim().slice(0,12));return e?e.innerText.trim().slice(0,20)+' | '+[...new Set(ex)].join(','):'-'})()"
        fwd = [pg.evaluate(LIT)]
        intro = pg.locator('aside nav [data-toc-group=introduction]')
        tap(pg, intro); pg.wait_for_timeout(700); fwd.append(pg.evaluate(LIT))
        vig = pg.locator('aside nav [data-toc-chapter=vigraha-tattva]')
        tap(pg, vig); pg.wait_for_timeout(700); fwd.append(pg.evaluate(LIT))
        tap(pg, vig); wait_url(pg, 'vigraha-tattva'); pg.wait_for_timeout(1200)
        back = []
        for _ in range(4):
            reveal(pg) if not pg.locator('.mobile-menu').count() else None
            tap(pg, pg.locator('[data-reader-nav=back]'))
            pg.wait_for_timeout(1100)
            back.append(pg.evaluate(LIT) if pg.locator('.mobile-menu').count() else 'page:' + pg.url.split('arcana-paddhati')[-1])
        dup = [i for i in range(1, len(back)) if back[i] == back[i - 1]]
        ck(dev, '17 Back mirrors the forward steps, no repeated step', not dup and back[:2] == fwd[::-1][:2] and back[-1].startswith('page:'), {'fwd': fwd, 'back': back})
        ck(dev, 'no page errors', not errs, errs[:2])
        b.close()
print(f"\n{sum(res)}/{len(res)} passed")
