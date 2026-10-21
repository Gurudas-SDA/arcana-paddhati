# -*- coding: utf-8 -*-
"""Back-matter chapter «Заключение» (the conclusion of the book) -> data/book.json, book.ru.json, book.ru-iast.json.

Satkirti's concept (Idea no. 2, msg 5692/5721; chapter in the book — msg 6063/6065): the spiritual culmination of the
book — one day of arcana, from waking the Deities to putting Them to rest, seen through rāgānugā-bhakti: mānasika-sevā
of Śrī Śrī Rādhā-Kṛṣṇa in Sevā-kuñja under the guidance of the senior mañjarī, as heard from rasika-vaiṣṇavas.

Sources in this folder:
  chapter_ru.md   RU master text (Markdown: «## » = subsection, «> » = Gurudev's words verbatim, «> — Шри Према …» =
                  its source line, lines «*IAST*» = verse, «Пословно:» = word-for-word). Sanskrit in IAST.
  quotes.json     every quote in order: Gurudev's English original (`en`), lecture, date, no., timecode, links.
                  RU of the quotes = the book's existing translation or the Academy RU transcript (transcripts/, `fetch`).
  verses_en.json  English translation + word-for-word of the three verses (hand-written).
  en_cache.json   English of the prose (AnyModel cx/gpt-6.1-sol, alt cx/gpt-6-sol), string by string.

  python build.py translate   EN for new/changed prose strings only
  python build.py apply       writes the section into data/book.json, book.ru.json (Cyrillic transliteration of the
                              Sanskrit, as in the other chapters), book.ru-iast.json — the last section, outside the parts
                              (back matter, unnumbered — lib/book.ts sectionNumbers). Other languages: night release.
  python build.py fetch       downloads the Academy transcripts of sources.json (gitignored)
"""
import copy, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import hand_chapter as hc  # noqa: E402
from iast_to_cyrillic import translit  # noqa: E402

SECTION_ID = "conclusion"
TITLE = {"ru": "Заключение", "en": "Conclusion"}
SUBTITLE = {"ru": "Внутреннее видение арчаны", "en": "The Inner Vision of Arcana"}
SUB_IDS = ["conclusion-same-actions", "conclusion-awakening", "conclusion-mangala-arati", "conclusion-morning",
           "conclusion-breakfast", "conclusion-noon", "conclusion-afternoon", "conclusion-evening", "conclusion-night",
           "conclusion-circle"]

SYSTEM = ("You translate the concluding chapter of a Gauḍīya Vaiṣṇava Deity-worship manual from Russian into English for "
          "the book 'Arcana-paddhati — The Process of Deity Worship'. The chapter is contemplative, literary prose: keep its "
          "quiet, warm tone; faithful, natural book English; do not add or omit content. Keep every ⟦…⟧ span exactly as "
          "it is. Sanskrit names and terms in English with IAST diacritics, as in Gauḍīya books: arcana, vaidhī-bhakti, "
          "rāgānugā-bhakti, rasika-vaiṣṇava, mañjarī, sakhī, guru-rūpa-sakhī, kuñja, Sevā-kuñja, Vraja, Vṛndāvana, Yamunā, "
          "Rādhā-kuṇḍa, Yāvaṭa, Nandagrāma, maṅgala-ārati, sandhyā-ārati, dhūpa-ārati, śṛṅgāra-ārati, rāja-bhoga, "
          "mahā-abhiṣeka, bhoga, mahā-prasāda, pūjārī, ācamana, tilaka, cāmara, tāmbūla, khīr, halavā, khichri, sabjī, "
          "purī, Śrīmatī Rādhikā, Svāminī, Lalitā, Śrī Rūpa Mañjarī, Rati Mañjarī, Mother Yaśodā, Śrīla Rūpa Gosvāmī, "
          "Śrīla Raghunātha dāsa Gosvāmī, Śrīla Viśvanātha Cakravartī Ṭhākura, Śrīla Bhaktivinoda Ṭhākura, "
          "Vilāpa-kusumāñjali, Vraja-vilāsa-stava, Upadeśāmṛta, Gaura-ārati, aṣṭa-kālīya-līlā, Śrī Caitanya Mahāprabhu, "
          "Gaurāṅga. «Шри Шри Радха-Кришна» = «Śrī Śrī Rādhā-Kṛṣṇa»; «Гурудев» = «Gurudev» (our spiritual master "
          "Śrī Prem Prayojan Prabhu). Answer with JSON only.")


