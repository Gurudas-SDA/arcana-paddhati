# -*- coding: utf-8 -*-
"""Install the "Mood — Gurudev" blocks into every data/book*.json.

scripts/moods/moods.json holds one entry per target (sub)section:
  {"target": "<section or subsection id>", "quote": "<EN, Gurudev's own words, verbatim>",
   "translations": {"ru": "...", "ru-iast": "...", "lv": "...", ...},
   "machine": ["lv", "de", ...], "source": {title, date, nr, timecode, transcript_url, audio_url}}
The block is put at the start of the target's content in ALL language files:
  {"type": "mood", "quote", "translation", ["translation_note": "machine"], "source"}
English: translation "". Idempotent: existing mood blocks are removed first.
Re-run after scripts/translate/tr.py rebuilds a book.<lang>.json.
Choices and alternatives: Отчёты/_исходники/2026-10-02_resheniya-citaty.md (Satkirti folder).
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "..", "data")
LANGS = ["en", "ru", "ru-iast", "lv", "de", "fr", "es", "it", "uk", "hu"]


def fname(lang):
    return os.path.join(DATA, "book.json" if lang == "en" else "book.%s.json" % lang)


def nodes(book):
    for s in book["sections"]:
        yield s
        for sub in s.get("subsections") or []:
            yield sub


def main():
    moods = json.load(open(os.path.join(HERE, "moods.json"), encoding="utf-8"))
    for lang in LANGS:
        p = fname(lang)
        raw = open(p, encoding="utf-8", newline="").read()
        book = json.loads(raw)
        by_id = {n["id"]: n for n in nodes(book)}
        for n in by_id.values():
            n["content"] = [b for b in n["content"] if b.get("type") != "mood"]
        for m in moods:
            node = by_id[m["target"]]
            block = {"type": "mood", "quote": m["quote"],
                     "translation": "" if lang == "en" else m["translations"][lang]}
            if lang != "en" and lang in m.get("machine", []):
                block["translation_note"] = "machine"
            block["source"] = m["source"]
            node["content"].insert(0, block)
        nl = "\n" if raw.endswith("\n") else ""
        open(p, "w", encoding="utf-8", newline="").write(json.dumps(book, ensure_ascii=False, indent=2) + nl)
        print("%s: %d mood blocks" % (lang, len(moods)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
