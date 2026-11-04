# -*- coding: utf-8 -*-
"""Noteikuma 79 (Стандарты) pārbaude VISAI grāmatai — daļas D1–D8 (A142b, Padomnieka pasts 2026.11.04_0405, S «Да» msg 1322).

Noteikums 79 (burtiski): «У каждого стиха, который мы цитируем в книге (в любой главе), обязательно есть пословный перевод; в приложении он открывается кнопкой «пословно». Пословный перевод делаем по образцу BBT: «слово — простое значение», без пояснений в скобках и без «или»; длинное составное слово делим на части, у каждой своё значение, короткое оставляем целым; слова, слитые по сандхи, разделяем. Если для стиха есть пословный перевод BBT — берём его. Исключение — короткие мантры (правило 178): пословный перевод есть в данных, кнопки нет.»

Daļas:
 D1 katram citētajam pantam (verse + mantras tabulās) ir wbw  (izņēmums: «Джая-дхвани», S msg 6828, sadaļa jaya-dhvani-front)
 D2 poga «пословно» ir (kods SectionContent: isShortMantra -> bez pogas), īsajām mantrām (178) dati ir, pogas nav
 D3 formāts «слово — простое значение» (katrs ieraksts: viena atslēga, ' — ', nozīme; atslēgā nav () un atstarpju; atslēga nebeidzas ar '-')
 D4 bez iekavām () [] nozīmē (un atslēgā)
 D5 bez «или» nozīmē (izņēmums: pats vārds vā/athavā/tu = «или», «или же»; BBT atsauce — sk. BBT_KEEP)
 D6 garš saliktenis dalīts: atslēga ar 3+ daļām (2+ defises) vai slēptu 3+ daļu salikteņi (HIDDEN) nav; īsie (2 daļas) palieku veseli
 D7 sandhi dalīts: SPLITS tabulas atslēgas nav; + heiristisks kandidātu skenētājs (vārdnīca) tikai informācijai
 D8 BBT: ja pantam ir BBT pārvārdojums (vedabase.io, RU; EN — A142c) — grāmatā tas pats (rezultāts no scripts/rule79_bbt_lookup.py kešs)
# tehniskais slieksnis Lipikāra, nav S noteikums: «garš» = 3+ daļas (2+ defises vai slēptas 3+ daļas); 2 daļu īpašvārdi/termini paliek veseli.

CLI:  python qa/rule79_check.py [data_dir] [--fix] [--json out.json]   (--fix labo D3(daļēji)/D4/D5/D6/D7 ar SPLITS tabulu, raksta datus)
"""
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts", "translate"))
from iast_to_cyrillic import translit  # noqa: E402

DATA_DEFAULT = os.path.join(HERE, "..", "data")
BOOKS = ("book.ru-iast.json", "book.ru.json")
EN_BOOK = "book.json"  # A142c (S msg 7484): angļu versija — tie paši D1–D8, nozīmes angliski
BOOKS_ALL = BOOKS + (EN_BOOK,)
EXEMPT_SECTIONS = {"jaya-dhvani-front"}  # S msg 6828 (26.10.2026)
LOCKED_SECTIONS = {"gaudiya-emblem"}  # S msg 6038 (21.10): «Эмблему не трогаешь, только стих» — D3–D7 netiek ne pārbaudītas, ne labotas (s101 d)
IGNORE_KEYS = ["priya-narma-sakhī"]  # klases termins, A142
CLASS_WORDS_OR = {"или", "или же", "либо", "or", "or else"}  # EN: vā/athavā/tu = «or», «or else»  # paša vārda nozīme (vā, athavā, tu) — nav alternatīva