def norm_quote(t):
    """«…» inside a quotation become „…“ (the quotation itself is put in «…»)."""
    return t.replace("«", "„").replace("»", "“")


def iast_spans(text):
    """*Latin* -> ⟦Latin⟧ (Sanskrit, IAST); *Cyrillic* emphasis -> plain."""
    def rep(m):
        s = m.group(1)
        return "⟦" + s + "⟧" if re.search(r"[A-Za-zāīūṛṝḷṅñṭḍṇśṣṁḥ]", s) else s
    return re.sub(r"\*([^*]+)\*", rep, text)


def parse():
    """chapter_ru.md -> {"intro": [items], "subs": [(title, [items])]}; items: ("text", s) ("verse", sk, tr, wbw)
    ("quote", ru, i) ("src", i)."""
    lines = open(os.path.join(HERE, "chapter_ru.md"), encoding="utf-8").read().split("\n")
    intro, subs, cur = [], [], None
    qi = 0
    paras, buf = [], []
    for ln in lines:  # paragraphs (blank-line separated; a blockquote line on its own)
        if ln.strip() == "":
            if buf:
                paras.append(buf); buf = []
            continue
        buf.append(ln)
    if buf:
        paras.append(buf)
    i = 0
    while i < len(paras):
        p = paras[i]
        first = p[0]
        if first.startswith("# ") or first == "---" or first == "## " + SUBTITLE["ru"]:
            i += 1; continue
        if first.startswith("## "):
            cur = []
            subs.append((first[3:].strip(), cur)); i += 1; continue
        target = intro if cur is None else cur
        if first.startswith("> — "):
            target.append(("src", qi)); qi += 1; i += 1; continue
        if first.startswith(">"):
            att = [x for x in p if x.startswith("> — ")]
            body = iast_spans(" ".join(x[1:].strip() for x in p if x.strip() != ">" and not x.startswith("> — ")).strip())
            target.append(("quote", body, qi))
            if att:
                target.append(("src", qi)); qi += 1
            i += 1; continue
        if all(x.startswith("*") and x.endswith("*") for x in p) and re.search(r"[āīūṛṣṇṭḍśṁḥ]", p[0]):
            sk = "\n".join(x.strip("*") for x in p)
            tr = " ".join(paras[i + 1])
            wbw = " ".join(paras[i + 2])
            assert wbw.startswith("Пословно: "), wbw[:40]
            target.append(("verse", sk, tr, wbw[len("Пословно: "):])); i += 3; continue
        target.append(("text", iast_spans(" ".join(p)))); i += 1
    return {"intro": intro, "subs": subs}


def quotes():
    return json.load(open(os.path.join(HERE, "quotes.json"), encoding="utf-8"))


def src_block(q, lang):
    place = (q.get("place") or {}).get(lang)
    date = q["date"] or ("дата не указана" if lang.startswith("ru") else "date unknown")
    parts = [f"«{q['title']}»" if lang.startswith("ru") else f"“{q['title']}”"]
    if place:
        parts.append(place)
    parts.append(date)
    parts.append(f"№ {q['nr']}" if lang.startswith("ru") else f"no. {q['nr']}")
    parts.append(q["timecode"])
    who = "Шри Према Прайоджана Прабху" if lang.startswith("ru") else "Śrī Prem Prayojan Prabhu"
    return {"type": "sources", "content": "— " + who + ", " + ", ".join(parts),
            "links": [{"transcript_url": q["transcript_url"], "audio_url": q["audio_url"]}]}


def prose_strings(doc):
    out = [TITLE["ru"], SUBTITLE["ru"]]
    for kind in [doc["intro"]] + [it for _, it in doc["subs"]]:
        for it in kind:
            if it[0] == "text":
                out.append(it[1])
    out += [t for t, _ in doc["subs"]]
    return list(dict.fromkeys(out))


