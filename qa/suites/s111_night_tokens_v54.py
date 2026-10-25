"""V54 Враджа Лила msg 1714 (DS V1.1 §7): ночью --ds-row-lit = --ap-band-toc; карточка «Saving to your phone» — только токены.
(nodots-izpildei 23.10 13:05; saskarnes autors, «Стандарты» 0а)

Vraja Lila (DS V1.1 §7 «исправить сразу»): in the night theme the lit row of «Содержание» was a solid #211C16
(--ds-row-lit night override) instead of --ap-band-toc (5 %); the night «Saving to your phone» card carried hard
colours (#1B1712 fill, #3A3228 line, #2E271E track) instead of tokens.
Tokens "surface-panel", "line-hairline", "surface-track" do not exist in the code; the nearest existing, unambiguous
ones are used (open question to Vraja): surface-panel = --rd-panel-bg, line-hairline = --rd-border, surface-track = --rd-hover.
Checks (night theme, per device):
  A  --ds-row-lit (probe) computes to the same colour as --ap-band-toc, and the real lit «Содержание» row (reader, menu open)
     has that colour as its background (one colour, from the token);
  B  card «Saving to your phone» (cover, state loading): fill = --rd-panel-bg, border = --rd-border, empty cell = --rd-hover;
  S  (static) the sources hold no #211C16 as a --ds-row-lit value and no hard #1B1712 / #3A3228 / #2E271E / #211C16 in the
     night .home-save rules (app/globals.css) and in design-system/tokens.css night block.
# tehniskais slieksnis Lipikāra, nav S noteikums: colours compared as computed strings of the same engine (exact), the
#   token --rd-hover is #2E271F vs old #2E271E (1 step) — accepted as the same token.
usage: python s111_night_tokens_v54.py <base-url>   (screens: V54_SHOTS=<dir> V54_SHOT_PREFIX=<prefix>)
"""
import os
import re
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
SHOTS = os.environ.get("V54_SHOTS")
SHOT_PREFIX = os.environ.get("V54_SHOT_PREFIX", "")
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CHAPTER = "vigraha-tattva"
results = []


def check(tag, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {tag} {name} {'' if ok else info}", flush=True)


def static():
    css = open(os.path.join(REPO, "app", "globals.css"), encoding="utf-8").read()
    tok = open(os.path.join(REPO, "design-system", "tokens.css"), encoding="utf-8").read()
    strip = lambda t: re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    css, tok = strip(css), strip(tok)
    night0 = re.findall(r"html\[data-reader-theme=\"night\"\]\s*\{[^}]*\}", tok)
    lit = [v for b in night0 for v in re.findall(r"--ds-row-lit\s*:\s*([^;]+);", b)]
    check("src", "S night --ds-row-lit is not a hex (no own override, or a token)", not any("#" in v for v in lit), lit)
    blocks = re.findall(r"html\[data-reader-theme=\"night\"\]\s+\.home-save[^{]*\{[^}]*\}", css)
    hard = [h for b in blocks for h in re.findall(r"#[0-9A-Fa-f]{6}\b", b) if h.upper() in ("#1B1712", "#3A3228", "#2E271E", "#211C16")]
    check("src", "S night .home-save rules hold no hard card colours", blocks and not hard, hard)
    night_tok = re.findall(r"html\[data-reader-theme=\"night\"\]\s*\{[^}]*\}", tok)
    hard_t = [h for b in night_tok for h in re.findall(r"#211C16", b.upper())]
    check("src", "S design-system/tokens.css night block holds no #211C16", night_tok and not hard_t, hard_t)


def shot(pg, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        pg.screenshot(path=os.path.join(SHOTS, f"{SHOT_PREFIX}{name}.png"))


PROBE_JS = """() => {
  const mk = (css) => { const d = document.createElement('div'); d.style.cssText = css; document.body.appendChild(d);
                        const v = getComputedStyle(d).backgroundColor; d.remove(); return v; };
  return {rowLit: mk('background:var(--ds-row-lit)'), bandToc: mk('background:var(--ap-band-toc)'),
          panel: mk('background:var(--rd-panel-bg)'), border: mk('background:var(--rd-border)'), track: mk('background:var(--rd-hover)')};
}"""
CARD_JS = """() => {
  const c = document.querySelector('.home-save'); if (!c) return null;
  const cs = getComputedStyle(c); const i = c.querySelector('.home-save-track i:last-child');
  return {bg: cs.backgroundColor, border: cs.borderTopColor, track: i ? getComputedStyle(i).backgroundColor : null};
}"""
LIT_JS = """() => { const r = document.querySelector('.mobile-menu[data-open] [data-toc-lit]') || document.querySelector('aside [data-toc-lit]');
  return r ? getComputedStyle(r).backgroundColor : null; }"""


def near(a, b, tol=2):
    pa = re.findall(r"[\d.]+", a or "")
    pb = re.findall(r"[\d.]+", b or "")
    return len(pa) == len(pb) >= 3 and all(abs(float(x) - float(y)) <= tol for x, y in zip(pa[:3], pb[:3]))


def run(browser, dev, opts):
    c = browser.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce", **opts)
    c.add_init_script("try{localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');"
                      "localStorage.setItem('ap.readerTheme','night');"
                      "localStorage.setItem('ap.offlineSave', JSON.stringify({s:'loading',d:84,t:214}));}catch(e){}")
    pg = c.new_page()
    touch = bool(opts.get("has_touch"))
    try:
        pg.goto(f"{BASE}/", wait_until="networkidle")
        pg.wait_for_timeout(1200)
        t = pg.evaluate(PROBE_JS)
        card = pg.evaluate(CARD_JS)
        check(dev, "B card exists (state loading)", card is not None, card)
        if card:
            alpha = lambda v: "0" if v and v.endswith(", 0)") else "1"
            check(dev, "B card fill = --rd-panel-bg", near(card["bg"], t["panel"]), [card["bg"], t["panel"]])
            check(dev, "B card line = --rd-border", near(card["border"], t["border"]), [card["border"], t["border"]])
            check(dev, "B empty cell = --rd-hover", near(card["track"], t["track"]), [card["track"], t["track"]])
        shot(pg, f"{dev}_kartite")
        pg.goto(f"{BASE}/ru-iast/{CHAPTER}/", wait_until="networkidle")
        pg.wait_for_timeout(900)
        for _ in range(3):
            if pg.locator(".reader-btn[data-reader-action=contents]").is_visible():
                break
            (pg.touchscreen.tap if touch else pg.mouse.click)(200, 600)
            pg.wait_for_timeout(700)
        btn = pg.locator(".reader-btn[data-reader-action=contents]")
        btn.tap() if touch else btn.click()
        pg.wait_for_selector(".mobile-menu[data-open] aside", timeout=8000)
        pg.wait_for_timeout(900)
        t = pg.evaluate(PROBE_JS)
        lit = pg.evaluate(LIT_JS)
        check(dev, "A --ds-row-lit = --ap-band-toc", t["rowLit"] == t["bandToc"], t)
        check(dev, "A real lit row of «Содержание» = --ap-band-toc", lit is not None and near(lit, t["bandToc"], 1), [lit, t["bandToc"]])
        shot(pg, f"{dev}_soderzhanie")
    except Exception as error:
        traceback.print_exc()
        check(dev, "scenario ran", False, str(error)[:300])
    finally:
        c.close()


static()
with sync_playwright() as p:
    for device, engine, options in qa.devices(["iphone14", "desktop"]):
        b = getattr(p, engine).launch()
        run(b, device, options)
        b.close()
print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
