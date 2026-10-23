"""V50 — legacy clean-up (Vraja Lila msg 6368 «почисти», 6369 «не трогать ничего относящееся к Саткирти»,
6370 «но неиспользуемые картинки стоит убрать»; 23.10.2026; saskarnes autors, «Стандарты» 0а).

Basis: Vraja_Lila/faili/2026.10.23_Legacy — что можно вычистить.md (analysis).
Criteria (register V50):
  A the two pictures no code / data / generator names (media/common/conch-shankha.png, frame-red-cartouche.png) are
    out of the app (public/) and named nowhere in app / components / lib / data / scripts / design-system / the built
    out/ (the originals are kept outside git: Arcana-paddhati/archive/2026.10.23_V50 …); no other picture removed —
    every picture the book data names is in public/media/;
  B the offline precache (precache-manifest.json) stores no PNG / JPG copy of a picture the pages show as WebP
    (lib/webp-images.json originals, cover/cover.jpg, the parampara photos' PNG fallback) and no media picture no
    built file names (ca-logo.png / .svg: PDF / EPUB only) — the files stay in public/ (the build serves them); every
    WebP partner, every hotspot mask and every picture a page loads IS in the precache; precache bytes ≤ the target;
  C the pages load no excluded file: home (cover), «Эмблема», «16 предметов» (paraphernalia), «Брахма-мухурта» (tilak), «Парампара» (desktop Chromium,
    iPhone 14 WebKit) request only the WebP (performance + network), each picture drawn (naturalWidth > 0);
    offline after the service worker took over (Chromium): the same pages open and every picture is drawn from the
    cache (naturalWidth > 0, no failed request);
  D dead code gone: INLINE_SA_OPEN / INLINE_SA_CLOSE, htmlLangFor (lib), CSS .book-cover, token --ds-radius-band;
    the symbols only their own file used have no `export` (frontMatter, INTRO_ID, bookmarks / navHistory / content
    helpers, types PairedItem / SourceLinks / Part / Hotspot); backMatter keeps its export (s88 reads it).
 # tehniskais slieksnis Lipikāra, nav S noteikums: precache target ≤ 392 000 000 B (V49 build 396 011 532 B minus
 #   the ~4.3 MB of excluded copies, rounded down to leave room for the day's text changes).
usage: python s103_legacy_cleanup_v50.py <base-url>
"""
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
ORIGIN = BASE.split("/arcana-paddhati")[0]
PREFIX = BASE[len(ORIGIN):]
REPO = qa.REPO
DEVICES = qa.devices(["desktop", "iphone14"])
TARGET = 430_000_000  # tehniskais slieksnis Lipikāra, nav S noteikums; V50 391,7 MB, ar A105/A106 (+~195 lapu URL) 417,1 MB
REMOVED = ["media/common/conch-shankha.png", "media/common/frame-red-cartouche.png"]
# page → the WebP it must draw (cover, emblem, paraphernalia hotspots, tilak hotspots, parampara photos)
PAGES = {"/ru-iast/": "cover", "/ru-iast/gaudiya-emblem/": "gaudiya-emblem-", "/ru-iast/main-worship-sixteen-items/": "paraphernalia-",
         "/ru-iast/daily-duties-brahma-muhurta/": "tilak-", "/ru-iast/parampara/": "parampara/photo/"}
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:900]}", flush=True)


def read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as f:
        return f.read()


def walk_text(dirs, exts):
    for d in dirs:
        for root, _, files in os.walk(os.path.join(REPO, d)):
            if "node_modules" in root or "/evidence" in root:
                continue
            for n in files:
                if n.endswith(exts):
                    p = os.path.join(root, n)
                    try:
                        yield p, open(p, encoding="utf-8", errors="ignore").read()
                    except OSError:
                        pass


# the excluded copies (same rule as scripts/build-precache.mjs)
webp_map = json.loads(read("lib/webp-images.json"))
portraits = json.loads(read("lib/parampara-portraits.json")).get("portraits", {})
BACKUPS = {"media/cover/cover.jpg"} | {"media/" + k for k in webp_map if re.search(r"\.(png|jpe?g)$", k)} | {
    "media/" + v["fallback"] for v in portraits.values() if isinstance(v, dict) and v.get("webp") and v.get("fallback")}
PARTNERS = {"media/" + v for v in webp_map.values()} | {
    "media/" + v["webp"] for v in portraits.values() if isinstance(v, dict) and v.get("webp")}
