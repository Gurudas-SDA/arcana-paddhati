# -*- coding: utf-8 -*-
"""Parampara section (Reader v7.4) -> data/book.json, book.ru.json, book.ru-iast.json.

Satkirti 06.10.2026 23:15–23:33 + 07.10.2026 12:34 / 13:07 (Стандарты книги, «Начало книги»):
  Обложка → [Шри Панча-таттва] → Парампара → «Мангалачарана» → «Введение»;
  one page = one guru (as in «Ведические мудрые истории»), oval frame (variant A);
  8 gurus, Śrīla Jagannātha dāsa Bābājī on his own page, no Gour Govinda Svāmī;
  portrait + caption only: no headings, no page numbers.
Captions: as in «Ведические мудрые истории» (RU) and «Gauḍīya-darśana» (EN), table of the analysis
«Начало книги по образцу книг Гурудева — анализ 2026-10-07», section 5 («Предлагаю» column);
Jagannātha dāsa Bābājī (not in those two books) as in «Haven of Love» / «The Victory of Pure Love»;
Gurudev — our standard «Шри Према Прайоджана Прабху» (02.10), EN as in his English books.

Satkirti 07.10 13:35: the page «Шри Панча-таттва» comes FIRST (same oval, caption «Шри Панча-таттва»),
then the 8 gurus. Picture sources: «Источники изображений v7.4.md» in the draft folder (to be replaced
with better pictures later: re-render with render_parampara.py, keep the file names).

    python scripts/parampara/apply_parampara.py      (idempotent)
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DATA = os.path.join(REPO, "data")
SECTION_ID = "parampara"
BEFORE = "mangalacarana"

TITLE = {"ru": "Гуру-парампара", "en": "Guru-paramparā"}
CAPTIONS = [  # (image, RU, EN)
    ("00", "Шри Панча-таттва", "Śrī Pañca-tattva"),
    ("01", "Шрила Джаганнатха дас Бабаджи Махарадж", "Śrīla Jagannātha dāsa Bābājī Mahārāja"),
    ("02", "Шрила Саччидананда Бхактивинода Тхакур", "Śrīla Saccidānanda Bhaktivinoda Ṭhākura"),
    ("03", "Шрила Гаура Кишора дас Бабаджи Махарадж", "Śrīla Gaura Kiśora dāsa Bābājī Mahārāja"),
    ("04", "Прабхупада Шрила Бхактисиддханта Сарасвати Тхакур", "Prabhupāda Śrīla Bhaktisiddhānta Sarasvatī Ṭhākura"),
    ("05", "Шрила Бхакти Праджнана Кешава Госвами Махарадж", "Śrīla Bhakti Prajñāna Keśava Gosvāmī Mahārāja"),
    ("06", "Шрила А. Ч. Бхактиведанта Свами Прабхупада", "Śrīla AC Bhaktivedānta Svāmī Prabhupāda"),
    ("07", "Шрила Бхактиведанта Нараяна Госвами Махарадж", "Śrīla Bhaktivedānta Nārāyaṇa Gosvāmī Mahārāja"),
    ("08", "Шри Према Прайоджана Прабху", "Śrī Prem Prayojan Prabhu"),
]


def section(lang):
    k = 1 if lang.startswith("ru") else 2
    return {
        "id": SECTION_ID,
        "title": TITLE["ru" if k == 1 else "en"],
        "subtitle": None,
        "page": "",
        "layout": "portraits",
        "content": [{"type": "portrait", "src": f"parampara/{c[0]}.png", "caption": c[k]} for c in CAPTIONS],
        "subsections": [],
    }


def write_json(path, obj):
    raw = open(path, encoding="utf-8", newline="").read()
    nl = "\n" if raw.endswith("\n") else ""
    open(path, "w", encoding="utf-8", newline="").write(json.dumps(obj, ensure_ascii=False, indent=2) + nl)


def main():
    for lang, fn in (("en", "book.json"), ("ru", "book.ru.json"), ("ru-iast", "book.ru-iast.json")):
        path = os.path.join(DATA, fn)
        book = json.load(open(path, encoding="utf-8"))
        book["sections"] = [s for s in book["sections"] if s["id"] != SECTION_ID]
        ids = [s["id"] for s in book["sections"]]
        book["sections"].insert(ids.index(BEFORE), section(lang))
        write_json(path, book)
        print("wrote", fn, [s["id"] for s in book["sections"]][:4])


if __name__ == "__main__":
    main()
