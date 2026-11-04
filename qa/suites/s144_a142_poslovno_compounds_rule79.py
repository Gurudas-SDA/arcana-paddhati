"""A142 (Саткирти msg 7436, 04.11: «Здесь вижу соединение 3 слов» — «Арати: Глава 14.4», пословный перевод «yogīndra-vandana … vraja-jana-bhaya-hārī … mohana-vaṁśī-bihārī»).
Стандарты 79 (burtiski): «Пословный перевод делаем по образцу BBT: «слово — простое значение», без пояснений в скобках и без «или»; длинное составное слово делим на части, у каждой своё значение, короткое оставляем целым; слова, слитые по сандхи, разделяем. Если для стиха есть пословный перевод BBT — берём его.»
Проверка (данные, без браузера) для data/book.ru-iast.json и data/book.ru.json (ru: ключи тем же iast_to_cyrillic):
 (1) ни в одном пословном переводе нет ключа из 3+ частей (2+ дефиса) — кроме одного терма-класса «priya-narma-sakhī» (оставлен целым);
 (2) старые составные ключи (по одному на каждый ранее найденный тип) не встречаются целиком;
 (3) стих Арати 14.4 разделён: vraja-jana-bhaya-hārī, mohana-vaṁśī-bihārī, nikuñja-rāsa-vilāsī -> по частям.
# tehniskais slieksnis Lipikāra, nav S noteikums: «3+ частей = 2+ дефиса»; исключения — IGNORE; имена из 2 частей (kṛṣṇa-caitanya) остаются целыми.
usage: python s144_a142_poslovno_compounds_rule79.py [data_dir]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts", "translate"))
from iast_to_cyrillic import translit  # noqa: E402

DATA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "data")
IGNORE = ["priya-narma-sakhī"]
OLD_KEYS = ["vraja-jana-bhaya-hārī", "mohana-vaṁśī-bihārī", "nikuñja-rāsa-vilāsī", "kṛpā-kaṭākṣa-bhājanam",
            "aravinda-bandhu-nandinī", "gopī-jana-vastra-hārī", "sac-cid-ānanda-vigrahaḥ", "śrī-guru-pāda-padma-nikaṭe",
            "yuga-dharma-dhurandhara-pātra-varam", "ati-komala-kāñcana-dīrgha-tanuṁ"]
NEW_PARTS = ["vraja", "jana", "bhaya", "hārī", "mohana", "vaṁśī", "bihārī", "nikuñja", "rāsa", "vilāsī"]
res = []


def chk(name, ok, ev=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} {ev if not ok else ''}".rstrip(), flush=True)


def walk(o):
    if isinstance(o, dict):
        if isinstance(o.get("wbw"), str):
            yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for x in o:
            yield from walk(x)


total = 0
for fn, cv in (("book.ru-iast.json", lambda x: x), ("book.ru.json", translit)):
    d = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
    keys = []
    for o in walk(d):
        keys += [e.partition(" — ")[0] for e in o["wbw"].rstrip(".").split("; ")]
    total += len(keys)
    ign = {cv(i) for i in IGNORE}
    bad = sorted({k for k in keys if k.count("-") >= 2 and k not in ign})
    chk(f"{fn}: нет ключей из 3+ частей (0 из {len(keys)})", not bad, f"{len(bad)}: {bad[:5]}")
    old = [k for k in OLD_KEYS if cv(k) in keys]
    chk(f"{fn}: старые составные ключи не встречаются целиком", not old, str(old))
    ks = set(keys)
    miss = [p for p in NEW_PARTS if cv(p) not in ks]
    chk(f"{fn}: части стиха Арати 14.4 есть отдельными словами", not miss, str(miss))
print(f"s144: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
