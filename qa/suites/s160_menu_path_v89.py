"""V89 — Vraja Lila's choices from V85b (msg 7859, 08.11.2026, verbatim):
 «1 A» — when «Вернуться»/«Вперёд» slide the menu out, the list scrolls so that the highlighted chapter (and subsection) is in the visible part;
 «2 B» — choosing a chapter with the arrow (a chapter with subsections): the menu stays open, BUT the choice is written into the path (pathSteps),
         so «Вернуться»/«Вперёд» go along it;
 «3 A» — expanding / collapsing a section in the contents does NOT write an entry into the browser history;
 «4 C» — after «Вернуться»/«Вперёд» the buttons do not turn grey during the transition; instead a short, unobtrusive transition indicator
         (attribute data-stepping on the bar + a small dot under the button);
 «5 B» — reading by scrolling: the menu scrolls automatically so that both the chapter's row and the highlighted subsection are visible.
Every step is a REAL tap on the button / row itself (touchscreen tap on phones and iPad, mouse click on desktop, at the element's centre) —
never a tap in the middle of the page while the contents are open. Waits for the STATE (page / menu), not for a fixed time.
# tehniskais slieksnis Lipikāra, nav S noteikums: waits up to 8000 ms for a settled state; 40 ms sampling of the buttons for 1.8 s.
usage: python s160_menu_path_v89.py <base-url>
"""
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
LANG = "ru-iast"
A, B, C, D = "vigraha-tattva", "daily-duties-brahma-muhurta", "maha-abhiseka", "daily-deity-schedule"
results = []

STATE = """() => { const b = (s) => document.querySelector('[data-reader-step=' + s + ']'); let ps = null;
  try { ps = JSON.parse(sessionStorage.getItem('ap.pathSteps') || 'null'); } catch (e) {}
  return {page: location.pathname.replace(/\\/$/, '').split('/').pop(), hash: location.hash, menu: !!document.querySelector('.mobile-menu[data-open]'),
          back: b('back') ? !b('back').disabled : null, fwd: b('forward') ? !b('forward').disabled : null,
          stepping: !!document.querySelector('.reader-bar-bottom[data-stepping]'),
          bc: b('back') ? getComputedStyle(b('back')).color : null, fc: b('forward') ? getComputedStyle(b('forward')).color : null,
          at: ps ? ps.at : null, n: ps && ps.ids ? ps.ids.length : null, pushes: window.__pushes || 0}; }"""
# the contents list: rows in/out of its visible part; `lit` = rows with aria-current
ROWS = """() => { const m = document.querySelector('.mobile-menu[data-open]'); if (!m) return null;
  const sc = m.querySelector('.toc-scroll'); const sr = sc.getBoundingClientRect();
  const inv = (e) => { const b = e.getBoundingClientRect(); return b.top >= sr.top - 2 && b.bottom <= sr.bottom + 2; };
  const lit = [...m.querySelectorAll('[data-toc-row][aria-current]')].map((e) => {
    const sub = e.dataset.tocRow.startsWith('sub:'); const li = sub && e.closest('ul') ? e.closest('ul').closest('li') : null; const ch = li ? li.querySelector('[data-toc-chapter]') : null;
    return {id: e.dataset.tocRow, vis: inv(e), chapter: ch ? ch.dataset.tocRow : null, chapterVis: ch ? inv(ch) : null}; });
  return {st: Math.round(sc.scrollTop), sh: Math.round(sr.height), lit}; }"""
