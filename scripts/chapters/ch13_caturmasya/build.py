# -*- coding: utf-8 -*-
"""Part IV, chapter 13 «Чатурмасья и Пурушоттама-маса» -> data/book*.json (+ ui strings).

The RU master text is chapter_ru.py (hand-written, not machine-translated from English); EN is its translation
(en_cache.json). The calendar table comes from calendar/table_Riga.json (calendar/gen_calendar.py).
  python build.py translate   -> en_cache.json (only strings changed in chapter_ru.py), i18n_cache.json (AnyModel)
  python build.py apply       -> writes data/book*.json + data/ui.*.json; idempotent (re-run = no diff)
After apply: python scripts/moods/apply_moods.py (re-inserts the Gurudev mood blocks), then npm run build.
The section is locked in scripts/translate/locked_sections.json, so tr.py assemble keeps it as written here.
"""
import json, os, re, sys, copy, datetime, importlib.util
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
DATA = os.path.join(REPO, "data")
sys.path.insert(0, os.path.join(REPO, "scripts", "translate"))
from iast_to_cyrillic import translit  # noqa
sys.path.insert(0, HERE)

spec = importlib.util.spec_from_file_location("ch", os.path.join(HERE, "chapter_ru.py"))
ch = importlib.util.module_from_spec(spec); spec.loader.exec_module(ch)

PART = {"id": "festivals-vows", "ru": "Праздники и обеты", "en": "Festivals and Vows"}
OTHER = ["lv", "de", "fr", "es", "it", "uk", "hu"]
LNAME = {"lv": "Latvian", "de": "German", "fr": "French", "es": "Spanish", "it": "Italian", "uk": "Ukrainian", "hu": "Hungarian", "ru": "Russian"}

