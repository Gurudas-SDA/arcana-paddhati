# -*- coding: utf-8 -*-
"""Front pages before the Guru-paramparā (Satkirti 22.10 msg 6137/6139, 6151–6155):

  «Упадеша-сара» (id upadesha-sara) — right after the cover, the epigraph of the whole book: Śrī Upadeśāmṛta 8
      (IAST = vedabase.io noi/8 + Versebase; translation and word-for-word BBT verbatim — vedabase.io/ru for ru + ru-iast,
      /en for en; verse_um8.json) + «Настроение Гурудева» (5 quotes on this verse: scripts/moods/moods.json, target
      upadesha-sara -> apply_moods.py).
  «Джая-дхвани» (id jaya-dhvani) — just before «Гуру-парампара»: the calls of glorification from the beginning of the
      Gauḍīya-gīti-guccha songbook (jaya_dhvani.py: source, IAST, draft RU/EN translation + word-for-word), one verse
      block per call (Satkirti will strike the lines that are not needed).

  python build.py apply    writes both sections into data/book.json, book.ru.json (Cyrillic transliteration of the
                           Sanskrit), book.ru-iast.json — at the start of the book, before «parampara» (front matter,
                           unnumbered); then the 9 other languages from i18n.json (night_sync.py upadesha-sara
                           jaya-dhvani) or English (the app's fallback) until translated.
"""
import copy, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
DATA = os.path.join(REPO, "data")
sys.path.insert(0, os.path.join(REPO, "scripts", "translate"))
sys.path.insert(0, HERE)
from iast_to_cyrillic import translit  # noqa: E402
from i18n_sections import put, write_atomic  # noqa: E402
import jaya_dhvani as jd  # noqa: E402

IDS = ["upadesha-sara", "jaya-dhvani"]
TITLE = {"upadesha-sara": {"ru": "Упадеша-сара", "en": "Upadeśa-sāra"},
         "jaya-dhvani": {"ru": "Джая-дхвани", "en": "Jaya-dhvani"}}
OTHER = ["lv", "de", "fr", "es", "it", "uk", "hu", "pt", "lt"]


def wbw(pairs, cyr):
    return "; ".join("%s — %s" % (translit(w) if cyr else w, g) for w, g in pairs) + "."


def sections(lang):
    v = json.load(open(os.path.join(HERE, "verse_um8.json"), encoding="utf-8"))
    ru, cyr = lang != "en", lang == "ru"
    um8 = {"type": "verse", "sanskrit": translit(v["IAST"]) if cyr else v["IAST"],
           "translation": v["TR_RU"] if ru else v["TR_EN"],
           "wbw": wbw(zip(v["HEAD"], v["WBW_RU"] if ru else v["WBW_EN"]), cyr)}
    lines = [{"type": "verse", "sanskrit": translit(iast) if cyr else iast, "translation": r if ru else e,
              "wbw": wbw([(w, gr if ru else ge) for w, gr, ge in ws], cyr)} for iast, r, e, ws in jd.LINES]
    t = "ru" if ru else "en"
    return [{"id": "upadesha-sara", "title": TITLE["upadesha-sara"][t], "subtitle": None, "page": "", "content": [um8],
             "subsections": []},
            {"id": "jaya-dhvani", "title": TITLE["jaya-dhvani"][t], "subtitle": None, "page": "", "content": lines,
             "subsections": []}]


def front(book, secs):
    """the new sections first, then the rest (parampara …); mood blocks already in the book are kept (apply_moods.py)"""
    old = {s["id"]: s for s in book["sections"]}
    for s in secs:
        moods = [b for b in old.get(s["id"], {}).get("content", []) if b.get("type") == "mood"]
        s["content"] = moods + s["content"]
    book["sections"] = secs + [s for s in book["sections"] if s["id"] not in IDS]
    for p in book.get("parts", []):
        assert not set(IDS) & set(p["sections"])


def apply():
    for lang, fn in (("en", "book.json"), ("ru", "book.ru.json"), ("ru-iast", "book.ru-iast.json")):
        p = os.path.join(DATA, fn)
        raw = open(p, encoding="utf-8", newline="").read()
        b = json.loads(raw)
        front(b, sections(lang))
        write_atomic(p, json.dumps(b, ensure_ascii=False, indent=2) + ("\n" if raw.endswith("\n") else ""))
        print("wrote", fn)
    en = json.load(open(os.path.join(DATA, "book.json"), encoding="utf-8"))
    en_ids = [s["id"] for s in en["sections"]]
    en_secs = {s["id"]: s for s in en["sections"]}
    for lang in OTHER:
        p = os.path.join(DATA, "book.%s.json" % lang)
        raw = open(p, encoding="utf-8", newline="").read()
        b = json.loads(raw)
        st = {}
        for sid in IDS:
            st[sid] = put(b, lang, sid, HERE, en_secs[sid], en_ids)
            if st[sid].startswith("none"):
                # English until translated (L27: every Sanskrit field exists in every book); no mood block
                e = copy.deepcopy(en_secs[sid])
                e["content"] = [x for x in e["content"] if x.get("type") != "mood"]
                old = next((s for s in b["sections"] if s["id"] == sid), None)
                if old:
                    e["content"] = [x for x in old["content"] if x.get("type") == "mood"] + e["content"]
                b["sections"] = [s for s in b["sections"] if s["id"] != sid]
                at = 0 if sid == "upadesha-sara" else 1
                b["sections"].insert(at, e)
        write_atomic(p, json.dumps(b, ensure_ascii=False, indent=2) + ("\n" if raw.endswith("\n") else ""))
        print(lang, st)


if __name__ == "__main__":
    if (sys.argv[1:] or [""])[0] == "apply":
        apply()
    else:
        print(__doc__)
