"""V49 — Noto Serif with a TRUE italic in our own cut; the Google fallback files out of the offline cache
(Vraja Lila msg 6363/6364 «big да», 23.10.2026; saskarnes autors, «Стандарты» 0а).

Context (faili/2026.10.23_V48 Вес и читаемость — Noto Serif и Charis SIL.md, measured on the live book): the book
loads only the upright cut (3 own woff2, 68 324 B); italic — the Sanskrit (IAST verses, the Russian Sanskrit
transliteration), translations, sources — is the browser's synthetic slant of the upright; the offline cache
(public/sw.js + precache-manifest.json) also stores the 8 Google Noto Serif fallback files (457 296 B), and 4 book
characters (U+0307, һ, ӣ, ӯ) were outside the cut.
Criteria (register V49):
  A an italic element (IAST verse, source, Russian Sanskrit) is drawn by a loaded ITALIC face of our cut: the
    browser downloaded our italic woff2 (performance resource entries ↔ the @font-face rules of our families) and
    document.fonts has an italic face of the element's family, loaded, covering every character of the element (or,
    as Chromium draws ṁ ṣ ī, every part of its canonical decomposition — m + U+0307 — by a loaded italic face); on
    Chromium also the platform font of the node (CDP CSS.getPlatformFontsForNode) is the italic Noto Serif — not
    synthetic; no Google Noto Serif file is downloaded on these pages;
  B the offline precache lists no Google fallback woff2 — only our cut;
  C the italic cut of each script has exactly the characters of the upright cut, and together they hold every
    book character Noto Serif has (fontTools on app/fonts/*.woff2).
 # tehniskais slieksnis Lipikāra, nav S noteikums: up to 40 italic elements per page are checked (all kinds present);
 #   «Noto Serif has» = the character is in any Noto Serif file of the build (own cut or Google fallback).
Pictures (V49_SHOTS=<dir>, V49_SHOT_PREFIX=<prefix>): <prefix><place>.png of the first IAST verse's word-by-word,
an English verse's word-by-word, a source and a Russian Sanskrit word-by-word (iPhone 14) — for the «было / стало» pairs.
usage: python s102_true_italic_v49.py <base-url>
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
# page, selector of the italic kind it must show (the verse's word-by-word Sanskrit words and translation are
# italic; the verse lines themselves are bold upright), picture (name, element)
PAGES = [
    ("/ru-iast/mangalacarana/", ".wbw-word", ("iast_pants", ".verse-wbw")),
    ("/mangalacarana/", ".wbw-word", ("en_pants", ".verse-wbw")),
    ("/ru-iast/conclusion/", ".source-note", ("avots", ".source-note")),
    # ("/ru/arcana-procedure/", …) — Cyrillic Russian removed from the book (S 23.10 Padomnieks 934–941)
]
SHOTS = os.environ.get("V49_SHOTS")
SHOT_PREFIX = os.environ.get("V49_SHOT_PREFIX", "V49_")
MAX_EL = 40  # tehniskais slieksnis Lipikāra
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:900]}", flush=True)


PROBE = """async ([sel, maxEl]) => {
  await document.fonts.ready;
  const norm = s => s.replace(/["']/g, '').trim();
  // @font-face rules: family, style, url
  const rules = [];
  for (const sh of document.styleSheets) { let rs; try { rs = sh.cssRules; } catch (e) { continue; }
    for (const r of rs) if (r instanceof CSSFontFaceRule) {
      const m = /url\\(["']?([^"')]+)/.exec(r.style.getPropertyValue('src'));
      rules.push({family: norm(r.style.getPropertyValue('font-family')), style: r.style.getPropertyValue('font-style') || 'normal',
                  url: m ? new URL(m[1], sh.href || location.href).href : null}); } }
  const faces = [...document.fonts].map(f => ({family: norm(f.family), style: f.style, status: f.status, range: f.unicodeRange, weight: f.weight}));
  const inRange = (cp, range) => range.split(',').some(p => { const m = /U\\+([0-9A-F?]+)(?:-([0-9A-F]+))?/i.exec(p.trim());
    if (!m) return false; let a, b; if (m[1].includes('?')) { a = parseInt(m[1].replace(/\\?/g, '0'), 16); b = parseInt(m[1].replace(/\\?/g, 'F'), 16); }
    else { a = parseInt(m[1], 16); b = m[2] ? parseInt(m[2], 16) : a; } return cp >= a && cp <= b; });
  const ours = f => /arcana/i.test(f);
  const els = [...document.querySelectorAll('.app-main *, main *')].filter(e => {
    const cs = getComputedStyle(e); if (cs.fontStyle !== 'italic' || cs.visibility === 'hidden') return false;
    // painted now: in the viewport (an off-screen page / column is not laid out, its fonts are not asked for)
    const r = e.getBoundingClientRect(); if (!r.width || !r.height || r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) return false;
    return [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()); });
  const kind = els.filter(e => e.closest(sel)).length;
  const bad = [];
  const sample = [...els.filter(e => e.closest(sel)).slice(0, maxEl / 2), ...els.filter(e => !e.closest(sel)).slice(0, maxEl / 2)];
  els.filter(e => e.closest(sel)).slice(0, 8).forEach(e => { e.setAttribute('data-s102', '');
    // its upright children (a link «транскрипт», «[…]») are hidden for the platform-font reading only
    e.querySelectorAll('*').forEach(c => { if (getComputedStyle(c).fontStyle !== 'italic') c.setAttribute('data-s102-skip', ''); }); });
  for (const e of sample) {
    const fams = getComputedStyle(e).fontFamily.split(',').map(norm);
    const text = [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('');
    for (const ch of new Set([...text])) { const cp = ch.codePointAt(0); if (cp <= 0x20 || cp === 0xA0) continue;
      const fam = fams.find(f => faces.some(x => x.family === f && inRange(cp, x.range)));
      if (!fam) continue;  // no web font has it (system font) — counted in C
      const it = faces.find(x => x.family === fam && x.style === 'italic' && x.status === 'loaded' && inRange(cp, x.range));
      // Chromium (HarfBuzz) may draw a precomposed letter (ṁ ṣ ī) by its parts (m + U+0307) from the first family
      // that has them — then the parts must be in a loaded italic face of our cut
      const parts = [...ch.normalize('NFD')].map(x => x.codePointAt(0));
      const byParts = parts.length > 1 && parts.every(q => faces.some(x => ours(x.family) && fams.includes(x.family) &&
        x.style === 'italic' && x.status === 'loaded' && inRange(q, x.range)));
      if (!byParts && (!it || !ours(fam))) { bad.push({el: e.className.slice(0, 40), ch, cp: cp.toString(16), fam}); break; } } }
  const res = performance.getEntriesByType('resource').map(r => r.name).filter(u => u.endsWith('.woff2'));
  const itUrls = rules.filter(r => ours(r.family) && r.style === 'italic').map(r => r.url);
  const googleUrls = rules.filter(r => !ours(r.family)).map(r => r.url);
  return {n: els.length, kind, bad, itLoaded: res.filter(u => itUrls.includes(u)).map(u => u.split('/').pop()),
          googleLoaded: res.filter(u => googleUrls.includes(u)).map(u => u.split('/').pop()),
          italicFaces: faces.filter(x => ours(x.family) && x.style === 'italic').map(x => x.family + ' ' + x.status),
          rules};
}"""

own_urls, google_urls = set(), set()
with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        for path, sel, shot in PAGES:
            c = b.new_context(service_workers="block", **opts)
            c.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
            pg = c.new_page()
            pg.goto(BASE + path, wait_until="networkidle")
            pg.wait_for_timeout(600)
            # open the first verses' panels (word-by-word, translation — closed at load) so their italic is drawn,
            # and bring the first element of the kind into the viewport
            pg.evaluate("[...document.querySelectorAll('.verse-chip')].slice(0, 6).forEach(c => c.click())")
            pg.wait_for_timeout(500)
            pg.locator(sel).first.scroll_into_view_if_needed()
            pg.wait_for_timeout(1200)
            pg.wait_for_load_state("networkidle")
            r = pg.evaluate(PROBE, [sel, MAX_EL])
            for x in r["rules"]:
                (own_urls if "arcana" in x["family"].lower() else google_urls).add(x["url"])
            check(dev, f"{path}: italic elements ({sel}) present", r["kind"] > 0, {"italic": r["n"], sel: r["kind"]})
            check(dev, f"{path}: A every italic character drawn by a loaded italic face of our cut",
                  r["n"] > 0 and not r["bad"], {"bad": r["bad"][:6], "italicFaces": r["italicFaces"]})
            check(dev, f"{path}: A our italic woff2 downloaded (resource entries)", len(r["itLoaded"]) > 0,
                  {"italic woff2": r["itLoaded"]})
            check(dev, f"{path}: A no Google Noto Serif file downloaded", not r["googleLoaded"], {"google": r["googleLoaded"]})
            if eng == "chromium":
                pg.add_style_tag(content="[data-s102-skip]{display:none!important}")
                pg.wait_for_timeout(200)
                cdp = c.new_cdp_session(pg)
                cdp.send("DOM.enable")
                cdp.send("CSS.enable")
                doc = cdp.send("DOM.getDocument", {"depth": -1})
                ids = cdp.send("DOM.querySelectorAll", {"nodeId": doc["root"]["nodeId"], "selector": "[data-s102]"})["nodeIds"]
                plat = set()
                for nid in ids:
                    for f in cdp.send("CSS.getPlatformFontsForNode", {"nodeId": nid})["fonts"]:
                        plat.add(f"{f['familyName']}|{f.get('postScriptName', '')}|{f['glyphCount']}")
                synth = [x for x in plat if "italic" not in x.lower() and "Noto" in x]
                check(dev, f"{path}: A platform font of {sel} = the italic Noto Serif (not a synthetic slant)",
                      plat and not synth, {"fonts": sorted(plat)})
            if SHOTS and shot and dev == "iphone14":
                os.makedirs(SHOTS, exist_ok=True)
                el = pg.locator(shot[1]).first
                el.scroll_into_view_if_needed()
                pg.wait_for_timeout(300)
                el.screenshot(path=os.path.join(SHOTS, f"{SHOT_PREFIX}{shot[0]}.png"))
            c.close()
        b.close()

    # B — offline precache
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto(BASE + "/", wait_until="domcontentloaded")
    man = pg.evaluate("async u => (await fetch(u)).json()", BASE + "/precache-manifest.json")
    urls = [u if isinstance(u, str) else (u.get("url") or "") for u in (man.get("urls") or man.get("files") or [])]
    fonts = [u for u in urls if u.split("?")[0].endswith(".woff2")]
    own_paths = {u.split("/_next/", 1)[-1] for u in own_urls if u}
    google_paths = {u.split("/_next/", 1)[-1] for u in google_urls if u}
    in_google = [u for u in fonts if u.split("/_next/", 1)[-1] in google_paths]
    not_own = [u for u in fonts if u.split("/_next/", 1)[-1] not in own_paths]
    sizes = {u.rsplit("/", 1)[-1]: pg.evaluate("async u => (await (await fetch(u)).arrayBuffer()).byteLength",
                                                (BASE.split("/arcana-paddhati")[0] + u) if u.startswith("/") else u) for u in fonts}
    check("precache", "B no Google Noto Serif fallback woff2 in the offline precache, only our cut",
          fonts and not in_google and not not_own,
          {"woff2": len(fonts), "google": [u.rsplit('/', 1)[-1] for u in in_google], "bytes": sum(sizes.values())})
    print(f"  precache woff2: {len(fonts)} files, {sum(sizes.values())} B {json.dumps(sizes)}", flush=True)
    b.close()

# C — the cut (fontTools)
from fontTools.ttLib import TTFont  # noqa: E402
fdir = os.path.join(qa.REPO, "app", "fonts")
book = set()
for f in glob.glob(os.path.join(qa.DATA, "book*.json")):
    book |= {ord(ch) for ch in open(f, encoding="utf-8").read() if ord(ch) > 0x20}
noto = set()
for f in glob.glob(os.path.join(qa.OUT, "_next", "static", "media", "*.woff2")) + glob.glob(os.path.join(fdir, "*.woff2")):
    noto |= set(TTFont(f).getBestCmap())
need = book & noto
up, it = set(), set()
for s in ("latin", "latinext", "cyrillic"):
    fu, fi = os.path.join(fdir, f"arcana-serif-{s}.woff2"), os.path.join(fdir, f"arcana-serif-{s}-italic.woff2")
    cu = set(TTFont(fu).getBestCmap())
    ci = set(TTFont(fi).getBestCmap()) if os.path.exists(fi) else set()
    up |= cu
    it |= ci
    check("cut", f"C {s}: italic cut has exactly the characters of the upright cut", ci == cu,
          {"upright": len(cu), "italic": len(ci), "only upright": [hex(x) for x in sorted(cu - ci)][:12]})
check("cut", f"C every book character Noto Serif has ({len(need)}) is in the upright AND the italic cut",
      need <= up and need <= it,
      {"book chars": len(need), "missing upright": [chr(x) + hex(x) for x in sorted(need - up)],
       "missing italic": [chr(x) + hex(x) for x in sorted(need - it)][:20]})

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
