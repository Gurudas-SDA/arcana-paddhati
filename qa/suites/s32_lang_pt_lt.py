"""A73 (Gurudas 10.10 20:30, agreed with Satkirti): two new languages of the book app — Portuguese (pt) and
Lithuanian (lt).
Acceptance:
  1) the book opens in Portuguese and in Lithuanian: /pt/ and /lt/ pages exist for every chapter, the text is
     not empty, <html lang> is the language;
  2) both languages are in the language menu of the «Аа» panel (with their own name, not «(EN)» = no data);
  3) the translation is complete: every chapter of the English book is there, every Sanskrit (IAST) field is
     byte-identical to the English/RU-IAST one, no larger English passages are left (stop-word sample),
     ui.<lang>.json has every key of ui.en.json; the offline cache (sw.js, precache) knows both languages.
usage: python s32_lang_pt_lt.py <base-url>   devices: QA_DEVICES"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else ""
LANGS = {"pt": ("Português", "pt"), "lt": ("Lietuvių", "lt")}
DEVICES = qa.devices(["pixel7", "iphone14", "desktop"])
res = []


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else info}", flush=True)


def load(fn):
    p = os.path.join(qa.DATA, fn)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def sk_fields(o, path=()):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "sanskrit":
                yield "/".join(map(str, path + (k,))), v
            yield from sk_fields(v, path + (k,))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from sk_fields(v, path + ((v.get("id") if isinstance(v, dict) and isinstance(v.get("id"), str) else i),))


TEXT_KEYS = ("title", "subtitle", "content", "translation", "caption", "alt", "label", "value", "badge")
SKIP_TYPES = ("mood",)   # Gurudev's own English words are shown in the original next to the translation


def texts(o, path=()):
    """(path, text) of the translatable prose fields of a book (no sanskrit, no wbw, no mood quotes)."""
    if isinstance(o, dict):
        if o.get("type") in SKIP_TYPES:
            return
        for k, v in o.items():
            if k in TEXT_KEYS and isinstance(v, str):
                yield "/".join(map(str, path + (k,))), v
            elif k in ("header", "cells") and isinstance(v, list):
                for i, x in enumerate(v):
                    if isinstance(x, str):
                        yield "/".join(map(str, path + (k, i))), x
            elif isinstance(v, (dict, list)):
                yield from texts(v, path + (k,))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from texts(v, path + ((v.get("id") if isinstance(v, dict) and isinstance(v.get("id"), str) else i),))


EN_STOP = set("the and of to is are with for which should be this that from by on his her their your you it as at "
              "when then while into after before must all one each".split())


def english_ratio(t):
    t = re.sub(r"⟦.*?⟧", " ", t, flags=re.S)
    words = re.findall(r"[A-Za-z]+", t)
    if len(words) < 6:
        return 0.0, len(words)
    return sum(w.lower() in EN_STOP for w in words) / len(words), len(words)


def data_checks():
    dev = "data"
    langs = json.load(open(os.path.join(qa.REPO, "lib", "languages.json"), encoding="utf-8"))
    en = load("book.json")
    ri = load("book.ru-iast.json")
    en_ids = [s["id"] for s in en["sections"]]
    en_sk = dict(sk_fields(en))
    ri_sk = dict(sk_fields(ri))
    ui_en = load("ui.en.json")
    sw = open(os.path.join(qa.REPO, "public", "sw.js"), encoding="utf-8").read()
    pre = open(os.path.join(qa.REPO, "scripts", "build-precache.mjs"), encoding="utf-8").read()
    for code, (name, html) in LANGS.items():
        ent = next((l for l in langs if l["code"] == code), None)
        chk(dev, f"{code}: lib/languages.json has «{name}» (htmlLang {html})",
            ent is not None and ent.get("name") == name and ent.get("htmlLang") == html and not ent.get("replacedBy"), str(ent))
        b = load(f"book.{code}.json")
        chk(dev, f"{code}: data/book.{code}.json exists", b is not None)
        if b is None:
            continue
        ids = [s["id"] for s in b["sections"]]
        chk(dev, f"{code}: every chapter of the English book, same order ({len(en_ids)})", ids == en_ids,
            f"missing {[i for i in en_ids if i not in ids]} extra {[i for i in ids if i not in en_ids]}")
        chk(dev, f"{code}: book title/parts translated", b.get("subtitle") and b["subtitle"] != en["subtitle"]
            and [p["id"] for p in b["parts"]] == [p["id"] for p in en["parts"]]
            and all(p["title"] != q["title"] for p, q in zip(b["parts"], en["parts"])), str(b.get("parts"))[:200])
        sk = dict(sk_fields(b))
        bad = [k for k in en_sk if sk.get(k) != en_sk[k]] + [k for k in sk if k not in en_sk]
        chk(dev, f"{code}: every Sanskrit (IAST) field byte-identical to EN ({len(en_sk)})", not bad, str(bad[:5]))
        bad_ri = [k for k in ri_sk if k in sk and sk[k] != ri_sk[k]]
        chk(dev, f"{code}: Sanskrit fields = RU-IAST ({len(ri_sk)})", not bad_ri, str(bad_ri[:5]))
        en_t = dict(texts(en))
        tr_t = dict(texts(b))
        empty = [k for k, v in tr_t.items() if not v.strip() and en_t.get(k, "").strip()]
        chk(dev, f"{code}: no empty text where English has text", not empty, str(empty[:5]))
        same_long = [k for k, v in tr_t.items() if v == en_t.get(k) and english_ratio(v)[0] >= 0.2]
        chk(dev, f"{code}: no English prose copied untranslated", not same_long, str(same_long[:5]))
        eng = [(k, round(r, 2)) for k, v in tr_t.items() for r, n in [english_ratio(v)] if r >= 0.25 and n >= 8]
        n = len(tr_t)
        chk(dev, f"{code}: English sentences left ≤ 0.5 % of {n} text fields (found {len(eng)})", len(eng) <= n * 0.005,
            str(eng[:6]))
        moods = []

        def mw(o):
            if isinstance(o, dict):
                if o.get("type") == "mood":
                    moods.append(o)
                for v in o.values():
                    mw(v)
            elif isinstance(o, list):
                for v in o:
                    mw(v)
        mw(b)
        mw_en = sum(1 for _ in re.finditer(r'"type": "mood"', json.dumps(en, ensure_ascii=False)))
        chk(dev, f"{code}: Gurudev's quotes ({mw_en}) present with a translation",
            len(moods) == mw_en and all(m.get("translation", "").strip() and m["translation"] != m["quote"] for m in moods),
            f"{len(moods)} blocks")
        ui = load(f"ui.{code}.json")
        chk(dev, f"{code}: ui.{code}.json has every key of ui.en.json ({len(ui_en)})",
            ui is not None and set(ui) == set(ui_en) and all(isinstance(ui[k], str) and ui[k].strip() for k in ui),
            "missing %s" % (sorted(set(ui_en) - set(ui or {}))[:8]))
        if ui:
            same = [k for k in ui_en if ui[k] == ui_en[k] and english_ratio(ui_en[k])[1] >= 3
                    and not re.search(r"Arcana|Chrome|\{", ui_en[k])]
            chk(dev, f"{code}: UI strings translated (identical to English ≤ 3)", len(same) <= 3, str(same[:8]))
        chk(dev, f"{code}: public/sw.js LANG_CODES has '{code}'", re.search(r"LANG_CODES = \[[^\]]*'%s'" % code, sw), "")
        chk(dev, f"{code}: scripts/build-precache.mjs LANG_DIRS has \"{code}\"", re.search(r'LANG_DIRS = \[[^\]]*"%s"' % code, pre), "")
        if os.path.isdir(qa.OUT):
            miss = [s for s in en_ids if not os.path.isfile(os.path.join(qa.OUT, code, s, "index.html"))]
            chk(dev, f"{code}: out/{code}/<chapter>/index.html for all {len(en_ids)} chapters", not miss, str(miss[:5]))
            chk(dev, f"{code}: search index public/search-index.{code}.json",
                os.path.isfile(os.path.join(qa.REPO, "public", f"search-index.{code}.json")), "")
            man = os.path.join(qa.OUT, "precache-manifest.json")
            if os.path.isfile(man):
                urls = json.load(open(man, encoding="utf-8")).get("urls") or []
                chk(dev, f"{code}: precache manifest has /{code}/ pages", any(f"/{code}/" in u for u in urls), "")


SWITCH = """() => { const s = document.querySelector('.reader-panel select'); if (!s) return null;
  return [...s.options].map(o => [o.value, o.textContent.trim()]); }"""


def run(p, dev, eng, o):
    b = getattr(p, eng).launch()
    c = b.new_context(locale="en-US", service_workers="block", **o)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    touch = o.get("has_touch", False)
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    for code, (name, html) in LANGS.items():
        r = pg.goto(f"{BASE}/{code}/", wait_until="networkidle")
        chk(dev, f"{code}: /{code}/ opens", r is not None and r.status == 200, str(r and r.status))
        if not r or r.status != 200:
            continue
        chk(dev, f"{code}: <html lang> = {html}", pg.evaluate("document.documentElement.lang") == html,
            pg.evaluate("document.documentElement.lang"))
        for sid in ("introduction", "worship-sixteen-articles", "mangala-arati-songs"):
            r = pg.goto(f"{BASE}/{code}/{sid}/", wait_until="networkidle")
            h1 = pg.evaluate("(document.querySelector('main h1')||{}).textContent||''").strip()
            body = pg.evaluate("(document.querySelector('main')||document.body).innerText.length")
            chk(dev, f"{code}/{sid}: heading + text not empty", r and r.status == 200 and h1 and body > 300,
                f"status {r and r.status} h1 «{h1[:40]}» text {body}")
        # «Аа» panel: the language menu
        vw = pg.viewport_size
        for _ in range(4):
            if pg.locator(".reader-panel").count():
                break
            if pg.locator(".reader-chrome[data-shown]").count() == 0:
                (pg.touchscreen.tap if touch else pg.mouse.click)(vw["width"] - 6, vw["height"] / 2)
                pg.wait_for_timeout(450)
            btn = pg.locator("[data-reader-action=aa]")
            try:
                btn.tap(timeout=3000) if touch else btn.click(timeout=3000)
            except Exception:
                pass
            pg.wait_for_timeout(600)
        opts = pg.evaluate(SWITCH) or []
        d = dict(opts)
        chk(dev, f"{code}: «Аа» language menu has Português and Lietuvių (own names, not «(EN)»)",
            d.get("pt") == "Português" and d.get("lt") == "Lietuvių", str(opts))
        sel = pg.evaluate("(document.querySelector('.reader-panel select')||{}).value")
        chk(dev, f"{code}: language menu shows {code} as the current language", sel == code, str(sel))
    chk(dev, "no page errors", not errs, str(errs[:3]))
    c.close()
    b.close()


def main():
    data_checks()
    if BASE:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            for dev, eng, o in DEVICES:
                run(p, dev, eng, o)
    print(f"\n{sum(res)}/{len(res)} passed")
    sys.exit(0 if all(res) else 1)


if __name__ == "__main__":
    main()
