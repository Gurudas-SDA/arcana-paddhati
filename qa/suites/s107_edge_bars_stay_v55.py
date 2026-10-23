"""V55 Враджа Лила msg 1728/1730 (23.10.2026 13:18, nodots-izpildei; saskarnes īpašnieks, «Стандарты» 0а).

Prasība burtiski (msg 1728): «ВАЖНО: исправь — мы договорились, что на начале главы или отмотав в конец автоматом
выезжают верхняя и нижняя панель… отматывая на начало главы панель выезжает и быстро сама же задвигается обратно;
с нижней панелью срабатывает через раз».
Norunātais (nodots-izpildei 23.10 13:18): «в НАЧАЛЕ и в КОНЦЕ главы (прокрутка до края) верхняя И нижняя панели
выезжают автоматически и ОСТАЮТСЯ, пока читатель не прокрутит обратно в текст или не коснётся».

How a phone scrolls, as the test plays it (the app's own .app-main, frame by frame):
  finger   — a short drag: touchmove + scroll every frame;
  glide    — the momentum after the finger is lifted: scroll events only, NO touchmove (a long fling glides
             ~2.4 s, a short one ~0.4 s);
  bounce   — iPhone (WebKit) only: the rubber band at the very top / bottom — scrollTop goes past the edge
             (below 0 / above the end) and springs back to it; Android Chrome has no such scrollTop values.
Per device (iphone14 WebKit, pixel7 Chromium), per mode («Страницы», «Лента»), 10 times each:
  S  scrolled down into the text first → the bars are gone (precondition, «прокрутит обратно в текст»);
     a fling back up to the chapter's start → both bars are out 0.7 s after it stops, and (1st round) still
     after 5 s more;
  E  scrolled up from the end into the text → the bars are gone; a fling down to the chapter's end → both
     bars are out 0.7 s after it stops, and (1st round) still after 5 s more.
Rounds alternate a long and a short glide. «Лента»: the chapter's start / end inside the whole book (no rubber band
there — the book goes on).
usage: python s107_edge_bars_stay_v55.py <base-url>
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
LANG = "ru-iast"
PAGES_CHAPTER = "daily-deity-schedule"
SCROLL_CHAPTER = "arcana-procedure"
ROUNDS = int(os.environ.get("S107_ROUNDS", "10"))
results = []


def check(device, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {device} {name} {info}", flush=True)


SHOWN_JS = """() => { const c = document.querySelector('.reader-chrome');
  const op = s => { const e = document.querySelector(s); return e ? parseFloat(getComputedStyle(e).opacity) : 0; };
  return {shown: !!(c && c.hasAttribute('data-shown')), top: op('.reader-bar-top'), bottom: op('.reader-bar-bottom')}; }"""

# The chapter's start / end as scroll positions of .app-main («Страницы»: the page; «Лента»: its section).
EDGES_JS = """id => {
  const m = document.querySelector('.app-main');
  const s = document.querySelector(`[data-book-section="${id}"]`);
  const real = m.scrollHeight - m.clientHeight;
  if (!s) {
    const sps = m.querySelectorAll('.chapter-end-space'); const sp = sps.length ? sps[sps.length - 1].offsetHeight : 0;
    return {start: 0, end: real, text: Math.max(0, real - sp), real};
  }
  const mr = m.getBoundingClientRect(), r = s.getBoundingClientRect();
  const margin = parseFloat(getComputedStyle(s).scrollMarginTop) || 0;
  const sp = s.querySelector('.chapter-end-space')?.offsetHeight || 0;
  const start = Math.round(m.scrollTop + r.top - mr.top - margin);
  const end = Math.ceil(m.scrollTop + (r.bottom - sp) - mr.bottom) + 1;
  return {start, end, text: end, real};
}"""

# One gesture: finger (touchmove + scroll each frame), then glide (scroll only), then — on WebKit phones at the
# very top / bottom — the rubber band past the edge and back. scrollTop reads the played value (it may be < 0 or
# past the end during the bounce, as on an iPhone); the real position follows, clamped.
GESTURE_JS = """async ({from, to, fingerMs, glideMs, over}) => {
  const m = document.querySelector('.app-main');
  const d = Object.getOwnPropertyDescriptor(Element.prototype, 'scrollTop');
  if (!m.__v55) {
    Object.defineProperty(m, 'scrollTop', {configurable: true,
      get() { return window.__v55Top !== undefined ? window.__v55Top : d.get.call(this); },
      set(v) { window.__v55Top = undefined; d.set.call(this, v); }});
    m.__v55 = 1;
  }
  const frame = () => new Promise(r => requestAnimationFrame(() => r()));
  const max = m.scrollHeight - m.clientHeight;
  const put = (v, finger) => {
    if (finger) m.dispatchEvent(new Event('touchmove', {bubbles: true}));
    d.set.call(m, Math.max(0, Math.min(max, v)));
    window.__v55Top = v;
    m.dispatchEvent(new Event('scroll'));
  };
  const phase = async (a, b, ms, finger, ease) => {
    const t0 = performance.now();
    for (;;) {
      await frame();
      const k = Math.min(1, (performance.now() - t0) / Math.max(1, ms));
      put(a + (b - a) * (ease ? 1 - Math.pow(1 - k, 3) : k), finger);
      if (k >= 1) break;
    }
  };
  const fingerTo = glideMs ? from + (to - from) * 0.25 : to;
  await phase(from, fingerTo, fingerMs, true, false);
  if (glideMs) await phase(fingerTo, to, glideMs, false, true);
  if (over) {
    const past = to + over;
    await phase(to, past, 110, false, true);
    await phase(past, to, 380, false, true);
  }
  await frame();
  window.__v55Top = undefined;
  d.set.call(m, Math.max(0, Math.min(max, to)));
  return m.scrollTop;
}"""


def run(browser, device, options, engine):
    context = browser.new_context(service_workers="block", **options)
    context.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true')}catch(e){}")
    page = context.new_page()
    errors = []
    host = BASE.split("//")[1].split("/")[0]
    page.on("pageerror", lambda error: None if (str(error).rstrip().endswith("due to access control checks.") and host in str(error)) else errors.append(str(error)))
    bounce = engine == "webkit"

    def gesture(frm, to, glide, over=0):
        return page.evaluate(GESTURE_JS, {"from": frm, "to": to, "fingerMs": 160 if glide else 320,
                                          "glideMs": glide, "over": over})

    def state():
        return page.evaluate(SHOWN_JS)

    def out(st):
        return st["shown"] and st["top"] > 0.9 and st["bottom"] > 0.9

    def rounds(mode, chapter):
        e = page.evaluate(EDGES_JS, chapter)
        span = min(700, max(200, (e["text"] - e["start"]) // 3))
        fail_s = fail_e = 0
        info_s = info_e = None
        # S — the chapter's start
        page.evaluate(f"() => {{ document.querySelector('.app-main').scrollTop = {e['start']}; }}")
        page.wait_for_timeout(400)
        for i in range(ROUNDS):
            glide = 2400 if i % 2 == 0 else 420
            gesture(e["start"], e["start"] + span, 0)  # into the text (finger only)
            page.wait_for_timeout(500)
            before = state()
            gesture(e["start"] + span, e["start"], glide, -70 if (bounce and e["start"] == 0) else 0)
            page.wait_for_timeout(700)
            after = state()
            later = None
            if i == 0:
                page.wait_for_timeout(5000)
                later = state()
            ok = (not before["shown"]) and out(after) and (later is None or out(later))
            if not ok:
                fail_s += 1
                info_s = info_s or {"round": i + 1, "glide_ms": glide, "before": before, "after": after, "after5s": later}
        check(device, f"S {mode}: {ROUNDS}× text → fling back to the chapter's start → both bars out and they stay",
              fail_s == 0, f"failed {fail_s}/{ROUNDS} first={info_s}" if fail_s else "")
        # E — the chapter's end
        e = page.evaluate(EDGES_JS, chapter)
        back = e["text"] - span
        # into the text above the end, reading on (down) — the bars from the start are gone
        page.evaluate(f"() => {{ document.querySelector('.app-main').scrollTop = {back - 300}; }}")
        page.wait_for_timeout(400)
        gesture(back - 300, back, 0)
        for i in range(ROUNDS):
            glide = 2400 if i % 2 == 0 else 420
            if i:
                gesture(e["end"], back, 0)  # up from the end into the text (finger only)
            page.wait_for_timeout(500)
            before = state()
            at_bottom = e["end"] >= e["real"] - 1
            gesture(back, e["end"], glide, 70 if (bounce and at_bottom) else 0)
            page.wait_for_timeout(700)
            after = state()
            later = None
            if i == 0:
                page.wait_for_timeout(5000)
                later = state()
            ok = (not before["shown"]) and out(after) and (later is None or out(later))
            if not ok:
                fail_e += 1
                info_e = info_e or {"round": i + 1, "glide_ms": glide, "before": before, "after": after, "after5s": later}
        check(device, f"E {mode}: {ROUNDS}× text → fling down to the chapter's end → both bars out and they stay",
              fail_e == 0, f"failed {fail_e}/{ROUNDS} first={info_e}" if fail_e else "")

    try:
        # «Страницы» (default)
        page.goto(f"{BASE}/{LANG}/{PAGES_CHAPTER}/", wait_until="networkidle")
        qa.wait_for_book_chapter(page, PAGES_CHAPTER)
        page.wait_for_timeout(1500)
        rounds("Страницы", PAGES_CHAPTER)
        # «Лента»
        page.evaluate("try{localStorage.setItem('ap.readerLayout','scroll')}catch(e){}")
        page.goto(f"{BASE}/{LANG}/{SCROLL_CHAPTER}/", wait_until="networkidle")
        page.wait_for_selector("[data-continuous-book]", state="attached", timeout=30000)
        qa.wait_for_book_chapter(page, SCROLL_CHAPTER)
        page.wait_for_timeout(1500)
        rounds("Лента", SCROLL_CHAPTER)
        page.evaluate("try{localStorage.removeItem('ap.readerLayout')}catch(e){}")
        check(device, "no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(device, "scenario ran", False, str(error)[:300])
    finally:
        context.close()


with sync_playwright() as playwright:
    for device, engine, options in qa.devices(["iphone14", "pixel7"]):
        browser = getattr(playwright, engine).launch()
        run(browser, device, options, engine)
        browser.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
