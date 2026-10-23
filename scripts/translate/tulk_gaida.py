# -*- coding: utf-8 -*-
"""«Tulkojums gaida» — sections / Gurudev quotes not yet translated into a language (Gurudas 23.10 msg 868: «Tulkojumu
trūkums netraucē turpināt darbu pie pašas grāmatas»). A failed night_sync.py no longer stops a release: the untranslated
(language, section) pairs are written to qa/tulkojumi_gaida.json, the book shows them in English until translated,
and qa/lint_content.py accepts that English fallback ONLY for the listed pairs (and lists them).
# tehniskais slieksnis Lipikāra, nav S noteikums; Gurudas msg 868

  python scripts/translate/tulk_gaida.py compute <section-id> ... [--moods <section-id> ...] [--copy <state.json>]
      -> qa/tulkojumi_gaida.json = {"updated", "pending": [{"lang", "section", "kind": "section"|"moods", "gen"}]}
         section = no i18n.json record made from the CURRENT English section (missing or STALE);
         moods   = a Gurudev quote (main or «more») of that section without a translation into the language.
  python scripts/translate/tulk_gaida.py snapshot <file>      (BEFORE the apply scripts)
      -> saves the current localized sections of every pending "section" pair (the previous version in the book)
  python scripts/translate/tulk_gaida.py fallback [--snapshot <file>]   (AFTER i18n_sections.py / build.py apply)
      -> for every pending "section" pair: a section that is a real translation in the snapshot is put back exactly as it
         was (the apply scripts would put a STALE i18n.json record over it, e.g. an older title); a section that is an
         English copy (or missing) becomes the CURRENT English section; then every English subsection the localized
         section lacks is inserted in English at its English place (e.g. the new 11th subsection of «Заключение»).
         Mood blocks are left out of English copies (apply_moods.py owns them; re-run it after this).
  python scripts/translate/tulk_gaida.py show
"""
import copy
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(REPO, "data")
LIST = os.path.join(REPO, "qa", "tulkojumi_gaida.json")
LANGS = ["lv", "de", "fr", "es", "it", "uk", "hu", "pt", "lt"]
MOODS = os.path.join(REPO, "scripts", "moods", "moods.json")
sys.path.insert(0, HERE)
from i18n_sections import en_hash, place, write_atomic  # noqa: E402

# the same map as night_sync.GENERATOR (night_sync is not imported: it reads the API keys at import)
GEN = {
    "conclusion": "scripts/chapters/ch99_conclusion",
    "upadesha-sara": "scripts/chapters/ch00a_front",
    "jaya-dhvani-front": "scripts/chapters/ch00a_front",
}


def load_list():
    if not os.path.exists(LIST):
        return {"updated": None, "pending": []}
    return json.load(open(LIST, encoding="utf-8"))


def pending_pairs():
    """{(lang, top-level section id)} of the list (both kinds)."""
    return {(p["lang"], p["section"]) for p in load_list().get("pending", [])}


def _en():
    return json.load(open(os.path.join(DATA, "book.json"), encoding="utf-8"))


def section_pending(sid, lang, en_secs):
    p = os.path.join(REPO, GEN[sid], "i18n.json")
    rec = (json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}).get(sid, {}).get(lang)
    return not rec or rec.get("en_hash") != en_hash(en_secs[sid])


def mood_pending(sid, lang, en_book):
    s = next(x for x in en_book["sections"] if x["id"] == sid)
    targets = {sid} | {x["id"] for x in s.get("subsections") or []}
    for m in json.load(open(MOODS, encoding="utf-8")):
        if m["target"] not in targets:
            continue
        if lang not in (m.get("translations") or {}):
            return True
        if any(lang not in (a.get("translation") or {}) for a in m.get("more") or []):
            return True
    return False


def compute(sections, mood_sections, copy_to=None):
    en_book = _en()
    en_secs = {s["id"]: s for s in en_book["sections"]}
    pend = []
    for lang in LANGS:
        for sid in sections:
            if section_pending(sid, lang, en_secs):
                pend.append({"lang": lang, "section": sid, "kind": "section", "gen": GEN[sid]})
        for sid in mood_sections:
            if mood_pending(sid, lang, en_book):
                pend.append({"lang": lang, "section": sid, "kind": "moods", "gen": "scripts/moods"})
    d = {"updated": time.strftime("%Y-%m-%d %H:%M"),
         "note": "Gurudas msg 868: tulkojums gaida — EN līdz tulkojumam; lint L27/L31 pieņem EN tikai šiem pāriem",
         "pending": pend}
    txt = json.dumps(d, ensure_ascii=False, indent=1) + "\n"
    write_atomic(LIST, txt, newline="\n")
    if copy_to:
        write_atomic(copy_to, txt, newline="\n")
    return d


TEXT_KEYS = ("title", "subtitle", "content", "translation", "wbw", "caption", "alt", "label", "value", "badge")


