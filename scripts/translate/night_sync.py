# -*- coding: utf-8 -*-
"""Night sync of the other languages (lv, de, fr, es, it, uk, hu) with the English book (Night release 08.10.2026).

Rule (Gurudas): by day only RU + EN are edited; at night the other languages are brought up to date.

For each section id given, the ENGLISH section (data/book.json) is translated into each language with
AnyModel cx/gpt-6.1-sol (fallback cx/gpt-6-sol, logged; both failing -> that language is skipped and reported).
Translated: section/subsection titles, table cells with words, text/instruction/subtitle/list content, verse translations, word-by-word
meanings (the Sanskrit words of a gloss stay byte-identical), portrait captions, image alt, table headers/badges,
paired-list labels/values. Never touched: verse `sanskrit` (IAST), ids, src, numbers, mood blocks (moods.json).
Conventions per language are taken from the existing book.<lang>.json (glossary.<lang>.json + aligned examples).

The result is stored in the generator's folder, `<generator>/i18n.json` = {"<lang>": {"en_hash": …, "section": …}},
and the generator (ch16_arati_songs/build.py, ch17_kartika_bhajans/build.py, parampara/apply_parampara.py) puts the
sections into data/book.<lang>.json — so a rebuild of a generator keeps the other languages. `en_hash` = hash of the
English section the translation was made from: a generator warns STALE when the English has changed since.

    python scripts/translate/night_sync.py <section-id> [...] [--langs lv,de] [--force]
Keys: C:\\Users\\gurud\\.credentials\\ca_pipeline\\config.ini [anymodel] key_* (never printed).
"""
import argparse
import concurrent.futures as cf
import configparser
import copy
import json
import os
import re
import sys
import threading
import time

import requests

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(REPO, "data")
URL = "https://anymodel.org/v1/chat/completions"
MODELS = ["cx/gpt-6.1-sol", "cx/gpt-6-sol"]
LANGS = ["lv", "de", "fr", "es", "it", "uk", "hu"]
LNAME = {"lv": "Latvian", "de": "German", "fr": "French", "es": "Spanish", "it": "Italian", "uk": "Ukrainian",
         "hu": "Hungarian"}
LOG = os.path.join(HERE, "night_sync.log")
GENERATOR = {  # section id -> folder of its generator (i18n.json is written there)
    "parampara": os.path.join(REPO, "scripts", "parampara"),
    "mangala-arati-songs": os.path.join(REPO, "scripts", "chapters", "ch16_arati_songs"),
    "gaura-arati-songs": os.path.join(REPO, "scripts", "chapters", "ch16_arati_songs"),
    "kartika-bhajans": os.path.join(REPO, "scripts", "chapters", "ch17_kartika_bhajans"),
    "gaudiya-emblem": os.path.join(REPO, "scripts", "chapters", "ch00_gaudiya_emblem"),
    "vigraha-tattva": os.path.join(REPO, "scripts", "chapters", "ch00b_vigraha_tattva"),
    "caturmasya-purusottama-masa": os.path.join(REPO, "scripts", "chapters", "ch13_caturmasya"),
    "guru-puja-vyasa-puja": os.path.join(REPO, "scripts", "chapters", "ch14_vyasa_puja"),
    "major-festivals": os.path.join(REPO, "scripts", "chapters", "ch15_major_festivals"),
}
MOODS = os.path.join(REPO, "scripts", "moods", "moods.json")
NL = chr(10)
_lock = threading.Lock()
USED_MODEL = {}


