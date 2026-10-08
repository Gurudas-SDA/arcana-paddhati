# -*- coding: utf-8 -*-
"""Other-language sections made by scripts/translate/night_sync.py, used by the chapter generators.

<generator>/i18n.json = {"<section id>": {"<lang>": {"en_hash", "model", "date", "section"}}}.
put(book, lang, sid, gen_dir, en_section) puts the translated section into a book.<lang>.json (at the place given
by the English section order). No translation record: a section the book already has is KEPT (never deleted -
v7.8.3, Codex review) and reported as MISSING; a book without that section shows English (the app's fallback).
CLI (night run; touches only the other-language books):  python scripts/translate/i18n_sections.py <section id> ...
A translation made from an older English section is still used, but reported as STALE (re-run night_sync.py).
Files are written atomically (temp file + os.replace): a crash mid-write never leaves a cut-off book / cache;
a locked file (Windows / OneDrive) is retried, then AtomicWriteError is raised (v7.8.4).
"""
import hashlib
import json
import os
import tempfile
import time


class AtomicWriteError(OSError):
    """The new file was written but could not replace the old one (kept whole) - a caller must report it."""


REPLACE_TRIES = 5          # os.replace attempts (Windows / OneDrive / antivirus may hold the file a moment)
REPLACE_BACKOFF = 0.15     # seconds before the 2nd try, doubled each time (0.15 + 0.3 + 0.6 + 1.2 s)


def _replace_retry(tmp, path):
    """os.replace with a short backoff on PermissionError (v7.8.4, Codex review: Windows / OneDrive locks)."""
    wait = REPLACE_BACKOFF
    for i in range(REPLACE_TRIES):
        try:
            os.replace(tmp, path)
            return
        except PermissionError as e:
            if i == REPLACE_TRIES - 1:
                raise AtomicWriteError(
                    e.errno, "write_atomic: could not replace %s after %d tries (%.1f s) - the file is locked "
                    "(OneDrive sync / antivirus / an open editor?); the old file is unchanged, the new content "
                    "was NOT saved: %s" % (path, REPLACE_TRIES, REPLACE_BACKOFF * (2 ** (REPLACE_TRIES - 1) - 1), e),
                    path) from e
            time.sleep(wait)
            wait *= 2


def write_atomic(path, text, newline=""):
    """Write `text` to `path` through a temp file in the same folder + os.replace (all or nothing).
    A locked target (PermissionError) is retried a few times; then AtomicWriteError is raised (never silent)."""
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix="-" + os.path.basename(path), dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        _replace_retry(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


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
        if any(s["id"] == sid for s in book["sections"]):
            # never delete a localized section because its cache record is missing (the app would show English)
            print("MISSING %s/%s: no translation record in %s - the existing localized section is kept; run "
                  "scripts/translate/night_sync.py %s --langs %s" % (lang, sid, p, sid, lang))
            return "missing (existing section kept)"
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
        write_atomic(path, json.dumps(book, ensure_ascii=False, indent=2) + nl)
    return rep


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    from night_sync import GENERATOR, DATA  # noqa: E402
    print(json.dumps(apply_sections(sys.argv[1:], GENERATOR, DATA), ensure_ascii=False, indent=1))
