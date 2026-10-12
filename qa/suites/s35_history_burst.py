"""History writes under fast tapping (UI §9.2, §9.3, §10.1, §10.2; Phase 3 item 1).

WebKit allows 100 pushState/replaceState calls per 10 s; beyond that it throws
and the Contents stop opening rows. Every pushState/replaceState is counted at
History.prototype. A write is the app's when a frame of its call stack comes
from an app chunk (found in out/ by the app's history keys); the rest are
Next.js's own router writes (one after each app write that changes the URL,
one after each Back / Forward), reported separately.

Per device and Contents mode (default one-tap, ?toc=two):
  A  17 actions (the burst that broke WebKit in Phase 2), each state recorded:
     app writes <= actions, one history entry per action, no quota error,
     every row did its action, Back x17 and Forward x17 restore every URL,
     highlight and open list.
  B  40 actions within 10 s (stress margin): the same limits, then a burst of
     20 Back and 20 Forward presses (writes measured, the right steps reached),
     then one more row action still works.
Taps are real touches / clicks paced at one per 250 ms.
An action is one tap on a Contents row: in the default mode it opens the
chapter (expanding its list) or collapses it; with ?toc=two every tap is a
step (highlight, expand, collapse).
usage: python s35_history_burst.py <base-url>   devices: QA_DEVICES
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from toc import Contents  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
LANG = "ru-iast"
PART = "temple-worship"
DEVICES = ["pixel7", "iphone14", "ipad-portrait", "desktop"]
SHORT, STRESS, STRESS_SECONDS, BACK_BURST = 17, 40, 10.0, 20
# One tap every 250 ms: 40 actions in 10 s, a fast person, for both cases.
PACE = STRESS_SECONDS / STRESS
KEYS = ("url", "menu", "lit", "open")
res = []

CHUNKS = os.path.join(qa.OUT, "_next", "static", "chunks")
APP_CHUNKS = sorted(
    f for f in os.listdir(CHUNKS)
    if f.endswith(".js") and any(m in open(os.path.join(CHUNKS, f), encoding="utf-8", errors="ignore").read()
                                 for m in ("apKey", "apBook", "apMenu", "apLit")))

COUNTER = r"""(() => {
  if (window.__qaWrites) return;
  try { Error.stackTraceLimit = 80; } catch (e) {}
  const APP = __APP__, P = History.prototype;
  const log = window.__qaWrites = [], errors = window.__qaQuota = [];
  const app = () => { const s = new Error().stack || ''; return APP.some(f => s.includes(f)); };
  for (const [name, kind] of [['pushState', 'push'], ['replaceState', 'replace']]) {
    const native = P[name];
    P[name] = function (data, unused, url) {
      log.push({kind, app: app()});
      try { return native.call(this, data, unused, url); }
      catch (e) { errors.push(kind + ': ' + e.message); throw e; }
    };
  }
})()""".replace("__APP__", json.dumps(APP_CHUNKS))


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} [toc={qa.TOC_MODE_NAME}] {'' if ok else info}"[:900], flush=True)


def info(dev, name):
    print(f"  [INFO] {dev} {name} [toc={qa.TOC_MODE_NAME}]", flush=True)


def writes(pg, since):
    w = pg.evaluate(f"window.__qaWrites.slice({since})")
    return dict(app=sum(x["app"] for x in w), app_push=sum(x["app"] and x["kind"] == "push" for x in w),
                app_replace=sum(x["app"] and x["kind"] == "replace" for x in w), next=sum(not x["app"] for x in w))


def plan(chapters, mode, n):
    """[(chapter, expected effect)] - n row taps cycling through the part's chapters."""
    cycle = ("open", "collapse") if mode.one else ("highlight", "expand", "collapse")
    out = []
    while len(out) < n:
        for c in chapters:
            out.extend((c, effect) for effect in cycle)
    return out[:n]


POINT = """async ([id, two]) => {
  // Where a person would tap: once the list has stopped moving (the app
  // smooth-scrolls an opened list into view), at most ~200 ms.
  const frame = () => new Promise(r => requestAnimationFrame(r));
  const list = document.querySelector('.mobile-menu .toc-scroll');
  for (let i = 0, last = -1; list && i < 12; i++) {
    await frame();
    if (list.scrollTop === last) break;
    last = list.scrollTop;
  }
  const row = document.querySelector(`.mobile-menu [data-toc-chapter="${id}"]`);
  const toggle = two && document.querySelector(`.mobile-menu [data-toc-toggle="${id}"]`);
  const target = toggle || row;
  if (!target) return null;
  // The app may still move the list (its reveal retry runs 120 ms after an
  // expand): measure again until the row really is under the point.
  let x = 0, y = 0, hit = null, hits = false;
  for (let i = 0; i < 15 && !hits; i++) {
    // The list scrolls smoothly (CSS); WebKit animates even an "instant"
    // scrollIntoView there, and hit-testing follows the animation. A finger
    // dragging the list moves it at once: scroll this one step without smoothing.
    const smooth = list && list.style.scrollBehavior;
    if (list) list.style.scrollBehavior = 'auto';
    target.scrollIntoView({block: 'nearest', behavior: 'instant'});
    if (list) list.style.scrollBehavior = smooth;
    await frame();
    const r = target.getBoundingClientRect();
    // As Contents.tap: the row 60 px in; with ?toc=two its toggle's centre.
    // (The row's far right lies under the list's scrollbar in WebKit.)
    x = toggle ? r.left + r.width / 2 : r.left + Math.min(60, r.width / 2); y = r.top + r.height / 2;
    hit = document.elementFromPoint(x, y);
    hits = !!hit && (hit === target || target.contains(hit) || row.contains(hit));
  }
  return {x, y, hits,
          at: hit ? (hit.tagName + ' ' + (hit.dataset.tocRow || hit.dataset.tocToggle || hit.className || '')).slice(0, 90) : null};
}"""


