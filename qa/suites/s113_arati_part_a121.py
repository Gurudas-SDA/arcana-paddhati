"""S msg 6811/6812/6817/6818/6824 (A121, 26.10.2026) + 6826 + 6828.

6811–6818, 6824 (S, verbatim excerpts as relayed to Lipikāra): all ārati in ONE new section «Арати», in place of the
song chapters of «Праздники, обеты и песни арати»; order: «Мангала-арати», «Раджа-бхога-арати» (Yaśomatī-nandana,
Jaya Yaśodā-nandana, Jaya Rādhā-Mādhava), «Гаура-арати», «Картика» («Пиши картика. Без дамодара»), «Ямунаштака»
(«Ямунаштаку вынеси отдельно»), «Джхулана-ятра» (Jhūlā jhūle Rādhā-Dāmodara, Rādhe jhūlana padhāro); «Ночью всё
поставь, что сможешь найти».
6826: «Все пронумеруй по центру. Короткие бхаджаны, одна-две шлоки не нумеруй».
6828: «В «Джая-дхвани» убери переводы. Это молитва, в которой перечисляют святых».

  a) data (en, ru-iast): part "arati" exists right after festivals-vows, its chapters are exactly the 6 ids in order;
     titles RU «Мангала-арати», «Раджа-бхога-арати», «Гаура-арати», «Картика», «Ямунаштака», «Джхулана-ятра»;
     festivals-vows has none of them and its title has no «арати»; book.sections has the 6 chapters together in order;
  b) raja-bhoga-arati = the 3 bhajans in order; Jaya Rādhā-Mādhava = 1 verse (only the checked 1st verse);
     yamunastaka = Śrī Yamunāṣṭakam alone (9 verses, Rūpa Gosvāmī), not inside «Картика»; kartika keeps Dāmodarāṣṭakam;
     jhulana-yatra-bhajans = Jhūlā jhūle + Rādhe jhūlana; every new verse IAST (no Cyrillic) + wbw + translation;
     no Cyrillic with diacritics in ru-iast;
  c) msg 6826: every song subsection («song-…») with ≥3 verses has "numbered": true, with 1–2 verses has none;
  d) msg 6828: «Джая-дхвани» (jaya-dhvani-front) — no verse has translation or word-by-word (S exception to
     «Стандарты» 79 for this prayer);
  e) app (with <base-url>): the TOC lists part «Арати» with the 6 chapters in order; raja-bhoga-arati shows 4 numbers
     for Yaśomatī-nandana and none for the 2 short bhajans; jaya-dhvani-front has no «перевод»/«пословно» buttons.
usage: python s113_arati_part_a121.py [<base-url>]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else None
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
CHAP = ["mangala-arati-songs", "raja-bhoga-arati", "gaura-arati-songs", "kartika-bhajans", "yamunastaka",
        "jhulana-yatra-bhajans"]
TITLES = {"ru-iast": ["Мангала-арати", "Раджа-бхога-арати", "Гаура-арати", "Картика", "Ямунаштака", "Джхулана-ятра"],
          "en": ["Maṅgala-ārati", "Rāja-bhoga-ārati", "Gaura-ārati", "Kārtika", "Yamunāṣṭaka", "Jhūlana-yātrā"]}
RAJA = ["song-yasomati-nandana", "song-jaya-yasoda-nandana", "song-jaya-radha-madhava"]
FIRST = {"song-yasomati-nandana": "yaśomatī-nandana", "song-jaya-yasoda-nandana": "jaya yaśodā-nandana",
         "song-jaya-radha-madhava": "jaya rādhā-mādhava", "song-yamunastakam": "bhrātur antakasya",
         "song-jhula-jhule": "jhūlā jhūle rādhā-dāmodara", "song-radhe-jhulana-padharo": "rādhe jhūlana padhāro"}
NVERSES = {"song-yasomati-nandana": 4, "song-jaya-yasoda-nandana": 2, "song-jaya-radha-madhava": 1,
           "song-yamunastakam": 9, "song-jhula-jhule": 5, "song-radhe-jhulana-padharo": 5}
CYR_DIAC = re.compile(r"[а-яА-ЯёЁ][̣̄̃̇́]")
CYR = re.compile(r"[А-Яа-яЁё]")
results = []


def check(where, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {where} {name} {'' if ok else info}".rstrip(), flush=True)


def verses(sub):
    return [b for b in sub.get("content") or [] if b.get("type") == "verse"]


# ---------------- a–d) data ----------------
for lang, fn in (("ru-iast", "book.ru-iast.json"), ("en", "book.json")):
    raw = open(os.path.join(DATA, fn), encoding="utf-8").read()
    b = json.loads(raw)
    secs = {s["id"]: s for s in b["sections"]}
    pids = [p["id"] for p in b["parts"]]
    part = next((p for p in b["parts"] if p["id"] == "arati"), None)
    fest = next((p for p in b["parts"] if p["id"] == "festivals-vows"), {"sections": [], "title": ""})
    check(fn, "a part «Арати» right after festivals-vows", part and pids.index("arati") == pids.index("festivals-vows") + 1, pids)
    check(fn, "a part chapters 1–6 in order", part and part["sections"] == CHAP, part and part["sections"])
    check(fn, "a part title", part and part["title"] == ("Арати" if lang == "ru-iast" else "Ārati"), part and part["title"])
    check(fn, "a chapter titles", [secs.get(c, {}).get("title") for c in CHAP] == TITLES[lang],
          [secs.get(c, {}).get("title") for c in CHAP])
    check(fn, "a festivals-vows: no ārati chapters, title without «арати/Ārati»",
          not set(CHAP) & set(fest["sections"]) and not re.search(r"арати|ārati", fest["title"], re.I), (fest["sections"], fest["title"]))
    ids = [s["id"] for s in b["sections"]]
    check(fn, "a chapters together in book order", all(c in ids for c in CHAP)
          and ids[ids.index(CHAP[0]):ids.index(CHAP[0]) + 6] == CHAP, [i for i in ids if i in CHAP])
    raja = secs.get("raja-bhoga-arati", {"subsections": []})
    check(fn, "b Раджа-бхога-арати = 3 bhajans in order", [x["id"] for x in raja["subsections"]] == RAJA,
          [x["id"] for x in raja["subsections"]])
    kart = secs.get("kartika-bhajans", {"subsections": []})
    check(fn, "b «Картика» keeps Dāmodarāṣṭakam, no Yamunāṣṭaka inside",
          "song-damodarastakam" in [x["id"] for x in kart["subsections"]] and "song-yamunastakam" not in [x["id"] for x in kart["subsections"]])
    yam = secs.get("yamunastaka", {"subsections": []})
    check(fn, "b «Ямунаштака» separate chapter = only Śrī Yamunāṣṭakam", [x["id"] for x in yam["subsections"]] == ["song-yamunastakam"])
    jh = secs.get("jhulana-yatra-bhajans", {"subsections": []})
    check(fn, "b «Джхулана-ятра» = Jhūlā jhūle + Rādhe jhūlana",
          [x["id"] for x in jh["subsections"]] == ["song-jhula-jhule", "song-radhe-jhulana-padharo"])
    for sub in raja["subsections"] + yam["subsections"] + jh["subsections"]:
        vs = verses(sub)
        sid = sub["id"]
        check(fn, f"b {sid}: {NVERSES.get(sid)} verses, starts «{FIRST.get(sid)}»", len(vs) == NVERSES.get(sid)
              and vs and vs[0]["sanskrit"].lower().startswith(FIRST.get(sid, "?")), (len(vs), vs and vs[0]["sanskrit"][:40]))
        check(fn, f"b {sid}: IAST (no Cyrillic) + wbw + translation", vs and all(
            not CYR.search(v["sanskrit"]) and (v.get("wbw") or "").strip() and (v.get("translation") or "").strip() for v in vs))
    if lang == "ru-iast":
        check(fn, "b no Cyrillic with diacritics (grep -c «[а-яА-ЯёЁ][̣̄̃̇́]» = 0)", not CYR_DIAC.search(raw), len(CYR_DIAC.findall(raw)))
    # c) msg 6826
    bad = []
    for s in b["sections"]:
        for sub in s.get("subsections") or []:
            if str(sub.get("id", "")).startswith("song-"):
                want = len(verses(sub)) >= 3
                if bool(sub.get("numbered")) != want:
                    bad.append((sub["id"], len(verses(sub)), sub.get("numbered")))
    check(fn, "c msg 6826: songs ≥3 verses numbered, 1–2 verses not", not bad, bad)
    # d) msg 6828
    jd = secs.get("jaya-dhvani-front", {"content": []})
    jv = verses(jd)
    check(fn, "d msg 6828: «Джая-дхвани» calls without translation / word-by-word",
          jv and not [v for v in jv if v.get("translation") or v.get("wbw")], len([v for v in jv if v.get("translation") or v.get("wbw")]))

if BASE is None:
    print(f"{sum(results)}/{len(results)} passed")
    sys.exit(0 if results and all(results) else 1)

# ---------------- e) app ----------------
from playwright.sync_api import sync_playwright  # noqa: E402

TOC_JS = """() => [...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href'))"""
with sync_playwright() as p:
    for device, engine, options in qa.devices(["iphone14", "desktop"]):
        browser = getattr(p, engine).launch()
        context = browser.new_context(service_workers="block", **options)
        page = context.new_page()
        for lang in ("", "ru-iast/"):
            tag = f"{device} {lang or 'en/'}"
            page.goto(f"{BASE}/{lang}raja-bhoga-arati/", wait_until="load")
            page.wait_for_selector("#song-yasomati-nandana .verse-text", state="attached", timeout=15000)
            n = page.evaluate("""() => ['song-yasomati-nandana','song-jaya-yasoda-nandana','song-jaya-radha-madhava']
                .map(id => { const s = document.getElementById(id);
                  return s ? [s.querySelectorAll('.verse-text').length, [...s.querySelectorAll('.verse-num')].map(e => e.textContent.trim()).join(',')] : null; })""")
            check(tag, "e Раджа-бхога-арати: Yaśomatī 4 numbered 1–4, short bhajans without numbers",
                  n == [[4, "1,2,3,4"], [2, ""], [1, ""]], n)
            hrefs = page.evaluate(TOC_JS)
            order = []
            for h in hrefs:
                m = re.search(r"/(" + "|".join(CHAP) + r")/?(?:#|$)", h or "")
                if m and m.group(1) not in order:
                    order.append(m.group(1))
            check(tag, "e navigation knows the 6 chapters in order", order == CHAP, order)
            page.goto(f"{BASE}/{lang}jaya-dhvani-front/", wait_until="load")
            page.wait_for_selector(".verse-text", state="attached", timeout=15000)
            btn = page.evaluate("""() => [document.querySelectorAll('.verse-text').length,
                [...document.querySelectorAll('main button, article button')].filter(b => /пословно|перевод|word|translation/i.test(b.textContent)).length]""")
            check(tag, "e «Джая-дхвани»: no «перевод»/«пословно» buttons", btn[0] > 0 and btn[1] == 0, btn)
        context.close()
        browser.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
