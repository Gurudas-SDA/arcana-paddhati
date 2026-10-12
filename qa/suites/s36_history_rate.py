"""Safari history quota (Vraja Lila 13.10): WebKit throws SecurityError after 100
pushState/replaceState calls in 10 s, and then «Содержание» stops opening rows.

Every pushState/replaceState is counted at History.prototype (app and Next.js
router writes alike, as Safari counts them) while a person reads fast:
  A  the book scrolled fast for 10 s (the reading area moved every frame);
  B  «Содержание» used fast for 10 s: the list flicked and a row tapped every
     200 ms; the menu is reopened when a tap opened a page. A tap is the row's
     pointerdown/pointerup/click dispatched at the point under the finger
     (Playwright's touchscreen.tap on WebKit takes ~0.4 s, which spreads the
     burst and hides the quota); QA_FAST_TAP=0 uses real touches, QA_PACE=<s>
     changes the pace.
Checks per phase: the most writes in any 10 s window <= 100, no SecurityError
from history; after the burst a row still opens (two taps -> new URL) and
«Назад» returns (transitions never freeze).
usage: python s36_history_rate.py <base-url>   devices: QA_DEVICES"""
import os
import sys
import time
from urllib.parse import unquote, urlsplit

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
L = "ru-iast"
DEVICES = qa.devices(["iphone14"])
LIMIT, WINDOW = 100, 10000.0  # WebKit: 100 calls per 10 s
BURST_S, PACE = 10.0, float(os.environ.get("QA_PACE", "0.2"))
FAST_TAP = os.environ.get("QA_FAST_TAP", "1") == "1"
res = []

COUNTER = r"""(() => {
  if (window.__qaW) return;
  const P = History.prototype, log = window.__qaW = [], err = window.__qaE = [];
  for (const n of ['pushState', 'replaceState']) {
    const native = P[n];
    P[n] = function (...a) {
      log.push([n, performance.now()]);
      try { return native.apply(this, a); }
      catch (e) { err.push(n + ': ' + e.name + ' ' + e.message); throw e; }
    };
  }
})()"""

SCROLL = """async (ms) => {
  const m = document.querySelector('.app-main'), t = performance.now();
  while (performance.now() - t < ms) {
    m.scrollTop += 240;
    if (m.scrollTop + m.clientHeight >= m.scrollHeight - 2) m.scrollTop = 0;
    m.dispatchEvent(new Event('scroll'));
    await new Promise(r => requestAnimationFrame(r));
  }
}"""

FLICK = """() => {
  const l = document.querySelector('.mobile-menu .toc-scroll');
  if (!l) return null;
  const max = Math.max(1, l.scrollHeight - l.clientHeight);
  l.scrollTop = (l.scrollTop + 70) % max;
  const r = l.getBoundingClientRect();
  return {x: r.left + 60, y: r.top + r.height * (0.25 + Math.random() * 0.5)};
}"""


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else info}"[:900], flush=True)


def info(dev, text):
    print(f"  [INFO] {dev} {text}", flush=True)


def here(url):
    u = urlsplit(url)
    return unquote(u.path) + (("#" + unquote(u.fragment)) if u.fragment else "")


def peak(ts):
    """Most calls inside any WINDOW ms."""
    best, j = 0, 0
    for i, t in enumerate(ts):
        while t - ts[j] > WINDOW:
            j += 1
        best = max(best, i - j + 1)
    return best


