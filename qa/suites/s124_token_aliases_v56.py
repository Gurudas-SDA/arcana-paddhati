"""V56 step 3a — Враджа Лила 30.10.2026 (V56 journal, decision 7 «постепенно»): the DS role names (--accent, --surface-page,
--text-primary, --line-hairline, --highlight-*, …) exist as ALIASES of the live tokens in design-system/tokens.css — the same
value in all three themes (white, sepia, night), so the book looks exactly as before (visual change 0).

Rule text (Vraja Lila, verbatim, 30.10.2026 12:48): «7) постепенно, но чтобы ты не запутался, отслеживал…»; synthesis
(plan point 2): new names as aliases, old names swept out step by step.
Checks
  A) source: tokens.css declares every pair of qa/lib/ds_aliases.json as «--new: var(--old);»;
  B) app (with <base-url>), iPhone 14 + desktop, three themes: for every pair the computed custom property --new on <html>
     is identical to --old (same string, so the same colour / length / time).
# tehniskais slieksnis Lipikāra, nav S noteikums: 37 pairs = the live tokens whose value equals the DS role (list in ds_aliases.json).
usage: python s124_token_aliases_v56.py [<base-url>]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else None
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
PAIRS = json.load(open(os.path.join(ROOT, "qa", "lib", "ds_aliases.json"), encoding="utf-8"))
results = []


def check(where, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {where} {name} {'' if ok else json.dumps(info, ensure_ascii=False)[:500]}", flush=True)


def static():
    tok = re.sub(r"/\*.*?\*/", "", open(os.path.join(ROOT, "design-system", "tokens.css"), encoding="utf-8").read(), flags=re.S)
    miss = [n for n, o in PAIRS if not re.search(r"--" + re.escape(n) + r"\s*:\s*var\(--" + re.escape(o) + r"\)\s*;", tok)]
    check("src", f"A tokens.css declares all {len(PAIRS)} aliases", not miss, miss)


PROBE = """(pairs) => { const cs = getComputedStyle(document.documentElement); const bad = [];
  for (const [n, o] of pairs) { const a = cs.getPropertyValue('--' + n).trim(), b = cs.getPropertyValue('--' + o).trim(); if (!a || a !== b) bad.push([n, a, o, b]); }
  return {theme: document.documentElement.getAttribute('data-reader-theme'), bad}; }"""


def app():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        for dev, eng, opts in qa.devices(["iphone14", "desktop"]):
            b = getattr(p, eng).launch()
            for theme in ("white", "sepia", "night"):
                c = b.new_context(service_workers="block", locale="ru-RU", **opts)
                c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');"
                                  f"localStorage.setItem('ap.readerTheme','{theme}');")
                pg = c.new_page()
                pg.goto(f"{BASE}/ru-iast/", wait_until="networkidle")
                pg.wait_for_timeout(900)
                r = pg.evaluate(PROBE, PAIRS)
                check(dev, f"B {theme}: all {len(PAIRS)} aliases = their live token", (r["theme"] or "white") == theme and not r["bad"], r)
                c.close()
            b.close()


static()
if BASE:
    app()
n = sum(results)
print(f"\n{n}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
