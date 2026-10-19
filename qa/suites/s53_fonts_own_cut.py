"""Fonts: the upright Noto Serif in our own cut (Vraja Lila msg 5316 p. 4, 20.10.2026; «Шрифты — разбор»).

Rule text (verbatim): «Шрифты: прямое начертание своей нарезкой (italic — нет).»
Checks per page (cover, Parampara, a long chapter; RU-IAST and EN):
  - the text is drawn by our cut (loaded FontFaces of the --font-arcana-* families), the full Google Noto Serif
    files are not downloaded for these pages (they stay as a fallback for characters outside the cut);
  - preloaded font bytes ≤ 80 KB (was 248 KB) — # tehniskais slieksnis Lipikāra, nav S noteikums (~67 KB measured).
usage: python s53_fonts_own_cut.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
PAGES = ["/ru-iast/", "/ru-iast/parampara/", "/ru-iast/caturmasya-purusottama-masa/", "/arcana-procedure/"]
DEVICES = qa.devices(["pixel7", "iphone14", "desktop"])
PRELOAD_MAX = 80 * 1024  # tehniskais slieksnis Lipikāra, nav S noteikums
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        for path in PAGES:
            c = b.new_context(service_workers="block", **opts)
            c.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
            pg = c.new_page()
            fonts = []
            pg.on("response", lambda r: fonts.append(r.url) if r.url.endswith(".woff2") else None)
            pg.goto(BASE + path, wait_until="networkidle")
            pg.wait_for_timeout(800)
            info = pg.evaluate("""async () => { await document.fonts.ready;
              const pre = [...document.querySelectorAll('link[rel=preload][as=font]')].map(l => l.href);
              const loaded = [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family);
              const fam = getComputedStyle(document.querySelector('.app-main') || document.body).fontFamily;
              return {pre, loaded, fam}; }""")
            sizes = []
            for u in info["pre"]:
                sizes.append(pg.evaluate("async u => (await (await fetch(u)).arrayBuffer()).byteLength", u))
            ours = [f for f in info["loaded"] if "Noto Serif" not in f]
            google = [f for f in info["loaded"] if f.strip("'\"") == "Noto Serif"]
            check(dev, f"{path}: text drawn by our cut, the full Noto Serif not downloaded",
                  ours and not google, {"loaded": info["loaded"], "woff2": [u.rsplit('/', 1)[-1] for u in fonts]})
            check(dev, f"{path}: preloaded fonts ≤ {PRELOAD_MAX // 1024} KB", sum(sizes) <= PRELOAD_MAX and len(sizes) >= 1,
                  {"files": len(sizes), "bytes": sum(sizes)})
            c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
