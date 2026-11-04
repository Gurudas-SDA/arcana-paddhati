"""A142b (Padomnieka pasts 2026.11.04_0405, S «Да» msg 1322; S 7436/7438): noteikuma 79 VISU daļu pārbaude visā grāmatā.
Стандарты 79 (burtiski): «У каждого стиха, который мы цитируем в книге (в любой главе), обязательно есть пословный перевод; в приложении он открывается кнопкой «пословно». Пословный перевод делаем по образцу BBT: «слово — простое значение», без пояснений в скобках и без «или»; длинное составное слово делим на части, у каждой своё значение, короткое оставляем целым; слова, слитые по сандхи, разделяем. Если для стиха есть пословный перевод BBT — берём его. Исключение — короткие мантры (правило 178): пословный перевод есть в данных, кнопки нет.»
Pārbaudes (deterministiskas, data/book.ru-iast.json + data/book.ru.json): qa/rule79_check.py daļas D1–D7.
# tehniskais slieksnis Lipikāra, nav S noteikums: «garš» = 3+ daļas; daudzvārdu atslēgas (hindi pēcvārdi) netiek skaitītas — sk. mantri_a142b_status.txt.
usage: python s145_a142b_rule79_all_parts.py [data_dir]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import rule79_check as R  # noqa: E402
from iast_to_cyrillic import translit  # noqa: E402

DATA = sys.argv[1] if len(sys.argv) > 1 else R.DATA_DEFAULT
res = []


def chk(name, ok, ev=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} {ev if not ok else ''}".rstrip(), flush=True)


for fn in R.BOOKS:
    d = R.load(DATA, fn)
    cv = (lambda x: x) if fn == "book.ru-iast.json" else translit
    r = R.check_book(d, cv, fn)
    chk(f"{fn} D1 katram pantam/mantrai ir wbw ({r['D1']['checked']})", not r["D1"]["bad"], str(r["D1"]["bad"][:3]))
    chk(f"{fn} D2 poga: kods SectionContent + dati ({r['D2']['checked']})", not r["D2"]["bad"], str(r["D2"]["bad"][:3]))
    d3 = [x for x in r["D3"]["bad"] if not x.startswith("daudzvārdu")]
    chk(f"{fn} D3 formāts «слово — значение» ({r['D3']['checked']})", not d3, str(d3[:3]))
    chk(f"{fn} D4 bez iekavām ({r['D4']['checked']})", not r["D4"]["bad"], str(r["D4"]["bad"][:3]))
    chk(f"{fn} D5 bez «или» ({r['D5']['checked']})", not r["D5"]["bad"], str(r["D5"]["bad"][:3]))
    chk(f"{fn} D6 nav 3+ daļu salikteņu ({r['D6']['checked']})", not r["D6"]["bad"], str(r["D6"]["bad"][:3]))
    chk(f"{fn} D7 sandhi/slēptie salikteņi dalīti ({r['D7']['checked']})", not r["D7"]["bad"], str(r["D7"]["bad"][:3]))
    chk(f"{fn} D8 BBT pantiem wbw = BBT RU burtiski, noteikums 79 ({r['D8']['checked']} vietas; D3–D7 šos pantus izslēdz: BBT, noteikums 79)", r["D8"]["checked"] > 0 and not r["D8"]["bad"], str(r["D8"]["bad"][:3]))
print(f"s145: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
