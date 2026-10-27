# -*- coding: utf-8 -*-
"""A123 (Satkirti msg 6848/6849, 27.10.2026): English translation + word-by-word for the 7 ārati songs.

data/book.json had IAST only for these 61 verses (song_en() in build.py — «the draft has no English translation»),
so the English app showed them as bare inline mantras. en_songs.json (here) holds, per song, the English translation
(verbatim from «Śrī Gauḍīya Gīti-guccha», GVP 2016) and the word-by-word, with the source of each recorded in the file.

This script sets ONLY «translation» and «wbw» of those verses in data/book.json, matched by subsection id and verse
order, after checking that the verse count is the same. IAST, RU (book.ru-iast.json / book.ru.json) and the other
languages are not touched (other languages: the night release translates the changed English chapters).
build.py is not used for this: data/book.json has since been edited by later releases (A120/A121 numbering, part
«Арати»), so a full rebuild would undo them.

    python scripts/chapters/ch16_arati_songs/en_apply.py      (idempotent)
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
CH = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.normpath(os.path.join(CH, "..", "..", "..", "data", "book.json"))


def main():
    songs = json.load(open(os.path.join(CH, "en_songs.json"), encoding="utf-8"))["songs"]
    raw = open(BOOK, encoding="utf-8", newline="").read()
    book = json.loads(raw)
    done = {}
    for sec in book["sections"]:
        for sub in sec.get("subsections") or []:
            if sub.get("id") not in songs:
                continue
            verses = [b for b in sub["content"] if b.get("type") == "verse"]
            src = songs[sub["id"]]["verses"]
            assert len(verses) == len(src), (sub["id"], len(verses), len(src))
            for v, s in zip(verses, src):
                assert s["translation"].strip() and s["wbw"].strip(), sub["id"]
                v["wbw"] = s["wbw"]
                v["translation"] = s["translation"]
            done[sub["id"]] = len(verses)
    assert set(done) == set(songs), set(songs) - set(done)
    nl = "\n" if raw.endswith("\n") else ""
    open(BOOK, "w", encoding="utf-8", newline="").write(json.dumps(book, ensure_ascii=False, indent=2) + nl)
    print("book.json:", done, "total", sum(done.values()))


if __name__ == "__main__":
    main()