def paced(t0, i):
    """Wait for the i-th tap's slot (i * PACE after t0)."""
    delay = t0 + i * PACE - time.monotonic()
    if delay > 0:
        time.sleep(delay)


def press(pg, flow, chapter):
    """A real touch / click on the row (its toggle with ?toc=two),
    without Playwright's per-action waits: WebKit's waits spread a burst over
    ~0.75 s per tap, which is not the speed of a person tapping."""
    point = pg.evaluate(POINT, [chapter, not flow.mode.one])
    if not point or not point["hits"]:
        raise AssertionError(f"row {chapter} not under its tap point: {point}")
    (pg.touchscreen.tap if flow.touch else pg.mouse.click)(point["x"], point["y"])


def traced(state, next_chapter, mode):
    """The default mode's agreed trace (lib/toc.py, Phase 2): a one-tap action
    marks the row it taps on the entry being left, so Back to that entry shows
    the row tapped next. ?toc=two has no trace."""
    if not mode.one or next_chapter is None:
        return state
    return {**state, "lit": ["sec:" + next_chapter]}


def did(effect, chapter, before, after):
    row = "sec:" + chapter
    if after["lit"] != [row] or not after["menu"]:
        return False
    if effect == "open":
        return chapter in after["open"] and after["url"].endswith(f"/{chapter}/")
    if effect == "highlight":
        return chapter not in after["open"] and after["url"] == before["url"]
    if effect == "expand":
        return chapter in after["open"] and after["url"] == before["url"]
    return chapter not in after["open"] and after["url"] == before["url"]  # collapse


def same(a, b):
    return all(a[k] == b[k] for k in KEYS)


def start(browser, options, mode):
    context = browser.new_context(locale="ru-RU", service_workers="block", **options)
    context.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
    context.add_init_script(COUNTER)
    pg = context.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    flow = Contents(pg, mode, options.get("has_touch", False))
    mode.start(pg, f"{BASE}/{LANG}/")
    pg.wait_for_timeout(600)
    flow.contents()
    flow.activate(flow.group(PART))
    pg.wait_for_timeout(1200)
    chapters = pg.locator(".mobile-menu [data-toc-chapter]").evaluate_all(
        "es => es.filter(e => e.offsetParent).map(e => e.dataset.tocChapter)")
    return context, pg, flow, errors, chapters


def burst(pg, flow, steps):
    """Tap every planned row at the pace. Each state is read at the end of its
    tap's slot, once settled. Returns (states, seconds, write offset, broke):
    broke = (action number, reason) when a row could no longer be tapped."""
    since = pg.evaluate("window.__qaWrites.length")
    states = [flow.state()]
    broke = None
    t0 = time.monotonic()
    for i, (chapter, _) in enumerate(steps):
        paced(t0, i)
        try:
            press(pg, flow, chapter)
        except Exception as error:  # noqa: BLE001
            broke = (i + 1, f"{type(error).__name__}: {str(error).splitlines()[0]}")
            break
        paced(t0 - 0.03, i + 1)
        states.append(flow.state())
    seconds = time.monotonic() - t0
    pg.wait_for_timeout(1200)
    return states, seconds, since, broke


def burst_checks(dev, pg, flow, errors, tag, steps, states, seconds, since, broke):
    """The limits every burst must keep; raises when the burst broke off."""
    n = len(steps)
    w = writes(pg, since)
    info(dev, f"{tag}: took {seconds:.1f} s; app {w['app']} (push {w['app_push']}, replace {w['app_replace']}), Next.js {w['next']}")
    chk(dev, f"{tag}: app history writes <= actions", w["app"] <= n, str(w))
    quota = pg.evaluate("window.__qaQuota")
    chk(dev, f"{tag}: no history quota error", not quota and not any("history." in e for e in errors), str(quota[:2] + errors[:2]))
    if broke:
        chk(dev, f"{tag}: every row did its action", False, f"the burst broke off at action {broke[0]} of {n}: {broke[1]}")
        raise AssertionError(f"burst broke off at action {broke[0]}")
    chk(dev, f"{tag}: one history entry per action", states[-1]["history"] - states[0]["history"] == n,
        str(states[-1]["history"] - states[0]["history"]))
    bad = [(i + 1, s[0], s[1]) for i, s in enumerate(steps) if not did(s[1], s[0], states[i], states[i + 1])]
    chk(dev, f"{tag}: every row did its action", not bad, str(bad[:3]))


