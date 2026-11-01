"""V61 step 5 «Разделы» (Враджа Лила, plan step 5; her decisions: msg 7167 31.10.2026 «3 - 48», question 4 «принять», question 5 «принять»).

Rule text (Vraja Lila, V61 plan, step 5, decisions of 30–31.10.2026):
 «3 - 48» (msg 7167): the side margin of the chapter text on a computer is FIXED 48 px (not 4.5 % of the width); phone 12 (scale; 16 broke UI-7.2 s02 column >= 92 %);
 the home page and «Содержание» margins follow the scale 4·8·12·16·24·32 (+48 only the page bottom and the chapter's side margin);
 the 2 px between the «Содержание» rows is the one exception (--space-dense);
 question 4 «принять»: at night the card «Продолжить» looks the same as «Сохранение» (one look);
 question 5 «принять»: ONE main dark text: h2 / h3 in the light theme a little more neutral, the text in sepia a little warmer = the one token.
Acceptance: (1) the chapter text starts 48 px from the article edge at any width >= 1024; (2) similar sections' margins no longer «jump»: only scale values;
 (3) day / sepia / night: nothing else changes.
  Check D fix (31.10): the colour test reads the page maha-abhiseka (it has h2 AND h3; vigraha-tattva has no h3 -> null) and the chapter BODY text
  p.text-[15px] (class text-[#1a1a1a]; the first bare <p> is a secondary text, not body). Body in the live book is #1a1a1a already, so no colour changes.

Checks
  A) source: .reader-article side padding: phone var(--space-12), 640-1023 var(--space-24) (technical choice: the old 4.5vw was 29-46 px there),
     >= 1024 var(--space-48) (token --pad-article-wide declared once in tokens.css); no 4.5vw left;
  B) source: the home cards (.home-resume*, .home-save*) and the «Содержание» panel (Sidebar.tsx) and the home page (HomePage.tsx) use only scale values
     in padding / margin / gap (var(--space-N), Tailwind 1/2/3/4/6/8/12, 0 and the dense 2 px = space-y-0.5 between the rows); the icon / button
     room classes pr-[96px] pr-[3px] pl-9 are not margins and stay (listed);
  C) source + app: at night the card «Продолжить» has the SAME background / border colour / text colour / padding as «Сохранение»;
  D) source + app: one main dark text: the light-theme h2 and h3 and the text read var(--text-primary) (= --rd-fg): day h2 = h3 = rgb(26,26,26),
     sepia h2 = h3 = body text = rgb(42,32,22), night unchanged (--rd-fg);
  E) app: the chapter article side padding = 48 at 1440 and 1024 wide; 24 at 800; 12 on the phone.
# tehniskais slieksnis Lipikāra, nav S noteikums: ±1 px measuring tolerance; 640-1023 = 24 (the plan left it to the scale: 16 or 24).
usage: python s128_sections_scale_v61.py [<base-url>]
"""
import json
import os
import re
import sys

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else None
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
results = []
TOL = 1.0


