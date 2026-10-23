"""Day release of book TEXT: the changed sections open and read right on phone, iPad and computer
(Padomnieks 2026.10.23_1609, S msg 946 «Логично, с этим согласен» + Gurudas msg 952: «S teksta izmaiņas DIENĀ:
būve + satura linteris (visa grāmata) + Playwright testi TIKAI mainītajām nodaļām/sadaļām (tālrunis, iPad, dators).
Pilnā regresija dienā — nē.»).

Which sections: QA_SECTIONS="ru-iast:conclusion,en:introduction" (lang:id; written by run_all.py --changed-from
from qa/lib/changed.py — the sections whose JSON differs from the base). Empty → all sections of en + ru-iast
(a self-check of this suite). Every page × device (iPhone 14, iPad portrait, desktop):
  1 the page opens (HTTP 200), no uncaught script error;
  2 the section title from the data is the page heading, every subsection is on the page with its title;
  3 the text of the data is on the page (every text / instruction / subtitle block and verse translation:
    5 words from it, compared letters-only — punctuation and line breaks do not matter);
  4 nothing runs off the right edge (as s13);
  5 every picture of the section loads (as s39).
A language that is not built (retired, lib/languages.json replacedBy) → SKIP.
usage: python s200_changed_sections.py <base-url>   devices: QA_DEVICES
"""
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = ["iphone14", "ipad-portrait", "desktop"]
SNIPPETS = 12  # per page — a technical sample size (Lipikāra), not an S rule
res = []


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else info}", flush=True)


def skip(dev, name, why):
    print(f"  [SKIP] {dev} {name} {why}", flush=True)


def norm(s):
    """letters and digits only, lower case, one space between words (punctuation / markup / breaks ignored)."""
    s = unicodedata.normalize("NFC", s or "").replace("­", "").replace("‍", "").replace("​", "")
    return " ".join(re.sub(r"[^\w]+|_", " ", s.lower()).split())


def book(lang):
    fn = os.path.join(qa.DATA, "book.json" if lang == "en" else f"book.{lang}.json")
    return json.load(open(fn, encoding="utf-8"))


def targets():
    v = os.environ.get("QA_SECTIONS", "").strip()
    if v:
        out = []
        for x in v.split(","):
            lang, _, sid = x.strip().partition(":")
            if sid:
                out.append((lang, sid))
        return out
    return [(lang, s["id"]) for lang in ("en", "ru-iast") for s in book(lang)["sections"]]


