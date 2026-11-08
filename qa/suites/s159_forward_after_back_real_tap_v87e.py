"""V87e — Vraja Lila's choice Nr.3 B (msg 7789, verbatim: «3 - вариант B …») as a REAL tap, the way a reader does it.
Menu -> another chapter -> browser «назад»: the menu is open over the previous page and «Вперёд» is ACTIVE; a real tap on «Вперёд»
(touchscreen tap on phones / iPad, mouse click on desktop, at the button's centre; NO tap anywhere else on the page first —
while the contents are open the bottom bar is on screen without the bars' `data-shown`, and a tap in the middle of the page
lands on a contents row and chooses that place) closes the menu and opens the page the reader left with «назад».
«Вернуться» goes back the same way. Waits for the STATE (page / menu), not for a fixed time.
Why it exists: 08.11.2026 the live check (scripts/state/v87_live.py) reported pixel7 3b as failing; the cause was the check's own
"show the bars" tap in the middle of the page, which on the Pixel 7 hit the row «#vigraha-fourth-form» of the open contents
(history.pushState with that hash cut the path off) — the app was right. This suite keeps the REAL reader's tap for 3b on all devices.
# tehniskais slieksnis Lipikāra, nav S noteikums: waits up to 8000 ms for the settled state.
usage: python s159_forward_after_back_real_tap_v87e.py <base-url>
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
A = "vigraha-tattva"
LANG = "ru-iast"
results = []

STATE = """() => { const b = (s) => document.querySelector('[data-reader-step=' + s + ']');
  return {page: location.pathname.replace(/\\/$/, '').split('/').pop(), hash: location.hash, menu: !!document.querySelector('.mobile-menu[data-open]'),
          barsShown: !!document.querySelector('.reader-chrome[data-shown]'),
          back: b('back') ? !b('back').disabled : null, fwd: b('forward') ? !b('forward').disabled : null}; }"""
PATH_IDS = "(() => { try { const p = JSON.parse(sessionStorage.getItem('ap.pathSteps') || 'null'); return p ? p.ids.join() + '@' + p.at + '/' + p.ids.length : ''; } catch (e) { return ''; } })()"


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:900]}", flush=True)


def real_tap(pg, touch, sel):
    """The tap of a reader: at the element's centre, only if it is the topmost element there."""
    r = pg.evaluate("""(s) => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect();
      const x = b.left + b.width / 2, y = b.top + b.height / 2; const t = document.elementFromPoint(x, y);
      return {x, y, top: !!t && (t === e || e.contains(t))}; }""", sel)
    if not r or not r["top"]:
        return False
    if touch:
        pg.touchscreen.tap(r["x"], r["y"])
    else:
        pg.mouse.click(r["x"], r["y"])
    return True


def wait_state(pg, cond, timeout=8000):
    """Wait for the state (cond is a JS expression over `s`), then let the page settle for one frame."""
    try:
        pg.wait_for_function("(() => { const s = (" + STATE + ")(); return " + cond + "; })()", timeout=timeout)
    except Exception:
        pass
    return pg.evaluate(STATE)


def go(pg, url):
    before = pg.evaluate(PATH_IDS) if pg.url.startswith("http") else ""
    pg.goto(url, wait_until="networkidle")
    pg.wait_for_function(f"(() => {{ const now = {PATH_IDS}; if (!now) return false; const [a, b] = now.split('@'); const [at, n] = b.split('/'); "
                         f"return now !== {json.dumps(before)} && +at === n - 1; }})()", timeout=20000)


def run(browser, dev, opts):
    touch = bool(opts.get("has_touch"))
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerLayout','page')}catch(e){}")
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    tag = f"{dev}/{LANG}"
    try:
        for p in ("", A):
            go(pg, f"{BASE}/{LANG}/{p + '/' if p else ''}")
        pg.wait_for_timeout(900)
        # the contents open with the bars' own button (reader bars are shown by a tap in the middle of the cover/page: that is
        # the reader's way to the button; the menu then stays open, nothing else is tapped on the page afterwards)
        for _ in range(4):
            if pg.evaluate("!!document.querySelector('.reader-chrome[data-shown]')"):
                break
            pg.mouse.click(pg.viewport_size["width"] // 2, pg.viewport_size["height"] // 2)
            pg.wait_for_timeout(450)
        opened = real_tap(pg, touch, "[data-reader-action=contents]")
        pg.wait_for_selector(".mobile-menu[data-open]", timeout=8000)
        pg.wait_for_timeout(700)
        target = pg.evaluate("""() => { const cur = location.pathname.replace(/\\/$/, '').split('/').pop();
          const a = [...document.querySelectorAll('.mobile-menu[data-open] aside nav a[href]')].find((x) => { const h = x.getAttribute('href');
            const last = h.split('#')[0].replace(/\\/$/, '').split('/').pop(); return !h.includes('#') && last && last !== cur && last !== 'ru-iast' && !x.hasAttribute('data-toc-cover'); });
          if (!a) return null; const last = a.getAttribute('href').replace(/\\/$/, '').split('/').pop(); a.scrollIntoView(); a.click(); return last; }""")
        s1 = wait_state(pg, f"s.page === {json.dumps(target)} && !s.menu")
        pg.go_back()
        s2 = wait_state(pg, f"s.page === {json.dumps(A)} && s.menu && s.fwd === true")
        check(tag, "3a menu -> other chapter -> browser «назад»: the menu is open over the previous page and «Вперёд» is ACTIVE",
              opened and target and s1["page"] == target and s2["page"] == A and s2["menu"] and s2["fwd"] is True, {"target": target, "afterPick": s1, "afterBack": s2})
        # the reader taps «Вперёд» itself — nothing else is tapped on the page before it
        tapped = real_tap(pg, touch, "[data-reader-step=forward]")
        s3 = wait_state(pg, f"s.page === {json.dumps(target)} && !s.menu")
        check(tag, "3b real tap on «Вперёд»: the menu closes and the page left with «назад» opens, not the previous one",
              tapped and s3["page"] == target and not s3["menu"] and s3["hash"] == "" and s3["fwd"] is False, {"tapped": tapped, "state": s3})
        # «Вернуться»: the bars are shown after a step (V82), the button is tapped as it is
        tapped_b = real_tap(pg, touch, "[data-reader-step=back]")
        s4 = wait_state(pg, f"s.page === {json.dumps(A)} && !s.menu")
        check(tag, "3c real tap on «Вернуться»: back to the previous page, menu closed, «Вперёд» active again",
              tapped_b and s4["page"] == A and not s4["menu"] and s4["fwd"] is True, {"tapped": tapped_b, "state": s4})
        check(tag, "3 no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(tag, "3 scenario ran", False, str(error)[:300])
    finally:
        c.close()


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "pixel7", "ipad-portrait", "desktop"]):
        b = getattr(p, eng).launch()
        run(b, dev, opts)
        b.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
