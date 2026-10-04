# -*- coding: utf-8 -*-
"""Chapter 13 «Настроение Гурудева» blocks -> scripts/moods/moods.json (then run scripts/moods/apply_moods.py).

EN = verbatim from the Academy transcript; RU = the Academy's own Russian transcript of the same lines (no machine
translation). Quotes are cut from transcripts/<nr>_{en,ru}.txt (gitignored; `python moods_ch13.py fetch` downloads
them from the Drive links in sources.json). Line i of the EN file corresponds to line i of the RU file.
  python moods_ch13.py fetch    # download missing transcripts
  python moods_ch13.py          # replace the chapter-13 entries in moods.json (idempotent)
"""
import io, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
MOODS = os.path.normpath(os.path.join(HERE, "..", "..", "moods", "moods.json"))
TR = os.path.join(HERE, "transcripts")
META = json.load(open(os.path.join(HERE, "sources.json"), encoding="utf-8"))

# transcript file names (= lecture titles in the Academy archive, without the EN_/RU_ prefix)
TITLES = {
    "9643": "Śayana Ekādaśī & Bhakti Vijñana Bharati Maharaja's Appearance Day - 2025-07-06 - Sri Prem Prayojan",
    "6557": "Istagosthi - Guru-Tattva - 2022-07-13 - Sri Prem Prayojan",
    "5601": "Day 3 - Sri Damodarashtakam part 1 - 2020-11-02 - Sri Prem Prayojan",
    "9183": "2025.10.10_Kartik evening 1st Vers Damodarastakam",
    "8032": "Glory of Kartika Month - 2024-10-16 - Sri Prem Prayojan",
    "10176": "2026.05.22_Purusottama Mas & Glory of Mahaprasadam_1",
    "3535": "Sri Prem Prayojan - 2018-10-23 - Introduction into Vraja Mandala Parikrama",
    "8943": "Q&A Radhika's Favourite Raga, Chaturmasya and Sphurti - 2025-04-05 - Sri PremPrayojan",
    "5994": "2021.07.26 Q&A - Next Acharya, Jat Gosai, Chaturmasya, Hemalata, Nirupadhi, Recordings, Pancharatra",
    "8942": "Q&A Prasadam, Chaturmasya and Japa - 2025-04-05 - Sri Prem Prayojan",
}


def fetch():
    import requests, docx
    os.makedirs(TR, exist_ok=True)
    for nr, x in META.items():
        for lang in ("en", "ru"):
            p = os.path.join(TR, f"{nr}_{lang}.txt")
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


def para(nr, lang, i):
    t = open(os.path.join(TR, f"{nr}_{lang}.txt"), encoding="utf-8").read().split("\n")[i]
    return re.sub(r"^\[\d\d:\d\d:\d\d\]\s*", "", t).strip()


def cut(text, start=None, end=None):
    if start:
        text = text[text.index(start):]
    if end:
        text = text[:text.index(end) + len(end)]
    return text.strip()


def piece(nr, ts, spec, join="\n\n"):
    """spec: list of (line index, en_start, en_end, ru_start, ru_end); index None = "[…]".
    join: separator between consecutive lines (" " = one paragraph)."""
    en = join.join("[…]" if i is None else cut(para(nr, "en", i), a, b) for i, a, b, c, d in spec)
    ru = join.join("[…]" if i is None else cut(para(nr, "ru", i), c, d) for i, a, b, c, d in spec)
    x = META[nr]
    src = {"title": TITLES[nr], "date": x["date"].replace(".", "-"), "nr": nr, "timecode": ts,
           "transcript_url": x.get("script_en_url") or "", "audio_url": x.get("dwnld_url") or ""}
    return en, ru, src


def entry(target, main, more=()):
    en, ru, src = main
    e = {"target": target, "candidate": "PartIV", "quote": en, "translations": {"ru": ru, "ru-iast": ru},
         "machine": [], "source": src}
    if more:
        e["more"] = [{"candidate": "PartIV", "label": "", "quote": a, "translation": {"ru": b, "ru-iast": b},
                      "machine": [], "source": s} for a, b, s in more]
    return e


def new_entries():
    return [
        entry("caturmasya-period",
              piece("9643", "00:22:52", [(7, "So many persons they begin", None, "Многие начинают", None)]),
              [piece("6557", "00:00:21", [(7, None, None, None, None), (8, None, None, None, None)])]),
        entry("caturmasya-vows",
              piece("6557", "00:04:50", [(10, None, None, None, None)]),
              [piece("8943", "00:01:24", [(36, None, None, None, None)])]),
        entry("brahmacari-sannyasi-vows",
              piece("8943", "00:04:16", [(37, "Now, you have to understand this.", None, "Теперь вы должны это понять.", None)]),
              [piece("5994", "00:26:20", [(78, "So in Cāturmāsya, the brahmacārīs", None, "В Чатурмасью брахмачари", None),
                                          (79, None, None, None, None)]),
               piece("6557", "00:02:45", [(9, None, None, None, None)])]),
        entry("kartika-niyama-seva",
              piece("5601", "00:04:17", [(19, None, None, None, None), (20, None, None, None, None)]),
              [piece("9183", "00:04:00", [(20, "So, actually, the Kārtika-vrata", None, "Итак, на самом деле", None)]),
               piece("8032", "00:15:16", [(106, None, None, None, None)]),
               # 8942, transcript block from 00:11:11: "...at least you must follow the month of Kārtika"
               piece("8942", "00:11:11", [(i, None, None, None, None) for i in (205, 206, 207, 208)], join=" ")]),
        entry("purusottama-masa",
              piece("10176", "00:18:40", [(62, "So then Śrī Kṛṣṇa said to Lord Nārāyaṇa", None, "Тогда Шри Кришна сказал Господу Нараяне", None),
                                          (None, None, None, None, None),
                                          (63, 'Krishna said, "Sometimes', None, "Кришна сказал: «Иногда", None)]),
              [piece("3535", "00:05:08", [(26, "I remember once", "more rādhā-pakṣa than to Himself.",
                                           "Помню, однажды", "чем предан Ему Самому.")])]),
    ]


if __name__ == "__main__":
    if sys.argv[1:] == ["fetch"]:
        fetch()
        sys.exit()
    NEW = new_entries()
    moods = json.load(open(MOODS, encoding="utf-8"))
    targets = {e["target"] for e in NEW}
    # keep the position of existing entries; append targets that are new
    out = [next(e for e in NEW if e["target"] == m["target"]) if m["target"] in targets else m for m in moods]
    out += [e for e in NEW if e["target"] not in {m["target"] for m in moods}]
    raw = open(MOODS, encoding="utf-8", newline="").read()
    nl = "\n" if raw.endswith("\n") else ""
    open(MOODS, "w", encoding="utf-8", newline="").write(json.dumps(out, ensure_ascii=False, indent=2) + nl)
    for e in NEW:
        print("==", e["target"], e["source"]["nr"], e["source"]["timecode"], "| more:", [m["source"]["nr"] for m in e.get("more", [])])
