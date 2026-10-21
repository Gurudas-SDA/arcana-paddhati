"""V26b — the renamed «Аа» background button in every language (Vraja Lila msg 5817, 21.10.2026; saskarnes autors,
«Стандарты» 0а; V21 rename list: msg 893 «reader.bg.night -> "Тёмный"»).

Rule text (verbatim, Vraja Lila msg 5817): «во всех языках (не только английский)... так же были другие переименования,
ты их перевёл?»
Criterion (Lipikāra, Vraja's words): the third background is called «dark» in every language, as RU «Тёмный» —
never «night» (Nacht / Noche / Nuit / Éjszaka / Notte / Naktinis / Nakts / Noturno / Ніч …).
Also: every key renamed in V21 (msg 893) exists in every language and keeps its placeholders ({n}, {what}).
(EN «Dark» came with V26, 427365a; checked here too.)
usage: python s78_bg_dark_all_langs.py
"""
import json
import os
import re
import sys

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
LANGS = ["ru-iast", "ru", "en", "de", "es", "fr", "hu", "it", "lt", "lv", "pt", "uk"]
# «night» words (stems) in each language — the old label
NIGHT = re.compile(r"night|ноч|nacht|noche|nuit|éjszak|ejszak|nott|nakt|noite|notur|nočn|ніч|нічн", re.I)
V21_KEYS = ["search.noResults", "search.noSections", "part.empty", "reader.bg.night", "reader.layout.page",
            "reader.layout.scroll", "sidebar.loadFailed", "section.fallback", "offline.progress",
            "offline.save.partialWhat", "install.bannerText", "reader.prev", "reader.next"]
results = []


def check(name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] static {name} {json.dumps(evidence, ensure_ascii=False)[:500]}", flush=True)


ru = json.load(open(os.path.join(REPO, "data", "ui.ru-iast.json"), encoding="utf-8"))
for lang in LANGS:
    d = json.load(open(os.path.join(REPO, "data", f"ui.{lang}.json"), encoding="utf-8"))
    v = d.get("reader.bg.night", "")
    check(f"{lang}: reader.bg.night is «dark», not «night»", bool(v) and not NIGHT.search(v), v)
    missing = [k for k in V21_KEYS if not d.get(k)]
    ph = [k for k in V21_KEYS if d.get(k) and sorted(re.findall(r"\{\w+\}", d[k])) != sorted(re.findall(r"\{\w+\}", ru[k]))]
    check(f"{lang}: all V21 renamed keys present, placeholders as in RU", not missing and not ph, {"missing": missing, "placeholders": ph})

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