def log(msg):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    with _lock:
        print(line, flush=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def keys():
    c = configparser.ConfigParser()
    c.read(r"C:\Users\gurud\.credentials\ca_pipeline\config.ini", encoding="utf-8")
    return [c["anymodel"][k] for k in c["anymodel"] if re.fullmatch(r"key_\d+", k)]


KEYS = keys()


sys.path.insert(0, HERE)
from i18n_sections import en_hash, write_atomic  # noqa: E402


# ---------------- model call ----------------
def call(lang, messages, key_i, max_tokens=32000):
    """-> (content, model). Tries gpt-6.1-sol on several keys, then gpt-6-sol; raises if both fail."""
    errs = []
    for model in MODELS:
        for attempt in range(4):
            key = KEYS[(key_i + attempt) % len(KEYS)]
            body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.2,
                    "response_format": {"type": "json_object"}}
            t0 = time.time()
            try:
                r = requests.post(URL, headers={"Authorization": "Bearer " + key, "User-Agent": "Mozilla/5.0"},
                                  json=body, timeout=600)
                if r.status_code == 400 and "response_format" in r.text:
                    body.pop("response_format")
                    r = requests.post(URL, headers={"Authorization": "Bearer " + key, "User-Agent": "Mozilla/5.0"},
                                      json=body, timeout=600)
                if r.status_code != 200:
                    raise RuntimeError("HTTP %s %s" % (r.status_code, r.text[:200].replace(key, "***")))
                d = r.json()
                u = d.get("usage") or {}
                log("  %s %s %.0fs in=%s out=%s fin=%s" % (lang, model, time.time() - t0, u.get("prompt_tokens"),
                                                          u.get("completion_tokens"), d["choices"][0].get("finish_reason")))
                if model != MODELS[0]:
                    USED_MODEL[lang] = model
                return d["choices"][0]["message"]["content"] or "", model
            except Exception as e:  # noqa: BLE001
                msg = str(e).replace(key, "***")[:250]
                errs.append("%s: %s" % (model, msg))
                log("  %s call error %s attempt %d: %s" % (lang, model, attempt + 1, msg))
                time.sleep(5 * (attempt + 1))
        log("  %s: %s failed on all tried keys -> next model" % (lang, model))
    raise RuntimeError("all models failed: " + " | ".join(errs[-3:]))


def parse_json(content):
    m = re.search(r"\{.*\}", content, re.S)
    return json.loads(m.group(0))


# ---------------- fields ----------------
def fields(sec):
    """[(path, text)] of the translatable text fields of a section (wbw separately)."""
    out = []

    def content(base, cont):
        for i, e in enumerate(cont):
            p = base + ["content", i]
            t = e["type"]
            if t == "mood":
                continue
            if t == "verse":
                if e.get("translation"):
                    out.append((p + ["translation"], e["translation"]))
            elif t in ("text", "instruction", "subtitle", "list", "bullet-list", "sources"):
                if e.get("content"):
                    out.append((p + ["content"], e["content"]))
            elif t == "image":
                if e.get("alt"):
                    out.append((p + ["alt"], e["alt"]))
            elif t == "portrait":
                if e.get("caption"):
                    out.append((p + ["caption"], e["caption"]))
            elif t == "paired-list":
                for ii, it in enumerate(e["items"]):
                    for f in ("label", "value"):
                        if it.get(f):
                            out.append((p + ["items", ii, f], it[f]))
            elif t == "table":
                for hi, h in enumerate(e["header"]):
                    out.append((p + ["header", hi], h))
                for ri, row in enumerate(e["rows"]):
                    for ci, cell in enumerate(row.get("cells") or []):
                        if re.search(r"[^\W\d_]", cell):   # words (not a bare number / year)
                            out.append((p + ["rows", ri, "cells", ci], cell))
                    if row.get("badge"):
                        out.append((p + ["rows", ri, "badge"], row["badge"]))
            elif t == "ornament":
                pass
            else:
                raise ValueError("unknown block type " + t)

    for f in ("title", "subtitle"):
        if sec.get(f):
            out.append(([f], sec[f]))
    content([], sec["content"])
    for j, ss in enumerate(sec.get("subsections") or []):
        if ss.get("title"):
            out.append((["subsections", j, "title"], ss["title"]))
        content(["subsections", j], ss["content"])
    return out


def wbw_fields(sec):
    out = []

    def walk(o, p):
        if isinstance(o, dict):
            if o.get("type") == "verse" and o.get("wbw"):
                out.append((p, o["sanskrit"], o["wbw"]))
            for k, v in o.items():
                walk(v, p + [k])
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, p + [i])
    walk(sec, [])
    return out


