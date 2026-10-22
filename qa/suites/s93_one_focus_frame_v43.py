"""V43 p.2 — ONE frame line on a focused / highlighted control, everywhere (Vraja Lila 22.10.2026, iPhone screenshots
1792651216877 / 1792651217013 / 1792651217063; saskarnes autors, «Стандарты» 0а).

Vraja Lila's words (verbatim): «двойные рамки всё ещё там (на поиске тоже)» — the bookmark name field in focus showed
its gold 1 px border AND a pale gold 2 px ring around it (two lines); the search field in «Содержание» the same
(V33 a496284 «одна рамка» was not released). Wanted: ONE frame, the same focus style everywhere, from the design system
(design-system/tokens.css --ds-focus*, components.css .ds-field).

A «line» is: a visible border on all four sides (a frame; a coloured left bar is a marker, not a frame), a visible
outline, or an outer box-shadow ring (no blur, spread > 0 — the Tailwind «ring»). An inset shadow right inside the
border, in the border's colour, thickens the same line (one line). An outline in the border's colour lying on it
(offset between −(outline+border) and 0) is the same line too.
 # tehniskais slieksnis Lipikāra, nav S noteikums: colours equal when every RGB channel differs ≤ 2; alpha ≤ 0.05 = invisible.

Checks, per device, for every focusable control (keyboard focus, :focus-visible) on: a chapter page with the bars,
«Содержание» (search field, rows, tabs, ✕), the bookmark window (field, buttons), verse chips and «Настроение Гурудева»:
  A  no control shows two lines (border + ring, border + outline beside it, outline + ring), and none shows no line;
  B  the bookmark name field and the search field: in focus exactly one line, gold (--ap-gold), 2 px;
  C  every focus line is the accent colour of the theme (--ap-gold) — one focus style.
usage: python s93_one_focus_frame_v43.py <base-url>
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
CH = "daily-duties-brahma-muhurta"
SEED = [{"id": "b-ff", "section": "arcana-procedure", "anchor": "2-svagata", "block": 0, "lang": "ru-iast", "time": 1792000000000, "name": "Утро"}]
MENU = ".mobile-menu[data-open]"
results = []

# Lines of one focused element (see the docstring).
LINES = r"""(el) => {
  const rgba = (s) => { const m = (s || '').match(/rgba?\(([^)]+)\)/); if (!m) return [0, 0, 0, 0];
    const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(parseFloat); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const vis = (s) => rgba(s)[3] > 0.05;
  const same = (a, b) => { const x = rgba(a), y = rgba(b); return [0, 1, 2].every((i) => Math.abs(x[i] - y[i]) <= 2); };
  const c = getComputedStyle(el);
  const sides = ['Top', 'Right', 'Bottom', 'Left'];
  const frame = sides.every((s) => parseFloat(c['border' + s + 'Width']) > 0 && c['border' + s + 'Style'] !== 'none' && vis(c['border' + s + 'Color']));
  const bw = parseFloat(c.borderTopWidth) || 0;
  const ow = parseFloat(c.outlineWidth) || 0, off = parseFloat(c.outlineOffset) || 0;
  const outline = c.outlineStyle !== 'none' && ow > 0 && vis(c.outlineColor);
  // box-shadow list: split on commas outside brackets
  const shadows = []; let depth = 0, cur = '';
  for (const ch of (c.boxShadow === 'none' ? '' : c.boxShadow)) { if (ch === '(') depth++; if (ch === ')') depth--;
    if (ch === ',' && !depth) { shadows.push(cur.trim()); cur = ''; } else cur += ch; }
  if (cur.trim()) shadows.push(cur.trim());
  const ring = [], inset = [];
  for (const s of shadows) { const col = (s.match(/rgba?\([^)]+\)/) || [''])[0]; if (!vis(col)) continue;
    const nums = s.replace(/rgba?\([^)]+\)/, '').replace('inset', '').trim().split(/\s+/).map(parseFloat);
    const [x, y, blur, spread] = [nums[0] || 0, nums[1] || 0, nums[2] || 0, nums[3] || 0];
    if (x === 0 && y === 0 && blur <= 1 && spread > 0) (s.includes('inset') ? inset : ring).push({col, spread}); }
  let lines = 0; const parts = [];
  if (frame) { lines++; parts.push('border ' + bw + 'px ' + c.borderTopColor); }
  if (outline) { const onBorder = frame && same(c.outlineColor, c.borderTopColor) && off <= 0 && off >= -(ow + bw);
    if (!onBorder) lines++; parts.push('outline ' + ow + 'px off ' + off + ' ' + c.outlineColor + (onBorder ? ' (on the border)' : '')); }
  for (const r of ring) { lines++; parts.push('ring ' + r.spread + 'px ' + r.col); }
  for (const r of inset) { const onBorder = frame && same(r.col, c.borderTopColor); if (!onBorder) lines++;
    parts.push('inset ' + r.spread + 'px ' + r.col + (onBorder ? ' (on the border)' : '')); }
  // the focus colour(s)
  const focusCols = [];
  if (outline) focusCols.push(c.outlineColor);
  for (const r of ring.concat(inset)) focusCols.push(r.col);
  if (!outline && !ring.length && !inset.length && frame) focusCols.push(c.borderTopColor);
  const gold = getComputedStyle(document.documentElement).getPropertyValue('--ap-gold').trim();
  const probe = document.createElement('i'); probe.style.color = gold; document.body.appendChild(probe);
  const goldRgb = getComputedStyle(probe).color; probe.remove();
  const width = (outline ? ow : 0) + (inset.length ? inset[0].spread : 0) + (frame && (!outline || same(c.outlineColor, c.borderTopColor)) ? bw : 0);
  return {lines, parts, gold: focusCols.length > 0 && focusCols.every((x) => same(x, goldRgb)), cols: focusCols, goldRgb,
          fv: el.matches(':focus-visible'), width,
          what: (el.getAttribute('aria-label') || el.textContent || el.getAttribute('placeholder') || el.tagName).trim().slice(0, 40),
          cls: (el.className && el.className.baseVal === undefined ? el.className : '').toString().split(' ').slice(0, 3).join(' ')};
}"""

LIST = """(scope) => { const root = scope ? document.querySelector(scope) : document;
  if (!root) return 0; const sel = 'a[href],button,input:not([type=hidden]),select,textarea,[tabindex]:not([tabindex="-1"]),[role=button]';
  const all = [...root.querySelectorAll(sel)].filter((e) => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight && cs.visibility !== 'hidden' && !e.closest('[inert]') && !e.disabled; });
  window.__qaFocus = all.slice(0, 40); return window.__qaFocus.length; }"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:900]}", flush=True)


