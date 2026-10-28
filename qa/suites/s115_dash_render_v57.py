"""V57 — Враджа Лила 23.10 13:36 (msg 1732/6487): «это некорректное отображение текста» — a double hyphen «--» in
the running text must be SHOWN as the typographic dash «—» (en/ru typography). Satkirti's source texts (data/book*.json)
are NOT changed: the dash is made when rendering (lib/book.ts parseInline).

Checks
  a) data: the source texts still contain « -- » (nothing was edited in data/); list per language is printed;
  b) rendering (node, lib/book.ts parseInline) of EVERY text of EVERY book*.json that has « -- »: the shown text has no «--»
     and has «—»; a Sanskrit ⟦…⟧ run and a URL / «a--b» without spaces stay unchanged;
  c) app (with <base-url>), iPhone 14: en /arcana-procedure/ and ru-iast /main-worship-sixteen-items/ show no « -- » and show « — ».
usage: python s115_dash_render_v57.py [<base-url>]
"""
import glob
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else None
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
DATA = os.path.join(ROOT, "data")
DASH = re.compile(r"(?<![-\w])--(?!-)|(?<!-)--(?![-\w])")
results = []


def check(where, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {where} {name} {'' if ok else info}".rstrip(), flush=True)


def strings(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from strings(v)
    elif isinstance(o, str):
        yield o


per = {}
for f in sorted(glob.glob(os.path.join(DATA, "book*.json"))):
    lang = os.path.basename(f)[5:-5] or "en"
    per[lang] = [s for s in strings(json.load(open(f, encoding="utf-8"))) if DASH.search(s)]
print("  « -- » in data per language:", {k: len(v) for k, v in per.items() if v})
check("data", "a the source texts still have « -- » (data/ not edited)", len(per.get("en", [])) >= 1 and len(per.get("ru-iast", [])) >= 1)

JS = """
import { parseInline } from %r;
const texts = JSON.parse(process.argv[1]);
const shown = texts.map(t => parseInline(t).filter(r => !r.sanskrit).map(r => r.text).join(''));
const extra = ['a ⟦x -- y⟧ b -- c', 'ID 1OP8gUMHDrqZaN6--CHD3FLK7tNt7qWZR end', 'a--b'].map(t => parseInline(t).map(r => r.sanskrit ? '⟦' + r.text + '⟧' : r.text).join(''));
console.log(JSON.stringify({ shown, extra }));
""" % ("file://" + os.path.abspath(os.path.join(ROOT, "lib", "book.ts")),)
for lang, texts in per.items():
    if not texts:
        continue
    out = subprocess.run(["node", "--experimental-strip-types", "--no-warnings", "--input-type=module", "-e", JS, json.dumps(texts)],
                         capture_output=True, text=True)
    try:
        r = json.loads(out.stdout.strip().splitlines()[-1])
    except Exception:
        check(lang, "b node render ran", False, out.stderr[-300:])
        continue
    bad = [s[:50] for s in r["shown"] if "--" in s or "—" not in s]
    check(lang, f"b {len(texts)} texts shown with «—», none with «--»", not bad, bad[:2])
    if lang == "en":
        e = r["extra"]
        check(lang, "b ⟦…⟧ run, URL id and «a--b» unchanged", e[0] == "a ⟦x -- y⟧ b — c" and "6--C" in e[1] and e[2] == "a--b", e)

if BASE is None:
    print(f"{sum(results)}/{len(results)} passed")
    sys.exit(0 if results and all(results) else 1)

from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as p:
    for device, engine, options in qa.devices(["iphone14"]):
        browser = getattr(p, engine).launch()
        context = browser.new_context(service_workers="block", **options)
        page = context.new_page()
        for lang, chap in (("en", "arcana-procedure"), ("ru-iast", "main-worship-sixteen-items")):
            page.goto(f"{BASE}{qa.lang_prefix(lang)}/{chap}/", wait_until="load")
            page.wait_for_selector("main p", state="attached", timeout=20000)
            txt = page.evaluate("document.body.textContent")
            check(f"{device} {lang}/{chap}", "c no « -- » shown, « — » shown", not DASH.search(txt) and " — " in txt)
        context.close()
        browser.close()
print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
