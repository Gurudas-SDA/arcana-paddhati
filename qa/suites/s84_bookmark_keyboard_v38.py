"""V38 — the bookmark's name window above the iPhone keyboard (Vraja Lila msg 1315–1317, 22.10.2026 23:09–00:18;
saskarnes autors, «Стандарты» 0а; ‼️ СРОЧНО).

Rule text (Vraja Lila's remark, as passed on — nodots-izpildei 22.10 00:20 п.1, verbatim):
 «ОКНО ЗАКЛАДКИ на iPhone 13 («New bookmark» и «Rename the bookmark»): клавиатура + полоса iOS «AutoFill Contact»
  ПЕРЕКРЫВАЮТ кнопки Cancel/Confirm. Окно — над клавиатурой (visualViewport/позиция по видимой области), кнопки всегда
  видны; полосу AutoFill убрать по возможности (autocomplete="off", name/id поля не похожи на контакт).»
Criterion (verbatim): «iPhone 13/SE: при клавиатуре Cancel/Confirm видны и нажимаются».

The keyboard cannot be opened in Playwright, so it is emulated the way iOS reports it: window.visualViewport shrinks
(the layout viewport — innerHeight — stays), and a «resize» event of visualViewport is sent.
 # tehniskais slieksnis Lipikāra, nav S noteikums: keyboard + AutoFill bar + status bar covering 433 px of 844
 # (iPhone 13 / 14, 390×844 — measured on Vraja Lila's screenshot msg 1315: the bar starts at 458 pt, the status bar
 # ends at 47 pt) and 324 px of 667 (iPhone SE: 216 keys + 44 suggestions + 44 AutoFill bar + 20 status bar).

Checks, per device, for «Новая закладка» (the ribbon) and «Переименовать» (the pencil in «Закладки»):
  A  with the keyboard: «Отмена» and «Подтвердить» lie wholly inside the visible area (visualViewport), the whole card too;
  B  they are pressable there: a tap on «Отмена» closes the window, a tap on «Подтвердить» saves (the new / new name);
  C  the field does not look like a contact to iOS: autocomplete="off", no name-like word in its id / name, a search-type
     field (Safari's contact AutoFill skips it) without the search field's ✕;
  D  without the keyboard the window stays in the middle of the screen (V34).
usage: python s84_bookmark_keyboard_v38.py <base-url>
"""
import json
import os
import re
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from toc import Contents  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
CH = "daily-duties-brahma-muhurta"
OTHER = "arcana-procedure"
KEYBOARD = {"iphone14": 433, "iphone-se": 324, "desktop": 433}
SEED = [{"id": "b-kb", "section": OTHER, "anchor": "2-svagata", "block": 0, "lang": "ru-iast", "time": 1792000000000, "name": "Утро"}]
MENU = ".mobile-menu[data-open]"
DLG = "[data-bookmark-dialog]"
CONTACT = re.compile(r"name|contact|fname|lname|first|last|full|user|mail|tel|phone|address|nick", re.I)
results = []

# iOS-like keyboard: visualViewport.height shrinks, innerHeight stays.
FAKE_VV = """(() => {
  const et = new EventTarget(); const st = {kb: 0};
  const fake = {
    get width() { return innerWidth; }, get height() { return innerHeight - st.kb; },
    offsetTop: 0, offsetLeft: 0, pageTop: 0, pageLeft: 0, scale: 1, onresize: null, onscroll: null,
    addEventListener: (...a) => et.addEventListener(...a), removeEventListener: (...a) => et.removeEventListener(...a),
    dispatchEvent: (e) => et.dispatchEvent(e),
  };
  Object.defineProperty(window, 'visualViewport', {get: () => fake, configurable: true});
  window.__kb = (h) => { st.kb = h; et.dispatchEvent(new Event('resize')); };
})();"""

