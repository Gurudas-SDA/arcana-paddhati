"""V61 solis 7 — Vraja Lila msg 7207 (01.11): «по поводу новых токенов и системы — лучше автоматом подгоняй под имеющуюся и если будет
просьба сделать исключение и она обоснованна — то окей». (s6: msg 1920, 30.10; msg 7164, 31.10 — «сначала предупреждает… позже — останавливает».)
Suite izsauc qa/token_guard.py uz īstā koda (jaunu vērtību nav → exit 0). Pašpārbaude ar pagaidu mapi: jauna vērtība → exit 1 un ieteikums
ar tuvāko tokenu (13px → --space-12; #123456 → krāsas tokens); izņēmums ar reason+who → exit 0; izņēmums bez reason → exit 1; --warn → exit 0.
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
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} {'' if ok else str(info)[:600]}", flush=True)


def run(*args):
    p = subprocess.run([sys.executable, GUARD, *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


# 1) īstais kods: nav jaunu vērtību -> exit 0 (bloķējošais režīms)
rc, out = run()
check("real code: guard exits 0 in blocking mode (0 new values)", rc == 0 and ", 0 jaunas" in out, out)

with tempfile.TemporaryDirectory() as tmp:
    os.makedirs(os.path.join(tmp, "app"))
    os.makedirs(os.path.join(tmp, "components"))
    css = os.path.join(tmp, "app", "globals.css")
    tsx = os.path.join(tmp, "components", "X.tsx")
    base = os.path.join(tmp, "base.json")
    exf = os.path.join(tmp, "exc.json")
    open(css, "w").write(".a { color: var(--text); padding: var(--space-8); margin: 0; }\n.old { color:#abcdef; }\n/* color:#999999; */\n")
    open(tsx, "w").write('export const X = () => <div className="p-[var(--space-8)] w-[50%]" />;\n')
    rc0, o0 = run("--root", tmp, "--baseline", base, "--update-baseline")
    check("tmp: baseline built", rc0 == 0 and "#abcdef" in open(base).read(), o0)
    rc1, o1 = run("--root", tmp, "--baseline", base, "--exceptions", exf)
    check("tmp: clean code -> exit 0, no new values", rc1 == 0 and ", 0 jaunas" in o1, o1)

    open(css, "a").write(".b { padding: 13px; }\n")
    rc2, o2 = run("--root", tmp, "--baseline", base, "--exceptions", exf)
    check("tmp: new 13px -> exit 1", rc2 == 1, o2)
    check("tmp: suggestion 13px -> var(--space-12)", "13px → var(--space-12)" in o2, o2)

    open(css, "a").write(".c { border-radius: 7px; }\n")
    rc2b, o2b = run("--root", tmp, "--baseline", base, "--exceptions", exf)
    check("tmp: radius value suggests a radius token", "7px → var(--ds-radius-block)" in o2b, o2b)

    open(css, "a").write(".d { color:#123456; }\n")
    rc2c, o2c = run("--root", tmp, "--baseline", base, "--exceptions", exf)
    check("tmp: new colour -> exit 1 and a colour token suggested", rc2c == 1 and "#123456 → var(--" in o2c, o2c)
    check("tmp: pre-existing #abcdef, var(--…), 0, % and comments are not reported", "#abcdef" not in o2c and "999999" not in o2c and "50%" not in o2c, o2c)

    rcw, ow = run("--root", tmp, "--baseline", base, "--exceptions", exf, "--warn")
    check("tmp: --warn -> exit 0, still prints the suggestion", rcw == 0 and "13px → var(--space-12)" in ow, ow)

    exc = [{"value": "13px", "file": "app/globals.css", "reason": "legacy widget needs exact 13px", "who": "msg 9999"},
           {"value": "7px", "file": "app/globals.css", "reason": "x", "who": "msg 9998"},
           {"value": "#123456", "file": "app/globals.css", "reason": "brand logo colour", "who": "msg 9997"}]
    json.dump({"exceptions": exc}, open(exf, "w"))
    rc3, o3 = run("--root", tmp, "--baseline", base, "--exceptions", exf)
    check("tmp: exceptions with reason+who -> exit 0", rc3 == 0 and ", 0 jaunas" in o3, o3)

    exc[0]["reason"] = ""
    json.dump({"exceptions": exc}, open(exf, "w"))
    rc4, o4 = run("--root", tmp, "--baseline", base, "--exceptions", exf)
    check("tmp: exception without reason -> exit 1 (invalid entry)", rc4 == 1 and "nederīgs" in o4, o4)

    exc[0]["reason"] = "ok"
    exc[0]["who"] = ""
    json.dump({"exceptions": exc}, open(exf, "w"))
    rc5, o5 = run("--root", tmp, "--baseline", base, "--exceptions", exf)
    check("tmp: exception without who -> exit 1 (invalid entry)", rc5 == 1 and "nederīgs" in o5, o5)

# V81 (Vraja Lila msg 7729): the file was empty at V61; the first real exceptions (exact mockup values with no token) are in it now,
# so the check is "valid list, every entry has value, file, reason and who" instead of "empty"
_exc = json.load(open(os.path.join(ROOT, "qa", "token_guard_exceptions.json"))).get("exceptions")
check("real exceptions file exists and is a valid list (every entry has value, file, reason, who)",
      isinstance(_exc, list) and all(all(str(e.get(k, "")).strip() for k in ("value", "file", "reason", "who")) for e in _exc), _exc)

n = sum(results)
print(f"\n{n}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
