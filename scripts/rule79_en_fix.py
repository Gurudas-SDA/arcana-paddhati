# -*- coding: utf-8 -*-
"""A142c: noteikuma 79 labošana angļu grāmatā (data/book.json); pārbaude — qa/rule79_check.py (BOOKS_ALL), tests s148.
 D8: EN BBT «Synonyms» (kešs no scripts/rule79_bbt_lookup.py --lang en) -> qa/rule79_bbt_verses.json «en» + wbw := BBT burtiski.
 D1: pantiem bez EN wbw — atslēgas no book.ru-iast.json (jau dalīti), nozīmes angliski (rule79_en_data.FILL).
 D4/D5/D6/D7: SPLITS_EN, BR (rule79_en_data). Mainīts TIKAI wbw.
usage: python rule79_en_fix.py <bbt_cache_en.json> [--apply]"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "qa"))
sys.path.insert(0, HERE)
import rule79_check as R  # noqa: E402
from rule79_en_data import BR, FILL, SPLITS_EN  # noqa: E402

FW = {"of", "by", "with", "for", "on", "to", "where", "which", "like", "from", "and", "here", "the", "her"}


def auto_br(v):
    v = re.sub(r"[\(\[]((?:[A-Za-z]+ ?){1,2})[\)\]]", lambda m: m.group(1) if m.group(1).strip().lower() in FW else m.group(0), v)
    if re.search(r"[()\[\]]", v):
        v = re.sub(r"\s*[\(\[][^()\[\]]*[\)\]]", "", v).strip()
    return v


def split_variant(sp, v):
    if isinstance(sp, str):
        return sp
    for sub, txt in sp.items():
        if sub != "*" and sub in v:
            return txt
    return sp["*"]


def fix_entries(ents, st):
    out = []
    for k, sep, v in ents:
        k = k.strip()
        if k.startswith("(") or k.endswith(")"):
            k = k.strip("()")
        sp = SPLITS_EN.get(k)
        if sp:
            for part in split_variant(sp, v).split("; "):
                pk, _, pv = part.partition(" — ")
                out.append((pk, " — ", pv))
            st["splits"] += 1
            continue
        if re.search(r"[()\[\]]", v):
            nv = BR.get((k, v)) or auto_br(v)
            if nv != v:
                st["brackets"] += 1
            v = nv
        out.append((k, " — ", v))
    return out


def main():
    cache = json.load(open(sys.argv[1], encoding="utf-8"))
    apply_ = "--apply" in sys.argv
    D = R.DATA_DEFAULT
    en = R.load(D, R.EN_BOOK)
    ri = R.load(D, "book.ru-iast.json")
    hr = {p: o for _, p, o, _ in R.iter_wbw_holders(ri)}
    # 1. qa/rule79_bbt_verses.json «en»
    vp = os.path.join(HERE, "..", "qa", "rule79_bbt_verses.json")
    info = json.load(open(vp, encoding="utf-8"))
    for u, v in info.items():
        v["en"] = [[k, m] for k, m in cache[u]]
        assert [k for k, _ in v["en"]] == v["en_keys"], u
    st = {"bbt": 0, "filled": 0, "splits": 0, "brackets": 0}
    bbt_paths = {pp: u for u, v in info.items() for pp in v["paths"]}
    missing = set()
    for sid, path, obj, kind in R.iter_wbw_holders(en):
        if sid in R.EXEMPT_SECTIONS or (sid in R.LOCKED_SECTIONS and not (obj.get("wbw") or "").strip()):
            continue  # «Джая-дхвани» (S 6828); emblēma: S 6038 «Эмблему не трогаешь» — trūkstošo EN wbw nepievieno (s101 d)
        w = (obj.get("wbw") or "").strip()
        dot = (hr[path].get("wbw") or "").strip().endswith(".") if not w else w.endswith(".")
        if path in bbt_paths and kind == "verse":
            obj["wbw"] = "; ".join(f"{k} — {m}" for k, m in info[bbt_paths[path]]["en"]) + ("." if dot else "")
            st["bbt"] += 1
            continue
        if not w:
            ents = []
            for k, _, v in R.split_entries(hr[path]["wbw"]):
                m = FILL.get(k + "|" + v) or FILL.get(k)
                if m is None:
                    missing.add((k, v))
                    m = "?"
                ents.append((k, " — ", m))
            st["filled"] += 1
        else:
            ents = R.split_entries(w)
        ents = fix_entries(ents, st)
        obj["wbw"] = R.join_entries(ents, dot)
    print(st)
    if missing:
        print("TRŪKST FILL:", sorted(missing))
    if apply_ and not missing:
        R.write_book(en, os.path.join(D, R.EN_BOOK))
        json.dump(info, open(vp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("raksts: data/book.json + qa/rule79_bbt_verses.json")


main()
