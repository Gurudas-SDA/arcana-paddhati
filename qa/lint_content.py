"""Satura linteris pār data/book.*.json (+ ui.*.json un uzbūvēto out/ HTML).

Katra pārbaude = Satkirti likums no «Стандарты книги и работы.md» / «Правила интерфейса книг.md»
(skat. qa/likumi.json). Izvade tādā pašā formātā kā pārlūka testi:
  [PASS] data L1 <apraksts>
  [FAIL] data L1 <apraksts> :: <ceļš> :: <fragments>
  [WARN] ... — atzīts izņēmums no qa/lint_config.json (ar pamatojumu), nebloķē.
Izejas kods 1, ja ir kaut viens FAIL.

usage: python qa/lint_content.py [--no-html] [--max N]
"""
import argparse
import glob
import json
import os
import re
import sys
from html.parser import HTMLParser

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import qa  # noqa: E402

CFG = json.load(open(os.path.join(qa.QA_DIR, "lint_config.json"), encoding="utf-8"))
COMB = "̀-ͯ"
WB = rf"(?<![\w{COMB}])"   # word start (diacritics are part of the word)
WE = rf"(?![\w{COMB}])"
# Bīju galvas (pantu pa vārdam), IAST + kirilica (book.ru.json): aiṁ klīṁ śrīṁ — tieši Satkirti likuma
# bījas (06.10 19:05). rāṁ u.c. ar paskaidrojumu («биджа-мантра Шри Радхи») likums neaptver.
BIJA_HEADS = {"aiṁ", "klīṁ", "śrīṁ",
              "аим̇", "клӣм̇", "ш́рӣм̇"}
# Vecā (nepareizā) rakstība: aing klīng śrīng hrīng (+ kirilica)
BIJA_OLD = ["aing", "klīng", "śrīng", "hrīng",
            "аинг", "клӣнг", "ш́рӣнг", "хрӣнг"]
MANTRA_RE = re.compile(r"(namaḥ|намах̣)⟧")   # same as components/SectionContent.tsx

# Parampara captions — exact (Satkirti 06.10/07.10; analysis «Начало книги …» 07.10, §5) — L21, s22.
PARAMPARA_RU = [
    "Шри Панча-таттва",   # Satkirti 07.10 13:35: Pañca-tattva page first
    "Шрила Джаганнатха дас Бабаджи Махарадж",
    "Шрила Саччидананда Бхактивинода Тхакур",
    "Шрила Гаура Кишора дас Бабаджи Махарадж",
    "Прабхупада Шрила Бхактисиддханта Сарасвати Тхакур",
    "Шрила Бхакти Праджнана Кешава Госвами Махарадж",
    "Шрила А. Ч. Бхактиведанта Свами Прабхупада",
    "Шрила Бхактиведанта Нараяна Госвами Махарадж",
    "Шри Према Прайоджана Прабху",
]
PARAMPARA_EN = [
    "Śrī Pañca-tattva",
    "Śrīla Jagannātha dāsa Bābājī Mahārāja",
    "Śrīla Saccidānanda Bhaktivinoda Ṭhākura",
    "Śrīla Gaura Kiśora dāsa Bābājī Mahārāja",
    "Prabhupāda Śrīla Bhaktisiddhānta Sarasvatī Ṭhākura",
    "Śrīla Bhakti Prajñāna Keśava Gosvāmī Mahārāja",
    "Śrīla AC Bhaktivedānta Svāmī Prabhupāda",
    "Śrīla Bhaktivedānta Nārāyaṇa Gosvāmī Mahārāja",
    "Śrī Prem Prayojan Prabhu",
]

FAILS = []
RESULTS = []


def books(pattern="book*.json"):
    return sorted(glob.glob(os.path.join(qa.DATA, pattern)))


def walk(o, ctx, path):
    """yield (path, author_text, key, string) for every string in the book."""
    skip_t = set(CFG["author_text_skip"]["types"])
    skip_k = set(CFG["author_text_skip"]["keys"])
    if isinstance(o, dict):
        t = o.get("type")
        a = ctx and t not in skip_t
        label = o.get("id") if isinstance(o.get("id"), str) else None
        for k, v in o.items():
            p = path + ([label] if label and k != "id" else []) + ([] if k in ("sections", "subsections", "content", "items", "parts") else [f"{t or ''}.{k}" if t else k])
            if isinstance(v, str):
                yield "/".join(map(str, p)), a and k not in skip_k, k, v
            else:
                yield from walk(v, a and k not in skip_k, p)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, ctx, path)


def snippet(s, m, pad=40):
    return s[max(0, m.start() - pad):m.end() + pad].replace("\n", " ")


def exception_for(check, fname, where, frag):
    for e in CFG.get("exceptions", []):
        if e["check"] == check and e["file"] == fname and e["match"] in f"{where} :: {frag}":
            return e
    return None


class Check:
    def __init__(self, cid, title):
        self.cid, self.title, self.hits, self.warns, self.info = cid, title, [], [], ""

    def hit(self, fname, where, frag):
        e = exception_for(self.cid, fname, where, frag)
        (self.warns if e else self.hits).append((fname, where, frag, e))

    def report(self, maxn):
        ok = not self.hits
        RESULTS.append(dict(id=self.cid, title=self.title, ok=ok, hits=len(self.hits), warns=len(self.warns)))
        print(f"  [{'PASS' if ok else 'FAIL'}] data {self.cid} {self.title}{(' — ' + self.info) if self.info else ''}", flush=True)
        for f, w, fr, _ in self.hits[:maxn]:
            print(f"        {f} :: {w} :: {fr}")
        if len(self.hits) > maxn:
            print(f"        … +{len(self.hits) - maxn}")
        for f, w, fr, e in self.warns[:maxn]:
            print(f"  [WARN] data {self.cid} izņēmums ({e['reason'][:90]}) :: {f} :: {w} :: {fr}")
        if not ok:
            FAILS.append(self.cid)