def case_a(browser, dev, options, mode):
    context, pg, flow, errors, chapters = start(browser, options, mode)
    tag = f"A {SHORT} actions"
    try:
        chk(dev, f"{tag}: setup - the part's chapters are listed", len(chapters) >= 3, str(chapters))
        steps = plan(chapters, mode, SHORT)
        states, seconds, since, broke = burst(pg, flow, steps)
        burst_checks(dev, pg, flow, errors, tag, steps, states, seconds, since, broke)
        bad = []
        for i in range(SHORT - 1, -1, -1):
            flow.nav("back", native=i % 2 == 1)
            got, want = flow.state(), traced(states[i], steps[i][0], mode)
            if not same(got, want):
                bad.append({"press": SHORT - i, "got": {k: got[k] for k in KEYS}, "want": {k: want[k] for k in KEYS}})
        chk(dev, f"{tag}: Back x{SHORT} restores every URL, highlight and open list", not bad, str(bad[:2]))
        bad = []
        for i in range(1, SHORT + 1):
            flow.nav("forward", native=i % 2 == 0)
            got, want = flow.state(), traced(states[i], steps[i][0] if i < SHORT else None, mode)
            if not same(got, want):
                bad.append({"press": i, "got": {k: got[k] for k in KEYS}, "want": {k: want[k] for k in KEYS}})
        chk(dev, f"{tag}: Forward x{SHORT} restores every URL, highlight and open list", not bad, str(bad[:2]))
    except Exception as error:  # noqa: BLE001
        chk(dev, f"{tag}: scenario completed", False, f"{type(error).__name__}: {str(error).splitlines()[0]}")
    finally:
        context.close()


def case_b(browser, dev, options, mode):
    context, pg, flow, errors, chapters = start(browser, options, mode)
    tag = f"B {STRESS} actions in {STRESS_SECONDS:.0f} s"
    try:
        steps = plan(chapters, mode, STRESS)
        states, seconds, since, broke = burst(pg, flow, steps)
        chk(dev, f"{tag}: setup - the actions were tapped within {STRESS_SECONDS:.0f} s", broke or seconds <= STRESS_SECONDS, f"{seconds:.1f} s")
        burst_checks(dev, pg, flow, errors, tag, steps, states, seconds, since, broke)

        # Back burst: Next.js writes once per press; the app must not add any.
        since = pg.evaluate("window.__qaWrites.length")
        for _ in range(BACK_BURST):
            pg.evaluate("history.back()")
            pg.wait_for_timeout(60)
        pg.wait_for_timeout(1500)
        w = writes(pg, since)
        info(dev, f"Back burst x{BACK_BURST}: app {w['app']}, Next.js {w['next']}")
        got, want = flow.state(), traced(states[STRESS - BACK_BURST], steps[STRESS - BACK_BURST][0], mode)
        chk(dev, f"Back burst x{BACK_BURST}: app adds no history writes", w["app"] == 0, str(w))
        chk(dev, f"Back burst x{BACK_BURST}: lands on the step {BACK_BURST} actions back", same(got, want),
            str({k: got[k] for k in KEYS}) + " want " + str({k: want[k] for k in KEYS}))
        since = pg.evaluate("window.__qaWrites.length")
        for _ in range(BACK_BURST):
            pg.evaluate("history.forward()")
            pg.wait_for_timeout(60)
        pg.wait_for_timeout(1500)
        w = writes(pg, since)
        info(dev, f"Forward burst x{BACK_BURST}: app {w['app']}, Next.js {w['next']}")
        got = flow.state()
        chk(dev, f"Forward burst x{BACK_BURST}: back on the last action's step", same(got, states[-1]),
            str({k: got[k] for k in KEYS}) + " want " + str({k: states[-1][k] for k in KEYS}))
        chk(dev, f"{tag}: no history quota error after the Back / Forward bursts",
            not pg.evaluate("window.__qaQuota") and not any("history." in e for e in errors),
            str(pg.evaluate("window.__qaQuota")[:2] + errors[:2]))
        chapter = next(c for c in chapters if c not in got["open"])
        before = flow.state()
        press(pg, flow, chapter)
        pg.wait_for_timeout(500)
        after = flow.state()
        effect = "open" if mode.one else "highlight"
        chk(dev, f"{tag}: a row still does its action afterwards", did(effect, chapter, before, after)
            and after["history"] == before["history"] + 1, str({k: after[k] for k in KEYS}))
    except Exception as error:  # noqa: BLE001
        chk(dev, f"{tag}: scenario completed", False, f"{type(error).__name__}: {str(error).splitlines()[0]}")
    finally:
        context.close()


def main():
    with sync_playwright() as p:
        for dev, eng, opts in qa.devices(DEVICES):
            browser = getattr(p, eng).launch()

            def body(mode):
                case_a(browser, dev, opts, mode)
                case_b(browser, dev, opts, mode)

            qa.run_toc_modes(body)
            browser.close()
    print(f"{sum(res)}/{len(res)} passed")
    sys.exit(0 if res and all(res) else 1)


main()
