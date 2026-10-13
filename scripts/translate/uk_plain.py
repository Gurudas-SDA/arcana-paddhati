# -*- coding: utf-8 -*-
"""A80 (Satkirti 12.10.2026 23:00, msg 2615): Ukrainian text is written like krishna.ua - Sanskrit names and
terms inside Ukrainian prose WITHOUT diacritics (no dots/lines above or under letters), with full letters.

Rules (Arcana-paddhati/Правила украинского написания (krishna.ua).md):
  а̄→а, ı̄/ı→і, ӯ→у; ṛ (р̣)→рі (Крішна, Шрімад, Вріндаван); ś/ṣ→ш; ṁ/ṅ/ñ/ṇ→м/н; ḥ→х;
  ṭh (т̣г/т̣х)→тх (Тхакур); jñ (джн̃)→гья (ягья, Прагьяна); ai (аі)→ай (вайшнав, Чайтанья);
  consonant+y+vowel → ь+я/ю/є (Нітьянанда, Чайтанья), after б/п/в/м/ф/р → ’я (Ачар’я, В’ясадева);
  y+vowel after a vowel or at the start → я/ю/є/ї (Нараяна, Яшода). bh=бг, dh=дг, gh=ґг, g=ґ stay.
Only Cyrillic words are changed; Latin IAST (verses, word-by-word Sanskrit, inline mantras) is never touched.

    python scripts/translate/uk_plain.py            # convert all Ukrainian targets in place
    python scripts/translate/uk_plain.py --check    # count what would change (exit 1 if anything)
"""
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))

CYR = "А-Яа-яІіЇїЄєҐґЁё"
# a Cyrillic "word": letters, dotless ı, combining marks, apostrophes inside
WORD = re.compile(f"[{CYR}ıӯӮӣӢӀӏ][{CYR}ıӯӮӣӢӀӏ̀-ͯ’ʼ']*")
VOW = "аеєиіїоуюяАЕЄИІЇОУЮЯ"
CONS = "бвгґджзклмнпрстфхцчшщБВГҐДЖЗКЛМНПРСТФХЦЧШЩ"
LABIAL_R = "бпвмфрБПВМФР"
IOT = {"а": "я", "у": "ю", "е": "є", "і": "ї", "и": "ї", "А": "Я", "У": "Ю", "Е": "Є", "І": "Ї", "И": "Ї"}
APO = "’"


def extra_marks(s):
    """combining marks that are NOT part of й/ї/ё + dotless ı + ӯ/ӣ (= «лишние точки и линии»)."""
    n = 0
    for ch in unicodedata.normalize("NFC", s):
        if ch in "ıӯӮӣӢӀӏ":
            n += 1
        elif 0x300 <= ord(ch) <= 0x36F:
            n += 1
    return n


ASP = re.compile("(?<=[а-яіґ])(тг|кг|пг|чг)(?=[аеіиоуя])", re.I)   # th/kh/ph/ch written with «г» (scheme: тх/кх/пх/чх)
FIX = {"Брагмачарі": "Брахмачарі", "панчакамы": "панчаками"}        # single source typos (Russian «ы», h=г)
LAT = {"ā": "а", "ī": "і", "ū": "у", "Ā": "А", "Ī": "І", "Ū": "У", "Ӏ": "І", "ӏ": "і"}
LAT_IN_CYR = re.compile(f"(?<=[{CYR}ı])[āīūĀĪŪӀӏ]|[āīūĀĪŪӀӏ](?=[{CYR}ı])")


def is_sanskrit_word(w):
    """a Cyrillic word written in the diacritic Sanskrit scheme (or with its traces)."""
    if extra_marks(w) or "ы" in w or ASP.search(w) or re.search("[Дд]жн", w):
        return True
    if re.search("[аА]і", w):           # ai written «аі» (Ukrainian never has «аі»: it is «аї»)
        return True
    if re.search(f"[{CONS}]й[аеуіи]", w):  # consonant + y + vowel («Нітйананда», «Чаітанйа»)
        return True
    if re.search(f"(^|[{VOW}])[Йй][аеуі]", w):  # y + vowel (Ukrainian writes я/ю/є/ї): «йантра», «Майа»
        return True
    return False


