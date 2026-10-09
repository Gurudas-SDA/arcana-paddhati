"""Night 09.10 — «tulasī-patram» (leaf), not «tulasī-pātram» (vessel), per source.
Source: Библиотека/…/Арчана-паддхати (The Process of Deity Worship)/_исходники/hints/p055.txt r.14 «tulasi-patram»;
draft «Подношение бхоги — черновик 2026-10-05.md» r.149 «tulasī-patraṁ». pātra = vessel, patra = leaf.
  a  no «tulasī-pātra…» / «туласӣ-па̄тра…» in any book, translation cache, i18n.json or glossary
  b  12-puspa verse (arcana-procedure) sanskrit = «etat tulasī-patram / etāni tulasī-patrāṇi\\nklīṁ kṛṣṇāya namaḥ»
     identical in every IAST book; RU Cyrillic has «туласӣ-патрам»; RU / RU-IAST wbw gloss the leaf form
  c  the 16-items label (main-worship-sixteen-items) has «tulasī-patram» in every book (RU: «туласӣ-патрам»)
  d  guard: vessel words stay vessel — «arghya-pātra» / «pādya-pātra» still present in book.json
No browser, no server: python s29_tulasi_patram_0910.py"""
import glob
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(REPO, "data")
TR = os.path.join(REPO, "scripts", "translate")
sys.stdout.reconfigure(encoding="utf-8")
res = []


def chk(name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] data {name} {'' if ok else str(info)[:400]}", flush=True)


nfc = lambda s: unicodedata.normalize("NFC", s)  # noqa: E731
rel = lambda f: os.path.relpath(f, REPO).replace("\\", "/")  # noqa: E731
BOOKS = sorted(glob.glob(os.path.join(DATA, "book*.json")))
CACHES = sorted(glob.glob(os.path.join(TR, "cache", "**", "*.json"), recursive=True))
I18N = sorted(glob.glob(os.path.join(REPO, "scripts", "**", "i18n.json"), recursive=True))
I18N += sorted(glob.glob(os.path.join(TR, "glossary.*.json")))
TEXT = {f: nfc(open(f, encoding="utf-8").read()) for f in BOOKS + CACHES + I18N}

# ---------- a ----------
BAD = re.compile(nfc(r"tulas[iī][\s\-]*pātra|туласӣ[\s\-]*па̄тра"), re.I)
bad = [f"{rel(f)}: {m.group(0)}" for f, t in TEXT.items() for m in BAD.finditer(t)]
chk(f"a no «tulasī-pātra…» / «туласӣ-па̄тра…» in books, caches ({len(CACHES)}), i18n/glossaries", not bad, bad)

# ---------- b ----------
WANT = "etat tulasī-patram / etāni tulasī-patrāṇi\nklīṁ kṛṣṇāya namaḥ"


def puspa12(book):
    sec = next(s for s in book["sections"] if s["id"] == "arcana-procedure")
    stack, found = [sec], None
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            if o.get("id") == "12-puspa":
                found = o
                break
            stack.extend(o.values())
        elif isinstance(o, list):
            stack.extend(o)
    assert found, "12-puspa not found"
    return [v for v in found["content"] if v.get("type") == "verse" and "tulas" in nfc(v.get("sanskrit", "")).lower()
            or v.get("type") == "verse" and "туласӣ" in nfc(v.get("sanskrit", ""))]


iast_bad, ru_bad, wbw_bad = [], [], []
for f in BOOKS:
    b = json.load(open(f, encoding="utf-8"))
    vs = puspa12(b)
    if not vs:
        iast_bad.append(f"{rel(f)}: no tulasī verse")
        continue
    v = vs[0]
    sk = nfc(v["sanskrit"])
    if f.endswith("book.ru.json"):
        if "туласӣ-патрам" not in sk or "па̄трам" in nfc(sk.replace("ета̄ни", "")).split("/")[0]:
            ru_bad.append(sk[:80])
    elif sk != nfc(WANT):
        iast_bad.append(f"{rel(f)}: {sk[:80]!r}")
    w = nfc(v.get("wbw", ""))
    if w and not ("tulasī-patram —" in w or "туласӣ-патрам —" in w):
        wbw_bad.append(f"{rel(f)}: {w[:80]}")
chk("b 12-puspa sanskrit = «etat tulasī-patram / …» identical in every IAST book", not iast_bad, iast_bad)
chk("b 12-puspa RU Cyrillic «туласӣ-патрам»", not ru_bad, ru_bad)
chk("b 12-puspa wbw (RU, RU-IAST) gloss «tulasī-patram» / «туласӣ-патрам»", not wbw_bad, wbw_bad)

# ---------- c ----------
lab_bad = []
for f in BOOKS:
    t = TEXT[f]
    want = "⟦етат туласӣ-патрам /" if f.endswith("book.ru.json") else "⟦etat tulasī-patram /"
    if want not in t:
        lab_bad.append(rel(f))
chk("c 16-items label «etat tulasī-patram / …» in every book", not lab_bad, lab_bad)

# ---------- d ----------
en = TEXT[os.path.join(DATA, "book.json")]
chk("d guard: vessels untouched («arghya-pātra», «pādya-pātra» present in book.json)",
    "arghya-pātra" in en and "pādya-pātra" in en)

print(f"s29: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
