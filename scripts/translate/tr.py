# -*- coding: utf-8 -*-
"""Arcana Paddhati translation orchestrator (AnyModel cx/gpt-5.6-sol).

Usage:
  python tr.py glossary [lang ...]      # build glossary.<lang>.json (model draft)
  python tr.py run <lang> [unit ...]    # translate units (cached)
  python tr.py all                      # all langs, all units
  python tr.py assemble                 # write data/book.<lang>.json + validate
The API key is obtained at runtime via pipeline.key_rent and kept in memory only.
"""
import json, os, re, sys, time, subprocess, copy, unicodedata
import requests

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from iast_to_cyrillic import translit  # noqa

PROJ = r"C:\Users\gurud\OneDrive\Dators\Claude code testi\03_Satkirti\Arcana-paddhati\arcana-paddhati"
SRC = os.path.join(PROJ, "data", "book.json")
URL = "https://anymodel.org/v1/chat/completions"
MODEL = "cx/gpt-5.6-sol"
LANGS = ["ru", "lv", "de", "fr", "es", "it", "uk"]
LNAME = {"ru": "Russian", "lv": "Latvian", "de": "German", "fr": "French",
         "es": "Spanish", "it": "Italian", "uk": "Ukrainian"}
CACHE = os.path.join(HERE, "cache")
PLOG = os.path.join(HERE, "progress.log")
IAST_CH = set("āīūṛṝḷḹṅñṭḍṇśṣṁṃḥĀĪŪṚṜḶṄÑṬḌṆŚṢṀṂḤ")

book = json.load(open(SRC, encoding="utf-8"))
_key = None
_key_index = None
PURPOSE = "arcana-translate"
STATS = {"calls": 0, "retries": 0, "errors": [], "tok_in": 0, "tok_out": 0}


