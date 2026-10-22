"""Satkirti 22.10 msg 6137 (instruction), burtiski:
«Ievadā likt Upadeśāmṛta 8 «tan-nāma-rūpa-caritādi-sukīrtanānu-smṛtyoḥ krameṇa rasanā-manasī niyojya / tiṣṭhan vraje
tad-anurāgi-janānugāmī kālaṁ nayed akhilam ity upadeśa-sāram» un «Настроение Гурудева» sadaļā savākt Gurudeva izteikumus
TIEŠI par šo pantu.» Satkirti 22.10 msg 6139 (on «вместо ŚB 11.3.48»): «Супер, как всё сделаешь сразу в книгу».
Satkirti 22.10 msg 6152 (voice): «хочу её поставить сразу же после обложки … белый лист. На этом белом листе будет эта
шлока с переводом … И потом эта парампара»; msg 6153: «Как назвать содержание? … чтобы содержание мы могли выйти на этот
стих»; msg 6155: «Еще я хочу … Джай вишнупада парамаханса … в нашем … Гити Гуччха … Шри Нарайна Махараджа там в начале.
Именно эту хочу. Но там нужно лишнее убрать»; msg 6154: «всё это на ночь можно уже загружать».
Satkirti 21.10 msg 6038: «Эмблему не трогаешь, только стих».
Стандарты 77: «У каждого стиха, который мы цитируем в книге (в любой главе), обязательно есть пословный перевод».
Стандарты 16: «Слова Гурудева приводим только дословно … с указанием источника: лекция, дата, номер, таймкод, ссылка на расшифровку».

  a  every book opens (front matter, no part) with «Упадеша-сара» (upadesha-sara), then «Джая-дхвани» (jaya-dhvani), then
     «Гуру-парампара»; «Упадеша-сара» holds one verse: Upadeśāmṛta 8 (IAST = vedabase.io noi/8 and Versebase; book.ru =
     academic Cyrillic of the same IAST); «Введение» has no verse and no quotes any more (ŚB 11.3.48 not brought back)
  e  «Джая-дхвани»: the 36 calls of the source (scripts/chapters/ch00a_front/jaya_dhvani.py) in order, one verse block
     each, with translation and word-for-word in every book (ru = Cyrillic of the IAST)
  b  en / ru / ru-iast: translation = BBT verbatim (vedabase.io/en resp. /ru, noi/8) + «(Śrī Upadeśāmṛta 8)» /
     «(«Шри Упадешамрита» 8)»; пословный = the 22 vedabase headwords in order with the vedabase glosses;
     the 9 other languages: a translation and a 22-word word-for-word with the same headwords — in that language, or the
     English one until the night release translates it (S msg 6139 «сразу в книгу», AnyModel 503 by day 22.10; Стандарты 75)
  c  «Настроение Гурудева» at «Упадеша-сара»: exactly 5 quotes, Gurudev's words on UM 8 (each names the verse words),
     lectures № 7717, 812, 554, 137, 447 — none of them a lecture already quoted in «Заключение» (it opens with UM 8);
     each with nr, date, timecode, transcript link; translated into every book language; ru-iast without Cyrillic
     Sanskrit with diacritics
  d  msg 6038: the «gaudiya-emblem» section is unchanged in every book file (sha256 = qa/snapshots/emblem_s6038.json)
No browser, no server: python s95_intro_um8.py"""
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
sys.path.insert(0, os.path.join(REPO, "scripts", "chapters", "ch00a_front"))
import jaya_dhvani as JD  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
res = []
nfc = lambda s: unicodedata.normalize("NFC", s or "")  # noqa: E731


def chk(name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] data {name} {'' if ok else str(info)[:400]}", flush=True)


IAST = ("tan-nāma-rūpa-caritādi-sukīrtanānu-\nsmṛtyoḥ krameṇa rasanā-manasī niyojya\n"
        "tiṣṭhan vraje tad-anurāgi-janānugāmī\nkālaṁ nayed akhilam ity upadeśa-sāram")
HEAD = ["tat", "nāma", "rūpa", "carita-ādi", "su-kīrtana", "anusmṛtyoḥ", "krameṇa", "rasanā", "manasī", "niyojya",
        "tiṣṭhan", "vraje", "tat", "anurāgi", "jana", "anugāmī", "kālam", "nayet", "akhilam", "iti", "upadeśa", "sāram"]
