# -*- coding: utf-8 -*-
"""A new language of the book (A73, Gurudas 10.10.2026: pt + lt) — the whole book translated with the night-sync
translator (night_sync.py: AnyModel cx/gpt-6.1-sol, fallback cx/gpt-6-sol, logged; both failing -> stop + report).

Same source and rules as the nightly sync of the other languages: the ENGLISH book (data/book.json) section by
section; verse `sanskrit` (IAST), ids, src, numbers byte-identical; word-by-word meanings translated with the
Sanskrit words unchanged; Gurudev's quotes (moods.json) translated and put in by scripts/moods/apply_moods.py.
Terms: glossary.<lang>.json (from the BBT editions on vedabase.io) + TERM_RULES in night_sync.py.

    python scripts/translate/new_lang.py pt,lt --keys 0,1        # one AnyModel key per language, in parallel
    python scripts/translate/new_lang.py pt --sections introduction   # a single section first (test)
    python scripts/translate/new_lang.py pt,lt --assemble-only

Steps per language (resumable, cache: scripts/translate/cache/<lang>/ns_<section>.json, git-ignored):
  1. every English section -> translate_section(); a generator section (night_sync.GENERATOR) is also saved
     into <generator>/i18n.json, so a later rebuild of that generator keeps the language;
  2. book subtitle, part titles, ch13 part/fallback note (scripts/chapters/ch13_caturmasya/i18n_cache.json);
  3. data/ui.<lang>.json (every key of ui.en.json, {placeholders} kept);
  4. Gurudev's quotes -> moods.json; 5. data/book.<lang>.json written, apply_moods.py run.
Keys: C:\\Users\\gurud\\.credentials\\ca_pipeline\\config.ini [anymodel] key_* (never printed).
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import night_sync as ns  # noqa: E402
from i18n_sections import en_hash, write_atomic  # noqa: E402

CACHE = os.path.join(HERE, "cache")
CH13 = os.path.join(ns.REPO, "scripts", "chapters", "ch13_caturmasya", "i18n_cache.json")
PH = re.compile(r"\{[a-zA-Z]+\}")


def cpath(lang, name):
    os.makedirs(os.path.join(CACHE, lang), exist_ok=True)
    return os.path.join(CACHE, lang, "ns_%s.json" % name)


def translate_sections(lang, sids, key_i):
    res = {}
    for sid in sids:
        es = next(s for s in ns.EN["sections"] if s["id"] == sid)
        p = cpath(lang, sid)
        if os.path.exists(p) and json.load(open(p, encoding="utf-8"))["en_hash"] == en_hash(es):
            res[sid] = "cached"
            continue
        t0 = time.time()
        try:
            rec = ns.translate_section(lang, sid, key_i)
        except Exception as e:  # noqa: BLE001
            ns.log("FAIL %s/%s: %s" % (lang, sid, e))
            res[sid] = "FAIL %s" % e
            if "all models failed" in str(e):
                ns.log("STOP %s: both models failed" % lang)
                break
            continue
        write_atomic(p, json.dumps(rec, ensure_ascii=False, indent=1) + "\n", newline="\n")
        if sid in ns.GENERATOR:
            ns.save(sid, lang, rec)
        res[sid] = "ok " + rec["model"]
        ns.log("DONE %s/%s %.0fs model=%s" % (lang, sid, time.time() - t0, rec["model"]))
    return res


def translate_meta(lang, key_i):
    p = cpath(lang, "_meta")
    if os.path.exists(p):
        return "cached"
    items = [("subtitle", ns.EN["subtitle"]), ("ch13part", "Festivals and Vows")]
    items += [("part:" + x["id"], x["title"]) for x in ns.EN["parts"]]
    got = ns.translate_items(lang, items, key_i, "meta")
    write_atomic(p, json.dumps(got, ensure_ascii=False, indent=1) + "\n", newline="\n")
    return "ok"


def ui_prompt(lang):
    gl = ns.load_gloss(lang)
    g = "\n".join("- %s → %s" % (k, v) for k, v in list(gl.items())[:120])
    return (f"Translate the UI strings of a website (the book app «Arcana-paddhati», a Vaiṣṇava Deity-worship manual) from "
            f"English into {ns.LNAME[lang]}. Return ONLY a JSON object with exactly the same keys. Rules: keep every "
            "{placeholder} exactly as is; keep the product name 'Arcana-paddhati' unchanged; keep the brand name 'Chrome'; "
            f"use the standard labels that iOS/Android show in {ns.LNAME[lang]} for 'Share', 'Add to Home Screen', 'Add', "
            "'Open in Browser'; keep quotation marks where the English has them; short, natural UI wording; 'Gurudev' "
            "is a name. Key 'language.fallbackSuffix' stays '(EN)'.\nGLOSSARY:\n" + g)


def translate_ui(lang, key_i):
    path = os.path.join(ns.DATA, "ui.%s.json" % lang)
    src = json.load(open(os.path.join(ns.DATA, "ui.en.json"), encoding="utf-8"))
    if os.path.exists(path) and set(json.load(open(path, encoding="utf-8"))) == set(src):
        return "cached"
    for attempt in range(3):
        content, model = ns.call(lang, [{"role": "system", "content": ui_prompt(lang)},
                                        {"role": "user", "content": json.dumps(src, ensure_ascii=False, indent=1)}],
                                 key_i + attempt, max_tokens=8000)
        try:
            out = ns.parse_json(content)
            bad = [k for k in src if not isinstance(out.get(k), str) or not out[k].strip()
                   or sorted(PH.findall(src[k])) != sorted(PH.findall(out[k]))]
            if bad or set(out) - set(src):
                raise ValueError("keys/placeholders bad=%s extra=%s" % (bad, sorted(set(out) - set(src))))
            out["language.fallbackSuffix"] = src["language.fallbackSuffix"]
            write_atomic(path, json.dumps({k: out[k] for k in src}, ensure_ascii=False, indent=2) + "\n", newline="\n")
            return "ok " + model
        except Exception as e:  # noqa: BLE001
            ns.log("  %s ui invalid (try %d): %s" % (lang, attempt + 1, e))
    raise RuntimeError("%s ui: cannot translate" % lang)


# Reviewed wording (A73 sample check 10.10): a few machine renderings replaced, applied on every run
# (pt «humor» = BBT pt-br word for «mood», as the book text itself uses it).
UI_FIX = {"pt": {"mood.button": "O humor de Gurudev", "sidebar.contents": "Sumário",
                 "reader.contents": "Sumário", "group.contents": "Sumário da introdução"}}
TITLE_FIX = {"lt": {"Mantrų, skirtų pagerbti caraṇāmṛtą": "Mantros caraṇāmṛtai pagerbti",
                    "Bhajans Kārtikai": "Kārtikos bhajanai",
                    "Viešpaties Caitanya ir Śrī Śrī Rādhā-Kṛṣṇos garbinimas šešiolika reikmenų":
                        "Viešpaties Caitanya ir Śrī Śrī Rādhā-Kṛṣṇos garbinimas su šešiolika reikmenų",
                    "Šventės, įžadai ir ārati dainos": "Šventės, įžadai ir ārati giesmės"}}


def fix_ui(lang):
    path = os.path.join(ns.DATA, "ui.%s.json" % lang)
    ui = json.load(open(path, encoding="utf-8"))
    ui.update(UI_FIX.get(lang, {}))
    write_atomic(path, json.dumps(ui, ensure_ascii=False, indent=2) + "\n", newline="\n")


def assemble(lang):
    import copy
    meta = json.load(open(cpath(lang, "_meta"), encoding="utf-8"))
    secs = []
    for s in ns.EN["sections"]:
        rec = json.load(open(cpath(lang, s["id"]), encoding="utf-8"))
        if rec["en_hash"] != en_hash(s):
            raise RuntimeError("%s/%s: STALE translation (English changed) - re-run" % (lang, s["id"]))
        sec = rec["section"]
        sec["title"] = TITLE_FIX.get(lang, {}).get(sec["title"], sec["title"])
        secs.append(sec)
    parts = copy.deepcopy(ns.EN["parts"])
    for x in parts:
        x["title"] = TITLE_FIX.get(lang, {}).get(meta["part:" + x["id"]], meta["part:" + x["id"]])
    fix_ui(lang)
    book = {"title": "Arcana Paddhati", "subtitle": meta["subtitle"], "parts": parts, "sections": secs}
    write_atomic(os.path.join(ns.DATA, "book.%s.json" % lang), json.dumps(book, ensure_ascii=False, indent=2) + "\n",
                 newline="\n")
    # ch13 generator: part title + fallback note of the language (its apply() needs them)
    ui = json.load(open(os.path.join(ns.DATA, "ui.%s.json" % lang), encoding="utf-8"))
    c = json.load(open(CH13, encoding="utf-8"))
    c["i18n"][lang] = {"part": meta["ch13part"], "note": ui["section.fallback"]}
    write_atomic(CH13, json.dumps(c, ensure_ascii=False, indent=1), newline="")
    return "book.%s.json: %d sections" % (lang, len(secs))


def run(lang, key_i, sids, assemble_only):
    out = {}
    if not assemble_only:
        out["sections"] = translate_sections(lang, sids, key_i)
        if any(str(v).startswith("FAIL") for v in out["sections"].values()):
            return lang, out
        if sids == [s["id"] for s in ns.EN["sections"]]:
            out["meta"] = translate_meta(lang, key_i)
            out["ui"] = translate_ui(lang, key_i)
            out["moods"] = ns.run_moods(lang, ns.targets_of(sids), key_i)[1]["moods"]
    return lang, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("langs")
    ap.add_argument("--keys", default="", help="key index per language, same order (e.g. 0,1)")
    ap.add_argument("--sections", default="")
    ap.add_argument("--assemble-only", action="store_true")
    a = ap.parse_args()
    langs = a.langs.split(",")
    for l in langs:
        assert l in ns.LANGS and l in ns.TERM_RULES, "unknown language " + l
    if a.keys:
        ks = [int(x) for x in a.keys.split(",")]
        assert len(ks) == len(langs) and len(set(ks)) == len(ks) and max(ks) < len(ns.KEYS), "bad --keys"
        ns.KEY_PIN.update(dict(zip(langs, ks)))
    ns.log("new_lang %s keys=%s models=%s (%d keys available)" % (langs, a.keys or "rotating", ns.MODELS, len(ns.KEYS)))
    sids = a.sections.split(",") if a.sections else [s["id"] for s in ns.EN["sections"]]
    with cf.ThreadPoolExecutor(len(langs)) as ex:
        futs = [ex.submit(run, l, i * 3, sids, a.assemble_only) for i, l in enumerate(langs)]
        out = dict(f.result() for f in futs)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    fails = ["%s/%s" % (l, k) for l, r in out.items() for k, v in (r.get("sections") or {}).items() if str(v).startswith("FAIL")]
    if fails:
        ns.log("EXIT 1: FAIL in " + ", ".join(fails))
        sys.exit(1)
    if not a.sections:
        for l in langs:
            print(assemble(l))
        r = subprocess.run([sys.executable, os.path.join(ns.REPO, "scripts", "moods", "apply_moods.py")],
                           capture_output=True, text=True, encoding="utf-8")
        print(r.stdout[-800:], r.stderr[-800:])
        if r.returncode:
            sys.exit(r.returncode)
    if ns.USED_MODEL:
        ns.log("NOTE fallback model used: %s" % ns.USED_MODEL)


if __name__ == "__main__":
    main()
