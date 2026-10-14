# -*- coding: utf-8 -*-
"""Part II «Домашний стандарт», first page: «Поклонение Божествам дома — на одной странице» (Satkirti 14.10.2026
23:08, msg 3486: «инструкция для поклонения божествам в доме одной бумажкой»).

Nothing new is written here: every step is a short pointer to the Temple-standard chapter it comes from, and every
mantra / verse block is COPIED from the book itself (data/book.ru-iast.json and the same block of data/book.ru.json /
data/book.json), found by its text — so the page can never drift from the chapters it summarises.

  python build.py translate  EN for the page's own strings (AnyModel cx/gpt-6.1-sol, alt cx/gpt-6-sol) -> en_cache.json
  python build.py apply      writes data/book.json, data/book.ru.json, data/book.ru-iast.json

RU first (Gurudas, 14.10). The English book needs the chapter too: the app takes the section order and the parts from
it, and lint L27 wants every Sanskrit field of ru-iast at the same place in book.json — the copied verses come from
book.json itself, only the page's own short strings are machine-translated (en_cache.json). Other languages show
English (the app's fallback) until translated. The section is locked for ru / ru-iast in
scripts/translate/locked_sections.json.
"""
import copy, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import hand_chapter as hc  # noqa: E402

SECTION_ID = "home-worship-one-page"
PART_ID = "home-worship"
AFTER = "main-worship-sixteen-items"   # last chapter of Part I — Part II starts right after it
TITLE = "Поклонение Божествам дома — на одной странице"

DATA = hc.DATA
IAST = json.load(open(os.path.join(DATA, "book.ru-iast.json"), encoding="utf-8"))
CYR = json.load(open(os.path.join(DATA, "book.ru.json"), encoding="utf-8"))
EN = json.load(open(os.path.join(DATA, "book.json"), encoding="utf-8"))
CACHE = os.path.join(HERE, "en_cache.json")
SYSTEM = ("You translate a short page of a Gauḍīya Vaiṣṇava Deity-worship manual from Russian into English for the book "
          "'Arcana-paddhati — The Process of Deity Worship'. Rules: faithful, plain, natural book English; do not add or "
          "omit content. Terms with IAST diacritics as in Gauḍīya books: ācamana, pañca-pātra, tilaka, bhoga, ārati, "
          "maṅgala-ārati, sandhyā-ārati, dhūpa-ārati, tulasī, Tulasī-devī, mahā-prasāda, paramparā, cāmara, khīr, "
          "Gopāla-mantra, Gaura-gāyatrī, Kāma-gāyatrī, naivedya, pādya, āsana. «Гурудев» = «Gurudev»; «Шри Шри "
          "Радха-Кришна» = «Śrī Śrī Rādhā-Kṛṣṇa»; «Гауранга» = «Gaurāṅga»; «Шриман Махапрабху» = «Śrīman Mahāprabhu». "
          "Chapter titles of this book: «Ежедневные обязанности, совершаемые в брахма-мухурту» → «Daily Duties performed "
          "in the Brāhma-muhūrta»; «Ежедневное расписание поклонения Божествам» → «Daily Deity Schedule»; «Порядок "
          "подношения бхоги» → «Procedure for Offering Bhoga»; «Главное поклонение с шестнадцатью упачарами» → «The Main "
          "Worship with Sixteen Items»; «Церемония арати» → «Ārati Ceremony»; «Молитвы о прощении оскорблений» → "
          "«Prayers Begging Forgiveness for Offences»; «Храмовый стандарт» → «Temple Standard»; «глава 2» → «chapter 2»; "
          "«Поклонение Божествам дома — на одной странице» → «Deity Worship at Home on One Page». Answer with JSON only.")


def _node(book, sec_id, sub_id):
    s = next(x for x in book["sections"] if x["id"] == sec_id)
    if sub_id is None:
        return s

    def walk(n):
        for x in n.get("subsections", []) or []:
            if x["id"] == sub_id:
                return x
            r = walk(x)
            if r:
                return r
    r = walk(s)
    assert r, (sec_id, sub_id)
    return r


