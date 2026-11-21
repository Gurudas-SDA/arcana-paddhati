"""V113 Vraja Lila msg 8643 + 8644 (21.11.2026), verbatim: «давай сделаем, что индикатор новой версии, загрузка и когда не удалось загрузить
остаётся только на обложке… и то, что доступна новая версия/обновление. Внутри на страницах оно не появляется снизу вообще» —
«выпускай в приоритетном порядке».
Criteria (register V113): the update strip (every state: loading N %, «Доступна новая версия / Обновить», «Не удалось загрузить / Повторить»)
  a  on the cover (HomePage): shown
  b  on an inner (chapter) page: NOT in the page at all, in none of the states, and no html[data-update-strip] / --update-banner-h
     (no empty space at the bottom)
  c  the state lives in lib/swUpdate.ts (not in the strip): a page that gets the state on a chapter shows it when the reader goes back to the cover
The states are made as in s_v110_update_banner.py: the progress message (loading), a worker that WAITS (noskip -> ready), an install that fails (brk -> failed).
The suite runs its OWN server over out/. usage: python s_v113_strip_cover_only.py [<ignored>]
V113_SHOTS=<dir> — save screenshots (iPhone 14 / Pixel 7, light + night): the cover with the failed strip, a chapter page without it
# tehniskais slieksnis Lipikāra, nav S noteikums: settle 700-1200 ms, 6 s wait for the failed state
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
import server as qa_server  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

SHOTS = os.environ.get("V113_SHOTS", "")
DEVICES = qa.devices(["iphone14", "pixel7", "ipad-portrait", "desktop"])
LANG = "ru-iast"
results = []
_orig_patched = qa_server._Handler._patched


def _patched(self, name):
    srv = self.server_ref
    if name.endswith("/sw.js") and srv.version_suffix and (getattr(srv, "noskip", False) or getattr(srv, "brk", False)):
        fn = self.translate_path(name)
        body = open(fn, "rb").read().decode("utf-8")
        body = body.replace(srv.base_version(), srv.base_version() + srv.version_suffix)
        if getattr(srv, "noskip", False):
            assert "await self.skipWaiting();" in body
            body = body.replace("await self.skipWaiting();", "")
        if getattr(srv, "brk", False):
            assert "await precacheCore(" in body
            body = body.replace("await precacheCore(", "throw new Error('V113 test: interrupted install'); await precacheCore(", 1)
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/javascript")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        return
    return _orig_patched(self, name)


qa_server._Handler._patched = _patched
SRV = qa_server.Server().start()
BASE = SRV.base


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


def flags(suffix="", delay=0.0, noskip=False, brk=False):
    SRV.version_suffix = suffix
    SRV.delay = delay
    SRV.noskip = noskip
    SRV.brk = brk


STRIP = """() => { const strips = [...document.querySelectorAll('[data-update-banner]')];
  const vis = strips.filter((e) => e.getBoundingClientRect().height > 0);
  const root = document.documentElement;
  return {n: strips.length, vis: vis.length, phase: strips[0] ? strips[0].getAttribute('data-update-phase') : null,
    text: strips[0] ? strips[0].textContent : null, attr: root.hasAttribute('data-update-strip'),
    h: root.style.getPropertyValue('--update-banner-h'), path: location.pathname}; }"""
PROGRESS = "() => navigator.serviceWorker.dispatchEvent(new MessageEvent('message', {data: {type: 'sw-update-progress', done: 53, total: 100}}))"
SHOT_NAMES = {"iphone14": "iPhone 14", "pixel7": "Pixel 7"}


def shot(pg, dev, name):
    if not SHOTS or dev not in SHOT_NAMES:
        return
    os.makedirs(SHOTS, exist_ok=True)
    for theme, suf in (("", ""), ("night", " (тёмная тема)")):
        pg.evaluate("t => t ? document.documentElement.setAttribute('data-reader-theme', t) : document.documentElement.removeAttribute('data-reader-theme')", theme)
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(SHOTS, f"2026.11.21_V113_{SHOT_NAMES[dev]}_{name}{suf}.png"))
    pg.evaluate("document.documentElement.removeAttribute('data-reader-theme')")


def settle(pg):
    pg.wait_for_load_state("load")
    pg.wait_for_function("navigator.serviceWorker.controller !== null", timeout=90000)
    pg.wait_for_timeout(1200)


def trigger(pg):
    pg.evaluate("sessionStorage.setItem('ap.swUpdateReloadAt', String(Date.now()))")
    pg.evaluate("navigator.serviceWorker.getRegistration().then(r => r.update())")


def new_ctx(p, eng, o):
    b = getattr(p, eng).launch()
    c = b.new_context(service_workers="allow", **o)
    c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');")
    return b, c


def watch(pg, ms=2500):
    """strip never appears over `ms`: the worst (max) numbers"""
    worst = {"n": 0, "vis": 0, "attr": False, "h": ""}
    for _ in range(ms // 250):
        s = pg.evaluate(STRIP)
        worst = {"n": max(worst["n"], s["n"]), "vis": max(worst["vis"], s["vis"]), "attr": worst["attr"] or s["attr"], "h": worst["h"] or s["h"]}
        pg.wait_for_timeout(250)
    return worst


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        print(dev, flush=True)
        try:
            man = json.load(open(os.path.join(qa.OUT, "precache-manifest.json"), encoding="utf-8"))
            chap = [u for u, g in zip(man["urls"], man["groups"]) if g == LANG and u.endswith("/") and u.count("/") > 3][3]
            # ---- loading: the cover has it, a chapter has not ----
            flags()
            b, c = new_ctx(p, eng, o)
            pg = c.new_page()
            pg.goto(f"{BASE}/{LANG}/", wait_until="load")
            settle(pg)
            pg.reload(wait_until="load")
            settle(pg)
            pg.evaluate(PROGRESS)
            pg.wait_for_timeout(700)
            s = pg.evaluate(STRIP)
            check(dev, "a1 cover: the strip «… 53 %» is shown", s["vis"] == 1 and "53" in (s["text"] or ""), s)
            pg.goto(SRV.origin + chap, wait_until="load")
            settle(pg)
            pg.evaluate(PROGRESS)
            w = watch(pg)
            check(dev, "b1 chapter page, loading: no strip in the page, no html[data-update-strip] / --update-banner-h", w["n"] == 0 and not w["attr"] and not w["h"], w)
            shot(pg, dev, "страница главы без строки обновления")
            # c: the state lives in lib/swUpdate.ts: cover -> (in-page navigation) chapter -> back = the cover shows the current state
            pg.goto(f"{BASE}/{LANG}/", wait_until="load")
            settle(pg)
            pg.reload(wait_until="load")
            settle(pg)
            moved = pg.evaluate("() => { const a = [...document.querySelectorAll('a[href]')].find((x) => { const u = new URL(x.href); return u.origin === location.origin && u.pathname.replace(/\\/$/, '') !== location.pathname.replace(/\\/$/, '') && !x.hasAttribute('download'); }); if (a) a.click(); return !!a; }")
            pg.wait_for_timeout(2000)
            inner = pg.evaluate(STRIP)
            if moved and inner["path"].rstrip("/") != f"{BASE}/{LANG}".replace(SRV.origin, "").rstrip("/"):
                pg.evaluate(PROGRESS)
                w2 = watch(pg, 1500)
                check(dev, "b1b inside the book (in-page navigation from the cover), loading: no strip", w2["n"] == 0 and not w2["attr"] and not w2["h"], {"w": w2, "path": inner["path"]})
                pg.go_back()
                pg.wait_for_timeout(1500)
                s2 = pg.evaluate(STRIP)
                check(dev, "c1 back on the cover (same page session): the current state «… 53 %» is shown", s2["vis"] == 1 and "53" in (s2["text"] or ""), s2)
            else:
                check(dev, "c1 in-page navigation from the cover works", False, inner)
            c.close()
            b.close()

            # ---- ready: a waiting version ----
            b, c = new_ctx(p, eng, o)
            pg = c.new_page()
            flags()
            pg.goto(SRV.origin + chap, wait_until="load")
            settle(pg)
            pg.reload(wait_until="load")
            settle(pg)
            flags("c", delay=0.02, noskip=True)
            trigger(pg)
            ok = True
            try:
                for _ in range(120):
                    if pg.evaluate("navigator.serviceWorker.getRegistration().then(r => !!(r && r.waiting))"):
                        break
                    pg.wait_for_timeout(250)
                else:
                    ok = False
            except Exception:
                ok = False
            check(dev, "b2a a new version WAITS (the state «Доступна новая версия» exists)", ok)
            w = watch(pg)
            check(dev, "b2 chapter page, «Доступна новая версия / Обновить»: no strip, no html[data-update-strip]", w["n"] == 0 and not w["attr"] and not w["h"], w)
            c.close()
            b.close()

            # ---- failed ----
            b, c = new_ctx(p, eng, o)
            pg = c.new_page()
            flags()
            pg.goto(SRV.origin + chap, wait_until="load")
            settle(pg)
            pg.reload(wait_until="load")
            settle(pg)
            flags("d", brk=True)
            trigger(pg)
            pg.wait_for_timeout(5000)
            w = watch(pg)
            check(dev, "b3 chapter page, «Не удалось загрузить / Повторить»: no strip, no html[data-update-strip]", w["n"] == 0 and not w["attr"] and not w["h"], w)
            # the cover in the same browser (the failed state is per page load: reach the cover and trigger there)
            pg.goto(f"{BASE}/{LANG}/", wait_until="load")
            settle(pg)
            trigger(pg)
            got = None
            for _ in range(120):
                s = pg.evaluate(STRIP)
                if s["phase"] == "failed":
                    got = s
                    break
                pg.wait_for_timeout(250)
            check(dev, "a2 cover: «Не удалось загрузить / Повторить» is shown", got and got["vis"] == 1 and "Не удалось загрузить" in got["text"] and "Повторить" in got["text"], got)
            shot(pg, dev, "обложка со строкой Не удалось загрузить")
            c.close()
            b.close()
        except Exception as e:  # noqa: BLE001
            check(dev, "EXCEPTION", False, str(e)[:600])

SRV.stop()
print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
