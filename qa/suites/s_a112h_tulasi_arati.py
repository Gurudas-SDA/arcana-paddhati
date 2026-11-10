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
  h) Туласи msg 255/257: «Сделайте поклон и прочитайте завершающую молитву:» вместо «Затем сделайте поклон.» + «Заключительная молитва. Гурудев или другой преданный читает:»; пант bhaktyā vihīnā… и «На этом арати Туласи завершается.» остаются;
  i) msg 259/265/267: 3.2 примечание «листья Туласи… Их кладут»; 3.1 три пункта → «Во время арати поётся бхаджан… Обходить Туласи необходимо минимум 4 раза.» (скобка убрана «Арати проводят одновременно с парикрамой»); 3.1/3.2 — стиль как в главах 1, 2, 4: повелительное, без меток «Если омовения не было.», подзаголовок без «:»;
  j) msg 7813: «Во время арати поётся…» остаётся; подпункты остаются; в примечании 3.2 выделены ⟦Шри Гуру⟧ и ⟦Шри Гауранги⟧ (как в главах 1, 2, 4; Шримати Радхарани там не выделяется); «На этом арати Туласи завершается.» / «This completes Tulasī-ārati.» убрано;
  k) msg 7814: подпункты — полные предложения: «Прочитайте пранаму Туласи — …», «Прочитайте молитву вайшнавам:» (EN «Recite the praṇāma to Tulasī — …», «Recite the prayer to the Vaiṣṇavas:»);
  l) msg 7815: в примечании 3.2 выделено и ⟦Шримати Радхарани⟧ (⟦Śrīmatī Rādhārāṇī⟧);
  m) A112k, Туласи msg 7846 (фото) + 7851 «Лампада»: в «Упачарах арати» без «Предложите / Прочитайте»: «Дхупа, благовония: …», «Дипа, лампада (фитилёк): …», «Пушпа, цветок: …», «Пранама Туласи — …», «Молитва вайшнавам:» (EN: «Dhūpa, incense: …», «Dīpa, lamp (wick): …», «Puṣpa, flower: …», «Praṇāma to Tulasī — …», «Prayer to the Vaiṣṇavas:»);
  n) A112l, Туласи msg 7847–7850: в «Настроение Гурудева» добавлены CA 7603 (02:35:58), CA 895 (01:08:26), CA 3332 (00:09:46); RU-перевод из файла «А112j Цитаты Гурудева…» буквально; всего не больше 6 (L13), главная цитата не тронута;
  o) A112m, Tulasi Sundari msg 313, 09.11: в сборе листьев 2 цитаты (как до A112l), в Туласи-арати три новые (CA 7603, 895, 3332);
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


