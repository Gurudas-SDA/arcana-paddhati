"""V56 step 2 — Враджа Лила 30.10.2026 (V56 journal, decision 8): «в единое золото» — the frames of the Parampara
portraits take the ONE gold token --ap-gold (#965700 on white / sepia, #E3A03C at night); the old golds #8B6508 and
#D4A843 stay nowhere in the portrait frame data.

Rule text (Vraja Lila, verbatim, 30.10.2026 12:48): «8) в единое золото» (to the plan question «цвет рамок в данных портретов
Парампары … перевести на единое золото?»).
Facts (30.10): components/PortraitImg.tsx MaskedPortrait already draws the frame lines with stroke var(--ap-gold) and ignores
the manifest «color»; the manifest (lib/parampara-portraits.json), scripts/parampara/check.json and render_parampara.py
still carried #8B6508 / #D4A843 as dead data. They now carry «var(--ap-gold)» — data = what is drawn.
Checks
  A) source: lib/parampara-portraits.json and scripts/parampara/check.json — every frame line colour is «var(--ap-gold)»,
     no #8B6508 / #D4A843 in them; render_parampara.py frame spec emits «var(--ap-gold)»; MaskedPortrait still strokes var(--ap-gold);
  B) app (with <base-url>), iPhone 14 + desktop, white and night: every .portrait-frame-lines path on /ru-iast/parampara/ is stroked
     with the computed --ap-gold of the theme (#965700 / #E3A03C).
usage: python s123_portrait_gold_v56.py [<base-url>]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else None
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
TOKEN = "var(--ap-gold)"
results = []


def check(where, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {where} {name} {'' if ok else json.dumps(info, ensure_ascii=False)[:500]}", flush=True)


def rd(*p):
    return open(os.path.join(ROOT, *p), encoding="utf-8").read()


def static():
    man = json.loads(rd("lib", "parampara-portraits.json"))["portraits"]
    cols = [l["color"] for v in man.values() for l in v.get("frame", {}).get("lines", [])]
    check("src", "A manifest: every frame line colour = var(--ap-gold)", cols and all(c == TOKEN for c in cols), sorted(set(cols)))
    chk = rd("scripts", "parampara", "check.json")
    cols2 = re.findall(r'"color"\s*:\s*"([^"]+)"', chk)
    check("src", "A check.json: every frame line colour = var(--ap-gold)", cols2 and all(c == TOKEN for c in cols2), sorted(set(cols2)))
    for name, text in (("manifest", json.dumps(man)), ("check.json", chk)):
        check("src", f"A {name}: no #8B6508 / #D4A843", not re.search(r"#8B6508|#D4A843", text, re.I))
    gen = rd("scripts", "parampara", "render_parampara.py")
    m = re.search(r'def frame_spec.*?(?=\ndef )', gen, re.S) or re.search(r'"lines": \[.*?\]\}', gen, re.S)
    body = m.group(0) if m else ""
    check("src", "A render_parampara.py frame spec: colours = var(--ap-gold), no GOLD_D / GOLD in «color»", body and TOKEN in body and not re.search(r'"color":\s*"#%02X', body), body[-300:])
    tsx = rd("components", "MaskedPortrait.tsx")
    check("src", "A MaskedPortrait strokes var(--ap-gold)", 'stroke: "var(--ap-gold)"' in tsx)


PROBE = """() => { const mk = () => { const d = document.createElement('div'); d.style.color = 'var(--ap-gold)'; document.body.appendChild(d);
    const c = getComputedStyle(d).color; d.remove(); return c; };
  const ps = [...document.querySelectorAll('.portrait-frame-lines path')];
  return {gold: mk(), n: ps.length, strokes: [...new Set(ps.map(p => getComputedStyle(p).stroke))]}; }"""


def app():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        for dev, eng, opts in qa.devices(["iphone14", "desktop"]):
            b = getattr(p, eng).launch()
            for theme, want in (("white", "rgb(150, 87, 0)"), ("night", "rgb(227, 160, 60)")):
                c = b.new_context(service_workers="block", locale="ru-RU", **opts)
                c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');"
                                  f"localStorage.setItem('ap.readerTheme','{theme}');")
                pg = c.new_page()
                pg.goto(f"{BASE}/ru-iast/parampara/", wait_until="networkidle")
                pg.wait_for_timeout(1500)
                r = pg.evaluate(PROBE)
                check(dev, f"B {theme}: frame lines present and stroked with the theme's gold {want}", r["n"] > 0 and r["gold"] == want and r["strokes"] == [want], r)
                c.close()
            b.close()


static()
if BASE:
    app()
n = sum(results)
print(f"\n{n}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
