"""A142c (Satkirti msg 7484 «Так этот вопрос закрыт на 2 языка или нет» → L 7485: angļu versiju darām pēc tā paša noteikuma 79): noteikuma 79 VISAS daļas angļu grāmatā (data/book.json).
Стандарты 79 (burtiski): «У каждого стиха, который мы цитируем в книге (в любой главе), обязательно есть пословный перевод; в приложении он открывается кнопкой «пословно». Пословный перевод делаем по образцу BBT: «слово — простое значение», без пояснений в скобках и без «или»; длинное составное слово делим на части, у каждой своё значение, короткое оставляем целым; слова, слитые по сандхи, разделяем. Если для стиха есть пословный перевод BBT — берём его. Исключение — короткие мантры (правило 178): пословный перевод есть в данных, кнопки нет.»
EN: «или» = «or»; D8 = BBT EN «Synonyms» (vedabase.io/en) burtiski. Pārbaudes: qa/rule79_check.py D1–D8 uz book.json.
# tehniskais slieksnis Lipikāra, nav S noteikums: «garš» = 3+ daļas; daudzvārdu atslēgas (87, hindi pēcvārdi) netiek skaitītas — sk. mantri_a142c_status.txt.
usage: python s148_a142c_rule79_en.py [data_dir]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import rule79_check as R  # noqa: E402

DATA = sys.argv[1] if len(sys.argv) > 1 else R.DATA_DEFAULT
res = []


def chk(name, ok, ev=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} {ev if not ok else ''}".rstrip(), flush=True)


fn = R.EN_BOOK
d = R.load(DATA, fn)
r = R.check_book(d, lambda x: x, fn)
chk(f"{fn} D1 katram pantam/mantrai ir wbw ({r['D1']['checked']})", not r["D1"]["bad"], f"{len(r['D1']['bad'])}: {r['D1']['bad'][:3]}")
chk(f"{fn} D2 poga: kods SectionContent + dati ({r['D2']['checked']})", not r["D2"]["bad"], str(r["D2"]["bad"][:3]))
d3 = [x for x in r["D3"]["bad"] if not x.startswith("daudzvārdu")]
chk(f"{fn} D3 formāts «word — meaning» ({r['D3']['checked']})", not d3, f"{len(d3)}: {d3[:3]}")
chk(f"{fn} D4 bez iekavām ({r['D4']['checked']})", not r["D4"]["bad"], f"{len(r['D4']['bad'])}: {r['D4']['bad'][:3]}")
chk(f"{fn} D5 bez «or» ({r['D5']['checked']})", not r["D5"]["bad"], f"{len(r['D5']['bad'])}: {r['D5']['bad'][:3]}")
chk(f"{fn} D6 nav 3+ daļu salikteņu ({r['D6']['checked']})", not r["D6"]["bad"], f"{len(r['D6']['bad'])}: {r['D6']['bad'][:3]}")
chk(f"{fn} D7 sandhi/slēptie salikteņi dalīti ({r['D7']['checked']})", not r["D7"]["bad"], f"{len(r['D7']['bad'])}: {r['D7']['bad'][:3]}")
chk(f"{fn} D8 BBT pantiem wbw = BBT EN burtiski, noteikums 79 ({r['D8']['checked']} vietas)", r["D8"]["checked"] > 0 and not r["D8"]["bad"], f"{len(r['D8']['bad'])}: {r['D8']['bad'][:3]}")
print(f"s148: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