def plain_word(w):
    s = unicodedata.normalize("NFC", w)
    s = s.replace("ӯ", "у").replace("Ӯ", "У").replace("ӣ", "і").replace("Ӣ", "І").replace("Ӏ", "І").replace("ӏ", "і")
    s = re.sub("аі", "ай", s)
    s = re.sub("Аі", "Ай", s)
    s = s.replace("ı", "і")
    s = unicodedata.normalize("NFD", s)
    # jñ -> гья
    s = re.sub("Дж(?=н̃)н̃", "Гй", s)
    s = re.sub("дж(?=н̃)н̃", "гй", s)
    # ṭh / ḍh
    s = re.sub("([Тт])̣[гх]", lambda m: m.group(1) + "х", s)
    # aspirated stems keep their letters in the dative/locative: Ра̄дзі -> Радгі, Мат̣сі -> Матхі, Раґгуна̄тзі -> Раґгунатхі
    s = re.sub("([Тт])̣[зс](?=[іı])", lambda m: m.group(1) + "х", s)
    s = re.sub("([Тт])з(?=[іı])", lambda m: m.group(1) + "х", s)
    s = re.sub("([Дд])з(?=[іı])", lambda m: m.group(1) + "г", s)
    # vocalic ṛ, ṝ, ḷ (only after a consonant or at the start; «Паур̣н̣ама̄сı̄» = Paurṇamāsī -> р)
    s = re.sub(f"(^|[^{VOW}])([Рр])̣̄?", lambda m: m.group(1) + m.group(2) + "і", s)
    s = s.replace("р̣", "р")
    s = re.sub("([Лл])̣̄?", lambda m: m.group(1) + "і", s)
    # re-compose й/ї/ё, then drop every remaining combining mark
    s = unicodedata.normalize("NFC", s)
    s = "".join(ch for ch in s if not (0x300 <= ord(ch) <= 0x36F))
    s = s.replace("аі", "ай")                       # ā+i: «Ніта̄і» -> Нітай (krishna.ua «Гаура-Нітай»)
    # y-glides
    def glide(m):
        prev, v = m.group(1), m.group(2)
        if prev in LABIAL_R:
            return prev + APO + IOT[v]
        # 13.10 (Пурохита, по правилу krishna.ua): ’ only after б, п, в, м, ф, р; after ч/ш/ж/щ it is «ь» (Ачьюта, Вайшья)
        return prev + "ь" + IOT[v]
    s = ASP.sub(lambda m: m.group(1)[0] + ("Х" if m.group(1)[1] == "Г" else "х"), s)
    s = re.sub("(?<=[Дд]ж)г(?=[аеіиоуя])", "х", s)  # jh: Джгулана -> Джхулана
    s = re.sub("([Дд])жн[яа]", lambda m: ("Г" if m.group(1) == "Д" else "г") + "ья", s)   # «Праджняні» -> Прагьяні
    s = FIX.get(s, s)
    s = re.sub("йй([аеуі])", lambda m: "й" + IOT[m.group(1)], s)   # «Ваійа̄сакі» -> Вайясакі
    s = re.sub(f"([{CONS}])й([аеуіи])", glide, s)
    s = re.sub(f"(^|[{VOW}’ʼ'\\-])([Йй])([аеуіАЕУІ])",
               lambda m: m.group(1) + (IOT[m.group(3)] if m.group(2) == "й" else IOT[m.group(3).upper()]), s)
    return s


# Russian-style spellings without diacritics -> krishna.ua forms (Кришна -> Крішна, Шри -> Шрі, Радха -> Радга, Гуру -> Ґуру)
NB = "(?<![А-Яа-яІіЇїЄєҐґ’'])"   # word start
VARIANTS = [
    (re.compile(NB + "Шримат[иі](?![а-яіїєґ])"), "Шріматі"),
    (re.compile(NB + "Шри(?!ф)"), "Шрі"),
    (re.compile("Кришн"), "Крішн"),
    (re.compile(NB + "Радх"), "Радг"),
    (re.compile("Мадхав"), "Мадгав"),
    (re.compile(NB + "Госвам[иі](?![а-яіїєґ])"), "Ґосвамі"),
    (re.compile(NB + "[ГҐ]ауранг"), "Ґауранґ"),
    (re.compile(NB + "Гаур"), "Ґаур"),
    (re.compile(NB + "Говінд"), "Ґовінд"),
    (re.compile(NB + "Гуру"), "Ґуру"),
    (re.compile(NB + "гуру"), "ґуру"),
    (re.compile(NB + "гопі"), "ґопі"),
    (re.compile(NB + "Гопі"), "Ґопі"),
    (re.compile("Вриндаван"), "Вріндаван"),
    (re.compile(NB + "врикш"), "врікш"),
    (re.compile("Вришабган"), "Врішабган"),
    (re.compile("Хришикеш"), "Хрішікеш"),
    (re.compile("Пундарикакш"), "Пундарікакш"),
    (re.compile("Шачимат"), "Шачімат"),
    (re.compile(NB + "Сарасвати(?![а-яіїєґ])"), "Сарасваті"),
    (re.compile(NB + "Йамун"), "Ямун"),
    (re.compile(NB + "Йашод"), "Яшод"),
    (re.compile(NB + "Йадав"), "Ядав"),
    (re.compile(NB + "рупануг(?!ґ)"), "рупануґ"),
    (re.compile(NB + "грихастх"), "ґріхастх"),
    (re.compile(NB + "дхам(?=[аиуі])"), "дгам"),
]


