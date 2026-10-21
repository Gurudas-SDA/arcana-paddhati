"""EN theme label (Vraja Lila msg 5780, 21.10.2026): the dark reading background is «Тёмный» in Russian, so in English
it is «Dark», not «Night» — in the «Аа» panel and anywhere else the English interface names that background.
Other languages are not touched here (they follow in the night release).
usage: python s70_en_theme_label.py
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402

res = []


def chk(name, ok, ev=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] data {name} {ev if not ok else ''}".rstrip(), flush=True)


en = json.load(open(os.path.join(qa.REPO, "data", "ui.en.json"), encoding="utf-8"))
ru = json.load(open(os.path.join(qa.REPO, "data", "ui.ru-iast.json"), encoding="utf-8"))
chk("RU reader.bg.night = «Тёмный»", ru.get("reader.bg.night") == "Тёмный", ru.get("reader.bg.night"))
chk("EN reader.bg.night = «Dark»", en.get("reader.bg.night") == "Dark", en.get("reader.bg.night"))
night = {k: v for k, v in en.items() if isinstance(v, str) and re.search(r"\bnight\b", v, re.I)}
chk("EN interface: no «Night» for the dark background anywhere (labels, aria, titles)", not night, night)
print(f"s70: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