INIT = """try { localStorage.setItem('ap.readerHintSeen','1'); localStorage.setItem('installDismissed','true'); localStorage.setItem('ap.readerLayout','page'); } catch (e) {}
(() => { try { window.__pushes = 0; const o = history.pushState; history.pushState = function () { window.__pushes++; return o.apply(this, arguments); }; } catch (e) {} })();"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:1100]}", flush=True)


def state(pg):
    for _ in range(4):
        try:
            return pg.evaluate(STATE)
        except Exception:
            pg.wait_for_timeout(300)
    return {"page": "?", "menu": False, "back": None, "fwd": None, "stepping": False, "at": None, "n": None, "pushes": 0}


def wait_state(pg, cond, timeout=8000):
    try:
        pg.wait_for_function("(() => { const s = (" + STATE + ")(); return " + cond + "; })()", timeout=timeout)
    except Exception:
        pass
    return state(pg)


def real_tap(pg, touch, sel, scroll=False):
    """The tap of a reader, at the element's centre, once it is the topmost element there (up to 2 s)."""
    r = None
    for _ in range(20):
        r = pg.evaluate("""([s, sc]) => { const e = document.querySelector(s); if (!e) return null; if (sc) e.scrollIntoView({block: 'center'});
          const b = e.getBoundingClientRect(); const x = b.left + b.width / 2, y = b.top + b.height / 2; const t = document.elementFromPoint(x, y);
          return {x, y, top: !!t && (t === e || e.contains(t))}; }""", [sel, scroll])
        if r and r["top"]:
            break
        pg.wait_for_timeout(100)
    if not r or not r["top"]:
        return False
    (pg.touchscreen.tap if touch else pg.mouse.click)(r["x"], r["y"])
    return True


def go(pg, page):
    pg.goto(f"{BASE}/{LANG}/{page + '/' if page else ''}", wait_until="networkidle")
    pg.wait_for_function("!!document.querySelector('[data-reader-step=back]')", timeout=20000)
    pg.wait_for_timeout(900)


