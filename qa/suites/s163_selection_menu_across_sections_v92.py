"""V92 — Vraja Lila 09.11 msg 2850/2851 (скриншоты iPad 07.11 21:44 / 21:48)
# V92 — Vraja Lila 09.11 msg 2850/2851
Bug: when the reader EXTENDS a selection past the end of the chapter section into the next section (a heading of another section),
our menu (4 colours · «Заметка» · «Копировать») vanished and only the system menu stayed.
Criteria (Vraja's words): «при выделении дополнительного текста… при выходе в другой раздел» our menu does NOT disappear.
A note is stored per section (data-book-section), so across sections colours and «Заметка» cannot store anything: the menu stays,
says why in one line ([data-hl-hint]), the colours and «Заметка» are disabled, «Копировать» still copies the whole selection.
 (1) a selection inside one section: menu with colours + «Заметка» enabled, no hint (unchanged);
 (2) the same selection EXTENDED into the next section: the menu is still visible and whole on the screen, a hint is shown,
     colours and «Заметка» are disabled, «Копировать» is enabled;
 (3) a selection started in one section and ended in another from the start behaves the same;
 (4) «Копировать» across sections gives the toast and closes the menu; shrinking back to one section brings the colours back.
# tehniskais slieksnis Lipikāra, nav S noteikums: settle 600 ms (debounce 220 ms)
usage: python s163_selection_menu_across_sections_v92.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7", "ipad-portrait", "desktop"])
results = []
PAGE = "book"  # whole book in one scroll, route /book/: sections are [data-book-section]


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else json.dumps(evidence, ensure_ascii=False)[:600]}", flush=True)


# select from word a of a long paragraph in section i up to the end of the first text of section j (j > i); mode 'ext' = first
# a selection inside section i, then extended (extend()), 'direct' = one range at once
PREP = """([] ) => {
  const secs = [...document.querySelectorAll('.app-main [data-book-section]')];
  const pick = (sec) => { for (const p of sec.querySelectorAll('p')) { if (!p.getClientRects().length || p.closest('button,table,[hidden],.mood-panel')) continue;
      const w = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
      for (let x = w.nextNode(); x; x = w.nextNode()) if ((x.data.match(/\\S+/g) || []).length >= 9 && x.parentElement.getClientRects().length) return x; } return null; };
  const nodes = secs.map(pick);
  let i = nodes.findIndex((n) => n);
  if (i < 0) return {err: 'no text', secs: secs.length};
  let j = -1; for (let k = i + 1; k < nodes.length; k++) if (nodes[k]) { j = k; break; }
  if (j < 0) return {err: 'one section only', secs: secs.length};
  window.__v92 = {a: nodes[i], b: nodes[j]};
  nodes[i].parentElement.scrollIntoView({block: 'center'});
  return {secs: secs.length, i, j};
}"""
SEL_IN = """() => { const n = window.__v92.a; const ws = [...n.data.matchAll(/\\S+/g)]; const r = document.createRange();
  r.setStart(n, ws[1].index); r.setEnd(n, ws[6].index + ws[6][0].length); const s = getSelection(); s.removeAllRanges(); s.addRange(r); return r.toString(); }"""
SEL_EXT = """() => { const s = getSelection(); const n = window.__v92.b; const ws = [...n.data.matchAll(/\\S+/g)];
  s.setBaseAndExtent(s.anchorNode, s.anchorOffset, n, ws[3].index + ws[3][0].length); return s.toString().length; }"""
SEL_DIRECT = """() => { const a = window.__v92.a, b = window.__v92.b; const wa = [...a.data.matchAll(/\\S+/g)], wb = [...b.data.matchAll(/\\S+/g)];
  const r = document.createRange(); r.setStart(a, wa[wa.length - 4].index); r.setEnd(b, wb[3].index + wb[3][0].length); const s = getSelection(); s.removeAllRanges(); s.addRange(r); return r.toString().length; }"""
STATE = """() => { const m = document.querySelector('[data-hl-menu]'); if (!m) return null; const b = m.getBoundingClientRect(); const cs = getComputedStyle(m);
  const hint = m.querySelector('[data-hl-hint]'); const dis = (q) => [...m.querySelectorAll(q)].map((e) => e.disabled || e.getAttribute('aria-disabled') === 'true');
  return {vis: cs.visibility !== 'hidden' && b.width > 0, l: b.left, r: b.right, t: b.top, b: b.bottom, vw: innerWidth, vh: innerHeight,
    hint: hint ? hint.textContent.trim() : null, colors: dis('[data-hl-color]'), note: dis('[data-hl-note]'), copy: dis('[data-hl-copy]')}; }"""


def whole(st):
    return st and st["vis"] and st["l"] >= 0 and st["r"] <= st["vw"] and st["t"] >= 0 and st["b"] <= st["vh"]


def wait_menu(pg, want=True):
    """settle, then poll up to 3 s until the menu is in the wanted state (WebKit scrolls/selects a little later)"""
    pg.wait_for_timeout(700)
    st = pg.evaluate(STATE)
    for _ in range(12):
        if bool(st) == want:
            break
        pg.wait_for_timeout(250)
        st = pg.evaluate(STATE)
    return st


def run(p, dev, eng, opts):
    b = getattr(p, eng).launch()
    c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce", **opts)
    c.add_init_script("try{localStorage.removeItem('ap.highlights');localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('ap.readerLayout','scroll');}catch(e){}")
    pg = c.new_page()
    pg.goto(f"{BASE}/ru-iast/book/", wait_until="networkidle")
    pg.wait_for_timeout(2500)
    pg.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important}")
    prep = pg.evaluate(PREP, [])
    check(dev, "two sections with text are in the page", "err" not in prep, prep)
    if "err" in prep:
        b.close()
        return
    pg.wait_for_timeout(800)  # let the scrollIntoView settle before selecting
    # (1)
    pg.evaluate(SEL_IN)
    st = wait_menu(pg)
    if not st:
        # diagnostics (V92 note): was the selection still there, and does a second selection show the menu?
        still = pg.evaluate("() => getSelection().toString().length")
        pg.evaluate(SEL_IN)
        st2 = wait_menu(pg)
        print(f"  [DIAG] {dev} first selection gave no menu (selection kept: {still} chars); re-select -> menu {'shown' if st2 else 'STILL absent'}", flush=True)
        st = st2
        pg.screenshot(path=f"/tmp/claude-1001/-home-satkirti-03-Satkirti/a07d1a16-5db1-4409-9080-8abc555630a2/scratchpad/s163_{dev}_nomenu.png")
    check(dev, "(1) inside one section: menu, colours and «Заметка» enabled, no hint",
          whole(st) and len(st["colors"]) == 4 and not any(st["colors"]) and st["note"] == [False] and st["hint"] is None, st)
    # (2) extended
    n = pg.evaluate(SEL_EXT)
    st = wait_menu(pg)
    check(dev, "(2) extended into the next section: our menu stays whole on the screen", whole(st), [n, st])
    check(dev, "(2) a hint says why", bool(st and st["hint"]), st)
    check(dev, "(2) colours and «Заметка» are disabled, «Копировать» enabled",
          bool(st) and len(st["colors"]) == 4 and all(st["colors"]) and st["note"] == [True] and st["copy"] == [False], st)
    items = pg.evaluate("() => localStorage.getItem('ap.highlights')")
    check(dev, "(2) nothing was stored", not items or '"items":[]' in items.replace(" ", ""), items)
    # (4) shrink back
    pg.evaluate(SEL_IN)
    st = wait_menu(pg)
    check(dev, "(4) shrinking back to one section brings the colours back", whole(st) and not any(st["colors"]) and st["hint"] is None, st)
    # (3) direct
    pg.evaluate(SEL_DIRECT)
    st = wait_menu(pg)
    check(dev, "(3) a range across sections from the start: menu + hint + disabled colours", whole(st) and bool(st["hint"]) and all(st["colors"]), st)
    # copy
    pg.locator("[data-hl-menu] [data-hl-copy]").click()
    pg.wait_for_timeout(500)
    check(dev, "(4) «Копировать» closes the menu", pg.evaluate("() => !document.querySelector('[data-hl-menu]')"))
    b.close()


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        try:
            run(p, dev, eng, opts)
        except Exception as e:  # noqa: BLE001
            check(dev, "scenario ran to the end", False, repr(e)[:400])

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
