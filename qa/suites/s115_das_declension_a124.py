# Гаура-Кишоре — rakstība gaida S (neatbildetie 28.10); tests pārbauda tikai locījumus.
"""A124 Саткирти msg 6859 (27.10.2026): «Насчёт этих склонений — бери за основу что-то самое авторитетное, и больше меня сейчас не спрашивай. И всё потом запускай».
Правило 63 «Стандартов»: «Грамматика. Исправлять неправильные формы слов, окончания, согласование и построение предложений.»
Правило 115: песни — по «Песеннику гаудия-вайшнава» (Воронеж 2015). Авторитет для формы имени: Песенник → BBT RU → «Бхаджана-рахасья» (Москва 2005).
Data-only test over data/book.ru.json, data/book.ru-iast.json and their sources (scripts/moods/moods.json, scripts/chapters/ch16_arati_songs/pesni_arati.json):
  1. «Джаганнатхе дас Бабаджи» (datīvs + nominatīvs «дас») nav — ir «Джаганнатхе дасу Бабаджи» (Песенник: «Шриле Джаганнатхе дасу Бабаджи»).
  2. «дасы» nav (ģenitīvs no «дас» = «даса»; Песенник: «Шрилы Рагхунатхи даса Госвами»).
  3. (atcelts 28.10) «Гаура-Кишор…» rakstība (defise) atgriezta — gaida S; tests to nepārbauda.
  4. Autora rinda «Шри Враджа-дхама-махимамрита» paliek «Кришнадас» (S msg 6859).
# tehniskais slieksnis Lipikāra, nav S noteikums: concrete counts = cases found in origin/main b00c5aa before the fix.
usage: python s115_das_declension_a124.py
"""
import json
import os
import re
import sys

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
FILES = ["data/book.ru.json", "data/book.ru-iast.json", "scripts/moods/moods.json",
         "scripts/chapters/ch16_arati_songs/pesni_arati.json"]
res = []


def chk(name, ok, ev=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] data {name} {ev if not ok else ''}".rstrip(), flush=True)


BAD = {
    "Джаганнатхе дас Бабаджи": re.compile(r"Джаганнатхе дас(?![а-яё])"),
    "дасы": re.compile(r"(?<![А-Яа-яЁё])[Дд]асы(?![а-яё])"),
}
for rel in FILES:
    t = open(os.path.join(REPO, rel), encoding="utf-8").read()
    for name, rx in BAD.items():
        chk(f"{rel}: no «{name}»", not rx.search(t), f"{len(rx.findall(t))} left")

GOOD = {  # per book file
    "Шриле Джаганнатхе дасу Бабаджи": 1,
    "Рагхунатхи даса Госвами": 2,
}
for rel in FILES[:2]:
    t = open(os.path.join(REPO, rel), encoding="utf-8").read()
    for s, n in GOOD.items():
        chk(f"{rel}: «{s}» ×{n}", t.count(s) == n, f"found {t.count(s)}")
    book = json.loads(t)
    sec = next(s for s in book["sections"] if s["id"] == "mangala-arati-songs")
    sub = next(x for x in sec["subsections"] if "Враджа-дхама-махимамрита" in x["title"])
    chk(f"{rel}: author line «Кришнадас» kept", sub["content"][0].get("content") == "Кришнадас",
        repr(sub["content"][0].get("content")))

print(f"s115: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
