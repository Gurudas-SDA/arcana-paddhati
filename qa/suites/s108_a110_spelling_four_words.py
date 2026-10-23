"""A110 Саткирти msg 6501/6502: viśrama→viśrāma, vyajñana→vyajana, puṣpāni→puṣpāṇi, nityanandāya→nityānandāya во всех языках; источник Method of Worship 2 (Маяпур)
(OCR p051/p153 viśrāma, p160 vyajana, p144 puṣpāṇi, p156 nityānandāya). Data-only test over data/book*.json (all fields: sanskrit, wbw, label, value ...).
Per file: the old forms are absent (viśramya is another word and is NOT touched; puṣpātya not touched), the new forms occur exactly as often as the old ones did.
# tehniskais slieksnis Lipikāra, nav S noteikums: the expected counts per file are old-form counts before the fix plus forms already correct (viśrāma 4+4 / 1 / 2 / 1; ru-iast puṣpāṇi 3, nityānandāya 2).
usage: python s108_a110_spelling_four_words.py
"""
import glob
import os
import re
import sys

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
L = r"\wāīūṛṝḷṅñṭḍṇśṣḥṁ"
OLD = {w: re.compile(rf"(?<![{L}]){w}(?![{L}])") for w in ("viśrama", "vyajñana", "puṣpāni", "nityanandāya")}
NEW = {w: re.compile(rf"(?<![{L}]){w}(?![{L}])") for w in ("viśrāma", "vyajana", "puṣpāṇi", "nityānandāya")}
EXP = {"viśrāma": 8, "vyajana": 1, "puṣpāṇi": 2, "nityānandāya": 1}
EXP_IAST = {"viśrāma": 8, "vyajana": 1, "puṣpāṇi": 3, "nityānandāya": 2}
res = []


def chk(name, ok, ev=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] data {name} {ev if not ok else ''}".rstrip(), flush=True)


files = sorted(glob.glob(os.path.join(DATA, "book*.json")))
files = [f for f in files if not f.endswith("book.ru.json")]  # Cyrillic edition has no IAST words
chk("11 IAST-bearing files found", len(files) == 11, str(len(files)))
for f in files:
    t = open(f, encoding="utf-8").read()
    n = os.path.basename(f)
    for w, rx in OLD.items():
        chk(f"{n}: no «{w}»", not rx.search(t), f"{len(rx.findall(t))} left")
    exp = EXP_IAST if n == "book.ru-iast.json" else EXP
    for w, rx in NEW.items():
        c = len(rx.findall(t))
        chk(f"{n}: «{w}» ×{exp[w]}", c == exp[w], f"found {c}")
print(f"s108: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
