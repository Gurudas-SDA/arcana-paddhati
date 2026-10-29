"""S msg 6961 (A127, 29.10.2026), part «Арати»: chapter order and «Ямунаштака» without a subsection.

S verbatim (as relayed to Lipikāra): «Джхулана-ятра» — 18-я, «Ямунаштака» — 19-я (Jhulana before Yamunāṣṭaka);
«Ямунаштака» без подраздела: «нажимаешь — и сразу попадаешь в Ямунаштаку», «Ямунаштака — это уже сам бхаджан».
(In the app «Содержание» the part's chapters are numbered 24–29 → Jhulana 25, Yamunāṣṭaka 26.)

  a) data (en, ru-iast): part «arati» chapters in order mangala, raja-bhoga, gaura, kartika, jhulana-yatra-bhajans,
     yamunastaka; sections order together the same; chapter numbers: Jhulana = Yamunāṣṭaka − 1;
  b) data: chapter yamunastaka has NO subsections; its content = the song itself (author line + 9 verses, first
     «bhrātur antakasya», each IAST (no Cyrillic) + wbw + translation); chapter flag "numbered": true; no id
     «song-yamunastakam» anywhere; jhulana-yatra-bhajans keeps its 2 song subsections;
  c) app (with <base-url>): yamunastaka page: 9 verse numbers 1–9, no subsection heading («Шри Ямунаштака»/«Śrī
     Yamunāṣṭakam» only as the page title / not as h2), «Содержание» lists Jhulana before Yamunāṣṭaka.
usage: python s121_yamunastaka_chapter_a127.py [<base-url>]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else None
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
CHAP = ["mangala-arati-songs", "raja-bhoga-arati", "gaura-arati-songs", "kartika-bhajans", "jhulana-yatra-bhajans",
        "yamunastaka"]
CYR = re.compile(r"[А-Яа-яЁё]")
results = []


def check(where, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {where} {name} {'' if ok else info}".rstrip(), flush=True)


for fn in ("book.ru-iast.json", "book.json"):
    raw = open(os.path.join(DATA, fn), encoding="utf-8").read()
    b = json.loads(raw)
    secs = {s["id"]: s for s in b["sections"]}
    ids = [s["id"] for s in b["sections"]]
    part = next((p for p in b["parts"] if p["id"] == "arati"), {"sections": []})
    check(fn, "a part «Арати»: Джхулана-ятра before Ямунаштака", part["sections"] == CHAP, part["sections"])
    at = ids.index(CHAP[0]) if CHAP[0] in ids else -1
    check(fn, "a sections in book order: same 6", ids[at:at + 6] == CHAP, ids[at:at + 6])
    check(fn, "a chapter number Джхулана-ятра = Ямунаштака − 1",
          "jhulana-yatra-bhajans" in ids and ids.index("yamunastaka") - ids.index("jhulana-yatra-bhajans") == 1)
    y = secs.get("yamunastaka", {})
    check(fn, "b «Ямунаштака» chapter has no subsections", y and not y.get("subsections"), y.get("subsections") and [x["id"] for x in y["subsections"]])
    vs = [x for x in y.get("content") or [] if x.get("type") == "verse"]
    check(fn, "b «Ямунаштака»: 9 verses in the chapter itself, first «bhrātur antakasya»",
          len(vs) == 9 and vs[0]["sanskrit"].lower().startswith("bhrātur antakasya"), len(vs))
    check(fn, "b «Ямунаштака» verses IAST (no Cyrillic) + wbw + translation",
          vs and all(not CYR.search(v["sanskrit"]) and (v.get("wbw") or "").strip() and (v.get("translation") or "").strip() for v in vs))
    check(fn, "b «Ямунаштака» chapter \"numbered\": true", y.get("numbered") is True, y.get("numbered"))
    check(fn, "b no «song-yamunastakam» anywhere", "song-yamunastakam" not in raw)
    jh = secs.get("jhulana-yatra-bhajans", {"subsections": []})
    check(fn, "b «Джхулана-ятра» keeps its 2 songs", [x["id"] for x in jh["subsections"]] == ["song-jhula-jhule", "song-radhe-jhulana-padharo"])

if BASE is None:
    print(f"{sum(results)}/{len(results)} passed")
    sys.exit(0 if results and all(results) else 1)

from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as p:
    for device, engine, options in qa.devices(["iphone14", "desktop"]):
        browser = getattr(p, engine).launch()
        context = browser.new_context(service_workers="block", **options)
        page = context.new_page()
        for lang in ("", "ru-iast/"):
            tag = f"{device} {lang or 'en/'}"
            page.goto(f"{BASE}/{lang}yamunastaka/", wait_until="load")
            page.wait_for_selector(".verse-text", state="attached", timeout=15000)
            got = page.evaluate("""() => [document.querySelectorAll('.verse-text').length,
                [...document.querySelectorAll('.verse-num')].map(e => e.textContent.trim()).join(','),
                document.querySelectorAll('[data-subsection]').length]""")
            check(tag, "c Ямунаштака: 9 verses numbered 1–9, no subsection", got == [9, "1,2,3,4,5,6,7,8,9", 0], got)
            for _ in range(3):
                if page.locator(".mobile-menu[data-open]").count():
                    break
                if page.locator(".reader-chrome[data-shown]").count() == 0:
                    vp = page.viewport_size
                    (page.touchscreen.tap if options.get("has_touch") else page.mouse.click)(vp["width"] - 6, vp["height"] / 2)
                    page.wait_for_timeout(600)
                try:
                    btn = page.locator("[data-reader-action=contents]").first
                    btn.tap() if options.get("has_touch") else btn.click()
                    page.wait_for_timeout(900)
                except Exception:
                    pass
            ids = page.evaluate("() => [...document.querySelectorAll('.mobile-menu[data-open] [data-toc-chapter]')].map(e => e.getAttribute('data-toc-chapter'))")
            order = [x for i, x in enumerate(ids) if x in CHAP and x not in ids[:i]]
            check(tag, "c «Содержание»: Джхулана-ятра before Ямунаштака", order == CHAP, order)
        context.close()
        browser.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
