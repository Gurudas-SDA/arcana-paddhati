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
    "Шрила Бхакти Прагьяна Кешава Госвами Махарадж",   # Satkirti 11.10 msg 2361: jñ = «гья»
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
    # Night 08.10: the other language books — same page order, oval pictures, 9 captions (translated), no headings.
    for f in allb:
        fn = name(f)
        if fn in ("book.ru-iast.json", "book.ru.json", "book.json"):
            continue
        b = loaded[f]
        ids = [s["id"] for s in b["sections"]]
        if ids[:3] != ["parampara", "mangalacarana", "introduction"]:
            c.hit(fn, "sections", f"order {ids[:3]} (expected parampara → mangalacarana → introduction)")
            continue
        sec = b["sections"][0]
        caps = [x.get("caption") for x in sec["content"] if x.get("type") == "portrait"]
        srcs = [x.get("src") for x in sec["content"] if x.get("type") == "portrait"]
        if sec.get("layout") != "portraits" or len(caps) != 9 or not all(caps) or srcs != [f"parampara/{i:02d}.png" for i in range(0, 9)] or sec.get("subsections"):
            c.hit(fn, "parampara", f"layout={sec.get('layout')} captions={caps} srcs={srcs}")
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
    # Night 08.10: also every other language book (lv, de, …: translated headings/authors, IAST verses as in EN).
    for fn in [name(f) for f in allb]:
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
            if fn in ("book.ru-iast.json", "book.ru.json"):
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
    for fn in [name(f) for f in allb]:   # Night 08.10: every language book (other languages: EN rules)
        b = loaded[os.path.join(qa.DATA, fn)]
        ru = fn in ("book.ru-iast.json", "book.ru.json")
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
    c.info = f"{nsongs} songs in {len(allb)} books"
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
        # Night 08.10: the other languages have the chapter too (translated by scripts/translate/night_sync.py)
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
    c.info = f"chapter checked in {nk} books; part list in {len(allb)} books"
    c.report(args.max)

    # L26 — Глава 3 «16 предметов» и глава 14: список = рисунок Parafernalia.png (Satkirti 07.10.2026 22:28):
    # каждому номеру рисунка 1–18 — ровно одна строка, по порядку рисунка, и название строки — тот же предмет,
    # что на рисунке (то же соответствие, что в главе 14). Предметы без номера — после нумерованных.
    # v7.8.1 (Codex review): ВСЕ языки книги; в гл. 3 первая строка без номера = pādya/arghya/ācamana (по содержанию).
    c = Check("L26", "ch3 + ch14 list = figure Parafernalia.png in every language: numbers 1–18 one row each, in order, row names = figure objects; ch3 unnumbered row = pādya/arghya/ācamana")
    import unicodedata

    def fold(t):  # lower case, no diacritics, no ⟦⟧ (keywords are written the same way)
        t = unicodedata.normalize("NFD", t.replace("⟦", "").replace("⟧", "").lower().replace("ı", "і"))  # Ukrainian ı̄ (dotless + macron) = і
        return "".join(ch for ch in t if not unicodedata.combining(ch))

    # figure number -> keywords per language; every keyword must be in the row ("a|b" = either)
    FIG = {
        "ru": ["панча-патра", "раковина омовения", "колокольчик", "дхупа", "дипа", "висарджания-патра", "пуджа-патра божества",
               "снана-патра божества", "пуджа-патра гурудева", "снана-патра гурудева", "асана божества", "асана пуджари",
               "сосуд воды", "цветы", "туласи", "чандана", "мадхупарка", "раковина трубят"],
        "en": ["panca-patra", "bathing conch", "bell", "dhupa", "dipa", "visarjaniya-patra", "puja-patra deity", "snana-patra deity",
               "puja-patra gurudeva", "snana-patra gurudeva", "asana deity", "asana pujari", "water-pot", "flowers", "tulasi",
               "candana", "madhuparka", "blowing conch"],
        "lv": ["panca-patra", "mazgasanas|udenim gliemeznica", "zvanin", "dhupa", "dipa", "visardzanija-patra", "pudza-patra dievib",
               "snana-patra dievib", "pudza-patra gurudev", "snana-patra gurudev", "asana dievib", "asana pudzari", "udens trauk",
               "ziedi", "tulasi", "candana", "madhuparka", "pusama gliemeznica"],
        "de": ["panca-patra", "wassermuschelhorn|bademuschelhorn", "glocke", "dhupa", "dipa", "visarjaniya-patra", "puja-patra bildgestalt",
               "snana-patra bildgestalt", "puja-patra gurudeva", "snana-patra gurudeva", "asana bildgestalt", "asana pujari",
               "wassergef", "blumen", "tulasi", "candana", "madhuparka", "muschelhorn blasen"],
        "es": ["panca-patra", "caracola bano", "campana", "dhupa", "dipa", "visarjaniya-patra", "puja-patra deidad", "snana-patra deidad",
               "puja-patra gurudeva", "snana-patra gurudeva", "asana deidad", "asana pujari", "recipiente agua", "flores", "tulasi",
               "candana", "madhuparka", "caracola soplar"],
        "fr": ["panca-patra", "conque bain", "cloche", "dhupa", "dipa", "visarjaniya-patra", "puja-patra divinite", "snana-patra divinite",
               "puja-patra gurudeva", "snana-patra gurudeva", "asana divinite", "asana pujari", "pot|eau", "fleurs", "tulasi",
               "candana", "madhuparka", "conque souffler"],
        "hu": ["panca-patra", "furdeteshez kagylokurt", "csengo", "dhupa", "dipa", "visarjaniya-patra", "puja-patra istenseg",
               "snana-patra istenseg", "puja-patra gurudeva", "snana-patra gurudeva", "asana istenseg", "asana pujari",
               "vizesedeny|vizeskorso", "viragok", "tulasi", "candana", "madhuparka", "megfujhato kagylokurt"],
        "it": ["panca-patra", "conchiglia bagno", "campana", "dhupa", "dipa", "visarjaniya-patra", "puja-patra divinita", "snana-patra divinita",
               "puja-patra gurudeva", "snana-patra gurudeva", "asana divinita", "asana pujari", "recipiente acqua", "fiori", "tulasi",
               "candana", "madhuparka", "conchiglia soffiare"],
        "pt": ["panca-patra", "buzio banho", "sino", "dhupa", "dipa", "visarjaniya-patra", "puja-patra deidade", "snana-patra deidade",
               "puja-patra gurudeva", "snana-patra gurudeva", "asana deidade", "asana pujari", "jarro agua", "flores", "tulasi",
               "candana", "madhuparka", "buzio soprar"],
        "lt": ["panca-patra", "maudymo kriaukle", "varpel", "dhupa", "dipa", "visarjaniya-patra", "puja-patra dievyb", "snana-patra dievyb",
               "puja-patra gurudev", "snana-patra gurudev", "asana dievyb", "asana pujari", "vandens ind", "geles", "tulasi",
               "candana", "madhuparka", "puciamoji kriaukle"],
        "uk": ["панча-патра", "мушля омовіння", "дзвіночок", "дгупа", "діпа", "вісарджан", "пуджа-патра божества",
               "снана-патра божества", "пуджа-патра ґурудева", "снана-патра ґурудева", "асана божества", "асана пуджарі",
               "посудина води", "квіти", "туласі", "чандана", "мадгупарка", "мушля сурмлення"],
    }
    # ch3 first unnumbered row: pādya / arghya / ācamana pātra (each word stem must be there)
    TAIL = {"ru": ["падья", "аргхья", "ачамана"], "uk": ["падья", "арґгья", "ачамана"],
            "lv": ["padja", "arghja", "acamana"], "_": ["padya", "argya|arghya", "acamana"]}
    LANGF = {"book.ru-iast.json": "ru", "book.ru.json": "ru", "book.json": "en"}
    for f in sorted(glob.glob(os.path.join(qa.DATA, "book.*.json"))):
        m_ = re.match(r"book\.([a-z]+)\.json$", os.path.basename(f))
        if m_ and m_.group(1) in FIG:
            LANGF[os.path.basename(f)] = m_.group(1)
    hs = json.load(open(os.path.join(qa.DATA, "hotspots.json"), encoding="utf-8"))["Parafernalia.png"]["spots"]
    NUMS = [str(i) for i in range(1, 19)]
    if sorted(hs, key=int) != NUMS:
        c.hit("hotspots.json", "Parafernalia.png", f"figure numbers {sorted(hs, key=int)} != 1–18")
    for f in sorted(glob.glob(os.path.join(qa.DATA, "book*.json"))):
        if os.path.basename(f) not in LANGF:
            c.hit(os.path.basename(f), "L26", "language has no figure keywords in L26 (add them)")
    nl = 0
    for fn, lg in LANGF.items():
        b = loaded.get(os.path.join(qa.DATA, fn)) or json.load(open(os.path.join(qa.DATA, fn), encoding="utf-8"))
        kw = [[[fold(alt) for alt in w.split("|")] for w in row.split()] for row in FIG[lg]]
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
            if numbered != NUMS or nums[:18] != NUMS or len(nums) != len(rows):
                c.hit(fn, f"{sid}/{subid}", f"numbers {numbered} (expected 1–18 in order, first, one each; {len(nums)} numbers / {len(rows)} rows)")
                continue
            for n, row, words in zip(NUMS, rows, kw):
                low = fold(row)
                miss = ["|".join(w) for w in words if not any(alt in low for alt in w)]
                if miss:
                    c.hit(fn, f"{sid}/{subid} №{n}", f"row «{row[:60]}» does not name the figure object ({miss})")
            if sid == "worship-sixteen-articles":
                tail = rows[18] if len(rows) > 18 else ""
                tw = [[fold(a) for a in w.split("|")] for w in TAIL.get(lg, TAIL["_"])]
                if not tail or not all(any(a in fold(tail) for a in w) for w in tw):
                    c.hit(fn, f"{sid}/{subid} row 19 (unnumbered)", f"«{tail[:60]}» is not the pādya / arghya / ācamana row")
    c.info = f"{nl} lists (ch3 + ch14 × {len(LANGF)} book files) against 18 figure objects"
    c.report(args.max)

    # L27 — Санскрит не переводится (Reader v7.8.3, Codex review of e8d33aa..bb066eb: «Mahā-mantra» in
    # guru-pankti-namaskara was localized in lv/de/fr/es/it/uk, the Ukrainian one even in Cyrillic). WHOLE books,
    # not only the night-synced sections: every `sanskrit` field of a translated book (lv, de, fr, es, it, uk, hu)
    # is byte-identical to the same field of book.json; the same fields exist. The RU pair is the source text:
    # book.ru.json is its Cyrillic transliteration (not compared). Night 09.10 (A68, Gurudas 08.10): book.ru-iast.json
    # is strict too — EN spelled after RU-IAST and the sources, RU glosses moved out of the field; a difference is a hit.
    c = Check("L27", "Sanskrit identical in every language: each `sanskrit` field of ru-iast/lv/de/fr/es/it/uk/hu/pt/lt = book.json (byte-identical)")

    def sk_fields(o, path=()):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "sanskrit":
                    yield "/".join(map(str, path + (k,))), v
                yield from sk_fields(v, path + (k,))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                yield from sk_fields(v, path + ((v.get("id") if isinstance(v, dict) and isinstance(v.get("id"), str) else i),))

    en_path = os.path.join(qa.DATA, "book.json")
    en_sk = dict(sk_fields(loaded[en_path])) if en_path in loaded else {}
    en_pending = {s.get("id") for s in (loaded[en_path].get("sections") or []) if isinstance(s, dict)
                  and s.get("translation_pending")} if en_path in loaded else set()
    ru_pair = set(CFG["ru_books"])
    nb = 0
    for f in allb:
        fn = name(f)
        if f == en_path:
            continue
        sk = dict(sk_fields(loaded[f]))
        if fn in ru_pair and fn != "book.ru-iast.json":
            continue
        nb += 1
        for k, v in sk.items():
            if k not in en_sk:
                c.hit(fn, k, f"«{v[:60]}» — no such sanskrit field in book.json")
            elif v != en_sk[k]:
                i = next((j for j in range(min(len(v), len(en_sk[k]))) if v[j] != en_sk[k][j]), min(len(v), len(en_sk[k])))
                c.hit(fn, k, f"«…{v[max(0, i - 20):i + 30]}» ≠ EN «…{en_sk[k][max(0, i - 20):i + 30]}»".replace("\n", " / "))
        # compared by the EN paths (v7.8.4, Codex review): a whole top-level section missing in this book
        # is reported too — every sanskrit field of it, not skipped
        have = {s.get("id") for s in loaded[f].get("sections") or [] if isinstance(s, dict)}
        for k in en_sk:
            if k not in sk:
                parts = k.split("/")
                gone = len(parts) > 1 and parts[0] == "sections" and parts[1] not in have
                # A83 (Satkirti 14.10 msg 3478 «одним языком, рус»): a chapter written in Russian only is in
                # book.json as the RU text marked "translation_pending"; until it is translated, a translated
                # book without that whole section shows the book.json section (lib/content.ts fallback, with
                # the "translation in preparation" note) — the same Sanskrit, nothing localized.
                if gone and fn not in ru_pair and parts[1] in en_pending:
                    continue
                c.hit(fn, k, "sanskrit field of book.json missing in this book"
                      + (f" (the whole section «{parts[1]}» is missing)" if gone else ""))
    c.info = f"{len(en_sk)} sanskrit fields × {nb} books (ru-iast + translated)"
    c.report(args.max)

    # L28 — Анусвара в IAST всегда «ṁ» (U+1E41), никогда «ṃ» (U+1E43) (Reader v7.8.3, live verifier 08.10:
    # «pṛthvi tvayā dhṛtā…» ch3.2 had «tvaṃ»). Every string of every book + ui file, and the night-sync sources
    # (scripts/translate/cache/**, generator i18n.json) — they would bring it back. Lecture transcripts are
    # sources quoted as they are (not checked).
    c = Check("L28", "IAST anusvāra is «ṁ» everywhere — no «ṃ/Ṃ» in books, ui files, translation caches, generator i18n.json")
    # v7.8.4 (Codex review): the JSON is decoded and every key / value checked after NFC normalization —
    # «m» + U+0323 (decomposed) and «ṃ» escapes are caught too, not only the raw characters of a line
    import unicodedata
    bad_m = re.compile("[Ṃṃ]")
    srcs = allb + books("ui*.json")
    srcs += glob.glob(os.path.join(qa.REPO, "scripts", "translate", "cache", "**", "*.json"), recursive=True)
    srcs += glob.glob(os.path.join(qa.REPO, "scripts", "**", "i18n.json"), recursive=True)

    def str_walk(o, path=""):
        if isinstance(o, str):
            yield path, o
        elif isinstance(o, dict):
            for k, v in o.items():
                yield f"{path}/{k} (key)", k
                yield from str_walk(v, f"{path}/{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                yield from str_walk(v, f"{path}/{i}")

    for f in srcs:
        rel = os.path.relpath(f, qa.REPO).replace("\\", "/")
        try:
            data = json.load(open(f, encoding="utf-8"))
        except ValueError as e:
            c.hit(rel, "json", f"not valid JSON ({str(e)[:60]}) — cannot check")
            continue
        for where, t in str_walk(data):
            n = unicodedata.normalize("NFC", t)
            for m in bad_m.finditer(n):
                raw = "" if t == n else " (decomposed m + U+0323)"
                c.hit(rel, where or "/", snippet(n, m, 25) + raw)
    c.info = f"{len(srcs)} files (decoded JSON, NFC)"
    c.report(args.max)

    # L29 — jñ в русском тексте = «гья» (Прагьяна, гьяна, гьяни, вигьяна, адвая-гьяна); санскрит с диакритикой
    # остаётся «джн̃» (кириллица) / «jñ» (IAST) (Satkirti 11.10.2026 23:25, msg 2361; анализ
    # «Праджняна или Праджнана — анализ» 08.10). Ловит «джн» без тильды (U+0303) в RU-книгах и в их
    # генераторах (chapter_ru.py, moods.json ru/ru-iast, parampara) — иначе ночной генератор вернёт старое.
    # Расшифровки лекций — источники как есть (не проверяются).
    c = Check("L29", "RU text: jñ = «гья» (Прагьяна, гьяна), not «джн(я/а)»; Sanskrit with diacritics «джн̃»/«jñ» unchanged")
    bad_jn = re.compile("[Дд]жн(?!̃)")   # «Дж/дж» + «н» not followed by combining tilde
    ru_jn = [os.path.join(qa.DATA, b) for b in CFG["ru_books"]]
    for f in ru_jn:
        for p, a, k, s in walk(loaded[f], True, []):
            for m in bad_jn.finditer(s):
                c.hit(name(f), p, snippet(s, m, 30))
    gen = glob.glob(os.path.join(qa.REPO, "scripts", "chapters", "*", "chapter_ru.py"))
    gen += glob.glob(os.path.join(qa.REPO, "scripts", "chapters", "*", "en_cache.json"))   # RU keys
    gen += glob.glob(os.path.join(qa.REPO, "scripts", "chapters", "*", "pesni_arati.json"))
    gen += [os.path.join(qa.REPO, "scripts", "parampara", "apply_parampara.py")]
    for f in gen:
        if not os.path.exists(f):
            continue
        raw = open(f, encoding="utf-8").read()
        for m in bad_jn.finditer(raw):
            c.hit(os.path.relpath(f, qa.REPO).replace("\\", "/"), "*", snippet(raw, m, 30))
    mp = os.path.join(qa.REPO, "scripts", "moods", "moods.json")
    n_gen = len(gen)
    if os.path.exists(mp):
        n_gen += 1

        def ru_vals(o, path=""):
            if isinstance(o, dict):
                for k2, v in o.items():
                    if k2 in ("ru", "ru-iast") and isinstance(v, str):
                        yield f"{path}/{k2}", v
                    else:
                        yield from ru_vals(v, f"{path}/{k2}")
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    yield from ru_vals(v, f"{path}/{i}")
        for where, t in ru_vals(json.load(open(mp, encoding="utf-8"))):
            for m in bad_jn.finditer(t):
                c.hit("scripts/moods/moods.json", where, snippet(t, m, 30))
    c.info = f"{len(ru_jn)} RU books + {n_gen} generator files"
    c.report(args.max)

    # L30 — A80 (Satkirti 12.10.2026 23:00, msg 2615): Ukrainian text like krishna.ua — no extra dots/lines above or
    # under letters, no missing letters (Кр̣шн̣а -> Крішна, ai -> ай, y -> ья/’я, jñ -> гья, th/kh -> тх/кх).
    # Rules: «Arcana-paddhati/Правила украинского написания (krishna.ua).md». Checked: book.uk.json + ui.uk.json (every
    # string except `sanskrit`) and the sources that would bring the old spelling back at night: the «uk» part of
    # generator i18n.json, moods.json translations.uk, glossary.uk.json. Latin IAST is never checked here.
    c = Check("L30", "UK text as on krishna.ua: no diacritics over/under Cyrillic letters, no missing letters (Крішна, вайшнав, Чайтанья, Нітьянанда, гья)")
    import unicodedata
    UKC = "А-Яа-яІіЇїЄєҐґ"
    UKCONS = "бвгґджзклмнпрстфхцчшщБВГҐДЖЗКЛМНПРСТФХЦЧШЩ"
    uk_rules = [
        ("diacritic", re.compile(f"[{UKC}ı][̀-ͯ]|[ıӯӮӣӢӀӏ]|(?<=[{UKC}])[āīūĀĪŪ]|[āīūĀĪŪ](?=[{UKC}])")),
        ("ṛ without і (Кршна)", re.compile(f"(?<![{UKC}])[{UKCONS}]р(?=[{UKCONS}])")),
        ("ai = «аі» (вайшнав, Чайтанья)", re.compile("[аА]і")),
        ("y after consonant = «й» (Нітьянанда, Ачар’я)", re.compile(f"[{UKCONS}]й[аеуіи]")),
        ("y + vowel = «я/ю/є/ї», not «йа» (янтра, Нараяна)", re.compile(f"(?<![{UKCONS}])[Йй][аеуі]")),
        ("jñ = «гья», not «джн»", re.compile("[Дд]жн")),
        ("Russian letter ы/э/ъ in UK text", re.compile("[ыэъЫЭЪ]")),
        ("Latin letter inside a Cyrillic word (праtіка, параmpарі)", re.compile(f"[{UKC}][A-Za-z]|[A-Za-z][{UKC}]")),
        ("th/kh/ph/ch = тх/кх/пх/чх, not «тг/кг» (Тхакур, Вішакха)", re.compile("(?<=[а-яіґ])(?:тг|кг|пг|чг)(?=[аеіиоуя])", re.I)),
        ("krishna.ua spelling (Крішна, Шрі, Прабгупада)", re.compile("Кришн|Шри(?![а-яіїєґ])|Прабхупад|Тгакур|Т̣")),
    ]
    # the converter is code, not data: import it from this checkout even when QA_REPO points at a temp data copy (s28)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "translate"))
    import uk_plain   # the same Russian-style -> krishna.ua table the converter uses (Шри, Радха, Гуру, Вриндаван …)
    uk_rules += [(f"krishna.ua spelling «{rep}»", rx) for rx, rep in uk_plain.VARIANTS]
    uk_skip = {"sanskrit", "src", "id", "audio_url", "transcript_url", "timecode", "date", "type", "layout", "page", "en_hash",
               "candidate", "target", "quote", "source"}   # source = lecture title as published (not UK text)

    def uk_strings(o, path=""):
        if isinstance(o, str):
            yield path, o
        elif isinstance(o, dict):
            for k, v in o.items():
                if k not in uk_skip:
                    yield from uk_strings(v, f"{path}/{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                yield from uk_strings(v, f"{path}/{i}")

    uk_src = []
    for fn in ("book.uk.json", "ui.uk.json"):
        fp = os.path.join(qa.DATA, fn)
        if os.path.exists(fp):
            uk_src.append((fn, json.load(open(fp, encoding="utf-8"))))
    gp = os.path.join(qa.REPO, "scripts", "translate", "glossary.uk.json")
    if os.path.exists(gp):
        uk_src.append(("scripts/translate/glossary.uk.json", json.load(open(gp, encoding="utf-8"))))
    for f in glob.glob(os.path.join(qa.REPO, "scripts", "**", "i18n.json"), recursive=True):
        j = json.load(open(f, encoding="utf-8"))   # {section id: {lang: {...}}} (or {lang: …})
        for part in ([j] + [v for v in j.values() if isinstance(v, dict)]) if isinstance(j, dict) else []:
            if "uk" in part:
                uk_src.append((os.path.relpath(f, qa.REPO).replace("\\", "/"), part["uk"]))
    mp = os.path.join(qa.REPO, "scripts", "moods", "moods.json")
    if os.path.exists(mp):
        uk_src.append(("scripts/moods/moods.json", [((m.get("translations") or {}).get("uk") or "") for m in json.load(open(mp, encoding="utf-8"))]))
    n_uk = 0
    for rel, data in uk_src:
        for where, t in uk_strings(data):
            t = unicodedata.normalize("NFC", t)
            n_uk += 1
            for rname, rx in uk_rules:
                for m in rx.finditer(t):
                    c.hit(rel, f"{where or '/'} [{rname}]", snippet(t, m, 25))
    c.info = f"{len(uk_src)} UK sources, {n_uk} strings"
    c.report(args.max)

    # L31 — A80b (13.10.2026; staging checkers A/B, «Для Гурудаса/2026-10-13 A80 UK/parbaude.md»): what L30 did not catch.
    # UK text = the same sources as L30 + moods «more[].translation.uk»; in `wbw` only the Ukrainian part after «—» is
    # checked (the heads are IAST by schema); ⟦…⟧ (inline IAST mantras by schema) is removed before the Latin rules.
    # Decisions 13.10 (Пурохита, по правилу krishna.ua) — rules file «Правила украинского написания (krishna.ua).md».
    c = Check("L31", "UK text as on krishna.ua (2): typographic apostrophe ’, no Latin/IAST in Ukrainian prose, no a.m./p.m., "
                     "no Russian forms (бхаджан, Махапрабху, Вринд…), Мангала, ья after ч/ш, «Шрі Ґурудева» capitalised")
    LAT = "A-Za-zÀ-ɏḀ-ỿ"
    IAST_D = "āīūṛṝḷṣśṇṭḍṁṅñḥĀĪŪṚṜḶṢŚṆṬḌṀṄÑḤ"
    uk_rules31 = [
        ("straight/modifier apostrophe in a Cyrillic word (use ’)", re.compile(f"[{UKC}]['ʼ][{UKC}]")),
        ("Latin/IAST letter touching a Cyrillic letter (оṁ)", re.compile(f"[{UKC}][{LAT}]|[{LAT}][{UKC}]")),
        ("IAST word in Ukrainian prose (write it in Ukrainian letters, as krishna.ua)", re.compile(f"[{LAT}]*[{IAST_D}][{LAT}]*")),
        ("a.m./p.m. (Ukrainian: «4:10 ранку», «6:30 вечора», as «утра/вечера» in the Russian book)", re.compile(r"\b[ap]\.\s?m\.", re.I)),
        ("Russian form «бхаджан» (бгаджан)", re.compile("[Бб]хаджан")),
        ("«Махапрабгу» (not Магапрабгу/Махапрабху)", re.compile("Магапрабгу|Махапрабху")),
        ("ṛ = «рі» (Вріндавана, Врінда-деві)", re.compile("Вринд|вринд")),
        ("«Мангала» without ґ (krishna.ua)", re.compile("[Мм]анґал")),
        ("ya after ч/ш/ж/щ = «ья» (Ачьюта; ’ only after б, п, в, м, ф, р)", re.compile(f"[чшжщЧШЖЩ]’[яюєї]")),
        ("«Шрі Ґурудева» with capitals", re.compile("[шШ]рі ґурудев|шрі Ґурудев")),
    ]
    uk31 = list(uk_src)
    if os.path.exists(mp):
        for m in json.load(open(mp, encoding="utf-8")):
            for a in m.get("more") or []:
                t = (a.get("translation") or {}).get("uk")
                if t:
                    uk31.append(("scripts/moods/moods.json:more", t))
    for rel, data in uk31:
        for where, t in uk_strings(data):
            if where.split("/")[-1] in ("scheme", "translation_note", "machine", "model"):
                continue        # glossary «scheme» = the transliteration table itself (IAST on purpose); metadata
            t = unicodedata.normalize("NFC", t)
            if where.endswith("/wbw"):
                t = " ; ".join(p.split("—", 1)[1] if "—" in p else "" for p in t.split(";"))
            t = re.sub("⟦[^⟧]*⟧", " ", t)
            for rname, rx in uk_rules31:
                for m in rx.finditer(t):
                    c.hit(rel, f"{where or '/'} [{rname}]", snippet(t, m, 25))
    c.info = f"{len(uk31)} UK sources"
    c.report(args.max)

    # L32 — A80-3 (13.10.2026; Satkirti: «в укр версии … написание слов — как на krishna.ua» = no Russian text in UK).
    # L30/L31 check the UK data; L32 checks what a UK reader actually gets: the BUILT UK pages (out/uk/**: visible
    # HTML + the page's RSC data incl. the UK contents/navigation) and out/search-index.uk.json — so a title that falls
    # back to Russian somewhere in the build is caught. Also «ё» (L30 has only ы/э/ъ). Every page embeds the contents of
    # ALL languages (root layout `locales`, used by the language switch): only `locales.uk` is checked, the other
    # languages are theirs. Not checked: lecture `source` titles (the recording's name as published, as in L30).
    c = Check("L32", "UK build: no Russian text in UK pages / UK navigation / UK search (ы э ъ ё, Кришна, Шри, Радха …)")
    ru_in_uk = re.compile(r"[ыэъёЫЭЪЁ]|Кришн|Шри(?![а-яіїєґ])|Радх[аеиуыо]|Прабхупад|Вриндав")
    for rel, data in uk31:
        for where, t in uk_strings(data):
            if where.split("/")[-1] in ("scheme",):
                continue
            for m in re.finditer("[ёЁ]", unicodedata.normalize("NFC", t)):
                c.hit(rel, where or "/", snippet(t, m, 25))
    push_rx = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)')
    dec = json.JSONDecoder()

    def only_uk_locale(rsc):
        out, i = [], 0
        for m in re.finditer(r'"locales":', rsc):
            if m.start() < i:
                continue
            try:
                obj, end = dec.raw_decode(rsc, m.end())
            except ValueError:
                continue
            out += [rsc[i:m.start()], json.dumps(obj.get("uk", {}), ensure_ascii=False)]
            i = end
        out.append(rsc[i:])
        return re.sub(r'"source":\{"title":"(?:[^"\\]|\\.)*"', '"source":{', "".join(out))

    def drop_pending_blocks(text, pending):
        mark = re.compile(r'data-book-section(?:="|":")([\w-]+)"')
        rows, order = {}, []
        lines = text.split("\n")
        cur = None
        other = []
        for ln in lines:
            m = re.match(r"([0-9a-f]+):", ln)
            if m and (m.group(1) not in rows):
                cur = m.group(1)
                rows[cur] = [ln]
                order.append(cur)
            elif cur is not None:
                rows[cur].append(ln)
            else:
                other.append(ln)
        rows = {k: "\n".join(v) for k, v in rows.items()}
        ref = re.compile(r'"\$[LQWKBF@]?([0-9a-f]+)"')
        prow = {k for k, v in rows.items()
                if re.match(r'[0-9a-f]+:\["\$","div","([\w-]+)",\{"data-book-section"', v)
                and re.match(r'[0-9a-f]+:\["\$","div","([\w-]+)"', v).group(1) in pending}

        def cut(t):
            ms = list(mark.finditer(t))
            keep, pos = [], 0
            for i, m in enumerate(ms):
                if m.group(1) in pending and m.start() >= pos:
                    keep.append(t[pos:m.start()])
                    pos = ms[i + 1].start() if i + 1 < len(ms) else len(t)
            keep.append(t[pos:])
            return "".join(keep)

        seen = set()
        # roots: rows not referenced by anyone (the page root) — walk from them, never into a pending block
        refd = {r for v in rows.values() for r in ref.findall(v)}
        stack = [k for k in order if k not in prow and k not in refd] or [k for k in order if k not in prow]
        while stack:
            k = stack.pop()
            if k in seen or k in prow or k not in rows:
                continue
            seen.add(k)
            stack += ref.findall(cut(rows[k]))
        return cut("\n".join(other)) + "\n" + "\n".join(cut(rows[k]) for k in order if k in seen)

    n32 = n32_pending = 0
    en_book = loaded.get(os.path.join(qa.DATA, "book.json")) or {}
    pending_sections = {x.get("id") for x in en_book.get("sections") or [] if isinstance(x, dict) and x.get("translation_pending")}
    uk_out = os.path.join(qa.OUT, "uk")
    if os.path.isdir(uk_out) and not args.no_html:
        files = [os.path.join(dp, fn) for dp, _, fns in os.walk(uk_out) for fn in fns if fn.endswith((".html", ".txt"))]
        si = os.path.join(qa.OUT, "search-index.uk.json")
        if os.path.exists(si):
            files.append(si)
        for f in sorted(files):
            raw = open(f, encoding="utf-8").read()
            if f.endswith(".html"):
                rsc = "".join(json.loads(s) for s in push_rx.findall(raw))
                text = re.sub(r"<script.*?</script>", " ", raw, flags=re.S) + "\n" + only_uk_locale(rsc)
            else:
                text = only_uk_locale(raw)
            n32 += 1
            rel = os.path.relpath(f, qa.OUT).replace(os.sep, "/")
            # A83: the page of a Russian-only chapter (book.json "translation_pending") is the app's English
            # fallback page, here still the RU text with the "not yet translated" note — skipped until translated
            # (the mark is removed by the translation; the rest of the UK build stays strict)
            if rel.split("/")[1:2] and rel.split("/")[1] in pending_sections:
                n32_pending += 1
                continue
            # A89 «Прокручивать» (uk/book/): the whole book in one page — the block of a Russian-only chapter is that
            # same fallback text: drop only that block (its RSC rows reachable from nothing else; the inline part from
            # its data-book-section mark to the next one) — the rest of the book page stays strict
            if rel.split("/")[1:2] == ["book"] and pending_sections:
                text = drop_pending_blocks(text, pending_sections)
                n32_pending += 1
            for m in ru_in_uk.finditer(text):
                c.hit("out", rel, snippet(text, m, 30))
    c.info = (f"{n32} built UK files" + (f" ({n32_pending} of Russian-only chapters awaiting translation skipped: "
              f"{', '.join(sorted(pending_sections))})" if n32_pending else "")) if n32 else "out/uk not built — only the data part checked"
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
