"""SW v6 (item 16): first visit -> core cached + controller within 90 s -> offline every ru-iast
chapter opens (direct + in-app); background fill -> transcripts + other languages offline.
usage: python s20_offline.py <base> [chromium|webkit]
  chromium: offline = context.set_offline(True) on the run_all server (<base>)
  webkit:   offline = the suite's OWN server process is killed (Playwright WebKit's
            set_offline also blocks the SW's cache answers), <base> is ignored
  QA_FAST=1: skip the background-fill part (transcripts / other languages)"""
import json, sys, time, urllib.request, subprocess, os
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402  (device profiles, repo paths)
import server as qa_server  # noqa: E402
SRV = None
if len(sys.argv) > 2 and sys.argv[2] == 'webkit':
    _port = qa_server.free_port()
    SRV = subprocess.Popen([sys.executable, os.path.join(qa.QA_DIR, 'lib', 'server.py'), str(_port)])
    time.sleep(1.5)
    sys.argv[1] = f"http://127.0.0.1:{_port}{qa.PREFIX}"
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip('/')
ENG = sys.argv[2] if len(sys.argv) > 2 else 'chromium'
UA = "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36"
man = json.load(urllib.request.urlopen(BASE + '/precache-manifest.json'))
ORIGIN = BASE.split('/arcana-paddhati')[0]
pages = [u for u, g in zip(man['urls'], man['groups']) if g == 'ru-iast' and u.endswith('/')]
trans = [u for u, g in zip(man['urls'], man['groups']) if g == 'transcripts' and u.endswith('.html')]
other = [u for u, g in zip(man['urls'], man['groups']) if g == 'de' and u.endswith('/')]
res = []


def ck(n, ok, info=''):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {ENG} {n} {info}", flush=True)


COUNT = """async()=>{let n=0,comp=false;for(const k of await caches.keys()){if(!k.startsWith('arcana-paddhati-'))continue;const c=await caches.open(k);n+=(await c.keys()).length;if(await c.match('/arcana-paddhati/__precache-complete__'))comp=true}return {n,comp}}"""

