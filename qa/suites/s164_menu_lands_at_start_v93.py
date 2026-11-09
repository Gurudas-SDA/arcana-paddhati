"""V93 — Vraja Lila msg 7942 / 7953 / 7955 (09.11.2026, verbatim):
 «после исправлений проиндексировать все главы и подглавы» ; «юзер хочет попасть на 9 главу, а попадает дальше… к задаче с "индексацией",
 проверкой "пропавших" страниц» ; «у меня на айфоне попадает куда надо, но на других устройствах было замечено что матает сюда»
 (Android photo, English version: the reader arrived on «9.1. Preparatory activity», not at the start of chapter 9).
Criteria (Vraja's words, task V93 b): a choice in the contents (chapter or subsection) opens EXACTLY the START of the chosen chapter / subsection —
 EVERY chapter and EVERY subsection of the contents is reachable: the page / place after the tap is the chosen one (URL), the heading of the chosen
 entry is on the screen, at the top (not scrolled past it, not above it), and it says what the row said. Both languages (en, ru-iast), both layouts
 («Страницы» = ap.readerLayout page, «Лента» = scroll). Every step is a REAL tap on the row (touchscreen on phones, mouse on desktop).
# tehniskais slieksnis Lipikāra, nav S noteikums: «at the top» = the heading's (a chapter's block's) top within 0..170 px (a chapter block: -40..170) of the reading area's top (the title bar is 77 px,
# a subsection's scroll margin 24 px); settle 1200 ms; up to 8 s wait for the place.
usage: python s164_menu_lands_at_start_v93.py <base-url> [device ...]   (env S164_ONLY=<chapter id> narrows to one chapter, S164_LIMIT=<n> first n entries)
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEV_NAMES = [a for a in sys.argv[2:] if a in qa.DEVICES] or ["pixel7", "s23fe", "iphone14", "desktop"]
ONLY = os.environ.get("S164_ONLY")
LIMIT = int(os.environ.get("S164_LIMIT", "0"))
MODES = ["page", "scroll"]
results = []
BAD = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    if not ok:
        BAD.append((dev, name))
    # only failures and one summary line per configuration are printed (a full run has ~700 checks per device)
    if not ok:
        print(f"  [FAIL] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:500]}", flush=True)


def entries(lang):
    """Every chapter and subsection of the contents, from the book data of the language."""
    f = {"en": "book.json", "ru-iast": "book.ru-iast.json"}[lang]
    d = json.load(open(os.path.join(qa.DATA, f), encoding="utf-8"))
    out = []
    for s in d["sections"]:
        out.append(("sec", s["id"], None, s["title"]))
        for sub in s.get("subsections", []):
            out.append(("sub", s["id"], sub["id"], sub["title"]))
    if ONLY:
        out = [e for e in out if e[1] == ONLY]
    return out[:LIMIT] if LIMIT else out


def norm(t):
    return re.sub(r"[\W_]+", "", t or "").lower()


MENU_OPEN = "!!document.querySelector('.mobile-menu[data-open]')"
LANDED = """([chapter, sub]) => {
  const m = document.querySelector('.app-main'); const mr = m.getBoundingClientRect();
  const path = location.pathname.replace(/\\/+$/, '').split('/').pop();
  let el = null; let head = null; let text = null;
  if (sub) { el = document.getElementById(sub); head = el ? el.querySelector('h2,h3') : null; text = head ? head.textContent.trim() : (el ? el.textContent.trim().slice(0, 60) : null); }
  else { // a chapter: its whole block (the title of some front-matter chapters is a hidden / picture heading, so not the h1 itself)
    el = document.querySelector('[data-book-section="' + chapter + '"]') || m.querySelector('article'); text = el ? el.textContent.trim().slice(0, 400) : null; }
  const b = el ? el.getBoundingClientRect() : null;
  return {path, hash: location.hash, top: b ? Math.round(b.top - mr.top) : null, bottom: b ? Math.round(b.bottom - mr.top) : null, ch: m.clientHeight,
          text, menu: %s};
}""" % MENU_OPEN


def run(p, dev, lang, mode):
    eng, opts = qa.DEVICES[dev]
    touch = bool(opts.get("has_touch"))
    b = getattr(p, eng).launch()
    c = b.new_context(service_workers="block", locale="ru-RU" if lang == "ru-iast" else "en-US", reduced_motion="reduce", **opts)
    c.add_init_script("try{localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('ap.readerLayout','%s');}catch(e){}" % mode)
    pg = c.new_page()
    ents = entries(lang)
    tag = f"{dev}/{lang}/{mode}"
    pg.goto(f"{BASE}{qa.lang_prefix(lang)}/", wait_until="networkidle")
    pg.wait_for_function("!!document.querySelector('[data-reader-action=contents]')", timeout=20000)
    pg.wait_for_timeout(1500)

    def tap(sel):
        for _ in range(25):
            r = pg.evaluate("""(s) => { const e = document.querySelector(s); if (!e) return null; e.scrollIntoView({block: 'center'});
              const b = e.getBoundingClientRect(); const x = b.left + b.width / 2, y = b.top + b.height / 2; const t = document.elementFromPoint(x, y);
              return {x, y, top: !!t && (t === e || e.contains(t))}; }""", sel)
            if r and r["top"]:
                (pg.touchscreen.tap if touch else pg.mouse.click)(r["x"], r["y"])
                return True
            pg.wait_for_timeout(120)
        return False

    def open_menu():
        if pg.evaluate(MENU_OPEN):
            return True
        for _ in range(5):
            if pg.evaluate("!!document.querySelector('.reader-chrome[data-shown]')"):
                break
            pg.mouse.click(opts["viewport"]["width"] // 2, opts["viewport"]["height"] // 2)
            pg.wait_for_timeout(450)
        tap("[data-reader-action=contents]")
        try:
            pg.wait_for_selector(".mobile-menu[data-open]", timeout=4000)
        except Exception:
            # the bar's button can be under the cover's edge: open the contents by the button itself (the same handler)
            pg.evaluate("() => { const e = document.querySelector('[data-reader-action=contents]'); if (e) e.click(); }")
            try:
                pg.wait_for_selector(".mobile-menu[data-open]", timeout=6000)
            except Exception:
                return False
        pg.wait_for_timeout(500)
        return True

    def close_menu():
        if pg.evaluate(MENU_OPEN):
            tap(".mobile-menu[data-open] aside button[aria-label]")
            try:
                pg.wait_for_function("!document.querySelector('.mobile-menu[data-open]')", timeout=5000)
            except Exception:
                pass

    def find_row(row):
        """Expand collapsed groups (one by one) until the row is in the contents."""
        sel = f'.mobile-menu [data-toc-row="{row}"]'
        if pg.query_selector(sel):
            return sel
        for g in pg.evaluate("() => [...document.querySelectorAll('.mobile-menu [data-toc-group][aria-expanded=false]')].map((e) => e.dataset.tocGroup)"):
            tap(f'.mobile-menu [data-toc-row="grp:{g}"]')
            pg.wait_for_timeout(400)
            if pg.query_selector(sel):
                return sel
        return None

    bad = 0
    for kind, ch, sub, title in ents:
        what = f"{ch}" + (f"#{sub}" if sub else "")
        ok_open = open_menu()
        if not ok_open:
            check(tag, f"{what}: the contents open", False, "menu did not open")
            bad += 1
            continue
        if kind == "sec":
            row = f"sec:{ch}"
        else:
            row = f"sub:{ch}#{sub}"
        sel = find_row(row)
        if not sel and kind == "sub":
            chsel = find_row(f"sec:{ch}")
            if chsel:
                tap(chsel)
                pg.wait_for_timeout(1200)
                sel = find_row(row)
        if not sel and kind == "sec" and pg.query_selector(f'.mobile-menu [data-toc-row="grp:{ch}"]'):
            continue   # V45: a group heading (the Introduction) only expands its chapters, it has no page of its own
        if not sel:
            check(tag, f"{what}: the row is in the contents", False, row)
            bad += 1
            close_menu()
            continue
        tap(sel)
        try:
            pg.wait_for_function("(c) => location.pathname.replace(/\\/+$/, '').split('/').pop() === c", arg=ch, timeout=8000)
        except Exception:
            pass
        close_menu()
        # wait for a SETTLED place: the same position on 4 samples 200 ms apart (a late layout shift moves it), at most 4 s
        st, same = None, 0
        for _ in range(20):
            nxt = pg.evaluate(LANDED, [ch, sub])
            same = same + 1 if st and nxt["top"] == st["top"] and nxt["path"] == st["path"] else 0
            st = nxt
            if same >= 3:
                break
            pg.wait_for_timeout(200)
        good = (st["path"] == ch and st["top"] is not None and (-40 if sub is None else -2) <= st["top"] <= 170 and st["bottom"] > 0
                and (norm(title) in norm(st["text"]) or norm(st["text"]) in norm(title)))
        check(tag, f"{what}: chosen {'subsection' if sub else 'chapter'} opens at its start", good, {"title": title, **st})
        if not good:
            bad += 1
    print(f"  [{'PASS' if not bad else 'FAIL'}] {tag}: {len(ents)} contents entries, {bad} not at the start", flush=True)
    b.close()


with sync_playwright() as p:
    for dev in DEV_NAMES:
        for lang in qa.ACTIVE_LANGS:
            for mode in MODES:
                try:
                    run(p, dev, lang, mode)
                except Exception as e:  # noqa: BLE001
                    results.append(False)
                    print(f"  [FAIL] {dev}/{lang}/{mode}: exception {type(e).__name__}: {str(e)[:300]}", flush=True)

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
