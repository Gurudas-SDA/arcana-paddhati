# -*- coding: utf-8 -*-
"""Shared builder for hand-written chapters (Part IV, chapters 14 and 15; chapter 13 keeps its own build.py).

A chapter folder holds:
  chapter_ru.py   RU master: SECTION_ID, TITLE, SUBTITLE, INTRO, SUBS, optional TABLES = {name: {"ru": table, "en": table}}
                  (a block {"type": "TABLE", "name": name} is replaced by the table of the book's language),
                  optional EN_FIX = {RU string: EN string} (hand-written English, e.g. quotations whose English
                  original exists — they are not sent to the model), AFTER = section id this chapter follows in its part.
  en_cache.json   EN translation string by string (src = RU string, en = translation, model)
  sources.json    lecture meta for the mood quotes (date, transcript and audio links)
  transcripts/    <nr>_en.txt / <nr>_ru.txt (gitignored; `fetch` downloads them from sources.json)

  python build.py translate   EN for new/changed strings only (AnyModel cx/gpt-6.1-sol, alt cx/gpt-6-sol)
  python build.py apply       writes data/book*.json (idempotent) — then scripts/moods/apply_moods.py
  python build.py moods       replaces this chapter's entries in scripts/moods/moods.json (then apply_moods.py)
  python build.py fetch       downloads missing transcripts
"""
import copy, io, json, os, re, sys, importlib.util

sys.stdout.reconfigure(encoding="utf-8")
CH = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(CH, "..", ".."))
DATA = os.path.join(REPO, "data")
MOODS = os.path.join(REPO, "scripts", "moods", "moods.json")
sys.path.insert(0, os.path.join(REPO, "scripts", "translate"))
from iast_to_cyrillic import translit  # noqa: E402
from i18n_sections import put  # noqa: E402

PART = {"id": "festivals-vows", "ru": "Праздники и обеты", "en": "Festivals and Vows"}
OTHER = ["lv", "de", "fr", "es", "it", "uk", "hu", "pt", "lt"]
FILES = {"en": "book.json", "ru": "book.ru.json", "ru-iast": "book.ru-iast.json"}