def get_in(o, path):
    for p in path:
        o = o[p]
    return o


def set_in(o, path, v):
    for p in path[:-1]:
        o = o[p]
    o[path[-1]] = v


def parse_wbw(w):
    pairs = []
    for part in w.split(";"):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(.*?)\s+[—–-]\s+(.*)$", part, re.S)
        pairs.append((m.group(1).strip(), m.group(2).strip()) if m else (part, ""))
    return pairs


def wbw_problems(tr, en):
    if not isinstance(tr, str) or not tr.strip():
        return ["empty"]
    p = []
    if "\n" in tr:
        p.append("newline")
    a, b = parse_wbw(en), parse_wbw(tr)
    if [w for w, _ in a] != [w for w, _ in b]:
        p.append("word sequence differs")
    if any(not m.strip(" .") for _, m in b):
        p.append("empty meaning")
    return p


# ---------------- conventions of a language book ----------------
def load_gloss(lang):
    p = os.path.join(HERE, "glossary.%s.json" % lang)
    d = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    out = dict(d.get("base", {}))
    for k, v in d.get("extra", {}).items():
        out.setdefault(k, v)
    return out


EN = json.load(open(os.path.join(DATA, "book.json"), encoding="utf-8"))


def examples(lang, n_text=6, n_verse=2, n_title=4):
    """Aligned (English, <lang>) pairs from chapters already translated: the book's own conventions
    (⟦…⟧ spans, how names/terms are written, register)."""
    tb = json.load(open(os.path.join(DATA, "book.%s.json" % lang), encoding="utf-8"))
    own = {s["id"]: s for s in tb["sections"]}
    tx, vs, ti, wb = [], [], [], []
    for sid in ("arcana-sri-guru", "daily-duties-brahma-muhurta", "mantras-honouring-caranamrita",
                "worship-sixteen-articles"):
        es = next(s for s in EN["sections"] if s["id"] == sid)
        ls = own.get(sid)
        if not ls:
            continue
        for path, t in fields(es):
            try:
                v = get_in(ls, path)
            except (KeyError, IndexError, TypeError):
                continue
            if path[-1] == "title" and len(ti) < n_title:
                ti.append((t, v))
            elif path[-1] == "translation" and len(vs) < n_verse:
                vs.append((t, v))
            elif path[-1] == "content" and "⟦" in t and len(t) < 400 and len(tx) < n_text:
                tx.append((t, v))
        for path, s, w in wbw_fields(es):
            if len(wb) < 2 and len(w) < 500:
                try:
                    wb.append((w, get_in(ls, path + ["wbw"])))
                except (KeyError, IndexError, TypeError):
                    pass
    return tx + vs + ti, wb


TERM_RULES = {
    "lv": ("Sanskrit names and terms inside Latvian prose are LATVIANIZED with Latvian letters and case endings, exactly as "
           "this book's Latvian examples show (Krišna, Čaitanja, vaišnavs, āčamana, Šrī Guru, Bhaktivinoda Thākurs, "
           "Višvanātha Čakravartī Thākurs, Nārājana, Kešava, Panča-tatva). Personal names get Latvian nominative endings "
           "where the book does so (e.g. «Bhaktivinoda Thākurs»). Latvianization: j → dž (Džagannātha, Pradžņāna), c → č, "
           "ś/ṣ → š, ṭ/ḍ/ṇ/ṅ → t/d/n/n, ñ → ņ, y → j, ṛ → ri, ṁ → m; long vowels keep macrons (ā ī ū ē)."),
    "uk": ("Sanskrit names and terms inside Ukrainian prose are written in the Ukrainian DIACRITIC Cyrillic used by this "
           "book and vedabase.io/uk (Кр̣шн̣а, Ш́рı̄ Ґуру, Бгактівінода Т̣га̄кура, Кеш́ава, На̄ра̄йан̣а, Пан̃ча-таттва, "
           "Прабгупа̄да): a а, ā а̄, i і, ī ı̄, u у, ū ӯ, ṛ р̣, e е, o о, ai аі, au ау, ṁ м̇, ḥ х̣, k к, kh кх, g ґ, gh ґг, "
           "ṅ н̇, c ч, ch чх, j дж, jh джх, ñ н̃, ṭ т̣, ḍ д̣, ṇ н̣, t т, th тх, d д, dh дг, n н, p п, ph пх, b б, bh бг, "
           "y й, r р, l л, v в, ś ш́, ṣ ш, s с, h х; inflected with Ukrainian case endings."),
}
for _l in ("de", "fr", "es", "it", "hu"):
    TERM_RULES[_l] = ("Sanskrit names and terms inside prose stay exactly as in the English source (IAST with diacritics: "
                      "Kṛṣṇa, Śrīla Bhaktivinoda Ṭhākura, Gurvaṣṭakam), as this book and vedabase.io/%s do; only the "
                      "English words around them are translated. Names in a caption or heading that are entirely "
                      "Sanskrit/IAST stay byte-identical." % _l)