def variants(text):
    for rx, rep in VARIANTS:
        text = rx.sub(rep, text)
    return text


# Latin letters typed inside Cyrillic words (source/model typos; lint L30 «Latin letter inside a Cyrillic word»)
MIXED = [("праatı̄копа̄сана̄", "пратікопасана"), ("праatікопасана", "пратікопасана"), ("праtı̄", "пратı̄"), ("праtі", "праті"),
         ("прeм", "прем"), ("параmpар", "парампар"), ("Санакa-", "Санака-")]


# ---- A80b (13.10.2026, staging checkers): IAST words in Ukrainian prose, apostrophes, a.m./p.m., single words ----
IAST_D = "āīūṛṝḷṣśṇṭḍṁṅñḥĀĪŪṚṜḶṢŚṆṬḌṀṄÑḤ"
_LATW = "A-Za-zāīūṛṝḷṣśṇṭḍṁṅñḥĀĪŪṚṜḶṢŚṆṬḌṀṄÑḤ"
_WRD = f"[{_LATW}][{_LATW}’'\\-]*"
# a run of Latin words (one quoted Sanskrit/Bengali phrase): words joined by spaces, commas, hyphens, ’
IAST_RUN = re.compile(f"{_WRD}(?:[ ,]+{_WRD})*")
_I2U = [("kh", "кх"), ("gh", "ґг"), ("ch", "чх"), ("jh", "джх"), ("ṭh", "тх"), ("ḍh", "дг"), ("th", "тх"), ("dh", "дг"),
        ("ph", "пх"), ("bh", "бг"), ("jñ", "гй"), ("ai", "ай"), ("au", "ау"),
        ("a", "а"), ("ā", "а"), ("i", "і"), ("ī", "і"), ("u", "у"), ("ū", "у"), ("ṛ", "рі"), ("ṝ", "рі"), ("ḷ", "лі"),
        ("e", "е"), ("o", "о"), ("k", "к"), ("g", "ґ"), ("ṅ", "н"), ("c", "ч"), ("j", "дж"), ("ñ", "н"), ("ṭ", "т"),
        ("ḍ", "д"), ("ṇ", "н"), ("t", "т"), ("d", "д"), ("n", "н"), ("p", "п"), ("b", "б"), ("m", "м"), ("y", "й"),
        ("r", "р"), ("l", "л"), ("v", "в"), ("w", "в"), ("ś", "ш"), ("ṣ", "ш"), ("s", "с"), ("h", "х"), ("ṁ", "м"),
        ("ḥ", "х"), ("f", "ф"), ("z", "з"), ("x", "кс"), ("q", "к"), ("'", "’")]


def _glides(res):
    res = re.sub("йй([аеуі])", lambda m: "й" + IOT[m.group(1)], res)
    res = re.sub(f"([{CONS}])йо", lambda m: m.group(1) + ("’йо" if m.group(1) in LABIAL_R else "ьо"), res)   # bhyo -> бгьо
    res = re.sub(f"([{CONS}])й([аеуіи])", lambda m: m.group(1) + ("’" if m.group(1) in LABIAL_R else "ь") + IOT[m.group(2)], res)
    res = re.sub(f"(^|[{VOW}’])й([аеуі])", lambda m: m.group(1) + IOT[m.group(2)], res)
    return res