# ------------------------------------------------------------ calendar
ROWS = json.load(open(os.path.join(HERE, "calendar", "table_Riga.json"), encoding="utf-8"))
RU_M = {3: "мар.", 4: "апр.", 5: "мая", 6: "июня", 7: "июля", 8: "авг.", 9: "сент.", 10: "окт.", 11: "нояб.", 12: "дек."}
EN_M = {3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
D = datetime.date.fromisoformat


def fmt(iso, lang):
    d = D(iso)
    return f"{d.day} {(RU_M if lang.startswith('ru') else EN_M)[d.month]}"


def calendar(lang):
    ru = lang.startswith("ru")
    header = (["Год", "Начало: 1-й месяц — без шака (Гуру-пурнима)", "2-й месяц — без йогурта", "3-й месяц — без молока; Вишварупа-махотсава",
               "4-й месяц — Карттика", "Бхишма-панчака", "Окончание (Карттика-пурнима)", "Пурушоттама-маса"] if ru else
              ["Year", "Start: 1st month — no śāk (Guru-pūrṇimā)", "2nd month — no yoghurt", "3rd month — no milk; Viśvarūpa-mahotsava",
               "4th month — Kārttika", "Bhīṣma-pañcaka", "End (Kārttika-pūrṇimā)", "Puruṣottama-māsa"])
    rows, inside = [], []
    for r in ROWS:
        starts = [r["m1"][0], r["m2"][0], r["m3"][0], r["m4"][0]]
        assert r["m1"] == r["guru"], r
        b0, b1 = r["bhisma"]
        assert starts[3] < b0 <= b1 <= r["end"], (r["year"], b0, b1)
        bp = (f"{D(b0).day}–{fmt(b1, lang)}" if D(b0).month == D(b1).month else f"{fmt(b0, lang)} – {fmt(b1, lang)}")
        cells = [str(r["year"])] + [fmt(x, lang) for x in starts] + [bp, fmt(r["end"], lang)]
        adh = r["adhika"]
        if adh:
            a0, a1 = adh[0], adh[1]
            cells.append(f"{fmt(a0, lang)} – {fmt(a1, lang)}")
            if starts[0] <= a0 <= r["end"]:
                k = max(i for i in range(4) if starts[i] <= a0)
                cells[1 + k] += "*"
                cells[-1] += "*"
                nxt = starts[k + 1] if k < 3 else r["end"]
                last = (D(nxt) - datetime.timedelta(1)).isoformat()
                inside.append((r["year"], k + 1, starts[k], last, a0, a1))
        else:
            cells.append("—")
        row = {"cells": cells}
        if adh:
            row["highlight"] = True
            row["badge"] = "Пурушоттама-маса" if ru else "Puruṣottama-māsa"
        rows.append(row)
    return {"type": "table", "header": header, "rows": rows}, inside


def cal_texts_ru(inside):
    MON = {1: "первый", 2: "второй", 3: "третий", 4: "четвёртый"}
    parts = []
    for (y, k, s, e, a0, a1) in inside:
        parts.append(f"{y} г. — {MON[k]} месяц обета: {fmt(s,'ru')} — {fmt(e,'ru')} (Пурушоттама-маса {fmt(a0,'ru')} — {fmt(a1,'ru')})")
    star = ("* В эти годы Пурушоттама-маса приходится на саму чатурмасью, и по расчёту GCal месяц обета, в который она "
            "попадает, продлевается до следующей пурнимы: " + "; ".join(parts) +
            ". Как соблюдать обет в такой год, уточняйте по календарю Чайтанья Академии на этот год.")
    return [
        {"type": "text", "content": "В таблице указан день, с которого начинается каждый месяц обета (это день пурнимы), даты "
                                    "Бхишма-панчаки (последние пять дней Карттики, от Уттхана-экадаши) и день окончания "
                                    "чатурмасьи. День начала третьего месяца — это и Вишварупа-махотсава (Бхадра-пурнима), "
                                    "когда брахмачари и санньяси могут побриться. Годы, в которые есть Пурушоттама-маса, выделены цветом; её даты — "
                                    "в последнем столбце."},
        {"type": "text", "content": "Даты рассчитаны для Риги (Латвия) — для неё составлен вайшнавский календарь Чайтанья Академии. "
                                    "В других местах даты могут отличаться на день; сверяйтесь с календарём для своего места."},
        "TABLE",
        {"type": "text", "content": star},
        {"type": "text", "content": "Как получены даты. Все годы рассчитаны для Риги программой GCal 11 (Gaurābda Calendar, "
                                    "ISKCON GBC Vaiṣṇava Calendar Committee; открытая библиотека gaurabda для Python, автор — "
                                    "Гопалаприя дас) — по правилу «пурнима-системы»: обет начинается в Гуру-пурниму, а каждый "
                                    "следующий месяц — в очередную пурниму. Проверка: на период, который охватывает "
                                    "опубликованный календарь Чайтанья Академии (сентябрь 2026 — ноябрь 2027), совпали все даты "
                                    "чатурмасьи (8 из 8) и все экадаши (31 из 31); Вишварупа-махотсава в GCal во все годы "
                                    "совпадает с началом третьего месяца, как и в календаре Чайтанья Академии. Пурушоттама-маса в GCal считается от "
                                    "новолуния до новолуния; для 2026 года это совпадает с общепринятыми датами адхика-масы "
                                    "(17 мая — 15 июня)."},
    ]


# ------------------------------------------------------------ helpers
def ru_master():
    sec = {"id": ch.SECTION_ID, "title": ch.TITLE, "subtitle": ch.SUBTITLE, "page": "",
           "content": copy.deepcopy(ch.INTRO), "subsections": copy.deepcopy(ch.SUBS)}
    tbl, inside = calendar("ru")
    blocks = [tbl if b == "TABLE" else b for b in cal_texts_ru(inside)]
    sec["subsections"].append({"id": "caturmasya-calendar", "title": ch.CAL_TITLE, "content": blocks})
    return sec


def strings_of(sec):
    """(path, text) of every translatable string (not verse sanskrit, not tables)."""
    out = [(("title",), sec["title"])]
    def walk(blocks, base):
        for i, b in enumerate(blocks):
            for k in ("content", "translation"):
                if b.get(k) and b["type"] != "table":
                    out.append((base + (i, k), b[k]))
    walk(sec["content"], ("content",))
    for j, sub in enumerate(sec["subsections"]):
        out.append((("subsections", j, "title"), sub["title"]))
        walk(sub["content"], ("subsections", j, "content"))
    return out


def set_path(obj, path, val):
    for p in path[:-1]:
        obj = obj[p]
    obj[path[-1]] = val


def map_inline(text, fn):
    return re.sub(r"⟦([^⟦⟧]*)⟧", lambda m: "⟦" + fn(m.group(1)) + "⟧", text)


def to_cyr(sec):
    s = copy.deepcopy(sec)
    s["subtitle"] = translit(s["subtitle"])
    def blocks(bs):
        for b in bs:
            if b["type"] == "verse":
                b["sanskrit"] = translit(b["sanskrit"])
            for k in ("content", "translation"):
                if b.get(k) and isinstance(b[k], str):
                    b[k] = map_inline(b[k], translit)
    blocks(s["content"])
    for sub in s["subsections"]:
        blocks(sub["content"])
    return s


KESAVA_EN = ("“Kārtika-vrata niyama-sevā is a part of cāturmāsya-vrata. Fully mature bhakti, which is the fruit of observing "
             "cāturmāsya-vrata, will not develop if one only honours ūrjā-vrata and not the full four months. In fact, this "
             "negligence actually reveals disrespect for cāturmāsya-vrata.”")

SYSTEM = ("You translate a chapter of a Gauḍīya Vaiṣṇava Deity-worship manual from Russian into English for the book "
          "'Arcana-paddhati — The Process of Deity Worship'. Rules: faithful, plain, natural book English; do not add or omit "
          "content. Keep every ⟦…⟧ span exactly as it is (characters and markers unchanged). Sanskrit names and terms in "
          "English with IAST diacritics, as in Gauḍīya books: Cāturmāsya, Kārttika, Puruṣottama-māsa, Guru-pūrṇimā, "
          "Vyāsa-pūrṇimā, Śayana Ekādaśī, Utthāna Ekādaśī, Āṣāḍha, Śrāvaṇa, Bhādra, Āśvina, Śrīdhara, Hṛṣīkeśa, Padmanābha, "
          "Dāmodara, saṅkalpa, niyama-sevā, Dāmodarāṣṭaka(m), Hari-bhakti-vilāsa, Skanda Purāṇa, Bhakti-rasāmṛta-sindhu, "
          "Śrīla Bhaktisiddhānta Sarasvatī Ṭhākura, Śrīla Bhakti Prajñāna Keśava Gosvāmī Mahārāja, Śrīla Bhaktivedānta "
          "Nārāyaṇa Gosvāmī Mahārāja, Śrīla A. C. Bhaktivedānta Svāmī Prabhupāda, Śrī Caitanya Mahāprabhu, Veṅkaṭa Bhaṭṭa, "
          "Śrīraṅgam, Śrīmatī Rādhikā, Ūrjeśvarī, Bhīṣma-pañcaka, Viśvarūpa-mahotsava, Gauḍīya Vedānta Samiti, "
          "Jagannātha Purī, Puruṣottama-kṣetra, Nārāyaṇa, Goloka, Rāma-vijaya-daśamī, śāk (leafy vegetables), urad dal, "
          "laukī, parmal. «Гурудев» = «Gurudev» (our spiritual master Śrī Prem Prayojan Prabhu). Book titles in italics are "
          "not marked; write them plainly: Arcana-dīpikā, Hari-bhakti-vilāsa. «лекция № 9643 от 06.07.2025» → "
          "«lecture no. 9643, 6 July 2025» (same pattern for all lectures). «Арчана-дипика», рус. изд., Дополнение для "
          "русского издания, с. 122 → «Arcana-dīpikā, Russian edition, Supplement to the Russian edition, p. 122». A "
          "quotation from the Russian supplement of Arcana-dīpikā is translated and followed by «(translated from the "
          "Russian)». The quotation of Śrīla Keśava Gosvāmī Mahārāja must be replaced by this exact English original: "
          + KESAVA_EN + " Russian dates like «17 мая» → «17 May». Answer with JSON only.")


def translate():
    from am import chat  # AnyModel; only needed here
    sec = ru_master()
    items = strings_of(sec)
    texts = [t for _, t in items]
    cp = os.path.join(HERE, "en_cache.json")
    old = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {"src": [], "en": [], "model": ""}
    known = dict(zip(old["src"], old["en"]))
    todo = [t for t in texts if t not in known]
    model = old.get("model", "")
    if todo:
        prompt = ("Translate each string of this JSON array from Russian into English. Return a JSON array of the same "
                  "length and order, strings only.\n\n" + json.dumps(todo, ensure_ascii=False, indent=0))
        out, model = chat(prompt, system=SYSTEM)
        m = re.search(r"\[.*\]", out, re.S)
        got = json.loads(m.group(0))
        assert len(got) == len(todo), (len(got), len(todo))
        for a, b in zip(todo, got):
            assert a.count("⟦") == b.count("⟦"), (a, b)
            known[a] = b
    print("translated", len(todo), "new strings")
    arr = [known[t] for t in texts]
    json.dump({"model": model, "src": texts, "en": arr}, open(os.path.join(HERE, "en_cache.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("EN done with", model, len(arr))
    if os.path.exists(os.path.join(HERE, "i18n_cache.json")):
        return
    # part title + fallback note in the other languages
    req = {"part": "Festivals and Vows",
           "note": "Translation in preparation — this chapter is shown in English."}
    langs = OTHER + ["ru"]
    prompt = ("Translate these two English UI strings of a Vaiṣṇava Deity-worship book app into each language: "
              + ", ".join(f"{l} ({LNAME[l]})" for l in langs) +
              ". 'Festivals and Vows' is the title of Part IV of the book (Vaiṣṇava festivals and vows/vratas). Return JSON "
              "{lang: {\"part\": ..., \"note\": ...}} only.\n\n" + json.dumps(req))
    out, model = chat(prompt)
    m = re.search(r"\{.*\}", out, re.S)
    j = json.loads(m.group(0))
    json.dump({"model": model, "i18n": j}, open(os.path.join(HERE, "i18n_cache.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("i18n done with", model, j)


def build_en():
    sec = ru_master()
    cache = json.load(open(os.path.join(HERE, "en_cache.json"), encoding="utf-8"))
    items = strings_of(sec)
    assert [t for _, t in items] == cache["src"], "RU master changed since translation — re-run translate"
    en = copy.deepcopy(sec)
    for (path, _), t in zip(items, cache["en"]):
        set_path(en, path, t)
    # the calendar table + its texts are built per language, not translated, except the explanatory texts
    tbl, inside = calendar("en")
    cal = en["subsections"][-1]["content"]
    for i, b in enumerate(cal):
        if b["type"] == "table":
            cal[i] = tbl
    return en


def upsert_section(book, sec):
    ids = [s["id"] for s in book["sections"]]
    if sec["id"] in ids:
        book["sections"][ids.index(sec["id"])] = sec
    else:
        book["sections"].append(sec)


def write_json(path, obj):
    raw = open(path, encoding="utf-8", newline="").read() if os.path.exists(path) else "\n"
    nl = "\n" if raw.endswith("\n") else ""
    open(path, "w", encoding="utf-8", newline="").write(json.dumps(obj, ensure_ascii=False, indent=2) + nl)


def apply():
    ru = ru_master()
    en = build_en()
    i18n = json.load(open(os.path.join(HERE, "i18n_cache.json"), encoding="utf-8"))["i18n"]
    files = {"en": "book.json", "ru": "book.ru.json", "ru-iast": "book.ru-iast.json"}
    for lang in ["en", "ru", "ru-iast"] + OTHER:
        book = json.load(open(os.path.join(DATA, files.get(lang, f"book.{lang}.json")), encoding="utf-8"))
        if lang == "en":
            upsert_section(book, en); title = PART["en"]
        elif lang == "ru":
            upsert_section(book, to_cyr(ru)); title = PART["ru"]
        elif lang == "ru-iast":
            upsert_section(book, ru); title = PART["ru"]
        else:
            title = i18n[lang]["part"]
        # every book lists the part; the chapter id is listed in the English book (structure source) and in books that have it
        parts = book.setdefault("parts", [])
        p = next((x for x in parts if x["id"] == PART["id"]), None)
        if p is None:
            p = {"id": PART["id"], "title": title, "sections": []}
            parts.append(p)
        p["title"] = title
        if ch.SECTION_ID not in p["sections"]:
            p["sections"].append(ch.SECTION_ID)
        write_json(os.path.join(DATA, files.get(lang, f"book.{lang}.json")), book)
        print("wrote", lang)
    # ui strings
    for lang in ["en", "ru", "ru-iast"] + OTHER:
        p = os.path.join(DATA, f"ui.{lang}.json")
        ui = json.load(open(p, encoding="utf-8"))
        if lang == "en":
            ui["section.fallback"] = "Translation in preparation — this chapter is shown in English."
        else:
            ui["section.fallback"] = i18n["ru" if lang == "ru-iast" else lang]["note"]
        write_json(p, ui)
    print("ui done")


if __name__ == "__main__":
    {"translate": translate, "apply": apply}[sys.argv[1]]()
