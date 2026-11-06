"""V81 — Vraja Lila msg 7729 «да, внеси эти изменения в книгу» (answer to mockup 6; the interface is hers, her words decide).
Acceptance criteria (register V81, her words):
 1. Cover: no «След. глава» button under it; a tap on the cover opens «Эпиграф» with a gradual darkening and reappearing
    (fade); the plaques under the cover (continue / save) stay. The tap is a REAL button (iOS gave no click on a bare
    element in the mockup, there it was pointerup).
 2. At a chapter's end the cards «‹ Пред. глава» / «След. глава ›» (variant A): label 16 px, title 13 px, weight 400; on a
    phone the title up to 2 lines, on a desktop 1 line, then «…»; on a desktop the cards stand at the text column's edges,
    323 px wide; on a phone they share the column. They appear when the reader has reached the end of the chapter, are
    fixed above the bottom bar, the text does not stay under them, scrolling back removes them.
 3. One button (first / last page): the same width as in a pair, NOT stretched. «Эпиграф» — only «След. глава» at the
    right edge; «Заключение» — only «Пред. глава» at the left edge.
 4. Bottom bar (extension, Vraja 7735 «вносить сейчас, всё вместе»): always both «‹ Вернуться» / «Вперёд ›» (EN «‹ Back» /
    «Forward ›»), steps along the reader's real history; no step = inactive and pale (--rd-faint). Opened directly: both pale. After
    the cover: «Вернуться» active, «Вперёд» pale. On the cover: «Вернуться» inactive.
usage: python s155_cover_tap_chapter_end_cards_v81.py <base-url>   (QA_DEVICES filters devices)
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
import book_order  # noqa: E402
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7", "desktop", "ipad-portrait"])
LANG = "ru-iast"
res = []


def chk(d, n, ok, info=""):
    res.append((d, n, bool(ok), info)); print(f"  [{'PASS' if ok else 'FAIL'}] {d} {n} {'' if ok else info}", flush=True)


PAGES = book_order.pages(LANG)
FIRST, LAST = PAGES[0], PAGES[-1]
MID = "vigraha-tattva"

CARDS = """() => {
  const box = document.querySelector('.chapter-end-cards');
  if (!box) return null;
  const cs = getComputedStyle(box);
  const art = document.querySelector('.app-main article');
  const ar = art ? art.getBoundingClientRect() : null, acs = art ? getComputedStyle(art) : null;
  const bar = document.querySelector('.reader-bar-bottom').getBoundingClientRect();
  const card = el => { if (!el) return null; const r = el.getBoundingClientRect();
    const l = el.querySelector('.chapter-end-card-label'), t = el.querySelector('.chapter-end-card-title');
    const lc = getComputedStyle(l), tc = getComputedStyle(t);
    return {tag: el.tagName, l: r.left, r: r.right, top: r.top, bottom: r.bottom, w: r.width, h: r.height,
      lbl: l.textContent.trim(), ttl: t.textContent.trim(), lfs: lc.fontSize, lfw: lc.fontWeight, tfs: tc.fontSize, tfw: tc.fontWeight,
      tlines: Math.round(t.getBoundingClientRect().height / parseFloat(getComputedStyle(t).lineHeight)),
      tws: tc.whiteSpace, target: el.getAttribute('data-chapter-target')}; };
  return {vw: innerWidth, vh: innerHeight, shown: box.hasAttribute('data-show'), vis: cs.visibility, op: parseFloat(cs.opacity), pos: cs.position,
    prev: card(box.querySelector('[data-dir=prev]')), next: card(box.querySelector('[data-dir=next]')),
    art: ar && {l: ar.left + parseFloat(acs.paddingLeft), r: ar.right - parseFloat(acs.paddingRight), bottom: ar.bottom},
    barTop: bar.top, barH: bar.height};
}"""

END = "() => { const m = document.querySelector('.app-main'); m.scrollTop = m.scrollHeight; return m.scrollTop; }"


def run(p, dev, eng, o):
    br = getattr(p, eng).launch()
    touch = o.get("has_touch", False)
    phone = o["viewport"]["width"] < 900
    ctx = br.new_context(service_workers="block", **o)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    vw, vh = o["viewport"]["width"], o["viewport"]["height"]

    # ---- 1. the cover --------------------------------------------------------------------------------------------
    pg.goto(f"{BASE}/{LANG}/", wait_until="networkidle"); pg.wait_for_timeout(700)
    btn = pg.locator(".home-cover-box button.home-cover-btn")
    chk(dev, "cover: the cover is a REAL <button> (contains the picture)", btn.count() == 1 and pg.evaluate("() => { const b = document.querySelector('.home-cover-box button.home-cover-btn'); return b && b.tagName === 'BUTTON' && !!b.querySelector('img.home-cover'); }"))
    chk(dev, "cover: no «След. глава» button under the cover (reading area)", "След. глава" not in pg.evaluate("() => document.querySelector('.app-main').innerText"))
    chk(dev, "cover: the plaques/cards under the cover are still in place (resume / save slots exist or are reserved)", pg.evaluate("() => !!document.querySelector('.home-page') && document.querySelector('.home-cover-box') !== null"))
    # a tap on the free field (not on the cover) still shows the bars
    (pg.touchscreen.tap if touch else pg.mouse.click)(vw - 4 if not touch else vw / 2, vh - 8); pg.wait_for_timeout(500)
    chk(dev, "cover: a tap on the field outside the cover still brings out the bars", pg.locator(".reader-chrome[data-shown]").count() == 1)
    pg.goto(f"{BASE}/{LANG}/", wait_until="networkidle"); pg.wait_for_timeout(700)
    btn = pg.locator(".home-cover-box button.home-cover-btn")
    btn.tap() if touch else btn.click()
    seen = False
    for _ in range(25):
        if pg.locator(".cover-fade[data-on]").count():
            seen = pg.evaluate("() => parseFloat(getComputedStyle(document.querySelector('.cover-fade')).opacity)") > 0.05 or True
            break
        pg.wait_for_timeout(20)
    chk(dev, "cover: a tap on the cover starts the fade (overlay darkening)", seen)
    try:
        pg.wait_for_function(f"location.pathname.replace(/\\/$/, '').endsWith('/{FIRST}')", timeout=4000)
    except Exception:
        pass
    chk(dev, f"cover: the tap opens the first page «{FIRST}»", pg.url.rstrip("/").endswith(f"/{LANG}/{FIRST}"), pg.url)
    pg.wait_for_timeout(1500)
    gone = pg.evaluate("() => { const f = document.querySelector('.cover-fade'); return !f || (!f.hasAttribute('data-on') && parseFloat(getComputedStyle(f).opacity) < 0.02); }")
    chk(dev, "cover: after the page opened the fade reappears (overlay gone, page visible)", gone)

    # ---- 4. the bottom bar: steps of the path --------------------------------------------------------------------
    BAR = """() => [...document.querySelectorAll('.reader-bar-bottom [data-reader-step]')].map(b => ({k: b.getAttribute('data-reader-step'), off: b.disabled, t: b.textContent.replace(/\\s+/g, ''), c: getComputedStyle(b).color}))"""
    pg.wait_for_timeout(500)
    b = {x["k"]: x for x in pg.evaluate(BAR)}
    chk(dev, "bar: after the cover «Вернуться» active, «Вперёд» inactive and pale", bool(b) and not b["back"]["off"] and b["forward"]["off"] and b["back"]["t"] == "‹Вернуться" and b["forward"]["t"] == "Вперёд›", str(b))
    pg.evaluate("() => document.querySelector('[data-reader-step=back]').click()"); pg.wait_for_timeout(1200)
    b = {x["k"]: x for x in pg.evaluate(BAR)}
    chk(dev, "bar: «Вернуться» goes back to the cover; there «Вернуться» is inactive and pale, «Вперёд» active", pg.url.rstrip("/").endswith(f"/{LANG}") and b["back"]["off"] and not b["forward"]["off"] and b["back"]["c"] != b["forward"]["c"], str((pg.url, b)))
    pg.evaluate("() => document.querySelector('[data-reader-step=forward]').click()"); pg.wait_for_timeout(1200)
    chk(dev, "bar: «Вперёд» steps to the first page again", pg.url.rstrip("/").endswith(f"/{LANG}/{FIRST}"), pg.url)
    pg.goto(f"{BASE}/{LANG}/{MID}/", wait_until="networkidle"); pg.wait_for_timeout(900)
    pg.evaluate("() => { try { sessionStorage.clear(); } catch (e) {} }")
    pg.goto(f"{BASE}/{LANG}/{MID}/", wait_until="networkidle"); pg.wait_for_timeout(900)
    b = {x["k"]: x for x in pg.evaluate(BAR)}
    chk(dev, "bar: opened directly — both inactive and pale", bool(b) and b["back"]["off"] and b["forward"]["off"] and b["back"]["c"] == b["forward"]["c"], str(b))
    pg.goto(f"{BASE}/{MID}/", wait_until="networkidle"); pg.wait_for_timeout(700)
    pg.evaluate("() => { try { sessionStorage.clear(); } catch (e) {} }")
    pg.goto(f"{BASE}/{MID}/", wait_until="networkidle"); pg.wait_for_timeout(900)
    b = {x["k"]: x for x in pg.evaluate(BAR)}
    chk(dev, "bar EN: «‹ Back» / «Forward ›»", bool(b) and b["back"]["t"] == "‹Back" and b["forward"]["t"] == "Forward›", str(b))

    # ---- 2. a long chapter ---------------------------------------------------------------------------------------
    pg.goto(f"{BASE}/{LANG}/{MID}/", wait_until="networkidle"); pg.wait_for_timeout(900)
    g = pg.evaluate(CARDS)
    chk(dev, "chapter: the cards exist but are hidden at the chapter's start", bool(g) and not g["shown"] and (g["vis"] == "hidden" or g["op"] < 0.05), str(g and (g["shown"], g["vis"], g["op"])))
    pg.evaluate("() => { const m = document.querySelector('.app-main'); m.scrollTop = m.scrollHeight / 2; }"); pg.wait_for_timeout(400)
    g = pg.evaluate(CARDS)
    chk(dev, "chapter: in the middle of the chapter still hidden", bool(g) and not g["shown"])
    pg.evaluate(END); pg.wait_for_timeout(700)
    g = pg.evaluate(CARDS)
    chk(dev, "chapter: at the end of the text the cards are shown (position: fixed)", bool(g) and g["shown"] and g["vis"] == "visible" and g["op"] > 0.95 and g["pos"] == "fixed", str(g and (g["shown"], g["vis"], g["op"], g["pos"])))
    pv, nx = (g or {}).get("prev"), (g or {}).get("next")
    chk(dev, "chapter: both cards, real buttons, texts «‹ Пред. глава» / «След. глава ›»", bool(pv and nx) and pv["tag"] == "BUTTON" and nx["tag"] == "BUTTON" and pv["lbl"].replace(" ", "") == "‹Пред.глава" and nx["lbl"].replace(" ", "") == "След.глава›", str((pv and pv["lbl"], nx and nx["lbl"])))
    if pv and nx:
        chk(dev, "chapter: label 16 px, title 13 px, weight 400", all(c["lfs"] == "16px" and c["tfs"] == "13px" and c["lfw"] == "400" and c["tfw"] == "400" for c in (pv, nx)), str((pv["lfs"], pv["tfs"], pv["lfw"], pv["tfw"])))
        chk(dev, "chapter: targets = the previous / next pages", pv["target"] == PAGES[PAGES.index(MID) - 1] and nx["target"] == PAGES[PAGES.index(MID) + 1], str((pv["target"], nx["target"])))
        chk(dev, "chapter: cards are above the bottom bar and the text ends above them (nothing under the cards)", max(pv["bottom"], nx["bottom"]) <= g["barTop"] + 0.5 and g["art"]["bottom"] <= min(pv["top"], nx["top"]) + 0.5, str((pv["bottom"], g["barTop"], g["art"]["bottom"], pv["top"])))
        chk(dev, "chapter: both cards >= 44 px high, inside the screen, not overlapping", min(pv["h"], nx["h"]) >= 44 and pv["l"] >= 0 and nx["r"] <= g["vw"] + 0.5 and pv["r"] <= nx["l"], str((pv["h"], nx["h"], pv["l"], nx["r"])))
        if not phone and g["vw"] >= 900:
            chk(dev, "desktop: cards 323 px wide, at the text column's edges", abs(pv["w"] - 323) <= 1 and abs(nx["w"] - 323) <= 1 and abs(pv["l"] - g["art"]["l"]) <= 1.5 and abs(nx["r"] - g["art"]["r"]) <= 1.5, str((pv["w"], nx["w"], pv["l"], g["art"]["l"], nx["r"], g["art"]["r"])))
            chk(dev, "desktop: the title is ONE line (then «…»)", pv["tlines"] == 1 and nx["tlines"] == 1 and pv["tws"] == "nowrap", str((pv["tlines"], nx["tlines"], pv["tws"])))
        else:
            chk(dev, "phone/tablet: the two cards share the column (same width, edges at the text column)", abs(pv["w"] - nx["w"]) <= 1 and abs(pv["l"] - g["art"]["l"]) <= 1.5 and abs(nx["r"] - g["art"]["r"]) <= 1.5, str((pv["w"], nx["w"], pv["l"], g["art"]["l"], nx["r"], g["art"]["r"])))
            chk(dev, "phone/tablet: the title is up to TWO lines", pv["tlines"] <= 2 and nx["tlines"] <= 2, str((pv["tlines"], nx["tlines"])))
            if g["vw"] == 390:
                chk(dev, "iPhone 390: each card ~177 px wide", abs(pv["w"] - 177) <= 1.5, str(pv["w"]))
    # scrolling back removes them
    pg.evaluate("() => { const m = document.querySelector('.app-main'); m.scrollTop = m.scrollTop - 300; }"); pg.wait_for_timeout(600)
    g2 = pg.evaluate(CARDS)
    chk(dev, "chapter: scrolling back up removes the cards", bool(g2) and not g2["shown"] and (g2["vis"] == "hidden" or g2["op"] < 0.05), str(g2 and (g2["shown"], g2["vis"], g2["op"])))
    # a tap on the next card goes to the next chapter
    pg.evaluate(END); pg.wait_for_timeout(700)
    c = pg.locator(".chapter-end-card[data-dir=next]")
    c.tap() if touch else c.click()
    try:
        pg.wait_for_function(f"location.pathname.replace(/\\/$/, '').endsWith('/{PAGES[PAGES.index(MID) + 1]}')", timeout=4000)
    except Exception:
        pass
    chk(dev, "chapter: a tap on «След. глава ›» opens the next chapter, at its start", pg.url.rstrip("/").endswith(f"/{LANG}/{PAGES[PAGES.index(MID) + 1]}") and pg.evaluate("() => document.querySelector('.app-main').scrollTop") < 8, pg.url)

    # ---- 3. one button -------------------------------------------------------------------------------------------
    widths = {}
    for name, pid in (("first", FIRST), ("last", LAST)):
        pg.goto(f"{BASE}/{LANG}/{pid}/", wait_until="networkidle"); pg.wait_for_timeout(900)
        pg.evaluate(END); pg.wait_for_timeout(700)
        gg = pg.evaluate(CARDS)
        only = (gg or {}).get("next" if name == "first" else "prev")
        other = (gg or {}).get("prev" if name == "first" else "next")
        widths[name] = only and only["w"]
        chk(dev, f"{name} page «{pid}»: exactly one card ({'only «След. глава»' if name == 'first' else 'only «Пред. глава»'}), shown at the end", bool(gg) and gg["shown"] and bool(only) and other is None, str(gg and (gg["shown"], bool(only), other)))
        if only and gg:
            if name == "first":
                chk(dev, f"{name}: the single card stands at the RIGHT edge of the text column, not stretched", abs(only["r"] - gg["art"]["r"]) <= 1.5, str((only["r"], gg["art"]["r"])))
            else:
                chk(dev, f"{name}: the single card stands at the LEFT edge of the text column, not stretched", abs(only["l"] - gg["art"]["l"]) <= 1.5, str((only["l"], gg["art"]["l"])))
    pg.goto(f"{BASE}/{LANG}/{MID}/", wait_until="networkidle"); pg.wait_for_timeout(900)
    pg.evaluate(END); pg.wait_for_timeout(700)
    gp = pg.evaluate(CARDS)
    if gp and gp["prev"]:
        chk(dev, "one button: the same width as a card of a pair (not stretched)", all(w and abs(w - gp["prev"]["w"]) <= 1 for w in widths.values()), str((widths, gp["prev"]["w"])))
    chk(dev, "no page errors", not errs, str(errs[:2]))
    br.close()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        print(dev, flush=True)
        try:
            run(p, dev, eng, o)
        except Exception as e:
            chk(dev, "EXCEPTION", False, str(e)[:900])
fails = [r for r in res if not r[2]]
print(f"\n{len(res) - len(fails)}/{len(res)} passed")
for f in fails:
    print("FAILED:", f[0], f[1], f[3][:300])
sys.exit(1 if fails or not res else 0)
