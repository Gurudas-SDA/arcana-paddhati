# -*- coding: utf-8 -*-
"""A121 (Satkirti 26.10.2026, msg 6811–6818, 6824, 6826, 6828): the part «Арати».

  * All ārati chapters in ONE new part «Арати» (id "arati", after «Праздники и обеты»), in this order:
      1 «Мангала-арати»       (mangala-arati-songs — was «Песни мангала-арати», content unchanged)
      2 «Раджа-бхога-арати»   (raja-bhoga-arati — NEW: Yaśomatī-nandana, Jaya Yaśodā-nandana, Jaya Rādhā-Mādhava)
      3 «Гаура-арати»         (gaura-arati-songs — was «Песни гаура-арати»)
      4 «Картика»             (kartika-bhajans — was «Бхаджаны для Картики»; «Шри Дамодараштака» stays there)
      5 «Ямунаштака»          (yamunastaka — NEW: Śrī Yamunāṣṭakam of Śrīla Rūpa Gosvāmī)
      6 «Джхулана-ятра»       (jhulana-yatra-bhajans — NEW: Jhūlā jhūle Rādhā-Dāmodara, Rādhe jhūlana padhāro)
    The old chapter ids are kept (links, bookmarks, reading places keep working). The part «Праздники, обеты и песни
    арати» keeps the festivals and is called «Праздники и обеты» / «Festivals and Vows».
  * msg 6826 «Все пронумеруй по центру. Короткие бхаджаны, одна-две шлоки не нумеруй»: every song subsection
    («song-…») with ≥3 verses gets "numbered": true (A120 flag), songs with 1–2 verses have no flag.
  * msg 6828 «В «Джая-дхвани» убери переводы»: the calls of «Джая-дхвани» (jaya-dhvani-front) have no translation and
    no word-by-word (exception to «Стандарты» 79 — Satkirti msg 6828).

Books: en (book.json) and ru-iast (the book's languages, S 23.10); book.ru.json (retired Cyrillic mirror) only gets the
«Джая-дхвани» change (its generator ch00a_front writes it). The other retired languages are not touched.
Must run AFTER ch16_arati_songs / ch17_kartika_bhajans / ch00a_front if those are rebuilt.

    python scripts/chapters/ch18_arati/build.py        (idempotent)
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
CH = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(CH, "..", "..", ".."))
DATA = os.path.join(REPO, "data")
sys.path.insert(0, CH)
from songs import CHAPTERS, FESTIVALS, PART, SONGS  # noqa: E402

FILES = {"en": "book.json", "ru-iast": "book.ru-iast.json"}
NEW_IDS = [c[0] for c in CHAPTERS if c[3]]


def song(sid, lang):
    s = SONGS[sid]
    en = lang == "en"
    content = [{"type": "text", "content": s["author"][1 if en else 0]}]
    for v in s["verses"]:
        content.append({"type": "verse", "sanskrit": v["sanskrit"],
                        "wbw": v["wbw_en" if en else "wbw_ru"], "translation": v["tr_en" if en else "tr_ru"]})
    return {"id": sid, "title": s["title"][1 if en else 0], "content": content}


def numbered(sub):
    return sum(1 for b in sub.get("content") or [] if b.get("type") == "verse") >= 3


def strip_jaya(book):
    for s in book["sections"]:
        if s["id"] == "jaya-dhvani-front":
            for b in s["content"]:
                if b.get("type") == "verse":
                    # "" (not absent): the app shows a verse without translation as a centred verse without
                    # buttons; an absent translation would make it an indented inline mantra (SectionContent.tsx).
                    b["translation"] = ""
                    b.pop("wbw", None)


def apply(book, lang):
    en = lang == "en"
    secs = {s["id"]: s for s in book["sections"]}
    # new chapters (rebuilt every run)
    for cid, ru_t, en_t, songs in CHAPTERS:
        if songs:
            secs[cid] = {"id": cid, "title": en_t if en else ru_t, "subtitle": None, "page": "", "content": [],
                         "subsections": [song(x, lang) for x in songs]}
        else:
            secs[cid]["title"] = en_t if en else ru_t
    # section order: the six chapters together, where «Мангала-арати» stood
    order = [s["id"] for s in book["sections"] if s["id"] not in NEW_IDS]
    chap = [c[0] for c in CHAPTERS]
    at = order.index("mangala-arati-songs")
    order = [x for x in order if x not in chap]
    order[at:at] = chap
    book["sections"] = [secs[x] for x in order]
    # parts
    parts = [p for p in book["parts"] if p["id"] != PART["id"]]
    fest = next(p for p in parts if p["id"] == FESTIVALS[0])
    fest["sections"] = [x for x in fest["sections"] if x not in chap]
    fest["title"] = FESTIVALS[2 if en else 1]
    parts.insert(parts.index(fest) + 1, {"id": PART["id"], "title": PART["title"][1 if en else 0], "sections": chap})
    book["parts"] = parts
    # msg 6826: songs with ≥3 verses numbered, 1–2 verses not
    for s in book["sections"]:
        for sub in s.get("subsections") or []:
            if str(sub.get("id", "")).startswith("song-"):
                if numbered(sub):
                    sub["numbered"] = True
                else:
                    sub.pop("numbered", None)
    strip_jaya(book)


def write_json(path, obj, raw):
    open(path, "w", encoding="utf-8", newline="").write(
        json.dumps(obj, ensure_ascii=False, indent=2) + ("\n" if raw.endswith("\n") else ""))


def main():
    for lang, fn in list(FILES.items()) + [("ru", "book.ru.json")]:
        path = os.path.join(DATA, fn)
        raw = open(path, encoding="utf-8", newline="").read()
        book = json.loads(raw)
        if lang == "ru":
            strip_jaya(book)
        else:
            apply(book, lang)
        write_json(path, book, raw)
        print("wrote", fn, [p["id"] for p in book["parts"]])


if __name__ == "__main__":
    main()
