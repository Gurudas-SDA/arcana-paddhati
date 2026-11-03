"""A140 — Satkirti msg 7403 (03.11.2026), A133 answer: «Убрать».
Rule text (literally): «S msg 7403 03.11: А133 — две лишние шлоки в пранаме Бхактипрагьяне Кешаве Госвами — „Убрать“».
In «Мангалачарана» the pranama to Bhaktiprajñāna Keśava Gosvāmī has two verses the Russian songbook
(«Песенник гаудия-вайшнава», Воронеж 2015) does not have:
  gaurāśraya-vigrahāya kṛṣṇa-kāmaika-cāriṇe / rūpānuga-pravarāya vinodeti-svarūpiṇe
  prabhupādāntaraṅgāya sarva-sad-guṇa-śāline / māyāvāda-tamo-ghnāya vedāntārtha-vāde namaḥ
Criteria (S words):
 (1) both verses (with translation and word-for-word) are gone from «Мангалачарана» in EVERY book data file
     (en, ru, ru-iast and the 9 other languages) and from every other data file;
 (2) the verses 9–10 (nama oṁ viṣṇu-pādāya ācārya-siṁha-rūpiṇe…, atimartya-caritrāya…) and the rest stay.
Data test, no browser: python s142_mangalacarana_two_slokas_removed.py [base-url ignored]
"""
import glob
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "data"))
GONE = ["gaurāśraya-vigrahāya", "prabhupādāntaraṅgāya", "kṛṣṇa-kāmaika-cāriṇe", "māyāvāda-tamo-ghnāya"]
GONE_CYR = ["гаура̄ш́райа-виграха̄йа", "прабхупа̄да̄нтаран̇га̄йа"]
KEEP = ["nama oṁ viṣṇu-pādāya ācārya-siṁha-rūpiṇe", "atimartya-caritrāya svāśritānāṁ ca pāline"]
KEEP_CYR = ["нама ом̇ виш̣н̣у-па̄да̄йа а̄ча̄рйа", "атимартйа-чаритра̄йа"]
results = []


def nfc(s):
    return unicodedata.normalize("NFC", s)


def check(name, ok, ev=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} {'' if ok else ev}", flush=True)


files = sorted(glob.glob(os.path.join(DATA, "*.json")))
for f in files:
    raw = nfc(open(f, encoding="utf-8").read())
    hits = [g for g in GONE + GONE_CYR if nfc(g) in raw]
    check(f"{os.path.basename(f)}: the two verses absent", not hits, hits)
for f in sorted(glob.glob(os.path.join(DATA, "book*.json"))):
    raw = nfc(open(f, encoding="utf-8").read())
    keep = KEEP_CYR if os.path.basename(f) == "book.ru.json" else KEEP
    miss = [k for k in keep if nfc(k) not in raw]
    check(f"{os.path.basename(f)}: verses 9-10 kept", not miss, miss)
    d = json.load(open(f, encoding="utf-8"))
    sec = d["sections"][3]
    verses = [c for c in sec["content"] if c.get("type") == "verse"]
    check(f"{os.path.basename(f)}: mangalacarana verses 9-10 sit consecutively before the Prabhupada ornament",
          any(c.get("type") == "verse" for c in sec["content"][13:15]) and sec["content"][15].get("type") == "ornament",
          [c.get("type") for c in sec["content"][12:18]])
print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
