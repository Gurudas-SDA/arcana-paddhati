"""V61 solis 8 — Vraja Lila msg 7207 (01.11): «по поводу новых токенов и системы - лучше автоматом подгоняй под имеющуюся и если будет
просьба сделать исключение и она обоснованна - то окей»; msg 7250 (02.11): «автоматически на ближайший токен»; msg 7251: «до и после»
(report); bot msg 2132: every replacement marked «заметно» / «мелко», «заметно» rows carry a selector.
qa/token_guard.py --fix: a NEW hard value is replaced with the nearest token var(--…) of the same group (colour / spacing / radius);
baseline and exceptions untouched; a value with no token in its group stays and still blocks. Without --fix: the old behaviour (blocks, leaves).
Technical threshold (Lipikāra, not a Vraja number): spacing/size/radius diff >= 4px or >= 20 % → «заметно»; colour: any channel >= 16/255.
usage: python s136_token_autofix_v61s8.py
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
GUARD = os.path.join(ROOT, "qa", "token_guard.py")
results = []


def check(name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} {'' if ok else str(info)[:700]}", flush=True)


def run(*args):
    p = subprocess.run([sys.executable, GUARD, *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


with tempfile.TemporaryDirectory() as tmp:
    for d in ("app", "components"):
        os.makedirs(os.path.join(tmp, d))
    css = os.path.join(tmp, "app", "globals.css")
    tsx = os.path.join(tmp, "components", "X.tsx")
    base, exf, rep = (os.path.join(tmp, n) for n in ("base.json", "exc.json", "report.md"))
    open(css, "w").write(".a { color: var(--text); padding: var(--space-8); }\n.old { color:#abcdef; }\n")
    open(tsx, "w").write('export const X = () => <div className="w-[50%]" />;\n')
    check("baseline built", run("--root", tmp, "--baseline", base, "--update-baseline")[0] == 0)
    NEW_CSS = (".b { padding: 13px; }\n.c { border-radius: 15px; }\n.d { color: #f5e6c9; }\n.e { margin: 30px; }\n"
               ".big { color: #123456; }\n.f { padding: 20px; }\n.w { width: 13px; }\n")
    open(css, "a").write(NEW_CSS)
    open(tsx, "a").write('export const Y = () => <div className="p-[13px]" />;\n')

    # (1) OLD behaviour = RED for the new demand: without --fix the value stays and the guard blocks
    rc, o = run("--root", tmp, "--baseline", base, "--exceptions", exf)
    check("without --fix: guard blocks (exit 1) and leaves 13px in the file", rc == 1 and "padding: 13px" in open(css).read(), o)

    # (2) --fix replaces with the nearest token
    rcf, of = run("--root", tmp, "--baseline", base, "--exceptions", exf, "--fix", "--report", rep)
    c = open(css).read()
    t = open(tsx).read()
    check("--fix: padding 13px -> var(--space-12)", "padding: var(--space-12)" in c, c)
    check("--fix: border-radius 15px -> a radius token", "border-radius: var(--" in c and "15px" not in c, c)
    check("--fix: margin 30px -> var(--space-32)", "margin: var(--space-32)" in c, c)
    check("--fix: colour #f5e6c9 -> a colour token", "#f5e6c9" not in c and "color: var(--" in c, c)
    check("--fix: Tailwind p-[13px] -> p-[var(--space-12)]", "p-[var(--space-12)]" in t, t)
    check("--fix: baseline value #abcdef and var()/% untouched", "color:#abcdef" in c and "w-[50%]" in t and "var(--space-8)" in c, c)
    check("--fix: width 13px (no token group) is NOT changed", "width: 13px" in c, c)
    check("--fix: prints «fails:rinda vecā → var(--x) (vērtība y)»", "app/globals.css:3 13px → var(--space-12) (vērtība 12px" in of, of)
    check("--fix: unfixable width still blocks (exit 1)", rcf == 1 and "width:13px" in of, of)

    # (3) second run without --fix: only the unfixable one remains; after removing it -> green
    rc2, o2 = run("--root", tmp, "--baseline", base, "--exceptions", exf)
    check("second run without --fix: only width:13px remains", rc2 == 1 and o2.count("KĻŪDA token_guard: ") == 1 and "width:13px" in o2, o2)
    open(css, "w").write(c.replace(".w { width: 13px; }\n", ""))
    rc3, o3 = run("--root", tmp, "--baseline", base, "--exceptions", exf)
    check("after fix, second run without --fix is green", rc3 == 0 and ", 0 jaunas" in o3, o3)

    # (4) report: до / после for each replacement; both categories; selector for «заметно»
    r = open(rep, encoding="utf-8").read()
    rows = [ln for ln in r.split("\n") if ln.startswith("| ") and "---" not in ln and "Файл:строка" not in ln]
    check("report has a row per replaced value (8)", len(rows) == 7, f"{len(rows)}\n{r}")
    check("report: every row has до (old value) and после (var(--…) = value)", all("var(--" in x for x in rows) and
          any("| 13px |" in x and "var(--space-12) = 12px" in x and "−1px" in x for x in rows), r)
    check("report: spacing 20px -> 16px (−4px) = заметно with selector .f", any("| 20px |" in x and "−4px" in x and "заметно" in x and ".f" in x for x in rows), r)
    check("report: both categories present", "заметно" in r and "мелко" in r, r)
    check("report: 13px/−1px = мелко; #123456 = заметно with selector .big",
          any("| 13px |" in x and "мелко" in x for x in rows) and any("#123456" in x and "заметно" in x and ".big" in x for x in rows), r)
    check("report: «мелко» rows have no selector, «заметно» rows have", all(x.rstrip().endswith("|  |") for x in rows if "мелко" in x) and
          all(not x.rstrip().endswith("|  |") for x in rows if "заметно" in x), r)
    check("--fix prints «TOKEN_FIX ZAMETNO: N» (N >= 1)", "TOKEN_FIX ZAMETNO: " in of and int(of.split("TOKEN_FIX ZAMETNO: ")[1].split()[0]) >= 1, of)
    check("--fix output marks each row заметно/мелко", of.count("; мелко)") + of.count("; заметно)") == 7, of)

    # (5) exception: value in the exceptions list is not changed
    open(css, "a").write(".x { padding: 13px; }\n")
    json.dump({"exceptions": [{"value": "13px", "file": "app/globals.css", "reason": "legacy needs 13px", "who": "msg 9999"}]}, open(exf, "w"))
    rce, oe = run("--root", tmp, "--baseline", base, "--exceptions", exf, "--fix")
    check("exception value is not changed by --fix", "padding: 13px" in open(css).read() and rce == 0 and "TOKEN_FIX" not in oe, oe)

    # (6) no tokens in group: hsl / alpha colours are left and block
    open(css, "w").write(open(css).read() + ".h { color: hsl(10, 20%, 30%); }\n.r { background: rgba(10,20,30,.5); }\n")
    rch, oh = run("--root", tmp, "--baseline", base, "--exceptions", exf, "--fix")
    ch = open(css).read()
    check("hsl() and rgba(alpha<1) are not changed and block", rch == 1 and "hsl(10, 20%, 30%)" in ch and "rgba(10,20,30,.5)" in ch, oh)

n = sum(results)
print(f"\n{n}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
