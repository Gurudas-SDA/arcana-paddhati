"""V61 step 2 — Враджа Лила 31.10.2026 02:52 «продолжай по другим задачам, всё по плану» (plan step 2, approved: «Основа без видимых
изменений: шкала отступов и роли становятся токенами (одно место, где они заданы); плюс вопросы 7, 8, 9»; answers 7 ✔, 8 ✔, 9 ✔
«подключить, где подходит, остальные удалить»; spacing scale: Vraja_Lila/faili/2026.10.30_V61 Шкала отступов.md).
Visible change = 0. Checks (static, no server):
  A) the spacing scale 4·8·12·16·24·32 (+48, +2 dense) and the role tokens are declared ONCE, in design-system/tokens.css;
  B) every declaration of app/globals.css and design-system/components.css, after expanding the new tokens back to their value,
     equals the same declaration at the step-1 commit (BASE_REF) — nothing but the token substitution changed (computed value identical);
  C) q7 the gold has one name (--accent): --rd-accent, --ds-accent, --ds-accent-deep are gone; q8 scrim / 44 px / 150 ms / 220 ms read
     tokens; q9 the six dead tokens: --ds-band, --ds-band-active, --ds-row-lit are connected, --ds-row-hover, --ds-text, --ds-text-muted removed.
# tehniskais slieksnis Lipikāra, nav S noteikums: minimum counts of substituted places (spacing >= 25, 44 px >= 5, durations >= 12).
  E) Q8 «тонкие линии» (Враджа Лила 31.10.2026 08:42, V grupa msg 2018, variant «а»: «один токен, в сепии свой оттенок #DCCCAC — линии
     боковой панели в сепии станут чуть темнее»): the thin lines read ONE token --line-hairline (tokens.css: day #E8DCC8, sepia #DCCCAC,
     night #3A3128 = the same visible colour as the night rules gave before); no #E8DCC8 thin line is left in tsx / css.
     B is adapted: the three --rd-border declarations (day / sepia / night) now read var(--line-hairline) and are compared with the step-1
     values through the token (HL); every other declaration is still compared one to one.
usage: python s126_spacing_tokens_v61.py
"""
import os
import re
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
BASE_REF = "19e7f5f"  # V61 step 1 (mantri/v61-s1 head): the values before step 2
FILES = ["app/globals.css", "design-system/components.css"]
results = []


