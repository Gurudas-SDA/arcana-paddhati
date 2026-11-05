"""A112c (Туласи Сундари, msg 179/181/183, 05.11.2026), раздел «Ежедневное поклонение Туласи».
Туласи Сундари (burtiski), msg 179: «Да, надо добавить пословный перевод. И всё-таки не «поднесите три предмета», а «предлагают три предмета» (по часовой стрелке)»
Туласи Сундари (burtiski), msg 181: «Пословный перевод мантрам, всем.»
Проверка:
  a) ru-iast: в «Арати» (1.3) нет «Поднесите/Подносите», есть «Предлагают три предмета» и «по часовой стрелке»;
  b) en, ru-iast: у КАЖДОЙ мантры (verse) обеих подглав есть непустой пословный перевод (wbw) и перевод;
  c) en: не заглушка («translation pending»), структура и санскрит = ru-iast; EN-текст «Three items are offered … clockwise»;
  e) Туласи Сундари msg 7670 (burtiski): «не делай пунктом 2.6, а сделай с точкой просто или как примечание» — «Куда класть…» не пункт 2.6, а «Примечание: …» (text), нумерация 2.1–2.5;
  f) Туласи Сундари msg 7671 (burtiski): «молитва Вринда Деви без ом вначале» — в tulasi-arati у «vṛndāyai tulasī-devyai…» нет «oṁ» (санскрит, wbw, ссылка в 1.4); в других главах не трогаем;
  d) санскрит в ru-iast без кириллицы с диакритикой (Стандарты «Санскрит везде пишем в IAST»).
usage: python s150_a112c_tulasi_worship.py
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


def sec(fn):
    b = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
    return next((s for s in b["sections"] if s["id"] == "daily-tulasi-worship"), None)


def blocks(s):
    return [x for sub in (s or {}).get("subsections", []) for x in sub["content"]]


S = {fn: sec(fn) for fn in ("book.json", "book.ru-iast.json")}
for fn, s in S.items():
    check(fn, "раздел daily-tulasi-worship есть, 2 подглавы", s is not None and len(s["subsections"]) == 2)
    verses = [x for x in blocks(s) if x["type"] == "verse"]
    check(fn, "b мантр: ровно 7 и у каждой есть wbw и translation", len(verses) == 7 and all((v.get("wbw") or "").strip() and (v.get("translation") or "").strip() for v in verses),
          [v["sanskrit"][:25] for v in verses if not (v.get("wbw") or "").strip()])

txt = " ".join(x.get("content", "") for x in blocks(S["book.ru-iast.json"]) if x["type"] == "list")
check("ru-iast", "a 1.3 «Предлагают три предмета … по часовой стрелке», без «Поднесите/Подносите»",
      "Предлагают три предмета" in txt and "по часовой стрелке" in txt and not re.search(r"Поднесите|Подносите", txt), txt[:300])
en = S["book.json"]
et = json.dumps(en, ensure_ascii=False)
check("en", "c не заглушка", "translation pending" not in et)
check("en", "c 1.3 «Three items are offered … clockwise»", re.search(r"Three items are offered.*clockwise", et) is not None)
ve = [x["sanskrit"] for x in blocks(en) if x["type"] == "verse"]
vr = [x["sanskrit"] for x in blocks(S["book.ru-iast.json"]) if x["type"] == "verse"]
check("en", "c санскрит = ru-iast", ve == vr, (len(ve), len(vr)))
check("en", "c типы блоков = ru-iast", [x["type"] for x in blocks(en)] == [x["type"] for x in blocks(S["book.ru-iast.json"])])
bad = [v for v in vr if re.search(r"[а-яА-ЯёЁ][̣̄̃̇́]", v)]
check("ru-iast", "d санскрит без кириллицы с диакритикой", not bad, bad)
nums = [n for x in blocks(S["book.ru-iast.json"]) if x["type"] == "list" for n in x["numbers"]]
check("ru-iast", "e нет пункта 2.6, есть 2.1–2.5", "2.6" not in nums and all(f"2.{i}" in nums for i in range(1, 6)), nums)
check("ru-iast", "e «Примечание: Туласи не кладут на стопы…»", any(x["type"] == "text" and x["content"].startswith("Примечание: Туласи не кладут на стопы") for x in blocks(S["book.ru-iast.json"])))
check("en", "e «Note: Tulasī is not placed on the feet…»", any(x["type"] == "text" and x["content"].startswith("Note: Tulasī is not placed on the feet") for x in blocks(en)))
for fn, s in S.items():
    sub = next(x for x in s["subsections"] if x["id"] == "tulasi-arati")
    vv = [x for x in sub["content"] if x["type"] == "verse" and "vṛndāyai" in x["sanskrit"]]
    ref = [x["content"] for x in sub["content"] if x["type"] == "instruction" and "vṛndāyai" in x["content"]]
    check(fn, "f vṛndāyai без «oṁ»: санскрит, wbw, ссылка в 1.4",
          len(vv) == 1 and vv[0]["sanskrit"].startswith("vṛndāyai") and not vv[0]["wbw"].startswith("oṁ") and len(ref) == 1 and "oṁ" not in ref[0], [vv and vv[0]["sanskrit"][:20], ref])
print(f"{sum(res)}/{len(res)} passed")
sys.exit(0 if res and all(res) else 1)