with sync_playwright() as p:
    if ENG == 'chromium':
        b = p.chromium.launch()
        c = b.new_context(viewport={'width': 412, 'height': 915}, has_touch=True, is_mobile=True, user_agent=UA, service_workers='allow')
    else:
        b = p.webkit.launch()
        c = b.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True, service_workers='allow')
    pg = c.new_page()
    progress = []
    pg.expose_function('__prog', lambda d: progress.append(d))
    pg.add_init_script("navigator.serviceWorker&&navigator.serviceWorker.addEventListener('message',e=>{if(e.data&&e.data.type==='precache-progress')window.__prog(e.data)})")
    t0 = time.time()
    pg.goto(BASE + '/ru-iast/', wait_until='load')
    try:
        pg.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller", timeout=90000)
        ck('controller (core installed) within 90 s', True, f'{time.time() - t0:.1f}s')
    except Exception:
        ck('controller (core installed) within 90 s', False, f'{time.time() - t0:.1f}s')
    st = pg.evaluate(COUNT)
    print('  cache entries at takeover:', st, flush=True)
    # offline right after takeover: every ru-iast page
    c.set_offline(True)
    if SRV:
        c.set_offline(False)
        SRV.kill(); SRV.wait(); time.sleep(0.5)
        bad = []
        for u in pages + trans[:3]:
            try:
                pg.goto(ORIGIN + u, wait_until='load', timeout=20000)
                pg.wait_for_timeout(300)
                if pg.evaluate("/не сохранена|not yet stored/.test(document.body.innerText)") or not pg.url.endswith(u):
                    bad.append(u)
            except Exception as e:
                bad.append(u + ' ' + str(e)[:80])
        ck(f'server gone right after core: {len(pages)} ru-iast pages open (transcripts not yet expected)', not [x for x in bad if 'transcripts' not in x], bad[:4])
        b.close()
        print("passed", sum(res), "/", len(res))
        sys.exit(0)
    if ENG == 'webkit':
        # Playwright WebKit (Windows) cannot navigate offline at all ("internal error",
        # also noted by the verifier): check through the worker with fetch().
        r = pg.evaluate("async(us)=>{const bad=[];for(const u of us){try{const x=await fetch(u);const t=await x.text();if(x.status!==200||!/<h1|home-cover/.test(t)||/не сохранена/.test(t))bad.push(u)}catch(e){bad.push(u+' '+e)}}return bad}", pages)
        ck(f'offline (fetch via SW) right after core: all {len(pages)} ru-iast pages', not r, r[:4])
        rsc = [u for u, g in zip(man['urls'], man['groups']) if g == 'ru-iast' and u.endswith('.txt')]
        r = pg.evaluate("async(us)=>{const bad=[];for(const u of us){try{const x=await fetch(u+'?_rsc=x',{headers:{RSC:'1'}});if(x.status!==200)bad.push(u)}catch(e){bad.push(u)}}return bad}", rsc)
        ck(f'offline (fetch via SW): all {len(rsc)} ru-iast RSC payloads', not r, r[:4])
        c.set_offline(False)
        pg.goto(BASE + '/ru-iast/', wait_until='load')
        t1 = time.time()
        while time.time() - t1 < 300:
            st = pg.evaluate(COUNT)
            if st['comp']:
                break
            pg.wait_for_timeout(5000)
        ck('background fill completes (marker)', st['comp'], f"{time.time() - t1:.0f}s entries={st['n']}")
        c.set_offline(True)
        r = pg.evaluate("async(us)=>{const bad=[];for(const u of us){try{const x=await fetch(u);if(x.status!==200)bad.push(u)}catch(e){bad.push(u)}}return bad}", trans[:15] + other[:6])
        ck('offline after fill (fetch): transcripts + German pages', not r, r[:4])
        b.close()
        print("passed", sum(res), "/", len(res))

        sys.exit(0)
    bad = []
    for u in pages:
        try:
            pg.goto(ORIGIN + u, wait_until='load', timeout=20000)
            ok = pg.evaluate("!!(document.querySelector('.app-main h1')||document.querySelector('.app-main img'))") and pg.evaluate("!/не сохранена|not yet stored/.test(document.body.innerText)")
            if not ok or not pg.url.endswith(u):
                bad.append(u)
        except Exception as e:
            bad.append(u + ' ' + str(e)[:60])
    ck(f'offline right after core: all {len(pages)} ru-iast pages open', not bad, bad[:4])
    # in-app navigation offline (contents -> chapter)
    pg.goto(ORIGIN + '/arcana-paddhati/ru-iast/daily-duties-brahma-muhurta/', wait_until='load')
    pg.wait_for_timeout(800)
    pg.evaluate("document.querySelector('.app-main').scrollTop=1e9")
    pg.wait_for_timeout(600)
    pg.evaluate("document.querySelector('[data-chapter-next]')&&document.querySelector('[data-chapter-next]').click()")
    pg.wait_for_timeout(2500)
    ck('offline in-app «След. глава»', 'daily-deity-schedule' in pg.url, pg.url[-50:])
    c.set_offline(False)
    if qa.fast():
        b.close()
        print(); print(f"{sum(res)}/{len(res)} passed")
        sys.exit(0)
    # background fill
    pg.goto(BASE + '/ru-iast/', wait_until='load')
    t1 = time.time()
    while time.time() - t1 < 300:
        st = pg.evaluate(COUNT)
        if st['comp']:
            break
        pg.wait_for_timeout(5000)
    ck('background fill completes (marker)', st['comp'], f"{time.time() - t1:.0f}s entries={st['n']} progress msgs={len(progress)} last={progress[-1] if progress else None}")
    c.set_offline(True)
    bad = []
    for u in trans[:15] + other[:6]:
        try:
            pg.goto(ORIGIN + u, wait_until='load', timeout=20000)
            if pg.evaluate("/не сохранена|not yet stored/.test(document.body.innerText)") or not pg.url.endswith(u):
                bad.append(u)
        except Exception as e:
            bad.append(u + ' ' + str(e)[:60])
    ck('offline after fill: transcripts + German pages', not bad, bad[:4])
    b.close()
print(f"\n{sum(res)}/{len(res)} passed")
