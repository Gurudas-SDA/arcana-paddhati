"""V84 — the path buttons «‹ Вернуться / Вперёд ›» after subsections chosen in the menu and «Вперёд» after the menu was opened
(Vraja Lila msg 7779, 7780, 07.11.2026; interface author, «Стандарты» 0а, S approval not needed).

Vraja msg 7779/7780 (task from Vraja's decision, verbatim from V83 findings Nr.1, Nr.2):
Nr.1 «Меню (или поиск) -> подраздел в той же главе (#taking-bath), потом ещё один (#applying-tilaka), затем Вернуться:
1-е нажатие возвращает к первому подразделу, но меню снова ОТКРЫТО ... В пути появляется лишний шаг (3 шага стали 4), и после
возврата Вперёд активна, хотя вперёд идти некуда. Логично: Вернуться = один шаг по местам, меню закрыто».
Nr.2 «Открыть главу, нажать Вернуться (мы на предыдущей, Вперёд активна), открыть меню, нажать Вперёд (меню открыто): Вперёд
активна, но ничего не делает, меню остаётся. Если меню закрыть крестиком и нажать Вперёд, меню ОТКРЫВАЕТСЯ САМО, на следующую
страницу не переходит. Либо Вперёд неактивна, либо переходит на следующую страницу» (V84 choice: it goes to the next page).
Criteria: 1) menu -> subsection -> another subsection -> «Вернуться»×3: every press is one step along the PLACES, the menu stays
closed, the path has no extra step (cover, A, B, #taking-bath, #applying-tilaka = 5 places) and «Вперёд» is inactive at the end
of the path; 2) page -> «Вернуться» -> menu -> «Вперёд» (menu open, or closed with ✕): goes to the next page of the path and
the menu is closed; never an active button that does nothing or opens the menu.
Devices: iphone14, pixel7, ipad-portrait, desktop; languages ru-iast, en.
# tehniskais slieksnis Lipikāra, nav S noteikums: waits 1500-2500 ms for the settled state.
usage: python s157_path_places_forward_v84.py <base-url>
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
    return "" if lang == "en" else "/" + lang  # English lives at the root of the book

STATE = """() => { const b = (s) => document.querySelector('[data-reader-step=' + s + ']');
  let ids = 0, at = -1; try { const p = JSON.parse(sessionStorage.getItem('ap.pathSteps') || 'null'); if (p) { ids = p.ids.length; at = p.at; } } catch (e) {}
  return {page: location.pathname.replace(/\\/$/, '').split('/').pop(), hash: location.hash, menu: !!document.querySelector('.mobile-menu[data-open]'),
          back: b('back') ? !b('back').disabled : null, fwd: b('forward') ? !b('forward').disabled : null, ids, at}; }"""
FLIPS = """() => { window.__flips = []; const st = () => !!document.querySelector('.mobile-menu[data-open]'); let last = st();
  const f = () => { const s = st(); if (s !== last) { window.__flips.push(s ? 'open' : 'closed'); last = s; } };
  new MutationObserver(f).observe(document.documentElement, {subtree: true, childList: true, attributes: true, attributeFilter: ['data-open']});
  const loop = () => { f(); requestAnimationFrame(loop); }; loop(); }"""
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


def step(pg, kind):
    pg.evaluate(f"document.querySelector('[data-reader-step={kind}]').click()")
    pg.wait_for_timeout(2500)


def go(pg, url):
    before = pg.evaluate(PATH_IDS) if pg.url.startswith("http") else ""
    pg.goto(url, wait_until="networkidle")
    pg.wait_for_function(f"(() => {{ const now = {PATH_IDS}; if (!now) return false; const [a, b] = now.split('@'); const [at, n] = b.split('/'); "
                         f"return now !== {json.dumps(before)} && +at === n - 1; }})()", timeout=20000)


def fresh(browser, opts, lang):
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerLayout','page')}catch(e){}")
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    go(pg, f"{BASE}{LP(lang)}/")
    go(pg, f"{BASE}{LP(lang)}/{A}/")
    go(pg, f"{BASE}{LP(lang)}/{B}/")
    pg.wait_for_timeout(900)
    return c, pg, errors


def run(browser, dev, opts, lang):
    tag = f"{dev}/{lang}"
    # ---- criterion 1: menu -> #taking-bath -> menu -> #applying-tilaka -> «Вернуться»×3, then «Вперёд»×3
    c, pg, errors = fresh(browser, opts, lang)
    try:
        open_menu(pg)
        pick(pg, "#taking-bath")
        s1 = pg.evaluate(STATE)
        open_menu(pg)
        pick(pg, "#applying-tilaka")
        s2 = pg.evaluate(STATE)
        check(tag, "1a two subsections chosen from the menu: menu closed, the path has 5 places (cover, A, B, 2 subsections)",
              not s1["menu"] and not s2["menu"] and s1["hash"] == "#taking-bath" and s2["hash"] == "#applying-tilaka" and s2["ids"] == 5 and s2["at"] == 4,
              {"s1": s1, "s2": s2})
        show_bars(pg)
        seq = []
        flips = []
        pg.evaluate(FLIPS)
        for _ in range(3):
            step(pg, "back")
            seq.append(pg.evaluate(STATE))
            flips.append(pg.evaluate("(window.__flips || ['reload']).splice(0)"))
        check(tag, "1b «Вернуться» x3 = three steps along the places (#taking-bath, the chapter's start, the previous page), menu closed every time",
              [(x["page"], x["hash"], x["menu"]) for x in seq] == [(B, "#taking-bath", False), (B, "", False), (A, "", False)], seq)
        # Vraja msg 7782/7783 (verbatim): «боковое меню будто мигает выезжает и заезжает при нажатии назад, а потом я не могу пойти
        # вперёд ... вперёд вообще сбивается в моменте и становится неактивным»
        check(tag, "1d «Вернуться»: the menu does not slide out and in again (no open/close flips) and «Вперёд» stays active while there is a place ahead",
              all(not [x for x in f if x != 'reload'] for f in flips) and seq[0]["fwd"] is True and seq[1]["fwd"] is True and seq[2]["fwd"] is True, {"flips": flips, "fwd": [x["fwd"] for x in seq]})
        fw = []
        for _ in range(3):
            step(pg, "forward")
            fw.append(pg.evaluate(STATE))
        check(tag, "1c «Вперёд» x3 returns along the same places, menu closed, and at the end of the path «Вперёд» is inactive",
              [(x["page"], x["hash"], x["menu"]) for x in fw] == [(B, "", False), (B, "#taking-bath", False), (B, "#applying-tilaka", False)]
              and fw[-1]["fwd"] is False and fw[-1]["ids"] == 5, fw)
        check(tag, "1 no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(tag, "1 scenario ran", False, str(error)[:300])
    finally:
        c.close()
    # ---- criterion 2: page -> «Вернуться» -> menu -> «Вперёд»; and the same with the menu closed by ✕
    for how in ("menu open", "menu closed with ✕", "no menu"):
        c, pg, errors = fresh(browser, opts, lang)
        try:
            show_bars(pg)
            step(pg, "back")
            s0 = pg.evaluate(STATE)
            if how != "no menu":
                open_menu(pg)
                if how == "menu closed with ✕":
                    pg.evaluate("document.querySelector('.mobile-menu[data-open] aside button[aria-label]').click()")
                    pg.wait_for_timeout(1500)
                    show_bars(pg)
            before = pg.evaluate(STATE)
            if before["fwd"]:
                step(pg, "forward")
            after = pg.evaluate(STATE)
            moved = after["page"] == B and not after["menu"]
            check(tag, f"2 [{how}] after «Вернуться»: «Вперёд» goes to the next page and the menu is closed (or the button is inactive: never active and idle)",
                  s0["page"] == A and s0["fwd"] and ((before["fwd"] and moved and after["ids"] == 3 and after["at"] == 2 and after["fwd"] is False)
                                                    or (not before["fwd"] and not after["menu"])),
                  {"afterBack": s0, "before": before, "after": after})
            check(tag, f"2 [{how}] «Вернуться» works after the step forward (one step to the previous page, menu closed)", True if not moved else (lambda: (step(pg, "back"), pg.evaluate(STATE))[1])()["page"] == A, "")
            check(tag, f"2 [{how}] no page errors", not errors, errors[:3])
        except Exception as error:
            traceback.print_exc()
            check(tag, f"2 [{how}] scenario ran", False, str(error)[:300])
        finally:
            c.close()


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "pixel7", "ipad-portrait", "desktop"]):
        b = getattr(p, eng).launch()
        for lang in ("ru-iast", "en"):
            run(b, dev, opts, lang)
        b.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
