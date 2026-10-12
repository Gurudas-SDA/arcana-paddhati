"""History writes under fast tapping (UI §9.2, §9.3, §10.1, §10.2, §11; Phase 3 item 1).

WebKit allows 100 pushState/replaceState calls per 10 s; beyond that it throws
and the Contents stop opening rows. Every pushState/replaceState is counted at
History.prototype. A write is the app's when a frame of its call stack comes
from an app chunk (found in out/ by the app's history keys); the rest are
Next.js's own router writes (one after each app write that changes the URL,
one after each Back / Forward), reported separately.

Per device and Contents mode (default one-tap, ?toc=two):
  A  17 actions (the burst that broke WebKit in Phase 2), each state recorded:
     app writes <= actions, Next.js writes only for the actions that change the
     URL (expand / collapse / highlight change none), one history entry per
     action, no quota error, every row did its action - every other tap lands
     near the row's right edge, which must do the same as a tap 60 px in (§11:
     the whole row is the target) -, Back x17 and Forward x17 restore every
     URL, highlight and open list; every entry has its own apId, never reused
     after Back and a new step; scroll and view live in one record per entry.
  B  40 actions and a burst of 20 Back presses inside one 10 s window (one
     tap per 200 ms): at most 85 history writes in all, the same limits as A,
     the Back burst reaches the step 20 actions back and adds no app write,
     20 Forward presses come back, then one more row action still works.
  C  The entry records never break the book: storage blocked (memory only),
     a reload in the middle of the steps, an entry from before apId (its view
     in history.state), entries evicted past the 200-record cap.

Pacing: Playwright's own taps on WebKit take ~0.75 s each (actionability
waits), which spreads a burst out and hides the quota defect. The suite drives
real touches / clicks (page.touchscreen / page.mouse) at a person's pace -
250 ms in A, 200 ms in B - at a point checked to be on the row.

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
SHORT, STRESS, BACK_BURST = 17, 40, 20
PACE_A, PACE_B = 0.25, 0.2
WINDOW_SECONDS, WINDOW_WRITES = 10.0, 85
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
      log.push({kind, app: app(), t: performance.now()});
      try { return native.call(this, data, unused, url); }
      catch (e) { errors.push(kind + ': ' + e.message); throw e; }
    };
  }
})()""".replace("__APP__", json.dumps(APP_CHUNKS))

# Storage that fails like a blocked / full one (case C): every access throws.
NO_STORAGE = r"""(() => {
  const P = Storage.prototype;
  for (const name of ['getItem', 'setItem', 'removeItem', 'key', 'clear']) {
    const native = P[name];
    P[name] = function (...args) {
      if (this === window.sessionStorage) throw new DOMException('blocked by QA', 'SecurityError');
      return native.apply(this, args);
    };
  }
})()"""


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} [toc={qa.TOC_MODE_NAME}] {'' if ok else info}"[:900], flush=True)


def info(dev, name):
    print(f"  [INFO] {dev} {name} [toc={qa.TOC_MODE_NAME}]", flush=True)


def count(w):
    return dict(app=sum(x["app"] for x in w), app_push=sum(x["app"] and x["kind"] == "push" for x in w),
                app_replace=sum(x["app"] and x["kind"] == "replace" for x in w), next=sum(not x["app"] for x in w))


def writes(pg, since, until=None):
    return count(pg.evaluate(f"window.__qaWrites.slice({since}{', ' + str(until) if until is not None else ''})"))


def quota_errors(pg, errors):
    return pg.evaluate("window.__qaQuota")[:2] + [e for e in errors if "history." in e][:2]


def plan(chapters, mode, n):
    """[(chapter, expected effect)] - n row taps cycling through the part's chapters."""
    cycle = ("open", "collapse") if mode.one else ("highlight", "expand", "collapse")
    out = []
    while len(out) < n:
        for c in chapters:
            out.extend((c, effect) for effect in cycle)
    return out[:n]


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


def show(s):
    return {k: s[k] for k in KEYS}


def traced(state, next_chapter, mode):
    """The default mode's agreed trace (lib/toc.py, Phase 2): a one-tap action
    marks the row it taps on the entry being left, so Back to that entry shows
    the row tapped next. ?toc=two has no trace."""
    if not mode.one or next_chapter is None:
        return state
    return {**state, "lit": ["sec:" + next_chapter]}


