"""Gurudas 23.10 msg 868 (burtiski): «Tulkojumu trūkums netraucē turpināt darbu pie pašas grāmatas. Organizējiet procesu tā,
lai tulkošanas trūkums nekavē pamatdarba procesus.»
# tehniskais slieksnis Lipikāra, nav S noteikums; Gurudas msg 868

«Tulkojums gaida»: night_sync.py failed for some (language, section) pairs -> qa/tulkojumi_gaida.json; the book shows those
sections in English (or the previous translation + new subsections in English); lint L27/L31 accept that ONLY for the
listed pairs; L38 keeps the list honest. Everything else stays strict. All mutations on a temporary COPY (never data/).
  a  the real data with the list: lint exit 0; L27/L31 print [TULK GAIDA] for the listed pairs only
  b  the same copy WITHOUT the list: L27 and L31 FAIL (the English fallback is caught when not listed)
  c  with the list + one sanskrit letter changed in de «mangalacarana» (not listed) -> L27 FAIL
  d  with the list + «a.m.» in a uk «mangalacarana» text (not listed) -> L31 FAIL
  e  with the list + a non-translated language (ru) / quotes already translated (de upadesha-sara) listed -> L38 FAIL
  f  every listed section pair is in English or keeps a translation, and «Заключение» has the 11th subsection in every book
No browser, no server: python s104_tulk_gaida.py"""
import contextlib
import glob
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(REPO, "data")
LINT = os.path.join(REPO, "qa", "lint_content.py")
LIST = os.path.join(REPO, "qa", "tulkojumi_gaida.json")
sys.stdout.reconfigure(encoding="utf-8")
res = []


def chk(name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] data {name} {'' if ok else str(info)[:400]}", flush=True)


def run_lint(root):
    out = os.path.join(root, "lint.json")
    with contextlib.suppress(FileNotFoundError):
        os.remove(out)
    t0 = time.time() - 1
    p = subprocess.run([sys.executable, LINT, "--no-html", "--json", out], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=REPO, env=dict(os.environ, QA_REPO=root))
    rr = json.load(open(out, encoding="utf-8")) if os.path.exists(out) and os.path.getmtime(out) >= t0 else None
    by = {c["id"]: c for c in rr or []}
    return p.returncode, by, p.stdout


def copy_tree():
    tmp = tempfile.mkdtemp(prefix="s104_")
    shutil.copytree(DATA, os.path.join(tmp, "data"), ignore=shutil.ignore_patterns("desktop.ini"))
    for rel in ["scripts/parampara/check.json", "scripts/translate/i18n_sections.py", "scripts/moods/moods.json",
                "scripts/translate/glossary.uk.json"] + \
            [os.path.relpath(f, REPO) for f in glob.glob(os.path.join(REPO, "scripts", "**", "i18n.json"), recursive=True)]:
        src = os.path.join(REPO, rel)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(os.path.join(tmp, rel)), exist_ok=True)
            shutil.copy(src, os.path.join(tmp, rel))
    os.makedirs(os.path.join(tmp, "qa"), exist_ok=True)
    if os.path.exists(LIST):
        shutil.copy(LIST, os.path.join(tmp, "qa", "tulkojumi_gaida.json"))
    return tmp


def rm(tmp):
    shutil.rmtree(tmp, onexc=lambda fn, q, e: (os.chmod(q, stat.S_IWRITE), fn(q)))


def edit_book(tmp, lang, fn):
    f = os.path.join(tmp, "data", f"book.{lang}.json")
    d = json.load(open(f, encoding="utf-8"))
    fn(d)
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def sec(d, sid):
    return next(s for s in d["sections"] if s["id"] == sid)


pend = json.load(open(LIST, encoding="utf-8")).get("pending", []) if os.path.exists(LIST) else []
pairs = {(p["lang"], p["section"]) for p in pend}
print("tulkojums gaida:", ", ".join(f"{p['lang']}/{p['section']}{' (quotes)' if p['kind'] == 'moods' else ''}" for p in pend)
      or "nav")