def B(sec_id, sub_id, starts, n=1, items=None):
    """The n-th block of chapter `sec_id` / subsection `sub_id` whose text starts with `starts` (IAST book), copied
    verbatim; the same block (same place) of the Cyrillic and the English book. `items`: keep only the first rows."""
    node = _node(IAST, sec_id, sub_id)
    hits = [i for i, b in enumerate(node["content"])
            if (b.get("sanskrit") or b.get("content") or "").startswith(starts)
            or (b.get("type") == "paired-list" and b["items"][0]["label"].startswith(starts))]
    assert len(hits) >= n, (sec_id, sub_id, starts, hits)
    i = hits[n - 1]
    a = copy.deepcopy(node["content"][i])
    c = copy.deepcopy(_node(CYR, sec_id, sub_id)["content"][i])
    e = copy.deepcopy(_node(EN, sec_id, sub_id)["content"][i])
    assert a["type"] == c["type"] == e["type"], (sec_id, sub_id, i)
    assert a.get("sanskrit") == e.get("sanskrit"), (sec_id, sub_id, i)
    if items is not None:
        for x in (a, c, e):
            x["items"] = x["items"][:items]
    return {"ru-iast": a, "ru": c, "en": e}


_EN = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
TODO = []   # RU strings without an English translation yet


def en(text):
    if text not in _EN:
        TODO.append(text)
    return _EN.get(text, text)


def T(kind, text):
    """Own short text of this page (RU; inline ⟦…⟧ terms; IAST mantras become Cyrillic in the ru book)."""
    return {"ru-iast": {"type": kind, "content": text}, "ru": {"type": kind, "content": hc.map_inline(text, hc.translit)},
            "en": {"type": kind, "content": en(text)}}


DDS = "daily-deity-schedule"
MAIN = "main-worship-sixteen-items"

INTRO = [
    T("text", "Краткий порядок ежедневного поклонения Божествам дома. Всё на этой странице взято из глав "
              "«Храмового стандарта»; подробности — в указанных главах."),
    T("text", "Порядок при пробуждении и поклонении: сначала ⟦Гурудев⟧, затем ⟦Гауранга⟧, затем ⟦Шри Шри "
              "Радха-Кришна⟧. При арати каждый предмет предлагают сначала ⟦Кришне⟧, затем ⟦Радхике⟧, ⟦Гауранге⟧, "
              "далее по парампаре и ⟦Гурудеву⟧."),
    T("text", "Если какого-то предмета нет, можно медитировать на него и, произнося мантру, предложить воду из "
              "⟦панча-патры⟧ (глава 2)."),
]