def _texts(o, out):
    if isinstance(o, dict):
        if o.get("type") == "mood":
            return out
        for k, v in o.items():
            if k in TEXT_KEYS and isinstance(v, str) and v.strip():
                out.append(v)
            elif k in ("header", "cells") and isinstance(v, list):
                out.extend(x for x in v if isinstance(x, str) and x.strip())
            else:
                _texts(v, out)
    elif isinstance(o, list):
        for v in o:
            _texts(v, out)
    return out


def is_english(sec, en_sec):
    """True when more than half of the text strings of `sec` are English strings of the English section
    (an English fallback copy, possibly of an older English version). # tehniskais slieksnis Lipikāra, nav S noteikums"""
    loc, en = _texts(sec, []), set(_texts(en_sec, []))
    return not loc or sum(1 for t in loc if t in en) * 2 > len(loc)


def snapshot(path):
    by = {}
    for p in load_list().get("pending", []):
        if p["kind"] == "section":
            by.setdefault(p["lang"], []).append(p["section"])
    snap = {}
    for lang, sids in by.items():
        book = json.load(open(os.path.join(DATA, "book.%s.json" % lang), encoding="utf-8"))
        cur = {s["id"]: s for s in book["sections"]}
        snap[lang] = {sid: cur.get(sid) for sid in sids}
    write_atomic(path, json.dumps(snap, ensure_ascii=False) + "\n", newline="\n")
    return {l: list(v) for l, v in snap.items()}


def fallback(snap_path=None):
    snap = json.load(open(snap_path, encoding="utf-8")) if snap_path else {}
    en_book = _en()
    en_ids = [s["id"] for s in en_book["sections"]]
    en_secs = {s["id"]: s for s in en_book["sections"]}
    by_lang = {}
    for p in load_list().get("pending", []):
        if p["kind"] == "section":
            by_lang.setdefault(p["lang"], []).append(p["section"])
    rep = {}

    def nomood(x):
        x = copy.deepcopy(x)
        for n in [x] + (x.get("subsections") or []):
            n["content"] = [b for b in n["content"] if b.get("type") != "mood"]
        return x

    for lang, sids in by_lang.items():
        path = os.path.join(DATA, "book.%s.json" % lang)
        raw = open(path, encoding="utf-8", newline="").read()
        book = json.loads(raw)
        rep[lang] = {}
        for sid in sids:
            en = en_secs[sid]
            loc = next((s for s in book["sections"] if s["id"] == sid), None)
            old = (snap.get(lang) or {}).get(sid) if snap_path else loc
            if old is None or is_english(old, en):
                new = nomood(en)
                if loc is not None:   # keep its mood blocks (apply_moods.py re-does them anyway)
                    for n in [new] + (new.get("subsections") or []):
                        lo = next((x for x in [loc] + (loc.get("subsections") or []) if x["id"] == n["id"]), None)
                        if lo:
                            n["content"] = [b for b in lo["content"] if b.get("type") == "mood"] + n["content"]
                place(book, new, en_ids)
                rep[lang][sid] = "EN section (current English)"
                continue
            if snap_path and loc is not None:
                old = copy.deepcopy(old)
                book["sections"][[s["id"] for s in book["sections"]].index(sid)] = old
            elif loc is None:
                old = copy.deepcopy(old)
                place(book, old, en_ids)
            loc = next(s for s in book["sections"] if s["id"] == sid)
            have = [x["id"] for x in loc.get("subsections") or []]
            added = []
            for i, es in enumerate(en.get("subsections") or []):
                if es["id"] in have:
                    continue
                before = [x["id"] for x in en["subsections"][:i]]
                subs = loc.setdefault("subsections", [])
                at = 0
                for j, x in enumerate(subs):
                    if x["id"] in before:
                        at = j + 1
                subs.insert(at, nomood(es))
                have = [x["id"] for x in subs]
                added.append(es["id"])
            rep[lang][sid] = ("previous translation + EN subsections " + ", ".join(added)) if added else "previous translation"
        write_atomic(path, json.dumps(book, ensure_ascii=False, indent=2) + ("\n" if raw.endswith("\n") else ""))
    return rep


def show():
    pend = load_list().get("pending", [])
    if not pend:
        return "tulkojums gaida: nav (viss iztulkots)"
    return "tulkojums gaida (EN līdz tulkojumam): " + ", ".join("%s/%s%s" % (p["lang"], p["section"],
                                                                             " (citāti)" if p["kind"] == "moods" else "")
                                                                 for p in pend)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    cmd = a[0] if a else "show"
    if cmd == "compute":
        rest = a[1:]
        cp = None
        if "--copy" in rest:
            i = rest.index("--copy")
            cp = rest[i + 1]
            rest = rest[:i] + rest[i + 2:]
        moods = []
        if "--moods" in rest:
            i = rest.index("--moods")
            moods = rest[i + 1:]
            rest = rest[:i]
        compute(rest, moods, cp)
        print(show())
    elif cmd == "snapshot":
        print(json.dumps(snapshot(a[1]), ensure_ascii=False))
    elif cmd == "fallback":
        sp = a[a.index("--snapshot") + 1] if "--snapshot" in a else None
        print(json.dumps(fallback(sp), ensure_ascii=False, indent=1))
    else:
        print(show())