# ---- D6/D7: slēptie salikteņi un sandhi (IAST atslēga -> {nozīme | '*' -> jaunais ieraksts "k — v; k — v"}) ----
SPLITS = {
    # vārdu sandhi (D7)
    "sadaiva": {"*": "sadā — всегда; eva — именно"},
    "tadaiva": {"*": "tadā — тогда; eva — именно"},
    "dāsyenaiva": {"*": "dāsyena — как слугу; eva — именно"},
    "tasyāgrajam": {"*": "tasya — его; agrajam — старшего брата"},
    "tanayāntike": {"*": "tanayā — дочери; antike — рядом"},
    "śraddhayānvitaḥ": {"*": "śraddhayā — с верой; anvitaḥ — исполненный"},
    # слитые 3+ части (D6/D7)
    "devasyotthāpanāvadhi": {"*": "devasya — Господа; utthāpana — пробуждения; avadhi — до"},
    "divyālaṅkāraṇopetaṁ": {"*": "divya — сверкающими; alaṅkāraṇa — украшениями; upetaṁ — украшенного"},
    "tad-bhāvākāṅkṣiṇo": {"*": "tad — тех; bhāva — чувства; ākāṅkṣiṇo — стремящиеся обрести"},
    "bāhyābhyantara-śuciḥ": {"*": "bāhya — внешне; abhyantara — внутренне; śuciḥ — чистый"},
    "gaurāvirbhāva-bhūmes": {"*": "gaura — Гауранги; āvirbhāva — явления; bhūmes — места"},
    "kalyāṇa-guṇārṇavasya": {"*": "kalyāṇa — благоприятных; guṇa — качеств; arṇavasya — океана"},
    "rādhikā-mādhavāśāṁ": {"*": "rādhikā — Радхики; mādhava — Мадхавы; āśāṁ — стремление"},
    "navāmbudāṅga-cikkaṇaṁ": {"*": "nava — свежей; ambuda — тучи; aṅga — тела; cikkaṇaṁ — сияющего"},
    "prabhāruṇāṅghri-komale": {"*": "prabhā — сияющих; aruṇa — красноватых; aṅghri — стоп; komale — о нежная"},
    "priyānurāga-rañjite": {"*": "priya — возлюбленного; anurāga — любовной привязанности; rañjite — о наслаждающаяся"},
    "tadīyeśita-jñeṣu": {"*": "tadīya — Его; īśita — владычества; jñeṣu — знающим"},
    "rādhāliṅgita-vigraham": {"*": "rādhā — Радха; āliṅgita — обнимает; vigraham — тело"},
    "śrī-caraṇāravindam": {"*": "śrī — Шри; caraṇa — стопам; aravindam — лотосным"},
    "veṇu-vaktrābjaṁ": {"*": "veṇu — флейтой; vaktra — уст; abjaṁ — лотосных"},
    "vipralambha-rasāmbhodhe": {"*": "vipralambha — разлуки; rasa — расы; ambhodhe — о океан"},
    "rāsa-rasārambhī": {"*": "rāsa — танца раса; rasa — вкуса; ārambhī — открывающий"},
    "jñānāñjana-śalākayā": {"палочкой для нанесения бальзама божественного знания": "jñāna — знания; añjana — бальзама; śalākayā — палочкой",
                            "факелом знания": "jñāna — знания; añjana — бальзама; śalākayā — факелом"},
    "ajñāna-timirāndhasya": {"*": "ajñāna — невежества; timira — тьмой; andhasya — ослеплённого"},
    "jadāhaṅkāra-nāśana": {"*": "jada — косное; ahaṅkāra — эго; nāśana — уничтожающий"},
    "pañca-tattvātmakaṁ": {"*": "pañca — пяти; tattva — аспектах; ātmakaṁ — проявленного"},
    "sucarcitāṅga-candanaṁ": {"*": "su — хорошо; carcita — умащённого; aṅga — тела; candanaṁ — сандаловой пастой"},
    "sunāsikāgra-mauktikaṁ": {"*": "su — прекрасного; nāsikā — носа; agra — на кончике; mauktikaṁ — жемчужиной"},
    "paramānanda-vardhanam": {"*": "parama — высшее; ānanda — блаженство; vardhanam — возрастающее"},
    "pūrṇānanda-kalevaram": {"*": "pūrṇa — исполненное; ānanda — блаженства; kalevaram — тело"},
    "gopī-janānanda": {"*": "gopī — гопи; jana — людей; ānanda — блаженству"},
    "sarva-gurūttamāya": {"высочайшему из всех гуру": "sarva — всех; guru — гуру; uttamāya — высочайшему",
                          "высшему из всех гуру": "sarva — всех; guru — гуру; uttamāya — высшему"},
    "pramoda-kānaneśvari": {"*": "pramoda — восхитительного; kānana — леса; īśvari — о повелительница"},
    "pramāṇa-śāsaneśvari": {"*": "pramāṇa — авторитетных; śāsana — предписаний; īśvari — о повелительница"},
    "triveda-bhāratīśvari": {"*": "tri — трёх; veda — Вед; bhāratī — учений; īśvari — о повелительница"},
    "tīra-gandhavāha": {"*": "tīra — берегов; gandha — ароматного; vāha — ветерка"},
    "padāṅgulī-nakhe": {"*": "pada — стоп; aṅgulī — пальцев; nakhe — о обладательница ногтей"},
    "ratna-siṁhāsane": {"*": "ratna — драгоценными камнями; siṁha — львиный; āsane — на троне"},
    "svarṇa-siṁhāsanaṁ": {"*": "svarṇa — золотой; siṁha — львиный; āsanaṁ — трон"},
    "śāradendu-maṇḍale": {"*": "śārada — осенних; indu — лун; maṇḍale — диски"},
    "varābhaya-pradaṁ": {"*": "vara — блага; abhaya — бесстрашие; pradaṁ — дарующего"},
    "vilāsānuga-vāsasam": {"*": "vilāsa — игр; anuga — сообразно; vāsasam — одетому"},
    "vrajāṅganā-sunāyakaṁ": {"*": "vraja — Враджа; aṅganā — девушек; su — прекрасному; nāyakaṁ — возлюбленному"},
    "vṛndāvana-sunāgaraṁ": {"*": "vṛndāvana — Вриндавана; su — искусному; nāgaraṁ — возлюбленному"},
    "rūpānuga-varāya": {"*": "rūpa — Рупы; anuga — последователей; varāya — величайшему"},
    "sukīrtana-anusmṛtyoḥ": {"*": "sukīrtana — в любовном воспевании; anusmṛtyoḥ — и памятовании"},
    "sumālānvitaṁ": {"украшенной прекрасным ожерельем": "su — прекрасным; mālā — ожерельем; anvitaṁ — украшенной",
                     "украшенную прекрасным ожерельем": "su — прекрасным; mālā — ожерельем; anvitaṁ — украшенную"},
}
# kandidāti, kas paliek veseli (vārdi/epiteti/termini; 2 daļas; nav izdalāms vienkārši) — izlemts pašam, lemumi-pasas.md
KEEP_WHOLE = {
    "vrajendra-nandana", "vrajendra-bhānu", "vrajendra-sūnu", "rūpānugāmṛta", "mahābhāva-svarūpā", "kāruṇya-ghanāghanatvam",
    "rādhikāyaḥ-priyātmane", "mādhavāśraya-vigraham", "vṛndāraṇya-maheśvarīm", "mallikākṣa-haṁsa", "indranīla-vṛnda",
    "bhaktivedānta-nārāyaṇa", "bhaktivedānta-svāmin", "padmajārcite",
}
# BBT: pants, kam RU BBT nozīme satur «или»/iekavas — ņemts burtiski no BBT (noteikums 79: «если есть BBT — берём его»)
BBT_KEEP_OR = {"su-kīrtana"}  # NOI 8: «в тщательное обсуждение или воспевание»