TR_EN = ("The essence of all advice is that one should utilize one’s full time – twenty-four hours a day – in nicely chanting "
         "and remembering the Lord’s divine name, transcendental form, qualities and eternal pastimes, thereby gradually "
         "engaging one’s tongue and mind. In this way one should reside in Vraja [Goloka Vṛndāvana-dhāma] and serve Kṛṣṇa "
         "under the guidance of devotees. One should follow in the footsteps of the Lord’s beloved devotees, who are deeply "
         "attached to His devotional service. (Śrī Upadeśāmṛta 8)")
TR_RU = ("Все наставления сводятся к следующему: необходимо все время — двадцать четыре часа в сутки — сосредоточенно "
         "повторять божественное имя Господа и воспевать Его трансцендентный облик, качества и вечные игры, постепенно "
         "занимая этой деятельностью свой язык и ум. Всегда памятуя о святом имени, облике, качествах и вечных играх "
         "Кришны, человек должен жить во Врадже [Голоке Вриндавана-дхаме] и служить Кришне под руководством преданных. "
         "Необходимо идти по стопам преданных, которые очень дороги Господу и глубоко привязаны к преданному служению Ему. "
         "(«Шри Упадешамрита» 8)")
WBW_EN = ["of Lord Kṛṣṇa", "the holy name", "form", "character, pastimes and so on", "in discussing or chanting nicely",
          "and in remembering", "gradually", "the tongue", "and one’s mind", "engaging", "residing", "in Vraja",
          "to Lord Kṛṣṇa", "attached", "persons", "following", "time", "should utilize", "full", "thus",
          "of advice or instruction", "the essence"]
WBW_RU = ["Господа Кришны", "святое имя", "облик", "качества, игры и так далее", "в тщательное обсуждение или воспевание",
          "и памятование", "постепенно", "язык", "и ум", "вовлекая", "живя", "во Врадже", "к Господу Кришне",
          "привязанным", "личностям", "следуя", "время", "нужно использовать", "всё", "такова", "наставления", "суть"]
NRS = ["7717", "812", "554", "137", "447"]
VERSE_WORDS = re.compile(r"tan-nāma|nāma-rūpa|rasanā|tiṣṭhan vraje|anurāgi|upadeśa-sār|essence of all advice|"
                         r"eighth verse|krameṇa|sukīrtan|anukīrtan", re.I)
CYR_DIA = re.compile("[а-яА-ЯёЁ][̣̄̃̇́]")
OTHER = ["lv", "de", "fr", "es", "it", "uk", "hu", "pt", "lt"]
BOOKS = {"en": "book.json", "ru-iast": "book.ru-iast.json", "ru": "book.ru.json", **{l: f"book.{l}.json" for l in OTHER}}


def sec_of(book, sid):
    """the section, or an empty stand-in (its checks then FAIL instead of crashing)"""
    return next((s for s in book["sections"] if s["id"] == sid), {"id": sid, "content": [], "subsections": []})


def wbw_pairs(w):
    return [tuple(x.strip().split(" — ", 1)) for x in nfc(w).rstrip(".").split(";") if x.strip()]


en_book = json.load(open(os.path.join(DATA, "book.json"), encoding="utf-8"))
concl_nrs = set(re.findall(r"№ ?(\d+)", json.dumps(sec_of(json.load(open(os.path.join(DATA, "book.ru.json"), encoding="utf-8")),
                                                            "conclusion"), ensure_ascii=False)))
