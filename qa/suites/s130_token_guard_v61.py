"""V61 solis 6 — Vraja Lila V61 solis 6 (msg 1920, 30.10; msg 7164, 31.10) — tikai brīdinājums; --strict vēlāk pēc Vrajas vārda.
«Автоматическая проверка перед выпуском: сначала предупреждает о новых значениях не из токенов, позже — останавливает».
Suite izsauc qa/token_guard.py uz īstā koda: brīdinājumi tiek izdrukāti, bet nekad nebloķē (PASS). Papildus pašpārbaude ar pagaidu
mapi: tīrs kods → 0 brīdinājumu; `color:#123456` / `p-[13px]` → brīdinājums; var(--…) un bāzē esošais → nav brīdinājuma; --strict → exit 1.
usage: python s130_token_guard_v61.py
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
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} {'' if ok else str(info)[:500]}", flush=True)


def run(*args):
    p = subprocess.run([sys.executable, GUARD, *args], capture_output=True, text=True)
    return p.returncode, p.stdout


# 1) īstais kods: brīdinājumi tikai izdrukāti, exit 0
rc, out = run()
warns = [l for l in out.splitlines() if l.startswith("BRĪDINĀJUMS token_guard")]
for l in warns:
    print("  " + l, flush=True)
check(f"real code: guard exits 0 (warn only; {len(warns)} warnings)", rc == 0, out)

# 2) pašpārbaude tmp mapē
with tempfile.TemporaryDirectory() as tmp:
    os.makedirs(os.path.join(tmp, "app"))
    os.makedirs(os.path.join(tmp, "components"))
    css = os.path.join(tmp, "app", "globals.css")
    tsx = os.path.join(tmp, "components", "X.tsx")
    base = os.path.join(tmp, "base.json")
    open(css, "w").write(".a { color: var(--text); padding: var(--space-8); margin: 0; }\n.old { color:#abcdef; }\n/* color:#999999; */\n")
    open(tsx, "w").write('export const X = () => <div className="p-[var(--space-8)] text-[color:var(--accent)] w-[50%]" />;\n')
    rc0, o0 = run("--root", tmp, "--baseline", base, "--update-baseline")
    check("tmp: baseline built, only the pre-existing #abcdef", "1 vērt" in o0 and "#abcdef" in open(base).read() and "999999" not in open(base).read(), o0)
    rc1, o1 = run("--root", tmp, "--baseline", base)
    check("tmp: clean code -> 0 warnings, exit 0", rc1 == 0 and "BRĪDINĀJUMS" not in o1, o1)
    open(css, "a").write(".b { color:#123456; padding: 13px; }\n")
    open(tsx, "a").write('export const Y = () => <div className="rounded-[10px] gap-[7px] text-[#abc123]" style={{ margin: "9px" }} />;\n')
    rc2, o2 = run("--root", tmp, "--baseline", base)
    need = ["color:#123456", "padding:13px", "rounded-[10px]", "gap-[7px]", "text-[#abc123]", "margin:9px"]
    check("tmp: new hard values -> warning for each, exit 0", rc2 == 0 and all(n in o2 for n in need), o2)
    check("tmp: pre-existing #abcdef, var(--…), 0, % and comments -> no warning", "#abcdef" not in o2 and "var(" not in o2 and "999999" not in o2 and "50%" not in o2, o2)
    rc3, _ = run("--root", tmp, "--baseline", base, "--strict")
    check("tmp: --strict -> exit 1", rc3 == 1)

n = sum(results)
print(f"\n{n}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