def paced(t0, i, pace):
    """Wait for the i-th tap's slot (i * pace after t0)."""
    delay = t0 + i * pace - time.monotonic()
    if delay > 0:
        time.sleep(delay)


POINT = """async ([id, edge]) => {
  // Where a person would tap: once the list has stopped moving (the app
  // scrolls an opened list into view), at most ~200 ms.
  const frame = () => new Promise(r => requestAnimationFrame(r));
  const list = document.querySelector('.mobile-menu .toc-scroll');
  for (let i = 0, last = -1; list && i < 12; i++) {
    await frame();
    if (list.scrollTop === last) break;
    last = list.scrollTop;
  }
  const row = document.querySelector(`.mobile-menu [data-toc-chapter="${id}"]`);
  if (!row) return null;
  // The row's own box (the button and, with ?toc=two, its toggle - one target).
  const box = row.parentElement;
  // The app may still move the list (its reveal retry runs 120 ms after an
  // expand): measure again until the row really is under the point.
  let x = 0, y = 0, hit = null, hits = false;
  for (let i = 0; i < 15 && !hits; i++) {
    row.scrollIntoView({block: 'nearest', behavior: 'instant'});
    await frame();
    const r = row.getBoundingClientRect();
    // 60 px in (as Contents.tap), or near the right edge: 8 px inside the
    // list's visible width, clear of its scrollbar. WebKit's overlay scrollbar
    // takes no width but catches hits, so up to 16 px are kept clear for it.
    const right = list ? list.getBoundingClientRect().left + list.clientWidth : r.right;
    const bar = list ? Math.max(16, list.offsetWidth - list.clientWidth) : 0;
    x = edge ? Math.min(r.right, right + (list ? list.offsetWidth - list.clientWidth : 0) - bar) - 8 : r.left + Math.min(60, r.width / 2);
    y = r.top + r.height / 2;
    hit = document.elementFromPoint(x, y);
    hits = !!hit && box.contains(hit);
  }
  return {x, y, hits,
          at: hit ? (hit.tagName + ' ' + (hit.dataset.tocRow || hit.dataset.tocToggle || hit.className || '')).slice(0, 90) : null};
}"""


def press(pg, flow, chapter, edge=False):
    """A real touch / click on the row, without Playwright's per-action waits."""
    point = pg.evaluate(POINT, [chapter, edge])
    if not point or not point["hits"]:
        raise AssertionError(f"row {chapter} not under its tap point: {point}")
    (pg.touchscreen.tap if flow.touch else pg.mouse.click)(point["x"], point["y"])


def entry_id(pg):
    return pg.evaluate("(history.state && history.state.apId) || null")


def start(browser, options, mode, scripts=()):
    context = browser.new_context(locale="ru-RU", service_workers="block", **options)
    context.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
    context.add_init_script(COUNTER)
    for script in scripts:
        context.add_init_script(script)
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


def burst(pg, flow, steps, pace, edges=None, settle=1200):
    """Tap every planned row at the pace. Each state (and entry id) is read at
    the end of its tap's slot, once settled. Returns (states, ids, seconds,
    write offset, broke): broke = (action number, reason) when a row could no
    longer be tapped."""
    since = pg.evaluate("window.__qaWrites.length")
    states, ids = [flow.state()], [entry_id(pg)]
    broke = None
    t0 = time.monotonic()
    for i, (chapter, _) in enumerate(steps):
        paced(t0, i, pace)
        try:
            press(pg, flow, chapter, edge=bool(edges and edges[i]))
        except Exception as error:  # noqa: BLE001
            broke = (i + 1, f"{type(error).__name__}: {str(error).splitlines()[0]}")
            break
        paced(t0 - 0.03, i + 1, pace)
        states.append(flow.state())
        ids.append(entry_id(pg))
    seconds = time.monotonic() - t0
    pg.wait_for_timeout(settle)
    return states, ids, seconds, since, broke