def log(msg):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    print(line, flush=True)
    with open(PLOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------------- key ----------------
def get_key():
    global _key, _key_index
    if _key:
        return _key
    r = subprocess.run([sys.executable, "-m", "pipeline.key_rent", "request", "--purpose",
                        PURPOSE, "--wait", "900", "--json"], cwd=r"C:\CA_Pipeline",
                       capture_output=True, text=True, encoding="utf-8")
    out = r.stdout
    i = out.find("{\n")
    if i < 0:
        i = out.rfind("{")
    try:
        d = json.loads(out[i:])
    except Exception:
        log("KEY: cannot parse key_rent output (rc=%s)" % r.returncode)
        sys.exit(2)
    if not d.get("granted"):
        log("KEY: not granted: %s" % (d.get("reason") or d.get("state")))
        sys.exit(3)
    _key = d["key"]
    _key_index = d.get("key_index")
    log("KEY: granted index #%s" % d.get("key_index"))
    return _key


def release_key():
    r = subprocess.run([sys.executable, "-m", "pipeline.key_rent", "release", "--key-index", str(_key_index)], cwd=r"C:\CA_Pipeline",
                       capture_output=True, text=True, encoding="utf-8")
    log("KEY release: " + " ".join(r.stdout.split())[:200])


# ---------------- model call ----------------
def call(messages, max_tokens=32000):
    key = get_key()
    body = {"model": MODEL, "messages": messages, "max_tokens": max_tokens,
            "temperature": 0.2, "response_format": {"type": "json_object"}}
    for attempt in range(4):
        t0 = time.time()
        try:
            STATS["calls"] += 1
            resp = requests.post(URL, headers={"Authorization": "Bearer " + key},
                                 json=body, timeout=600)
            if resp.status_code == 400 and "response_format" in body and "response_format" in resp.text:
                body.pop("response_format")
                continue
            if resp.status_code in (429, 500, 502, 503, 504, 520, 522, 524):
                raise RuntimeError("HTTP %s" % resp.status_code)
            if resp.status_code != 200:
                raise RuntimeError("HTTP %s: %s" % (resp.status_code, resp.text[:300].replace(key, "***")))
            d = resp.json()
            ch = d["choices"][0]
            u = d.get("usage") or {}
            STATS["tok_in"] += u.get("prompt_tokens", 0) or 0
            STATS["tok_out"] += u.get("completion_tokens", 0) or 0
            return ch["message"]["content"] or "", ch.get("finish_reason"), u, time.time() - t0
        except Exception as e:
            msg = str(e).replace(key, "***")[:300]
            STATS["errors"].append(msg)
            STATS["retries"] += 1
            log("  call error (attempt %d): %s" % (attempt + 1, msg))
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("call failed 4x")


# ---------------- extraction ----------------
def units():
    """[(unit_id, [(path, text)])]; path = list of keys into book."""
    res = [("book", [(["title"], book["title"]), (["subtitle"], book["subtitle"])])]
    for si, s in enumerate(book["sections"]):
        items = []
        base = ["sections", si]
        for f in ("title", "subtitle"):
            if s.get(f):
                items.append((base + [f], s[f]))

        def content(pbase, cont):
            for ci, e in enumerate(cont):
                p = pbase + ["content", ci]
                if e["type"] == "verse":
                    if e.get("translation"):
                        items.append((p + ["translation"], e["translation"]))
                elif e["type"] in ("text", "instruction", "subtitle", "list"):
                    if e.get("content"):
                        items.append((p + ["content"], e["content"]))
                elif e["type"] == "image":
                    if e.get("alt"):
                        items.append((p + ["alt"], e["alt"]))
                elif e["type"] == "paired-list":
                    for ii, it in enumerate(e["items"]):
                        for f in ("label", "value"):
                            if it.get(f):
                                items.append((p + ["items", ii, f], it[f]))
                else:
                    raise ValueError("unknown type " + e["type"])
                for extra in e:
                    if extra not in ("type", "sanskrit", "translation", "content", "src", "alt", "items", "layout"):
                        raise ValueError("unknown field %s" % extra)
        content(base, s["content"])
        for j, ss in enumerate(s.get("subsections") or []):
            sb = base + ["subsections", j]
            if ss.get("title"):
                items.append((sb + ["title"], ss["title"]))
            for f in ss:
                if f not in ("id", "title", "content"):
                    raise ValueError("unknown subsection field " + f)
            content(sb, ss["content"])
        res.append((s["id"], items))
    return res


def pkey(path):
    return "/".join(map(str, path))


# ---------------- prompts ----------------
TERM_RULES = {
    "ru": ("Sanskrit terms and names inside Russian prose: write them in the simplified Russian form WITHOUT diacritics, "
           "exactly as in Russian Gaudiya Vaishnava literature and vedabase.io/ru (Кришна, Чайтанья, вайшнав, тилака, "
           "ачаман, Шри Гуру, прасад, Вриндаван). Decline them according to Russian grammar."),
    "uk": ("Sanskrit terms and names inside Ukrainian prose: write them in the Ukrainian DIACRITIC Cyrillic transliteration "
           "used by vedabase.io/uk (e.g. Кр̣шн̣а, Арджуна, бра̄хман̣а, Бгаґавад-ґı̄та̄, праса̄да, Вр̣нда̄вана, Ш́рı̄ Ґуру). Scheme: "
           "a а, ā а̄, i і, ī ı̄ (dotless ı + macron), u у, ū ӯ, ṛ р̣, e е, o о, ai аі, au ау, ṁ м̇, ḥ х̣, k к, kh кх, g ґ, gh ґг, "
           "ṅ н̇, c ч, ch чх, j дж, jh джх, ñ н̃, ṭ т̣, ḍ д̣, ṇ н̣, t т, th тх, d д, dh дг, n н, p п, ph пх, b б, bh бг, m м, "
           "y й, r р, l л, v в, ś ш́, ṣ ш, s с, h х. Inflect them with Ukrainian case endings (Кр̣шн̣и, Кр̣шн̣і). "
           "English words (Deity, devotee, spiritual master...) are translated into Ukrainian per the glossary."),
    "lv": ("Sanskrit terms and names inside Latvian prose: latvianize them according to Latvian phonetics and grammar, "
           "with Latvian case endings (Krišna, vaišnavs, tilaka, āčamana, Višnu, Šrī Guru, Čaitanja, prasāds, Vrindāvana). "
           "Be consistent throughout the book."),
}
for _l in ("de", "fr", "es", "it"):
    TERM_RULES[_l] = ("Sanskrit terms and names inside prose: keep them exactly as in the English source (IAST with diacritics, "
                      "e.g. Kṛṣṇa, ācamana, tilaka, prasāda), as vedabase.io/%s does. Translate the English text naturally." % _l)


def system_prompt(lang, gloss):
    g = "\n".join("- %s → %s" % (k, v) for k, v in gloss.items())
    return f"""You are an expert translator of Gauḍīya Vaiṣṇava literature. You translate "Arcana Paddhati", an English temple manual of Deity worship, into {LNAME[lang]}.
Write natural, literary {LNAME[lang]} in the style of {LNAME[lang]} Gauḍīya Vaiṣṇava publications (terminology as on vedabase.io/{lang if lang!='lv' else 'lv (Latvian Vaishnava publishing practice)'}).

INPUT: a JSON object {{"items":[{{"k":"<id>","t":"<English text>"}}, ...]}}.
OUTPUT: ONLY a JSON object {{"items":[{{"k":"<same id>","t":"<translation>"}}, ...], "new_terms":[{{"en":"<term>","tr":"<your rendering>"}}]}}
- Return EVERY item, same "k", same order, none empty, no extra items.
- "new_terms": up to 15 recurring terms/names from these items that are NOT yet in the glossary, with the rendering you used (may be empty).

RULES
1. If an item's text is entirely a Sanskrit mantra or Sanskrit text (e.g. "oṁ keśavāya namaḥ", "idaṁ āsanam"), return it EXACTLY unchanged (same IAST, same diacritics).
2. Sanskrit mantras, verse fragments or invocations quoted inside prose (e.g. "... while chanting oṁ vāsudevāya namaḥ.", "jaya oṁ viṣṇupāda ... kī jaya") must be kept EXACTLY in IAST and wrapped in the markers ⟦ and ⟧, e.g. ⟦oṁ vāsudevāya namaḥ⟧. Use the markers ONLY for mantras/Sanskrit phrases, not for single terms or names used as words of the sentence.
3. {TERM_RULES[lang]}
4. Preserve line breaks (\\n), punctuation style, bracketed notes, markdown/HTML if present. Do not add or omit content. Do not add explanations.
5. MANDATORY GLOSSARY — use these renderings consistently (inflect as grammar requires):
{g}
"""


def load_gloss(lang):
    p = os.path.join(HERE, "glossary.%s.json" % lang)
    if not os.path.exists(p):
        return {}
    d = json.load(open(p, encoding="utf-8"))
    out = dict(d.get("base", {}))
    for k, v in d.get("extra", {}).items():
        out.setdefault(k, v)
    return out


def add_extra(lang, terms):
    p = os.path.join(HERE, "glossary.%s.json" % lang)
    d = json.load(open(p, encoding="utf-8"))
    base = {k.lower() for k in d.get("base", {})}
    ex = d.setdefault("extra", {})
    n = 0
    for t in terms or []:
        en, tr = (t.get("en") or "").strip(), (t.get("tr") or "").strip()
        if en and tr and en.lower() not in base and en not in ex and len(ex) < 150:
            ex[en] = tr
            n += 1
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return n


# ---------------- translation ----------------
def translate_items(lang, items, label):
    """items: [(k, text)] -> ({k: t}, new_terms). Retries and splitting."""
    gloss = load_gloss(lang)
    payload = {"items": [{"k": k, "t": t} for k, t in items]}
    want = [k for k, _ in items]
    for attempt in range(3):
        content, fin, u, dt = call([
            {"role": "system", "content": system_prompt(lang, gloss)},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
        log("  %s %s try%d: %.0fs fin=%s in=%s out=%s" % (lang, label, attempt + 1, dt, fin,
                                                          u.get("prompt_tokens"), u.get("completion_tokens")))
        if fin == "length":
            break
        try:
            m = re.search(r"\{.*\}", content, re.S)
            d = json.loads(m.group(0))
            got = {}
            for it in d["items"]:
                got[str(it["k"])] = it["t"]
            bad = [k for k in want if not isinstance(got.get(k), str) or not got[k].strip()]
            extra = set(got) - set(want)
            if bad or extra:
                raise ValueError("missing/empty %d, extra %d" % (len(bad), len(extra)))
            if any(got[k].count("⟦") != got[k].count("⟧") for k in want):
                raise ValueError("unbalanced markers")
            return got, d.get("new_terms") or []
        except Exception as e:
            STATS["retries"] += 1
            STATS["errors"].append("%s %s: %s" % (lang, label, e))
            log("  invalid response: %s" % e)
    if len(items) <= 1:
        raise RuntimeError("cannot translate single item %s" % label)
    h = len(items) // 2
    log("  splitting %s into %d + %d" % (label, h, len(items) - h))
    a, ta = translate_items(lang, items[:h], label + "a")
    b, tb = translate_items(lang, items[h:], label + "b")
    a.update(b)
    return a, ta + tb


def run_lang(lang, only=None):
    os.makedirs(os.path.join(CACHE, lang), exist_ok=True)
    for uid, items in units():
        if only and uid not in only:
            continue
        cp = os.path.join(CACHE, lang, uid + ".json")
        if os.path.exists(cp):
            continue
        t0 = time.time()
        short = [("k%d" % i, t) for i, (p, t) in enumerate(items)]
        got, terms = translate_items(lang, short, uid)
        res = {pkey(items[int(k[1:])][0]): v for k, v in got.items()}
        n = add_extra(lang, terms)
        json.dump({"unit": uid, "lang": lang, "items": res, "new_terms": terms},
                  open(cp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        log("DONE %s/%s items=%d %.0fs glossary+%d" % (lang, uid, len(items), time.time() - t0, n))


# ---------------- glossary ----------------
GLOSS_TERMS = """Deity; Deities; Their Lordships; the Lord; Supreme Lord; Supreme Personality of Godhead; spiritual master; Śrī Guru; gurudeva; guru-paramparā (disciplic succession); devotee; Vaiṣṇava; Vaiṣṇavas; pure devotee; offering (noun); to offer; bhoga; naivedya; prasāda; mahā-prasāda; ārati; dhūpa-ārati; obeisances; to offer obeisances; praṇāma; daṇḍavat; paraphernalia; tilaka; ūrdhva-puṇḍra; gopī-candana; ācamana; ācamana-pātra; pañca-pātra; caraṇāmṛta; pūjārī; worship; Deity worship; arcana; mantra; mahā-mantra; chanting (of the holy name); holy name; incense; ghee lamp; cāmara; conch; bell; flower garland; sandalwood paste (candana); tulasī; Tulasī-devī; Kṛṣṇa; Rādhā; Śrīmatī Rādhikā; Rādhā-Kṛṣṇa; Caitanya Mahāprabhu; Nityānanda Prabhu; Gaurāṅga; Viṣṇu; Nārāyaṇa; Śrī; Śrīla; Gosvāmī; Mahārāja; Prabhupāda; Bhaktivedānta; Vṛndāvana; Ganges / Gaṅgā; Yamunā; āsana; snāna (bathing); abhiṣeka; mahā-abhiṣeka; arghya; pādya; madhuparka; transcendental; pastimes (līlā); gopīs; sakhīs; mercy; devotional service (bhakti); eternal servant; dīkṣā (initiation); brāhma-muhūrta; śikhā; Śālagrāma-śilā; Govardhana-śilā; temple; altar; kīrtana; japa; prema; Vaikuṇṭha; Gauḍīya Vaiṣṇava; forgiveness (prayers for); Padma Purāṇa; Śrīmad-Bhāgavatam"""


def build_glossary(lang):
    p = os.path.join(HERE, "glossary.%s.json" % lang)
    if os.path.exists(p):
        log("glossary %s exists" % lang)
        return
    extra = {
        "ru": "Use the forms of the Russian Bhaktivedanta Book Trust editions as on vedabase.io/ru (e.g. Божество, духовный учитель, преданный, поклоны, прасад, арати, ачаман, тилака, пуджари, чаранамрита, Кришна, Вриндаван). No diacritics.",
        "uk": "Use the forms of Ukrainian Vaishnava editions as on vedabase.io/uk (Божество, духовний вчитель, відданий, поклони, прасад, араті, тілака, Крішна, Вріндаван). No diacritics.",
        "lv": "Use Latvian Vaishnava publishing practice: latvianized spelling with Latvian letters and gender/case endings (Krišna, Višnu, vaišnavs, tilaka, āčamana, prasāds, ārati, Šrī Guru, Čaitanja Mahāprabhu, Vrindāvana, garīgais skolotājs, bhakta/Dieva kalps, Dievība, pazemīgi noliekties / godbijības apliecinājumi).",
    }.get(lang, "Use the terminology of the %s Bhaktivedanta Book Trust editions as on vedabase.io/%s. Sanskrit words stay in IAST with diacritics exactly as in the English source (Kṛṣṇa, ācamana, prasāda); translate the English words (Deity, spiritual master, devotee, obeisances, paraphernalia, offering...) with the established %s Vaishnava equivalents." % (LNAME[lang], lang, LNAME[lang]))
    msg = [{"role": "system", "content": "You are an expert in Gauḍīya Vaiṣṇava terminology in %s. Output only JSON." % LNAME[lang]},
           {"role": "user", "content": "Create a translation glossary English→%s for a Deity-worship manual. %s\nFor each term give the canonical dictionary (nominative) form. Return {\"base\": {\"<English term as given>\": \"<%s form>\"}}.\nTerms: %s" % (LNAME[lang], extra, LNAME[lang], GLOSS_TERMS)}]
    content, fin, u, dt = call(msg, 8000)
    d = json.loads(re.search(r"\{.*\}", content, re.S).group(0))
    d.setdefault("extra", {})
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log("glossary %s: %d terms %.0fs" % (lang, len(d["base"]), dt))


# ---------------- assembly ----------------
MARK = re.compile(r"⟦(.*?)⟧", re.S)


def has_iast(s):
    return any(c in IAST_CH for c in s)


def get_in(o, path):
    for p in path:
        o = o[p]
    return o


def set_in(o, path, v):
    for p in path[:-1]:
        o = o[p]
    o[path[-1]] = v


def finalize(lang, text, src, cyr):
    """Apply marker / mantra rules. cyr=True -> Russian Cyrillic translit."""
    if text == src and has_iast(src) and cyr:
        return translit(src)
    if cyr:
        return MARK.sub(lambda m: translit(m.group(1)), text)
    return MARK.sub(lambda m: m.group(1), text)


def build(lang):
    """Returns dict of variant-> book. lang 'ru' gives ru and ru-iast."""
    tr = {}
    for uid, _ in units():
        cp = os.path.join(CACHE, lang, uid + ".json")
        tr.update(json.load(open(cp, encoding="utf-8"))["items"])
    variants = {"ru": [("ru", True), ("ru-iast", False)]}.get(lang, [(lang, False)])
    out = {}
    for name, cyr in variants:
        b = copy.deepcopy(book)
        for uid, items in units():
            for path, src in items:
                set_in(b, path, finalize(lang, tr[pkey(path)], src, cyr))
        if cyr:
            def walk(o):
                if isinstance(o, dict):
                    for k, v in o.items():
                        if k == "sanskrit" and isinstance(v, str):
                            o[k] = translit(v)
                        else:
                            walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)
            walk(b)
        out[name] = b
    return out


def struct_eq(a, b, tpath=""):
    errs = []
    if type(a) != type(b):
        return ["type %s" % tpath]
    if isinstance(a, dict):
        if list(a.keys()) != list(b.keys()):
            errs.append("keys %s" % tpath)
        for k in a:
            if k in b:
                if k in ("id", "type", "src", "layout", "page") and a[k] != b[k]:
                    errs.append("value %s/%s" % (tpath, k))
                errs += struct_eq(a[k], b[k], tpath + "/" + k)
    elif isinstance(a, list):
        if len(a) != len(b):
            errs.append("len %s" % tpath)
        for i, (x, y) in enumerate(zip(a, b)):
            errs += struct_eq(x, y, "%s/%d" % (tpath, i))
    return errs


def iter_sanskrit(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "sanskrit":
                yield path + "/sanskrit", v
            else:
                yield from iter_sanskrit(v, path + "/" + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from iter_sanskrit(v, "%s/%d" % (path, i))


def assemble():
    rep = []
    allb = {}
    for lang in LANGS:
        allb.update(build(lang))
    src_s = dict(iter_sanskrit(book))
    U = units()
    for name, b in allb.items():
        e = struct_eq(book, b)
        rep.append("[%s] structure: %s" % (name, "OK" if not e else "FAIL %d %s" % (len(e), e[:5])))
        s = dict(iter_sanskrit(b))
        if name == "ru":
            lat = [p for p, v in s.items() if v is not None and re.search(r"[a-zA-Z]", v)]
            rep.append("[ru] sanskrit fields with latin letters: %d" % len(lat))
        else:
            diff = [p for p in src_s if src_s[p] != s.get(p)]
            rep.append("[%s] sanskrit byte-identical: %s" % (name, "OK" if not diff else "FAIL %d" % len(diff)))
        marks = [pkey(p) for _, items in U for p, _ in items if "⟦" in get_in(b, p) or "⟧" in get_in(b, p)]
        rep.append("[%s] leftover markers: %d" % (name, len(marks)))
        same = [(pkey(p), t) for _, items in U for p, t in items if get_in(b, p) == t]
        rep.append("[%s] fields identical to English: %d" % (name, len(same)))
        for p, t in same:
            rep.append("      = %s | %s" % (p, t[:80].replace("\n", " / ")))
        if name in ("ru", "uk"):
            # Latin letters left in Cyrillic prose outside mantra-derived text
            lat = []
            for _, items in U:
                for p, t in items:
                    v = get_in(b, p)
                    if v != t and re.search(r"[A-Za-zāīūṛṣśṇṭḍṁḥ]{3,}", MARK.sub("", v)):
                        lat.append((pkey(p), re.findall(r"[A-Za-zĀ-ſḀ-ỿ'-]{3,}", v)[:6]))
            rep.append("[%s] translated fields still containing Latin words: %d" % (name, len(lat)))
            for p, w in lat[:60]:
                rep.append("      ~ %s %s" % (p, w))
    # ru vs ru-iast differ only in sanskrit/mantra fields
    ru, ri = allb["ru"], allb["ru-iast"]
    trr = {}
    for uid, _ in U:
        trr.update(json.load(open(os.path.join(CACHE, "ru", uid + ".json"), encoding="utf-8"))["items"])
    bad = []
    for _, items in U:
        for p, t in items:
            a, c = get_in(ru, p), get_in(ri, p)
            raw = trr[pkey(p)]
            if a != c and not (raw == t or "⟦" in raw):
                bad.append(pkey(p))
    rep.append("[ru vs ru-iast] differences outside sanskrit/mantra fields: %d %s" % (len(bad), bad[:5]))
    ok = all("FAIL" not in r for r in rep)
    for name, b in allb.items():
        json.dump(b, open(os.path.join(PROJ, "data", "book.%s.json" % name), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    open(os.path.join(HERE, "validation.txt"), "w", encoding="utf-8").write("\n".join(rep))
    print("\n".join(r for r in rep if not r.startswith("      ")))
    print("ALL OK" if ok else "HAS FAILURES")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd in ("run", "glossary") and len(sys.argv) > 2 and len(sys.argv[2]) == 2:
        PURPOSE = "arcana-" + sys.argv[2]
    try:
        if cmd == "glossary":
            for l in (sys.argv[2:] or LANGS):
                build_glossary(l)
        elif cmd == "run":
            run_lang(sys.argv[2], sys.argv[3:] or None)
        elif cmd == "all":
            for l in LANGS:
                run_lang(l)
        elif cmd == "assemble":
            assemble()
        elif cmd == "units":
            for u, it in units():
                print(u, len(it), sum(len(t) for _, t in it))
    finally:
        if _key:
            release_key()
        if cmd != "units" and cmd != "assemble":
            log("STATS calls=%d retries=%d tok_in=%d tok_out=%d errors=%d" % (
                STATS["calls"], STATS["retries"], STATS["tok_in"], STATS["tok_out"], len(STATS["errors"])))
