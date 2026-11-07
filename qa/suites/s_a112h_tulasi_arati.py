"""A112h (Туласи Сундари, решает сама; Липикара, бот msg 236/238/240/242/244, 07.11.2026), «Ежедневное поклонение Туласи» → «Туласи-арати».
Туласи Сундари (burtiski): «Также надо поменять подачу и текст: добавь время начала 5:20, объединить два первых пункта, убрать что зачёркнуто.» (236)
«Убери зачёркнутое. Также «Арати проводят», а не тире» (240)
«Мы используем слова «упачары» и названия предметов на санскрите» (242)
«Также предметы и количество кругов пиши не таблицей, а как обычно, в ряд» (244)
Проверка (ru-iast и en):
  a) первый пункт объединён и со временем 5:20, после мангала-арати;
  b) нет подзаголовка «Порядок проведения:», слов «Пранама.», «Бхаджан и парикрама.», «Пойте и», тире «Арати — …», предложения «Предлагают три предмета…»;
  c) «Прочитайте молитву Вринде-деви…», «Начните бхаджан», «Обходите вокруг Туласи не менее четырёх раз.», «Арати проводят одновременно с парикрамой.»;
  d) нет таблицы (paired-list) в tulasi-arati; подзаголовок со словом «упачары»; три пункта: дхупа / дипа / пушпа с числами 7; 4-2-3-7; 3 и «затем Гуру и всем преданным»;
  f) Туласи msg 249: «После бхаджана прочитайте молитвы и поклонитесь:» вместо «Когда бхаджан допет, одновременно прочитайте обе молитвы…», подпункты остаются;
  g) Туласи msg 251/253: «Затем, орошая Туласи-деви водой из панча-патры, пойте:» вместо пункта «Полив. Гурудев или другой преданный…»; пант полива остаётся;
  e) мантр по-прежнему 7 в разделе; санскрит в ru-iast без кириллицы с диакритикой.
usage: python s_a112h_tulasi_arati.py
"""
import json
import os
import re
import sys

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
res = []


def check(where, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {where} {name} {'' if ok else info}".rstrip(), flush=True)


def sub(fn):
    b = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
    s = next(s for s in b["sections"] if s["id"] == "daily-tulasi-worship")
    return s, next(x for x in s["subsections"] if x["id"] == "tulasi-arati")


RU = {
    "have": ["Туласи-арати проводят в 5:20 утра, после мангала-арати. Поклоняться Туласи, как и Божествам, можно только в чистой одежде.",
             "Прочитайте молитву Вринде-деви и сделайте поклоны:", "Начните бхаджан «Джая Радхе",
             "Обходите вокруг Туласи не менее четырёх раз.", "Арати проводят одновременно с парикрамой.",
             "⟦дхупа⟧, благовония: 7 кругов вокруг всего дерева, затем Гуру и всем преданным",
             "⟦дипа⟧, лампада (фитилёк): корням (стопам) — 4 круга, стволу — 2, верхушке — 3, всему дереву — 7; затем Гуру и всем преданным",
             "⟦пушпа⟧, цветок: 3 круга вокруг всего дерева, затем Гуру и всем преданным",
             "После бхаджана прочитайте молитвы и поклонитесь:", "молитву вайшнавам:", "пранаму Туласи — ", "Затем, орошая Туласи-деви водой из ⟦панча-патры⟧, пойте:"],
    "gone": ["Порядок проведения", "Пранама.", "Бхаджан и парикрама", "Пойте и", "Арати — одновременно", "Предлагают три предмета", "Предметы арати", "Когда бхаджан допет", "обе молитвы", "Полив.", "Гурудев или другой преданный"],
    "sub": "Упачары арати",
}
EN = {
    "have": ["Tulasī-ārati is performed at 5:20 a.m., after maṅgala-ārati. Worship of Tulasī, as of the Deities, may be performed only in clean clothes.",
             "Recite the prayer to Vṛndā-devī and offer obeisances:", "Begin the bhajana “Jaya Rādhe",
             "Circumambulate Tulasī at least four times.", "Ārati is performed simultaneously with the parikramā.",
             "⟦dhūpa⟧, incense: 7 circles around the whole tree, then to Guru and all the devotees",
             "⟦dīpa⟧, lamp (wick): to the roots (feet) — 4 circles, trunk — 2, top — 3, whole tree — 7; then to Guru and all the devotees",
             "⟦puṣpa⟧, flower: 3 circles around the whole tree, then to Guru and all the devotees",
             "After the bhajana, recite the prayers and offer obeisances:", "prayer to the Vaiṣṇavas:", "praṇāma to Tulasī — ", "Then, sprinkling Tulasī-devī with water from the ⟦pañca-pātra⟧, sing:"],
    "gone": ["Order of the procedure", "Praṇāma. Recite", "Bhajana and parikramā", "Sing and circumambulate", "Ārati — simultaneously", "Three items are offered", "Items of ārati", "When the bhajana is finished", "both prayers", "Watering.", "Gurudeva or another devotee"],
    "sub": "Upacāras of ārati",
}
for fn, T in (("book.ru-iast.json", RU), ("book.json", EN)):
    s, sb = sub(fn)
    c = sb["content"]
    txt = [x.get("content", "") for x in c if isinstance(x.get("content"), str)]
    allt = "\n".join(txt)
    for h in T["have"]:
        check(fn, f"a/c/d есть «{h[:45]}»", h in allt)
    for g in T["gone"]:
        check(fn, f"b нет «{g}»", g not in allt)
    check(fn, "d нет таблицы paired-list", not [x for x in c if x["type"] == "paired-list"])
    check(fn, f"d подзаголовок «{T['sub']}…»", any(x["type"] == "subtitle" and x["content"].startswith(T["sub"]) for x in c))
    check(fn, "e мантр 7 в разделе", len([x for sb2 in s["subsections"] for x in sb2["content"] if x["type"] == "verse"]) == 7)
    if fn == "book.ru-iast.json":
        bad = re.findall(r"[а-яА-ЯёЁ][̣̄̃̇́]", json.dumps(sb, ensure_ascii=False))
        check(fn, "e нет кириллицы с диакритикой", not bad, bad)
    else:
        check(fn, "e в EN нет кириллицы", not re.search(r"[а-яА-ЯёЁ]", json.dumps(sb, ensure_ascii=False)))
print(f"{sum(res)}/{len(res)} PASS")
sys.exit(0 if all(res) else 1)