# a + b + c + d on one copy, mutated step by step
tmp = copy_tree()
try:
    code, by, out = run_lint(tmp)
    chk("a real data + list: L27/L31/L38 pass", all(by.get(k, {}).get("ok") for k in ("L27", "L31", "L38")),
        f"exit {code} {[(k, by.get(k)) for k in ('L27', 'L31', 'L38')]}")
    tl = [ln for ln in out.splitlines() if "[TULK GAIDA]" in ln]
    listed = all(any(f"{l}/{s}" in ln for ln in tl) for l, s in {(l, s) for l, s in pairs if l == "uk"}) if pend else True
    chk("a [TULK GAIDA] lines name only listed pairs", (bool(tl) == bool(pend)) and listed and all(
        all(tuple(x.split(" ")[0].split("/")) in pairs for x in ln.split(": ", 1)[1].split(", ")) for ln in tl), tl)

    if pend:
        os.remove(os.path.join(tmp, "qa", "tulkojumi_gaida.json"))
        code, by, _ = run_lint(tmp)
        chk("b without the list: L27 and L31 FAIL (English fallback caught)", code != 0 and by.get("L27", {}).get("ok") is False
            and (by.get("L31", {}).get("ok") is False or not any(l == "uk" for l, _ in pairs)), f"exit {code} {by.get('L27')} {by.get('L31')}")
        shutil.copy(LIST, os.path.join(tmp, "qa", "tulkojumi_gaida.json"))

    def l27_bad(d):
        for b in sec(d, "mangalacarana")["content"]:
            if b.get("sanskrit") and "ā" in b["sanskrit"]:
                b["sanskrit"] = b["sanskrit"].replace("ā", "a", 1)
                return
        raise AssertionError("no sanskrit with ā in de mangalacarana")
    edit_book(tmp, "de", l27_bad)
    code, by, _ = run_lint(tmp)
    chk("c list + de «mangalacarana» sanskrit ā→a (not listed) → L27 FAIL", code != 0 and by.get("L27", {}).get("ok") is False
        and by.get("L27", {}).get("hits", 0) >= 1, f"exit {code} {by.get('L27')}")
finally:
    rm(tmp)

tmp = copy_tree()
try:
    def l31_bad(d):
        for b in sec(d, "mangalacarana")["content"]:
            if b.get("type") == "text" and b.get("content"):
                b["content"] += " 4:10 a.m."
                return
        for b in sec(d, "mangalacarana")["content"]:
            if b.get("translation"):
                b["translation"] += " 4:10 a.m."
                return
        raise AssertionError("no text in uk mangalacarana")
    edit_book(tmp, "uk", l31_bad)
    code, by, _ = run_lint(tmp)
    chk("d list + «a.m.» in uk «mangalacarana» (not listed) → L31 FAIL", code != 0 and by.get("L31", {}).get("ok") is False,
        f"exit {code} {by.get('L31')}")
finally:
    rm(tmp)

tmp = copy_tree()
try:
    lp = os.path.join(tmp, "qa", "tulkojumi_gaida.json")
    d = json.load(open(lp, encoding="utf-8")) if os.path.exists(lp) else {"pending": []}
    d["pending"] = d.get("pending", []) + [{"lang": "ru", "section": "conclusion", "kind": "section",
                                            "gen": "scripts/chapters/ch99_conclusion"}]
    json.dump(d, open(lp, "w", encoding="utf-8"), ensure_ascii=False)
    code, by, _ = run_lint(tmp)
    chk("e ru listed → L38 FAIL", code != 0 and by.get("L38", {}).get("ok") is False, f"exit {code} {by.get('L38')}")
    moods = json.load(open(os.path.join(REPO, "scripts", "moods", "moods.json"), encoding="utf-8"))
    us = [m for m in moods if m["target"] == "upadesha-sara"]
    done_lang = next((l for l in ("de", "hu", "lt", "lv", "fr", "es", "it", "uk", "pt")
                      if us and all(l in (m.get("translations") or {}) and all(l in (a.get("translation") or {})
                                                                              for a in m.get("more") or []) for m in us)), None)
    if done_lang:
        d["pending"] = [p for p in d["pending"] if p["lang"] != "ru"] + [{"lang": done_lang, "section": "upadesha-sara",
                                                                         "kind": "moods", "gen": "scripts/moods"}]
        json.dump(d, open(lp, "w", encoding="utf-8"), ensure_ascii=False)
        code, by, _ = run_lint(tmp)
        chk(f"e {done_lang}/upadesha-sara quotes (already translated) listed → L38 FAIL", code != 0 and by.get("L38", {}).get("ok") is False,
            f"exit {code} {by.get('L38')}")
finally:
    rm(tmp)

# f
en = json.load(open(os.path.join(DATA, "book.json"), encoding="utf-8"))
n_en = len(sec(en, "conclusion")["subsections"])
bad = []
for f in sorted(glob.glob(os.path.join(DATA, "book*.json"))):
    b = json.load(open(f, encoding="utf-8"))
    ss = [x["id"] for x in sec(b, "conclusion")["subsections"]]
    if len(ss) != n_en or ss[-1] != "conclusion-ashtakala":
        bad.append((os.path.basename(f), len(ss), ss[-1:]))
chk(f"f «Заключение» has {n_en} subsections, the last = conclusion-ashtakala, in every book (English until translated)", not bad, bad)

print(f"s104: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
