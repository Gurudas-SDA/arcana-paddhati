"""V82 — the bottom bar «‹ Вернуться / Вперёд ›» stays visible and active with «Содержание» open (Vraja Lila msg 7768,
variant A, 06.11.2026; saskarnes autors, «Стандарты» 0а, S approval not needed).

Vraja msg 7768, atceļ V35 daļu («panelis izvēlnē paslēpts»). Rule text (task from Vraja's choice, verbatim): «sānu izvēlne
un aptumšojums beidzas virs apakšējā paneļa «Вернуться / Вперёд», panelis pilnā platumā, redzams un aktīvs; «Вернуться»
ar atvērtu izvēlni aizver izvēlni un dara vienu soli atpakaļ».
Criteria: 1) with the menu open the bar is on screen, full width, not dimmed, on top and tappable; 2) the last item of
the contents scrolls to the very end and is not covered by the bar; 3) «Вернуться» with the menu open closes the menu and
makes ONE step back (the page before, the menu stays closed); 4) related bug (Playwright iPhone 14): after a chapter is
chosen in the menu the menu closes, «Вернуться» is active and leads to the previous page — it does not open the menu again.
V82 papildinājums (Vraja Lila msg 7769, burtiski): «при нажатии назад или вперёд нижнее меню должно оставаться до тех пор,
пока юзер не начнёт скроллить или кликом не уберёт его» — criterion 5: after «Вернуться» / «Вперёд» the bars (top and bottom)
stay on the page that opens, 3× «Вернуться» then «Вперёд» without opening them again, also after the 4 s auto-hide time;
they go away only after the reader's own scroll or a tap; restoring the place of the entry (programmatic scroll) does not hide.
# tehniskais slieksnis Lipikāra, nav S noteikums: waits 1500-2500 ms for the settled state; 9 s = the old bug's «menu stays open».
Devices: iphone14, pixel7, ipad-portrait, ipad-landscape, desktop + phones in landscape.
usage: python s156_panel_in_menu_v82.py <base-url>
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
LANG = "ru-iast"
A = "vigraha-tattva"
B = "daily-duties-brahma-muhurta"
PICK = "Гуру-парампара"
PICKS = ["parampara", "mangalacarana", "upadesha-sara"]  # section ids of the rows chosen in the contents, in this order
results = []

STATE = """() => { const vh = innerHeight; const m = document.querySelector('.mobile-menu[data-open]');
  const b = document.querySelector('.reader-bar-bottom'); const cs = b && getComputedStyle(b); const r = b && b.getBoundingClientRect();
  const at = (x, y) => { const e = document.elementFromPoint(x, y); return !!(e && e.closest('.reader-bar-bottom')); };
  const btn = (s) => { const e = b && b.querySelector(s); if (!e) return null; const q = e.getBoundingClientRect();
    return {disabled: !!e.disabled, hit: !!(e.ownerDocument.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2) === e || e.contains(e.ownerDocument.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2)))}; };
  const dim = m && m.querySelector(':scope > .sidebar-backdrop');
  return {url: location.pathname, vh, vw: innerWidth, menu: !!m, hist: history.length,
    bar: b ? {opacity: +(+cs.opacity).toFixed(2), top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right),
              hit: at(r.left + r.width / 2, r.top + r.height / 2), back: btn('[data-reader-step=back]'), forward: btn('[data-reader-step=forward]'),
              dimmed: !!dim && dim.getBoundingClientRect().bottom > r.top + 1} : null}; }"""
LAST = """() => { const m = document.querySelector('.mobile-menu[data-open]'); const aside = m.querySelector('aside');
  let sc = null; for (const e of aside.querySelectorAll('*')) { const o = getComputedStyle(e).overflowY; if ((o === 'auto' || o === 'scroll') && e.scrollHeight > e.clientHeight + 2) { sc = e; break; } }
  if (!sc) sc = aside; sc.scrollTop = sc.scrollHeight;
  return new Promise((done) => setTimeout(() => { const rows = [...aside.querySelectorAll('a,button')].filter((e) => { const q = e.getBoundingClientRect(); return q.height > 0 && q.width > 0; });
    const last = rows[rows.length - 1]; const q = last.getBoundingClientRect(); const bar = document.querySelector('.reader-bar-bottom').getBoundingClientRect();
    const e = document.elementFromPoint(q.left + q.width / 2, Math.min(q.top + q.height / 2, bar.top - 1));
    done({atEnd: sc.scrollTop + sc.clientHeight >= sc.scrollHeight - 2, lastBottom: Math.round(q.bottom), lastTop: Math.round(q.top), barTop: Math.round(bar.top),
          hitMenu: !!(e && e.closest('.mobile-menu aside')), text: last.textContent.trim().slice(0, 40)}); }, 300)); }"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:800]}", flush=True)


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


