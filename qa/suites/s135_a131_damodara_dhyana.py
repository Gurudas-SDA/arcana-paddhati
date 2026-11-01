"""A131 — new subsection «Медитация на Шри Дамодару (дамодара-дхьяна)» in the section «Арати» -> chapter «Картика»
(kartika-bhajans), RIGHT AFTER «Шри Дамодараштака».
Satkirti msg 7226 (01.11.2026) «Подходит»; msg 7225; msg 7187: «эту шлоку Гурудев читает в Картику на мангала-арати перед лекцией»;
msg 7194: «Всё должно быть попроще» (word-by-word = one line «word — simple meaning»);
rule «У каждого стиха, который мы цитируем в книге (в любой главе), обязательно есть пословный перевод»;
rule «Санскрит везде пишем в IAST с диакритикой».
Criteria (register A131): (1) the subsection exists with this exact title directly after «Шри Дамодараштака» (book.json, book.ru.json,
book.ru-iast.json); (2) the verse has 4 IAST lines (the last: dhyāyema dāmodaram), with the A131 corrections
(śyāmalima, jāḍyaṁ, jāguḍa, niveśitojjvala); (3) it has a translation and a word-by-word, and an author line
«Шрила Рупа Госвами, «Става-мала» (по словам Гурудева, лекция CA 5652, 22.11.2020)»; (4) the RU texts have no Cyrillic+diacritics
sanskrit in book.ru-iast.json; (5) «Шри Дамодараштака» is still first and has 8 verses and the numbering flag; the chapter's
other songs are unchanged.
usage: python s135_a131_damodara_dhyana.py [<base-url>]   (data check; the base url is not needed)
"""
import json
import os
import re
import sys

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
TITLE_RU = "Медитация на Шри Дамодару (дамодара-дхьяна)"
SUB = "song-damodara-dhyana"
results = []


def check(name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} {'' if ok else info}".rstrip(), flush=True)


def sec(book):
    return next(s for s in book["sections"] if s["id"] == "kartika-bhajans")


for fn in ["book.json", "book.ru.json", "book.ru-iast.json"]:
    book = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
    subs = sec(book)["subsections"]
    ids = [s["id"] for s in subs]
    i = ids.index("song-damodarastakam")
    check(f"{fn}: subsection {SUB} right after song-damodarastakam", ids[i + 1:i + 2] == [SUB], ids)
    if ids[i + 1:i + 2] != [SUB]:
        continue
    sub = subs[i + 1]
    if fn != "book.json":
        check(f"{fn}: title = «{TITLE_RU}»", sub["title"] == TITLE_RU, sub["title"])
    else:
        check(f"{fn}: EN title has Dāmodara-dhyāna", "Dāmodara" in sub["title"] and "dhyāna" in sub["title"], sub["title"])
    verses = [b for b in sub["content"] if b["type"] == "verse"]
    check(f"{fn}: one verse", len(verses) == 1, len(verses))
    if len(verses) != 1:
        continue
    v = verses[0]
    lines = v["sanskrit"].split("\n")
    check(f"{fn}: verse has 4 lines", len(lines) == 4, lines)
    if fn != "book.ru.json":
        s = v["sanskrit"]
        for w in ["śyāmalima", "jāḍyaṁ", "jāguḍa", "niveśitojjvala"]:
            check(f"{fn}: «{w}»", w in s, s)
        check(f"{fn}: last line ends «dhyāyema dāmodaram»", lines[-1].rstrip(" |").endswith("dhyāyema dāmodaram"), lines[-1])
    check(f"{fn}: translation + word-by-word", bool(v.get("translation")) and bool(v.get("wbw")) and " — " in v["wbw"])
    texts = " ".join(b.get("content", "") for b in sub["content"] if b["type"] == "text")
    if fn == "book.ru-iast.json":
        check(f"{fn}: author line", "Шрила Рупа Госвами, «Става-мала» (по словам Гурудева, лекция CA 5652, 22.11.2020)" in texts, texts)
        bad = re.compile("[а-яА-ЯёЁ][̣̄̃̇́]")
        alltxt = json.dumps(sub, ensure_ascii=False)
        check(f"{fn}: no Cyrillic+diacritics sanskrit", not bad.search(alltxt))
    first = subs[i]
    check(f"{fn}: Damodarashtaka still 8 verses + numbered", sum(1 for b in first["content"] if b["type"] == "verse") == 8 and first.get("numbered"))

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
