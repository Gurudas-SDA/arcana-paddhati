"""V47 — ONE gold everywhere: every gold element takes the variant B token --ap-gold; the old gold nowhere
(Vraja Lila, nodots-izpildei 22.10 22:31; saskarnes autors, «Стандарты» 0а).

Vraja Lila (screenshots 1792697323847-AQAD9RBrG5X20VJ8.jpg, 1792697323929-AQAD9hBrG5X20VJ8.jpg, iPhone, en):
«ЦВЕТА ВАРИАНТА B НЕ ВЕЗДЕ (после V43): прогресс-бар загрузки «Saving to your phone» и цветки-разделители между
стихами (❀) — прежнее светлое золото. Все золотые элементы — на один токен варианта B (design-system;
медово-янтарный, тот же, что у остальных золотых элементов), вкл. прогресс-бар, цветки, прочие украшения; пройти по
всей книге — старого золота нигде».
Criteria (register V47): the «Saving to your phone» bar and the ❀ in the token's colour in all three themes; no element
of the book shows an old gold (white / sepia / night); every gold in the code is the one token.

Old golds (before 061e919): #D4A843 (light gold: the bar, scrollbars, table rules, link underlines, portrait / caption
ornament lines), #B8860B (the ❀ at opacity 0.7, the night bar, mantra lines, the manifest), #8B6508 (dark gold: the
caption rhombus, the bookmark-row icon, portrait frames, transcripts' links), #E8B04A (the toast's «Undo»).
 # tehniskais slieksnis Lipikāra, nav S noteikums: a colour «is» an old gold when each channel is within 2 of it (any
 #   notation: rgb(), color(srgb …), hex); a translucent highlight band (alpha < 0.6 — selected row, search hit,
 #   bookmark glow; rule UI-2.4 «лёгкая полупрозрачная бежевая полоска», s07) is not a gold element and is not
 #   counted; «the token's colour» = the computed --ap-gold of that theme within 2 per channel; the ❀ «full tone» =
 #   effective opacity ≥ 0.99.

Checks, per device × theme (white, sepia, night):
  A the «Saving to your phone» bar (a probe of the home card's track: filled, part-filled cell) = the token;
  B the ❀ between the prayers of «Maṅgalācaraṇa» = the token, full tone;
  C no element (and no ::before / ::after) on the cover, «Maṅgalācaraṇa», «Парампара», «Распорядок» and on probes of
    the state-only elements (paused bar, toast «Undo», loading spinner, page-loading line) has an old gold in colour,
    background (also gradients), borders, outline, underline, fill, stroke, box-shadow;
  D the stylesheets the page loaded contain no opaque old gold;
  E (white only) a lecture transcript page: no old gold;
  S (once, from the repository next to this file) the sources contain no old gold outside the highlight bands.
usage: python s99_one_gold_v47.py <base-url>
"""
import json
import os
import re
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
SHOTS = os.environ.get("V47_SHOTS")
SHOT_PREFIX = os.environ.get("V47_SHOT_PREFIX", "2026.10.22_V47_")
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OLD = {"#D4A843": (212, 168, 67), "#B8860B": (184, 134, 11), "#8B6508": (139, 101, 8), "#E8B04A": (232, 176, 74),
       "#DAA520": (218, 165, 32)}
results = []

SCAN = """(OLD) => {
  const toRGBA = (s) => {
    const out = [];
    const re = /rgba?\\(([^)]*)\\)|color\\(srgb ([^)]*)\\)/g; let m;
    while ((m = re.exec(s))) {
      if (m[1] !== undefined) { const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number);
        out.push([p[0], p[1], p[2], p.length > 3 ? p[3] : 1]); }
      else { const p = m[2].split(/[ \\/]+/).filter(Boolean).map(Number);
        out.push([p[0] * 255, p[1] * 255, p[2] * 255, p.length > 3 ? p[3] : 1]); }
    }
    return out; };
  const isOld = (c) => c[3] >= 0.6 && Object.entries(OLD).find(([k, o]) =>
    Math.abs(c[0] - o[0]) <= 2 && Math.abs(c[1] - o[1]) <= 2 && Math.abs(c[2] - o[2]) <= 2);
  const PROPS = ['color', 'background-color', 'background-image', 'border-top-color', 'border-right-color',
    'border-bottom-color', 'border-left-color', 'outline-color', 'text-decoration-color', 'fill', 'stroke',
    'box-shadow'];
  const name = (e) => (e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') +
    (typeof e.className === 'string' && e.className ? '.' + e.className.trim().split(/\\s+/).slice(0, 3).join('.') :
     (e.getAttribute && e.getAttribute('class') ? '.' + e.getAttribute('class').split(/\\s+/)[0] : '')));
  const bad = []; let n = 0;
  for (const e of document.querySelectorAll('body *')) {
    for (const pseudo of [null, '::before', '::after']) {
      const cs = getComputedStyle(e, pseudo);
      if (pseudo && (cs.content === 'none' || cs.content === 'normal')) continue;
      n++;
      for (const p of PROPS) {
        const v = cs.getPropertyValue(p);
        if (!v || v === 'none') continue;
        // a border colour counts only where the border is drawn; an outline only where it is drawn
        if (p.startsWith('border-') && parseFloat(cs.getPropertyValue(p.replace('-color', '-width'))) === 0) continue;
        if (p === 'outline-color' && (cs.outlineStyle === 'none' || parseFloat(cs.outlineWidth) === 0)) continue;
        if (p === 'text-decoration-color' && !/underline|overline|line-through/.test(cs.textDecorationLine)) continue;
        for (const c of toRGBA(v)) { const o = isOld(c); if (o) bad.push([name(e) + (pseudo || ''), p, o[0], v.slice(0, 80)]); }
      }
    }
  }
  return {n, bad};
}"""

