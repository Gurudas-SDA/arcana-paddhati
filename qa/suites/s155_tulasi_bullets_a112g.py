"""A112g (Туласи Сундари, решает сама; Липикара msg 7688/7689, бот 192/194/204/205, 06.11.2026), раздел «Ежедневное поклонение Туласи».
Туласи Сундари (burtiski): «Изменение в разделе про Туласи: убери эти цифры 1.1) и 1.2) и тд сделай как в прошлих отделах, с точками :» / «По типу как на скрине».
Туласи Сундари: «Да. Пункт про руки перенесем, я скажу куда» (примечание про руки пока остаётся на месте).
Проверка (ru-iast и en):
  a) нет блоков list с numbers (номера 1.1)…2.5) заменены пунктами «•» = тип instruction, как в «Распорядок служения во второй половине дня»);
  b) нет ссылки «как в пункте 1.1» / «as in item 1.1»;
  c) убраны вычеркнутые слова: «Снова две молитвы, поклоны.», строка «Текст, пословный и общий перевод — как в главе «Мангалачарана Гурудева»…», метки «Когда и в каком виде.» и «Когда нельзя.» (текст после них остаётся), абзац «Тексты лекций — русская расшифровка CA…» (EN аналогично);
  d) примечание про руки ОСТАЁТСЯ; мантр по-прежнему 7.
usage: python s155_tulasi_bullets_a112g.py
"""
import json
import os
import sys

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
res = []


def check(where, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {where} {name} {'' if ok else info}".rstrip(), flush=True)


def blocks(fn):
    b = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
    s = next(s for s in b["sections"] if s["id"] == "daily-tulasi-worship")
    return [x for sub in s["subsections"] for x in sub["content"]]


GONE = {
    "book.ru-iast.json": ["Снова две молитвы, поклоны", "Текст, пословный и общий перевод", "Когда и в каком виде", "Когда нельзя", "Тексты лекций", "в пункте 1.1"],
    "book.json": ["Two prayers again, obeisances", "The text, word-for-word and general translation", "When and how", "When not to", "The lecture texts", "item 1.1"],
}
KEEP = {
    "book.ru-iast.json": ["Примечание: Туласи не кладут на стопы", "Листья собирают после омовения", "Не собирайте листья в", "Когда бхаджан допет", "пранаму Туласи — "],
    "book.json": ["Note: Tulasī is not placed on the feet", "Leaves are gathered after bathing", "Do not gather leaves on", "When the bhajana is finished", "praṇāma to Tulasī — "],
}
for fn in GONE:
    bl = blocks(fn)
    check(fn, "a нет list/numbers", not [x for x in bl if x["type"] == "list" or "numbers" in x], [x.get("numbers") for x in bl if "numbers" in x])
    allt = "\n".join(x.get("content", "") for x in bl if isinstance(x.get("content"), str))
    for g in GONE[fn]:
        check(fn, f"b/c убрано «{g}»", g not in allt)
    for k in KEEP[fn]:
        check(fn, f"d осталось «{k}»", k in allt)
    check(fn, "d мантр 7", len([x for x in bl if x["type"] == "verse"]) == 7)
print(f"{sum(res)}/{len(res)} PASS")
sys.exit(0 if all(res) else 1)