SUBS = [
    {"id": "home-before-service", "title": "Перед служением", "content": [
        T("instruction", "Омовение, чистая одежда, ⟦тилака⟧. Перед входом к Божествам — ачаман:"),
        B("daily-duties-brahma-muhurta", "sadhararana-acamana", "⟦oṁ keśavāya namaḥ⟧", items=3),
        T("text", "Подробно — глава 1 «Ежедневные обязанности, совершаемые в брахма-мухурту»."),
    ]},
    {"id": "home-morning", "title": "Утро: пробуждение и мангала-арати", "content": [
        T("instruction", "Позвоните в колокольчик за дверью, постучите и войдите. Касаясь стоп, пробудите "
                         "⟦Гурудева⟧, ⟦Гаурангу⟧ и ⟦Шри Шри Радха-Кришну⟧:"),
        B(DDS, "waking-the-lord", "uttiṣṭhottiṣṭha śrī guro"),
        B(DDS, "waking-the-lord", "uttiṣṭhottiṣṭha gaurāṅga"),
        B(DDS, "waking-the-lord", "go-gopa-gokulānanda"),
        T("instruction", "Предложите ачаман (воду для уст): ложку воды из ⟦панча-патры⟧ — в пустой сосуд, звоня в "
                         "колокольчик:"),
        B(DDS, "washing-mouth", "idaṁ ācamanīyaṁ aiṁ gurave namaḥ"),
        T("instruction", "Затем мысленно предложите веточку для чистки зубов (⟦eṣa danta-kāṣṭhaḥ⟧ …) и снова ачаман — "
                         "12 раз (допустимо 3)."),
        T("instruction", "Протрите лицо, руки и стопы Божеств чистой тканью; снимите старые цветы и туласи, очистите "
                         "алтарь; предложите туласи и украсьте Божества."),
        T("instruction", "Предложите бхогу (см. «Бхога») и проведите ⟦мангала-арати⟧ (см. «Арати»)."),
        T("text", "Подробно — глава 2 «Ежедневное расписание поклонения Божествам»."),
    ]},
    {"id": "home-bhoga", "title": "Бхога (каждый раз одинаково)", "content": [
        T("instruction", "Предлагайте бхогу с чувством, что ⟦Шри Гурудев⟧ сам предлагает её ⟦Шриману Махапрабху⟧ и "
                         "⟦Шри Шри Радха-Кришне⟧. Совершите ачаман. На каждое блюдо положите листок туласи. Снимите с Божеств корону и "
                         "флейту."),
        T("instruction", "Звоня в колокольчик, предложите лепестки цветов к стопам, асану, падью, ачаман и найведью:"),
        B("offering-bhoga", "bhoga-procedure", "eṣa puṣpāñjaliḥ"),
        B("offering-bhoga", "bhoga-procedure", "idaṁ naivedyaṁ"),
        T("text", "Асану, падью и ачаман предлагают так же, заменяя первые слова: ⟦idaṁ āsanaṁ⟧, ⟦etat pādyaṁ⟧, "
                  "⟦idaṁ ācamanīyaṁ⟧."),
        T("instruction", "Держа правую руку над тарелкой (левая поверх правой), восемь раз повторите "
                         "⟦гопала-мантру⟧. Выйдите; по десять раз — ⟦гаура-гаятри⟧ и ⟦кама-гаятри⟧ (мантры, полученные "
                         "от гуру); немного подождите."),
        T("instruction", "Постучите, войдите, предложите воду для полоскания рта (⟦idaṁ ācamanīyaṁ⟧), тамбулу "
                         "(⟦idaṁ tāmbūlaṁ⟧) и асану (⟦idaṁ āsanaṁ⟧), уберите тарелку. Верните корону и флейту. Остатки — "
                         "⟦махапрасад⟧ — предложите Гурудеву и вайшнавам (⟦idaṁ mahā-prasādaṁ aiṁ gurave namaḥ⟧ …)."),
        T("text", "Подробно — глава 6 «Порядок подношения бхоги»."),
    ]},
    {"id": "home-arati", "title": "Арати", "content": [
        T("instruction", "Предметы арати и порядок их предложения:"),
        B(MAIN, "arati-ceremony", "Благовония"),
        T("instruction", "К названию предмета добавляют мантру того, кому его предлагают: ⟦śrīṁ klīṁ "
                         "rādhā-kṛṣṇābhyāṁ namaḥ⟧, ⟦klīṁ gaurāya svāhā⟧, ⟦aiṁ gurave namaḥ⟧."),
        T("instruction", "Короткое ⟦дхупа-арати⟧ (после завтрака, днём и поздно вечером): благовония, цветы, "
                         "⟦чамара⟧ и павлинье опахало (не зимой)."),
        T("text", "Подробно — глава 10 «Главное поклонение с шестнадцатью упачарами», «Церемония арати»."),
    ]},
    {"id": "home-day", "title": "Днём", "content": [
        T("instruction", "Подношение бхоги (тот же порядок) и полное арати. Если днём Божества отдыхают — уложите Их теми же "
                         "молитвами, что вечером, и пробудите, как утром (глава 2)."),
    ]},
    {"id": "home-evening", "title": "Вечер: сандхья-арати и отдых", "content": [
        T("instruction", "Бхога и ⟦сандхья-арати⟧; позже — ещё бхога и ⟦дхупа-арати⟧."),
        T("instruction", "Уберите ⟦Туласи-деви⟧ с алтаря, цветы и гирлянды; оденьте Божества просто; снимите короны "
                         "и флейту; предложите кхир и воду."),
        T("instruction", "Касаясь Их стоп, пригласите отдыхать:"),
        B(DDS, "putting-deities-to-rest-evening", "āgaccha śayana-sthānaṁ"),
        B(DDS, "putting-deities-to-rest-evening", "āgaccha viśrama-sthānaṁ"),
        B(DDS, "putting-deities-to-rest-evening", "āgaccha viśrāma-sthānaṁ"),
        T("instruction", "Прочитайте молитву о прощении оскорблений:"),
        B("prayers-forgiveness", "short-version-forgiveness", "aṅga-hīnaṁ kriyā-hīnaṁ"),
        T("text", "Подробно — глава 2 «Ежедневное расписание поклонения Божествам» и глава 9 «Молитвы о прощении "
                  "оскорблений»."),
    ]},
]