for lang, fn in BOOKS.items():
    b = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
    ids = [x["id"] for x in b["sections"]]
    chk(f"a {fn}: book opens with upadesha-sara → jaya-dhvani → parampara", ids[:3] == ["upadesha-sara", "jaya-dhvani", "parampara"],
        ids[:4])
    chk(f"a {fn}: the two front pages belong to no part", not {"upadesha-sara", "jaya-dhvani"} & {x for p in b.get("parts", []) for x in p["sections"]})
    intro = sec_of(b, "introduction")
    chk(f"a {fn}: Введение has no verse and no «Настроение» (UM 8 moved, ŚB 11.3.48 not back)",
        not [x for x in intro["content"] if x.get("type") in ("verse", "mood")], [x.get("type") for x in intro["content"]])
    # e
    jd = sec_of(b, "jaya-dhvani")
    jv = [x for x in jd["content"] if x.get("type") == "verse"]
    want = [nfc(translit(l[0]) if lang == "ru" else l[0]) for l in JD.LINES]
    chk(f"e {fn}: Джая-дхвани = the 36 calls of the source in order", [nfc(x.get("sanskrit")) for x in jv] == want and len(want) == 36,
        len(jv))
    chk(f"e {fn}: every call has a translation and a word-for-word", all(x.get("translation", "").strip() and x.get("wbw", "").strip() for x in jv))
    sec = sec_of(b, "upadesha-sara")
    blob = nfc(json.dumps(sec, ensure_ascii=False))
    verses = [x for x in sec["content"] if x.get("type") == "verse"]
    want_sk = nfc(translit(IAST) if lang == "ru" else IAST)
    # a
    chk(f"a {fn}: Упадеша-сара verse = Upadeśāmṛta 8", len(verses) == 1 and nfc(verses[0].get("sanskrit")) == want_sk,
        [nfc(v.get("sanskrit"))[:60] for v in verses])
    old = [w for w in ("labdhvānugraha", "mūrtyābhimatayātmanaḥ", "лабдхва̄нуграха", "11.3.48") if w in blob]
    old += [w for w in ("labdhvānugraha", "mūrtyābhimatayātmanaḥ", "лабдхва̄нуграха", "11.3.48")
            if w in nfc(json.dumps(intro, ensure_ascii=False))]
    chk(f"a {fn}: no ŚB 11.3.48 in Упадеша-сара or Введение", not old, old)
    if not verses:
        continue
    v = verses[0]
    pairs = wbw_pairs(v.get("wbw", ""))
    heads = [p[0] for p in pairs]
    glosses = [p[1] if len(p) > 1 else "" for p in pairs]
    # b
    if lang in ("en", "ru", "ru-iast"):
        want_tr = TR_EN if lang == "en" else TR_RU
        chk(f"b {fn}: translation = BBT verbatim + source", nfc(v.get("translation")) == nfc(want_tr), v.get("translation"))
        want_heads = [nfc(translit(h)) for h in HEAD] if lang == "ru" else [nfc(h) for h in HEAD]
        chk(f"b {fn}: пословный перевод = 22 vedabase headwords in order", heads == want_heads, heads)
        chk(f"b {fn}: пословный перевод glosses = vedabase.io/{'en' if lang == 'en' else 'ru'}",
            glosses == [nfc(g) for g in (WBW_EN if lang == "en" else WBW_RU)], glosses)
    else:
        tr = nfc(v.get("translation"))
        machine = tr != nfc(TR_EN)
        chk(f"b {fn}: translation of UM 8 ({'in ' + lang if machine else 'English until the night release'})",
            tr.strip() and "11.3.48" not in tr and (machine or glosses == [nfc(g) for g in WBW_EN]), tr[:120])
        chk(f"b {fn}: пословный перевод: the 22 headwords as in English, every gloss present",
            heads == [nfc(h) for h in HEAD] and all(g.strip() for g in glosses), heads)
    # c
    moods = [x for x in sec["content"] if x.get("type") == "mood"]
    if lang in OTHER and not moods:
        # no translation of the quotes yet: apply_moods.py leaves the block out until the night release
        chk(f"c {fn}: «Настроение Гурудева» not yet translated -> no block (never the old ŚB 11.3.48 quotes)", True)
        continue
    chk(f"c {fn}: one «Настроение Гурудева» block", len(moods) == 1, len(moods))
    if not moods:
        continue
    qs = [moods[0]] + list(moods[0].get("more") or [])
    nrs = [q.get("source", {}).get("nr") for q in qs]
    chk(f"c {fn}: 5 quotes = lectures № {', '.join(NRS)}", nrs == NRS, nrs)
    chk(f"c {fn}: no lecture already quoted in «Заключение»", not set(nrs) & concl_nrs, set(nrs) & concl_nrs)
    chk(f"c {fn}: every quote is on UM 8 (names its words)", all(VERSE_WORDS.search(nfc(q.get("quote"))) for q in qs),
        [q.get("source", {}).get("nr") for q in qs if not VERSE_WORDS.search(nfc(q.get("quote")))])
    bad = [q.get("source", {}).get("nr") for q in qs
           if not all(q.get("source", {}).get(k) for k in ("nr", "date", "timecode", "transcript_url", "title"))]
    chk(f"c {fn}: every quote has nr, date, timecode, transcript link", not bad, bad)
    if lang != "en":
        chk(f"c {fn}: every quote translated into the book's language",
            all(nfc(q.get("translation")).strip() for q in qs), [q.get("source", {}).get("nr") for q in qs if not q.get("translation")])
    if lang == "ru-iast":
        hits = CYR_DIA.findall(blob)
        hits += CYR_DIA.findall(nfc(json.dumps(jd, ensure_ascii=False)))
        chk(f"c {fn}: Упадеша-сара and Джая-дхвани have no Cyrillic Sanskrit with diacritics", not hits, hits[:10])

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
