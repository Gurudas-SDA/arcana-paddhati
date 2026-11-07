"""V87 — Vraja Lila's choices for the small places of V83 (V86 file «Варианты по мелким местам»; Vraja msg 7789, verbatim:
«3 - вариант B; 4 - вариант A; 5 - вариант B; 6 - вариант C»). Interface author, «Стандарты» 0а, S approval not needed.

Nr.3 (B). Menu -> another chapter -> browser «назад»: the menu opens over the previous page and «Вперёд» is ACTIVE. Pressing it:
the menu closes, the page the reader left with «назад» opens (Эпиграф -> menu -> Гуру-парампара -> «назад» -> «Вперёд» = Гуру-парампара).
Then «Вернуться» goes back the same way, no extra step. Nothing ahead (opened directly): the button is inactive.
Nr.4 (A): NOT CHANGED (cover tap and «Продолжить чтение» behave as before) — nothing to test beyond s03/s07.
Nr.5 (B). «Аа» open: the bottom bar is above the dimming and not dimmed; «Вернуться» closes «Аа» and makes ONE step, «Вперёд» too if active.
An inactive button: nothing happens, «Аа» stays open. Phone and desktop. The rest of the page is still dimmed.
Nr.6 (C). Phone in landscape (iPhone 14 844x390, Pixel 7 915x412): the menu's head, search, tabs and the «Обложка» row scroll together with the
list, so after scrolling the whole menu height is the list; the bottom bar stays visible, the last row scrolls to the end and is not covered;
the ✕ is reachable after scrolling back. Portrait, iPad and desktop do not change.
# tehniskais slieksnis Lipikāra, nav S noteikums: waits 1500-2500 ms for the settled state; 2 px tolerance for rects.
usage: python s158_path_menu_aa_landscape_v87.py <base-url>
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
B = "daily-duties-brahma-muhurta"
results = []


def LP(lang):
    return "" if lang == "en" else "/" + lang


STATE = """() => { const b = (s) => document.querySelector('[data-reader-step=' + s + ']');
  let ids = 0, at = -1; try { const p = JSON.parse(sessionStorage.getItem('ap.pathSteps') || 'null'); if (p) { ids = p.ids.length; at = p.at; } } catch (e) {}
  return {page: location.pathname.replace(/\\/$/, '').split('/').pop(), hash: location.hash, menu: !!document.querySelector('.mobile-menu[data-open]'),
          panel: !!document.querySelector('.reader-panel'),
          back: b('back') ? !b('back').disabled : null, fwd: b('forward') ? !b('forward').disabled : null, ids, at}; }"""
PATH_IDS = "(() => { try { const p = JSON.parse(sessionStorage.getItem('ap.pathSteps') || 'null'); return p ? p.ids.join() + '@' + p.at + '/' + p.ids.length : ''; } catch (e) { return ''; } })()"


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:900]}", flush=True)


def show_bars(pg):
    for _ in range(4):
        if pg.evaluate("!!document.querySelector('.reader-chrome[data-shown]')"):
            return
        pg.mouse.click(pg.viewport_size["width"] // 2, pg.viewport_size["height"] // 2)
        pg.wait_for_timeout(450)


def open_menu(pg):
    show_bars(pg)
    pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('[data-reader-action=contents]').click()")
    pg.wait_for_selector(".mobile-menu[data-open]", timeout=5000)
    pg.wait_for_timeout(700)


def pick(pg, frag):
    pg.evaluate("""(f) => { const a = [...document.querySelectorAll('.mobile-menu[data-open] aside nav a[href]')].find(x => x.getAttribute('href').includes(f));
      a.scrollIntoView(); a.click(); }""", frag)
    pg.wait_for_timeout(2500)


def pick_other(pg):
    """Choose in the open contents a visible chapter link (no #) other than the current page; returns the page name."""
    name = pg.evaluate("""() => { const cur = location.pathname.replace(/\\/$/, '').split('/').pop();
      const a = [...document.querySelectorAll('.mobile-menu[data-open] aside nav a[href]')].find((x) => { const h = x.getAttribute('href');
        const last = h.split('#')[0].replace(/\\/$/, '').split('/').pop(); return !h.includes('#') && last && last !== cur && last !== 'ru-iast' && !x.hasAttribute('data-toc-cover'); });
      if (!a) return null; const last = a.getAttribute('href').replace(/\\/$/, '').split('/').pop(); a.scrollIntoView(); a.click(); return last; }""")
    pg.wait_for_timeout(2500)
    return name


def step(pg, kind):
    pg.evaluate(f"document.querySelector('[data-reader-step={kind}]').click()")
    pg.wait_for_timeout(2500)


def go(pg, url):
    before = pg.evaluate(PATH_IDS) if pg.url.startswith("http") else ""
    pg.goto(url, wait_until="networkidle")
    pg.wait_for_function(f"(() => {{ const now = {PATH_IDS}; if (!now) return false; const [a, b] = now.split('@'); const [at, n] = b.split('/'); "
                         f"return now !== {json.dumps(before)} && +at === n - 1; }})()", timeout=20000)


def ctx(browser, opts):
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerLayout','page')}catch(e){}")
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    return c, pg, errors


def fresh(browser, opts, lang, pages=("", A, B)):
    c, pg, errors = ctx(browser, opts)
    for p in pages:
        go(pg, f"{BASE}{LP(lang)}/{p + '/' if p else ''}")
    pg.wait_for_timeout(900)
    return c, pg, errors


def run_nr3(browser, dev, opts, lang):
    tag = f"{dev}/{lang}"
    # A (Эпиграф-like page) -> menu -> B -> browser back -> menu open over A, «Вперёд» active -> B
    c, pg, errors = fresh(browser, opts, lang, ("", A))
    try:
        open_menu(pg)
        T = pick_other(pg)
        s1 = pg.evaluate(STATE)
        pg.go_back()
        pg.wait_for_timeout(2500)
        s2 = pg.evaluate(STATE)
        check(tag, "3a menu -> other chapter -> browser «назад»: the menu is open over the previous page and «Вперёд» is ACTIVE",
              T and s1["page"] == T and s2["page"] == A and s2["menu"] and s2["fwd"] is True, {"target": T, "afterPick": s1, "afterBack": s2})
        step(pg, "forward")
        s3 = pg.evaluate(STATE)
        check(tag, "3b «Вперёд»: the menu closes and the page left with «назад» opens",
              s3["page"] == T and not s3["menu"] and s3["fwd"] is False, s3)
        show_bars(pg)
        step(pg, "back")
        s4 = pg.evaluate(STATE)
        check(tag, "3c «Вернуться» goes back the same way: previous page, menu closed, no extra step in the path",
              s4["page"] == A and not s4["menu"] and s4["ids"] == s3["ids"] and s4["fwd"] is True, {"s3": s3, "s4": s4})
        check(tag, "3 no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(tag, "3 scenario ran", False, str(error)[:300])
    finally:
        c.close()
    # nothing ahead: opened directly -> menu -> browser back is not possible; the button is inactive
    c, pg, errors = ctx(browser, opts)
    try:
        go(pg, f"{BASE}{LP(lang)}/{B}/")
        pg.wait_for_timeout(900)
        show_bars(pg)
        open_menu(pg)
        s = pg.evaluate(STATE)
        check(tag, "3d nothing ahead (opened directly), menu open: «Вперёд» is inactive", s["fwd"] is False, s)
    except Exception as error:
        traceback.print_exc()
        check(tag, "3d scenario ran", False, str(error)[:300])
    finally:
        c.close()


BAR_OVER = """(sel) => { const b = document.querySelector(sel); if (!b) return null; const r = b.getBoundingClientRect();
  const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  const bar = document.querySelector('.reader-bar-bottom'); const bd = document.querySelector('.reader-panel-backdrop');
  const mid = document.elementFromPoint(window.innerWidth / 2, 20);
  return {onButton: !!e && (e === b || b.contains(e)), backdrop: !!bd, pageDimmed: !!bd && (mid === bd || bd.contains(mid)),
          barBottomAboveBackdrop: !!bd && bd.getBoundingClientRect().bottom <= bar.getBoundingClientRect().top + 2}; }"""


def open_aa(pg):
    show_bars(pg)
    pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('[data-reader-action=aa]').click()")
    pg.wait_for_selector(".reader-panel", timeout=5000)
    pg.wait_for_timeout(600)


def click_btn(pg, kind):
    r = pg.evaluate(f"(() => {{ const r = document.querySelector('[data-reader-step={kind}]').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }})()")
    pg.mouse.click(r[0], r[1])
    pg.wait_for_timeout(2500)


def run_nr5(browser, dev, opts, lang):
    tag = f"{dev}/{lang}"
    c, pg, errors = fresh(browser, opts, lang)
    try:
        show_bars(pg)
        step(pg, "back")  # on A, «Вперёд» active
        open_aa(pg)
        o = pg.evaluate(BAR_OVER, "[data-reader-step=back]")
        s0 = pg.evaluate(STATE)
        check(tag, "5a «Аа» open: the bottom bar is above the dimming (not dimmed), the rest of the page is still dimmed",
              o and o["onButton"] and o["backdrop"] and o["pageDimmed"] and o["barBottomAboveBackdrop"] and s0["panel"], {"o": o, "s0": s0})
        click_btn(pg, "forward")
        s1 = pg.evaluate(STATE)
        check(tag, "5b «Вперёд» with «Аа» open: «Аа» closes and ONE step is made (to the next page)", s1["page"] == B and not s1["panel"] and not s1["menu"], s1)
        show_bars(pg)
        open_aa(pg)
        s2 = pg.evaluate(STATE)
        check(tag, "5c inactive «Вперёд» with «Аа» open: tap does nothing, «Аа» stays open", s2["fwd"] is False and s2["panel"], s2)
        click_btn(pg, "forward")
        s3 = pg.evaluate(STATE)
        check(tag, "5d after the tap on the inactive button: same page, «Аа» still open", s3["page"] == B and s3["panel"], s3)
        click_btn(pg, "back")
        s4 = pg.evaluate(STATE)
        check(tag, "5e «Вернуться» with «Аа» open: «Аа» closes and one step back (previous page), path not longer",
              s4["page"] == A and not s4["panel"] and s4["ids"] == s1["ids"] and s4["fwd"] is True, {"s1": s1, "s4": s4})
        check(tag, "5 no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(tag, "5 scenario ran", False, str(error)[:300])
    finally:
        c.close()


MENU_RECTS = """() => {
  const asideEl = document.querySelector('.mobile-menu[data-open] aside'); const bar = document.querySelector('.reader-bar-bottom');
  const r = (e) => e ? e.getBoundingClientRect() : null; const a = r(asideEl); const bb = r(bar);
  const scroller = [asideEl, ...asideEl.querySelectorAll('*')].filter((e) => e.scrollHeight > e.clientHeight + 4 && /(auto|scroll)/.test(getComputedStyle(e).overflowY));
  const rows = [...asideEl.querySelectorAll('.toc-scroll > ul > li')]; const last = rows[rows.length - 1];
  return {aside: a && [a.top, a.bottom], bar: bb && [bb.top, bb.bottom], vh: innerHeight,
          scrollers: scroller.map((e) => e.className.toString().slice(0, 30)),
          search: r(asideEl.querySelector('input[type=search]')) && r(asideEl.querySelector('input[type=search]')).bottom,
          tabs: r(asideEl.querySelector('[data-sidebar-tabs]')) && r(asideEl.querySelector('[data-sidebar-tabs]')).bottom,
          cover: r(asideEl.querySelector('[data-toc-cover]')) && r(asideEl.querySelector('[data-toc-cover]')).bottom,
          close: r(asideEl.querySelector('.sidebar-close')) && [r(asideEl.querySelector('.sidebar-close')).top, r(asideEl.querySelector('.sidebar-close')).bottom],
          last: last && [r(last).top, r(last).bottom]}; }"""
SCROLL_ALL = """(to) => { const asideEl = document.querySelector('.mobile-menu[data-open] aside');
  [asideEl, ...asideEl.querySelectorAll('*')].filter((e) => e.scrollHeight > e.clientHeight + 4 && /(auto|scroll)/.test(getComputedStyle(e).overflowY))
    .forEach((e) => { e.scrollTop = to === 'end' ? 1e6 : 0; }); }"""


def run_nr6(browser, dev, opts, lang, land):
    tag = f"{dev}{'-landscape' if land else ''}/{lang}"
    c, pg, errors = fresh(browser, opts, lang, ("", A))
    try:
        open_menu(pg)
        pg.evaluate(SCROLL_ALL, "end")
        pg.wait_for_timeout(500)
        m = pg.evaluate(MENU_RECTS)
        if land:
            top = m["aside"][0]
            check(tag, "6a after scrolling the head, search, tabs and «Обложка» are scrolled away (the whole menu height is the list)",
                  m["search"] <= top + 2 and m["tabs"] <= top + 2 and m["cover"] <= top + 2, m)
            check(tag, "6b the bottom bar is visible, the last row scrolls to the end and is not covered by it",
                  m["bar"][0] < m["vh"] and m["aside"][1] <= m["bar"][0] + 2 and m["last"][1] <= m["bar"][0] + 2 and m["last"][1] >= m["aside"][1] - 80, m)
            pg.evaluate(SCROLL_ALL, "top")
            pg.wait_for_timeout(500)
            m2 = pg.evaluate(MENU_RECTS)
            check(tag, "6c scrolled back: the ✕ is reachable (inside the menu)", m2["close"] and m2["close"][0] >= m2["aside"][0] - 2 and m2["close"][1] <= m2["aside"][1] + 2, m2)
        else:
            top = m["aside"][0]
            check(tag, "6d (unchanged) portrait / iPad / desktop: the cover row, search and tabs stay fixed when the list scrolls",
                  m["cover"] > top + 2 and m["search"] > top + 2, m)
        check(tag, "6 no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(tag, "6 scenario ran", False, str(error)[:300])
    finally:
        c.close()


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "pixel7", "ipad-portrait", "desktop"]):
        b = getattr(p, eng).launch()
        for lang in ("ru-iast", "en"):
            run_nr3(b, dev, opts, lang)
            run_nr5(b, dev, opts, lang)
            run_nr6(b, dev, opts, lang, False)
        b.close()
    for dev, eng, opts in qa.devices(["iphone14", "pixel7"]):
        o = dict(opts)
        vp = o["viewport"]
        o["viewport"] = {"width": 844, "height": 390} if dev == "iphone14" else {"width": 915, "height": 412}
        b = getattr(p, eng).launch()
        for lang in ("ru-iast", "en"):
            run_nr6(b, dev, o, lang, True)
        b.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