def system_prompt(lang):
    gl = load_gloss(lang)
    g = "\n".join("- %s → %s" % (k, v) for k, v in list(gl.items())[:220])
    ex, _ = examples(lang)
    e = "\n".join("EN: %s\n%s: %s" % (a, lang.upper(), b) for a, b in ex)
    return f"""You are an expert translator of Gauḍīya Vaiṣṇava literature. You translate parts of "Arcana Paddhati" (a manual of Deity worship by Chaitanya Academy) from English into {LNAME[lang]}, continuing an existing {LNAME[lang]} edition of this book — match its conventions exactly.

INPUT: {{"items":[{{"k":"<id>","t":"<English text>"}}, ...]}}
OUTPUT: ONLY a JSON object {{"items":[{{"k":"<same id>","t":"<{LNAME[lang]} text>"}}, ...]}} — EVERY item, same k, same order, none empty.

RULES
1. An item that is entirely Sanskrit/IAST (a mantra, a song title such as "Śrī Gurvaṣṭakam", a verse fragment) is rendered as the {LNAME[lang]} edition renders such names/terms (rule 3); a Sanskrit MANTRA or verse quotation stays EXACTLY in IAST.
2. ⟦ and ⟧ mark Sanskrit spans. Keep every ⟦…⟧ span at the corresponding place (same number, same order). A mantra / Sanskrit phrase inside ⟦…⟧ is copied byte-identically; a single term or name inside ⟦…⟧ may take the edition's spelling and case ending INSIDE the markers, as the examples show. Do not add new ⟦ ⟧.
3. {TERM_RULES[lang]}
4. "Chaitanya Academy" is the name of the community: keep it as "Chaitanya Academy"{' (Ukrainian: «Чайтанья Академія», declined)' if lang == 'uk' else ''}.
5. Preserve line breaks (\\n), quotation marks style of the language, brackets, punctuation. Do not add or omit content, no explanations.
6. Translate the meaning faithfully and literarily, in the devotional register of the existing edition.

GLOSSARY of this edition (use consistently, inflect as grammar requires):
{g}

EXAMPLES from this edition (English → {LNAME[lang]}):
{e}
"""


def wbw_prompt(lang):
    gl = load_gloss(lang)
    g = "\n".join("- %s → %s" % (k, v) for k, v in list(gl.items())[:220])
    _, wb = examples(lang)
    e = "\n".join("EN: %s\n%s: %s" % (a, lang.upper(), b) for a, b in wb)
    return f"""You are a Gauḍīya-Vaiṣṇava Sanskrit scholar. You translate the word-by-word glosses of verses of "Arcana Paddhati" from English into {LNAME[lang]}, continuing the existing {LNAME[lang]} edition.

INPUT: {{"items":[{{"k":"<id>","sanskrit":"<verse, IAST>","en":"<English gloss>","translation":"<the edition's {LNAME[lang]} translation of the verse>"}}, ...]}}
OUTPUT: ONLY {{"items":[{{"k":"<same id>","wbw":"<{LNAME[lang]} gloss>"}}, ...]}} — every item, same k, same order.

RULES
1. Keep EXACTLY the same entries as the English gloss: the same Sanskrit words, character-for-character (IAST, diacritics, hyphens, apostrophes, brackets), same order, none added, dropped, merged or split. Translate ONLY the meaning after " — ".
2. Format: one line, pairs "word — meaning" separated by "; " (as in the English). Never use ";" inside a meaning (use ","). No line breaks.
3. Meanings: short, natural {LNAME[lang]}, consistent with the given translation and the glossary. {TERM_RULES[lang]}
GLOSSARY:
{g}
EXAMPLES from this edition:
{e}
"""