def path_of(s):
    return s["url"].rstrip("/").split("/")[-1]


def visit(pg):
    """cover -> A -> B, so «Вернуться» has a step (the page A)."""
    pg.goto(f"{BASE}/{LANG}/", wait_until="networkidle")
    pg.goto(f"{BASE}/{LANG}/{A}/", wait_until="networkidle")
    pg.goto(f"{BASE}/{LANG}/{B}/", wait_until="networkidle")
    pg.wait_for_timeout(900)


def run(browser, dev, opts):
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerLayout','page')}catch(e){}")
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        visit(pg)
        open_menu(pg)
        s = pg.evaluate(STATE)
        bar = s["bar"] or {}
        w = s["vw"]
        check(dev, "1 menu open: bottom bar on screen, full width, not dimmed, on top, both buttons tappable",
              s["menu"] and bar.get("opacity", 0) >= 0.99 and bar.get("bottom", 0) <= s["vh"] + 1 and abs(bar.get("left", 9)) <= 1 and abs(bar.get("right", 0) - w) <= 1
              and bar.get("hit") and not bar.get("dimmed") and bar.get("back") and bar["back"]["hit"] and not bar["back"]["disabled"]
              and bar.get("forward") and bar["forward"]["hit"], s)
        last = pg.evaluate(LAST)
        check(dev, "2 menu open: the last item of the contents scrolls to the end and is not covered by the bar",
              last["atEnd"] and last["lastBottom"] <= last["barTop"] + 1 and last["hitMenu"], last)
        pg.evaluate("document.querySelector('.mobile-menu[data-open] aside').scrollTop = 0")
        # 3 «Вернуться» with the menu open: closes it and makes ONE step back
        before = pg.evaluate(STATE)
        pg.evaluate("document.querySelector('[data-reader-step=back]').click()")
        pg.wait_for_timeout(2200)
        after = pg.evaluate(STATE)
        check(dev, "3 «Вернуться» with the menu open closes the menu and goes one step back (the menu stays closed)",
              not after["menu"] and path_of(after) == A and path_of(before) == B, {"before": before["url"], "after": after["url"], "menu": after["menu"]})
        # 4 related bug: a chapter chosen in the menu -> menu closes, «Вернуться» active, leads to the previous page
        pg.goto(f"{BASE}/{LANG}/{B}/", wait_until="networkidle")
        pg.wait_for_timeout(900)
        open_menu(pg)
        pg.evaluate("""(t) => { const a = [...document.querySelectorAll('.mobile-menu[data-open] aside nav a')].find(x => x.textContent.includes(t)); a.click(); }""", PICK)
        pg.wait_for_timeout(2500)
        s = pg.evaluate(STATE)
        picked_url = s["url"]
        show_bars(pg)
        s = pg.evaluate(STATE)
        back = (s["bar"] or {}).get("back") or {}
        check(dev, "4a after a chapter is chosen in the menu: the menu is closed, «Вернуться» is active",
              not s["menu"] and back and not back["disabled"], {"url": s["url"], "menu": s["menu"], "back": back})
        pg.evaluate("document.querySelector('[data-reader-step=back]').click()")
        pg.wait_for_timeout(2500)
        s2 = pg.evaluate(STATE)
        check(dev, "4b «Вернуться» after the choice leads to the previous page and does not open the menu",
              not s2["menu"] and s2["url"] != picked_url and path_of(s2) == B, {"picked": picked_url, "now": s2["url"], "menu": s2["menu"]})
        # 5 (msg 7769): bars stay after steps; go away on the reader's scroll / tap
        pg.goto(f"{BASE}/{LANG}/{B}/", wait_until="networkidle")
        pg.wait_for_timeout(900)
        for t in PICKS:
            open_menu(pg)
            pg.evaluate("""(t) => { const a = [...document.querySelectorAll('.mobile-menu[data-open] aside nav a[href]')].find(x => x.getAttribute('href').replace(/\\/$/, '').endsWith('/' + t)); a.scrollIntoView(); a.click(); }""", t)
            pg.wait_for_timeout(2500)
        shown = "!!document.querySelector('.reader-chrome[data-shown]')"
        seq = []
        for i, (kind, wait) in enumerate((("back", 1200), ("back", 4800), ("back", 1200), ("forward", 1200))):
            if i == 0:
                show_bars(pg)  # only the first time: later the bars must still be there, nobody reopens them
            btn = pg.locator(f"[data-reader-step={kind}]")
            ok_before = pg.evaluate(shown) and btn.is_enabled()
            btn.click(timeout=3000)
            pg.wait_for_timeout(wait)
            st = pg.evaluate(STATE)
            seq.append({"step": f"{i + 1} {kind}", "enabledBefore": ok_before, "url": path_of(st), "shownAfter": pg.evaluate(shown), "menu": st["menu"]})
        check(dev, "5a 3x «Вернуться» then «Вперёд»: the bars stay on every page (also after 4.8 s), the next step is pressable at once",
              all(x["enabledBefore"] and x["shownAfter"] and not x["menu"] for x in seq) and [x["url"] for x in seq] == ["mangalacarana", "parampara", B, "parampara"][:4],
              seq)
        pg.wait_for_timeout(5000)
        check(dev, "5b the bars are still there 5 s after the last step (no auto-hide)", pg.evaluate(shown), None)
        # the reader's scroll: a wheel event (the reader's gesture, as the app sees it) and the scroll itself
        # (mobile WebKit has no Mouse.wheel)
        pg.evaluate("""() => { const m = document.querySelector('.app-main'); m.dispatchEvent(new WheelEvent('wheel', {deltaY: 120, bubbles: true}));
          m.scrollTop += 150; }""")
        pg.wait_for_timeout(120)
        pg.evaluate("document.querySelector('.app-main').scrollTop += 400")
        pg.wait_for_timeout(1800)
        check(dev, "5c the reader's own scroll takes the bars away", not pg.evaluate(shown), None)
        show_bars(pg)
        pg.locator("[data-reader-step=back]").click(timeout=3000)
        pg.wait_for_timeout(1500)
        st_shown = pg.evaluate(shown)
        pg.mouse.click(pg.viewport_size["width"] // 2, pg.viewport_size["height"] // 2)
        pg.wait_for_timeout(900)
        check(dev, "5d after a step the bars stay; a tap takes them away", st_shown and not pg.evaluate(shown), {"afterStep": st_shown})
        check(dev, "no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(dev, "scenario ran", False, str(error)[:300])
    finally:
        c.close()


def landscape(opts):
    o = dict(opts)
    v = o["viewport"]
    o["viewport"] = {"width": v["height"], "height": v["width"]}
    return o


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "pixel7", "ipad-portrait", "ipad-landscape", "desktop"]):
        b = getattr(p, eng).launch()
        run(b, dev, opts)
        if dev in ("iphone14", "pixel7"):
            run(b, dev + "-landscape", landscape(opts))
        b.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