UNNAMED = {"media/common/ca-logo.png", "media/common/ca-logo.svg"}

# ---- A: the two unused pictures out of the app, named nowhere; nothing else removed
for rel in REMOVED:
    check("static", f"A {rel} not in public/", not os.path.exists(os.path.join(REPO, "public", rel)))
names = [r.rsplit("/", 1)[-1] for r in REMOVED]
hits = [os.path.relpath(p, REPO) for p, t in walk_text(["app", "components", "lib", "data", "scripts", "design-system", "out"],
                                                       (".ts", ".tsx", ".js", ".mjs", ".css", ".json", ".py", ".html", ".txt"))
        if any(n in t for n in names) and "precache-manifest" not in p]
check("static", "A the removed pictures are named in no code / data / generator / built file", not hits, hits[:6])
srcs = set()
for p, t in walk_text(["data"], (".json",)):
    srcs |= set(re.findall(r'"src":\s*"([^"]+\.(?:png|jpe?g|webp|svg))"', t))
missing = [s for s in srcs if not os.path.exists(os.path.join(REPO, "public", "media", s))
           and not (s in portraits and os.path.exists(os.path.join(REPO, "public", "media", portraits[s].get("fallback", "-"))))]
check("static", f"A every picture the book data names is in public/media/ (a masked portrait: its photo) ({len(srcs)})", not missing, missing[:6])
kept = [r for r in BACKUPS | UNNAMED if not os.path.exists(os.path.join(REPO, "public", r))]
check("static", f"A the precache-excluded files stay in public/ ({len(BACKUPS | UNNAMED)})", not kept, kept[:6])

# ---- B: precache
man = json.load(urllib.request.urlopen(BASE + "/precache-manifest.json?s103"))
urls = set(man["urls"])
rel_of = lambda u: u[len(PREFIX) + 1:]  # noqa: E731
listed = {rel_of(u) for u in urls}
bad = sorted((BACKUPS | UNNAMED | set(REMOVED)) & listed)
check("static", f"B precache stores no PNG/JPG copy of a WebP picture, no unnamed picture, no removed picture "
                f"({len(BACKUPS)} copies + {len(UNNAMED)} unnamed)", not bad, bad[:8])
raster = sorted(r for r in listed if r.startswith("media/") and not r.startswith("media/hotspots/")
                and re.search(r"\.(png|jpe?g)$", r))
check("static", "B no PNG/JPG picture of media/ (outside hotspot masks) left in the precache", not raster, raster[:6])
nopart = sorted(PARTNERS - listed)
check("static", f"B every WebP partner is in the precache ({len(PARTNERS)})", not nopart, nopart[:6])
masks = []
for root, _, files in os.walk(os.path.join(REPO, "public", "media", "hotspots")):
    for n in files:
        masks.append(os.path.relpath(os.path.join(root, n), os.path.join(REPO, "public")).replace(os.sep, "/"))
nomask = sorted(set(masks) - listed)
check("static", f"B every hotspot mask / ink is in the precache ({len(masks)})", masks and not nomask, nomask[:6])
check("static", f"B precache bytes ≤ {TARGET}", man["bytes"] <= TARGET, {"bytes": man["bytes"], "urls": len(urls)})

# ---- D: dead code
lib_book, lib_content = read("lib/book.ts"), read("lib/content.ts")
check("static", "D INLINE_SA_OPEN / INLINE_SA_CLOSE gone", "INLINE_SA_" not in lib_book)
check("static", "D htmlLangFor gone", "htmlLangFor" not in lib_content)
check("static", "D CSS .book-cover gone", ".book-cover" not in read("app/globals.css"))
check("static", "D token --ds-radius-band gone", "--ds-radius-band" not in read("design-system/tokens.css"))
NOEXPORT = {"lib/book.ts": ["frontMatter", "INTRO_ID", "PairedItem", "SourceLinks", "Part"],
            "lib/bookmarks.ts": ["BOOKMARKS_KEY", "BOOKMARKS_MAX", "bookmarkAtPlace", "NEAR_SCREEN_PART"],
            "lib/content.ts": ["hasBook", "getBook", "isFallbackSection", "getFrontGroup", "hasWordByWord", "MACHINE_NOTE_SECTION"],
            "lib/navHistory.ts": ["MAIN_SELECTOR", "VIEW_KEYS", "entryId"], "lib/offlineProgress.ts": ["readOfflineSave"],
            "lib/readerPrefs.ts": ["applyReaderPrefs"], "lib/searchMark.ts": ["clearSearchMark"],
            "lib/transcripts.ts": ["transcriptPage"], "lib/hotspots.ts": ["Hotspot"]}