def load(folder):
    spec = importlib.util.spec_from_file_location("chapter_ru", os.path.join(folder, "chapter_ru.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def master(ch, lang="ru"):
    """The section with TABLE placeholders filled for `lang` ("ru" or "en")."""
    tables = getattr(ch, "TABLES", {})

    def fill(blocks):
        return [copy.deepcopy(tables[b["name"]][lang]) if b.get("type") == "TABLE" else copy.deepcopy(b) for b in blocks]

    return {"id": ch.SECTION_ID, "title": ch.TITLE, "subtitle": ch.SUBTITLE, "page": "",
            "content": fill(ch.INTRO),
            "subsections": [{"id": s["id"], "title": s["title"], "content": fill(s["content"])} for s in ch.SUBS]}


def strings_of(sec):
    """(path, text) of every translatable string (not verse sanskrit, not tables, not per-language "sources" lines)."""
    out = [(("title",), sec["title"])]

    def walk(blocks, base):
        for i, b in enumerate(blocks):
            for k in ("content", "translation"):
                if b.get(k) and b["type"] not in ("table", "sources"):
                    out.append((base + (i, k), b[k]))

    walk(sec["content"], ("content",))
    for j, sub in enumerate(sec["subsections"]):
        out.append((("subsections", j, "title"), sub["title"]))
        walk(sub["content"], ("subsections", j, "content"))
    return out


def set_path(obj, path, val):
    for p in path[:-1]:
        obj = obj[p]
    obj[path[-1]] = val


def map_inline(text, fn):
    return re.sub(r"⟦([^⟦⟧]*)⟧", lambda m: "⟦" + fn(m.group(1)) + "⟧", text)


def to_cyr(sec):
    s = copy.deepcopy(sec)
    s["subtitle"] = translit(s["subtitle"])

    def blocks(bs):
        for b in bs:
            if b["type"] == "verse":
                b["sanskrit"] = translit(b["sanskrit"])
            for k in ("content", "translation"):
                if b.get(k) and isinstance(b[k], str):
                    b[k] = map_inline(b[k], translit)

    blocks(s["content"])
    for sub in s["subsections"]:
        blocks(sub["content"])
    return s


def translate(folder, system):
    sys.path.insert(0, folder)
    from am import chat  # AnyModel; only needed here
    ch = load(folder)
    fix = getattr(ch, "EN_FIX", {})
    texts = [t for _, t in strings_of(master(ch))]
    cp = os.path.join(folder, "en_cache.json")
    old = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {"src": [], "en": [], "model": ""}
    known = dict(zip(old["src"], old["en"]))
    todo = [t for t in dict.fromkeys(texts) if t not in known and t not in fix]
    model = old.get("model", "")
    for k in range(0, len(todo), 25):
        part = todo[k:k + 25]
        prompt = ("Translate each string of this JSON array from Russian into English. Return a JSON array of the same "
                  "length and order, strings only.\n\n" + json.dumps(part, ensure_ascii=False, indent=0))
        out, model = chat(prompt, system=system)
        got = json.loads(re.search(r"\[.*\]", out, re.S).group(0))
        assert len(got) == len(part), (len(got), len(part))
        for a, b in zip(part, got):
            assert a.count("⟦") == b.count("⟦"), (a, b)
            known[a] = b
        print("translated", k + len(part), "/", len(todo), "with", model)
    arr = [fix.get(t) or known[t] for t in texts]
    json.dump({"model": model, "src": texts, "en": arr}, open(cp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("EN strings:", len(arr), "new:", len(todo), "hand-written:", sum(1 for t in texts if t in fix))


def build_en(ch, folder):
    sec = master(ch, "en")
    cache = json.load(open(os.path.join(folder, "en_cache.json"), encoding="utf-8"))
    items = strings_of(master(ch, "ru"))
    assert [t for _, t in items] == cache["src"], "RU master changed since translation — run: python build.py translate"
    fix = getattr(ch, "EN_FIX", {})
    for (path, src), t in zip(items, cache["en"]):
        set_path(sec, path, fix.get(src) or t)
    return sec


def upsert_section(book, sec):
    ids = [s["id"] for s in book["sections"]]
    if sec["id"] in ids:
        book["sections"][ids.index(sec["id"])] = sec
    else:
        book["sections"].append(sec)


def keep_moods(old_book, sec):
    """apply_moods.py owns the mood blocks: keep the ones already in the book, so a re-run of apply is a no-op."""
    old = {n["id"]: n for s in old_book["sections"] if s["id"] == sec["id"] for n in [s] + s.get("subsections", [])}
    for n in [sec] + sec["subsections"]:
        moods = [b for b in old.get(n["id"], {}).get("content", []) if b.get("type") == "mood"]
        n["content"] = moods + [b for b in n["content"] if b.get("type") != "mood"]


def write_json(path, obj):
    raw = open(path, encoding="utf-8", newline="").read() if os.path.exists(path) else "\n"
    nl = "\n" if raw.endswith("\n") else ""
    open(path, "w", encoding="utf-8", newline="").write(json.dumps(obj, ensure_ascii=False, indent=2) + nl)


def apply(folder):
    ch = load(folder)
    ru = master(ch, "ru")
    en = build_en(ch, folder)
    for lang in ["en", "ru", "ru-iast"] + OTHER:
        path = os.path.join(DATA, FILES.get(lang, f"book.{lang}.json"))
        book = json.load(open(path, encoding="utf-8"))
        sec = {"en": en, "ru": to_cyr(ru) if lang == "ru" else ru, "ru-iast": ru}.get(lang)
        if sec is None:
            # Night 08.10: other languages — the English chapter translated by scripts/translate/night_sync.py
            # (<chapter folder>/i18n.json; mood blocks come from moods.json via apply_moods.py).
            en_book = json.load(open(os.path.join(DATA, FILES["en"]), encoding="utf-8"))
            en_sec = next((s for s in en_book["sections"] if s["id"] == ch.SECTION_ID), None)
            if en_sec is not None:
                old = next((s for s in book["sections"] if s["id"] == ch.SECTION_ID), None)
                st = put(book, lang, ch.SECTION_ID, folder, en_sec, [s["id"] for s in en_book["sections"]])
                new = next((s for s in book["sections"] if s["id"] == ch.SECTION_ID), None)
                if old is not None and new is not None:
                    keep_moods({"sections": [old]}, new)
                print("  ", lang, ch.SECTION_ID, st)
        if sec is not None:
            sec = copy.deepcopy(sec)
            keep_moods(book, sec)
            upsert_section(book, sec)
            # keep the book order = the part order
            ids = [s["id"] for s in book["sections"]]
            after = getattr(ch, "AFTER", None)
            if after in ids and ids.index(sec["id"]) != ids.index(after) + 1:
                book["sections"].remove(sec)
                book["sections"].insert([s["id"] for s in book["sections"]].index(after) + 1, sec)
        # every book lists the chapter in Part IV (books without the section show the English one, with a note);
        # a front-matter chapter (IN_PART = False) stays outside the parts, placed only by AFTER (the app takes the
        # section order from the English book and shows the English section where a language has none)
        if not getattr(ch, "IN_PART", True):
            write_json(path, book)
            print("wrote", lang)
            continue
        p = next(x for x in book["parts"] if x["id"] == PART["id"])
        if ch.SECTION_ID not in p["sections"]:
            after = getattr(ch, "AFTER", None)
            p["sections"].insert(p["sections"].index(after) + 1 if after in p["sections"] else len(p["sections"]), ch.SECTION_ID)
        write_json(path, book)
        print("wrote", lang)


# ------------------------------------------------------------------ mood quotes
def fetch(folder):
    import requests, docx
    meta = json.load(open(os.path.join(folder, "sources.json"), encoding="utf-8"))
    tr = os.path.join(folder, "transcripts")
    os.makedirs(tr, exist_ok=True)
    for nr, x in meta.items():
        for lang in ("en", "ru"):
            p = os.path.join(tr, f"{nr}_{lang}.txt")
            if os.path.exists(p):
                continue
            fid = re.search(r"/d/([^/]+)", x[f"script_{lang}_url"]).group(1)
            r = requests.get(f"https://drive.google.com/uc?export=download&id={fid}", timeout=120)
            d = docx.Document(io.BytesIO(r.content))
            paras = [q.text for q in d.paragraphs]
            for t in d.tables:
                for row in t.rows:
                    paras.append(" | ".join(c.text for c in row.cells))
            open(p, "w", encoding="utf-8").write("\n".join(paras))
            print(nr, lang, len(paras))


class Quotes:
    """Cuts verbatim quotes from transcripts/<nr>_{en,ru}.txt. A line is addressed by its [hh:mm:ss] timecode
    (the EN and RU files have the same timecodes, not always the same line numbers) or, for a line without a
    timecode, by ("#", index)."""

    def __init__(self, folder, titles):
        self.folder, self.titles = folder, titles
        self.meta = json.load(open(os.path.join(folder, "sources.json"), encoding="utf-8"))

    def line(self, nr, lang, key):
        L = open(os.path.join(self.folder, "transcripts", f"{nr}_{lang}.txt"), encoding="utf-8").read().split("\n")
        if isinstance(key, dict):  # the two transcripts differ here: {"en": key, "ru": key}
            key = key[lang]
        if isinstance(key, tuple):
            t = L[key[1]]
        else:
            hits = [x for x in L if x.startswith("[" + key + "]")]
            assert len(hits) == 1, (nr, lang, key, len(hits))
            t = hits[0]
        return re.sub(r"^\[\d\d:\d\d:\d\d\]\s*", "", t).strip()

    @staticmethod
    def cut(text, start=None, end=None):
        if start:
            text = text[text.index(start):]
        if end:
            text = text[:text.index(end) + len(end)]
        return text.strip()

    def piece(self, nr, ts, spec, join="\n\n", fix_ru=None):
        """spec: list of (line key, en_start, en_end, ru_start, ru_end); key None = "[…]"."""
        en = join.join("[…]" if k is None else self.cut(self.line(nr, "en", k), a, b) for k, a, b, c, d in spec)
        ru = join.join("[…]" if k is None else self.cut(self.line(nr, "ru", k), c, d) for k, a, b, c, d in spec)
        for a, b in (fix_ru or {}).items():  # obvious typing slips in the Academy RU transcript (Latin letters etc.)
            assert a in ru, (nr, a)
            ru = ru.replace(a, b)
        x = self.meta[nr]
        src = {"title": self.titles[nr], "date": x["date"].replace(".", "-"), "nr": nr, "timecode": ts,
               "transcript_url": x.get("script_en_url") or "", "audio_url": x.get("dwnld_url") or ""}
        return en, ru, src

    @staticmethod
    def entry(target, main, more=()):
        en, ru, src = main
        e = {"target": target, "candidate": "PartIV", "quote": en, "translations": {"ru": ru, "ru-iast": ru},
             "machine": [], "source": src}
        if more:
            e["more"] = [{"candidate": "PartIV", "label": "", "quote": a, "translation": {"ru": b, "ru-iast": b},
                          "machine": [], "source": s} for a, b, s in more]
        return e


def write_moods(new):
    moods = json.load(open(MOODS, encoding="utf-8"))
    targets = {e["target"] for e in new}
    out = [next(e for e in new if e["target"] == m["target"]) if m["target"] in targets else m for m in moods]
    out += [e for e in new if e["target"] not in {m["target"] for m in moods}]
    write_json(MOODS, out)
    for e in new:
        print("==", e["target"], e["source"]["nr"], e["source"]["timecode"], "| more:", [m["source"]["nr"] for m in e.get("more", [])])


def main(folder, system, mood_entries):
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "translate":
        translate(folder, system)
    elif cmd == "apply":
        apply(folder)
    elif cmd == "fetch":
        fetch(folder)
    elif cmd == "moods":
        write_moods(mood_entries())
    else:
        print(__doc__)
