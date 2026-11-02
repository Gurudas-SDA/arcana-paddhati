"""A137 (02.11.2026), Satkirti msg 7293 (voice, transcript) verbatim:
«Это назовём «Мангалачарана Гурудева». Его ставим там, где Арати, в конце — после «Ямунаштаки». То, что была
«Дамодара-дхьяна» (aṅga-śyāmalima…), которую мы недавно поставили, — оттуда всё это убираешь, и этот стих ставится после
«śyāmasundara śikhaṇḍa-śekhara» (шестой пункт): седьмым ставишь «aṅga…», а «tavaivāsmi» будет восьмым. Потому что
«Дамодара-дхьяна» читается только во время Картики; и Гурудев, когда читает эту мангалачарану перед лекцией, добавляет
тот стих. Поставить его после «śyāmasundara» и написать, как дополнительный стих на Картику.»
Msg 7297: «Скриншот пришлёшь».

Data check (en = book.json, ru-iast; book.ru.json only: the dhyana is gone from «Картика»):
  a) chapter «gurudeva-mangalacarana» (RU «Мангалачарана Гурудева», EN «Gurudeva’s Maṅgalācaraṇa») is the LAST chapter of the
     part «arati», right after «yamunastaka», and in the book order too;
  b) 8 verses in the order: nāma-śreṣṭhaṁ / gurave gaura-candrāya / ānanda-līlāmaya / bhaktyā vihīnā / govinda dāmodara /
     śyāmasundara śikhaṇḍa-śekhara / aṅga-śyāmalima / tavaivāsmi; every verse has «пословно» (wbw);
     translation: all 8 in ru-iast except 5 (no source, left empty — never invented); en: 1–4, 6, 7 (5 and 8: no source);
  c) the 7th is preceded by the note «Дополнительный стих на Картику» / «Additional verse for Kārtika»;
  d) «Картика» (kartika-bhajans) has no «song-damodara-dhyana» subsection (3 songs), nowhere in the data (all books);
  e) no Cyrillic+diacritics sanskrit (ru-iast), IAST in verses.
usage: python s137_gurudeva_mangalacarana_a137.py            (DATA_DIR env = another data folder, for the red run on origin/main)
"""
import json
import os
import re
import sys

DATA = os.environ.get("DATA_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
CID = "gurudeva-mangalacarana"
HEAD = ["nāma-śreṣṭhaṁ", "gurave gaura-candrāya", "ānanda-līlāmaya", "bhaktyā vihīnā", "govinda dāmodara",
        "śyāmasundara śikhaṇḍa-śekhara", "aṅga-śyāmalima", "tavaivāsmi"]
NO_TR = {"ru-iast": {4}, "en": {4, 7}}   # verse index without a translation source (5th; en also 8th)
results = []


def check(where, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {where} {name} {'' if ok else info}".rstrip(), flush=True)


bad = re.compile("[а-яА-ЯёЁ][̣̄̃̇́]")
for fn, lang, title, note in (("book.ru-iast.json", "ru-iast", "Мангалачарана Гурудева", "Дополнительный стих на Картику"),
                              ("book.json", "en", "Gurudeva’s Maṅgalācaraṇa", "Additional verse for Kārtika")):
    raw = open(os.path.join(DATA, fn), encoding="utf-8").read()
    b = json.loads(raw)
    secs = {s["id"]: s for s in b["sections"]}
    ids = [s["id"] for s in b["sections"]]
    part = next(p for p in b["parts"] if p["id"] == "arati")["sections"]
    check(fn, "a chapter is the last of the part «Арати», right after yamunastaka", part[-2:] == ["yamunastaka", CID], part)
    check(fn, "a chapter follows yamunastaka in the book order", CID in ids and ids.index(CID) == ids.index("yamunastaka") + 1)
    c = secs.get(CID)
    if not c:
        continue
    check(fn, f"a title «{title}»", c["title"] == title, c["title"])
    cont = c.get("content") or []
    vs = [x for x in cont if x["type"] == "verse"]
    check(fn, "b 8 verses", len(vs) == 8, len(vs))
    if len(vs) != 8:
        continue
    for i, (v, h) in enumerate(zip(vs, HEAD)):
        check(fn, f"b verse {i + 1} starts «{h}»", v["sanskrit"].replace("\n", " ").startswith(h), v["sanskrit"][:40])
        check(fn, f"b verse {i + 1} has «пословно» (wbw) of «слово — значение»", " — " in (v.get("wbw") or ""))
        if i not in NO_TR[lang]:
            check(fn, f"b verse {i + 1} has a translation", bool((v.get("translation") or "").strip()))
        else:
            check(fn, f"b verse {i + 1}: no source -> translation empty (not invented)", not (v.get("translation") or "").strip())
    k = cont.index(vs[6])
    check(fn, f"c the 7th verse is preceded by the note «{note}»", k > 0 and cont[k - 1] == {"type": "text", "content": note}, cont[k - 1:k])
    check(fn, "a one-sentence intro first", cont and cont[0]["type"] == "text")
    check(fn, "b chapter numbered", c.get("numbered") is True)
    if lang == "ru-iast":
        check(fn, "e no Cyrillic+diacritics sanskrit", not bad.search(json.dumps(c, ensure_ascii=False)))
for fn in ("book.json", "book.ru-iast.json", "book.ru.json", "book.de.json", "book.lv.json"):
    b = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
    k = next(s for s in b["sections"] if s["id"] == "kartika-bhajans")
    check(fn, "d «Картика»: no dhyana subsection", "song-damodara-dhyana" not in [x["id"] for x in k["subsections"]]
          and "dhyāyema" not in json.dumps(k, ensure_ascii=False))
    if fn in ("book.json", "book.ru-iast.json", "book.ru.json"):
        check(fn, "d «Картика»: 3 songs, Damodarashtaka first", [x["id"] for x in k["subsections"]][:1] == ["song-damodarastakam"] and len(k["subsections"]) == 3)

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