def check(where, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {where} {name} {'' if ok else str(info)[:500]}", flush=True)


def strip(t):
    return re.sub(r"/\*.*?\*/", "", t, flags=re.S)


def now(path):
    return strip(open(os.path.join(ROOT, path), encoding="utf-8").read())


def before(path):
    return strip(subprocess.check_output(["git", "-C", ROOT, "show", f"{BASE_REF}:{path}"]).decode("utf-8"))


# new token -> the literal / old reference it stands for
EXPAND_NEW = {
    "--space-4": "4px", "--space-8": "8px", "--space-12": "12px", "--space-16": "16px", "--space-24": "24px", "--space-32": "32px",
    "--target": "44px", "--dur-fast": "150ms", "--dur-slide": "220ms", "--mark-scrim": "rgba(0, 0, 0, 0.6)",
    "--accent": "var(--ap-gold)", "--ds-row-lit": "var(--ap-band-toc)", "--ds-band-active": "var(--rd-row-active)",
    "--ds-band": "var(--rd-row-stripe)", "--radius-pill": "9999px", "--line-hairline": "HL",
}
EXPAND_OLD = {"--rd-accent": "var(--ap-gold)", "--ds-accent-deep": "var(--ap-gold)", "--ds-accent": "var(--ap-gold)",
              "--ds-radius-pill": "9999px"}
REMOVED_DECL = {"--rd-accent", "--ds-accent", "--ds-accent-deep"}


def expand(v, table):
    for _ in range(3):
        v = re.sub(r"var\((--[\w-]+)\)", lambda m: table.get(m.group(1), m.group(0)), v)
    return re.sub(r"\s+", " ", v.strip())


HL_OLD = {"#E8DCC8", "#DCCCAC", "#3A3128"}  # Q8: --rd-border at step 1 (day / sepia / night) = now the token --line-hairline


def decls(css, table):
    out = []
    for m in re.finditer(r"([\w-]+)\s*:\s*([^;{}]+);", css):
        if m.group(1) in REMOVED_DECL:
            continue
        v = expand(m.group(2), table)
        if m.group(1) == "--rd-border" and v in HL_OLD:
            v = "HL"
        out.append((m.group(1), v))
    return out


def gone(name, text):
    return not re.search(re.escape(name) + r"(?![\w-])", text)


def static():
    tok = now("design-system/tokens.css")
    allcss = "\n".join(now(f) for f in ["app/globals.css", "design-system/components.css", "design-system/tokens.css"])
    side = open(os.path.join(ROOT, "components", "Sidebar.tsx"), encoding="utf-8").read()
    # A one place
    for n, v in [("4", "4px"), ("8", "8px"), ("12", "12px"), ("16", "16px"), ("24", "24px"), ("32", "32px"), ("48", "48px")]:
        d = re.findall(rf"(?m)^\s*--space-{n}\s*:\s*([^;]+);", allcss)
        check("src", f"A --space-{n} declared once = {v}", len(d) == 1 and d[0].strip() == v, d)
    check("src", "A --space-dense (2px exception) declared once", len(re.findall(r"(?m)^\s*--space-dense\s*:\s*2px;", allcss)) == 1)
    roles = ["--gap-row", "--gap-buttons", "--gap-label-field", "--gap-group", "--gap-paragraph", "--pad-window", "--gap-heading",
             "--pad-screen", "--pad-screen-wide", "--pad-window-wide", "--gap-block", "--gap-section", "--pad-page-bottom"]
    for r in roles:
        d = re.findall(rf"(?m)^\s*{r}\s*:\s*var\(--space-(\d+)\);", tok)
        check("src", f"A role {r} declared once in tokens.css as a scale step", len(d) == 1, d)
    check("src", "A the scale is declared only in tokens.css", all(not re.search(r"(?m)^\s*--space-\d+\s*:", now(f)) for f in FILES))
    # B equal to before
    for f in FILES:
        new, old = decls(now(f), EXPAND_NEW), decls(before(f), EXPAND_OLD)
        bad = [(i, a, b) for i, (a, b) in enumerate(zip(new, old)) if a != b]
        check("src", f"B {f}: {len(new)} declarations equal the step-1 values after expanding the tokens",
              len(new) == len(old) and not bad, (len(new), len(old), bad[:3]))
    css = now("app/globals.css") + now("design-system/components.css")
    n_sp = len(re.findall(r"var\(--space-\d+\)", css))
    check("src", f"B spacing declarations read the scale (>= 25, now {n_sp})", n_sp >= 25, n_sp)
    # C q7
    for n in ["--rd-accent", "--ds-accent", "--ds-accent-deep"]:
        check("src", f"C q7 {n} is gone", gone(n, allcss) and gone(n, side))
    check("src", "C q7 the one gold name --accent is used", len(re.findall(r"var\(--accent\)", css)) >= 10)
    # q8
    check("src", "C q8 scrim via --mark-scrim in 3 rules, rgba(0,0,0,0.6) only in --lang-dim",
          css.count("var(--mark-scrim)") >= 3 and len(re.findall(r"rgba\(0, 0, 0, 0\.6\)", css)) == 1, css.count("var(--mark-scrim)"))
    check("src", "C q8 44 px reads --target (>= 5)", css.count("var(--target)") >= 5 and not re.search(r":\s*44px;", css), css.count("var(--target)"))
    check("src", "C q8 150 ms / 220 ms read --dur-fast / --dur-slide (>= 12)",
          css.count("var(--dur-fast)") + css.count("var(--dur-slide)") >= 12 and not re.search(r"\b(150|220)ms", css))
    # q9
    check("src", "C q9 --ds-row-lit connected in the lit «Содержание» rows (6), --ap-band-toc not used there",
          side.count("var(--ds-row-lit)") == 6 and "var(--ap-band-toc)" not in side, side.count("var(--ds-row-lit)"))
    check("src", "C q9 --ds-band / --ds-band-active connected (selected row, zebra)",
          css.count("var(--ds-band-active)") >= 5 and css.count("var(--ds-band)") >= 1)
    for n in ["--ds-row-hover", "--ds-text", "--ds-text-muted"]:
        check("src", f"C q9 dead token {n} removed", gone(n, allcss))
    # D) a CSS rule that targets a Tailwind class like .bg-[var(--x)] must still find that class in the components — a renamed
    #    class leaves the rule dead and changes the look (31.10 pixel check: sepia lit «Содержание» row text after --ap-band-toc
    #    -> --ds-row-lit in Sidebar.tsx; app/globals.css V47b sepia selector kept the old name)
    src = ""
    for d in ["components", "app"]:
        for dp, _, fs in os.walk(os.path.join(ROOT, d)):
            for f in fs:
                if f.endswith((".tsx", ".ts")):
                    src += open(os.path.join(dp, f), encoding="utf-8").read()
    for path in FILES:
        for pre, var in sorted(set(re.findall(r"\.([a-z-]+)-\\\[var\\\((--[a-z0-9-]+)\\\)\\\]", now(path)))):
            cls = f"{pre}-[var({var})]"
            check(path, f"D class selector .{cls} still used in components", cls in src)

    # E) Q8 thin lines: one token
    t = strip(open(os.path.join(ROOT, "design-system/tokens.css"), encoding="utf-8").read())
    g = now("app/globals.css")
    for theme, val in [(None, "#E8DCC8"), ("sepia", "#DCCCAC"), ("night", "#3A3128")]:
        if theme is None:
            blk = re.search(r":root\s*\{[^}]*?--line-hairline\s*:\s*([^;]+);", t)
        else:
            blk = re.search(r'html\[data-reader-theme="' + theme + r'"\]\s*\{[^}]*?--line-hairline\s*:\s*([^;]+);', t)
        check("src", f"E q8 --line-hairline {theme or 'day'} = {val} in tokens.css", blk and blk.group(1).strip().upper() == val, blk and blk.group(1))
    check("src", "E q8 --line-hairline declared 3 times only (day, sepia, night)", len(re.findall(r"(?m)^\s*--line-hairline\s*:", allcss)) == 3)
    rb = re.findall(r"(?m)^\s*--rd-border\s*:\s*([^;]+);", g)
    check("src", "E q8 --rd-border (day, sepia, night) all read var(--line-hairline)", rb == ["var(--line-hairline)"] * 3, rb)
    check("src", "E q8 --ds-line (control lines) reads var(--line-hairline) at :root",
          re.search(r":root\s*\{[^}]*?--ds-line\s*:\s*var\(--line-hairline\)", t) is not None)
    # no #E8DCC8 thin line left; allowed = the two dead night override selectors (kept so B stays equal)
    left = []
    night_sel = re.compile(r'^\s*html\[data-reader-theme="night"\] \.(bg|border)-\\\[\\#E8DCC8\\\]')
    for d in ["components", "app", "design-system"]:
        for dp, _, fs in os.walk(os.path.join(ROOT, d)):
            for f in fs:
                if f.endswith((".tsx", ".ts", ".css")):
                    txt = open(os.path.join(dp, f), encoding="utf-8").read()
                    if f.endswith(".css"):
                        txt = strip(txt)
                    for ln, line in enumerate(txt.splitlines(), 1):
                        if re.search(r"E8DCC8", line, re.I) and not night_sel.match(line) and not (f == "tokens.css" and "--line-hairline" in line) \
                                and not (f == "globals.css" and line.strip() == "border: 1px solid #E8DCC8;"):
                            left.append(f"{f}:{ln}")
    check("src", "E q8 no #E8DCC8 thin line left in tsx / css (allowed: the day value of the token, 2 dead night selectors, the .hs-peek frame)", not left, left[:8])
    n_tok = sum(open(os.path.join(ROOT, c), encoding="utf-8").read().count("border-[color:var(--line-hairline)]")
                for c in ["components/Sidebar.tsx", "components/SectionContent.tsx", "components/MoodBlock.tsx"])
    check("src", f"E q8 the 10 + 3 + 3 thin lines of Sidebar / SectionContent / MoodBlock read the token (now {n_tok}, want 16)", n_tok == 16, n_tok)
    # the .hs-peek (floating picture) frame is NOT a sidebar line and has no night rule: it stays #E8DCC8 in all three themes, otherwise night would
    # change from #E8DCC8 to #3A3128 (night must stay 0 px, Vraja's choice «а» concerns the sidebar lines)
    check("src", "E q8 .hs-peek frame stays #E8DCC8 (night 0 px)", re.search(r"\.hs-peek\s*\{[^}]*?border:\s*1px solid #E8DCC8;", g) is not None)


static()
n = sum(results)
print(f"\n{n}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
