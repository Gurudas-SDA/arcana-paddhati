"""The book's languages for the translation scripts — read from ONE place, lib/languages.json.

S 23.10.2026 (Padomnieks 934–941): «Оставляю два языка: английский и русский… оставить версию с IAST» —
the book is en + ru-iast only. A language with "replacedBy" in lib/languages.json is retired: the night
translations (night_sync.py, tr.py, ui_tr.py) skip it, the app does not build it. Its data files
(data/book.<lang>.json, ui.<lang>.json, generator i18n.json) are kept, so giving it back = removing
"replacedBy" there (and one translation from the finished English, as on 23.10 — «убрать, но сохранить»).

    AKTIVAS_VALODAS   codes of the book's languages, in lib/languages.json order (["en", "ru-iast"])
    IZNEMTAS          {retired code: replacement}
    IEMESLS           the reason printed when a retired language is skipped
    aktivas(langs)    the given codes without the retired ones (each skipped one reported via `log`)
"""
import json
import os

_LANGS_JSON = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib", "languages.json"))
_ALL = json.load(open(_LANGS_JSON, encoding="utf-8"))

AKTIVAS_VALODAS = [l["code"] for l in _ALL if not l.get("replacedBy")]
IZNEMTAS = {l["code"]: l["replacedBy"] for l in _ALL if l.get("replacedBy")}
IEMESLS = "S 23.10 Padomnieks 934–941: valoda izņemta"


def aktivas(langs, log=print):
    out = []
    for l in langs:
        if l in IZNEMTAS:
            log("skip %s: %s (-> %s)" % (l, IEMESLS, IZNEMTAS[l]))
        else:
            out.append(l)
    return out
