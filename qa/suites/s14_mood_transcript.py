"""«Настроение Гурудева» window: a TAP on «транскрипт» opens the transcript inside the app (Правила §8;
Satkirti / Gurudas 06.10, Pixel 7: the URL stayed the same). For every page with a quote that has a
bundled transcript (fast: the first 3): open the window by a tap, tap the link, the URL must become
/transcripts/… within 5 s in the same tab and the transcript text must be there; back. Then OFFLINE
(service worker on, network off; Chromium): the transcript seen before opens again from the app's cache.
Note: wait with pg.wait_for_timeout — Playwright updates pg.url only while it processes events
(a time.sleep loop never sees the new URL; that made s10 «§8» look broken).
usage: python s14_mood_transcript.py <base-url>   devices: QA_DEVICES; QA_FAST=1 -> 3 pages"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
res = []
TRANSCRIPTS = json.load(open(os.path.join(qa.REPO, "lib", "transcripts.json"), encoding="utf-8"))


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else info}", flush=True)


def bundled(url):
    import re
    m = re.search(r"/d/([\w-]+)|[?&]id=([\w-]+)", url or "")
    return bool(m and TRANSCRIPTS.get(m.group(1) or m.group(2)))


def pages():
    """(lang, section id) of pages whose FIRST mood block's main quote has a bundled transcript."""
    out = []
    for lang in ["ru-iast", "ru"]:
        b = json.load(open(os.path.join(qa.DATA, f"book.{lang}.json"), encoding="utf-8"))
        for s in b["sections"]:
            first = None
            for blk in s.get("content") or []:
                if blk.get("type") == "mood":
                    first = blk
                    break
            if first is None:
                for ss in s.get("subsections") or []:
                    for blk in ss.get("content") or []:
                        if blk.get("type") == "mood":
                            first = blk
                            break
                    if first:
                        break
            if first and bundled((first.get("source") or {}).get("transcript_url")):
                out.append((lang, s["id"]))
    return out[:3] if qa.fast() else out


def run(p, dev, eng, o, plist):
    b = getattr(p, eng).launch()
    c = b.new_context(locale="ru-RU", service_workers="allow", **o)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    pg = c.new_page()
    touch = o.get("has_touch", False)

    def tap(x, y):
        (pg.touchscreen.tap if touch else pg.mouse.click)(x, y)

    def center(sel):
        pg.evaluate("s=>document.querySelector(s).scrollIntoView({block:'center'})", sel)
        pg.wait_for_timeout(300)
        return pg.evaluate("s=>{const r=document.querySelector(s).getBoundingClientRect(); return {x:r.left+r.width/2,y:r.top+r.height/2}}", sel)

    def open_and_tap(url):
        pg.goto(url, wait_until="load")
        pg.wait_for_timeout(800)
        q = center(".mood-toggle")
        tap(q["x"], q["y"])
        pg.wait_for_timeout(700)
        if not pg.evaluate("!!document.querySelector('.mood-dialog a[data-transcript-link]')"):
            return None, "окно не открылось или в нём нет ссылки «транскрипт»"
        lk = center(".mood-dialog a[data-transcript-link]")
        href = pg.evaluate("document.querySelector('.mood-dialog a[data-transcript-link]').getAttribute('href')")
        n0, u0, t0 = len(c.pages), pg.url, time.time()
        tap(lk["x"], lk["y"])
        while "/transcripts/" not in pg.url and time.time() - t0 < 5:
            pg.wait_for_timeout(100)
        dt = time.time() - t0
        try:
            pg.wait_for_load_state("load", timeout=10000)
        except Exception:
            pass
        body = pg.evaluate("document.body ? document.body.innerText.length : 0") if "/transcripts/" in pg.url else 0
        ok = "/transcripts/" in pg.url and len(c.pages) == n0 and body > 500
        return ok, f"href={href}, url {u0} -> {pg.url} ({dt:.1f}s), новых вкладок={len(c.pages) - n0}, текст={body} симв."

    first_ok = None
    for lang, sid in plist:
        url = f"{BASE}/{lang}/{sid}/"
        try:
            ok, info = open_and_tap(url)
            chk(dev, f"§8 тап «транскрипт» в окне «Настроение» открывает транскрипт в приложении ({lang}/{sid})", ok, info)
            if ok and first_ok is None:
                first_ok = url
            pg.go_back()
            pg.wait_for_timeout(600)
        except Exception as e:
            chk(dev, f"§8 тап «транскрипт» в окне «Настроение» ({lang}/{sid})", False, "ERR " + str(e)[:200])
    # a touch tap whose click the browser swallows (e.g. the tap that stops the window's scrolling on Android):
    # pointerdown + pointerup on the link and NO click — the transcript must still open
    if first_ok:
        try:
            pg.goto(first_ok, wait_until="load")
            pg.wait_for_timeout(800)
            q = center(".mood-toggle")
            tap(q["x"], q["y"])
            pg.wait_for_timeout(700)
            u0, t0 = pg.url, time.time()
            pg.evaluate("""()=>{const a=document.querySelector('.mood-dialog a[data-transcript-link]'); a.scrollIntoView({block:'center'});
               const r=a.getBoundingClientRect(); const o={bubbles:true,pointerType:'touch',isPrimary:true,pointerId:9,clientX:r.left+4,clientY:r.top+4};
               a.dispatchEvent(new PointerEvent('pointerdown',o)); a.dispatchEvent(new PointerEvent('pointerup',o));}""")
            while "/transcripts/" not in pg.url and time.time() - t0 < 5:
                pg.wait_for_timeout(100)
            chk(dev, "§8 тап без click (браузер «съел» click) всё равно открывает транскрипт", "/transcripts/" in pg.url,
                f"url {u0} -> {pg.url}")
            pg.go_back()
            pg.wait_for_timeout(600)
        except Exception as e:
            chk(dev, "§8 тап без click всё равно открывает транскрипт", False, "ERR " + str(e)[:200])
    # offline: the app (service worker) has the page and the transcript seen above. Chromium only: Playwright's
    # WebKit cannot navigate with set_offline + service worker ("internal error"); WebKit offline = s20wk.
    if first_ok and eng == "chromium":
        try:
            pg.goto(first_ok, wait_until="load")
            pg.wait_for_timeout(1500)
            ctrl = pg.evaluate("!!(navigator.serviceWorker && navigator.serviceWorker.controller)")
            open_and_tap(first_ok)  # online once more, now through the service worker (it keeps what it served)
            pg.go_back()
            pg.wait_for_timeout(800)
            c.set_offline(True)
            ok, info = open_and_tap(first_ok)
            chk(dev, "§8 OFFLINE: тап «транскрипт» в окне открывает транскрипт из приложения", ok and ctrl, f"SW={ctrl}; {info}")
        except Exception as e:
            chk(dev, "§8 OFFLINE: тап «транскрипт» в окне", False, "ERR " + str(e)[:200])
        finally:
            c.set_offline(False)
    b.close()


with sync_playwright() as p:
    plist = pages()
    print(f"{len(plist)} pages", flush=True)
    for dev, eng, o in qa.devices(["pixel7", "s23fe", "iphone14", "iphone-se"]):
        print(dev, flush=True)
        run(p, dev, eng, o, plist)

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