def section(lang):
    doc, Q = parse(), quotes()
    verses_en = json.load(open(os.path.join(HERE, "verses_en.json"), encoding="utf-8"))
    en = None
    if lang == "en":
        cache = json.load(open(os.path.join(HERE, "en_cache.json"), encoding="utf-8"))
        en = dict(zip(cache["src"], cache["en"]))
        missing = [s for s in prose_strings(doc) if s not in en]
        assert not missing, "RU changed since translation — run: python build.py translate (%d new)" % len(missing)
    vi = [0]

    def items(lst):
        out = []
        for it in lst:
            if it[0] == "text":
                out.append({"type": "text", "content": en[it[1]] if en else it[1]})
            elif it[0] == "quote":
                q = Q[it[2]]
                txt = "“" + q["en"].strip("“”\"") + "”" if en else "«" + norm_quote(it[1]) + "»"
                out.append({"type": "text", "content": txt})
            elif it[0] == "src":
                out.append(src_block(Q[it[1]], "en" if en else "ru"))
            elif it[0] == "verse":
                v = verses_en[vi[0]]; vi[0] += 1
                assert v["sanskrit"] == it[1], ("verses_en.json out of step", v["sanskrit"][:30])
                out.append({"type": "verse", "sanskrit": it[1], "translation": v["translation"] if en else it[2],
                            "wbw": v["wbw"] if en else it[3]})
        return out

    sec = {"id": SECTION_ID, "title": TITLE["en" if en else "ru"], "subtitle": SUBTITLE["en" if en else "ru"],
           "page": "", "content": items(doc["intro"]),
           "subsections": [{"id": SUB_IDS[k], "title": en[t] if en else t, "content": items(lst)}
                           for k, (t, lst) in enumerate(doc["subs"])]}
    assert len(doc["subs"]) == len(SUB_IDS)
    assert sum(1 for _ in Q) == len([1 for _, lst in doc["subs"] for it in lst if it[0] == "quote"]) + \
        len([1 for it in doc["intro"] if it[0] == "quote"])
    if lang == "ru":
        sec = to_cyr(sec)
    return sec


def to_cyr(sec):
    """Cyrillic edition: Sanskrit of verses, word-for-word words and ⟦…⟧ spans transliterated (as hand_chapter.to_cyr)."""
    s = copy.deepcopy(sec)

    def blocks(bs):
        for b in bs:
            if b["type"] == "verse":
                b["sanskrit"] = translit(b["sanskrit"])
                b["wbw"] = "; ".join((translit(w.split(" — ", 1)[0]) + " — " + w.split(" — ", 1)[1]) if " — " in w else w
                                     for w in b["wbw"].split("; "))
            for k in ("content", "translation"):
                if b.get(k) and isinstance(b[k], str) and b["type"] != "sources":
                    b[k] = hc.map_inline(b[k], translit)

    blocks(s["content"])
    for sub in s["subsections"]:
        blocks(sub["content"])
    return s


def translate():
    sys.path.insert(0, HERE)
    from am import chat
    doc = parse()
    texts = prose_strings(doc)
    cp = os.path.join(HERE, "en_cache.json")
    old = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {"src": [], "en": [], "model": ""}
    known = dict(zip(old["src"], old["en"]))
    todo = [t for t in texts if t not in known]
    models = set()
    for k in range(0, len(todo), 12):
        part = todo[k:k + 12]
        prompt = ("Translate each string of this JSON array from Russian into English. Return a JSON array of the same "
                  "length and order, strings only.\n\n" + json.dumps(part, ensure_ascii=False, indent=0))
        out, model = chat(prompt, system=SYSTEM)
        models.add(model)
        got = json.loads(re.search(r"\[.*\]", out, re.S).group(0))
        assert len(got) == len(part), (len(got), len(part))
        for a, b in zip(part, got):
            assert a.count("⟦") == b.count("⟦"), (a, b)
            known[a] = b
        print("translated", k + len(part), "/", len(todo), "with", model)
    json.dump({"model": ",".join(sorted(models)) or old.get("model", ""), "src": texts, "en": [known[t] for t in texts]},
              open(cp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("EN strings:", len(texts), "new:", len(todo))


def apply():
    for lang, fn in (("en", "book.json"), ("ru", "book.ru.json"), ("ru-iast", "book.ru-iast.json")):
        path = os.path.join(hc.DATA, fn)
        book = json.load(open(path, encoding="utf-8"))
        sec = section(lang)
        ids = [s["id"] for s in book["sections"]]
        if SECTION_ID in ids:
            book["sections"][ids.index(SECTION_ID)] = sec
        else:
            book["sections"].append(sec)
        # always the last section of the book, outside the parts (back matter)
        book["sections"] = [s for s in book["sections"] if s["id"] != SECTION_ID] + [sec]
        for p in book.get("parts", []):
            assert SECTION_ID not in p["sections"]
        hc.write_json(path, book)
        print("wrote", fn)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "translate":
        translate()
    elif cmd == "apply":
        apply()
    elif cmd == "fetch":
        hc.fetch(HERE)
    else:
        print(__doc__)