def burst_checks(dev, pg, errors, tag, steps, states, seconds, since, broke, until=None):
    """The limits every burst must keep; raises when the burst broke off."""
    n = len(steps)
    w = writes(pg, since, until)
    info(dev, f"{tag}: took {seconds:.1f} s; app {w['app']} (push {w['app_push']}, replace {w['app_replace']}), Next.js {w['next']}")
    chk(dev, f"{tag}: app history writes <= actions", w["app"] <= n, str(w))
    opens = sum(effect == "open" for _, effect in steps[:len(states) - 1])
    chk(dev, f"{tag}: Next.js writes only for actions that change the URL (expand / collapse / highlight: none)",
        w["next"] == opens, f"Next.js {w['next']}, URL-changing actions {opens}")
    quota = quota_errors(pg, errors)
    chk(dev, f"{tag}: no history quota error", not quota, str(quota))
    if broke:
        chk(dev, f"{tag}: every row did its action", False, f"the burst broke off at action {broke[0]} of {n}: {broke[1]}")
        raise AssertionError(f"burst broke off at action {broke[0]}")
    chk(dev, f"{tag}: one history entry per action", states[-1]["history"] - states[0]["history"] == n,
        str(states[-1]["history"] - states[0]["history"]))
    bad = [(i + 1, s[0], s[1]) for i, s in enumerate(steps) if not did(s[1], s[0], states[i], states[i + 1])]
    chk(dev, f"{tag}: every row did its action", not bad, str(bad[:3]))
    return w


def case_a(browser, dev, options, mode):
    context, pg, flow, errors, chapters = start(browser, options, mode)
    tag = f"A {SHORT} actions"
    try:
        chk(dev, f"{tag}: setup - the part's chapters are listed", len(chapters) >= 3, str(chapters))
        steps = plan(chapters, mode, SHORT)
        edges = [i % 2 == 1 for i in range(SHORT)]
        states, ids, seconds, since, broke = burst(pg, flow, steps, PACE_A, edges)
        burst_checks(dev, pg, errors, tag, steps, states, seconds, since, broke)
        bad = [(i + 1, s[0], s[1]) for i, s in enumerate(steps) if edges[i] and not did(s[1], s[0], states[i], states[i + 1])]
        chk(dev, f"{tag}: a tap near the row's right edge does the same as one 60 px in (§11)",
            not bad and any(edges) and not all(edges), str(bad[:3]))
        chk(dev, f"{tag}: apId - every entry has its own id", all(ids) and len(set(ids)) == len(ids), str(ids))
        bad = []
        for i in range(SHORT - 1, -1, -1):
            flow.nav("back", native=i % 2 == 1)
            got, want = flow.state(), traced(states[i], steps[i][0], mode)
            if not same(got, want) or entry_id(pg) != ids[i]:
                bad.append({"press": SHORT - i, "got": show(got), "want": show(want)})
        chk(dev, f"{tag}: Back x{SHORT} restores every URL, highlight and open list", not bad, str(bad[:2]))
        bad = []
        for i in range(1, SHORT + 1):
            flow.nav("forward", native=i % 2 == 0)
            got, want = flow.state(), traced(states[i], steps[i][0] if i < SHORT else None, mode)
            if not same(got, want) or entry_id(pg) != ids[i]:
                bad.append({"press": i, "got": show(got), "want": show(want)})
        chk(dev, f"{tag}: Forward x{SHORT} restores every URL, highlight and open list", not bad, str(bad[:2]))
        for _ in range(3):
            flow.nav("back")
        chapter = steps[-3][0]
        press(pg, flow, chapter)
        pg.wait_for_timeout(500)
        new = entry_id(pg)
        chk(dev, f"{tag}: apId - Back x3 and a new step get a new id, never one used before",
            new and new not in ids, f"{new} in {ids}")
        stored = pg.evaluate("""() => { try { return {
            entries: JSON.parse(sessionStorage.getItem('ap.entries') || '[]'),
            legacy: sessionStorage.getItem('ap.scroll') }; } catch (e) { return null; } }""")
        records = dict(stored["entries"]) if stored else {}
        ok = stored and stored["legacy"] is None and all(i in records for i in ids[1:]) and all(
            set(r) <= {"key", "scroll", "at", "view"} for r in records.values())
        chk(dev, f"{tag}: one record per entry holds its scroll and view (no separate scroll store)", ok,
            str({"legacy": stored and stored["legacy"], "missing": [i for i in ids[1:] if i not in records][:3]}))
    except Exception as error:  # noqa: BLE001
        chk(dev, f"{tag}: scenario completed", False, f"{type(error).__name__}: {str(error).splitlines()[0]}")
    finally:
        context.close()


