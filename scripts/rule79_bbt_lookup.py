# -*- coding: utf-8 -*-
"""Noteikums 79 (D8): kuriem grāmatas pantiem ir BBT pārvārdojums (vedabase.io) un vai grāmatas wbw ar to sakrīt.
Meklē vedabase.io (EN meklēšana pēc pirmās rindas IAST -> ASCII), salīdzina pantu tekstu (SequenceMatcher >= 0.80),
tad ņem RU lapas «Пословный перевод» un salīdzina nozīmju secību ar data/book.ru-iast.json.
Atsākams: kešs JSON (arg 1), katrs palaids = līdz ~250 s. Izvade: kešs + gala pārskats (--report).
usage: python rule79_bbt_lookup.py <cache.json> [--report]   (DATA = ../data)
"""
import difflib
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "book.ru-iast.json")
CACHE = sys.argv[1]
BUDGET = 240
T0 = time.time()
UA = {"User-Agent": "Mozilla/5.0 (rule79-bbt-lookup; Satkirti book QA)"}


def fold(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("ṁ", "m").replace("ṃ", "m")
    return re.sub(r"[^a-z]", "", s)


def get(url):
    for i in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25)
            return r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(1.5)
    return None


def text_of(h):
    h = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    x = html.unescape(re.sub(r"<[^>]+>", "|", h))
    return re.sub(r"\|+", "|", x)


def verses():
    d = json.load(open(DATA, encoding="utf-8"))
    out = []

    def walk(o, p=""):
        if isinstance(o, dict):
            if o.get("type") == "verse" and (o.get("wbw") or "").strip():
                out.append((p, o))
            for k, v in o.items():
                walk(v, p + "/" + k)
        elif isinstance(o, list):
            for i, x in enumerate(o):
                walk(x, p + "/" + str(i))
    walk(d)
    return out


def en_verse_text(h):
    x = text_of(h)
    m = re.search(r"\|Verse text\|(.*?)\|(?:Synonyms|Translation)\|", x, flags=re.S)
    return (m.group(1) if m else "").replace("|", " ")


def ru_wbw(h):
    x = text_of(h)
    m = re.search(r"\|Пословный перевод\|(.*?)\|(?:Перевод|Комментарий)\|", x, flags=re.S)
    if not m:
        return None
    s = m.group(1).replace("|", "")
    pairs = []
    for e in s.rstrip(".").split("; "):
        k, _, v = e.partition(" — ")
        pairs.append((k.strip(), v.strip()))
    return pairs


def main():
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    vs = verses()
    uniq = {}
    for p, o in vs:
        key = fold(o["sanskrit"].splitlines()[0])[:60]
        uniq.setdefault(key, (p, o))
    todo = [(k, v) for k, v in uniq.items() if k not in cache]
    print(f"verses {len(vs)}, unique first lines {len(uniq)}, cached {len(uniq)-len(todo)}, todo {len(todo)}", flush=True)
    for key, (p, o) in todo:
        if time.time() - T0 > BUDGET:
            print("budget reached; rerun", flush=True)
            break
        first = " ".join(o["sanskrit"].split("\n")[0].split()[:7])
        q = urllib.parse.quote(unicodedata.normalize("NFD", first).encode("ascii", "ignore").decode())
        h = get(f"https://vedabase.io/en/search/?query={q}")
        rec = {"q": first, "match": None}
        failed = h is None
        if h:
            links = []
            for m in re.finditer(r'href="(/en/library/[a-z0-9]+(?:/[a-z0-9\-]+)*/)"', h):
                u = m.group(1)
                if u not in links and re.search(r"/\d+/$", u):
                    links.append(u)
            full = fold(" ".join(o["sanskrit"].split("\n")[:2]))
            best = (0, None)
            for u in links[:4]:
                ph = get("https://vedabase.io" + u)
                time.sleep(0.25)
                if not ph:
                    failed = True
                    continue
                vt = fold(en_verse_text(ph))
                r = difflib.SequenceMatcher(None, full[:120], vt[:min(len(full), 120)]).ratio()
                if r > best[0]:
                    best = (r, u)
            if best[0] >= 0.80:
                rec["match"] = best[1]
                rec["ratio"] = round(best[0], 2)
                rh = get("https://vedabase.io" + best[1].replace("/en/", "/ru/", 1))
                rec["ru"] = ru_wbw(rh) if rh else None
        if failed:
            print("tīkla kļūda, netiek keširēts:", first, flush=True)
            continue
        cache[key] = rec
        json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
        time.sleep(0.3)
    if "--report" in sys.argv:
        m = {k: r for k, r in cache.items() if r.get("match")}
        print(f"BBT match: {len(m)} of {len(cache)} unique")
        for k, r in m.items():
            print(r["match"], r["ratio"], r["q"], "| ru wbw:", bool(r.get("ru")))


main()
