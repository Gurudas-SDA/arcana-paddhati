"""«Назад» returns to the search with the query AND the opened result in view
(Правила §6; v7.2 verifier "back_search"), system Back and the app's ‹ Назад,
alternating. Ported from v72/back_search.py.
usage: python s12_back_to_search.py <base-url>   devices: QA_DEVICES; QA_FAST=1 -> 2 rounds"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
U = BASE + "/ru-iast/"
N = 2 if qa.fast() else 6
res = []


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else info}", flush=True)


def run(p, dev, eng, o):
    b = getattr(p, eng).launch()
    c = b.new_context(locale="ru-RU", service_workers="block", **o)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    pg = c.new_page()
    touch = o.get("has_touch", False)

    def tap(x, y):
        (pg.touchscreen.tap if touch else pg.mouse.click)(x, y)

    def wait_until(js, t=15):
        t0 = time.time()
        while time.time() - t0 < t:
            if pg.evaluate(js):
                return time.time() - t0
            time.sleep(0.1)
        return None

    for it in range(N):
        how = "sys" if it % 2 == 0 else "app"
        try:
            pg.goto(U + "introduction/?i=%d" % it, wait_until="networkidle"); time.sleep(0.6)
            if pg.evaluate("!!document.querySelector('.mobile-menu')"):
                pg.keyboard.press("Escape"); time.sleep(0.5)
            pg.evaluate("document.querySelector('[data-reader-action=search]').click()"); time.sleep(0.6)
            pg.evaluate("(()=>{const i=document.querySelector('.mobile-menu input[type=search]'); i.select()})()")
            pg.keyboard.type("тилак", delay=30); pg.keyboard.press("Enter")
            wait_until("document.querySelectorAll('.mobile-menu [data-result]').length>3")
            k = 4  # the 5th result (needs scrolling of the result list on phones)
            pg.evaluate("k=>{const e=document.querySelectorAll('.mobile-menu [data-result]')[k]; e.scrollIntoView({block:'center'})}", k); time.sleep(0.3)
            r = pg.evaluate("k=>{const e=document.querySelectorAll('.mobile-menu [data-result]')[k]; const q=e.getBoundingClientRect(); return {x:q.left+30,y:q.top+Math.min(q.height/2,12),key:e.dataset.result}}", k)
            u0 = pg.url
            tap(r["x"], r["y"])
            wait_until(f"location.href!=={json.dumps(u0)} && !document.querySelector('.mobile-menu')", 10); time.sleep(1.0)
            if how == "sys":
                pg.go_back()
            else:
                for _ in range(3):
                    if pg.evaluate("document.documentElement.hasAttribute('data-reader-bars')"):
                        break
                    vp = pg.viewport_size; tap(6, vp["height"] // 2); time.sleep(0.6)
                bb = pg.evaluate("(()=>{const q=document.querySelector('[data-reader-nav=back]').getBoundingClientRect(); return [q.left+q.width/2,q.top+q.height/2]})()")
                tap(*bb)
            dt = wait_until(f"""(()=>{{const m=document.querySelector('.mobile-menu'); if(!m) return false; const i=m.querySelector('input[type=search]'); const nav=m.querySelector('nav');
               const e=[...m.querySelectorAll('[data-result]')].find(x=>x.dataset.result==={json.dumps(r['key'])}); if(!i||i.value!=='тилак'||!e) return false;
               const a=e.getBoundingClientRect(), n=nav.getBoundingClientRect(); return a.top>=n.top-1 && a.bottom<=n.bottom+1}})()""", 8)
            st = pg.evaluate("(()=>{const m=document.querySelector('.mobile-menu'); return {menu:!!m, q:m?.querySelector('input[type=search]')?.value, n:m?m.querySelectorAll('[data-result]').length:0, url:location.pathname}})()")
            chk(dev, f"6 back ({how}) -> search with the query, opened result in view (round {it + 1})", dt is not None, str(st))
        except Exception as e:
            chk(dev, f"6 back ({how}) -> search with the query (round {it + 1})", False, "ERR " + str(e)[:200])
    b.close()


with sync_playwright() as p:
    for dev, eng, o in qa.devices(["pixel7", "iphone14", "desktop", "mac-safari"]):
        print(dev, flush=True)
        try:
            run(p, dev, eng, o)
        except Exception as e:
            chk(dev, "EXCEPTION", False, str(e)[:600])
print()
print(f"{sum(res)}/{len(res)} passed")
