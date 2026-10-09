"""Night 09.10 (A68, Gurudas 08.10) — Sanskrit stays Sanskrit, spelled as in the sources, in every language.
  a  translation caches (scripts/translate/cache/**, gitignored, used by tr.py assemble), generator i18n.json and the
     books: «pādya-pātra» / «arghya-pātra» only — never «padya-pātra» / «argya-pātra» (HU cache had «padya-pātra»)
  b  scripts/translate/night_sync.py exits ≠ 0 when any language/section ended in FAIL (exit 0 when all ok/cached)
  c  no gloss words inside `sanskrit` fields: no Cyrillic in book.ru-iast.json (was «махамантру»,
     «для одного листа … или …»), no English «for one leaf … or … for several leaves» in any book; the 12-puspa
     gloss lives in the verse `translation` of every book
  d  four EN IAST misspellings fixed after RU-IAST and the sources, in every book / cache / i18n.json:
     māyāvāda (not māyāvada), aravinda-locanaṁ (not locananaṁ), jāgṛvāṁsaḥ (not «jāgṛvaṁ saḥ»), tapta-kāñcana (not kāṣcana)
  e  qa lint L27 is strict for RU-IAST too: every `sanskrit` field of book.ru-iast.json = book.json, a difference is a hit
     (Codex review 09.10: the lint exit code is checked, the result JSON must be written by THIS run — a crash with an
     old JSON is a FAIL — and a negative case: one RU-IAST sanskrit difference in a temporary COPY of data/ → L27 FAIL)
No browser, no server: python s28_a68_night_0910.py"""
import contextlib
import glob
import io
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(REPO, "data")
TR = os.path.join(REPO, "scripts", "translate")
sys.stdout.reconfigure(encoding="utf-8")
res = []


def chk(name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] data {name} {'' if ok else str(info)[:400]}", flush=True)


def sk_fields(o, path=()):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "sanskrit":
                yield "/".join(map(str, path + (k,))), v
            yield from sk_fields(v, path + (k,))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from sk_fields(v, path + ((v.get("id") if isinstance(v, dict) and isinstance(v.get("id"), str) else i),))


BOOKS = sorted(glob.glob(os.path.join(DATA, "book*.json")))
CACHES = sorted(glob.glob(os.path.join(TR, "cache", "**", "*.json"), recursive=True))
I18N = sorted(glob.glob(os.path.join(REPO, "scripts", "**", "i18n.json"), recursive=True))
I18N += sorted(glob.glob(os.path.join(TR, "glossary.*.json")))   # glossaries feed the translators
TEXT = {f: open(f, encoding="utf-8").read() for f in BOOKS + CACHES + I18N}
rel = lambda f: os.path.relpath(f, REPO).replace("\\", "/")  # noqa: E731

# ---------- a ----------
bad = [rel(f) for f, t in TEXT.items() if re.search(r"(?<![\wāĀ])(?:[Pp]adya|[Aa]rgya)-pātr", t)]
chk("a «pādya-pātra» / «arghya-pātra» (never «padya-/argya-pātra») in books, translation caches, i18n.json "
    f"({len(CACHES)} cache files)", not bad, bad)

# ---------- b ----------
sys.path.insert(0, TR)
import night_sync as NS  # noqa: E402


def run_main(fake):
    orig_run, orig_argv, orig_log = NS.run_lang, sys.argv, NS.log
    NS.run_lang = lambda lang, sids, key_i, force: (lang, fake(lang))
    NS.log = lambda msg: None   # the real night_sync.log stays clean
    sys.argv = ["night_sync.py", "parampara", "--langs", "lv,de"]
    code = 0
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            NS.main()
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    finally:
        NS.run_lang, sys.argv, NS.log = orig_run, orig_argv, orig_log
    return code


c_fail = run_main(lambda l: {"parampara": "FAIL all models failed" if l == "de" else "ok cx/gpt-6.1-sol"})
c_ok = run_main(lambda l: {"parampara": "cached" if l == "de" else "ok cx/gpt-6.1-sol"})
chk("b night_sync exits ≠ 0 when a section ended in FAIL, 0 when all ok/cached", c_fail != 0 and c_ok == 0,
    f"exit with FAIL={c_fail}, all ok={c_ok}")

# ---------- c ----------
books = {os.path.basename(f): json.load(open(f, encoding="utf-8")) for f in BOOKS}
cyr = [(k, v[:60]) for k, v in sk_fields(books["book.ru-iast.json"]) if re.search(r"[А-Яа-яЁё]", v)]
chk("c no Cyrillic (Russian glosses) in book.ru-iast.json sanskrit fields", not cyr, cyr)
gloss = [(b, k) for b, d in books.items() if b != "book.ru.json" for k, v in sk_fields(d)
         if re.search(r"\((?:for|для)\b|\b(?:or|leaves|several|или)\b", v)]
chk("c no gloss words («for one leaf», «or», «leaves») in any book's sanskrit field", not gloss, gloss)


def puspa(d):
    s = next(x for x in d["sections"] if x["id"] == "arcana-procedure")
    s = next(x for x in s["subsections"] if x["id"] == "12-puspa")
    return next(x for x in s["content"] if x.get("type") == "verse" and re.search(r"tulasī-|туласӣ-", x.get("sanskrit", "")))


# Codex review 09.10 (Low): not only «not empty» — the RU / EN wording of the moved note is there, and the
# sanskrit field of no book carries it
NOTE = {"book.ru.json": ("для одного листа", "для нескольких листьев"),
        "book.ru-iast.json": ("для одного листа", "для нескольких листьев"),
        "book.json": ("one leaf", "several leaves")}