def section(lang):
    def title(t):
        return en(t) if lang == "en" else t
    return {"id": SECTION_ID, "title": title(TITLE), "subtitle": None, "page": "",
            "content": [b[lang] for b in INTRO],
            "subsections": [{"id": s["id"], "title": title(s["title"]), "content": [b[lang] for b in s["content"]]}
                            for s in SUBS]}


def translate():
    """EN for the page's own strings (AnyModel cx/gpt-6.1-sol, alternative cx/gpt-6-sol — Gurudas' rule)."""
    import configparser
    import requests
    section("en")
    todo = list(dict.fromkeys(TODO))
    if not todo:
        print("EN: nothing new")
        return
    c = configparser.ConfigParser()
    c.read(os.path.expanduser("~/.credentials/ca_pipeline/config.ini"), encoding="utf-8")
    keys = [c["anymodel"][f"key_{i}"] for i in range(20, 0, -1) if f"key_{i}" in c["anymodel"]]
    prompt = ("Translate each string of this JSON array from Russian into English. Keep the ⟦ ⟧ markers around the same "
              "terms; inside them write the English/IAST form (⟦Гурудев⟧ → ⟦Gurudev⟧, ⟦панча-патры⟧ → ⟦pañca-pātra⟧); "
              "IAST Sanskrit inside ⟦ ⟧ (e.g. ⟦idaṁ āsanaṁ⟧) stays exactly as it is. Return a JSON array of the same "
              "length and order, strings only.\n\n" + json.dumps(todo, ensure_ascii=False, indent=0))
    last = None
    for model in ("cx/gpt-6.1-sol", "cx/gpt-6-sol"):
        for k in keys:
            try:
                r = requests.post("https://anymodel.org/v1/chat/completions", headers={"Authorization": "Bearer " + k},
                                  json={"model": model, "messages": [{"role": "system", "content": SYSTEM},
                                                                     {"role": "user", "content": prompt}]}, timeout=600)
                if r.status_code != 200:
                    last = (model, r.status_code, r.text[:200])
                    continue
                out = r.json()["choices"][0]["message"]["content"]
                got = json.loads(re.search(r"\[.*\]", out, re.S).group(0))
                assert len(got) == len(todo), (len(got), len(todo))
                for x, y in zip(todo, got):
                    assert x.count("⟦") == y.count("⟦"), (x, y)
                    _EN[x] = y
                json.dump(_EN, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                print("EN:", len(todo), "strings with", model)
                return
            except Exception as e:  # noqa: BLE001
                last = (model, str(e)[:200])
    raise SystemExit(f"AnyModel failed: {last}")


def apply():
    secs = {"en": section("en"), "ru": section("ru"), "ru-iast": section("ru-iast")}
    if TODO:
        raise SystemExit("EN missing for %d strings — run: python build.py translate" % len(set(TODO)))
    for lang, sec in secs.items():
        path = os.path.join(DATA, hc.FILES[lang])
        book = json.load(open(path, encoding="utf-8"))
        book["sections"] = [s for s in book["sections"] if s["id"] != SECTION_ID]
        ids = [s["id"] for s in book["sections"]]
        book["sections"].insert(ids.index(AFTER) + 1, sec)
        part = next(p for p in book["parts"] if p["id"] == PART_ID)
        if SECTION_ID in part["sections"]:
            part["sections"].remove(SECTION_ID)
        part["sections"].insert(0, SECTION_ID)
        hc.write_json(path, book)
        print("wrote", lang)
    # other languages: the English section translated by scripts/translate/night_sync.py (i18n.json here);
    # every book lists the chapter in Part II (a book without a translation shows the English one)
    en_book = json.load(open(os.path.join(DATA, hc.FILES["en"]), encoding="utf-8"))
    en_ids = [s["id"] for s in en_book["sections"]]
    for lang in hc.OTHER:
        path = os.path.join(DATA, f"book.{lang}.json")
        book = json.load(open(path, encoding="utf-8"))
        st = hc.put(book, lang, SECTION_ID, HERE, secs["en"], en_ids)
        part = next(p for p in book["parts"] if p["id"] == PART_ID)
        if SECTION_ID not in part["sections"]:
            part["sections"].insert(0, SECTION_ID)
        hc.write_json(path, book)
        print("wrote", lang, st)


if __name__ == "__main__":
    if sys.argv[1:] == ["apply"]:
        apply()
    elif sys.argv[1:] == ["translate"]:
        translate()
    else:
        print(__doc__)
