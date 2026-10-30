"""V61 step 1 — V61 вопрос 3 — Враджа Лила 30.10 15:22 «вопрос 3 - принимаю»: ночью один оттенок наведения.

Rule text (Vraja Lila, verbatim, 30.10.2026 15:22): «вопрос 3 - принимаю»
(question 3 of the V61 list, group 9: «Ночью три разных оттенка для одного жеста «навёл на строку». Хотите один
(`--surface-hover`)?»; the target tone = the one the «Аа» button already has: rgb(46, 39, 31)).

Checks
  A) source: the night theme has no own hover colour for the «Содержание» row (#FDF8F0 cream) and none for the menu ✕
     (#3A2F1F): both take var(--rd-hover) (= --surface-hover); night --rd-hover = #2E271F; the light and sepia
     tokens/rules are untouched (--rd-hover #F5E6C8 / #FAF5EA, the cream hover of the rows stays in the markup);
  B) app (with <base-url>), desktop 1280, NIGHT theme: with the mouse over a row of «Содержание», over the menu ✕ and
     over the «Аа» button, the computed background of all three is the same rgb(46, 39, 31), and the text of each is
     >= 4.5:1 on it;
  C) app, desktop 1280, LIGHT and SEPIA theme: the hover of the «Содержание» row stays cream rgb(253, 248, 240), of the
     menu ✕ rgb(245, 230, 200), of «Аа» = the theme's --rd-hover (nothing changed).
# tehniskais slieksnis Lipikāra, nav S noteikums: 4.5:1 (WCAG AA text contrast), 1280 px desktop width.
usage: python s125_night_hover_one_shade_v61.py [<base-url>]
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
NIGHT = "rgb(46, 39, 31)"


def check(where, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {where} {name} {'' if ok else json.dumps(info, ensure_ascii=False)[:700]}", flush=True)


def strip(t):
    return re.sub(r"/\*.*?\*/", "", t, flags=re.S)


def lum(rgb):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def nums(s):
    return [float(x) for x in re.findall(r"[\d.]+", s)[:3]]


def static():
    css = strip(open(os.path.join(ROOT, "app", "globals.css"), encoding="utf-8").read())
    tok = strip(open(os.path.join(ROOT, "design-system", "tokens.css"), encoding="utf-8").read())
    rd = re.findall(r'html\[data-reader-theme="night"\]\s*\{[^}]*--rd-hover\s*:\s*([^;]+);', css)
    check("src", "A night --rd-hover = #2E271F", rd and rd[-1].strip().upper() == "#2E271F", rd)
    def night_rule(sel):
        for m in re.finditer(r"([^{}]+)\{([^}]*)\}", css):
            sels = [x.strip() for x in m.group(1).split(",")]
            if any(x.startswith('html[data-reader-theme="night"]') and x.endswith(sel) for x in sels):
                return m.group(2)
        return None

    for what, sel in (("✕ hover (.sidebar-close:hover)", ".sidebar-close:hover"),
                      ("row hover (.hover:bg-[#FDF8F0]:hover)", r".hover\:bg-\[\#FDF8F0\]:hover")):
        body = night_rule(sel)
        check("src", f"A night {what} = a hover token, not a number",
              body is not None and re.search(r"background(-color)?\s*:\s*var\(--(surface-hover|rd-hover)\)", body) is not None
              and "#3A2F1F" not in body.upper(), body or "rule missing")
    check("src", "A light --rd-hover #F5E6C8 and sepia #FAF5EA unchanged",
          re.search(r"--rd-hover\s*:\s*#F5E6C8", css, re.I) and re.search(r'data-reader-theme="sepia"\]\s*\{[^}]*--rd-hover\s*:\s*#FAF5EA', css, re.I) is not None)
    check("src", "A tokens.css: --surface-hover = var(--rd-hover)", re.search(r"--surface-hover\s*:\s*var\(--rd-hover\)", tok) is not None)


OPEN = """() => { const t = document.querySelector('[data-reader-action=contents]'); if (t) t.click(); return !!t; }"""
# a plain (not lit) row of «Содержание» with visible area; scrolled into the middle of the panel
ROW = """() => { const rows = [...document.querySelectorAll('[data-toc-row]')].filter(r => !r.hasAttribute('data-toc-lit') && r.getBoundingClientRect().height > 20);
  const r = rows.find(x => x.getBoundingClientRect().top > 120 && x.getBoundingClientRect().bottom < innerHeight - 80) || rows[0];
  if (!r) return null; r.scrollIntoView({block: 'center'}); const b = r.getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; }"""
CENTER = """(sel) => { const e = document.querySelector(sel); if (!e) return null; const b = e.getBoundingClientRect();
  return b.width ? [b.left + b.width / 2, b.top + b.height / 2, b.top >= 0 && b.bottom <= innerHeight] : null; }"""
HOVERED = """([x, y]) => { let e = document.elementFromPoint(x, y); const out = [];
  for (let n = e; n && n !== document.body; n = n.parentElement) { const s = getComputedStyle(n); out.push([n.tagName + '.' + (n.className.toString().slice(0, 40)), s.backgroundColor, s.color]); }
  return out; }"""


def measure(pg, point, wanted_cls):
    """hover the point, wait out the transition, return (bg, color) of the nearest painted ancestor with the wanted class."""
    pg.mouse.move(point[0] - 6, point[1] - 6)
    pg.wait_for_timeout(80)
    pg.mouse.move(point[0], point[1])
    pg.wait_for_timeout(450)
    chain = pg.evaluate(HOVERED, [point[0], point[1]])
    for name, bg, color in chain:
        if re.search(r"(?<![\w-])" + re.escape(wanted_cls) + r"(?![\w-])", name):
            return bg, color, chain
    return None, None, chain


def gestures(pg):
    """-> {name: (bg, text colour)} for the three gestures with the mouse over each (the top bar with «Аа» is on the
    screen at the start; «Содержание» is opened after it)."""
    out = {}
    pt = pg.evaluate(CENTER, ".reader-aa")
    bg, col, ch = measure(pg, pt, "reader-aa") if pt else (None, None, [])
    out["button «Аа»"] = (bg, col, ch)
    pg.mouse.move(5, 5)
    pg.wait_for_timeout(300)
    pg.evaluate(OPEN)
    pg.wait_for_timeout(1300)
    pt = pg.evaluate(ROW)
    bg, col, ch = measure(pg, pt, "sidebar-link") if pt else (None, None, [])
    out["row «Содержание»"] = (bg, col, ch)
    pt = pg.evaluate(CENTER, ".sidebar-close")
    bg, col, ch = measure(pg, pt, "sidebar-close") if pt else (None, None, [])
    out["✕ of the menu"] = (bg, col, ch)
    return out


def app():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        for theme in ("night", "light", "sepia"):
            c = b.new_context(viewport={"width": 1280, "height": 800}, locale="ru-RU", service_workers="block")
            c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');")
            pg = c.new_page()
            pg.goto(f"{BASE}/ru-iast/daily-deity-schedule/", wait_until="networkidle")
            pg.wait_for_timeout(1500)
            pg.evaluate("t => document.documentElement.setAttribute('data-reader-theme', t)", theme)
            pg.wait_for_timeout(300)
            g = gestures(pg)
            if theme == "night":
                bgs = {k: v[0] for k, v in g.items()}
                check("desktop night", f"B all three hovers have one background {NIGHT}", all(v == NIGHT for v in bgs.values()), bgs)
                for k, (bg, col, chain) in g.items():
                    ok = bool(bg and col) and contrast(nums(col), nums(bg)) >= 4.5
                    check("desktop night", f"B text on the hover of {k} >= 4.5:1", ok, [bg, col])
            else:
                want = {"row «Содержание»": "rgb(253, 248, 240)", "✕ of the menu": "rgb(245, 230, 200)"}
                aa = {"light": "rgb(245, 230, 200)", "sepia": "rgb(250, 245, 234)"}[theme]
                want["button «Аа»"] = aa
                for k, v in want.items():
                    check(f"desktop {theme}", f"C hover of {k} = {v} (as before)", g[k][0] == v, [g[k][0], g[k][2][:3]])
            c.close()
        b.close()


static()
if BASE:
    app()
n = sum(results)
print(f"\n{n}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
