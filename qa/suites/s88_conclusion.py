"""Satkirti 21.10 msg 6065, burtiski: «Нет черновик не надо, постарайся сделать это добросовестно. У тебя это очень хорошо
получается. Ты уловил настроения гурудева и моё. Раздел назови, заключение. Утромтяидолжен увидеть это уже в книге.»
Satkirti msg 5692 (Идея №2, «Стиль заключительной главы»): «Она проходит через весь ежедневный цикл арчаны — от
пробуждения Божества до укладывания Его спать.»
Стандарты 32: «Санскрит везде пишем в IAST с диакритикой». Стандарты 15: «Слова Гурудева приводим только дословно …
с указанием источника: лекция, дата, номер, таймкод, ссылка на расшифровку».

  a  section «conclusion» exists in book.json / book.ru.json / book.ru-iast.json, titled «Заключение» / «Conclusion»,
     is the LAST section of the book and outside every part (back matter)
  b  the day cycle in order: subsection titles walk from the waking of the Deities to Their rest
     (пробуждение → мангала-арати → утро → завтрак → полдень → после полудня → вечер → ночь); the first cycle subsection
     names the waking, the night one names the rest (отдых)
  c  every quotation (text block in «…» / “…”) is followed by a source line with the lecture no., a date (or «дата не
     указана»), a timecode and a transcript link; ≥ 20 quotations; the same number in all three books
  d  book.ru-iast.json «conclusion»: no Cyrillic with diacritics anywhere (grep «[а-яА-ЯёЁ][̣̄̃̇́]» = 0);
     book.ru.json: none in the prose (text outside ⟦…⟧, titles, source lines) — the Cyrillic edition transliterates only
     the verses and ⟦…⟧ terms, as in every other chapter
  e  no «черновик» / «Липикара» in the chapter; lib/book.ts leaves the back matter unnumbered (backMatter in sectionNumbers)
No browser, no server: python s88_conclusion.py"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(REPO, "data")
sys.stdout.reconfigure(encoding="utf-8")
res = []
CYR_DIA = re.compile("[а-яА-ЯёЁ][̣̄̃̇́]")
BOOKS = {"en": "book.json", "ru": "book.ru.json", "ru-iast": "book.ru-iast.json"}
CYCLE = ["пробужд", "мангала-арати", "утро", "завтрак", "полдень", "после полудня", "вечер", "ночь"]


def chk(name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] data {name} {'' if ok else str(info)[:400]}", flush=True)


def blocks(sec):
    out = list(sec.get("content", []))
    for sub in sec.get("subsections", []):
        out += sub.get("content", [])
    return out


books = {k: json.load(open(os.path.join(DATA, v), encoding="utf-8")) for k, v in BOOKS.items()}
secs = {}
for lang, b in books.items():
    sec = next((s for s in b["sections"] if s["id"] == "conclusion"), None)
    secs[lang] = sec
    chk(f"a {lang}: section «conclusion» present", sec is not None)
if not all(secs.values()):
    print(f"RESULT: {sum(res)}/{len(res)} pass")
    sys.exit(1)

chk("a ru title «Заключение»", secs["ru"]["title"] == "Заключение" and secs["ru-iast"]["title"] == "Заключение",
    secs["ru"]["title"])
chk("a en title «Conclusion»", secs["en"]["title"] == "Conclusion", secs["en"]["title"])
for lang, b in books.items():
    chk(f"a {lang}: last section of the book", b["sections"][-1]["id"] == "conclusion", b["sections"][-1]["id"])
    chk(f"a {lang}: outside every part", all("conclusion" not in p["sections"] for p in b.get("parts", [])))

titles = [s["title"].lower() for s in secs["ru"]["subsections"]]
pos, at = [], 0
for key in CYCLE:
    j = next((i for i in range(at, len(titles)) if key in titles[i]), None)
    pos.append(j)
    if j is not None:
        at = j + 1
chk("b ru: the day cycle in order (" + " → ".join(CYCLE) + ")", None not in pos, list(zip(CYCLE, pos)) + [titles])
chk("b ru: waking first, rest at night", None not in pos and "пробужд" in titles[pos[0]] and "отдых" in titles[pos[-1]],
    titles)
chk("b en/ru-iast: same subsections", [s["id"] for s in secs["en"]["subsections"]] ==
    [s["id"] for s in secs["ru"]["subsections"]] == [s["id"] for s in secs["ru-iast"]["subsections"]])

counts = {}
for lang, sec in secs.items():
    bl = blocks(sec)
    q = [i for i, b in enumerate(bl) if b["type"] == "text" and re.match(r"^[«“]", b.get("content", ""))]
    bad = []
    for i in q:
        nxt = bl[i + 1] if i + 1 < len(bl) else {}
        c = nxt.get("content", "")
        ok = (nxt.get("type") == "sources" and re.search(r"(№|no\.) \d+", c) and re.search(r"\d\d:\d\d:\d\d", c)
              and (re.search(r"\d{4}-\d\d-\d\d", c) or "дата не указана" in c or "date unknown" in c)
              and (nxt.get("links") or [{}])[0].get("transcript_url", "").startswith("https://"))
        if not ok:
            bad.append(bl[i]["content"][:60])
    counts[lang] = len(q)
    chk(f"c {lang}: every quotation has its source line (no., date, timecode, transcript link)", not bad, bad)
chk("c ≥ 20 quotations, the same in en/ru/ru-iast", counts["ru"] >= 20 and len(set(counts.values())) == 1, counts)

raw_iast = json.dumps(secs["ru-iast"], ensure_ascii=False)
chk("d ru-iast: no Cyrillic with diacritics", not CYR_DIA.search(raw_iast), CYR_DIA.findall(raw_iast)[:5])
prose = [secs["ru"]["title"], secs["ru"]["subtitle"] or ""] + [s["title"] for s in secs["ru"]["subsections"]]
for b in blocks(secs["ru"]):
    if b["type"] in ("text", "sources"):
        prose.append(re.sub(r"⟦[^⟦⟧]*⟧", "", b.get("content", "")))
    if b["type"] == "verse":
        prose.append(b.get("translation", ""))
hits = [p[:60] for p in prose if CYR_DIA.search(p)]
chk("d ru: no Cyrillic with diacritics in the prose", not hits, hits)

allt = json.dumps(secs, ensure_ascii=False)
chk("e no «черновик» / «Липикара» in the chapter", not re.search(r"черновик|Липикар", allt, re.I))
bt = open(os.path.join(REPO, "lib", "book.ts"), encoding="utf-8").read()
m = re.search(r"export function sectionNumbers\([\s\S]*?\n}\n", bt)
chk("e lib/book.ts: back matter unnumbered", m and "backMatter" in m.group(0) and "export function backMatter" in bt)

print(f"RESULT: {sum(res)}/{len(res)} pass")
sys.exit(0 if all(res) else 1)