OR_RE = {False: r"\bили\b", True: r"\bor\b"}
SHORT_END = ("namaḥ", "svāhā", "phaṭ", "намах̣", "сва̄ха̄", "пхат̣")


def nfc(s):
    return unicodedata.normalize("NFC", s)


def is_short_mantra(text):
    """lib/book.ts isShortMantra: viena rinda, 2–6 vārdi, beidzas namaḥ/svāhā/phaṭ (+ . !)."""
    s = nfc(re.sub("[⟦⟧]", "", text or "")).strip()
    if not s or "\n" in s:
        return False
    w = s.split()
    return 2 <= len(w) <= 6 and re.search("(" + "|".join(nfc(e) for e in SHORT_END) + r")[.!]?$", s) is not None


def split_entries(wbw):
    s = wbw.strip()
    if s.endswith("."):
        s = s[:-1]
    out = []
    for e in s.split("; "):
        k, sep, v = e.partition(" — ")
        out.append((k, sep, v))
    return out


def join_entries(ents, dot=True):
    return "; ".join(f"{k} — {v}" for k, _, v in ents) + ("." if dot else "")


def load(data_dir, name):
    return json.load(open(os.path.join(data_dir, name), encoding="utf-8"))


def iter_wbw_holders(d):
    """(sec_id, path, obj, kind) — obj['wbw'] vai trūkstošs: verse bloki + paired-list vienumi ar mantru."""
    for si, s in enumerate(d["sections"]):
        for ss in [s] + (s.get("subsections") or []):
            where = s["id"] if ss is s else f"{s['id']}/{ss['id']}"
            for i, b in enumerate(ss.get("content") or []):
                if b.get("type") == "verse":
                    yield s["id"], f"{where}/#{i}", b, "verse"
                elif b.get("type") == "paired-list":
                    for j, it in enumerate(b.get("items") or []):
                        txt = (it.get("label") or "") + " " + (it.get("value") or "")
                        if it.get("wbw") or re.search("(namaḥ|намах̣)⟧", txt):
                            yield s["id"], f"{where}/#{i}.{j}", it, "mantra"