BHA_RU = "Во время арати поётся бхаджан «Джая Радхе, джая Кришна, джая Вриндавана» («Шри Враджа-дхама-махимамрита»; текст — в разделе «Арати», глава «Мангала-арати»). Обходить Туласи необходимо минимум 4 раза."
RU = {
    "have": ["Туласи-арати проводят в 5:20 утра, после мангала-арати. Поклоняться Туласи, как и Божествам, можно только в чистой одежде.",
             "Прочитайте молитву Вринде-деви и сделайте поклоны:", BHA_RU,
             "⟦Дхупа⟧, благовония: 7 кругов вокруг всего дерева, затем Гуру и всем преданным.",
             "⟦Дипа⟧, лампада (фитилёк): корням (стопам) — 4 круга, стволу — 2, верхушке — 3, всему дереву — 7; затем Гуру и всем преданным.",
             "⟦Пушпа⟧, цветок: 3 круга вокруг всего дерева, затем Гуру и всем преданным.",
             "После бхаджана прочитайте молитвы и поклонитесь:", "Пранама Туласи — ⟦vṛndāyai tulasī-devyai…⟧.", "Молитва вайшнавам:",
             "Затем, орошая Туласи-деви водой из ⟦панча-патры⟧, пойте:", "Сделайте поклон и прочитайте завершающую молитву:",
             # msg 267 — стиль как в главах 1, 2, 4; A112n (Tulasi группа 7975-7977, бот 316/318) — 4 пункта сбора в её форме
             "Собирать листья можно после омовения и в чистой одежде.",
             "Если омовения не было, совершите ⟦манаса-снану⟧ (омовение в уме) и идите собирать Туласи с этим настроением:",
             "Перед тем как начать срывать листья, необходимо прочитать ⟦чаяна-мантру⟧:",
             "После сбора необходимо прочитать мантру с просьбой о прощении (⟦апарадха-кшама-прартхана⟧):",
             "Примечание: листья Туласи не кладут на стопы ⟦Шримати Радхарани⟧, ⟦Шри Гуру⟧ и ⟦Шри Гауранги⟧. Их кладут в правую руку."],
    "gone": ["Порядок проведения", "Пранама.", "Бхаджан и парикрама", "Пойте и", "Арати — одновременно", "Предлагают три предмета", "Предметы арати", "Когда бхаджан допет", "обе молитвы", "Полив.", "Гурудев или другой преданный поливает Туласи", "\nпранаму Туласи — ", "\nмолитву вайшнавам:", "Затем сделайте поклон", "Заключительная молитва",
             "Начните бхаджан", "Обходите вокруг", "Арати проводят одновременно", "Листья собирают", "Если омовения не было.", "Перед срыванием.", "После сбора.", "Примечание: Туласи не кладут", "Её кладут", "На этом арати Туласи завершается",
             "Предложите", "Прочитайте пранаму", "Прочитайте молитву вайшнавам", "лампаду"],
    "sub": "Упачары арати",
}
BHA_EN = "During ārati, the bhajana “Jaya Rādhe, jaya Kṛṣṇa, jaya Vṛndāvana” (“Śrī Vraja-dhāma-mahimāmṛta”; the text is in the section “Ārati”, chapter “Maṅgala-ārati”) is sung. Tulasī must be circumambulated at least 4 times."
EN = {
    "have": ["Tulasī-ārati is performed at 5:20 a.m., after maṅgala-ārati. Worship of Tulasī, as of the Deities, may be performed only in clean clothes.",
             "Recite the prayer to Vṛndā-devī and offer obeisances:", BHA_EN,
             "⟦Dhūpa⟧, incense: 7 circles around the whole tree, then to Guru and all the devotees.",
             "⟦Dīpa⟧, lamp (wick): to the roots (feet) — 4 circles, trunk — 2, top — 3, whole tree — 7; then to Guru and all the devotees.",
             "⟦Puṣpa⟧, flower: 3 circles around the whole tree, then to Guru and all the devotees.",
             "After the bhajana, recite the prayers and offer obeisances:", "Praṇāma to Tulasī — ⟦vṛndāyai tulasī-devyai…⟧.", "Prayer to the Vaiṣṇavas:",
             "Then, sprinkling Tulasī-devī with water from the ⟦pañca-pātra⟧, sing:", "Offer obeisances and recite the concluding prayer:",
             "Gather leaves after bathing and in clean clothes.",
             "If one has not bathed, perform ⟦mānasa-snāna⟧ (bathing in the mind) and go to gather Tulasī in this mood:",
             "Before picking, recite the ⟦cayana-mantra⟧ (the mantra for gathering leaves):",
             "After gathering, recite the mantra begging forgiveness (⟦aparādha-kṣamā-prārthanā⟧):",
             "Note: Tulasī leaves are not placed on the feet of ⟦Śrīmatī Rādhārāṇī⟧, ⟦Śrī Guru⟧ and ⟦Śrī Gaurāṅga⟧. They are placed in the right hand."],
    "gone": ["Order of the procedure", "Praṇāma. Recite", "Bhajana and parikramā", "Sing and circumambulate", "Ārati — simultaneously", "Three items are offered", "Items of ārati", "When the bhajana is finished", "both prayers", "Watering.", "Gurudeva or another devotee waters Tulasī", "\npraṇāma to Tulasī — ", "\nprayer to the Vaiṣṇavas:", "Then offer obeisances", "Closing prayer",
             "Begin the bhajana", "Circumambulate Tulasī at least", "Ārati is performed simultaneously", "Leaves are gathered", "If one has not bathed.", "Before picking.", "After gathering.", "Note: Tulasī is not placed", "She is placed", "This completes Tulasī-ārati",
             "Offer ⟦", "Recite the praṇāma", "Recite the prayer to the Vaiṣṇavas", "a lamp (wick)"],
    "sub": "Upacāras of ārati",
}
for fn, T in (("book.ru-iast.json", RU), ("book.json", EN)):
    s, sb = sub(fn)
    c = sb["content"]
    txt = [x.get("content", "") for sb2 in s["subsections"] for x in sb2["content"] if isinstance(x.get("content"), str)]  # 3.1 + 3.2
    allt = "\n".join(txt)
    for h in T["have"]:
        check(fn, f"a/c/d есть «{h[:45]}»", h in allt)
    for g in T["gone"]:
        check(fn, f"b нет «{g}»", g not in allt)
    check(fn, "d подзаголовок без двоеточия (стиль глав 1, 2, 4)", not any(x["type"] == "subtitle" and x["content"].endswith(":") for x in c))
    check(fn, "d нет таблицы paired-list", not [x for x in c if x["type"] == "paired-list"])
    check(fn, f"d подзаголовок «{T['sub']}…»", any(x["type"] == "subtitle" and x["content"].startswith(T["sub"]) for x in c))
    check(fn, "e мантр 7 в разделе", len([x for sb2 in s["subsections"] for x in sb2["content"] if x["type"] == "verse"]) == 7)
    if fn == "book.ru-iast.json":
        bad = re.findall(r"[а-яА-ЯёЁ][̣̄̃̇́]", json.dumps(sb, ensure_ascii=False))
        check(fn, "e нет кириллицы с диакритикой", not bad, bad)
    else:
        check(fn, "e в EN нет кириллицы", not re.search(r"[а-яА-ЯёЁ]", json.dumps(sb, ensure_ascii=False)))