def run(args):
    ru = [os.path.join(qa.DATA, b) for b in CFG["ru_books"]]
    allb = books()
    parts = "|".join(CFG["pair_second_parts"])
    loaded = {f: json.load(open(f, encoding="utf-8")) for f in allb}
    name = os.path.basename

    # L1 — Склоняется только последняя часть: Радха-Кришны, не «Радхе-Кришне»
    c = Check("L1", "Dievību pāris: locās tikai otrā daļa (nav «Радхе-/Радху-/Радхи-/Радхой-» pirms pāra otrās daļas)")
    rx = re.compile(r"Радх(е|у|и|ы|ой|ою)-[А-ЯЁ]")
    for f in ru:
        for p, a, k, s in walk(loaded[f], True, []):
            for m in rx.finditer(s):
                c.hit(name(f), p, snippet(s, m))
    c.report(args.max)

    # L2 — «Шри Шри» pirms Dievību pāra autora tekstā; «Шри Шри» ar atstarpi
    c = Check("L2", "«Шри Шри» pirms Dievību pāra autora tekstā (ne «Шри-Шри», ne viens «Шри»)")
    rx = re.compile(rf"Радх[а-яё]*-(?:{parts})")
    bad_sep = re.compile(r"Шри-Шри|ШриШри")
    for f in ru:
        for p, a, k, s in walk(loaded[f], True, []):
            for m in bad_sep.finditer(s):
                c.hit(name(f), p, snippet(s, m))
            if not a:
                continue
            for m in rx.finditer(s):
                pre = s[max(0, m.start() - 8):m.start()]
                if not re.search(r"Шри[  ]Шри[  ]$", pre):
                    c.hit(name(f), p, snippet(s, m))
    c.report(args.max)

    # L3 — «Радха-Говинда» не пишем (кроме дословных цитат и переводов стихов)
    c = Check("L3", "nav «Радха-Говинда» autora tekstā (izņēmums: pantu tulkojumi, citāti)")
    rx = re.compile(r"Радх[а-яё]*-Говинд")
    for f in ru:
        for p, a, k, s in walk(loaded[f], True, []):
            if a:
                for m in rx.finditer(s):
                    c.hit(name(f), p, snippet(s, m))
    c.report(args.max)

    # L4 — без «-джи/-джиу» после пары имён Божеств
    c = Check("L4", "Dievību pāris bez «-джи/-джиу»")
    rx = re.compile(rf"Радх[а-яё]*-(?:{parts})[а-яё]*-джиу?{WE}")
    for f in ru:
        for p, a, k, s in walk(loaded[f], True, []):
            for m in rx.finditer(s):
                c.hit(name(f), p, snippet(s, m))
    c.report(args.max)

    # L5 — bīju rakstība un «— биджа-мантра» pa vārdam
    c = Check("L5", "bījas: aiṁ/klīṁ/śrīṁ (nav aing/klīng/śrīng); pa vārdam «— биджа-мантра» (katrā valodā savs termins)")
    old = re.compile(WB + "(" + "|".join(map(re.escape, BIJA_OLD)) + ")" + WE, re.I)
    n_bija = 0
    for f in allb:
        term = CFG["bija_term"].get(name(f))
        for p, a, k, s in walk(loaded[f], True, []):
            for m in old.finditer(s):
                c.hit(name(f), p, snippet(s, m))
            if k == "wbw" and term:
                for part in s.split(";"):
                    mm = re.match(r"^\s*[\"«]?(\S+?)\s+[—–-]\s+(.*?)\s*$", part, re.S)
                    if mm and mm.group(1) in BIJA_HEADS:
                        n_bija += 1
                        if mm.group(2).rstrip(".") != term:
                            c.hit(name(f), p, part.strip()[:80])
    c.info = f"{n_bija} bīju glosas"
    c.report(args.max)

    # L6 — у каждого стиха / мантры есть пословный перевод
    c = Check("L6", "katram pantam (verse) un mantrai (⟦… namaḥ⟧ tabulās) ir «пословно» (wbw)")
    tot = 0
    for b in CFG["wbw_required_books"]:
        f = os.path.join(qa.DATA, b)
        for s in loaded[f]["sections"]:
            for ss in [s] + (s.get("subsections") or []):
                where0 = s["id"] if ss is s else f"{s['id']}/{ss['id']}"
                for i, blk in enumerate(ss.get("content") or []):
                    if blk.get("type") == "verse":
                        tot += 1
                        if not (blk.get("wbw") or "").strip():
                            c.hit(b, f"{where0}/#{i} verse", blk.get("sanskrit", "")[:60].replace("\n", " "))
                    if blk.get("type") == "paired-list":
                        for it in blk.get("items", []):
                            txt = (it.get("label") or "") + " " + (it.get("value") or "")
                            if MANTRA_RE.search(txt):
                                tot += 1
                                if not (it.get("wbw") or "").strip():
                                    c.hit(b, f"{where0}/#{i} mantra", txt[:70])
    # other languages: information only (not Satkirti's books in RU)
    other = []
    for f in allb:
        if name(f) in CFG["wbw_required_books"]:
            continue
        vs = []

        def _w(o):
            if isinstance(o, dict):
                if o.get("type") == "verse":
                    vs.append(o)
                for v in o.values():
                    _w(v)
            elif isinstance(o, list):
                for v in o:
                    _w(v)
        _w(loaded[f])
        miss = sum(1 for v in vs if not (v.get("wbw") or "").strip())
        if miss:
            other.append(f"{name(f)} {miss}/{len(vs)}")
    c.info = f"{tot} panti+mantras RU; citās valodās bez wbw (info, nebloķē): " + (", ".join(other) or "nav")
    c.report(args.max)

    # L7 — ⟦ ⟧ marķieri: dati sabalansēti, uzbūvētajā lapā nav redzami
    c = Check("L7", "nav neapstrādātu marķieru ⟦ ⟧ (dati sabalansēti; uzbūvētajās lapās nav redzami)")
    for f in allb:
        for p, a, k, s in walk(loaded[f], True, []):
            depth = 0
            for ch in s:
                if ch == "⟦":
                    depth += 1
                    if depth > 1:
                        break
                elif ch == "⟧":
                    depth -= 1
                    if depth < 0:
                        break
            if depth != 0:
                c.hit(name(f), p, s[:80])
    if not args.no_html:
        n = scan_html(c)
        c.info = f"{n} HTML lapas pārbaudītas" if n else "out/ nav — HTML daļa izlaista"
    c.report(args.max)

    # L8 — nav bengāļu / devanāgarī burtu (sanskrits latīņu IAST)
    c = Check("L8", "nav bengāļu/devanāgarī rakstzīmju (sanskrits — IAST)")
    rx = re.compile(r"[ऀ-ॿঀ-৿]+")
    for f in allb:
        for p, a, k, s in walk(loaded[f], True, []):
            for m in rx.finditer(s):
                c.hit(name(f), p, snippet(s, m, 20))
    c.report(args.max)

    # L9 — нет обрезанных надписей «…» в заголовках интерфейса
    c = Check("L9", "nav «…» nogriezumu UI virsrakstos (daļas, nodaļas, apakšnodaļas, starpvirsraksti, ui.*.json)")
    for f in allb:
        b = loaded[f]
        for pt in b.get("parts", []):
            if "…" in (pt.get("title") or "") or "..." in (pt.get("title") or ""):
                c.hit(name(f), f"part {pt.get('id')}", pt["title"])
        for s in b["sections"]:
            for ss in [s] + (s.get("subsections") or []):
                for key in ("title", "subtitle"):
                    v = ss.get(key) or ""
                    if "…" in v or "..." in v:
                        c.hit(name(f), f"{ss.get('id')}.{key}", v)
                for blk in ss.get("content") or []:
                    if blk.get("type") == "subtitle" and ("…" in blk["content"] or "..." in blk["content"]):
                        c.hit(name(f), f"{ss.get('id')} subtitle", blk["content"][:80])
    for f in sorted(glob.glob(os.path.join(qa.DATA, "ui*.json"))):
        for p, a, k, s in walk(json.load(open(f, encoding="utf-8")), True, []):
            if "…" in s or "..." in s:
                c.hit(name(f), p, s[:80])
    c.report(args.max)

    # L10 — В «Содержании» нет строки «Начало главы»
    c = Check("L10", "«Начало главы» neeksistē (ui.*.json, dati, uzbūvētās lapas)")
    for f in sorted(glob.glob(os.path.join(qa.DATA, "*.json"))):
        s = open(f, encoding="utf-8").read()
        for m in re.finditer("Начало главы", s):
            c.hit(name(f), "", snippet(s, m))
    if not args.no_html:
        for path, text in html_texts():
            if "Начало главы" in text:
                c.hit("out", path, "Начало главы")
    c.report(args.max)

    # L11 — Склонение: Гурудев, Гурудева, Гурудеву, Гурудевом, о Гурудеве (autora teksts)
    c = Check("L11", "«Гурудев» locījumi autora tekstā: -, -а, -у, -ом, -е (nav «Гурудевы/Гурудевой»)")
    rx = re.compile(r"Гурудев(ы|ой|ою|ам|ами|ах)" + WE)
    for f in ru:
        for p, a, k, s in walk(loaded[f], True, []):
            if a:
                for m in rx.finditer(s):
                    c.hit(name(f), p, snippet(s, m))
    c.report(args.max)

    # L12 — Слова Гурудева: с источником (лекция, дата, №, таймкод, ссылка на расшифровку)
    c = Check("L12", "katram Gurudeva citātam (mood) ir avots: lekcija, datums, №, taimkods, transkripta saite")
    n = 0
    for f in ru:
        for ctx_id, m in moods(loaded[f]):
            n += 1
            src = m.get("source") or {}
            miss = [k for k in ("title", "date", "nr", "timecode", "transcript_url") if not str(src.get(k) or "").strip()] if isinstance(src, dict) else ["source"]
            if not (m.get("quote") or "").strip():
                miss.append("quote")
            if miss:
                c.hit(name(f), ctx_id, "trūkst: " + ", ".join(miss))
    c.info = f"{n} citāti"
    c.report(args.max)

    # L13 — «Ещё цитаты»: главная + 3 лучших + «Показать все», всего не больше 20
    c = Check("L13", "«Ещё цитаты»: kopā ar galveno ne vairāk par 20")
    for f in ru:
        for ctx_id, m in moods(loaded[f]):
            if 1 + len(m.get("more") or []) > 20:
                c.hit(name(f), ctx_id, f"{1 + len(m.get('more') or [])} citāti")
    c.report(args.max)

    # L14 — Уже поставленную главную цитату не меняем без прямой просьбы Саткирти; добавлять можно
    c = Check("L14", "galvenie Gurudeva citāti nav mainīti/izņemti (salīdzinājums ar qa/snapshots/main_quotes.json; pievienot drīkst)")
    snap_p = os.path.join(qa.QA_DIR, "snapshots", "main_quotes.json")
    cur = main_quotes(loaded[os.path.join(qa.DATA, "book.ru-iast.json")])
    if args.update_quote_snapshot:
        os.makedirs(os.path.dirname(snap_p), exist_ok=True)
        json.dump(cur, open(snap_p, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
        c.info = f"momentuzņēmums pārrakstīts ({sum(len(v) for v in cur.values())} citāti)"
    elif os.path.exists(snap_p):
        snap = json.load(open(snap_p, encoding="utf-8"))
        for ctx_id, quotes in snap.items():
            for q in quotes:
                if q not in cur.get(ctx_id, []):
                    c.hit("book.ru-iast.json", ctx_id, "galvenais citāts mainīts vai izņemts: «" + q[:70] + "…»")
        c.info = f"{sum(len(v) for v in snap.values())} citāti momentuzņēmumā"
    else:
        c.hit("qa/snapshots/main_quotes.json", "", "nav momentuzņēmuma — palaid: python qa/lint_content.py --update-quote-snapshot")
    c.report(args.max)

    # L15 — Структура книги: «… — The Process of Deity Worship» (без «Temple Manual»); части I/II/III
    c = Check("L15", "grāmatas struktūra: nosaukumā nav «Temple Manual»; daļas I Храмовый / II Домашний / III Проповеднические центры")
    for f in allb:
        b = loaded[f]
        for k in ("title", "subtitle"):
            if "temple manual" in (b.get(k) or "").lower():
                c.hit(name(f), k, b[k])
    ids = [pt.get("id") for pt in loaded[os.path.join(qa.DATA, "book.ru-iast.json")].get("parts", [])]
    if ids[:3] != ["temple-worship", "home-worship", "preaching-centres"]:
        c.hit("book.ru-iast.json", "parts", str(ids))
    c.report(args.max)

    # L16 — «Библиотека» не распространяем; аудио (даршан, лекции) — никогда в приложении
    c = Check("L16", "lietotnē nav audio failu un nav «Библиотека» failu (public/, out/)")
    for root in (os.path.join(qa.REPO, "public"), qa.OUT):
        if not os.path.isdir(root):
            continue
        for dp, dns, fns in os.walk(root):
            for fn in fns + dns:
                low = fn.lower()
                if low.endswith((".mp3", ".m4a", ".wav", ".ogg", ".opus", ".aac", ".flac")) or "библиотек" in low:
                    c.hit(os.path.relpath(root, qa.REPO), os.path.relpath(os.path.join(dp, fn), root), fn)
    c.report(args.max)

    # L18 — Санскрит везде IAST с диакритикой (КСВ 06.10: молитва 9.1 «anga-hinam … krsna-karsna-prasadatah»,
    # мантры маха-абхишеки «idaṁ ksira-snaniyam…»). Heuristika pa vārdiem: sanskrita vārds BEZ neviena
    # diakritiskā simbola ar tipisku ASCII aizvietojumu (ks=kṣ, sh, ng=ṅg, jn=jñ, nc/nj=ñc/ñj, aa/ii/uu, -anīya,
    # rsn/isn=ṣṇ, usp=uṣp, nkh=ṅkh, sri, maha, esa, hum, hina, -bhiyo, vrind) vai vārds, kas beidzas ar
    # patskani+h (visarga «ḥ» kā «h», arī vārdā ar citām diakritikām: «matāh»).
    # Kur: pantu sanskrits (verse.sanskrit) un «пословно» galvas visās latīņu grāmatās; ⟦…⟧ latīņu fragmenti
    # un latīņu starpvirsraksti book.ru-iast.json.
    c = Check("L18", "sanskrits ar IAST diakritiku (nav ASCII aizvietojumu: ksira-snaniyam, krsna, namah …)")
    ascii_mark = re.compile(r"ks|sh|ng|jn|nc|nj|aa|ii|uu|aniy|rsn|isn|usp|nkh|^sri$|^krs|^esa$|^maha$|^hum$|hin[ao]m?$|iyo$|vrind|[aiueo]h$")
    visarga_h = re.compile(r"[aāiīuūeo]h$")
    iast_set = set("āīūṛṝḷḹṅñṭḍṇśṣṁṃḥĀĪŪṚṜḶṄÑṬḌṆŚṢṀṂḤ")
    tok_split = re.compile(r"[\s\-—–,.;:!?()«»\"'’…/\[\]]+")
    latin_word = re.compile(r"[A-Za-zāīūṛṝḷḹṅñṭḍṇśṣṁṃḥĀĪŪṚṜḶṄÑṬḌṆŚṢṀṂḤ]+")

    def ascii_tokens(s):
        bad = []
        for t in tok_split.split(s):
            if not t or not latin_word.fullmatch(t):
                continue
            tl = t.lower()
            if set(tl) & iast_set:
                if visarga_h.search(tl):
                    bad.append(t)
            elif ascii_mark.search(tl):
                bad.append(t)
        return bad

    n18 = 0
    for f in allb:
        if name(f) == "book.ru.json":
            continue  # kirilicas spogulis = translit(book.ru-iast.json)
        is_ri = name(f) == "book.ru-iast.json"

        def w18(o, ctx):
            nonlocal n18
            if isinstance(o, dict):
                if isinstance(o.get("id"), str):
                    ctx = o["id"]
                for k, v in o.items():
                    if isinstance(v, str):
                        units = []
                        if k == "sanskrit":
                            units.append(("verse", v))
                        elif k == "wbw":
                            units.append(("wbw", " ".join(p.split("—")[0] for p in v.split(";"))))
                        elif is_ri and o.get("type") != "mood" and k not in ("quote", "translation", "title", "transcript_url", "audio_url"):
                            units += [("⟦⟧", m.group(1)) for m in re.finditer(r"⟦([^⟧]*)⟧", v) if re.search("[a-z]", m.group(1))]
                            if o.get("type") == "subtitle" and re.search("[a-z]", v):
                                units.append(("subtitle", v))
                        for kind, u in units:
                            n18 += 1
                            bt = ascii_tokens(u)
                            if bt:
                                c.hit(name(f), f"{ctx}/{kind}", ", ".join(bt[:6]) + " | " + u[:60].replace("\n", " / "))
                    else:
                        w18(v, ctx)
            elif isinstance(o, list):
                for v in o:
                    w18(v, ctx)
        w18(loaded[f], "")
    c.info = f"{n18} sanskrita fragmenti"
    c.report(args.max)

    # L19 — В русской книге нет английского текста (КСВ 06.10: «Порядок арчаны» — «(for one leaf) or …
    # (for several leaves)»). Visur RU grāmatās, izņemot Gurudeva vārdus oriģinālā (mood quote), avotu
    # nosaukumus/saites un «…» pēdiņās citētus nosaukumus: ≥2 angļu palīgvārdi vienā virknē = angļu teksts.
    c = Check("L19", "RU grāmatās nav angļu teksta (izņemot Gurudeva vārdus oriģinālā un avotu nosaukumus)")
    en_words = re.compile(r"\b(the|and|or|for|of|with|one|several|to|into|is|are|this|that|from|by|each|leaf|leaves|offer|chant|while|then)\b", re.I)
    for f in ru:
        def w19(o, ctx, key=""):
            if isinstance(o, dict):
                if isinstance(o.get("id"), str):
                    ctx = o["id"]
                for k, v in o.items():
                    if k in ("id", "source", "quote", "image", "src", "alt_en") or (o.get("type") == "mood" and k == "quote"):
                        continue
                    if k == "more":
                        for m in v or []:
                            w19({kk: vv for kk, vv in m.items() if kk not in ("quote", "source")}, ctx)
                        continue
                    w19(v, ctx, k)
            elif isinstance(o, list):
                for v in o:
                    w19(v, ctx, key)
            elif isinstance(o, str):
                t = re.sub(r"«[^»]*»", " ", o)
                t = re.sub(r"https?://\S+", " ", t)
                ms = en_words.findall(t)
                if len(ms) >= 2:
                    c.hit(name(f), f"{ctx}/{key}", ", ".join(ms[:5]) + " | " + o[:70].replace("\n", " / "))
        w19(loaded[f], "")
    c.report(args.max)

    # L21 — Парампара (Satkirti 06.10 23:15–23:33, 07.10 12:34–13:07): 8 гуру по одному на страницу, в этом
    # порядке, подписи как в «Ведических мудрых историях», без Гоур Говинды Свами; тело гуру никогда не обрезается.
    c = Check("L21", "parampara: Śrī Pañca-tattva first, then 8 gurus in order, exact captions, no Gour Govinda Svāmī; every figure fully inside its oval")
    exp = {"ru": PARAMPARA_RU, "en": PARAMPARA_EN}
    for fn, lang in (("book.ru-iast.json", "ru"), ("book.ru.json", "ru"), ("book.json", "en")):
        b = loaded[os.path.join(qa.DATA, fn)]
        ids = [s["id"] for s in b["sections"]]
        if ids[:3] != ["parampara", "mangalacarana", "introduction"]:
            c.hit(fn, "sections", f"order {ids[:3]} (expected parampara → mangalacarana → introduction)")
            continue
        sec = b["sections"][0]
        caps = [x.get("caption") for x in sec["content"] if x.get("type") == "portrait"]
        srcs = [x.get("src") for x in sec["content"] if x.get("type") == "portrait"]
        if sec.get("layout") != "portraits" or caps != exp[lang] or srcs != [f"parampara/{i:02d}.png" for i in range(0, 9)]:
            c.hit(fn, "parampara", f"layout={sec.get('layout')} captions={caps} srcs={srcs}")
        if sec.get("subsections"):
            c.hit(fn, "parampara", "has subsections (headings) — portrait + caption only")
    for f in allb:
        raw = json.dumps(loaded[f], ensure_ascii=False)
        for bad in ("Gour Govinda", "Гоур Говинд", "Gour-Govinda"):
            if bad in raw:
                c.hit(name(f), "*", f"«{bad}» in the book (Satkirti 06.10: not in our parampara)")
    chk = json.load(open(os.path.join(qa.REPO, "scripts", "parampara", "check.json"), encoding="utf-8"))
    for pg in chk["pages"]:
        cx, cy, cw, ch = pg["crop"]
        a, bb = cw / 2, ch / 2
        if abs(cw / ch - chk["aspect"]) > 0.002:
            c.hit("check.json", pg["id"], f"oval aspect {cw / ch:.4f} != {chk['aspect']}")
        import math as _m
        ts = [2 * _m.pi * k / 2880 for k in range(2880)]
        ell = [(cx + a * _m.cos(t), cy + bb * _m.sin(t)) for t in ts]
        for x, y in pg["hull"]:
            q = ((x - cx) / a) ** 2 + ((y - cy) / bb) ** 2
            d = min(_m.hypot(x - ex, y - ey) for ex, ey in ell) / cw
            if q >= 1 or d < chk["margin"] - 0.0005:
                c.hit("check.json", pg["id"], f"contour point {(x, y)} {'OUTSIDE' if q >= 1 else 'too close'} (clearance {d:.3f} < {chk['margin']})")
        img = os.path.join(qa.REPO, "public", "images", pg["image"])
        if not os.path.isfile(img):
            c.hit("public/images", pg["image"], "missing")
        else:
            from PIL import Image as _Img
            with _Img.open(img) as im:
                if list(im.size) != pg["image_size"] or im.mode != "RGBA":
                    c.hit("public/images", pg["image"], f"size/mode {im.size} {im.mode} != check.json {pg['image_size']}")
    if [pg["id"] for pg in chk["pages"]] != [f"{i:02d}" for i in range(0, 9)]:
        c.hit("check.json", "pages", f"{[pg['id'] for pg in chk['pages']]} (expected 00 Pañca-tattva + 01–08)")
    c.info = f"{len(chk['pages'])} portraits re-verified"
    c.report(args.max)

    # L22 — Песни мангала-арати и гаура-арати в книге (Satkirti 07.10 13:07): IAST + пословный перевод + перевод.
    c = Check("L22", "ārati songs: maṅgala-ārati (5) and gaura-ārati (2) in Part IV with IAST, word-by-word and translation")
    for fn in ("book.ru-iast.json", "book.ru.json", "book.json"):
        b = loaded[os.path.join(qa.DATA, fn)]
        secs = {s["id"]: s for s in b["sections"]}
        part = next((p for p in b["parts"] if p["id"] == "festivals-vows"), {"sections": []})
        for sid, n, first in (("mangala-arati-songs", 5, "saṁsāra-dāvānala-līḍha-loka-"),
                              ("gaura-arati-songs", 2, "jaya jaya gorācāṅdera āratiko śobhā")):
            s = secs.get(sid)
            if not s or sid not in part["sections"] or len(s["subsections"]) != n:
                c.hit(fn, sid, f"missing / not in Part IV / {len(s['subsections']) if s else 0} songs (expected {n})")
                continue
            verses = [x for sub in s["subsections"] for x in sub["content"] if x.get("type") == "verse"]
            if fn == "book.ru.json":
                first = None  # Cyrillic mirror
            if first and not verses[0]["sanskrit"].startswith(first):
                c.hit(fn, sid, "first verse is not " + first)
            if fn != "book.json":
                bad = [sub["id"] for sub in s["subsections"] for x in sub["content"]
                       if x.get("type") == "verse" and not (x.get("wbw") and x.get("translation"))]
                if bad:
                    c.hit(fn, sid, f"verses without wbw/translation: {bad[:3]}")
    c.report(args.max)

    # L23 — Название по-русски: «Чайтанья Академия», склоняется только второе слово («в Чайтанья Академии»);
    # никогда «Академия Чайтаньи» (Satkirti 07.10 14:58). Books + their generator sources + RU transcript pages.
    c = Check("L23", "RU name «Чайтанья Академия» (never «Академия Чайтаньи») in books, generators and RU transcripts")
    import re as _re
    bad_ca = _re.compile(r"Академи\w* Чайтаньи")
    bare_ca = _re.compile(r"(?<!Чайтанья )календар\w* Академи\w*")   # bare «календаре Академии» = Chaitanya Academy
    targets = [f for f in allb]
    targets += glob.glob(os.path.join(qa.REPO, "scripts", "chapters", "**", "*.py"), recursive=True)
    targets += glob.glob(os.path.join(qa.REPO, "scripts", "chapters", "**", "*.json"), recursive=True)
    targets += glob.glob(os.path.join(qa.REPO, "scripts", "moods", "*.json"))
    targets += glob.glob(os.path.join(qa.REPO, "public", "transcripts", "*-ru.html"))
    for f in targets:
        raw = open(f, encoding="utf-8").read()
        for rx in (bad_ca, bare_ca):
            for m in rx.finditer(raw):
                c.hit(os.path.relpath(f, qa.REPO), "*", f"«{m.group(0)}» → «Чайтанья Академи…»")
    c.info = f"{len(targets)} files"
    c.report(args.max)

    # L24 — Песни/бхаджаны (Satkirti 07.10 16:05): заголовок по-русски, затем ОДНА строка — автор, затем стихи
    # в IAST; без строк-источников под песнями и без повторного заголовка латиницей. Song section = any
    # subsection «song-…» (all songs / stotras of the book, also future ones).
    c = Check("L24", "songs: RU heading → one author line → ≥1 verse (IAST); no source lines, no repeated title")
    # v7.6.1 (Codex review of v7.5): broader source patterns; EVERY non-verse block is counted (the old
    # `[:1]` slice let a second block after the verses through); heading Cyrillic in RU; verses IAST in
    # ru-iast / en (Cyrillic only in the retired book.ru.json mirror).
    src_rx = re.compile(r"(?i)purebhakti|G[īi]ti[- ]?guccha|\bGVP\b|https?://|www\.|Источник|\bизд(?:\.|ание|ательств)"
                        r"|\bс\. ?\d|\bpp?\. ?\d|\bed\.|Publications|\bSource")
    cyr = re.compile(r"[А-Яа-яЁё]")
    lat = re.compile(r"[A-Za-z]")
    iast_d = re.compile(r"[āīūṛṝḷṅñṭḍṇśṣṁḥĀĪŪṚṜḶṄÑṬḌṆŚṢṀḤ]")
    nsongs = 0
    for fn in ("book.ru-iast.json", "book.ru.json", "book.json"):
        b = loaded[os.path.join(qa.DATA, fn)]
        ru = fn != "book.json"
        for s in b["sections"]:
            subs = [sub for sub in (s.get("subsections") or []) if str(sub.get("id", "")).startswith("song-")]
            if subs:
                # the chapter's own introduction: no source lines either
                for i, x in enumerate(s.get("content") or []):
                    t = json.dumps(x, ensure_ascii=False)
                    if x.get("type") == "sources" or src_rx.search(t):
                        c.hit(fn, f"{s['id']}[{i}]", f"source line in a song chapter: {t[:90]}")
            for sub in subs:
                nsongs += 1
                items = sub.get("content") or []
                where = f"{s['id']}/{sub['id']}"
                title = str(sub.get("title") or "").strip()
                if not title:
                    c.hit(fn, where, "song without a heading")
                elif ru and (not cyr.search(title) or lat.search(title) or iast_d.search(title)):
                    c.hit(fn, where, f"RU song heading not in Russian (Cyrillic): «{title}»")
                for i, x in enumerate(items):
                    if x.get("type") == "verse":
                        continue
                    t = x.get("content") if isinstance(x.get("content"), str) else json.dumps(x, ensure_ascii=False)
                    if x.get("type") == "sources" or src_rx.search(t):
                        c.hit(fn, f"{where}[{i}]", f"source line under a song: {t[:90]}")
                others = [i for i, x in enumerate(items) if x.get("type") != "verse"]
                verses = [x for x in items if x.get("type") == "verse"]
                if not items or items[0].get("type") != "text" or others != [0]:
                    c.hit(fn, where, f"exactly one author line, first (non-verse blocks at {others}, "
                                     f"types {[items[i].get('type') for i in others]})")
                if not verses:
                    c.hit(fn, where, "no verses")
                for k, v in enumerate(verses, 1):
                    sk = str(v.get("sanskrit") or "")
                    if fn == "book.ru.json":
                        bad_v = not sk.strip() or lat.search(sk)
                    else:
                        bad_v = not sk.strip() or cyr.search(sk) or not lat.search(sk) or not iast_d.search(sk)
                    if bad_v:
                        c.hit(fn, f"{where} v{k}", f"verse text not {'Cyrillic' if fn == 'book.ru.json' else 'IAST'}: {sk[:60]!r}")
                if not items or items[0].get("type") != "text":
                    continue
                a = str(items[0].get("content") or "")
                if not a.strip():
                    c.hit(fn, where, "empty author line")
                    continue
                # RU: the author in Cyrillic, no ⟦…⟧ (IAST) at all; EN: at most one ⟦…⟧ (the author), no « — ».
                # (v7.6: the EN author lines of the Kārtika bhajans are plain English sentences without ⟦…⟧ —
                # «exactly one» became «at most one»; the repeated title is checked directly below.)
                if (ru and "⟦" in a) or (not ru and (a.count("⟦") > 1 or " — " in a)) or "\n" in a:
                    c.hit(fn, where, f"author line carries a title / IAST: {a[:90]}")
                if ru and (not cyr.search(a) or iast_d.search(a)):
                    c.hit(fn, where, f"RU author line not in Cyrillic: {a[:90]}")
                plain = a.replace("⟦", "").replace("⟧", "").lower()
                tl = title.lower()
                core = re.sub(r"\s*\(.*?\)\s*", " ", tl).strip()   # title without its «(…)» alias
                if tl and (tl in plain or (len(core) >= 6 and core in plain)):
                    c.hit(fn, where, f"author line repeats the song title «{title}»: {a[:90]}")
    c.info = f"{nsongs} songs (RU, RU Cyrillic, EN)"
    c.report(args.max)

    # L25 — «Бхаджаны для Картики» (Reader v7.6, 07.10.2026): new chapter right after «Песни гаура-арати» in
    # Part IV; 3 songs with 8 / 9 / 13 verses (Rādhā-kṛpā-kaṭākṣa: GVP's 13), IAST with diacritics, every verse
    # with word-by-word + translation, no source lines (L24 covers the song format of this chapter as well).
    c = Check("L25", "Kārtika bhajans: after gaura-ārati in Part IV, 3 songs (8/9/13 verses), IAST diacritics, no sources")
    want = [("song-damodarastakam", 8, "namāmīśvaraṁ sac-cid-ānanda-rūpaṁ"),
            ("song-nanda-nandanastakam", 9, "sucāru-vaktra-maṇḍalaṁ sukarṇa-ratna-kuṇḍalam"),
            ("song-radha-krpa-kataksa-stava-raja", 13, "munīndra-vṛnda-vandite tri-loka-śoka-hāriṇī")]
    diac = re.compile(r"[āīūṛṝḷṅñṭḍṇśṣṁḥ]")
    nk = 0
    for f in allb:
        fn = os.path.basename(f)
        b = loaded[f]
        part = next((p for p in b["parts"] if p["id"] == "festivals-vows"), {"sections": []})["sections"]
        if "kartika-bhajans" not in part or "gaura-arati-songs" not in part \
                or part.index("kartika-bhajans") != part.index("gaura-arati-songs") + 1:
            c.hit(fn, "parts/festivals-vows", f"kartika-bhajans not right after gaura-arati-songs: {part}")
        if fn not in ("book.ru-iast.json", "book.ru.json", "book.json"):
            continue  # other languages: English fallback until the night translation run
        ids = [s["id"] for s in b["sections"]]
        if "kartika-bhajans" not in ids or ids.index("kartika-bhajans") != ids.index("gaura-arati-songs") + 1:
            c.hit(fn, "sections", "kartika-bhajans missing / not right after gaura-arati-songs")
            continue
        nk += 1
        s = b["sections"][ids.index("kartika-bhajans")]
        subs = s.get("subsections") or []
        if [x["id"] for x in subs] != [w[0] for w in want]:
            c.hit(fn, "kartika-bhajans", f"songs {[x['id'] for x in subs]} != {[w[0] for w in want]}")
            continue
        for sub, (sid, n, first) in zip(subs, want):
            vs = [x for x in sub["content"] if x.get("type") == "verse"]
            if len(vs) != n:
                c.hit(fn, sid, f"{len(vs)} verses (expected {n})")
            if any(not (v.get("wbw") and v.get("translation")) for v in vs):
                c.hit(fn, sid, "verse without word-by-word / translation")
            if fn != "book.ru.json":   # ru = Cyrillic mirror of the IAST
                if vs and not vs[0]["sanskrit"].startswith(first):
                    c.hit(fn, sid, "first verse is not " + first)
                nodiac = [i + 1 for i, v in enumerate(vs) if not diac.search(v["sanskrit"])]
                if nodiac:
                    c.hit(fn, sid, f"verses without IAST diacritics: {nodiac}")
            for x in sub["content"]:
                t = x.get("content") if isinstance(x.get("content"), str) else ""
                if x.get("type") == "sources" or src_rx.search(t) or re.search(r"Источник|Source", t):
                    c.hit(fn, sid, f"source line: {t[:90]}")
        if fn == "book.ru-iast.json" and not any("Чайтанья Академи" in x.get("content", "") for x in s.get("content") or []):
            c.hit(fn, "kartika-bhajans", "intro sentence with «Чайтанья Академии» missing")
    c.info = f"chapter checked in {nk} books (RU, RU Cyrillic, EN); part list in {len(allb)} books"
    c.report(args.max)

    # L26 — Глава 3 «16 предметов» и глава 14: список = рисунок Parafernalia.png (Satkirti 07.10.2026 22:28):
    # каждому номеру рисунка 1–18 — ровно одна строка, по порядку рисунка, и название строки — тот же предмет,
    # что на рисунке (то же соответствие, что в главе 14). Предметы без номера — после нумерованных.
    c = Check("L26", "ch3 + ch14 list = figure Parafernalia.png: numbers 1–18 one row each, in order, row names = figure objects")
    FIG = {  # figure number -> (RU words, EN words); every word must be in the row (case-insensitive)
        "1": (["панча-патра"], ["pañca-pātra"]), "2": (["раковина", "омовения"], ["bathing", "conch"]),
        "3": (["колокольчик"], ["bell"]), "4": (["дхупа"], ["dhūpa"]), "5": (["дипа"], ["dīpa"]),
        "6": (["висарджания-патра"], ["visarjanīya-pātra"]), "7": (["пуджа-патра", "божества"], ["pūjā-pātra", "deity"]),
        "8": (["снана-патра", "божества"], ["snāna-pātra", "deity"]), "9": (["пуджа-патра", "гурудева"], ["pūjā-pātra", "gurudeva"]),
        "10": (["снана-патра", "гурудева"], ["snāna-pātra", "gurudeva"]), "11": (["асана", "божества"], ["āsana", "deity"]),
        "12": (["асана", "пуджари"], ["āsana", "pujārī"]), "13": (["сосуд для воды"], ["water-pot"]),
        "14": (["цветы"], ["flowers"]), "15": (["туласи"], ["tulasī"]), "16": (["чандана"], ["candana"]),
        "17": (["мадхупарка"], ["madhuparka"]), "18": (["раковина", "трубят"], ["blowing", "conch"])}
    hs = json.load(open(os.path.join(qa.DATA, "hotspots.json"), encoding="utf-8"))["Parafernalia.png"]["spots"]
    if sorted(hs, key=int) != list(FIG):
        c.hit("hotspots.json", "Parafernalia.png", f"figure numbers {sorted(hs, key=int)} != 1–18")
    nl = 0
    for fn, k in (("book.ru-iast.json", 0), ("book.ru.json", 0), ("book.json", 1)):
        b = loaded[os.path.join(qa.DATA, fn)]
        for sid, subid in (("worship-sixteen-articles", "required-paraphernalia"), ("main-worship-sixteen-items", "main-worship-paraphernalia")):
            s_ = next((x for x in b["sections"] if x["id"] == sid), None)
            ss = next((x for x in (s_ or {}).get("subsections") or [] if x["id"] == subid), None)
            lst = next((x for x in (ss or {}).get("content") or [] if x.get("type") == "list" and x.get("numbers")), None)
            if not lst:
                c.hit(fn, f"{sid}/{subid}", "numbered list missing")
                continue
            nl += 1
            rows = [r for r in lst["content"].split(chr(10)) if r.strip()]
            nums = lst["numbers"]
            numbered = [n for n in nums if n]
            if numbered != list(FIG) or nums[:18] != list(FIG) or len(nums) != len(rows):
                c.hit(fn, f"{sid}/{subid}", f"numbers {numbered} (expected 1–18 in order, first, one each; {len(nums)} numbers / {len(rows)} rows)")
                continue
            for n, row in zip(nums[:18], rows):
                low = row.replace("⟦", "").replace("⟧", "").lower()
                miss = [w for w in FIG[n][k] if w.lower() not in low]
                if miss:
                    c.hit(fn, f"{sid}/{subid} №{n}", f"row «{row[:60]}» does not name the figure object ({miss})")
    c.info = f"{nl} lists (ch3 + ch14 × RU, RU Cyrillic, EN) against 18 figure objects"
    c.report(args.max)

    # L17 — Откат: метка pirms-interfeisa-2026-10-05 существует
    c = Check("L17", "atgriešanās punkts: git tags pirms-interfeisa-2026-10-05 eksistē")
    import subprocess
    r = subprocess.run(["git", "rev-parse", "-q", "--verify", "refs/tags/pirms-interfeisa-2026-10-05"], cwd=qa.REPO,
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if r.returncode != 0:
        c.hit("git", "refs/tags", "tags pirms-interfeisa-2026-10-05 nav atrasts")
    c.report(args.max)

    # L20 — OneDrive «desktop.ini» zem .git/refs salauž git (fetch/pull: «broken ref refs/…/desktop.ini»;
    # 06.10). Labojums: izdzēst TIKAI šos desktop.ini failus zem .git/refs.
    c = Check("L20", "zem .git/refs nav OneDrive desktop.ini (citādi git fetch/pull lūzt)")
    r = subprocess.run(["git", "rev-parse", "--git-dir"], cwd=qa.REPO, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    if r.returncode == 0:
        gd = r.stdout.strip()
        refs = os.path.join(gd if os.path.isabs(gd) else os.path.join(qa.REPO, gd), "refs")
        for dp, dns, fns in os.walk(refs):
            for fn in fns:
                if fn.lower() == "desktop.ini":
                    c.hit("git", os.path.relpath(os.path.join(dp, fn), qa.REPO), "izdzēs šo failu (tikai to)")
    c.report(args.max)


def moods(book):
    """(nearest id, mood block) for every Gurudeva quote block."""
    out = []

    def w(o, ctx_id):
        if isinstance(o, dict):
            if isinstance(o.get("id"), str):
                ctx_id = o["id"]
            if o.get("type") == "mood":
                out.append((ctx_id, o))
            for v in o.values():
                w(v, ctx_id)
        elif isinstance(o, list):
            for v in o:
                w(v, ctx_id)
    w(book, "")
    return out


def main_quotes(book):
    cur = {}
    for ctx_id, m in moods(book):
        cur.setdefault(ctx_id, []).append((m.get("quote") or "").strip())
    return cur

_HTML_CACHE = []


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "template"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "template") and self.skip:
            self.skip -= 1

    def handle_data(self, d):
        if not self.skip:
            self.out.append(d)


def html_texts():
    """(relative path, visible text) of every book page in out/ (cached)."""
    if _HTML_CACHE:
        return _HTML_CACHE
    if not os.path.isdir(qa.OUT):
        return []
    for d in CFG["rendered_html_dirs"]:
        root = os.path.join(qa.OUT, d)
        if not os.path.isdir(root):
            continue
        for sub in sorted(os.listdir(root)):
            f = os.path.join(root, sub, "index.html")
            if d == "" and sub in CFG["rendered_html_dirs"]:
                continue
            if os.path.isfile(f):
                p = _Text()
                p.feed(open(f, encoding="utf-8").read())
                _HTML_CACHE.append((os.path.relpath(f, qa.OUT).replace(os.sep, "/"), "".join(p.out)))
    return _HTML_CACHE


def scan_html(c):
    pages = html_texts()
    for path, text in pages:
        for m in re.finditer("[⟦⟧]", text):
            c.hit("out", path, snippet(text, m))
    return len(pages)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-html", action="store_true", help="skip the out/ (built pages) part")
    ap.add_argument("--max", type=int, default=8, help="examples per failed check")
    ap.add_argument("--json", help="write results here")
    ap.add_argument("--update-quote-snapshot", action="store_true",
                    help="pārrakstīt qa/snapshots/main_quotes.json (TIKAI pēc Satkirti tieša lūguma mainīt galveno citātu)")
    args = ap.parse_args()
    print("lint_content: data/ + out/", flush=True)
    run(args)
    print()
    print(f"{sum(1 for r in RESULTS if r['ok'])}/{len(RESULTS)} passed")
    if args.json:
        json.dump(RESULTS, open(args.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if FAILS:
        print("LINT FAILED: " + ", ".join(FAILS))
        sys.exit(1)


if __name__ == "__main__":
    main()