# ---------------- translate one section into one language ----------------
def translate_items(lang, items, key_i, label, depth=0):
    sp = system_prompt(lang)
    want = [k for k, _ in items]
    for attempt in range(3):
        content, _ = call(lang, [{"role": "system", "content": sp},
                                 {"role": "user", "content": json.dumps({"items": [{"k": k, "t": t} for k, t in items]},
                                                                       ensure_ascii=False)}], key_i + attempt)
        try:
            d = parse_json(content)
            got = {str(it["k"]): it["t"] for it in d["items"]}
            bad = [k for k in want if not isinstance(got.get(k), str) or not got[k].strip()]
            if bad or set(got) - set(want):
                raise ValueError("missing/empty %d extra %d" % (len(bad), len(set(got) - set(want))))
            src = dict(items)
            for k in want:
                if got[k].count("⟦") != got[k].count("⟧"):
                    raise ValueError("unbalanced markers in " + k)
                if src[k].count(NL) != got[k].count(NL):
                    raise ValueError("line count differs in %s (%d vs %d)" % (k, src[k].count(NL), got[k].count(NL)))
                if src[k].count("⟦") != got[k].count("⟦"):
                    raise ValueError("⟦⟧ span count differs in %s (%d vs %d)" % (k, src[k].count("⟦"), got[k].count("⟦")))
            return got
        except Exception as e:  # noqa: BLE001
            log("  %s %s invalid response (try %d): %s" % (lang, label, attempt + 1, e))
    if len(items) <= 1 or depth > 3:
        raise RuntimeError("%s %s: cannot translate" % (lang, label))
    h = len(items) // 2
    a = translate_items(lang, items[:h], key_i, label + "a", depth + 1)
    a.update(translate_items(lang, items[h:], key_i + 1, label + "b", depth + 1))
    return a