def case_b(browser, dev, options, mode):
    context, pg, flow, errors, chapters = start(browser, options, mode)
    tag = f"B {STRESS} actions + {BACK_BURST} Back in {WINDOW_SECONDS:.0f} s"
    try:
        steps = plan(chapters, mode, STRESS)
        t_first = pg.evaluate("performance.now()")
        states, ids, seconds, since, broke = burst(pg, flow, steps, PACE_B, settle=0)
        until = pg.evaluate("window.__qaWrites.length")
        if not broke:
            # Straight on: the Back burst in the same 10 s window.
            for _ in range(BACK_BURST):
                pg.evaluate("history.back()")
                pg.wait_for_timeout(60)
        t_end = pg.evaluate("performance.now()")
        pg.wait_for_timeout(1500)
        log = pg.evaluate(f"window.__qaWrites.slice({since})")
        span = (t_end - t_first) / 1000
        total = len(log)
        times = sorted(x["t"] for x in log)
        peak = max((sum(1 for u in times if t <= u < t + WINDOW_SECONDS * 1000) for t in times), default=0)
        w_all = count(log)
        info(dev, f"{tag}: {span:.1f} s from the first tap to the last Back; {total} writes "
                  f"(app {w_all['app']}, Next.js {w_all['next']}); peak in any 10 s window {peak}")
        chk(dev, f"{tag}: setup - all of it inside one {WINDOW_SECONDS:.0f} s window", broke or span <= WINDOW_SECONDS, f"{span:.1f} s")
        chk(dev, f"{tag}: at most {WINDOW_WRITES} history writes in the window", total <= WINDOW_WRITES, f"{total} writes")
        burst_checks(dev, pg, errors, tag, steps, states, seconds, since, broke, until)
        w = writes(pg, until)
        info(dev, f"Back burst x{BACK_BURST}: app {w['app']}, Next.js {w['next']}")
        got, want = flow.state(), traced(states[STRESS - BACK_BURST], steps[STRESS - BACK_BURST][0], mode)
        chk(dev, f"Back burst x{BACK_BURST}: app adds no history writes", w["app"] == 0, str(w))
        chk(dev, f"Back burst x{BACK_BURST}: lands on the step {BACK_BURST} actions back", same(got, want),
            f"{show(got)} want {show(want)}")
        since = pg.evaluate("window.__qaWrites.length")
        for _ in range(BACK_BURST):
            pg.evaluate("history.forward()")
            pg.wait_for_timeout(60)
        pg.wait_for_timeout(1500)
        w = writes(pg, since)
        info(dev, f"Forward burst x{BACK_BURST}: app {w['app']}, Next.js {w['next']}")
        got = flow.state()
        chk(dev, f"Forward burst x{BACK_BURST}: back on the last action's step", same(got, states[-1]),
            f"{show(got)} want {show(states[-1])}")
        quota = quota_errors(pg, errors)
        chk(dev, f"{tag}: no history quota error after the Back / Forward bursts", not quota, str(quota))
        chapter = next(c for c in chapters if c not in got["open"])
        before = flow.state()
        press(pg, flow, chapter)
        pg.wait_for_timeout(500)
        after = flow.state()
        effect = "open" if mode.one else "highlight"
        chk(dev, f"{tag}: a row still does its action afterwards", did(effect, chapter, before, after)
            and after["history"] == before["history"] + 1, str(show(after)))
    except Exception as error:  # noqa: BLE001
        chk(dev, f"{tag}: scenario completed", False, f"{type(error).__name__}: {str(error).splitlines()[0]}")
    finally:
        context.close()


def steps_back(pg, flow, states, ids, steps, mode, n, exact=True):
    """Back n times; returns the presses whose URL / menu (and, if exact,
    highlight / open lists) differ from the recorded steps."""
    bad = []
    for k in range(1, n + 1):
        i = len(states) - 1 - k
        flow.nav("back", native=k % 2 == 0)
        got, want = flow.state(), traced(states[i], steps[i][0], mode)
        keys = KEYS if exact else ("url", "menu")
        if any(got[key] != want[key] for key in keys):
            bad.append({"press": k, "got": show(got), "want": show(want)})
    return bad


