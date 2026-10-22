"""Satkirti 22.10 msg 6141 (balss, transkripts burtiski): «… расписать Ashtakali Leelu по времени: с такого-то времени по
тут такая Ashtakali название, что происходит? Ну, коротко, чтобы, знаешь, как на одну строчку. … можно потом в конце
записать, что это взято оттуда-оттуда-то …»
Satkirti 22.10 msg 6151 (balss, burtiski): «у нас есть раздел заключение, и в нём есть подглавы, 10 подглав. И сделать
одиннадцатую, одиннадцатую Аштакалы Лилы. И вот эту таблицу всю и поставь. … И после таблицы у тебя были источники, и там
ещё было третий последний абзац насчёт того, что в русском издании, там округлено. И этот абзац вообще не нужен. Нам нужно
то чётко, что источник идёт от … Рахаяся, также Гурудев и Шрила Нарайяна Махарадж, всё, достаточно. … И после этого эту
шлоку надо снова целиком её показать, снова целиком.»
Стандарты 33: «Санскрит везде пишем в IAST с диакритикой».

  a  «conclusion» has 11 subsections; the 11th (last) is «conclusion-ashtakala» «Аштакалия-лила» / «Aṣṭa-kālīya-līlā»;
     no separate section «ashtakala-lila»; «conclusion» stays the last section of the book
  b  the 11th subsection has one table of 8 rows in the order of the day: niśānta, prātaḥ, pūrvāhna, madhyāhna,
     aparāhna, sāyaṁ, pradoṣa, rātri; each row = time «H:MM–H:MM», name (IAST in ru-iast / en), what happens — ONE line
     (≤ 160 characters, # tehniskais slieksnis Lipikāra, nav S noteikums)
  c  the times join into 24 hours without gap or overlap, starting at 3:36
  d  the subsection ends with the source line: Bhajana-rahasya, Bhaktivinoda, Gurudev, Nārāyaṇa Mahārāja — ONLY these
     (no other ācārya, book or lecture: Viśvanātha, Rūpa, Kṛṣṇadāsa, Līlāmṛta, no. 4170 …) — and nothing
     about the rounded times of the English edition (no «округл» / «rounded» / «Gaudiya Vedanta Publications»)
  e  the 10th subsection («Круг замыкается») ends with the Upadeśāmṛta 8 verse in full (sanskrit + translation + wbw),
     the same verse as at the start of the chapter
  f  book.ru-iast.json: no Cyrillic with diacritics in the 11th subsection
No browser, no server: python s93_ashtakala.py"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(REPO, "data")
sys.stdout.reconfigure(encoding="utf-8")
res = []
SUB = "conclusion-ashtakala"
CYR_DIA = re.compile("[а-яА-ЯёЁ][̣̄̃̇́]")
BOOKS = {"en": "book.json", "ru": "book.ru.json", "ru-iast": "book.ru-iast.json"}
NAMES = ["niśānta", "prātaḥ", "pūrvāhna", "madhyāhna", "aparāhna", "sāyaṁ", "pradoṣa", "rātri"]
TITLE = {"en": "Aṣṭa-kālīya-līlā", "ru": "Аштакалия-лила", "ru-iast": "Аштакалия-лила"}


def chk(name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] data {name} {'' if ok else str(info)[:400]}", flush=True)


def mins(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)


books = {k: json.load(open(os.path.join(DATA, v), encoding="utf-8")) for k, v in BOOKS.items()}
subs = {}
for lang, b in books.items():
    ids = [s["id"] for s in b["sections"]]
    chk(f"a {lang}: no separate section «ashtakala-lila»; «conclusion» is the last section", "ashtakala-lila" not in ids
        and ids[-1] == "conclusion", ids[-2:])
    con = next((s for s in b["sections"] if s["id"] == "conclusion"), {"subsections": []})
    ss = con["subsections"]
    chk(f"a {lang}: «Заключение» has 11 subsections, the 11th = «{SUB}» «{TITLE[lang]}»", len(ss) == 11
        and ss[-1]["id"] == SUB and ss[-1]["title"] == TITLE[lang], [(x["id"], x["title"]) for x in ss[-2:]])
    subs[lang] = ss[-1] if ss and ss[-1]["id"] == SUB else None
    if len(ss) >= 10:
        c10, c0 = ss[9]["content"], con["content"]
        first = next((x for x in c0 if x["type"] == "verse"), {})
        last = c10[-1] if c10 else {}
        chk(f"e {lang}: subsection 10 ends with the Upadeśāmṛta 8 verse in full (= the chapter's first verse)",
            last.get("type") == "verse" and last.get("sanskrit") == first.get("sanskrit") and last.get("translation")
            == first.get("translation") and last.get("wbw") == first.get("wbw") and "kālaṁ nayed" in json.dumps(
                books["ru-iast"], ensure_ascii=False), (ss[9]["title"], last.get("type")))
if not all(subs.values()):
    print(f"RESULT: {sum(res)}/{len(res)} pass")
    sys.exit(1)

for lang, sub in subs.items():
    tables = [x for x in sub["content"] if x["type"] == "table"]
    chk(f"b {lang}: exactly one table", len(tables) == 1, len(tables))
    if not tables:
        continue
    rows = [r["cells"] for r in tables[0]["rows"]]
    chk(f"b {lang}: 8 rows × 3 cells", len(rows) == 8 and all(len(r) == 3 for r in rows), [len(r) for r in rows])
    if len(rows) != 8:
        continue
    times = [re.fullmatch(r"(\d{1,2}:\d\d)–(\d{1,2}:\d\d)", r[0]) for r in rows]
    chk(f"b {lang}: every time «H:MM–H:MM»", all(times), [r[0] for r in rows])
    if lang != "ru":
        chk(f"b {lang}: names in the order of the day (IAST)", all(n in r[1] for n, r in zip(NAMES, rows)), [r[1] for r in rows])
    long = [r[2][:50] for r in rows if len(r[2]) > 160 or "\n" in r[2]]
    chk(f"b {lang}: «что происходит» — one short line each (≤ 160)", not long, long)
    if all(times):
        span = [(mins(m.group(1)), mins(m.group(2))) for m in times]
        joined = all(span[i][1] == span[(i + 1) % 8][0] for i in range(8))
        total = sum((y - x) % 1440 for x, y in span)
        chk(f"c {lang}: times join into 24 h from 3:36", joined and total == 1440 and span[0][0] == mins("3:36"),
            [r[0] for r in rows])

for lang, sub in subs.items():
    last = sub["content"][-1]
    c = last.get("content", "")
    chk(f"d {lang}: ends with the source line — Bhajana-rahasya, Bhaktivinoda, Gurudev, Nārāyaṇa Mahārāja",
        last["type"] == "sources" and re.search(r"(?i)бхаджана-рахась|bhajana-rahasya", c)
        and re.search(r"(?i)бхактивинод|bhaktivinod", c) and re.search(r"Гурудев|Gurudev", c)
        and re.search(r"Нараян|Nārāyaṇa", c), c[:300])
    other = re.findall(r"(?i)вишванатх|viśvanāth|рупа госвам|rūpa gosvām|кришнадас|kṛṣṇadās|лиламрит|līlāmṛt|"
                       r"смарана-мангал|smaraṇa-maṅgal|бхаванамрит|bhāvanāmṛt|№ ?4170|no\. ?4170", c)
    chk(f"d {lang}: only the three sources (Bhajana-rahasya, Gurudev, Nārāyaṇa Mahārāja) — no other ācārya / book / "
        "lecture", not other, other)
    allt = json.dumps(sub, ensure_ascii=False)
    chk(f"d {lang}: no paragraph about the rounded English-edition times", not re.search(
        r"(?i)округл|rounded|Gaudiya Vedanta Publications", allt), re.findall(r"(?i)округл\w*|rounded", allt))

raw = json.dumps(subs["ru-iast"], ensure_ascii=False)
chk("f ru-iast: no Cyrillic with diacritics", not CYR_DIA.search(raw), CYR_DIA.findall(raw)[:5])

print(f"RESULT: {sum(res)}/{len(res)} pass")
sys.exit(0 if all(res) else 1)
