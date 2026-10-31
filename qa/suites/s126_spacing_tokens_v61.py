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
    "--ds-band": "var(--rd-row-stripe)", "--radius-pill": "9999px",
}
EXPAND_OLD = {"--rd-accent": "var(--ap-gold)", "--ds-accent-deep": "var(--ap-gold)", "--ds-accent": "var(--ap-gold)",
              "--ds-radius-pill": "9999px"}
REMOVED_DECL = {"--rd-accent", "--ds-accent", "--ds-accent-deep"}


def expand(v, table):
    for _ in range(3):
        v = re.sub(r"var\((--[\w-]+)\)", lambda m: table.get(m.group(1), m.group(0)), v)
    return re.sub(r"\s+", " ", v.strip())


def decls(css, table):
    out = []
    for m in re.finditer(r"([\w-]+)\s*:\s*([^;{}]+);", css):
        if m.group(1) in REMOVED_DECL:
            continue
        out.append((m.group(1), expand(m.group(2), table)))
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


static()
n = sum(results)
print(f"\n{n}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