def case_c(browser, dev, options, mode):
    tag = "C records"
    # C1 storage blocked: records in memory only; within the page every step restores exactly.
    context, pg, flow, errors, chapters = start(browser, options, mode, scripts=(NO_STORAGE,))
    try:
        steps = plan(chapters, mode, 4)
        states, ids, _, _, broke = burst(pg, flow, steps, PACE_A)
        bad = steps_back(pg, flow, states, ids, steps, mode, 4) if not broke else ["broke"]
        chk(dev, f"{tag}: storage blocked - every row acts, Back restores every step, nothing throws",
            not broke and not bad and not errors, str((broke, bad[:2], errors[:2])))
    except Exception as error:  # noqa: BLE001
        chk(dev, f"{tag}: storage blocked - scenario completed", False, f"{type(error).__name__}: {str(error).splitlines()[0]}")
    finally:
        context.close()

    context, pg, flow, errors, chapters = start(browser, options, mode)
    try:
        steps = plan(chapters, mode, 4)
        states, ids, _, _, broke = burst(pg, flow, steps, PACE_A)
        # C2 reload in the middle: the records come back from sessionStorage.
        flow.nav("back")
        pg.reload(wait_until="networkidle")
        pg.wait_for_timeout(1200)
        got, want = flow.state(), traced(states[3], steps[3][0], mode)
        bad = [] if same(got, want) else [{"after reload": show(got), "want": show(want)}]
        bad += steps_back(pg, flow, states[:4], ids, steps, mode, 2)
        chk(dev, f"{tag}: reload mid-history - the step and every Back keep URL, highlight and open lists",
            not broke and not bad and not errors, str((broke, bad[:2], errors[:2])))

        # C3 an entry from before apId: its view in history.state, no record.
        pg.evaluate("""() => {
          const s = {...history.state}, id = s.apId;
          const list = JSON.parse(sessionStorage.getItem('ap.entries') || '[]');
          const rec = (list.find(([k]) => k === id) || [null, {}])[1];
          Object.assign(s, rec.view || {}); delete s.apId;
          sessionStorage.setItem('ap.entries', JSON.stringify(list.filter(([k]) => k !== id)));
          history.replaceState(s, '');
        }""")
        before = flow.state()
        pg.reload(wait_until="networkidle")
        pg.wait_for_timeout(1200)
        got = flow.state()
        chk(dev, f"{tag}: an entry without apId keeps its highlight and open lists from history.state",
            same(got, before) and not errors, f"{show(got)} want {show(before)} {errors[:2]}")

        # C4 past the 200-record cap: the steps' records are evicted.
        pg.evaluate("""() => {
          const list = JSON.parse(sessionStorage.getItem('ap.entries') || '[]');
          for (let i = 0; i < 200; i++) list.push(['qa-' + i, {view: {}}]);
          sessionStorage.setItem('ap.entries', JSON.stringify(list));
        }""")
        pg.reload(wait_until="networkidle")
        pg.wait_for_timeout(1200)
        here = flow.state()
        press(pg, flow, chapters[-1])   # one more record: the oldest ones go
        pg.wait_for_timeout(500)
        flow.nav("back")
        got = flow.state()
        bad = [] if (got["url"], got["menu"]) == (here["url"], here["menu"]) else [{"back": show(got), "want": show(here)}]
        bad += steps_back(pg, flow, states[:2], ids, steps, mode, 1, exact=False)
        evicted = pg.evaluate("""() => { const ids = JSON.parse(sessionStorage.getItem('ap.entries') || '[]').map(([k]) => k);
          return {size: ids.length, mine: ids.filter(k => !k.startsWith('qa-')).length}; }""")
        chk(dev, f"{tag}: past the 200-record cap - Back still reaches every step's URL and menu, nothing throws",
            not bad and not errors and evicted["size"] <= 200, str((bad[:2], errors[:2], evicted)))
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
                case_c(browser, dev, opts, mode)

            qa.run_toc_modes(body)
            browser.close()
    print(f"{sum(res)}/{len(res)} passed")
    sys.exit(0 if res and all(res) else 1)


main()
