# -*- coding: utf-8 -*-
"""Install the "Mood — Gurudev" blocks into every data/book*.json.

scripts/moods/moods.json holds one entry per target (sub)section:
  {"target": "<section or subsection id>", "quote": "<EN, Gurudev's own words, verbatim>",
   "translations": {"ru": "...", "ru-iast": "...", "lv": "...", ...},
   "machine": ["lv", "de", ...], "source": {title, date, nr, timecode, transcript_url, audio_url, [note], [i18n]},
   "more": [{"candidate", "label", "quote", "translation": {lang: text}, "machine": [langs], "source"}, ...]}
`more` = the other candidate quotes for that block (the app shows them all after the chosen one in the overlay; best first; print/Kindle
show them only in the appendix, scripts/formats/build_formats.py).
The block is put at the start of the target's content in ALL language files:
  {"type": "mood", "quote", "translation", ["translation_note": "machine"], "source",
   ["more": [{"quote", "translation", ["translation_note": "machine"], "source"}, ...]]}
Source: `note` (e.g. a private recording without links) is shown after the source line; `i18n: {lang: {title, note}}`
overrides those fields for that language (and sets source.lang). English: translation "". Idempotent: existing mood blocks are removed first.
Re-run after scripts/translate/tr.py rebuilds a book.<lang>.json.
Choices and alternatives: Отчёты/_исходники/2026-10-02_resheniya-citaty.md (Satkirti folder).
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "..", "data")
LANGS = ["en", "ru", "ru-iast", "lv", "de", "fr", "es", "it", "uk", "hu", "pt", "lt"]


def fname(lang):
    return os.path.join(DATA, "book.json" if lang == "en" else "book.%s.json" % lang)


def nodes(book):
    for s in book["sections"]:
        yield s
        for sub in s.get("subsections") or []:
            yield sub


def src_for(src, lang):
    """The source of a quote for one language: `i18n.<lang>` (e.g. a Russian title/note) overrides the
    English fields and then `lang` is set (the source line's language); `i18n` itself is not written."""
    out = {k: v for k, v in src.items() if k != "i18n"}
    loc = (src.get("i18n") or {}).get(lang)
    if loc:
        out.update(loc)
        out["lang"] = "ru" if lang.startswith("ru") else lang
    return out


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
            if m["target"] not in by_id:
                # A section not yet translated into this language (the app shows the English one, with its mood).
                continue
            node = by_id[m["target"]]
            block = {"type": "mood", "quote": m["quote"],
                     "translation": "" if lang == "en" else m["translations"][lang]}
            if lang != "en" and lang in m.get("machine", []):
                block["translation_note"] = "machine"
            block["source"] = src_for(m["source"], lang)
            more = []
            for a in m.get("more", []):
                alt = {"quote": a["quote"], "translation": "" if lang == "en" else a["translation"][lang]}
                if lang != "en" and lang in a.get("machine", []):
                    alt["translation_note"] = "machine"
                alt["source"] = src_for(a["source"], lang)
                more.append(alt)
            if more:
                block["more"] = more
            node["content"].insert(0, block)
        nl = "\n" if raw.endswith("\n") else ""
        open(p, "w", encoding="utf-8", newline="").write(json.dumps(book, ensure_ascii=False, indent=2) + nl)
        done = [m for m in moods if m["target"] in by_id]
        print("%s: %d mood blocks, %d more quotes" % (lang, len(done), sum(len(m.get("more", [])) for m in done)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