def bars(pg, touch):
    for _ in range(4):
        if pg.evaluate("!!document.querySelector('.reader-chrome[data-shown]')") or state(pg)["menu"]:
            return
        pg.mouse.click(pg.viewport_size["width"] // 2, pg.viewport_size["height"] // 2)
        pg.wait_for_timeout(450)


def open_menu(pg, touch):
    if state(pg)["menu"]:
        return True
    bars(pg, touch)
    ok = real_tap(pg, touch, "[data-reader-action=contents]")
    try:
        pg.wait_for_selector(".mobile-menu[data-open]", timeout=8000)
    except Exception:
        return False
    pg.wait_for_timeout(900)
    return ok


def close_menu(pg, touch):
    if not state(pg)["menu"]:
        return
    real_tap(pg, touch, ".mobile-menu[data-open] aside button[aria-label]")
    wait_state(pg, "!s.menu")


def step(pg, touch, which):
    """A real tap on the button; when the bar is not on screen yet (it is shown by the reader's own tap on the page), show it and tap again."""
    ok = False
    for _ in range(3):
        if not state(pg)["menu"]:
            bars(pg, touch)
        ok = real_tap(pg, touch, f"[data-reader-step={which}]")
        if ok:
            break
        pg.wait_for_timeout(400)
    return ok


def lit_visible(pg):
    """Every highlighted row of the open menu is in the visible part, and so is the chapter row of a highlighted subsection."""
    r = pg.evaluate(ROWS)
    if not r or not r["lit"]:
        return False, r
    ok = all(x["vis"] and (x["chapterVis"] is not False) for x in r["lit"])
    return ok, r


def run(browser, dev, opts):
    touch = bool(opts.get("has_touch"))
    tag = f"{dev}/{LANG}"

    def fresh(pages):
        c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
        c.add_init_script(INIT)
        pg = c.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        for p in pages:
            go(pg, p)
        return c, pg, errors

    # ---- 1 A: the menu slid out by «Вернуться»/«Вперёд» shows the highlighted chapter (and subsection) ---------------------------------
    c = None
    try:
        c, pg, errors = fresh(["", A, B])
        for rid in (f"sec:{C}", f"sec:{D}", f"sec:{C}"):
            open_menu(pg, touch)
            real_tap(pg, touch, f'.mobile-menu[data-open] [data-toc-row="{rid}"]', scroll=True)
            wait_state(pg, f"s.page === {json.dumps(rid[4:])}", 8000)
            pg.wait_for_timeout(600)
            close_menu(pg, touch)
        slid, bad = 0, []
        for which in ("back", "back", "back", "forward", "forward", "forward"):
            s = state(pg)
            if (which == "back" and not s["back"]) or (which == "forward" and not s["fwd"]):
                bars(pg, touch)
            before = state(pg)["page"]
            step(pg, touch, which)
            s = wait_state(pg, f"s.page !== {json.dumps(before)}", 6000)
            pg.wait_for_timeout(900)
            if s["menu"]:
                slid += 1
                ok, rows = lit_visible(pg)
                if not ok:
                    bad.append({"step": which, "page": s["page"], "rows": rows})
                close_menu(pg, touch)
        check(tag, "1A every time «Вернуться»/«Вперёд» slid the menu out, the highlighted chapter (and subsection) is in the visible part of the list", not bad, {"slid": slid, "bad": bad[:2]})
        # (the system / browser «назад» onto a menu entry keeps the list's exact offset - rule 10, s04 (d); only the buttons bring the highlight into view)
        check(tag, "1 no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(tag, "1 scenario ran", False, str(error)[:300])
    finally:
        if c:
            c.close()

    # ---- 2 B: a chapter chosen with the arrow keeps the menu open, and the choice is a step of the path ------------------------------
    c = None
    try:
        c, pg, errors = fresh(["", A, B])
        n0 = state(pg)["n"]
        open_menu(pg, touch)
        target = pg.evaluate("""(cur) => { const e = [...document.querySelectorAll('.mobile-menu[data-open] [data-toc-chapter]')].find((x) => x.dataset.tocChapter !== cur
            && x.getAttribute('aria-expanded') === 'false' && x.dataset.tocChapter !== 'maha-abhiseka'); return e ? e.dataset.tocChapter : null; }""", B)
        if not target:  # every chapter with subsections shown is open: open a group first
            target = pg.evaluate("""() => { const e = document.querySelector('.mobile-menu[data-open] [data-toc-chapter]'); return e ? e.dataset.tocChapter : null; }""")
        tapped = real_tap(pg, touch, f'.mobile-menu[data-open] [data-toc-chapter="{target}"]', scroll=True)
        s1 = wait_state(pg, f"s.page === {json.dumps(target)}", 8000)
        pg.wait_for_timeout(700)
        s1 = state(pg)
        check(tag, "2B choosing a chapter with the arrow: the page opens and the menu stays open", tapped and s1["page"] == target and s1["menu"], {"target": target, "state": s1})
        check(tag, "2B the choice is written into the path (one step more, the place is the new chapter)", s1["n"] == (n0 or 0) + 1 and s1["at"] == (s1["n"] or 0) - 1, {"n0": n0, "state": s1})
        bars(pg, touch)
        step(pg, touch, "back")
        s2 = wait_state(pg, f"s.page === {json.dumps(B)} && !s.menu", 8000)
        check(tag, "2B «Вернуться» goes back along the path to the previous page (menu closed)", s2["page"] == B and not s2["menu"], s2)
        wait_state(pg, "s.fwd === true", 8000)  # the button's state follows ~100 ms after the page changes
        step(pg, touch, "forward")
        s3 = wait_state(pg, f"s.page === {json.dumps(target)}", 8000)
        check(tag, "2B «Вперёд» reaches the chapter chosen with the arrow", s3["page"] == target, s3)
        check(tag, "2 no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(tag, "2 scenario ran", False, str(error)[:300])
    finally:
        if c:
            c.close()

    # ---- 3 A: expanding / collapsing a section writes nothing into the browser history -------------------------------------------------
    c = None
    try:
        c, pg, errors = fresh(["", A, B])
        open_menu(pg, touch)
        p0 = state(pg)["pushes"]
        h0 = pg.evaluate("history.length")
        groups = pg.evaluate("[...document.querySelectorAll('.mobile-menu[data-open] [data-toc-group]')].map((e) => e.dataset.tocGroup)")
        done = 0
        for g in (groups[:2] * 2)[:4]:
            if real_tap(pg, touch, f'.mobile-menu[data-open] [data-toc-group="{g}"]', scroll=True):
                done += 1
            pg.wait_for_timeout(500)
        p1, h1 = state(pg)["pushes"], pg.evaluate("history.length")
        check(tag, "3A expanding / collapsing sections in the contents: no entry is written into the browser history", done >= 3 and p1 == p0 and h1 == h0,
              {"toggles": done, "pushState": p1 - p0, "history.length": [h0, h1]})
        close_menu(pg, touch)
        check(tag, "3A closing the contents after the toggles needs no extra «назад» (page still the same)", state(pg)["page"] == B and not state(pg)["menu"], state(pg))
        check(tag, "3 no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(tag, "3 scenario ran", False, str(error)[:300])
    finally:
        if c:
            c.close()

    # ---- 4 C: after «Вернуться»/«Вперёд» the buttons do not turn grey; a short indicator instead ------------------------------------
    c = None
    try:
        c, pg, errors = fresh(["", A, B, C])
        # mid-path: «Вернуться» once first (not sampled), then the sampled step has both buttons enabled before AND after it
        bars(pg, touch)
        step(pg, touch, "back")
        wait_state(pg, f"s.page === {json.dumps(B)}", 8000)
        pg.wait_for_timeout(1200)
        for mode in ("step", "step after reload"):
            if mode != "step":
                pg.reload(wait_until="networkidle")
                pg.wait_for_timeout(900)
            bars(pg, touch)
            s0 = state(pg)
            which = "back"
            step(pg, touch, which)
            t0 = time.time()
            samples = []
            while time.time() - t0 < 1.8:
                try:
                    samples.append(pg.evaluate(STATE))
                except Exception:
                    pass  # the document is being replaced (a step across documents)
                pg.wait_for_timeout(30)
            fin = samples[-1] if samples else {}
            # grey = the button LOOKS inactive (its colour is not the enabled colour of the same button before the step)
            grey = [x for x in samples if (s0["back"] and fin.get("back") and x["back"] is False and x["bc"] != s0["bc"])
                    or (s0["fwd"] and fin.get("fwd") and x["fwd"] is False and x["fc"] != s0["fc"])]
            ind = any(x["stepping"] for x in samples)
            check(tag, f"4C [{mode}] a button that is enabled before and after the step does not turn grey during it", bool(samples) and not grey and bool(s0["back"]),
                  {"before": {k: s0.get(k) for k in ("page", "back", "fwd")}, "samples": len(samples), "grey": len(grey), "final": {k: fin.get(k) for k in ("page", "back", "fwd")}})
            check(tag, f"4C [{mode}] a short transition indicator is shown and is gone when the step is over", ind and not fin.get("stepping"), {"seen": ind, "afterwards": fin.get("stepping")})
            if mode == "step":
                pg.wait_for_timeout(500)
        check(tag, "4 no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(tag, "4 scenario ran", False, str(error)[:300])
    finally:
        if c:
            c.close()

    # ---- 5 B: reading by scrolling - the menu shows both the chapter's row and the highlighted subsection ----------------------------
    c = None
    try:
        c, pg, errors = fresh(["", A, D])
        # daily-deity-schedule has 13 subsections; «raja-bhoga-offering» is the 9th: chapter row + 9 subsection rows fit in the list at once,
        # but the subsection centred alone (the old way) leaves the chapter's row above the visible part
        sub = "raja-bhoga-offering"
        pg.evaluate("(id) => { const e = document.getElementById(id); if (e) e.scrollIntoView({block: 'start'}); }", sub)
        pg.wait_for_timeout(1200)
        rows = {"sub": sub}
        open_menu(pg, touch)
        pg.wait_for_timeout(600)
        ok, r = lit_visible(pg)
        lit_sub = bool(r and any(x["id"].startswith("sub:") for x in r["lit"]))
        check(tag, "5B the lit subsection is the one being read (case occurred)", bool(sub) and lit_sub, {"plan": rows, "sub": sub, "rows": r})
        check(tag, "5B the menu shows both the chapter's row and the highlighted subsection", bool(sub) and ok, r)
        check(tag, "5 no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(tag, "5 scenario ran", False, str(error)[:300])
    finally:
        if c:
            c.close()


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "pixel7", "ipad-portrait", "desktop"]):
        b = getattr(p, eng).launch()
        run(b, dev, opts)
        b.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