def check(where, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {where} {name} {'' if ok else json.dumps(info, ensure_ascii=False)[:900]}", flush=True)


def rd(*p):
    return open(os.path.join(ROOT, *p), encoding="utf-8").read()


def strip(t):
    return re.sub(r"/\*.*?\*/", "", t, flags=re.S)


SCALE_PX = {0, 4, 8, 12, 16, 24, 32, 48}
TW_OK = {"0", "1", "2", "3", "4", "6", "8", "12"}
TW_NOT_MARGINS = {"pr-[96px]", "pr-[3px]", "pl-9"}  # reserved room for buttons / icons, not a margin


def rules(css, sel_re):
    out = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        if re.search(sel_re, m.group(1).strip()):
            out.append((m.group(1).strip(), m.group(2)))
    return out


def bad_css_spacing(body):
    bad = []
    for m in re.finditer(r"(?<![\w-])((?:padding|margin)(?:-(?:top|right|bottom|left|inline|block))?|gap|row-gap|column-gap)\s*:\s*([^;]+);", body):
        for v in re.findall(r"(?<![\w.-])(-?[\d.]+)(px|rem)\b", m.group(2)):
            px = float(v[0]) * (16 if v[1] == "rem" else 1)
            if px not in SCALE_PX:
                bad.append(f"{m.group(1)}: {m.group(2).strip()}")
    return bad


def static():
    css = strip(rd("app", "globals.css"))
    tok = strip(rd("design-system", "tokens.css"))
    # A
    d = re.findall(r"(?m)^\s*--pad-article-wide\s*:\s*([^;]+);", tok)
    check("src", "A --pad-article-wide declared once = var(--space-48)", d == ["var(--space-48)"], d)
    check("src", "A no 4.5vw left in globals.css", "4.5vw" not in css)
    ph = re.search(r"\.reader-article\s*\{[^}]*?padding\s*:\s*[^;]*?var\(--space-12\)[^;]*;", css)
    check("src", "A phone: .reader-article side padding var(--space-12)", bool(ph), "")
    got = {}
    for k, v in re.findall(r"@media \(min-width: (\d+)px\)\s*\{\s*\.reader-article\s*\{([^}]*)\}", css):
        got[k] = got.get(k, "") + v
    check("src", "A >= 640: side padding var(--space-24)", "640" in got and "var(--space-24)" in got["640"], got.get("640"))
    check("src", "A >= 1024: side padding var(--pad-article-wide)", "1024" in got and "var(--pad-article-wide)" in got["1024"], got.get("1024"))
    # B
    for sel, name in [(r"\.home-resume|\.home-save", "home cards")]:
        bad = []
        for s, b in rules(css, sel):
            if s == ".home-save-track":  # decor: the 2 px between the progress segments (a bar, not a margin) — technical exception
                continue
            bad += [f"{s}: {x}" for x in bad_css_spacing(b)]
        check("src", f"B {name}: padding / margin / gap only on the scale", not bad, bad)
    for f in ["Sidebar.tsx", "HomePage.tsx"]:
        s = rd("components", f)
        bad = []
        for m in re.finditer(r"(?<![\w-])((?:sm:|md:|lg:)?(?:p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|gap|gap-x|gap-y|space-y|space-x)-(\[[\d.]+px\]|[\d.]+))(?![\w-])", s):
            cls = m.group(1)
            base = re.sub(r"^(sm|md|lg):", "", cls)
            n = base.split("-", 1)[1] if not base.startswith(("gap-x", "gap-y", "space-y", "space-x")) else base.split("-", 2)[2]
            if base in TW_NOT_MARGINS or base == "space-y-0.5":
                continue
            if n not in TW_OK:
                bad.append(cls)
        check("src", f"B {f}: spacing classes only on the scale (dense space-y-0.5 and {sorted(TW_NOT_MARGINS)} excepted)", not bad, sorted(set(bad)))
    # C
    def blk(sel):
        return "\n".join(b for s, b in rules(css, r"^" + re.escape(sel) + r"$"))
    night_r = blk('html[data-reader-theme="night"] .home-resume')
    night_s = blk('html[data-reader-theme="night"] .home-save')
    check("src", "C night «Продолжить»: background = var(--rd-panel-bg), border-color = var(--rd-border)",
          "var(--rd-panel-bg)" in night_r and "var(--rd-border)" in night_r, night_r)
    check("src", "C night «Продолжить» and «Сохранение» text colour equal",
          re.search(r"(?<![-\w])color\s*:\s*([^;]+);", night_r) and re.search(r"(?<![-\w])color\s*:\s*([^;]+);", night_r).group(1)
          == re.search(r"(?<![-\w])color\s*:\s*([^;]+);", night_s).group(1), (night_r, night_s))
    # D
    d1 = re.search(r"\.reader-article\s*:is\(([^)]*)\)\s*\{([^}]*)\}", css)
    check("src", "D .reader-article text classes #1a1a1a / #2C1810 read var(--text-primary)",
          bool(d1) and "1a1a1a" in d1.group(1) and "2C1810" in d1.group(1) and "var(--text-primary)" in d1.group(2), d1 and d1.group(0)[:200])


M_PAD = "() => { const a = document.querySelector('.reader-article'); const s = getComputedStyle(a); return [parseFloat(s.paddingLeft), parseFloat(s.paddingRight), innerWidth]; }"
M_COLOR = """() => { const a = document.querySelector('.reader-article'); const col = e => e && getComputedStyle(e).color;
  return {h2: col(a.querySelector('h2')), h3: col(a.querySelector('h3')), p: col(a.querySelector('p.text-\\\\[15px\\\\]')), fg: getComputedStyle(document.documentElement).getPropertyValue('--rd-fg').trim()}; }"""
M_CARDS = """() => { const mk = c => { const e = document.createElement('div'); e.className = c; e.textContent = 'x'; document.body.appendChild(e); return e; };
  const r = mk('home-resume'), s = mk('home-save'); const g = e => { const c = getComputedStyle(e); return [c.backgroundColor, c.borderTopColor, c.color, c.paddingLeft]; };
  const out = [g(r), g(s)]; r.remove(); s.remove(); return out; }"""


def app():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        for tag, kw, want in [("1440", {"viewport": {"width": 1440, "height": 900}}, 48), ("1024", {"viewport": {"width": 1024, "height": 768}}, 48),
                              ("800", {"viewport": {"width": 800, "height": 900}}, 24), ("iPhone 14", p.devices["iPhone 14"], 12)]:
            c = b.new_context(service_workers="block", locale="ru-RU", **kw)
            c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');")
            pg = c.new_page()
            pg.goto(f"{BASE}/ru-iast/vigraha-tattva/", wait_until="networkidle")
            pg.wait_for_timeout(900)
            m = pg.evaluate(M_PAD)
            check(tag, f"E chapter side padding = {want}", abs(m[0] - want) <= TOL and abs(m[1] - want) <= TOL, m)
            c.close()
        for theme in ["day", "sepia", "night"]:
            c = b.new_context(service_workers="block", locale="ru-RU", viewport={"width": 1280, "height": 800})
            tv = {"sepia": "sepia", "night": "night"}.get(theme)
            c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');"
                              + (f"localStorage.setItem('ap.readerTheme','{tv}');" if tv else ""))
            pg = c.new_page()
            pg.goto(f"{BASE}/ru-iast/maha-abhiseka/", wait_until="networkidle")
            pg.wait_for_timeout(900)
            col = pg.evaluate(M_COLOR)
            if theme == "day":
                check(theme, "D h2 = h3 = rgb(26, 26, 26)", col["h2"] == col["h3"] == "rgb(26, 26, 26)", col)
            elif theme == "sepia":
                check(theme, "D h2 = h3 = body text = rgb(42, 32, 22)", col["h2"] == col["h3"] == col["p"] == "rgb(42, 32, 22)", col)
            else:
                check(theme, "D h2 = h3 = body text (one colour)", col["h2"] == col["h3"] == col["p"], col)
            if theme == "night":
                cards = pg.evaluate(M_CARDS)
                check(theme, "C «Продолжить» = «Сохранение»: background, border, text colour, padding-left", cards[0] == cards[1], cards)
            c.close()
        b.close()


static()
if BASE:
    app()
n = sum(results)
print(f"\n{n}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
