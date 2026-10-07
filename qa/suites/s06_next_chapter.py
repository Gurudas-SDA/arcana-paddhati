"""Reader UI v6 (Satkirti 06.10.2026): «След. глава ›» at the end of every chapter.
usage: python v6_test.py <base-url> [shots-dir]   (ONLY=pixel,iphone ...)
Checks per device: link after the last block, next chapter's number + title,
>= 44px target, clear of the bottom bar at the chapter end, opens the next
chapter at its top, Back / «‹ Назад» / Forward history, last chapter has no
link, theme colours, «Аа» scaling, translate=no, no third-party requests."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402  (device profiles, repo paths)
import os, sys
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
BASE = sys.argv[1].rstrip("/"); SHOTS = sys.argv[2] if len(sys.argv) > 2 else None
ONLY = None  # device filter: QA_DEVICES (qa/lib/qa.py)
HOST = urlparse(BASE).netloc
IOS_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
IPAD_UA = IOS_UA.replace("iPhone; CPU iPhone OS", "iPad; CPU OS")
PIXEL_UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36")
DEVICES = qa.devices(['iphone14', 'iphone-se', 'pixel7', 'ipad-portrait', 'ipad-landscape', 'desktop'])
LANG = "ru-iast"
# (chapter, expected next id, expected start of the title line)
CASES = [
    # v7 (Satkirti 06.10): Introduction group without numbers, Part I numbered from 1
    ("introduction", "gaudiya-emblem", "Эмблема Гаудия-матха"),
    # v7.1 (Satkirti 06.10): Мангалачарана before Введение, outside the group
    ("mangalacarana", "introduction", "Введение"),
    ("vigraha-tattva", "daily-duties-brahma-muhurta", "1. "),
    ("offering-bhoga", "mantras-honouring-caranamrita", "7. "),
    ("main-worship-sixteen-items", "home-worship", "Часть II. "),
    ("guru-puja-vyasa-puja", "major-festivals", "13. "),
    # v7.4 (appended last: the loop index decides which history checks run)
    # (Satkirti 07.10): parampara → Мангалачарана; Part IV ends with the ārati songs
    ("parampara", "mangalacarana", "Мангалачарана"),
    ("major-festivals", "mangala-arati-songs", "14. "),
]
LAST = "gaura-arati-songs"
res = []


def chk(d, n, ok, info=""):
    res.append((d, n, bool(ok), info)); print(f"  [{'PASS' if ok else 'FAIL'}] {d} {n} {'' if ok else info}", flush=True)


GEO = """() => { const a = document.querySelector('.chapter-next-link'); if (!a) return null;
  const art = document.querySelector('.app-main article'); const r = a.getBoundingClientRect();
  const lab = a.querySelector('.chapter-next-label'), tit = a.querySelector('.chapter-next-title');
  const last = art.lastElementChild; const bar = document.querySelector('.reader-bar-bottom').getBoundingClientRect();
  return {t: r.top, b: r.bottom, l: r.left, r: r.right, w: r.width, h: r.height, vw: innerWidth, vh: innerHeight,
    label: lab.textContent.trim(), title: tit.textContent.trim(), href: a.getAttribute('href'),
    isLast: last && last.classList.contains('chapter-next'), barTop: bar.top,
    shown: !!document.querySelector('.reader-chrome[data-shown]'),
    labFs: parseFloat(getComputedStyle(lab).fontSize), titFs: parseFloat(getComputedStyle(tit).fontSize),
    labColor: getComputedStyle(lab).color, titColor: getComputedStyle(tit).color,
    tr: a.closest('[translate]') && a.closest('[translate]').getAttribute('translate'),
    labFont: getComputedStyle(lab).fontFamily, bodyFont: getComputedStyle(document.querySelector('.app-main article h1')).fontFamily}; }"""


def run(p, dev, eng, o):
    br = getattr(p, eng).launch()
    touch = o.get("has_touch", False)
    errs, foreign = [], []
    ctx = br.new_context(service_workers="block", **o)
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("request", lambda r: foreign.append(r.url) if urlparse(r.url).netloc not in (HOST, "") and not r.url.startswith(("data:", "blob:")) else None)

    def act(loc):
        loc.scroll_into_view_if_needed()
        loc.tap() if touch else loc.click(); pg.wait_for_timeout(700)

    def to_end():
        # scroll like a reader: in steps, so the reader sees the chapter end
        for _ in range(3):
            pg.evaluate("(() => { const m = document.querySelector('.app-main'); m.scrollTop = m.scrollHeight; m.dispatchEvent(new Event('scroll')); })()")
            pg.wait_for_timeout(350)
        pg.wait_for_timeout(500)

    def shot(n):
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, f"v6-{dev}-{n}.png"))

    pg.goto(f"{BASE}/{LANG}/{CASES[0][0]}/", wait_until="networkidle"); pg.wait_for_timeout(700)
    pg.evaluate("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")

    for i, (cid, nid, title0) in enumerate(CASES):
        pg.goto(f"{BASE}/{LANG}/{cid}/", wait_until="networkidle"); pg.wait_for_timeout(800)
        g = pg.evaluate(GEO)
        if not g:
            chk(dev, f"{cid}: link present", False, "no .chapter-next-link"); continue
        chk(dev, f"{cid}: link is the article's last block (after all content)", g["isLast"], str(g))
        chk(dev, f"{cid}: «След. глава ›» -> {nid}", g["label"].replace(" ", " ") == "След. глава ›" and g["href"].rstrip("/").endswith(f"/{LANG}/{nid}"), str(g))
        chk(dev, f"{cid}: next chapter's title under it ({title0}…), smaller", g["title"].startswith(title0) and g["titFs"] < g["labFs"] and g["t"] < g["b"], str(g))
        chk(dev, f"{cid}: tap target >= 44px high, inside the screen", g["h"] >= 44 and g["w"] >= 44 and g["l"] >= 0 and g["r"] <= g["vw"] + 0.5, str(g))
        chk(dev, f"{cid}: translate=no, book serif font", g["tr"] == "no" and "Noto Serif" in g["labFont"], str(g))
        to_end()
        g = pg.evaluate(GEO)
        chk(dev, f"{cid}: at the chapter end the link is fully visible above the bottom bar", g["t"] >= 0 and g["b"] <= (g["barTop"] if g["shown"] else g["vh"]) + 0.5, str(g))
        if i == 1:
            shot("1-chapter-end")
        before = pg.url
        act(pg.locator(".chapter-next-link"))
        pg.wait_for_timeout(600)
        top = pg.evaluate("(() => { const m = document.querySelector('.app-main'); const h = document.querySelector('.app-main article h1, .app-main article header'); return {st: m.scrollTop, h1: h ? h.getBoundingClientRect().top : -1}; })()")
        chk(dev, f"{cid}: tap opens {nid}", pg.url.rstrip("/").endswith(f"/{LANG}/{nid}"), pg.url)
        chk(dev, f"{cid}: next chapter starts at its top", top["st"] <= 2 and 0 <= top["h1"] < 200, str(top))
        if i == 1:
            shot("2-next-chapter-top")
        # history: «‹ Назад» (bottom bar) back, «Вперёд ›» forward, browser Back
        if i in (0, 3):
            pg.go_back(); pg.wait_for_timeout(1000)
            chk(dev, f"{cid}: browser Back returns to {cid}", pg.url == before, pg.url)
            pos = pg.evaluate("(() => { const m = document.querySelector('.app-main'); return {st: m.scrollTop, max: m.scrollHeight - m.clientHeight}; })()")
            chk(dev, f"{cid}: ...at the place where the reader left it (chapter end)", pos["st"] >= pos["max"] - 40, str(pos))
            pg.go_forward(); pg.wait_for_timeout(1000)
            chk(dev, f"{cid}: browser Forward -> {nid} again", pg.url.rstrip("/").endswith(f"/{nid}"), pg.url)
        else:
            if pg.locator(".reader-chrome[data-shown]").count() == 0:
                pg.evaluate("(() => { const m = document.querySelector('.app-main'); m.scrollTop = 400; })()"); pg.wait_for_timeout(200)
                pg.evaluate("(() => { const m = document.querySelector('.app-main'); m.scrollTop = 0; })()"); pg.wait_for_timeout(300)
            if pg.locator(".reader-chrome[data-shown]").count() == 0:
                h1 = pg.locator(".app-main article p").first.bounding_box()
                (pg.touchscreen.tap if touch else pg.mouse.click)(h1["x"] + 4, h1["y"] + h1["height"] / 2); pg.wait_for_timeout(500)
            act(pg.locator("[data-reader-nav=back]")); pg.wait_for_timeout(700)
            chk(dev, f"{cid}: «‹ Назад» returns to {cid}", pg.url == before, pg.url)

    # last chapter: no link; non-empty part page: no link
    pg.goto(f"{BASE}/{LANG}/{LAST}/", wait_until="networkidle"); pg.wait_for_timeout(600)
    chk(dev, f"{LAST} (last chapter): no «След. глава»", pg.locator(".chapter-next").count() == 0)
    if dev in ("iphone14", "ipad-portrait"):
        to_end(); shot("3-last-chapter-end")
    pg.goto(f"{BASE}/{LANG}/home-worship/", wait_until="networkidle"); pg.wait_for_timeout(600)
    g = pg.evaluate(GEO)
    chk(dev, "empty part page (Часть II) -> Часть III", bool(g) and g["href"].rstrip("/").endswith("/preaching-centres"), str(g))

    # English page: English label
    pg.goto(f"{BASE}/vigraha-tattva/", wait_until="networkidle"); pg.wait_for_timeout(600)
    g = pg.evaluate(GEO)
    chk(dev, "English page: «Next chapter ›» -> /daily-duties-brahma-muhurta/ (v7.1: Maṅgalācaraṇa before the Introduction)", bool(g) and g["label"].startswith("Next chapter") and g["href"].rstrip("/").endswith("/daily-duties-brahma-muhurta"), str(g))

    # themes + «Аа»
    pg.goto(f"{BASE}/{LANG}/vigraha-tattva/", wait_until="networkidle"); pg.wait_for_timeout(600)
    fs0 = pg.evaluate(GEO)["labFs"]
    pg.evaluate("document.documentElement.style.setProperty('--reader-zoom','1.22')"); pg.wait_for_timeout(200)
    fs1 = pg.evaluate(GEO)["labFs"]
    chk(dev, "link text follows «Аа»", fs1 > fs0 * 1.15, f"{fs0} -> {fs1}")
    pg.evaluate("document.documentElement.style.removeProperty('--reader-zoom')")
    pg.evaluate("document.documentElement.setAttribute('data-reader-theme','night')"); pg.wait_for_timeout(200)
    g = pg.evaluate(GEO)
    chk(dev, "night theme: gold label, light-muted title", g["labColor"] == "rgb(212, 168, 67)" and g["titColor"] == "rgb(187, 174, 154)", str(g))
    if dev in ("iphone14", "ipad-portrait"):
        to_end(); shot("4-night")
    pg.evaluate("document.documentElement.setAttribute('data-reader-theme','sepia')"); pg.wait_for_timeout(200)
    g = pg.evaluate(GEO)
    chk(dev, "sepia theme: accent label, muted title", g["labColor"] == "rgb(184, 134, 11)" and g["titColor"] == "rgb(92, 61, 46)", str(g))
    if dev in ("iphone14", "ipad-portrait"):
        to_end(); shot("5-sepia")
    pg.evaluate("document.documentElement.removeAttribute('data-reader-theme')")

    chk(dev, "no requests to third-party hosts", not foreign, "; ".join(foreign[:5]))
    chk(dev, "no page errors", not errs, "; ".join(errs[:3]))
    ctx.close(); br.close()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        if ONLY and dev not in ONLY.split(","):
            continue
        print(dev, flush=True)
        try:
            run(p, dev, eng, o)
        except Exception as e:
            chk(dev, "EXCEPTION", False, str(e)[:900])
fails = [r for r in res if not r[2]]
print(f"\n{len(res) - len(fails)}/{len(res)} passed")
for f in fails:
    print("FAILED:", f[0], f[1], f[3][:300])