def snippets(section):
    """5-word samples of the section's visible text, spread over the section."""
    texts = []

    def walk(x):
        if isinstance(x, dict):
            t = x.get("type")
            if t in ("text", "instruction", "subtitle") and isinstance(x.get("content"), str):
                texts.append(x["content"])
            elif t == "verse" and isinstance(x.get("translation"), str):
                texts.append(x["translation"])
            for k, v in x.items():
                if k in ("content", "subsections", "items"):
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(section.get("content", []))
    for sub in section.get("subsections", []) or []:
        walk(sub.get("content", []))
    out = []
    for t in texts:
        w = norm(t).split()
        if len(w) >= 5:
            mid = max(0, len(w) // 2 - 2)
            out.append(" ".join(w[mid:mid + 5]))
    if len(out) > SNIPPETS:
        step = len(out) / SNIPPETS
        out = [out[int(i * step)] for i in range(SNIPPETS)]
    return out


OVERFLOW_JS = """root => {
  const W = document.documentElement.clientWidth;
  if (!root) return {W, n: -1, items: []};
  const bad = [];
  for (const e of root.querySelectorAll('*')) {
    const r = e.getBoundingClientRect();
    if (r.width === 0 || r.height === 0 || r.right <= W + 1) continue;
    const cs = getComputedStyle(e);
    if (cs.visibility === 'hidden' || cs.position === 'fixed') continue;
    let p = e.parentElement, scroller = false;
    while (p && p !== document.body) {
      const ox = getComputedStyle(p).overflowX;
      if ((ox === 'auto' || ox === 'scroll') && p.scrollWidth > p.clientWidth + 1 && !p.classList.contains('app-main')) { scroller = true; break; }
      p = p.parentElement;
    }
    if (scroller) continue;
    if ([...e.children].some(ch => ch.getBoundingClientRect().right > W + 1)) continue;
    bad.push({tag: e.tagName, right: Math.round(r.right), txt: (e.innerText || e.textContent || '').trim().slice(0, 50)});
  }
  return {W, n: bad.length, items: bad.slice(0, 4)};
}"""

PAGE_JS = """root => {
  if (!root) return null;
  const h1 = [...root.querySelectorAll('h1')].map(h => h.textContent || '');
  const subs = [...root.querySelectorAll('[data-subsection]')].map(s => ({id: s.id, text: (s.querySelector('h2') || s).textContent || ''}));
  return {h1, subs, text: root.textContent || ''};
}"""

IMAGES_JS = """async root => {
  const imgs = root ? [...root.querySelectorAll('img')] : [];
  const t0 = performance.now();
  for (const i of imgs) {
    i.scrollIntoView({block: 'center'});
    if (i.loading === 'lazy') i.loading = 'eager';
    while (!(i.complete && (i.naturalWidth > 0 || i.dataset.pngFallback)) && performance.now() - t0 < 20000)
      await new Promise(r => setTimeout(r, 50));
  }
  const bad = imgs.filter(i => !(i.complete && i.naturalWidth > 0)).map(i => (i.currentSrc || i.src || '(no src)').replace(location.origin, ''));
  return {total: imgs.length, bad};
}"""


def run(p, dev, eng, o, plist):
    b = getattr(p, eng).launch()
    c = b.new_context(locale="ru-RU", service_workers="block", **o)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    for lang, sid in plist:
        where = f"{lang}/{sid}"
        rel = f"{'' if lang == 'en' else lang + '/'}{sid}/"
        if not os.path.exists(os.path.join(qa.OUT, rel, "index.html")):
            skip(dev, f"S-izlaidums: sadaļa {where}", "(lapa nav būvēta — valoda izņemta vai sadaļas nav)")
            continue
        try:
            sec = next(s for s in book(lang)["sections"] if s["id"] == sid)
        except StopIteration:
            chk(dev, f"S-izlaidums: sadaļa {where} ir datos", False, "nav data/book")
            continue
        errs.clear()
        try:
            r = pg.goto(f"{BASE}/{rel}", wait_until="load")
            try:
                qa.wait_for_book_chapter(pg, sid)
            except Exception:
                pass
            pg.wait_for_timeout(400)
            chk(dev, f"S-izlaidums: {where} atveras (HTTP 200)", r is not None and r.ok, f"status {r.status if r else None}")
            info = qa.reading_eval(pg, PAGE_JS)
            if not info:
                chk(dev, f"S-izlaidums: {where} lasāmā daļa ir lapā", False, "nav .app-main article")
                continue
            title = norm(sec.get("title", ""))
            chk(dev, f"S-izlaidums: {where} virsraksts = dati «{sec.get('title', '')[:60]}»",
                any(title and title in norm(h) for h in info["h1"]), f"h1 {[h[:60] for h in info['h1']]}")
            have = {s["id"]: norm(s["text"]) for s in info["subs"]}
            for sub in sec.get("subsections", []) or []:
                t = norm(sub.get("title", ""))
                chk(dev, f"S-izlaidums: {where} apakšnodaļa «{sub.get('title', '')[:50]}»",
                    sub["id"] in have and t in have[sub["id"]], f"lapā: {sorted(have)[:8]}")
            text = norm(info["text"])
            missing = [s for s in snippets(sec) if s not in text]
            chk(dev, f"S-izlaidums: {where} datu teksts lapā", not missing, f"nav lapā: {missing[:3]}")
            ov = qa.reading_eval(pg, OVERFLOW_JS)
            chk(dev, f"S-izlaidums: {where} nekas neiziet pa labo malu", ov["n"] == 0, f"ширина {ov['W']}px; {ov['n']} эл.: {ov['items']}")
            im = qa.reading_eval(pg, IMAGES_JS)
            chk(dev, f"S-izlaidums: {where} attēli ielādēti ({im['total']})", not im["bad"], f"neielādēti: {im['bad'][:4]}")
            chk(dev, f"S-izlaidums: {where} bez skripta kļūdām", not errs, f"{errs[:2]}")
        except Exception as e:
            chk(dev, f"S-izlaidums: {where}", False, "ERR " + str(e)[:160])
    c.close()
    b.close()


with sync_playwright() as p:
    plist = targets()
    print(f"sadaļas: {len(plist)} — {', '.join(f'{l}:{s}' for l, s in plist[:12])}{' …' if len(plist) > 12 else ''}", flush=True)
    for dev, eng, o in qa.devices(DEVICES):
        print(dev, flush=True)
        run(p, dev, eng, o, plist)

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