def translate_wbw(lang, items, key_i, label, chunk=10):
    """items: [(k, sanskrit, en_wbw, translation)] -> {k: wbw}"""
    sp = wbw_prompt(lang)
    done = {}
    todo = list(items)
    for attempt in range(4):
        if not todo:
            break
        nxt = []
        for i in range(0, len(todo), chunk):
            part = todo[i:i + chunk]
            payload = {"items": [{"k": k, "sanskrit": s, "en": w, "translation": t} for k, s, w, t in part]}
            content, _ = call(lang, [{"role": "system", "content": sp},
                                     {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}], key_i + attempt)
            try:
                got = {str(it["k"]): it.get("wbw") for it in parse_json(content)["items"]}
            except Exception as e:  # noqa: BLE001
                log("  %s %s wbw invalid: %s" % (lang, label, e))
                got = {}
            for k, s, w, t in part:
                pr = wbw_problems(got.get(k), w)
                if pr:
                    log("  %s %s wbw %s: %s" % (lang, label, k, pr))
                    nxt.append((k, s, w, t))
                else:
                    done[k] = got[k].strip()
        todo = nxt
        chunk = max(1, chunk // 3)
    if todo:
        raise RuntimeError("%s %s: wbw failed for %d verses" % (lang, label, len(todo)))
    return done


def translate_section(lang, sid, key_i):
    es = next(s for s in EN["sections"] if s["id"] == sid)
    sec = copy.deepcopy(es)
    fl = fields(es)
    items = [("k%d" % i, t) for i, (_, t) in enumerate(fl)]
    got = {}
    CH = 40
    for i in range(0, len(items), CH):
        got.update(translate_items(lang, items[i:i + CH], key_i, "%s#%d" % (sid, i // CH)))
    for i, (path, _) in enumerate(fl):
        set_in(sec, path, got["k%d" % i])
    wf = wbw_fields(es)
    if wf:
        wi = [("w%d" % i, s, w, get_in(sec, p + ["translation"]) if get_in(es, p).get("translation") else "")
              for i, (p, s, w) in enumerate(wf)]
        wd = translate_wbw(lang, wi, key_i + 2, sid)
        for i, (p, _, _) in enumerate(wf):
            set_in(sec, p + ["wbw"], wd["w%d" % i])
    # invariants: sanskrit byte-identical, structure identical
    assert [x for _, x, _ in wbw_fields(sec)] == [x for _, x, _ in wf]
    assert json.dumps(strip_text(sec)) == json.dumps(strip_text(es)), "structure changed"
    for n in [sec] + (sec.get("subsections") or []):   # mood blocks: moods.json + apply_moods.py own them
        n["content"] = [b for b in n["content"] if b.get("type") != "mood"]
    return {"en_hash": en_hash(es), "model": USED_MODEL.get(lang, MODELS[0]),
            "date": time.strftime("%Y-%m-%d %H:%M"), "section": sec}


def strip_text(o):
    """Structure + untranslated fields only (for the invariant check)."""
    tr = ("title", "subtitle", "content", "translation", "wbw", "caption", "alt", "label", "value", "badge")
    if isinstance(o, dict):
        return {k: strip_text(v) for k, v in o.items()
                if k not in ("header", "cells") and not (k in tr and isinstance(v, str))}
    if isinstance(o, list):
        return [strip_text(v) for v in o]
    return o


def i18n_path(sid):
    return os.path.join(GENERATOR[sid], "i18n.json")


def save(sid, lang, rec):
    with _lock:
        p = i18n_path(sid)
        d = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
        d.setdefault(sid, {})[lang] = rec
        d = {k: {l: d[k][l] for l in LANGS if l in d[k]} for k in sorted(d)}
        write_atomic(p, json.dumps(d, ensure_ascii=False, indent=1) + "\n", newline="\n")


def done_already(sid, lang):
    p = i18n_path(sid)
    if not os.path.exists(p):
        return False
    rec = json.load(open(p, encoding="utf-8")).get(sid, {}).get(lang)
    es = next(s for s in EN["sections"] if s["id"] == sid)
    return bool(rec) and rec["en_hash"] == en_hash(es)


def run_lang(lang, sids, key_i, force):
    res = {}
    for sid in sids:
        if not force and done_already(sid, lang):
            log("SKIP %s/%s (up to date)" % (lang, sid))
            res[sid] = "cached"
            continue
        t0 = time.time()
        try:
            rec = translate_section(lang, sid, key_i)
            save(sid, lang, rec)
            res[sid] = "ok " + rec["model"]
            log("DONE %s/%s %.0fs model=%s" % (lang, sid, time.time() - t0, rec["model"]))
        except Exception as e:  # noqa: BLE001
            res[sid] = "FAIL %s" % e
            log("FAIL %s/%s: %s" % (lang, sid, e))
            if "all models failed" in str(e):
                log("STOP %s: both models failed" % lang)
                break
    return lang, res


# ---------------- Gurudev's quotes (scripts/moods/moods.json) ----------------
def mood_prompt(lang):
    gl = load_gloss(lang)
    g = NL.join("- %s → %s" % (k, v) for k, v in list(gl.items())[:220])
    return f"""You translate quotations of Gurudev (Śrī Prem Prayojan Prabhu) — his own spoken English words from lectures — into {LNAME[lang]} for the {LNAME[lang]} edition of "Arcana Paddhati". The English original is shown next to the translation in the book.
INPUT: {{"items":[{{"k":"<id>","t":"<English quote>"}}, ...]}}  OUTPUT: ONLY {{"items":[{{"k":"<same id>","t":"<{LNAME[lang]}>"}}, ...]}} — every item, same order.
RULES: faithful to the spoken words (keep their order and emphasis, smooth only obvious speech slips), natural {LNAME[lang]}, no additions, no omissions, keep paragraph breaks (\n). Sanskrit words and names inside the quote: {TERM_RULES[lang]} Keep "(..)" and "[...]" marks as they are.
GLOSSARY:
{g}
"""


def mood_jobs(targets):
    """[(ref, text)] of the quotes (main + more) of `targets` without a translation into some language."""
    moods = json.load(open(MOODS, encoding="utf-8"))
    jobs = []
    for mi, m in enumerate(moods):
        if m["target"] not in targets:
            continue
        jobs.append((("m", mi), m["quote"], m.get("translations", {})))
        for ai, alt in enumerate(m.get("more", [])):
            jobs.append((("a", mi, ai), alt["quote"], alt.get("translation", {})))
    return jobs


def run_moods(lang, targets, key_i):
    jobs = [(ref, q) for ref, q, tr in mood_jobs(targets) if lang not in tr]
    if not jobs:
        return lang, {"moods": "cached"}
    sp = mood_prompt(lang)
    got = {}
    for i in range(0, len(jobs), 8):
        part = jobs[i:i + 8]
        items = [("q%d" % (i + j), q) for j, (_, q) in enumerate(part)]
        for attempt in range(3):
            content, _ = call(lang, [{"role": "system", "content": sp},
                                     {"role": "user", "content": json.dumps({"items": [{"k": k, "t": t} for k, t in items]},
                                                                           ensure_ascii=False)}], key_i + attempt)
            try:
                d = {str(x["k"]): x["t"] for x in parse_json(content)["items"]}
                if any(not isinstance(d.get(k), str) or not d[k].strip() for k, _ in items):
                    raise ValueError("missing items")
                got.update(d)
                break
            except Exception as e:  # noqa: BLE001
                log("  %s moods invalid (try %d): %s" % (lang, attempt + 1, e))
        else:
            return lang, {"moods": "FAIL chunk %d" % i}
    with _lock:
        moods = json.load(open(MOODS, encoding="utf-8"))
        for j, (ref, _) in enumerate(jobs):
            t = got["q%d" % j]
            if ref[0] == "m":
                m = moods[ref[1]]
                m.setdefault("translations", {})[lang] = t
                if lang not in m.setdefault("machine", []):
                    m["machine"].append(lang)
            else:
                a = moods[ref[1]]["more"][ref[2]]
                a.setdefault("translation", {})[lang] = t
                if lang not in a.setdefault("machine", []):
                    a["machine"].append(lang)
        write_atomic(MOODS, json.dumps(moods, ensure_ascii=False, indent=2) + NL)
    log("DONE %s moods: %d quotes" % (lang, len(jobs)))
    return lang, {"moods": "ok %d" % len(jobs)}


def targets_of(sids):
    out = set()
    for s in EN["sections"]:
        if s["id"] in sids:
            out.add(s["id"])
            out.update(x["id"] for x in s.get("subsections") or [])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sections", nargs="+")
    ap.add_argument("--langs", default=",".join(LANGS))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--moods", action="store_true", help="translate the Gurudev quotes of these sections (moods.json)")
    a = ap.parse_args()
    langs = a.langs.split(",")
    for sid in a.sections:
        assert sid in GENERATOR, "no generator registered for " + sid
    with cf.ThreadPoolExecutor(len(langs)) as ex:
        if a.moods:
            tg = targets_of(a.sections)
            futs = [ex.submit(run_moods, l, tg, i) for i, l in enumerate(langs)]
        else:
            futs = [ex.submit(run_lang, l, a.sections, i, a.force) for i, l in enumerate(langs)]
        out = dict(f.result() for f in futs)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    # A68 (Codex review 08.10): a FAIL must stop the night release (cron / batch sees exit ≠ 0), never pass silently
    fails = ["%s/%s" % (l, k) for l, r in out.items() for k, v in r.items() if str(v).startswith("FAIL")]
    if fails:
        log("EXIT 1: FAIL in " + ", ".join(fails))
        sys.exit(1)


if __name__ == "__main__":
    main()
