# -*- coding: utf-8 -*-
"""Part I «Храмовый стандарт», chapter «Порядок проведения мангала-арати (для пуджари)» (A83, Satkirti 14.10.2026).

RU master: chapter_ru.py (Sanskrit in IAST). Sources and the step-by-step source table (internal, not in the book):
03_Satkirti/Arcana-paddhati/Черновики/2026.10.15_Мангала-арати — сравнение с образцами.md

    python build.py apply      writes data/book.ru-iast.json (RU master), data/book.ru.json (Cyrillic mirror)
                               and data/book.json (RU copy marked for translation: the app and lint L27 take chapter
                               ids, order and Sanskrit fields from the English book); idempotent.
                               Then: python ../../moods/apply_moods.py

Translation (Satkirti 14.10 22:52, msg 3478: «одним языком, рус»): only Russian for now. The English book gets the RU master
marked for translation ("translation_pending": "ru", English title + one English line); the other languages show
it with the app's "translation in preparation" note. To translate later: replace the placeholder by a translation of the RU master
(cx/gpt-6.1-sol, alt cx/gpt-6-sol), then scripts/translate/night_sync.py mangala-arati-procedure.
"""
import copy, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
DATA = os.path.join(REPO, "data")
sys.path.insert(0, os.path.dirname(HERE))
import hand_chapter as hc  # noqa: E402
from iast_to_cyrillic import translit  # noqa: E402  (path set by hand_chapter)

PART_ID = "temple-worship"
PLACEHOLDER_EN = {
    "title": "Maṅgala-ārati Procedure (for the Pūjārī)",
    "text": "This chapter is not yet translated: the Russian text is shown below; the English translation is in preparation.",
}


def wbw_cyr(wbw):
    """Word-by-word: transliterate the Sanskrit headword of each «word — meaning» pair."""
    out = []
    for pair in wbw.split("; "):
        if " — " in pair:
            w, m = pair.split(" — ", 1)
            out.append(translit(w) + " — " + m)
        else:
            out.append(pair)
    return "; ".join(out)


def to_cyr(sec):
    s = hc.to_cyr(sec)

    def blocks(bs):
        for b in bs:
            if b["type"] == "verse" and b.get("wbw"):
                b["wbw"] = wbw_cyr(b["wbw"])
            if b["type"] == "paired-list":
                for it in b["items"]:
                    for k in ("label", "value"):
                        if it.get(k):
                            it[k] = hc.map_inline(it[k], translit)
                    if it.get("wbw"):
                        it["wbw"] = wbw_cyr(it["wbw"])
            if b["type"] in ("list", "bullet-list") and b.get("content"):
                b["content"] = hc.map_inline(b["content"], translit)

    blocks(s["content"])
    for sub in s["subsections"]:
        blocks(sub["content"])
    return s


def en_placeholder(ru):
    """English book: the RU master marked for translation (the app takes chapter ids, order and — lint L27 —
    every Sanskrit field from the English book, so the structure and Sanskrit must be there byte for byte)."""
    sec = copy.deepcopy(ru)
    sec["title"] = PLACEHOLDER_EN["title"]
    sec["translation_pending"] = "ru"
    sec["content"] = [{"type": "text", "content": PLACEHOLDER_EN["text"]}] + sec["content"]

    def drop_wbw(o):  # the RU word-by-word (bīja term «биджа-мантра», lint L5) is not English; L6 is info-only for EN
        if isinstance(o, dict):
            o.pop("wbw", None)
            for v in o.values():
                drop_wbw(v)
        elif isinstance(o, list):
            for v in o:
                drop_wbw(v)

    drop_wbw(sec)
    return sec


def place(book, sec, after):
    old = next((s for s in book["sections"] if s["id"] == sec["id"]), None)
    if old is not None:
        hc.keep_moods({"sections": [old]}, sec)
        book["sections"].remove(old)
    ids = [s["id"] for s in book["sections"]]
    book["sections"].insert(ids.index(after) + 1 if after in ids else len(ids), sec)
    p = next(x for x in book["parts"] if x["id"] == PART_ID)
    if sec["id"] in p["sections"]:
        p["sections"].remove(sec["id"])
    p["sections"].insert(p["sections"].index(after) + 1 if after in p["sections"] else len(p["sections"]), sec["id"])


def apply():
    ch = hc.load(HERE)
    ru = hc.master(ch, "ru")
    for fname, sec in (("book.ru-iast.json", ru), ("book.ru.json", to_cyr(ru)), ("book.json", en_placeholder(ru))):
        path = os.path.join(DATA, fname)
        book = json.load(open(path, encoding="utf-8"))
        place(book, copy.deepcopy(sec), ch.AFTER)
        hc.write_json(path, book)
        print("wrote", fname)


if __name__ == "__main__":
    if sys.argv[1:] == ["apply"]:
        apply()
    else:
        print(__doc__)
