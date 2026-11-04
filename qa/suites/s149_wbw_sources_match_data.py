"""A142s (Lipikāra, Padomnieka pasts 2026.11.04): ģeneratoru avotu wbw = data wbw (ru-iast) ch16/ch17/ch99.
Стандарты 79 (burtiski): «У каждого стиха, который мы цитируем в книге (в любой главе), обязательно есть пословный перевод; … Если для стиха есть пословный перевод BBT — берём его.»
# tehniskais tests Lipikāra, nav S noteikums; sargā S noteikumu 79 labojumus (A132/A142/A142b) no pārrakstīšanas, ja kāds palaiž ch16/ch17/ch99 build.py apply.
usage: python s149_wbw_sources_match_data.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
import sync_wbw_sources as Y  # noqa: E402

r = Y.sync(write=False)
res = []
for k, label in (("ch16", "ch16 pesni_arati.json"), ("ch17", "ch17 kartika_bhajany.json"), ("ch99", "ch99 chapter_ru.md")):
    ok = r[k] == 0
    res.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}: avota wbw = data/book.ru-iast.json wbw" + ("" if ok else f" — atšķiras {r[k]}"), flush=True)
print(f"s149: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if all(res) else 1)