def iast_word(w):
    """one IAST (or Bengali-IAST) word -> Ukrainian letters by the krishna.ua table (Rādhā-Śyāma -> Радга-Шьяма)."""
    out = []
    for part in w.split("-"):
        low, cap = part.lower(), part[:1].isupper()
        res, i = "", 0
        while i < len(low):
            for a, b in _I2U:
                if low.startswith(a, i):
                    res += b
                    i += len(a)
                    break
            else:
                res += low[i]
                i += 1
        res = _glides(res.replace("аі", "ай"))      # ā+i as in plain_word (Нітай): «milāiba» -> мілайба
        if cap and res:
            res = res[0].upper() + res[1:]
        out.append(res)
    return "-".join(out)


def iast_runs(text):
    """Latin phrases with at least one IAST letter (outside ⟦…⟧, which are inline IAST mantras by schema) -> Ukrainian."""
    def one(seg):
        def run(m):
            r = m.group(0)
            if not re.search(f"[{IAST_D}]", r):
                return r                                   # plain Latin (GVP, Chrome, ISKCON) - not Sanskrit
            return re.sub(_WRD, lambda w: iast_word(w.group(0)), r)
        return IAST_RUN.sub(run, seg)
    parts = re.split("(⟦[^⟧]*⟧)", text)
    return "".join(p if p.startswith("⟦") else one(p) for p in parts)


# «оṁ» = Cyrillic «о» + IAST «ṁ» (mixed word): the syllable om
MIXED2 = [("оṁ", "ом"), ("Оṁ", "Ом")]


def _time(m):
    """«4:10 a.m.» -> «4:10 ранку.» (13.10: Ukrainian time words, as «утра/дня/вечера» in the Russian book)."""
    h, mm, ap = int(m.group(1)), m.group(2), m.group(3).lower()
    if ap == "a":
        word = "ночі" if h == 12 else "ранку"
    else:
        word = "дня" if h == 12 or h <= 4 else "вечора"
    tail = (m.group(4) or "").strip()
    nxt = m.string[m.end():m.end() + 2].strip()[:1]
    if tail:
        punct = tail
    elif not nxt or nxt.isupper() or nxt == "⟦":
        punct = "."
    else:
        punct = ""
    return f"{h}:{mm} {word}{punct}"


TIME = re.compile(r"(\d{1,2}):(\d\d)\s?([apAP])\.\s?[mM]\.(\s*[.:,;](?=\s|$))?")
APOS = re.compile(f"(?<=[{CYR}])['ʼ](?=[{CYR}])")
# single words the staging checkers found (13.10): Russian forms and wrong letters -> the book's / krishna.ua form
FIX_WORDS = [
    (re.compile("Магапрабгу"), "Махапрабгу"), (re.compile("Махапрабху"), "Махапрабгу"),
    (re.compile("([Бб])хаджан"), lambda m: m.group(1) + "гаджан"),
    (re.compile("([Вв])ринд"), lambda m: m.group(1) + "рінд"),
    (re.compile("([Мм])анґал"), lambda m: m.group(1) + "ангал"),          # 13.10: «Мангала» (krishna.ua, rules table)
    (re.compile("([Нн])іт’янанд"), lambda m: m.group(1) + "ітьянанд"),
    (re.compile("([Чч])айтан’"), lambda m: m.group(1) + "айтань"),
    (re.compile("([чшжщЧШЖЩ])’(?=[яюєї])"), lambda m: m.group(1) + "ь"),  # Ачьюта, Вайшья, Ґганашьяма
    (re.compile("[шШ]рі [ґҐ]урудев"), "Шрі Ґурудев"),                      # 13.10: «Шрі Ґурудева» with capitals
]


def fix_more(text, iast=True):
    for a, b in MIXED2:
        text = text.replace(a, b)
    if iast:
        text = iast_runs(text)
    text = TIME.sub(_time, text)
    text = APOS.sub("’", text)
    for rx, rep in FIX_WORDS:
        text = rx.sub(rep, text)
    return text


def plain(text, iast=True):
    if not isinstance(text, str) or not text:
        return text
    return fix_more(plain0(text), iast)


def plain_wbw(text):
    """wbw = «IAST head — Ukrainian; …»: the heads stay IAST (schema), only the Ukrainian part gets the IAST rule."""
    if not isinstance(text, str) or not text:
        return text
    out = []
    for sg in plain0(text).split(";"):
        if "—" in sg:
            h, rest = sg.split("—", 1)
            out.append(fix_more(h, iast=False) + "—" + fix_more(rest))
        else:
            out.append(fix_more(sg, iast=False))
    return ";".join(out)


