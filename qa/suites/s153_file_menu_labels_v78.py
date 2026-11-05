"""V78 — Vraja Lila msg 7621–7623 (Vraja Lila is responsible for the interface: her words are the decision).
Her words, literally: «давай уберём функцию copy as text из заметок, она лишняя»;
«так же в написании нужно синхронизировать названия функций: Download bookmarks или notes; Load from a file — в обоих разделах;
так же синхронизируй в русском переводе».
Criteria (register V78):
 (1) the notes file menu has no «Copy as text» («Скопировать текстом» in RU) — no button, no handler, no unused i18n key;
 (2) EN: Bookmarks = «Download bookmarks» + «Load from a file»; Notes = «Download notes» + «Load from a file»;
 (3) RU (ru and ru-iast): «Скачать закладки» / «Скачать заметки» and «Загрузить из файла» in both sections.
Other languages have none of these keys (they fall back to English via lib/ui-en-fallback.json) — nothing to synchronise there.
usage: python s153_file_menu_labels_v78.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402

res = []


def chk(name, ok, ev=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} {ev if not ok else ''}".rstrip(), flush=True)


def load(rel):
    return json.load(open(os.path.join(qa.REPO, rel), encoding="utf-8"))


EXPECT = {
    "en": ("Download bookmarks", "Download notes", "Load from a file"),
    "ru": ("Скачать закладки", "Скачать заметки", "Загрузить из файла"),
    "ru-iast": ("Скачать закладки", "Скачать заметки", "Загрузить из файла"),
}
for lang, (bm, nt, ld) in EXPECT.items():
    d = load(f"data/ui.{lang}.json")
    chk(f"{lang} bookmarks.save = «{bm}»", d.get("bookmarks.save") == bm, d.get("bookmarks.save"))
    chk(f"{lang} notes.save = «{nt}»", d.get("notes.save") == nt, d.get("notes.save"))
    chk(f"{lang} bookmarks.load = «{ld}»", d.get("bookmarks.load") == ld, d.get("bookmarks.load"))
    chk(f"{lang} notes.load = «{ld}»", d.get("notes.load") == ld, d.get("notes.load"))
    chk(f"{lang} no notes.copyText key", "notes.copyText" not in d, d.get("notes.copyText"))

# no other language carries the removed key
for fn in sorted(os.listdir(os.path.join(qa.REPO, "data"))):
    if fn.startswith("ui.") and fn.endswith(".json"):
        d = load(f"data/{fn}")
        if "notes.copyText" in d:
            chk(f"{fn} no notes.copyText key", False, d["notes.copyText"])
fb = load("lib/ui-en-fallback.json")
chk("ui-en-fallback has no notes.copyText", "notes.copyText" not in fb.get("keys", []))

src = open(os.path.join(qa.REPO, "components", "Sidebar.tsx"), encoding="utf-8").read()
chk("Sidebar: no data-notes-copytext button", "data-notes-copytext" not in src)
chk("Sidebar: no notes.copyText use", "notes.copyText" not in src)
chk("Sidebar: no copyNotesText handler (unused code removed)", "copyNotesText" not in src)
chk("Sidebar: no asText import (unused after removal)", "asText" not in src)

print(f"s153: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