GEOM = """() => { const d = document.querySelector('[data-bookmark-dialog]'); if (!d) return null;
  const vv = window.visualViewport; const top = vv.offsetTop, bottom = vv.offsetTop + vv.height;
  const box = (e) => { if (!e) return null; const r = e.getBoundingClientRect(); return {top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right)}; };
  const card = box(d.querySelector('[role=dialog]')), cancel = box(d.querySelector('[data-bookmark-dialog-cancel]')),
        confirm = box(d.querySelector('[data-bookmark-dialog-confirm]'));
  const inside = (b) => !!b && b.top >= top - 0.5 && b.bottom <= bottom + 0.5 && b.left >= 0 && b.right <= innerWidth + 0.5;
  const hit = (sel) => { const e = d.querySelector(sel); if (!e) return false; const r = e.getBoundingClientRect();
    const x = r.left + r.width / 2, y = r.top + r.height / 2; return y < bottom && e.contains(document.elementFromPoint(x, y)); };
  const inp = d.querySelector('[data-bookmark-dialog-input]');
  // the search field's ✕ hidden: a stylesheet rule for this field's ::-webkit-search-cancel-button with display none
  // (getComputedStyle cannot read that pseudo-element).
  const noX = (() => { if (!inp) return false; const want = (sel) => sel.split(',').some((one) => { const [base, pseudo] = one.trim().split('::');
      if (pseudo !== '-webkit-search-cancel-button') return false; try { return inp.matches(base); } catch (e) { return false; } });
    for (const sh of document.styleSheets) { let rules; try { rules = sh.cssRules; } catch (e) { continue; }
      const walk = (list) => { for (const r of list) { if (r.cssRules && walk(r.cssRules)) return true;
        if (r.selectorText && want(r.selectorText) && r.style && r.style.display === 'none') return true; } return false; };
      if (walk(rules)) return true; } return false; })();
  const cr = card && d.querySelector('[role=dialog]').getBoundingClientRect();
  return {mode: d.getAttribute('data-bookmark-dialog'), visible: [Math.round(top), Math.round(bottom)], card, cancel, confirm,
          inCard: inside(card), inCancel: inside(cancel), inConfirm: inside(confirm),
          hitCancel: hit('[data-bookmark-dialog-cancel]'), hitConfirm: hit('[data-bookmark-dialog-confirm]'),
          cy: cr ? Math.round(cr.top + cr.height / 2 - innerHeight / 2) : null,
          field: inp ? {id: inp.id, name: inp.getAttribute('name') || '', type: inp.type, ac: inp.getAttribute('autocomplete'),
                        formAc: inp.form ? inp.form.getAttribute('autocomplete') : null, noX} : null}; }"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


def stored(pg):
    return pg.evaluate("(JSON.parse(localStorage.getItem('ap.bookmarks') || 'null') || {items: []}).items")


def tap(pg, loc, touch, wait=400):
    (loc.tap if touch else loc.click)()
    pg.wait_for_timeout(wait)


def press_ribbon(pg, touch, flow):
    flow.bars()
    btn = pg.locator("[data-reader-action=bookmark]")
    if pg.locator(".reader-chrome[data-shown]").count():
        tap(pg, btn, touch, wait=500)
    else:
        btn.evaluate("b => b.click()")
        pg.wait_for_timeout(500)


def keyboard_checks(pg, dev, what, kb):
    g0 = pg.evaluate(GEOM)
    if g0 is None:
        check(dev, f"{what}: the window opens", False)
        return False
    check(dev, f"D {what}: without the keyboard the window is in the middle", abs(g0["cy"]) <= 40, g0["cy"])
    f = g0["field"] or {}
    check(dev, f"C {what}: the field is not a contact for iOS (autocomplete off, no name-like id/name, search type, no ✕)",
          f.get("ac") == "off" and not CONTACT.search(f.get("id", "")) and not CONTACT.search(f.get("name", ""))
          and f.get("type") == "search" and f.get("noX") is True, f)
    pg.evaluate(f"window.__kb({kb})")
    pg.wait_for_timeout(500)
    g = pg.evaluate(GEOM)
    check(dev, f"A {what}: keyboard up — «Отмена» and «Подтвердить» (and the card) inside the visible area",
          g["inCard"] and g["inCancel"] and g["inConfirm"], {k: g[k] for k in ("visible", "card", "cancel", "confirm")})
    check(dev, f"B {what}: keyboard up — both buttons are the top element at their middle (pressable)",
          g["hitCancel"] and g["hitConfirm"], {k: g[k] for k in ("hitCancel", "hitConfirm")})
    return True


def run(browser, dev, opts):
    touch = opts.get("has_touch", False)
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    c.add_init_script(FAKE_VV)
    c.add_init_script("if (!sessionStorage.getItem('qaSeeded')) { localStorage.setItem('ap.readerHintSeen','1');"
                      "localStorage.setItem('installDismissed','true');"
                      f"localStorage.setItem('ap.bookmarks', JSON.stringify({json.dumps({'v': 1, 'items': SEED}, ensure_ascii=False)}));"
                      "sessionStorage.setItem('qaSeeded','1'); }")
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    kb = KEYBOARD[dev]
    try:
        pg.goto(f"{BASE}/ru-iast/{CH}/", wait_until="networkidle")
        pg.wait_for_timeout(1500)
        flow = Contents(pg, qa.TocMode("default"), touch)

        # «Новая закладка»: «Отмена» with the keyboard up, then «Подтвердить»
        press_ribbon(pg, touch, flow)
        if keyboard_checks(pg, dev, "«Новая закладка»", kb):
            n = len(stored(pg))
            tap(pg, pg.locator("[data-bookmark-dialog-cancel]"), touch)
            check(dev, "B «Новая закладка»: «Отмена» pressed with the keyboard up closes, nothing set",
                  pg.locator(DLG).count() == 0 and len(stored(pg)) == n, len(stored(pg)))
            pg.evaluate("window.__kb(0)")
            press_ribbon(pg, touch, flow)
            pg.evaluate(f"window.__kb({kb})")
            pg.wait_for_timeout(400)
            tap(pg, pg.locator("[data-bookmark-dialog-confirm]"), touch)
            check(dev, "B «Новая закладка»: «Подтвердить» pressed with the keyboard up saves the bookmark",
                  pg.locator(DLG).count() == 0 and len(stored(pg)) == n + 1, len(stored(pg)))
            pg.evaluate("window.__kb(0)")

        # «Переименовать» from the pencil in «Закладки»
        pg.evaluate("document.querySelector('.app-main').scrollTop = 0")
        pg.wait_for_timeout(400)
        flow.contents()
        tab = pg.locator(f"{MENU} [data-sidebar-tab=bookmarks]")
        if tab.count() and tab.get_attribute("aria-selected") != "true":
            tap(pg, tab, touch)
        tap(pg, pg.locator(f"{MENU} [data-bookmark-id=b-kb] [data-bookmark-rename]"), touch)
        if keyboard_checks(pg, dev, "«Переименовать»", kb):
            pg.locator("[data-bookmark-dialog-input]").fill("Утро V38")
            tap(pg, pg.locator("[data-bookmark-dialog-confirm]"), touch)
            names = {b["id"]: b.get("name") for b in stored(pg)}
            check(dev, "B «Переименовать»: «Подтвердить» pressed with the keyboard up saves the new name",
                  pg.locator(DLG).count() == 0 and names.get("b-kb") == "Утро V38", names)
        check(dev, "no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(dev, "scenario ran", False, str(error)[:300])
    finally:
        c.close()


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "iphone-se", "desktop"]):
        b = getattr(p, eng).launch()
        run(b, dev, opts)
        b.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
