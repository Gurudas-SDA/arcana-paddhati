# -*- coding: utf-8 -*-
"""Sinhronizē ru-iast pasvārdu (wbw) no data/book.ru-iast.json atpakaļ ģeneratoru avotos
(ch16 pesni_arati.json, ch17 kartika_bhajany.json, ch99 chapter_ru.md), lai build.py apply
neatceltu A132/A142/A142b (S noteikums 79) labojumus.  Lieto: python3 scripts/sync_wbw_sources.py [--check]
--check: nerakstīt, tikai izdrukāt atšķirību skaitu (exit 1, ja >0).  Funkcija diffs() — QA testam."""
import json, os, sys, re
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CH = os.path.join(REPO, "scripts", "chapters")
SONG_IDS = {1: "song-gurvastakam", 2: "song-prabhupada-padma-stavakah", 3: "song-mangala-arati",
            4: "song-vibhavari-sesa", 5: "song-vraja-dhama-mahimamrta", 6: "song-gaura-arati", 7: "song-yugala-arati"}
P16 = os.path.join(CH, "ch16_arati_songs", "pesni_arati.json")
P17 = os.path.join(CH, "ch17_kartika_bhajans", "kartika_bhajany.json")
P99 = os.path.join(CH, "ch99_conclusion", "chapter_ru.md")


def _rd(p):
    return open(p, encoding="utf-8", newline="").read()


def _wr(p, s):
    open(p, "w", encoding="utf-8", newline="").write(s)


def _data():
    b = json.load(open(os.path.join(REPO, "data", "book.ru-iast.json"), encoding="utf-8"))
    S = {s["id"]: s for s in b["sections"]}
    subs = {}
    for s in S.values():
        for u in s.get("subsections", []):
            subs[u["id"]] = [x for x in u["content"] if x["type"] == "verse"]
    return S, subs


def sync(write):
    """Returns {source: number of wbw differing}; writes sources if write."""
    S, subs = _data()
    res = {}
    raw16 = _rd(P16); src = json.loads(raw16); n = 0
    for s in src:
        for v, x in zip(s["verses"], subs[SONG_IDS[s["song_no"]]]):
            if v["wbw"] != x["wbw"]:
                v["wbw"] = x["wbw"]; n += 1
        assert len(s["verses"]) == len(subs[SONG_IDS[s["song_no"]]]), s["song_no"]
    res["ch16"] = n
    if write and n:
        _wr(P16, json.dumps(src, ensure_ascii=False, indent=1))
    raw17 = _rd(P17); kb = json.loads(raw17); n = 0
    for u in kb["ru-iast"]["subsections"]:
        vv = [y for y in u["content"] if y["type"] == "verse"]
        assert len(vv) == len(subs[u["id"]]), u["id"]
        for v, x in zip(vv, subs[u["id"]]):
            if v["wbw"] != x["wbw"]:
                v["wbw"] = x["wbw"]; n += 1
    res["ch17"] = n
    if write and n:
        _wr(P17, json.dumps(kb, ensure_ascii=False, indent=2))
    # ch99: "Пословно: ..." lines in chapter_ru.md, in order, vs the 3 verses of section «conclusion»
    con = S["conclusion"]
    dv = [b for b in con["content"] if b["type"] == "verse"]
    for u in con["subsections"]:
        dv += [b for b in u["content"] if b["type"] == "verse"]
    lines = _rd(P99).split("\n"); k = 0; n = 0
    for i, ln in enumerate(lines):
        if ln.startswith("Пословно: "):
            want = "Пословно: " + dv[k]["wbw"]; k += 1
            if ln != want:
                lines[i] = want; n += 1
    assert k == len(dv), (k, len(dv))
    res["ch99"] = n
    if write and n:
        _wr(P99, "\n".join(lines))
    return res


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    r = sync(write="--check" not in sys.argv)
    print(r)
    sys.exit(1 if "--check" in sys.argv and any(r.values()) else 0)
