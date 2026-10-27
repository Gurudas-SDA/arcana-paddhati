"""A123 — S msg 6848/6849 (27.10.2026): «английский вариант — вот какой бардак… если ошибка, надо всё исправлять. И пересмотреть всё».
«Стандарты» правило 79 (verbatim): «У каждого стиха, который мы цитируем в книге (в любой главе), обязательно есть
пословный перевод; в приложении он открывается кнопкой «пословно». Исключение — короткие мантры (правило 178):
пословный перевод есть в данных, кнопки нет.»

Cause (origin/main b00c5aa): in the English book (data/book.json) 7 ārati songs had IAST only — no translation and no
word-by-word for 61 verses (song-gurvastakam 9, song-prabhupada-padma-stavakah 11, song-mangala-arati 9,
song-vibhavari-sesa 8, song-vraja-dhama-mahimamrta 11, song-gaura-arati 7, song-yugala-arati 6), so the English app
showed them as bare inline mantras (S screenshot 14.2 Śrī Prabhupāda-padma-stavakaḥ). The Russian book has them.

  a) data (en): EVERY «song-…» subsection — every verse has a translation and a word-by-word (S exceptions: none of the
     songs; «Джая-дхвани», S msg 6828, is not a song subsection); the 7 songs have exactly 61 such verses;
  b) data: the IAST of these 61 verses in book.json is the same as in book.ru-iast.json (A123 changes no IAST),
     and book.ru-iast.json still has translation + word-by-word for all of them;
  c) app (with <base-url>), English, iPhone 14: every verse of the 7 songs has a «word-by-word» and a «translation»
     button (so none is shown as an inline mantra).
usage: python s114_en_songs_a123.py [<base-url>]
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else None
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
SONGS = {"mangala-arati-songs": ["song-gurvastakam", "song-prabhupada-padma-stavakah", "song-mangala-arati",
                                 "song-vibhavari-sesa", "song-vraja-dhama-mahimamrta"],
         "gaura-arati-songs": ["song-gaura-arati", "song-yugala-arati"]}
NVERSES = {"song-gurvastakam": 9, "song-prabhupada-padma-stavakah": 11, "song-mangala-arati": 9, "song-vibhavari-sesa": 8,
           "song-vraja-dhama-mahimamrta": 11, "song-gaura-arati": 7, "song-yugala-arati": 6}
results = []


def check(where, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {where} {name} {'' if ok else info}".rstrip(), flush=True)


def subs(book):
    out = {}

    def walk(xs):
        for s in xs:
            if str(s.get("id", "")).startswith("song-"):
                out[s["id"]] = [b for b in s.get("content") or [] if b.get("type") == "verse"]
            walk(s.get("subsections") or [])
    walk(book["sections"])
    return out


en = subs(json.load(open(os.path.join(DATA, "book.json"), encoding="utf-8")))
ri = subs(json.load(open(os.path.join(DATA, "book.ru-iast.json"), encoding="utf-8")))

# a)
bad = {sid: [i + 1 for i, v in enumerate(vs) if not ((v.get("translation") or "").strip() and (v.get("wbw") or "").strip())]
       for sid, vs in en.items()}
bad = {k: v for k, v in bad.items() if v}
check("book.json", f"a every «song-…» verse has translation + word-by-word ({len(en)} songs, {sum(map(len, en.values()))} verses)",
      en and not bad, bad)
seven = {sid: len(en.get(sid, [])) for sid in NVERSES}
check("book.json", "a the 7 ārati songs: 61 verses, all with translation + word-by-word",
      seven == NVERSES and all((v.get("translation") or "").strip() and (v.get("wbw") or "").strip()
                               for sid in NVERSES for v in en.get(sid, [])), seven)
# b)
check("book.json", "b IAST of the 61 verses = book.ru-iast.json",
      all([v["sanskrit"] for v in en.get(sid, [])] == [v["sanskrit"] for v in ri.get(sid, [])] for sid in NVERSES))
check("book.ru-iast.json", "b RU still has translation + word-by-word for the 61 verses",
      all(len(ri.get(sid, [])) == n and all(v.get("translation") and v.get("wbw") for v in ri[sid]) for sid, n in NVERSES.items()))

if BASE is None:
    print(f"{sum(results)}/{len(results)} passed")
    sys.exit(0 if results and all(results) else 1)

# c) app
from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as p:
    for device, engine, options in qa.devices(["iphone14"]):
        browser = getattr(p, engine).launch()
        context = browser.new_context(service_workers="block", **options)
        page = context.new_page()
        for chap, ids in SONGS.items():
            page.goto(f"{BASE}/{chap}/", wait_until="load")
            page.wait_for_selector(f"#{ids[0]} .verse-text", state="attached", timeout=15000)
            got = page.evaluate("""(ids) => ids.map(id => { const s = document.getElementById(id); if (!s) return [id, -1, -1, -1];
                const chips = [...s.querySelectorAll('.verse-chips')];
                return [id, s.querySelectorAll('.verse-text').length,
                        chips.filter(c => /word-by-word/i.test(c.textContent)).length,
                        chips.filter(c => /translation/i.test(c.textContent)).length]; })""", ids)
            for sid, nv, nw, nt in got:
                check(f"{device} en/{chap}", f"c {sid}: {NVERSES[sid]} verses, each with «word-by-word» + «translation»",
                      nv == NVERSES[sid] and nw == nv and nt == nv, (nv, nw, nt))
        context.close()
        browser.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