PROBES = """() => {
  const box = document.createElement('div'); box.id = 'qa-v47-probes';
  box.innerHTML = `
    <div class="home-save"><div class="home-save-track"><i class="on"></i><i class="part" style="--part:40%"></i><i></i></div></div>
    <div class="home-save"><div class="home-save-track is-idle"><i class="on"></i><i class="part" style="--part:40%"></i><i></i></div></div>
    <button class="reader-toast-undo">Undo</button>
    <span class="toc-loading-spin"></span>
    <div class="nav-progress" style="position:static"></div>
    <div class="verse-ornament">❀</div>`;
  document.body.appendChild(box);
  const tok = getComputedStyle(document.documentElement).getPropertyValue('--ap-gold').trim();
  const t = document.createElement('i'); t.style.color = 'var(--ap-gold)'; box.appendChild(t);
  return {token: tok, tokenRGB: getComputedStyle(t).color};
}"""

BAR = """() => { const tr = document.querySelector('#qa-v47-probes .home-save-track:not(.is-idle)');
  return {on: getComputedStyle(tr.querySelector('i.on')).backgroundColor,
          part: getComputedStyle(tr.querySelector('i.part')).backgroundImage,
          real: [...document.querySelectorAll('.home-save-track:not(#qa-v47-probes *) i.on')].map(i => getComputedStyle(i).backgroundColor)}; }"""

ORN = """() => { const eff = (e) => { let o = 1; for (let x = e; x && x.nodeType === 1; x = x.parentElement) o *= +getComputedStyle(x).opacity; return o; };
  return [...document.querySelectorAll('.verse-ornament')].filter(e => !e.closest('#qa-v47-probes')).map(e =>
    ({text: e.textContent.trim(), color: getComputedStyle(e).color, op: +eff(e).toFixed(3)})); }"""

CSS_TEXT = """() => { let t = ''; for (const s of document.styleSheets) { try { for (const r of s.cssRules) t += r.cssText + '\\n'; } catch (e) {} } return t; }"""


