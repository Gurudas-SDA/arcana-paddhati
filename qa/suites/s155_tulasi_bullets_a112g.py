"""A112g (Туласи Сундари, решает сама; Липикара msg 7688/7689, бот 192/194/204/205, 06.11.2026), раздел «Ежедневное поклонение Туласи».
Туласи Сундари (burtiski): «Изменение в разделе про Туласи: убери эти цифры 1.1) и 1.2) и тд сделай как в прошлих отделах, с точками :» / «По типу как на скрине».
Туласи Сундари: «Да. Пункт про руки перенесем, я скажу куда» (примечание про руки пока остаётся на месте).
Проверка (ru-iast и en):
  a) нет блоков list с numbers (номера 1.1)…2.5) заменены пунктами «•» = тип instruction, как в «Распорядок служения во второй половине дня»);
  b) нет ссылки «как в пункте 1.1» / «as in item 1.1»;
  c) убраны вычеркнутые слова: «Снова две молитвы, поклоны.», строка «Текст, пословный и общий перевод — как в главе «Мангалачарана Гурудева»…», метки «Когда и в каком виде.» и «Когда нельзя.» (текст после них остаётся), абзац «Тексты лекций — русская расшифровка CA…» (EN аналогично);
  e) Туласи Сундари (бот msg 211, группа 7699, burtiski): «В настроение гуру оставь только 1 и 3 цитаты» — в «Настроение Гурудева» подглавы «Сбор листьев…» (tulasi-leaves-flowers) остаются 1-я (CA:5823) и 3-я (CA:4730:3, «cannot even offer tulasī directly to Guru»), 2-й (CA:4730:2, «feet of Caitanya Mahāprabhu. But in rāgānugā-bhakti») нет; счётчик = 2 (1 + len(more)); moods.json совпадает (apply_moods не вернёт);
  f) Туласи Сундари (группа 7701, burtiski): «эта глава визуально должна выглядеть как предыдущее разделы. Я про пункты, разделения, точки перед началом и тд» — оформление только существующими типами, как «Распорядок…»/«Пробуждение Господа»: пункты = instruction («•»), подзаголовки = subtitle (разделитель сверху), таблица = paired-list, мантры = verse; свободный text — только «Примечание…» (как «(Физически поместите…)» в waking-the-lord); нет list/numbers; набор типов: 20 + 9 блоков в 3.1 (instruction 13, subtitle 2, paired-list 1, verse 4), в 3.2 (mood 1, instruction 5, verse 3, text 1);
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
MD = os.path.join(DATA, "..", "scripts", "moods", "moods.json")
mj = next(x for x in json.load(open(MD, encoding="utf-8")) if x["target"] == "tulasi-leaves-flowers")
check("moods.json", "e main CA:5823 + more = [CA:4730:3]", mj["candidate"] == "CA:5823" and [m["candidate"] for m in mj["more"]] == ["CA:4730:3"], [m["candidate"] for m in mj["more"]])
for fn in GONE:
    b = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
    sub = next(sb for s_ in b["sections"] if s_["id"] == "daily-tulasi-worship" for sb in s_["subsections"] if sb["id"] == "tulasi-leaves-flowers")
    mood = [x for x in sub["content"] if x["type"] == "mood"]
    check(fn, "e один блок «Настроение», счётчик 2 (1 + more)", len(mood) == 1 and 1 + len(mood[0].get("more", [])) == 2, [len(m.get("more", [])) for m in mood])
    if mood:
        allq = [mood[0]["quote"]] + [m["quote"] for m in mood[0].get("more", [])]
        check(fn, "e 1-я цитата (Gaurāṅga … right hand) на месте", "we worship Gaurāṅga Mahāprabhu" in allq[0])
        check(fn, "e 3-я («cannot even offer tulasī directly to Guru») на втором месте", len(allq) == 2 and "cannot even offer tulasī directly to Guru" in allq[1], allq[-1][:60])
        check(fn, "e 2-й цитаты («feet of Caitanya Mahāprabhu. But in rāgānugā-bhakti») нет", not any("But in rāgānugā-bhakti" in q for q in allq))
import collections
EXPECT = {"tulasi-arati": {"instruction": 15, "subtitle": 1, "verse": 4}  # A112h: 2 пункта→1, +3 упачары вместо таблицы, подзаголовок «Порядок проведения:» убран
          ,
          "tulasi-leaves-flowers": {"mood": 1, "instruction": 5, "verse": 3, "text": 1}}
for fn in GONE:
    b = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
    for sb in next(s_ for s_ in b["sections"] if s_["id"] == "daily-tulasi-worship")["subsections"]:
        got = dict(collections.Counter(x["type"] for x in sb["content"]))
        check(fn, f"f {sb['id']}: типы блоков как в существующих форматах, нет list", got == EXPECT[sb["id"]], got)
        free = [x["content"][:25] for x in sb["content"] if x["type"] == "text"]
        check(fn, f"f {sb['id']}: свободный text только «Примечание/Note»", all(t.startswith(("Примечание", "Note")) for t in free), free)
print(f"{sum(res)}/{len(res)} PASS")
sys.exit(0 if all(res) else 1)
