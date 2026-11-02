"""V66 — «Закладки»: a bookmark can be moved up / down by a long press (Vraja Lila).
Vraja Lila, literally: «хотел бы ввести функцию в закладках, что при удерживании нажатия на них можно было бы перемещать
их вверх вниз… кейс — например я хочу их распределить по приоритетности и могу их перетянуть и сделать важные для себя
наверху списка»; «иконка с точками перед названием закладки… без checkmarks… без hairline»; variant «А — с рамкой»
(a lifted bookmark with a thin frame in the accent colour, --ap-gold), «только радиус скругления углов хотелось бы
поменьше» -> «А3» = 10 px (msg 7316).
Criteria (register V66): (1) a six-dot handle stands BEFORE the bookmark's name (a 44 px target); (2) no checkmarks, no
hairline dividers: the rows are cards with a gap; (3) the card radius is 10 px (token --ds-radius-card); (4) a long press
lifts a card with the frame in --ap-gold; (5) dragging up / down changes the order; (6) the order stays after a reload
(localStorage ap.bookmarks); (7) a plain tap still opens the bookmark and a plain swipe does not lift it; (8) the keyboard
(handle focused, arrows up / down) moves it; (9) day, night, sepia.
# tehniskais slieksnis Lipikāra, nav S noteikums: hold 600 ms (the app holds 450 ms), steps 12, settle 400 ms, gap >= 4 px
usage: python s138_bookmark_reorder_v66.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["pixel7", "iphone14", "ipad-portrait", "desktop", "mac-safari"])
NAMES = [("daily-duties-brahma-muhurta", "Брахма-мухурта"), ("maha-abhiseka", "Маха-абхишека"), ("offering-bhoga", "Подношение бхоги"),
         ("mangalacarana", "Мангалачарана"), ("parampara", "Парампара")]
HOLD_MS = 600
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


ORDER = "() => [...document.querySelectorAll('[data-bookmark-row]')].map(r => r.dataset.bookmarkId)"
GEOM = """() => [...document.querySelectorAll('[data-bookmark-row]')].map(r => { const b = r.getBoundingClientRect();
  const h = r.querySelector('[data-bookmark-handle]'); const hb = h ? h.getBoundingClientRect() : null;
  const t = r.querySelector('[data-bookmark-title]').getBoundingClientRect();
  return {id: r.dataset.bookmarkId, x: b.left, y: b.top, w: b.width, h: b.height, bottom: b.bottom,
          handle: hb ? {l: hb.left, r: hb.right, w: hb.width, h: hb.height, dots: h.querySelectorAll('circle').length} : null, titleLeft: t.left}; })"""
RADIUS = """() => { const r = document.querySelector('[data-bookmark-row]'); const cs = getComputedStyle(r);
  return {radius: cs.borderTopLeftRadius, token: getComputedStyle(document.documentElement).getPropertyValue('--ds-radius-card').trim()}; }"""
JUNK = """() => { const l = document.querySelector('[data-bookmarks-list]');
  const rows = [...l.querySelectorAll('[data-bookmark-row]')].map(r => getComputedStyle(r));
  return {checks: l.querySelectorAll('input[type=checkbox],[role=checkbox],[data-bookmark-check],hr').length,
          dividers: rows.filter(c => c.borderBottomStyle !== 'none' && c.borderTopStyle === 'none').length}; }"""
LIFT = """() => { const r = document.querySelector('[data-bookmark-lifted]'); if (!r) return null;
  const p = document.createElement('i'); p.style.color = 'var(--ap-gold)'; document.body.appendChild(p);
  const gold = getComputedStyle(p).color; p.remove();
  const cs = getComputedStyle(r);
  return {id: r.dataset.bookmarkId, border: cs.borderTopColor, gold, width: cs.borderTopWidth}; }"""
SYN = """([type, x, y]) => { const el = type === 'pointerdown' ? document.elementFromPoint(x, y) : window;
  const e = new PointerEvent(type, {pointerType: 'touch', pointerId: 7, isPrimary: true, button: 0, buttons: type === 'pointerup' ? 0 : 1,
    clientX: x, clientY: y, bubbles: true, cancelable: true}); (el || window).dispatchEvent(e); }"""


def open_tab(pg, theme=None, seed=None):
    pg.goto(f"{BASE}/ru-iast/introduction/", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    pg.evaluate("() => document.querySelector('[data-reader-action=contents]').click()")
    pg.wait_for_timeout(700)
    pg.evaluate("() => { const b = document.querySelector('[data-sidebar-tab=bookmarks]'); if (b) b.click(); }")
    pg.wait_for_selector("[data-bookmark-row]", timeout=8000)
    pg.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important}")
    pg.wait_for_timeout(300)


def new_ctx(b, opts, theme=None):
    items = [{"id": f"b{i}", "section": s, "anchor": None, "block": 0, "lang": "ru-iast", "time": 1000 - i, "name": n}
             for i, (s, n) in enumerate(NAMES)]
    c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce", **opts)
    c.add_init_script("try{if(!localStorage.getItem('ap.bookmarks')){localStorage.setItem('ap.bookmarks',JSON.stringify({v:1,items:%s}));}"
                      "localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');%s}catch(e){}"
                      % (json.dumps(items), f"localStorage.setItem('ap.readerTheme','{theme}');" if theme else ""))
    return c


def center(pg, idx, dx=None):
    g = pg.evaluate(GEOM)[idx]
    return g, (g["x"] + (dx if dx is not None else g["w"] / 2), g["y"] + g["h"] / 2)


def hold_and_drag(pg, touch, src, dst, hold=HOLD_MS, on_handle=False, release=True):
    """Hold the card `src`, drag it to the place of `dst`; returns the lifted state seen before the move."""
    geo = pg.evaluate(GEOM)
    g = geo[src]
    x = g["x"] + (g["handle"]["w"] / 2 if on_handle else g["w"] / 2)
    y = g["y"] + g["h"] / 2
    ty = geo[dst]["y"] + (4 if dst < src else geo[dst]["h"] - 4)
    if touch:
        pg.evaluate(SYN, ["pointerdown", x, y])
        pg.wait_for_timeout(hold)
        lifted = pg.evaluate(LIFT)
        for i in range(1, 13):
            pg.evaluate(SYN, ["pointermove", x, y + (ty - y) * i / 12])
            pg.wait_for_timeout(20)
        pg.wait_for_timeout(200)
        if release:
            pg.evaluate(SYN, ["pointerup", x, ty])
    else:
        pg.mouse.move(x, y)
        pg.mouse.down()
        pg.wait_for_timeout(hold if not on_handle else 150)
        lifted = pg.evaluate(LIFT)
        for i in range(1, 13):
            pg.mouse.move(x, y + (ty - y) * i / 12)
            pg.wait_for_timeout(20)
        pg.wait_for_timeout(200)
        if release:
            pg.mouse.up()
    pg.wait_for_timeout(400)
    return lifted


def stored_pos(pg):
    return pg.evaluate("() => { const v = JSON.parse(localStorage.getItem('ap.bookmarks')); return v.items.map(b => [b.id, b.pos]); }")


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        touch = bool(opts.get("has_touch"))
        br = getattr(p, eng).launch()
        try:
            c = new_ctx(br, opts)
            pg = c.new_page()
            open_tab(pg)
            geo = pg.evaluate(GEOM)
            # (1) the handle stands before the name, 44 px, six dots
            ok1 = all(g["handle"] and g["handle"]["r"] <= g["titleLeft"] + 1 and g["handle"]["w"] >= 44 and g["handle"]["h"] >= 44
                      and g["handle"]["dots"] == 6 for g in geo)
            check(dev, "handle: six dots, before the name, >= 44 px", ok1, [g["handle"] for g in geo[:2]])
            # (2) no checkmarks / hairlines: cards with a gap
            junk = pg.evaluate(JUNK)
            gaps = [geo[i + 1]["y"] - geo[i]["bottom"] for i in range(len(geo) - 1)]
            check(dev, "cards: no checkmarks, no hairline dividers, gap between", junk["checks"] == 0 and junk["dividers"] == 0 and min(gaps) >= 4,
                  {"junk": junk, "gaps": gaps})
            # (3) radius 10 px
            rd = pg.evaluate(RADIUS)
            check(dev, "card radius = 10 px (token --ds-radius-card)", rd["radius"] == "10px" and rd["token"] == "10px", rd)
            # (7) a plain tap / click opens the bookmark (no lift)
            before = pg.url
            link = pg.locator("[data-bookmark-row] a").nth(1)
            link.tap() if touch else link.click()
            pg.wait_for_timeout(1500)
            check(dev, "a plain tap opens the bookmark", NAMES[1][0] in pg.url and pg.url != before, pg.url)
            open_tab(pg)
            # (7b) a swipe / quick move before the hold does not lift
            if not touch:
                g, (x, y) = center(pg, 2)
                pg.mouse.move(x, y)
                pg.mouse.down()
                pg.mouse.move(x, y + 30, steps=4)
                pg.wait_for_timeout(HOLD_MS)
                still = pg.evaluate(LIFT)
                pg.mouse.up()
                pg.wait_for_timeout(300)
                check(dev, "a move before the hold does not lift (scroll stays free)", still is None and pg.evaluate(ORDER) == [f"b{i}" for i in range(5)], still)
                open_tab(pg)
            # (4) a long press lifts with the --ap-gold frame; (5) dragging changes the order
            lifted = hold_and_drag(pg, touch, 3, 0, release=False)
            check(dev, "long press lifts: frame in --ap-gold", bool(lifted) and lifted["border"] == lifted["gold"] and lifted["id"] == "b3", lifted)
            gap_shown = pg.evaluate("() => !!document.querySelector('[data-bookmark-gap]')")
            check(dev, "a place for the drop is shown while dragging", gap_shown)
            if touch:
                pg.evaluate(SYN, ["pointerup", 10, 10])
            else:
                pg.mouse.up()
            pg.wait_for_timeout(400)
            order = pg.evaluate(ORDER)
            check(dev, "dragging changes the order (4th card to the top)", order == ["b3", "b0", "b1", "b2", "b4"], order)
            # (6) the order stays after a reload
            pg.reload(wait_until="networkidle")
            pg.wait_for_timeout(1000)
            pg.evaluate("() => document.querySelector('[data-reader-action=contents]').click()")
            pg.wait_for_timeout(600)
            pg.evaluate("() => { const b = document.querySelector('[data-sidebar-tab=bookmarks]'); if (b) b.click(); }")
            pg.wait_for_selector("[data-bookmark-row]", timeout=8000)
            order2 = pg.evaluate(ORDER)
            check(dev, "the order stays after a reload", order2 == ["b3", "b0", "b1", "b2", "b4"], {"order": order2, "stored": stored_pos(pg)})
            # drag down too
            hold_and_drag(pg, touch, 0, 2)
            order3 = pg.evaluate(ORDER)
            check(dev, "dragging down changes the order (top card to the 3rd place)", order3 == ["b0", "b1", "b3", "b2", "b4"], order3)
            # (8) the keyboard: the handle focused, arrow up
            pg.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important}")
            pg.locator("[data-bookmark-row] [data-bookmark-handle]").nth(2).focus()
            pg.keyboard.press("ArrowUp")
            pg.wait_for_timeout(300)
            order4 = pg.evaluate(ORDER)
            focused = pg.evaluate("() => document.activeElement && document.activeElement.hasAttribute('data-bookmark-handle') && document.activeElement.closest('[data-bookmark-row]').dataset.bookmarkId")
            check(dev, "keyboard: arrow up moves the bookmark, the handle keeps the focus", order4 == ["b0", "b3", "b1", "b2", "b4"] and focused == "b3", {"order": order4, "focus": focused})
            # desktop mouse: the handle drags at once
            if not touch:
                hold_and_drag(pg, False, 1, 4, on_handle=True)
                order5 = pg.evaluate(ORDER)
                check(dev, "mouse: dragging by the handle", order5 == ["b0", "b1", "b2", "b4", "b3"], order5)
            c.close()
            # (9) the lifted frame in night and sepia
            if dev == "desktop":
                for th in ("night", "sepia"):
                    c2 = new_ctx(br, opts, th)
                    pg2 = c2.new_page()
                    open_tab(pg2)
                    lifted = hold_and_drag(pg2, False, 2, 0, release=False)
                    check(dev, f"{th}: lifted frame in --ap-gold, radius 10 px",
                          bool(lifted) and lifted["border"] == lifted["gold"] and pg2.evaluate(RADIUS)["radius"] == "10px", lifted)
                    pg2.mouse.up()
                    c2.close()
        except Exception as e:  # noqa: BLE001
            check(dev, "run", False, f"error: {e}")
        br.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