def check(tag, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {tag} {name} {json.dumps(evidence, ensure_ascii=False)[:900]}", flush=True)


def rgb(s):
    m = re.search(r"rgba?\(([^)]*)\)", s or "")
    if m:
        return [float(x) for x in re.split(r"[ ,/]+", m.group(1).strip()) if x][:3]
    m = re.search(r"color\(srgb ([^)]*)\)", s or "")
    if m:
        return [float(x) * 255 for x in re.split(r"[ /]+", m.group(1).strip()) if x][:3]
    return None


def same(a, b):
    a, b = rgb(a), rgb(b)
    return bool(a and b) and all(abs(x - y) <= 2 for x, y in zip(a, b))


def css_old(text):
    """Opaque old golds in stylesheet text (hex 3/6/8 digits, rgb()/rgba() with alpha ≥ 0.6, keywords)."""
    found = []
    for k, (r, g, b) in OLD.items():
        h = k[1:].lower()
        for m in re.finditer(r"#" + h + r"([0-9a-f]{2})?(?![0-9a-f])", text, re.I):
            a = int(m.group(1), 16) / 255 if m.group(1) else 1
            if a >= 0.6:
                found.append(m.group(0))
        for m in re.finditer(rf"rgba?\(\s*{r}[ ,]+{g}[ ,]+{b}\s*(?:[,/]\s*([0-9.]+%?))?\s*\)", text):
            a = m.group(1)
            a = 1 if a is None else (float(a[:-1]) / 100 if a.endswith("%") else float(a))
            if a >= 0.6:
                found.append(m.group(0))
    found += re.findall(r"(?<![\w-])(?:dark)?goldenrod(?![\w-])", text, re.I)
    return found


def static_sources():
    """S — the code itself: every gold is the token (highlight bands — translucent — excepted)."""
    roots = ["app", "components", "lib", "design-system", "public/sw.js", "public/manifest.json", "public/transcripts",
             "scripts/transcripts/build_transcripts.py"]
    exts = (".css", ".ts", ".tsx", ".js", ".html", ".py")
    bad = []
    for r in roots:
        p = os.path.join(REPO, r)
        files = [p] if os.path.isfile(p) else [os.path.join(d, f) for d, _, fs in os.walk(p) for f in fs]
        for f in files:
            if not f.endswith(exts) and not f.endswith("manifest.json"):
                continue
            try:
                text = open(f, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)       # comments name the old values on purpose
            for hit in css_old(text):
                bad.append([os.path.relpath(f, REPO), hit])
    if not os.path.isdir(os.path.join(REPO, "app")):
        print("  [INFO] S sources not found next to the suite — skipped", flush=True)
        return
    check("src", "S the sources hold no opaque old gold (one token)", not bad, {"file,value": bad[:12], "n": len(bad)})


def shot(pg, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        pg.screenshot(path=os.path.join(SHOTS, f"{SHOT_PREFIX}{name}.png"))


PAGES = [("", "cover"), ("mangalacarana", "mangalacarana"), ("parampara", "parampara"),
         ("daily-deity-schedule", "schedule")]


def run(browser, dev, opts, theme):
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    init = "try{localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');"
    init += ("localStorage.removeItem('ap.readerTheme')" if theme == "white" else f"localStorage.setItem('ap.readerTheme','{theme}')")
    c.add_init_script(init + "}catch(e){}")
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    tag = f"{dev}/{theme}"
    try:
        for path, label in PAGES:
            pg.goto(f"{BASE}/{path + '/' if path else ''}", wait_until="networkidle")
            pg.wait_for_timeout(900)
            got = pg.evaluate("() => document.documentElement.getAttribute('data-reader-theme') || 'white'")
            if label == "cover":
                check(tag, "theme applied", got == theme, {"data-reader-theme": got})
            if label == "parampara":
                try:
                    qa.load_portraits(pg, 15000)
                except Exception:
                    pass
            tok = pg.evaluate(PROBES)
            if label == "cover":
                b = pg.evaluate(BAR)
                ok = same(b["on"], tok["tokenRGB"]) and same(b["part"], tok["tokenRGB"]) and all(same(x, tok["tokenRGB"]) for x in b["real"])
                check(tag, "A «Saving to your phone» bar: filled and part-filled cells = the token --ap-gold", ok,
                      {"token": tok, "bar": b})
                css = pg.evaluate(CSS_TEXT)
                hits = css_old(css)
                check(tag, "D the loaded stylesheets hold no opaque old gold", not hits, {"hits": sorted(set(hits))[:12], "n": len(hits)})
            if label == "mangalacarana":
                orn = pg.evaluate(ORN)
                ok = bool(orn) and all(same(o["color"], tok["tokenRGB"]) and o["op"] >= 0.99 for o in orn)
                check(tag, "B ❀ between the prayers = the token, full tone", ok, {"token": tok, "ornaments": orn[:4], "n": len(orn)})
                el = pg.query_selector(".verse-ornament:not(#qa-v47-probes *)")
                if el:
                    el.scroll_into_view_if_needed()
                    pg.evaluate("() => document.getElementById('qa-v47-probes').style.display = 'none'")
                    shot(pg, f"{theme}_{dev}_zvaigznite")
                    pg.evaluate("() => document.getElementById('qa-v47-probes').style.display = ''")
            s = pg.evaluate(SCAN, {k: list(v) for k, v in OLD.items()})
            check(tag, f"C «{label}» (+ probes): no element shows an old gold", s["n"] > 20 and not s["bad"],
                  {"elements": s["n"], "old": s["bad"][:10], "nBad": len(s["bad"])})
            if label == "cover":
                pg.evaluate("""() => { const p = document.getElementById('qa-v47-probes'); p.style.cssText =
                  'position:fixed;left:16px;right:16px;bottom:16px;z-index:9999;padding:8px;background:var(--rd-bg,#fff)';
                  p.querySelectorAll('.home-save-track').forEach(t => { t.style.height = '7px'; t.style.margin = '6px 0'; }); }""")
                shot(pg, f"{theme}_{dev}_progresa-josla")
        if theme == "white":
            pg.goto(f"{BASE}/transcripts/10011-en.html", wait_until="domcontentloaded")
            s = pg.evaluate(SCAN, {k: list(v) for k, v in OLD.items()})
            check(tag, "E lecture transcript page: no element shows an old gold", s["n"] > 3 and not s["bad"],
                  {"elements": s["n"], "old": s["bad"][:8]})
        check(tag, "no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(tag, "scenario ran", False, str(error)[:300])
    finally:
        c.close()


static_sources()
with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "pixel7", "desktop"]):
        b = getattr(p, eng).launch()
        for theme in ("white", "sepia", "night"):
            run(b, dev, opts, theme)
        b.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
