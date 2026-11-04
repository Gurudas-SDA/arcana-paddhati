# -*- coding: utf-8 -*-
"""Noteikums 79 D8: pantiem, kam ir BBT RU pārvārdojums (vedabase.io, kešs no rule79_bbt_lookup.py), grāmatas wbw := BBT burtiski.
ru-iast: atslēgas IAST (no EN lapas «Synonyms», tā pati secība), nozīmes — BBT RU; ru: atslēgas un nozīmes — BBT RU (kirilica) burtiski.
Tikai pantiem, kur nozīmju secība atšķiras (un EN/RU ierakstu skaits sakrīt). usage: python rule79_apply_bbt.py <cache.json> [--apply]
"""
import json
import os
import re
import sys
import time
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "qa"))
import rule79_check as R  # noqa: E402
from iast_to_cyrillic import translit  # noqa: E402

src = open(os.path.join(HERE, "rule79_bbt_lookup.py"), encoding="utf-8").read().replace("\nmain()\n", "\n").replace("CACHE = sys.argv[1]", "CACHE = None")
lk = {"__file__": os.path.join(HERE, "rule79_bbt_lookup.py"), "__name__": "lk"}
exec(compile(src, "rule79_bbt_lookup.py", "exec"), lk)

cache = json.load(open(sys.argv[1], encoding="utf-8"))
for _r in cache.values():  # BBT iekavās ir «; » — fragmentus (bez « — ») pievieno iepriekšējai nozīmei
    if _r.get("ru"):
        _m = []
        for _k, _v in _r["ru"]:
            if not _v and _m:
                _m[-1][1] += "; " + _k
            else:
                _m.append([_k, _v])
        _r["ru"] = _m
apply_ = "--apply" in sys.argv


def fold_ru(s):
    return re.sub(r"[^а-яё]", "", s.lower().replace("ё", "е"))


def clean(s):
    return re.sub(r"<[^>]*>", "", s).strip()


def en_keys(url):
    h = lk["get"]("https://vedabase.io" + url)
    x = lk["text_of"](h)
    m = re.search(r"\|Synonyms\|(.*?)\|(?:Translation|Перевод)\|", x, flags=re.S)
    s = m.group(1).replace("|", "")
    return [e.partition(" — ")[0].strip() for e in s.rstrip(".").split("; ")]


def key_of(o):
    s = "".join(c for c in unicodedata.normalize("NFD", o["sanskrit"].splitlines()[0].lower()) if not unicodedata.combining(c)).replace("ṁ", "m")
    return re.sub(r"[^a-z]", "", s)[:60]


done = []
bbt_info = {}
targets = {}  # path -> (match, ru pairs, en keys), noteikts pēc ru-iast
for name in R.BOOKS:
    d = R.load(R.DATA_DEFAULT, name)
    seen = set()
    for sid, path, obj, kind in R.iter_wbw_holders(d):
        if kind != "verse" or not (obj.get("wbw") or "").strip():
            continue
        if name == "book.ru-iast.json":
            k = key_of(obj)
            r = cache.get(k)
            if not r or not r.get("match") or not r.get("ru"):
                continue
            if sid in R.LOCKED_SECTIONS:
                continue
            ek = en_keys(r["match"])
            time.sleep(0.3)
            if len(ek) == len(r["ru"]):
                bbt_info.setdefault(r["match"], {"ru": [[clean(a), clean(b_)] for a, b_ in r["ru"]], "en_keys": [clean(x) for x in ek], "paths": []})["paths"].append(path)
            if len(ek) != len(r["ru"]):
                print("SKAITS NESAKRĪT", path, len(ek), len(r["ru"]))
                continue
            targets[path] = (r["match"], r["ru"], ek)
            seen.add(k)
        elif path not in targets:
            continue
        match, ru, ek = targets[path]
        _k, _v = R.bbt_expected({"en_keys": [clean(x) for x in ek], "ru": [[clean(a), clean(b_)] for a, b_ in ru]}, name)
        pairs = [f"{k_} — {v_}" for k_, v_ in zip(_k, _v)]
        dot = obj["wbw"].strip().endswith(".")
        obj["wbw"] = "; ".join(pairs) + ("." if dot else "")
        done.append((name, path, match))
    if apply_:
        R.write_book(d, os.path.join(R.DATA_DEFAULT, name))
if apply_:
    json.dump(bbt_info, open(os.path.join(HERE, "..", "qa", "rule79_bbt_verses.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("BBT pantu atrašanās vietas (visas kopijas):", sum(len(v["paths"]) for v in bbt_info.values()), "unikālu pantu:", len(bbt_info))
for x in done:
    print(x)
print("aizvietoti:", len(done), "(apply)" if apply_ else "(dry)")