def run(p, dev, eng, o):
    b = getattr(p, eng).launch()
    c = b.new_context(locale="ru-RU", service_workers="block", **o)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    c.add_init_script(COUNTER)
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    vw = pg.viewport_size
    menu = lambda: pg.locator(".mobile-menu").count() == 1

    def open_contents():
        for _ in range(4):
            if menu():
                return True
            if pg.locator(".reader-chrome[data-shown]").count() == 0:
                pg.touchscreen.tap(vw["width"] - 6, vw["height"] / 2)
                pg.wait_for_timeout(300)
            try:
                pg.locator("[data-reader-action=contents]").tap(timeout=2000)
            except Exception:
                pass
            pg.wait_for_timeout(400)
        return menu()

    def calls(since):
        return pg.evaluate(f"window.__qaW.slice({since})")

    def report(phase, w, extra=""):
        ts = [t for _, t in w]
        n_push = sum(1 for k, _ in w if k == "pushState")
        pk = peak(ts)
        info(dev, f"{phase}: {len(w)} calls ({n_push} pushState, {len(w) - n_push} replaceState){extra}; peak {pk} per 10 s")
        chk(dev, f"{phase}: history calls in any 10 s <= {LIMIT}", pk <= LIMIT, f"peak {pk}")

    pg.goto(f"{BASE}/{L}/introduction/", wait_until="networkidle")
    pg.wait_for_timeout(1000)

    # A: the book scrolled fast
    n0 = pg.evaluate("window.__qaW.length")
    pg.evaluate(SCROLL, int(BURST_S * 1000))
    pg.wait_for_timeout(600)  # the last write after the scroll stops
    report("A book fast scroll 10 s", calls(n0))

    # B: «Содержание» used fast
    chk(dev, "B Содержание opens", open_contents())
    n1 = pg.evaluate("window.__qaW.length")
    t0, taps, reopen = time.monotonic(), 0, 0
    while time.monotonic() - t0 < BURST_S:
        slot = t0 + taps * PACE
        if slot > time.monotonic():
            time.sleep(slot - time.monotonic())
        if not menu():
            reopen += 1
            open_contents()
            continue
        pt = pg.evaluate(FLICK)
        if pt and FAST_TAP:
            pg.evaluate("""([x, y]) => { const e = document.elementFromPoint(x, y); if (!e) return;
              const o = {bubbles: true, cancelable: true, clientX: x, clientY: y, pointerType: 'touch', isPrimary: true};
              e.dispatchEvent(new PointerEvent('pointerdown', o)); e.dispatchEvent(new PointerEvent('pointerup', o));
              e.click(); }""", [pt["x"], pt["y"]])
        elif pt:
            pg.touchscreen.tap(pt["x"], pt["y"])
        taps += 1
    pg.wait_for_timeout(800)
    report("B Содержание fast flick+taps 10 s", calls(n1), f", {taps} taps, menu reopened {reopen}x")

    qerr = pg.evaluate("window.__qaE") + [e for e in errs if "history" in e.lower() or "SecurityError" in e]
    chk(dev, "no SecurityError from pushState/replaceState", not qerr, str(qerr[:3]))

    # transitions still work: two taps on a row open it, «Назад» comes back
    ok_open = ok_back = False
    if open_contents():
        u0 = here(pg.url)
        rows = pg.locator(".mobile-menu nav a[data-toc-row]")
        target = None
        for i in range(rows.count()):
            href = unquote(rows.nth(i).get_attribute("href") or "")
            if href and href.split("#")[0].rstrip("/") != u0.split("#")[0].rstrip("/") and rows.nth(i).get_attribute("data-toc-row") != "cover":
                target = rows.nth(i)
                break
        if target is not None:
            for _ in range(2):
                try:
                    target.scroll_into_view_if_needed(timeout=2000)
                    target.tap(timeout=3000)
                except Exception:
                    pass
                pg.wait_for_timeout(300)
                if not menu():
                    break
            try:
                pg.wait_for_function("(u) => decodeURI(location.pathname) + decodeURIComponent(location.hash) !== u && !document.querySelector('.mobile-menu')",
                                     arg=u0, timeout=8000)
                ok_open = True
            except Exception:
                pass
            if ok_open:
                pg.go_back()
                try:
                    pg.wait_for_function("(u) => decodeURI(location.pathname) + decodeURIComponent(location.hash) === u", arg=u0, timeout=8000)
                    ok_back = True
                except Exception:
                    pass
    chk(dev, "after the burst: two taps on a row open it (no freeze)", ok_open, here(pg.url))
    chk(dev, "after the burst: «Назад» returns to the place before", ok_back, here(pg.url))
    b.close()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        print(f"== {dev}", flush=True)
        try:
            run(p, dev, eng, o)
        except Exception as e:
            chk(dev, "suite crashed", False, repr(e)[:300])
print(f"s36: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