def plain0(text):
    if not isinstance(text, str) or not text:
        return text
    for a, b in MIXED:
        if a in text:
            text = text.replace(a, b)
    nfc = unicodedata.normalize("NFC", text)                 # Latin «a» + U+0304 inside a Cyrillic word = ā
    if LAT_IN_CYR.search(nfc):
        text = LAT_IN_CYR.sub(lambda m: LAT[m.group(0)], nfc)   # Latin ā/ī/ū or palochka inside a Cyrillic word
    text = WORD.sub(lambda m: plain_word(m.group(0)) if is_sanskrit_word(m.group(0)) else m.group(0), text)
    return variants(text)


SKIP_KEYS = {"sanskrit", "src", "id", "audio_url", "transcript_url", "timecode", "date", "type", "layout", "page",
             "en_hash", "candidate", "target", "quote", "source", "scheme", "translation_note", "machine", "model"}
# source = lecture title as published; scheme = the glossary's transliteration table (IAST on purpose)


def conv(o, stats, key=None):
    if isinstance(o, dict):
        return {k: (v if k in SKIP_KEYS else conv(v, stats, k)) for k, v in o.items()}
    if isinstance(o, list):
        return [conv(v, stats, key) for v in o]
    if isinstance(o, str):
        n = plain_wbw(o) if key == "wbw" else plain(o)
        if n != o:
            stats["strings"] += 1
            stats["marks"] += extra_marks(o) - extra_marks(n)
        return n
    return o


def targets():
    """(path, getter of the Ukrainian part, setter) for every file that feeds the Ukrainian book."""
    T = [os.path.join(REPO, "data", "book.uk.json"), os.path.join(REPO, "data", "ui.uk.json"),
         os.path.join(REPO, "scripts", "translate", "glossary.uk.json")]
    for root in ("scripts/chapters", "scripts/parampara"):
        for dp, _, fns in os.walk(os.path.join(REPO, root)):
            for fn in fns:
                if fn == "i18n.json":
                    T.append(os.path.join(dp, fn))
    T.append(os.path.join(REPO, "scripts", "moods", "moods.json"))
    return T


def convert_file(p, stats):
    d = json.load(open(p, encoding="utf-8"))
    base = os.path.basename(p)
    if base in ("book.uk.json", "ui.uk.json", "glossary.uk.json"):
        new = conv(d, stats)
    elif base == "i18n.json":
        new = dict(d)                     # {section id: {lang: {...}}} (or {lang: …})
        if "uk" in d:
            new["uk"] = conv(d["uk"], stats)
        for sid, v in d.items():
            if isinstance(v, dict) and "uk" in v:
                v2 = dict(v)
                v2["uk"] = conv(v["uk"], stats)
                new[sid] = v2
    elif base == "moods.json":
        new = []
        for m in d:
            m2 = dict(m)
            for k, v in m.items():
                if isinstance(v, dict) and "uk" in v:
                    v2 = dict(v)
                    v2["uk"] = conv(v["uk"], stats)
                    m2[k] = v2
            if isinstance(m.get("more"), list):      # A80b: the other candidate quotes were left in the old spelling
                more = []
                for a in m["more"]:
                    a2 = dict(a)
                    tr = a.get("translation")
                    if isinstance(tr, dict) and "uk" in tr:
                        a2["translation"] = dict(tr, uk=conv(tr["uk"], stats))
                    more.append(a2)
                m2["more"] = more
            new.append(m2)
    else:
        new = d
    return d, new


def dump_like(p, obj):
    raw = open(p, encoding="utf-8").read()
    indent = None
    m = re.match(r"[\[{]\r?\n( +)", raw)
    if m:
        indent = len(m.group(1))
    out = json.dumps(obj, ensure_ascii=False, indent=indent)
    if raw.endswith("\n"):
        out += "\n"
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(out)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    check = "--check" in sys.argv
    total = 0
    for p in targets():
        if not os.path.exists(p):
            continue
        stats = {"strings": 0, "marks": 0}
        d, new = convert_file(p, stats)
        if stats["strings"]:
            total += stats["strings"]
            print(f"{os.path.relpath(p, REPO)}: {stats['strings']} strings, {stats['marks']} diacritics removed")
            if not check:
                dump_like(p, new)
    print(f"total strings changed: {total}")
    if check and total:
        sys.exit(1)


if __name__ == "__main__":
    main()
