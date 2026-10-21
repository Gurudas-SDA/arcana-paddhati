"""Satkirti 21.10 msg 6026/6028/6030 (balss), burtiski pēc transkripta:
«Перепиши Введение. … поставь второй стих (ŚB 11.3.48 «labdhvānugraha ācāryāt») с переводом BBT, конечно же.
И потом „Настроение Гурудева“ — найди, если можешь, пять цитат.»
Satkirti 21.10 msg 6038: «Эмблему не трогаешь, только стих».
Стандарты 75: «У каждого стиха, который мы цитируем в книге (в любой главе), обязательно есть пословный перевод».
Стандарты 32: «Санскрит везде пишем в IAST с диакритикой».

  a  «Введение» (introduction) in book.json / book.ru-iast.json / book.ru.json: the verse is ŚB 11.3.48 (IAST = vedabase.io
     and Versebase; book.ru = academic Cyrillic of the same IAST); the old «arcye viṣṇau…» is nowhere in the section
  b  translation = BBT verbatim (vedabase.io/ru resp. /en, 11.3.48) + source «(«Шримад-Бхагаватам» 11.3.48)» /
     «(Śrīmad-Bhāgavatam 11.3.48)»; word-for-word (пословный) = the 11 vedabase headwords in order, RU glosses = vedabase.io/ru
  c  «Настроение Гурудева» at the Introduction in en / ru / ru-iast: exactly 5 quotes (main + 4), each with lecture nr,
     date, timecode, transcript link; RU / RU-IAST translation present; RU-IAST text has no Cyrillic Sanskrit with
     diacritics (grep «[а-яА-ЯёЁ][̣̄̃̇́]» = 0)
  d  msg 6038: the «gaudiya-emblem» section is unchanged in every book file (sha256 = qa/snapshots/emblem_s6038.json)
No browser, no server: python s79_intro_sb11348.py"""
import glob
import hashlib
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(REPO, "data")
sys.path.insert(0, os.path.join(REPO, "scripts", "translate"))
from iast_to_cyrillic import translit  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
res = []
nfc = lambda s: unicodedata.normalize("NFC", s or "")  # noqa: E731


def chk(name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] data {name} {'' if ok else str(info)[:400]}", flush=True)


IAST = "labdhvānugraha ācāryāt\ntena sandarśitāgamaḥ\nmahā-puruṣam abhyarcen\nmūrtyābhimatayātmanaḥ"
HEAD = ["labdhvā", "anugrahaḥ", "ācāryāt", "tena", "sandarśita", "āgamaḥ", "mahā-puruṣam", "abhyarcet", "mūrtyā",
        "abhimatayā", "ātmanaḥ"]
TR_RU = ("Обретя милость духовного учителя, который раскрывает ученику суть предписаний Вед, вайшнав должен поклоняться "
         "наиболее привлекательному для него образу Верховной Личности Бога. («Шримад-Бхагаватам» 11.3.48)")
TR_EN = ("Having obtained the mercy of his spiritual master, who reveals to the disciple the injunctions of Vedic scriptures, "
         "the devotee should worship the Supreme Personality of Godhead in the particular personal form of the Lord the "
         "devotee finds most attractive. (Śrīmad-Bhāgavatam 11.3.48)")
WBW_RU = ["обретя", "милость", "духовного учителя", "им", "показанный", "(метод поклонения, приведенный) в вайшнава-тантрах",
          "Верховной Личности", "ученик должен поклоняться", "в определенном образе", "который притягателен", "для него"]
WBW_EN = ["having obtained", "mercy", "from the spiritual master", "by him", "being shown",
          "(the process of worship given by) the vaiṣṇava-tantras", "the Supreme Person", "the disciple should worship",
          "in the particular personal form", "which is preferred", "by himself"]
CYR_DIA = re.compile("[а-яА-ЯёЁ][̣̄̃̇́]")
BOOKS = {"en": "book.json", "ru-iast": "book.ru-iast.json", "ru": "book.ru.json"}


def intro(book):
    return next(s for s in book["sections"] if s["id"] == "introduction")