# n) A112l: цитаты в «Настроении Гурудева»
NEW = {"7603": ("02:35:58", "Поэтому, если кто-то будет почитать Вринду Деви и предлагать ее листья", "с этой абхиманой, с этой концепцией.", "So if anyone will honor Vṛndā Devī", "with that abhimāna, with that conception."),
       "895": ("01:08:26", "Поэтому в следующий раз, увидев Туласи", "в красном платье бандхука, о, и с множеством украшений.", "So next time you see Tulasī", "red bandhuka dress, oh, and many ornaments is standing there."),
       "3332": ("00:09:46", "Так что служение Туласи в своей жизни", "всё это анукула для бхакти.", "So serving Tulasī in your life", "this is all anukūla for bhakti.")}
# A112m (Tulasi Sundari msg 313, 09.11): три новые цитаты — в «Туласи-арати», в «Сборе листьев» осталось 2
for fn in ("book.ru-iast.json", "book.json"):
    s, ar = sub(fn)
    lf = next(x for x in s["subsections"] if x["id"] == "tulasi-leaves-flowers")
    ml = next(x for x in lf["content"] if x["type"] == "mood")
    check(fn, "n главная цитата «…we worship Gaurāṅga Mahāprabhu» на месте в «Сборе листьев», всего 2", ml["source"]["nr"] == "5823" and ml["quote"].startswith("…we worship Gaurāṅga") and 1 + len(ml.get("more") or []) == 2)
    check(fn, "n в «Сборе листьев» нет CA 7603/895/3332", not any(x["source"].get("nr") in NEW for x in [ml] + (ml.get("more") or [])))
    ms = [x for x in ar["content"] if x["type"] == "mood"]
    check(fn, "n в «Туласи-арати» один блок «Настроение», 3 цитаты (L13 ≤ 6)", len(ms) == 1 and 1 + len(ms[0].get("more") or []) == 3)
    allq = [ms[0]] + (ms[0].get("more") or []) if ms else []
    for nr, (tc, ru0, ru1, en0, en1) in NEW.items():
        q = next((x for x in allq if x["source"].get("nr") == nr), None)
        check(fn, f"n CA {nr} есть в «Настроении Гурудева» «Туласи-арати»", q is not None)
        if q is None:
            continue
        check(fn, f"n CA {nr} тайм-код {tc}, ссылка на расшифровку", q["source"].get("timecode") == tc and q["source"].get("transcript_url", "").startswith("https://drive.google.com/file/d/") and q["source"].get("date"))
        check(fn, f"n CA {nr} EN-цитата буквально", q["quote"].startswith(en0) and q["quote"].endswith(en1), q["quote"][-50:])
        if fn == "book.ru-iast.json":
            check(fn, f"n CA {nr} RU-перевод буквально", q["translation"].startswith(ru0) and q["translation"].endswith(ru1), q["translation"][-50:])
print(f"{sum(res)}/{len(res)} PASS")
sys.exit(0 if all(res) else 1)
