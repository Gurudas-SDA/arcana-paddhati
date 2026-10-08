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
No browser, no server: python s28_a68_night_0910.py"""
import contextlib
import glob
import io
import json
import os
import re
import subprocess
import sys

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


nog = [b for b, d in books.items() if not (puspa(d).get("translation") or "").strip()]
chk("c 12-puspa: the «one leaf / several leaves» note is in the verse translation of every book", not nog, nog)

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
lint = os.path.join(REPO, "qa", ".results", "lint_s28.json")
os.makedirs(os.path.dirname(lint), exist_ok=True)
subprocess.run([sys.executable, os.path.join(REPO, "qa", "lint_content.py"), "--no-html", "--json", lint],
               capture_output=True, cwd=REPO)
l27 = next((c for c in json.load(open(lint, encoding="utf-8")) if c["id"] == "L27"), {})
chk("e lint L27 compares RU-IAST strictly (title names ru-iast) and passes", "ru-iast" in l27.get("title", "") and l27.get("ok"), l27)

print(f"s28: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