def wbw_pairs(w):
    return [tuple(x.strip().split(" — ", 1)) for x in nfc(w).rstrip(".").split(";") if x.strip()]


for lang, fn in BOOKS.items():
    b = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
    sec = intro(b)
    blob = nfc(json.dumps(sec, ensure_ascii=False))
    verses = [x for x in sec["content"] if x.get("type") == "verse"]
    want_sk = nfc(translit(IAST) if lang == "ru" else IAST)
    # a
    chk(f"a {fn}: Введение verse = ŚB 11.3.48", len(verses) == 1 and nfc(verses[0].get("sanskrit")) == want_sk,
        [nfc(v.get("sanskrit"))[:60] for v in verses])
    old = [w for w in ("arcye viṣṇau", "śilā-dhīr", "арчйе", "ш́ила̄-дхӣр", "Падма-пурана", "Padma Purāṇa") if w in blob]
    chk(f"a {fn}: no «arcye viṣṇau…» left in Введение", not old, old)
    if not verses:
        continue
    v = verses[0]
    # b
    want_tr = TR_EN if lang == "en" else TR_RU
    chk(f"b {fn}: translation = BBT verbatim + source", nfc(v.get("translation")) == nfc(want_tr), v.get("translation"))
    pairs = wbw_pairs(v.get("wbw", ""))
    heads = [p[0] for p in pairs]
    want_heads = [nfc(translit(h)) for h in HEAD] if lang == "ru" else [nfc(h) for h in HEAD]
    chk(f"b {fn}: пословный перевод = 11 vedabase headwords in order", heads == want_heads, heads)
    glosses = [p[1] if len(p) > 1 else "" for p in pairs]
    chk(f"b {fn}: пословный перевод glosses = vedabase.io/{'en' if lang == 'en' else 'ru'}",
        glosses == [nfc(g) for g in (WBW_EN if lang == "en" else WBW_RU)], glosses)
    # c
    moods = [x for x in sec["content"] if x.get("type") == "mood"]
    chk(f"c {fn}: one «Настроение Гурудева» block", len(moods) == 1, len(moods))
    if moods:
        m = moods[0]
        qs = [m] + list(m.get("more") or [])
        chk(f"c {fn}: 5 quotes (main + 4)", len(qs) == 5, len(qs))
        bad = [q.get("source", {}).get("nr") for q in qs
               if not all(q.get("source", {}).get(k) for k in ("nr", "date", "timecode", "transcript_url", "title"))]
        chk(f"c {fn}: every quote has nr, date, timecode, transcript link", not bad, bad)
        chk(f"c {fn}: every quote has Gurudev's words (EN)", all(nfc(q.get("quote")).strip() for q in qs))
        if lang != "en":
            chk(f"c {fn}: every quote translated into the book's language",
                all(nfc(q.get("translation")).strip() for q in qs))
        if lang == "ru-iast":
            hits = [CYR_DIA.findall(nfc(q.get("translation"))) for q in qs]
            chk(f"c {fn}: no Cyrillic Sanskrit with diacritics in the quotes (Стандарты 32)", not any(hits), hits)
    if lang == "ru-iast":
        hits = CYR_DIA.findall(blob)
        chk(f"c {fn}: Введение has no Cyrillic Sanskrit with diacritics", not hits, hits[:10])

# d
snap = json.load(open(os.path.join(REPO, "qa", "snapshots", "emblem_s6038.json"), encoding="utf-8"))["sha256"]
diff = []
for f in sorted(glob.glob(os.path.join(DATA, "book*.json"))):
    b = json.load(open(f, encoding="utf-8"))
    s = next((x for x in b["sections"] if x["id"] == "gaudiya-emblem"), None)
    name = os.path.basename(f)
    h = hashlib.sha256(json.dumps(s, ensure_ascii=False, sort_keys=True).encode()).hexdigest() if s else None
    if snap.get(name) != h:
        diff.append(name)
chk(f"d msg 6038: «Эмблема Гаудия-матха» unchanged in all {len(snap)} book files", not diff, diff)

print(f"\n{sum(res)}/{len(res)} PASS", flush=True)
sys.exit(0 if all(res) else 1)
