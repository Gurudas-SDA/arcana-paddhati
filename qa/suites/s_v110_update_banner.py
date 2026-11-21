"""V110 Vraja Lila msg 8612–8614 (variant «а», 21.11.2026): a new version of the book is announced, not silent.

Rule text (msg 8612–8614, verbatim): «сообщение «Доступна новая версия — Обновить» и «Обновление N %»» —
«а — выпускай сразу после заметок, отчитаешься по выполнению со скриншотами».

The suite runs its OWN server over out/ (qa/lib/server.py); a «new deploy» = the same build with a new version stamp
in sw.js + precache-manifest.json, slowed by srv.delay (so the new worker's core download is really visible).
Checks per device (iphone14 / pixel7 / ipad-portrait / desktop):
  A  while the new worker installs: strip «Загружается новая версия книги — N %» (N grows, ≥ 2 values), inside the
     viewport, above the reader's bottom bar; then the page switches by itself and shows «Книга обновлена» for a few
     seconds, then the strip is gone
  B  a new worker that WAITS (install without skipWaiting): «Доступна новая версия книги» + button «Обновить»;
     the button switches to the new version (reload) and «Книга обновлена» follows
  C  an install that is interrupted (worker redundant): «Не удалось загрузить» + «Повторить» in ONE row
     (V111, Vraja Lila msg 8620: «когда не удалось сократи текст чтобы кнопка умещалась в одном ряду»);
     the button asks the browser again (registration.update) and the update then goes through
usage: python s_v110_update_banner.py [<base ignored>]    V110_SHOTS=<dir> — also save screenshots (light + night)
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
import server as qa_server  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

SHOTS = os.environ.get("V110_SHOTS", "")
SHOT_TAG = os.environ.get("V110_SHOT_TAG", "2026.11.21_V110")
DEVICES = qa.devices(["iphone14", "pixel7", "ipad-portrait", "desktop"])
results = []

# the server: sw.js of a «deploy» can wait instead of skipWaiting (noskip) or fail its install (brk)
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
            body = body.replace("await precacheCore(", "throw new Error('V110 test: interrupted install'); await precacheCore(", 1)
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


def state(pg):
    return pg.evaluate("""() => { const e = document.querySelector('[data-update-banner]');
      if (!e) return null; const r = e.getBoundingClientRect(); const b = e.querySelector('button');
      return {phase: e.getAttribute('data-update-phase'), text: (e.querySelector('.update-banner-text')||{}).textContent,
        button: b ? b.textContent : null, top: r.top, bottom: r.bottom, left: r.left, right: r.right,
        vw: innerWidth, vh: innerHeight, pad: parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--reader-pad-bottom')) || 0}; }""")


def wait_phase(pg, phase, timeout=90):
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        try:
            last = state(pg)
        except Exception:
            last = None  # navigation in progress
        if last and last["phase"] == phase:
            return last
        pg.wait_for_timeout(120)
    return None


SHOT_NAMES = {"iphone14": "iPhone 14", "pixel7": "Pixel 7"}


def shot(pg, dev, name):
    if not SHOTS or dev not in SHOT_NAMES:
        return
    os.makedirs(SHOTS, exist_ok=True)
    for theme, suf in (("", ""), ("night", " (тёмная тема)")):
        pg.evaluate("t => t ? document.documentElement.setAttribute('data-reader-theme', t) : document.documentElement.removeAttribute('data-reader-theme')", theme)
        pg.wait_for_timeout(250)
        pg.screenshot(path=os.path.join(SHOTS, f"{SHOT_TAG}_{SHOT_NAMES[dev]}_{name}{suf}.png"))
    pg.evaluate("document.documentElement.removeAttribute('data-reader-theme')")


def trigger(pg):
    # a page that was reloaded a moment ago does not reload again at updatefound (InstallBanner, 10 min): it stays and shows the strip
    pg.evaluate("sessionStorage.setItem('ap.swUpdateReloadAt', String(Date.now()))")
    pg.evaluate("navigator.serviceWorker.getRegistration().then(r => r.update())")


def settle(pg):
    """the previous reload is over: page rendered, a controller present"""
    pg.wait_for_load_state("load")
    pg.wait_for_function("navigator.serviceWorker.controller !== null", timeout=60000)
    pg.wait_for_timeout(800)


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        c = b.new_context(service_workers="allow", **opts)
        c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');")
        pg = c.new_page()
        flags()
        man = json.load(open(os.path.join(qa.OUT, "precache-manifest.json"), encoding="utf-8"))
        chap = [u for u, g in zip(man["urls"], man["groups"]) if g == "ru-iast" and u.endswith("/") and u.count("/") > 3][3]
        pg.goto(SRV.origin + chap, wait_until="load")
        try:
            pg.wait_for_function("navigator.serviceWorker.controller !== null", timeout=90000)
        except Exception:
            pass
        pg.wait_for_timeout(2500)
        pg.reload(wait_until="load")  # a page that HAS a worker (a first visit is claimed without reload: nothing to update)
        settle(pg)
        check(dev, "0 no strip before any update", state(pg) is None, state(pg))

        # ---- A: the core of the new version downloads (slow), the page switches by itself ----
        flags("b", delay=0.06)
        trigger(pg)
        seen, texts, boxes = [], [], []
        t0 = time.time()
        print(f"     [{dev}] A starts", flush=True)
        shot_done = False
        while time.time() - t0 < 120:
            try:
                s = state(pg)
            except Exception:
                s = None
            if s and s["phase"] == "loading":
                m = re.search(r"(\d+) %", s["text"] or "")
                if m:
                    seen.append(int(m.group(1)))
                texts.append(s["text"])
                boxes.append(s)
                if not shot_done and m and 8 <= int(m.group(1)) <= 90:
                    shot(pg, dev, "Загружается новая версия — N %")
                    shot_done = True
            elif s and s["phase"] in ("ready", "done"):
                break
            elif s is None and seen:
                break
            pg.wait_for_timeout(100)
        ok_text = bool(texts) and all(re.fullmatch(r"Загружается новая версия книги — \d+ %", t or "") for t in texts)
        check(dev, "A1 «Загружается новая версия книги — N %» shown while the new version downloads", ok_text, texts[:2])
        check(dev, "A2 N grows (>= 2 different values, never goes back)", len(set(seen)) >= 2 and seen == sorted(seen), seen[:12])
        bx = boxes[len(boxes) // 2] if boxes else None
        check(dev, "A3 strip inside the screen, above the reader's bottom bar",
              bx and bx["left"] >= 0 and bx["right"] <= bx["vw"] + 0.5 and bx["bottom"] <= bx["vh"] - 48 + 0.5 and bx["top"] > bx["vh"] / 2, bx)
        print(f"     [{dev}] A loading seen after {time.time() - t0:.0f}s", flush=True)
        d = wait_phase(pg, "done", 120)
        check(dev, "A4 after the switch (reload) «Книга обновлена»", d and d["text"] == "Книга обновлена", d and d["text"])
        gone = False
        for _ in range(80):
            try:
                if state(pg) is None:
                    gone = True
                    break
            except Exception:
                pass  # the page is reloading (the strip was shown on the old page too)
            pg.wait_for_timeout(100)
        check(dev, "A5 «Книга обновлена» disappears by itself within 8 s", gone)
        settle(pg)

        # ---- B: a waiting version: «Доступна новая версия книги» + «Обновить» ----
        flags("c", delay=0.02, noskip=True)
        trigger(pg)
        r = wait_phase(pg, "ready", 120)
        check(dev, "B1 waiting version: «Доступна новая версия книги» + button «Обновить»",
              r and r["text"] == "Доступна новая версия книги" and r["button"] == "Обновить", r)
        if r:
            shot(pg, dev, "Доступна новая версия — Обновить")
            pg.wait_for_timeout(1500)
            still = state(pg)
            check(dev, "B2 the page does NOT switch by itself while it waits (the reader decides)", still and still["phase"] == "ready", still)
            pg.locator("[data-update-action=ready]").click()
            d = wait_phase(pg, "done", 90)
            check(dev, "B3 «Обновить» switches to the new version and «Книга обновлена» follows", d and d["text"] == "Книга обновлена", d and d["text"])
            settle(pg)
            names = pg.evaluate("caches.keys()")
            check(dev, "B4 the new version is the one in use (its cache exists)", any(n.endswith(SRV.base_version() + "c") for n in names), names)
        flags("d", brk=True)

        # ---- C: an interrupted install ----
        trigger(pg)
        f = wait_phase(pg, "failed", 90)
        check(dev, "C1 interrupted install: «Не удалось загрузить» + button «Повторить»",
              f and f["text"] == "Не удалось загрузить" and f["button"] == "Повторить", f)
        row = pg.evaluate("""() => { const t = document.querySelector('.update-banner-text'), b = document.querySelector('[data-update-action=failed]');
            if (!t || !b) return null; const r1 = t.getBoundingClientRect(), r2 = b.getBoundingClientRect();
            return {textTop: r1.top, textBottom: r1.bottom, btnTop: r2.top, btnBottom: r2.bottom, textLines: Math.round(r1.height / parseFloat(getComputedStyle(t).lineHeight))}; }""")
        check(dev, "C1c V111 text and «Повторить» in one row (button not wrapped below the text, text in one line)",
              row and row["btnTop"] < row["textBottom"] and row["textTop"] < row["btnBottom"] and row["textLines"] <= 1, row)
        if f:
            shot(pg, dev, "Не удалось загрузить — Повторить")
            flags("d", delay=0.02)  # the network is fine again
            # (a browser may retry the broken install by itself and re-draw the strip meanwhile: click the button as it is)
            clicked = pg.evaluate("() => { const b = document.querySelector('[data-update-action=failed]'); if (b) b.click(); return !!b; }")
            check(dev, "C1b the «Повторить» button is there to press", clicked)
            seen_after = wait_phase(pg, "done", 120)
            check(dev, "C2 «Повторить» asks the browser again and the update goes through", seen_after and seen_after["text"] == "Книга обновлена", seen_after and seen_after["text"])
        c.close()
        b.close()

SRV.stop()
print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