def bbt_verses():
    """qa/rule79_bbt_verses.json: BBT pantu vietas (path -> url) un BBT RU pārvārdojums; šiem pantiem D3–D7 netiek piemērotas (noteikums 79: «берём его»)."""
    p = os.path.join(HERE, "rule79_bbt_verses.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


# BBT RU vērtībās kirilica ar diakritiku → IAST ru-iast failā («Санскрит везде пишем в IAST с диакритикой»)
CYR2IAST = {"девакӣ-джанма-ва̄дах̣": "devakī-janma-vādaḥ"}


def bbt_expected(info, name):
    """(atslēgas, nozīmes) kā tām jābūt book failā."""
    if name == EN_BOOK:  # A142c: EN BBT «Synonyms» burtiski (qa/rule79_bbt_verses.json «en»)
        return [k for k, _ in info["en"]], [v for _, v in info["en"]]
    if name == "book.ru-iast.json":
        vals = []
        for _, b in info["ru"]:
            for a, z in CYR2IAST.items():
                b = b.replace(a, z)
            vals.append(b)
        return info["en_keys"], vals
    return [translit(k) for k in info["en_keys"]], [b for _, b in info["ru"]]


def bbt_keys():
    ks = set()
    for v in bbt_verses().values():
        ks.update(v["en_keys"])
        ks.update(translit(k) for k in v["en_keys"])
    return ks


BBT_PATHS = {pp: u for u, v in bbt_verses().items() for pp in v["paths"]}


def iter_entries(d):
    for sid, path, obj, kind in iter_wbw_holders(d):
        if sid in LOCKED_SECTIONS or path in BBT_PATHS:
            continue
        if (obj.get("wbw") or "").strip():
            for idx, (k, sep, v) in enumerate(split_entries(obj["wbw"])):
                yield sid, path, obj, kind, idx, k, sep, v


def entry_key_iast_variants(k, cv):
    return k


def check_book(d, cv, name, bbt_cache=None):
    """Atgriež {daļa: dict(checked, bad(list))}; cv = IAST->(IAST vai kirilica) atslēgu pārveidotājs."""
    R = {x: {"checked": 0, "bad": []} for x in ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8")}
    ign = {cv(i) for i in IGNORE_KEYS}
    keep_whole = {cv(i) for i in KEEP_WHOLE}
    splits = {cv(k): v for k, v in SPLITS.items()}
    seen_holders = set()
    # D1/D2
    code = open(os.path.join(HERE, "..", "components", "SectionContent.tsx"), encoding="utf-8").read()
    code_ok = "isShortMantra(item.sanskrit) ? undefined : item.wbw" in code
    for sid, path, obj, kind in iter_wbw_holders(d):
        txt = obj.get("sanskrit") if kind == "verse" else (obj.get("label") or "")
        R["D1"]["checked"] += 1
        has = bool((obj.get("wbw") or "").strip())
        if not has and sid not in EXEMPT_SECTIONS and not (sid in LOCKED_SECTIONS and name == EN_BOOK):  # EN emblēmas wbw nav: S 6038 «Эмблему не трогаешь» (s101 d) — jautājums S
            R["D1"]["bad"].append(f"{path} :: {(txt or '')[:60]}")
        if has:
            R["D2"]["checked"] += 1
            short = is_short_mantra(txt) if kind == "verse" else False
            # poga ir <=> ir wbw un nav īsā mantra; kods to nodrošina tikai, ja SectionContent satur isShortMantra nosacījumu
            if not code_ok:
                R["D2"]["bad"].append(f"{path} :: SectionContent nav isShortMantra nosacījuma")
            if short and not has:
                R["D2"]["bad"].append(f"{path} :: īsā mantra bez datiem")
    # D3–D7 pa ierakstiem
    for sid, path, obj, kind, idx, k, sep, v in iter_entries(d):
        for part in ("D3", "D4", "D5", "D6", "D7"):
            R[part]["checked"] += 1
        loc = f"{path}[{idx}] {k} — {v}"[:130]
        if not sep or not k.strip() or not v.strip() or k.endswith("-") or "(" in k or ")" in k:
            R["D3"]["bad"].append(loc)
        elif re.search(r"\s", k):
            R["D3"]["bad"].append("daudzvārdu atslēga: " + loc)
        if re.search(r"[()\[\]]", k + v):
            R["D4"]["bad"].append(loc)
        if re.search(OR_RE[name == EN_BOOK], v, flags=re.I) and v.strip().lower().rstrip(".") not in CLASS_WORDS_OR and k not in {cv(x) for x in BBT_KEEP_OR}:
            R["D5"]["bad"].append(loc)
        if k not in ign and k not in keep_whole and k.count("-") >= 2:
            R["D6"]["bad"].append(loc)
        if k in splits:
            R["D7"]["bad"].append(loc)
    # D8: BBT pantiem wbw = BBT RU burtiski (ru-iast: atslēgas no BBT EN, nozīmes BBT RU; ru: BBT RU kirilica)
    info = bbt_verses()
    for sid, path, obj, kind in iter_wbw_holders(d):
        u = BBT_PATHS.get(path)
        if not u or kind != "verse":
            continue
        R["D8"]["checked"] += 1
        want = info[u]
        if name == EN_BOOK and not want.get("en"):
            R["D8"]["bad"].append(f"{path} :: nav BBT EN datu ({u})")
            continue
        keys, vals = bbt_expected(want, name)
        exp = "; ".join(f"{k} — {v}" for k, v in zip(keys, vals))
        if (obj.get("wbw") or "").strip().rstrip(".") != exp.rstrip("."):
            R["D8"]["bad"].append(f"{path} :: nav BBT ({u})")
    return R


def candidate_scan(d, cv):
    """D7 informatīvs: vārdnīcas skenētājs (X+Y ar patskaņu sandhi, abi X,Y ir citur kā atsevišķi vārdi) — tikai kandidāti."""
    parts = set()
    for sid, path, obj, kind, idx, k, sep, v in iter_entries(d):
        for t in re.split(r"[-\s]", k):
            t = nfc(t.lower()).strip("()'’‘")
            if t:
                parts.add(t)
    SAND = [("ā", "a ā", "a ā"), ("e", "a ā", "i ī"), ("o", "a ā", "u ū"), ("ai", "a ā", "e ai"), ("au", "a ā", "o au"),
            ("ī", "i ī", "i ī"), ("ū", "u ū", "u ū")]
    out = []
    for t in sorted(parts):
        if len(t) < 7:
            continue
        hit = None
        for i in range(3, len(t) - 2):
            for res, xs, ys in SAND:
                if t.startswith(res, i):
                    X, Y = t[:i], t[i + len(res):]
                    for xe in xs.split():
                        for ye in ys.split():
                            if X + xe in parts and ye + Y in parts and len(X) >= 3 and len(Y) >= 2:
                                hit = (X + xe, ye + Y)
        if hit:
            out.append((t, hit))
    return out


def fix_book(d, cv):
    """Labo D4/D5/D6/D7 vietā; atgriež skaitļus. Secība: SPLITS -> iekavas -> «или»."""
    splits = {cv(k): {kk: ("; ".join(
        f"{cv(p.partition(' — ')[0])} — {p.partition(' — ')[2]}" for p in vv.split("; "))) for kk, vv in v.items()} for k, v in SPLITS.items()}
    st = {"splits": 0, "brackets": 0, "ili": 0, "key_parens": 0, "empty_after_strip": []}
    for sid, path, obj, kind in iter_wbw_holders(d):
        if sid in LOCKED_SECTIONS or path in BBT_PATHS or not (obj.get("wbw") or "").strip():
            continue
        ents = split_entries(obj["wbw"])
        had_dot = obj["wbw"].strip().endswith(".")
        new = []
        for k, sep, v in ents:
            if k in splits:
                m = splits[k]
                rep = m.get(v) or m.get("*")
                if rep:
                    st["splits"] += 1
                    for p in rep.split("; "):
                        pk, _, pv = p.partition(" — ")
                        new.append((pk, " — ", pv))
                    continue
            new.append((k, sep, v))
        out = []
        for k, sep, v in new:
            if re.search(r"[()]", k):
                k2 = k.replace("(", "").replace(")", "")
                st["key_parens"] += 1
                k = k2
                v = re.sub(r"^\((.*)\)$", r"\1", v.strip())
            v0 = v
            if re.search(r"[()\[\]]", v) and not re.search(r"[\(\[][^()\[\]]*[\)\]]", v):
                v = re.sub(r"[()\[\]]", "", v).strip()  # nesapārota iekava (piem. «…санкиртану)»)
                st["brackets"] += 1
            if re.search(r"[()\[\]]", v):
                v = re.sub(r"\s*[\(\[][^()\[\]]*[\)\]]", "", v)
                v = re.sub(r"\s+", " ", v).strip()
                if not v:
                    st["empty_after_strip"].append(f"{path} {k}")
                    v = v0
                else:
                    st["brackets"] += 1
            if re.search(r"\bили\b", v, flags=re.I) and v.strip().lower().rstrip(".") not in CLASS_WORDS_OR and k not in {cv(x) for x in BBT_KEEP_OR}:
                v2 = re.split(r"\s+или\s+", v)[0].strip().rstrip(",;")
                if v2 and v2 != v:
                    v = v2
                    st["ili"] += 1
            out.append((k, " — ", v))
        obj["wbw"] = join_entries(out, had_dot)
    return st


def write_book(d, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(d, indent=2, ensure_ascii=False) + "\n")


def en_info(data_dir):
    """EN (book.json): atsevišķi atzīmēts — tikai saliktenis/iekavu skaits; EN = BBT teksts, netiek labots."""
    d = load(data_dir, "book.json")
    n = br = ili = 0
    for sid, path, obj, kind, idx, k, sep, v in iter_entries(d):
        n += 1
        br += bool(re.search(r"[()\[\]]", k + v))
        ili += bool(re.search(r"\bor\b", v))
    return {"entries": n, "with_brackets": br, "with_or": ili}


def d8_report(data_dir, cache_path):
    """D8: kešs no scripts/rule79_bbt_lookup.py -> cik pantiem ir BBT RU, cik sakrīt nozīmju secība."""
    if not cache_path or not os.path.exists(cache_path):
        return None
    cache = json.load(open(cache_path, encoding="utf-8"))
    d = load(data_dir, "book.ru-iast.json")
    fold = lambda s: re.sub(r"[^а-яё]", "", s.lower())
    res = {"verses_unique": 0, "bbt_found": 0, "bbt_ru": 0, "equal": 0, "diff": []}
    seen = set()
    for sid, path, obj, kind in iter_wbw_holders(d):
        if kind != "verse" or not (obj.get("wbw") or "").strip():
            continue
        key = re.sub(r"[^a-z]", "", "".join(c for c in unicodedata.normalize("NFD", obj["sanskrit"].splitlines()[0].lower()) if not unicodedata.combining(c)).replace("ṁ", "m"))[:60]
        if key in seen:
            continue
        seen.add(key)
        res["verses_unique"] += 1
        r = cache.get(key)
        if not r or not r.get("match"):
            continue
        res["bbt_found"] += 1
        if not r.get("ru"):
            continue
        res["bbt_ru"] += 1
        bbt = [fold(v) for k, v in r["ru"]]
        ours = [fold(v) for k, sep, v in split_entries(obj["wbw"])]
        if bbt == ours:
            res["equal"] += 1
        else:
            res["diff"].append((path, r["match"], len(bbt), len(ours)))
    return res


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    data_dir = args[0] if args else DATA_DEFAULT
    fix = "--fix" in sys.argv
    out_json = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    cache = None
    for a in sys.argv:
        if a.startswith("--bbt-cache="):
            cache = a.split("=", 1)[1]
    summary = {}
    for name in BOOKS_ALL:
        d = load(data_dir, name)
        cv = (lambda x: x) if name in ("book.ru-iast.json", EN_BOOK) else translit
        if fix and name != EN_BOOK:  # EN labo scripts/rule79_en_fix.py (nozīmes angliski)
            st = fix_book(d, cv)
            write_book(d, os.path.join(data_dir, name))
            print(f"FIX {name}: {st}")
            d = load(data_dir, name)
        R = check_book(d, cv, name)
        summary[name] = {p: {"checked": v["checked"], "bad": len(v["bad"]), "examples": v["bad"][:5]} for p, v in R.items()}
        print(f"== {name}")
        for p in ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"):
            v = R[p]
            print(f"  {p}: pārbaudīts {v['checked']}, pārkāpumi {len(v['bad'])}")
            for x in v["bad"][:4]:
                print("     ", x)
        cand = candidate_scan(d, cv)
        print(f"  D7 kandidāti (vārdnīcas heiristika, informatīvi): {len(cand)}")
        summary[name]["D7_candidates"] = len(cand)
    print("== EN (book.json, atsevišķi):", en_info(data_dir))
    r8 = d8_report(data_dir, cache)
    print("== D8:", r8 if r8 else "nav keša (scripts/rule79_bbt_lookup.py)")
    if out_json:
        json.dump(summary, open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return summary


if __name__ == "__main__":
    main()