NOTE_ANY = [w for ws in NOTE.values() for w in ws]
nog = []
for b, d in books.items():
    v = puspa(d)
    tr = (v.get("translation") or "").strip()
    if not tr or any(w not in tr for w in NOTE.get(b, ())):
        nog.append((b, "translation", tr[:80]))
    if any(w in v.get("sanskrit", "") for w in NOTE_ANY):
        nog.append((b, "sanskrit", v["sanskrit"][:80]))
chk("c 12-puspa: the «one leaf / several leaves» note is in the verse translation of every book "
    "(RU «для одного листа … для нескольких листьев», EN «one leaf … several leaves»), not in the sanskrit field",
    not nog, nog)

# ---------- d ----------
WRONG = {"māyāvada": "māyāvāda", "locananaṁ": "locanaṁ", "jāgṛvaṁ": "jāgṛvāṁsaḥ", "kāṣcana": "kāñcana"}
left = [(rel(f), w) for f, t in TEXT.items() for w in WRONG if w in t]
chk("d no «māyāvada / aravinda-locananaṁ / jāgṛvaṁ saḥ / tapta-kāṣcana» in books, caches, i18n.json", not left, left)
en = dict(sk_fields(books["book.json"]))
want = {"sections/mangalacarana/content/16/sanskrit": "māyāvāda-tamo-ghnāya",
        "sections/daily-duties-brahma-muhurta/subsections/morning-prayers/content/2/sanskrit": "aravinda-locanaṁ\n",
        "sections/daily-duties-brahma-muhurta/subsections/sadhararana-acamana/content/17/sanskrit": "jāgṛvāṁsaḥ samindhate",
        "sections/arcana-procedure/subsections/16-pranama/content/6/sanskrit": "tapta-kāñcana-gaurāṅgi"}
miss = [k for k, w in want.items() if w not in en.get(k, "")]
chk("d EN sanskrit has the source spelling at all four places", not miss, miss)

# ---------- e ----------
ri = dict(sk_fields(books["book.ru-iast.json"]))
diff = [k for k in en if ri.get(k) != en[k]] + [k for k in ri if k not in en]
chk("e every sanskrit field of book.ru-iast.json = book.json (byte-identical)", not diff, diff)
LINT = os.path.join(REPO, "qa", "lint_content.py")


def run_lint(root, out):
    """lint_content.py --no-html over <root>/data (QA_REPO); returns (exit code, results or None, stderr tail).
    The result file is removed first and must be newer than the start — an old JSON never counts."""
    with contextlib.suppress(FileNotFoundError):
        os.remove(out)
    t0 = time.time() - 1
    p = subprocess.run([sys.executable, LINT, "--no-html", "--json", out], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=REPO, env=dict(os.environ, QA_REPO=root))
    fresh = os.path.exists(out) and os.path.getmtime(out) >= t0
    return p.returncode, (json.load(open(out, encoding="utf-8")) if fresh else None), (p.stderr or "")[-300:]


lint = os.path.join(REPO, "qa", ".results", "lint_s28.json")
os.makedirs(os.path.dirname(lint), exist_ok=True)
code, rr, err = run_lint(REPO, lint)
l27 = next((c for c in rr or [] if c["id"] == "L27"), {})
chk("e lint ran to the end on the real data: exit 0 and a fresh result JSON (no crash with an old JSON)",
    code == 0 and rr is not None, f"exit {code}, fresh JSON {rr is not None} {err}")
chk("e lint L27 compares RU-IAST strictly (title names ru-iast) and passes", "ru-iast" in l27.get("title", "") and l27.get("ok"), l27)

# negative case: a temporary COPY of data/ (never data/ itself) with ONE RU-IAST sanskrit difference → L27 FAIL
tmp = tempfile.mkdtemp(prefix="s28_l27_")
try:
    shutil.copytree(DATA, os.path.join(tmp, "data"), ignore=shutil.ignore_patterns("desktop.ini"))
    os.makedirs(os.path.join(tmp, "scripts", "parampara"))
    shutil.copy(os.path.join(REPO, "scripts", "parampara", "check.json"), os.path.join(tmp, "scripts", "parampara"))
    key = "sections/mangalacarana/content/16/sanskrit"
    f = os.path.join(tmp, "data", "book.ru-iast.json")
    d = json.load(open(f, encoding="utf-8"))
    v = d["sections"][[s_["id"] for s_ in d["sections"]].index("mangalacarana")]["content"][16]
    assert "māyāvāda" in v["sanskrit"], v["sanskrit"][:80]
    v["sanskrit"] = v["sanskrit"].replace("māyāvāda", "māyāvada", 1)   # one letter: ā → a
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    ncode, nr, nerr = run_lint(tmp, os.path.join(tmp, "lint_neg.json"))
    n27 = next((c for c in nr or [] if c["id"] == "L27"), {})
    chk("e negative: one RU-IAST sanskrit difference (māyāvāda → māyāvada, temp copy) → L27 FAIL, lint exit ≠ 0",
        nr is not None and n27.get("ok") is False and n27.get("hits", 0) >= 1 and ncode != 0,
        f"exit {ncode}, L27 {n27} {nerr} ({key})")
finally:
    shutil.rmtree(tmp, onexc=lambda fn, q, e: (os.chmod(q, stat.S_IWRITE), fn(q)))

print(f"s28: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
