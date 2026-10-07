# -*- coding: utf-8 -*-
"""Other-language sections made by scripts/translate/night_sync.py, used by the chapter generators.

<generator>/i18n.json = {"<section id>": {"<lang>": {"en_hash", "model", "date", "section"}}}.
put(book, lang, sid, gen_dir, en_section) puts the translated section into a book.<lang>.json (at the place given
by the English section order) or, when there is no translation yet, removes it (the app then shows English).
CLI (night run; touches only the other-language books):  python scripts/translate/i18n_sections.py <section id> ...
A translation made from an older English section is still used, but reported as STALE (re-run night_sync.py).
"""
import hashlib
import json
import os


def en_hash(sec):
    return hashlib.sha256(json.dumps(sec, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def place(book, sec, en_ids):
    """Insert/replace `sec` in book["sections"] following the English order `en_ids`."""
    secs = [s for s in book["sections"] if s["id"] != sec["id"]]
    before = en_ids[:en_ids.index(sec["id"])]
    at = 0
    for i, s in enumerate(secs):
        if s["id"] in before:
            at = i + 1
    secs.insert(at, sec)
    book["sections"] = secs


def put(book, lang, sid, gen_dir, en_section, en_ids):
    p = os.path.join(gen_dir, "i18n.json")
    rec = (json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}).get(sid, {}).get(lang)
    if not rec:
        book["sections"] = [s for s in book["sections"] if s["id"] != sid]
        return "none (English fallback)"
    place(book, rec["section"], en_ids)
    if rec["en_hash"] != en_hash(en_section):
        print("STALE %s/%s: the English section changed after the translation (%s) — run "
              "scripts/translate/night_sync.py %s --langs %s" % (lang, sid, rec["date"], sid, lang))
        return "stale"
    return "ok"


# ---------------- CLI: put the translated sections into the other-language books only ----------------
OTHER = ["lv", "de", "fr", "es", "it", "uk", "hu"]


def apply_sections(sids, gen_dirs, data_dir):
    """Write the i18n.json sections of `sids` into data/book.<lang>.json (EN/RU untouched); mood blocks already in a
    book are kept (apply_moods.py owns them). Returns {lang: {sid: status}}."""
    en_book = json.load(open(os.path.join(data_dir, "book.json"), encoding="utf-8"))
    en_ids = [s["id"] for s in en_book["sections"]]
    rep = {}
    for lang in OTHER:
        path = os.path.join(data_dir, f"book.{lang}.json")
        raw = open(path, encoding="utf-8", newline="").read()
        book = json.loads(raw)
        rep[lang] = {}
        for sid in sids:
            en_sec = next(s for s in en_book["sections"] if s["id"] == sid)
            old = next((s for s in book["sections"] if s["id"] == sid), None)
            rep[lang][sid] = put(book, lang, sid, gen_dirs[sid], en_sec, en_ids)
            new = next((s for s in book["sections"] if s["id"] == sid), None)
            if old is not None and new is not None:
                om = {n["id"]: [b for b in n["content"] if b.get("type") == "mood"] for n in [old] + old.get("subsections", [])}
                for n in [new] + new.get("subsections", []):
                    n["content"] = om.get(n["id"], []) + [b for b in n["content"] if b.get("type") != "mood"]
        nl = "\n" if raw.endswith("\n") else ""
        open(path, "w", encoding="utf-8", newline="").write(json.dumps(book, ensure_ascii=False, indent=2) + nl)
    return rep


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    from night_sync import GENERATOR, DATA  # noqa: E402
    print(json.dumps(apply_sections(sys.argv[1:], GENERATOR, DATA), ensure_ascii=False, indent=1))
