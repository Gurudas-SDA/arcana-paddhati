"""V56 step 1 — Враджа Лила 30.10.2026 13:09 «пример 1 — 6px» (V56 journal, decision 2; plan point 13 «полоса»):
every highlight band of a selected row (lists, the tilak list, text bands, the zebra stripe under them) has the corner
radius 6 px — not 4 px any more. Other radii of the book stay as they are («как сейчас», 13:14).

Rule text (Vraja Lila, verbatim, 30.10.2026 13:09): «пример 1 — 6px».
Checks
  A) source (globals.css, design-system/tokens.css): the band rules carry 6px (and 6px 0 0 6px / 0 6px 6px 0 on the
     place cell and the mantra of the tilak list); no 4px is left on them;
  B) app (with <base-url>), iPhone 14 + desktop: after a tap on a row's number, every painted element of the row has
     only corners of 0 or 6 px, at least one corner 6 px (list «11) асана для Божества», tilak list row 2).
# tehniskais slieksnis Lipikāra, nav S noteikums: «0 or 6 px» per corner; the cell/mantra halves keep 0 on the inner side.
usage: python s122_band_radius_v56.py [<base-url>]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else None
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
results = []


def check(where, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {where} {name} {'' if ok else json.dumps(info, ensure_ascii=False)[:600]}", flush=True)


def strip(t):
    return re.sub(r"/\*.*?\*/", "", t, flags=re.S)


def radii_of(css, selector):
    out = []
    for m in re.finditer(r"(?m)^[ \t]*" + re.escape(selector) + r"[ \t]*\{([^}]*)\}", css):
        out += re.findall(r"border-radius\s*:\s*([^;]+);", m.group(1))
    return [v.strip() for v in out]


def static():
    css = strip(open(os.path.join(ROOT, "app", "globals.css"), encoding="utf-8").read())
    tok = strip(open(os.path.join(ROOT, "design-system", "tokens.css"), encoding="utf-8").read())
    cases = [(".hs-text", "6px"), (".hs-row[data-active] .hs-cell-first", "6px 0 0 6px"), (".hs-cell + span > .hs-text", "0 6px 6px 0"),
             (".hs-row[data-active]:has(> .hs-cell-first)", "6px"), (".hs-row:is(li, div)[data-active]", "6px")]
    for sel, want in cases:
        got = radii_of(css, sel)
        check("src", f"A {sel} = {want}", got and all(g == want for g in got), got)
    m = re.search(r"\.hs-row:nth-of-type\(even\),\s*\.pl-row:nth-of-type\(even\)\s*\{([^}]*)\}", css)
    got = re.findall(r"border-radius\s*:\s*([^;]+);", m.group(1)) if m else []
    check("src", "A zebra stripe (.hs-row/.pl-row even) = 6px", got == ["6px"], got)
    t = re.findall(r"--ds-radius-block\s*:\s*([^;]+);", tok)
    check("src", "A --ds-radius-block = 6px", t and t[0].strip().startswith("6px"), t)


FIND = """([text, idx]) => { const rows = [...document.querySelectorAll('.app-main [data-hs-row]')]
    .filter(r => r.tagName !== 'SPAN' && (text ? r.textContent.includes(text) : r.querySelector('.hs-cell-first')));
  const r = text ? rows[0] : rows[idx]; if (!r) return null;
  r.scrollIntoView({block: 'center'});
  const num = r.querySelector('.hs-cell-first') || r.querySelector('.nl-num .hs-text');
  const b = num.getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; }"""
MEASURE = """([text, idx]) => { const rows = [...document.querySelectorAll('.app-main [data-hs-row]')]
    .filter(r => r.tagName !== 'SPAN' && (text ? r.textContent.includes(text) : r.querySelector('.hs-cell-first')));
  const r = text ? rows[0] : rows[idx]; if (!r) return null;
  const px = (v) => parseFloat(v) || 0;
  const painted = [r, ...r.querySelectorAll('*')].filter(e => { const c = getComputedStyle(e).backgroundColor; return c && !/, 0\\)$/.test(c) && c !== 'transparent'; });
  return {active: r.hasAttribute('data-active'),
          painted: painted.map(e => { const s = getComputedStyle(e); return [e.className.toString().slice(0, 30), px(s.borderTopLeftRadius), px(s.borderTopRightRadius), px(s.borderBottomRightRadius), px(s.borderBottomLeftRadius)]; })}; }"""
CASES = [("worship-sixteen-articles", "асана для Божества", 0, "16 articles, 11) асана для Божества"),
         ("daily-duties-brahma-muhurta", None, 1, "tilak list, row 2")]


def app():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        for dev, eng, opts in qa.devices(["iphone14", "desktop"]):
            b = getattr(p, eng).launch()
            for section, text, idx, label in CASES:
                c = b.new_context(service_workers="block", locale="ru-RU", **opts)
                c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');")
                pg = c.new_page()
                pg.goto(f"{BASE}/ru-iast/{section}/", wait_until="networkidle")
                pg.wait_for_timeout(1200)
                pt = pg.evaluate(FIND, [text, idx])
                if not pt:
                    check(dev, f"B {label}: the row is there", False, "not found")
                    c.close()
                    continue
                pg.wait_for_timeout(500)
                pt = pg.evaluate(FIND, [text, idx])
                (pg.touchscreen.tap if opts.get("has_touch") else pg.mouse.click)(pt[0], pt[1])
                pg.wait_for_timeout(700)
                m = pg.evaluate(MEASURE, [text, idx])
                ok = bool(m and m["active"] and m["painted"]) and all(all(v in (0, 6) for v in q[1:]) and any(v == 6 for v in q[1:]) for q in m["painted"])
                check(dev, f"B {label}: every painted element of the selected row has corners 0 or 6 px (at least one 6)", ok, m)
                c.close()
            b.close()


static()
if BASE:
    app()
n = sum(results)
print(f"\n{n}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