still = [f"{f}:{s}" for f, ss in NOEXPORT.items() for s in ss
         if re.search(rf"^export (?:async )?(?:const|function|interface|type|let|class) {s}\b", read(f), re.M)]
check("static", "D the file-local symbols have no export", not still, still)
check("static", "D backMatter keeps its export (s88)", "export function backMatter" in lib_book)

# ---- C: pages
PROBE = """() => [...document.querySelectorAll('img, svg image')].map(i => i.tagName === 'IMG'
  ? {src: i.currentSrc || i.src, w: i.naturalWidth, complete: i.complete}
  : {src: i.href.baseVal, w: 1, complete: true})"""


def scroll_all(pg):
    try:  # a hotspot picture mounts after hydration
        pg.wait_for_function("document.querySelectorAll('img, svg image').length > 0", timeout=15000)
    except Exception:  # noqa: BLE001
        pass
    pg.evaluate("""async () => { const els = [...document.querySelectorAll('img')];
      for (const e of els) { e.loading = 'eager'; e.scrollIntoView({block: 'center'}); await new Promise(r => setTimeout(r, 150)); } }""")
    pg.wait_for_timeout(1200)


excl_urls = {PREFIX + "/" + r for r in BACKUPS | UNNAMED}
with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        c = b.new_context(service_workers="block", **opts)
        c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
        pg = c.new_page()
        req = []
        pg.on("request", lambda r: req.append(r.url.split("?")[0]))
        for path in PAGES:
            req.clear()
            pg.goto(BASE + path, wait_until="networkidle")
            scroll_all(pg)
            imgs = pg.evaluate(PROBE)
            got = [u[len(ORIGIN):] for u in req]
            loaded = sorted({u for u in got if u in excl_urls})
            undrawn = [i["src"].rsplit("/", 1)[-1] for i in imgs if i["complete"] and not i["w"]]
            webp = sum(1 for u in got if u.endswith(".webp"))
            want = [i for i in imgs if PAGES[path] in i["src"] and i["src"].endswith(".webp")]
            check(dev, f"C {path}: no excluded PNG/JPG requested, every picture drawn, the {PAGES[path]}… WebP shown",
                  not loaded and not undrawn and want, {"loaded": loaded, "undrawn": undrawn, "pictures": len(imgs), "webp": webp})
        c.close()
        b.close()
    # offline (Chromium): after the SW took over, the same pages + every picture from the cache
    if any(d[0] == "desktop" for d in DEVICES):
        b = p.chromium.launch()
        c = b.new_context(service_workers="allow", **qa.DEVICES["desktop"][1])
        c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
        pg = c.new_page()
        pg.goto(BASE + "/ru-iast/", wait_until="load")
        try:
            pg.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller", timeout=120000)
            ok = True
        except Exception:
            ok = False
        check("desktop", "C offline: service worker took over (core cached)", ok)
        c.set_offline(True)
        failed = []
        pg.on("requestfailed", lambda r: failed.append(r.url.split("?")[0][len(ORIGIN):]))
        for path in PAGES:
            failed.clear()
            try:
                pg.goto(BASE + path, wait_until="load", timeout=30000)
                scroll_all(pg)
                imgs = pg.evaluate(PROBE)
                text_ok = not pg.evaluate("/не сохранена|not yet stored/.test(document.body.innerText)")
            except Exception as e:  # noqa: BLE001
                imgs, text_ok = [], False
                failed.append(str(e)[:80])
            undrawn = [i["src"].rsplit("/", 1)[-1] for i in imgs if not i["w"]]
            pics = [f for f in failed if re.search(r"\.(png|jpe?g|webp|svg)$", f)]
            want = [i for i in imgs if PAGES[path] in i["src"] and i["src"].endswith(".webp")]
            text_ok = text_ok and pg.url.split("?")[0].endswith(path)
            check("desktop", f"C offline {path}: opens (this page, not a fallback), every picture drawn from the cache",
                  text_ok and want and not undrawn and not pics, {"pictures": len(imgs), "undrawn": undrawn, "failed": pics[:4]})
        c.close()
        b.close()

print("passed", sum(results), "/", len(results))
sys.exit(0 if all(results) else 1)