def focus_all(pg, scope):
    """Keyboard-focus every visible control in scope; returns their line reports."""
    n = pg.evaluate(LIST, scope)
    out = []
    for i in range(n):
        pg.keyboard.press("Shift")            # keyboard modality, so .focus() is :focus-visible
        r = pg.evaluate(f"""() => {{ const el = window.__qaFocus[{i}]; if (!el || !el.isConnected) return null;
            el.focus({{preventScroll: true}}); return document.activeElement === el; }}""")
        if not r:
            continue
        pg.wait_for_timeout(60)
        rep = pg.evaluate(f"() => ({LINES})(window.__qaFocus[{i}])")
        if rep["fv"]:
            out.append(rep)
    pg.evaluate("() => document.activeElement && document.activeElement.blur && document.activeElement.blur()")
    return out


def judge(dev, where, reps):
    double = [r for r in reps if r["lines"] >= 2]
    check(dev, f"A {where}: no control in focus shows two frame lines ({len(reps)} controls)", reps and not double,
          [{k: r[k] for k in ("what", "cls", "parts")} for r in double][:8])
    none = [r for r in reps if r["lines"] == 0]
    check(dev, f"A {where}: every control in focus shows a focus line (not none)", reps and not none,
          [{k: r[k] for k in ("what", "cls", "parts")} for r in none][:8])
    off = [r for r in reps if r["parts"] and not r["gold"]]
    check(dev, f"C {where}: every focus line is the theme accent --ap-gold (one focus style)", reps and not off,
          [{k: r[k] for k in ("what", "cls", "cols", "goldRgb")} for r in off][:8])


def field(pg, dev, what, sel):
    pg.keyboard.press("Shift")
    pg.locator(sel).first.evaluate("e => e.focus({preventScroll: true})")
    pg.wait_for_timeout(250)                   # after the colour transition
    r = pg.locator(sel).first.evaluate(f"(el) => ({LINES})(el)")
    check(dev, f"B {what}: in focus exactly ONE line, gold, 2 px", r["lines"] == 1 and r["gold"] and abs(r["width"] - 2) <= 0.5,
          {k: r[k] for k in ("parts", "cols", "goldRgb", "width")})


def run(browser, dev, opts):
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    c.add_init_script("if (!sessionStorage.getItem('qaSeeded')) { localStorage.setItem('ap.readerHintSeen','1');"
                      "localStorage.setItem('installDismissed','true');"
                      f"localStorage.setItem('ap.bookmarks', JSON.stringify({json.dumps({'v': 1, 'items': SEED}, ensure_ascii=False)}));"
                      "sessionStorage.setItem('qaSeeded','1'); }")
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        pg.goto(f"{BASE}/{LANG}/{CH}/", wait_until="networkidle")
        pg.wait_for_timeout(1500)
        if not pg.locator(".reader-chrome[data-shown]").count():
            pg.mouse.click(200, 430)
            pg.wait_for_timeout(500)
        judge(dev, "chapter page (bars, verse chips, «Настроение Гурудева»)", focus_all(pg, ".reader-chrome") + focus_all(pg, ".app-main"))
        # «Содержание»: search field, tabs, rows, ✕
        pg.locator("[data-reader-action=contents]").evaluate("b => b.click()")
        pg.wait_for_timeout(700)
        field(pg, dev, "search field in «Содержание»", f"{MENU} .search-input")
        judge(dev, "«Содержание»", focus_all(pg, MENU))
        tab = pg.locator(f"{MENU} [data-sidebar-tab=bookmarks]")
        if tab.count():
            tab.evaluate("b => b.click()")
            pg.wait_for_timeout(400)
            judge(dev, "«Закладки»", focus_all(pg, MENU))
            pg.locator(f"{MENU} [data-bookmark-id=b-ff] [data-bookmark-rename]").evaluate("b => b.click()")
            pg.wait_for_timeout(500)
            field(pg, dev, "bookmark name field", "[data-bookmark-dialog-input]")
            judge(dev, "bookmark window", focus_all(pg, "[data-bookmark-dialog]"))
            pg.locator("[data-bookmark-dialog-cancel]").evaluate("b => b.click()")
            pg.wait_for_timeout(300)
        check(dev, "no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(dev, "scenario ran", False, str(error)[:300])
    finally:
        c.close()


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "desktop"]):
        b = getattr(p, eng).launch()
        run(b, dev, opts)
        b.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
