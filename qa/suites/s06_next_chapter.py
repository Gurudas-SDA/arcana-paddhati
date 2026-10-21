"""Reader UI v6 (Satkirti 06.10.2026) «next chapter», rewritten for V17 (Vraja Lila msg 796 / 5635 / 5639,
20.10.2026; «Стандарты» 0а): the next chapter is the bottom bar's «Вперёд ›» (the block at the end of
every chapter is removed; the next chapter's title is not on the bar — «Название след. главы на панели — НЕ
нужно»).
usage: python s06_next_chapter.py <base-url> [shots-dir]
Checks per device: no block at the chapter end, «Вперёд ›» goes to the next page of the contents,
>= 44px target inside the screen, the bars are out at the chapter end with «Вперёд ›» on screen, opens the
next chapter at its top, browser Back / Forward history, «‹ Назад» = the previous chapter, last chapter has
no «Вперёд ›», theme colours, no third-party requests."""
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
    # V17: the parts' own pages are in the order too (the contents lists them; mock approved, msg 5639)
    ("vigraha-tattva", "temple-worship", "Часть I"),
    ("offering-bhoga", "mantras-honouring-caranamrita", "7. "),
    ("main-worship-sixteen-items", "home-worship", "Часть II. "),
    ("guru-puja-vyasa-puja", "major-festivals", "13. "),
    # v7.4 (appended last: the loop index decides which history checks run)
    # (Satkirti 07.10): parampara → Мангалачарана; Part IV ends with the ārati songs
    ("parampara", "mangalacarana", "Мангалачарана"),
    ("major-festivals", "mangala-arati-songs", "14. "),
    # v7.6 (07.10): «Бхаджаны для Картики» right after «Песни гаура-арати» — now the last chapter
    ("gaura-arati-songs", "kartika-bhajans", "16. "),
    # 22.10 (Satkirti msg 6065): «Заключение» after the parts, unnumbered — now the last page of the book
    ("kartika-bhajans", "conclusion", "Заключение"),
]
LAST = "conclusion"
res = []


def chk(d, n, ok, info=""):
    res.append((d, n, bool(ok), info)); print(f"  [{'PASS' if ok else 'FAIL'}] {d} {n} {'' if ok else info}", flush=True)


GEO = """root => { const a = document.querySelector('[data-reader-nav=forward]'); if (!a) return null;
  const r = a.getBoundingClientRect(); const bar = document.querySelector('.reader-bar-bottom').getBoundingClientRect();
  return {t: r.top, b: r.bottom, l: r.left, r: r.right, w: r.width, h: r.height, vw: innerWidth, vh: innerHeight,
    label: a.textContent.replace(/\\s+/g, ' ').trim(), target: a.getAttribute('data-chapter-target'),
    barText: document.querySelector('.reader-bar-bottom').textContent, block: document.querySelectorAll('.chapter-next, .chapter-next-link').length,
    barTop: bar.top, shown: !!document.querySelector('.reader-chrome[data-shown]'),
    fs: parseFloat(getComputedStyle(a).fontSize), color: getComputedStyle(a).color,
    tr: a.closest('[translate]') && a.closest('[translate]').getAttribute('translate')}; }"""


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
            qa.scroll_chapter(pg, 1)
            pg.wait_for_timeout(350)
        pg.wait_for_timeout(500)

    def shot(n):
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, f"v6-{dev}-{n}.png"))

    pg.goto(f"{BASE}/{LANG}/{CASES[0][0]}/", wait_until="networkidle"); pg.wait_for_timeout(700)
    pg.evaluate("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")

    def bars():
        if pg.locator(".reader-chrome[data-shown]").count() == 0:
            h1 = qa.reading_locator(pg, "article p, article h1").first.bounding_box()
            (pg.touchscreen.tap if touch else pg.mouse.click)(h1["x"] + 4, h1["y"] + h1["height"] / 2); pg.wait_for_timeout(500)

    for i, (cid, nid, title0) in enumerate(CASES):
        pg.goto(f"{BASE}/{LANG}/{cid}/", wait_until="networkidle"); pg.wait_for_timeout(800)
        bars()
        g = qa.reading_eval(pg, GEO)
        if not g:
            chk(dev, f"{cid}: «Вперёд ›» present", False, "no [data-reader-nav=forward]"); continue
        chk(dev, f"{cid}: no next-chapter block at the chapter's end (V17)", g["block"] == 0, str(g))
        chk(dev, f"{cid}: «Вперёд ›» -> {nid}", g["label"].replace(" ", "").replace(" ", "") == "Вперёд›" and g["target"] == nid, str(g))
        chk(dev, f"{cid}: the next chapter's title is not on the bar ({title0}…)", title0 not in g["barText"], str(g))
        chk(dev, f"{cid}: translate=no (the browser offers no translation)", g["tr"] == "no", str(g))
        chk(dev, f"{cid}: tap target >= 44px high, inside the screen", g["h"] >= 44 and g["w"] >= 44 and g["l"] >= 0 and g["r"] <= g["vw"] + 0.5, str(g))
        to_end()
        g = qa.reading_eval(pg, GEO)
        chk(dev, f"{cid}: at the chapter end the bars are out, «Вперёд ›» fully on screen", g["shown"] and g["t"] >= 0 and g["b"] <= g["vh"] + 0.5, str(g))
        if i == 1:
            shot("1-chapter-end")
        before = pg.url
        act(pg.locator("[data-reader-nav=forward]"))
        pg.wait_for_timeout(600)
        top = qa.reading_eval(pg, f"root => {{ const h = root.querySelector('article h1, article header'); return {{st: {qa.READING_POSITION_JS}.top, h1: h ? h.getBoundingClientRect().top : -1}}; }}")
        chk(dev, f"{cid}: tap opens {nid}", pg.url.rstrip("/").endswith(f"/{LANG}/{nid}"), pg.url)
        chk(dev, f"{cid}: next chapter starts at its top", top["st"] <= 2 and 0 <= top["h1"] < 200, str(top))
        if i == 1:
            shot("2-next-chapter-top")
        # history: browser Back / Forward; «‹ Назад» (bottom bar) = the previous chapter (V17)
        if i in (0, 3):
            pg.go_back(); pg.wait_for_timeout(1000)
            chk(dev, f"{cid}: browser Back returns to {cid}", pg.url == before, pg.url)
            pos = pg.evaluate(f"(() => {{ const p = {qa.READING_POSITION_JS}; return {{st: p.top, max: p.max}}; }})()")
            chk(dev, f"{cid}: ...at the place where the reader left it (chapter end)", pos["st"] >= pos["max"] - 40, str(pos))
            pg.go_forward(); pg.wait_for_timeout(1000)
            chk(dev, f"{cid}: browser Forward -> {nid} again", pg.url.rstrip("/").endswith(f"/{nid}"), pg.url)
        else:
            bars()
            act(pg.locator("[data-reader-nav=back]")); pg.wait_for_timeout(700)
            chk(dev, f"{cid}: «‹ Назад» returns to {cid} (the previous chapter)", pg.url == before, pg.url)

    # last chapter: no «Вперёд ›»; empty part page: to the next one
    pg.goto(f"{BASE}/{LANG}/{LAST}/", wait_until="networkidle"); pg.wait_for_timeout(600)
    bars()
    chk(dev, f"{LAST} (last chapter): no «Вперёд»", pg.locator("[data-reader-nav=forward]").count() == 0 and pg.locator(".chapter-next").count() == 0)
    if dev in ("iphone14", "ipad-portrait"):
        to_end(); shot("3-last-chapter-end")
    pg.goto(f"{BASE}/{LANG}/home-worship/", wait_until="networkidle"); pg.wait_for_timeout(600)
    bars()
    g = qa.reading_eval(pg, GEO)
    chk(dev, "empty part page (Часть II) -> Часть III", bool(g) and g["target"] == "preaching-centres", str(g))

    # English page: English label
    pg.goto(f"{BASE}/vigraha-tattva/", wait_until="networkidle"); pg.wait_for_timeout(600)
    bars()
    g = qa.reading_eval(pg, GEO)
    chk(dev, "English page: «Forward ›» -> /temple-worship/ (V17: the part's page is in the order)", bool(g) and g["label"].startswith("Forward") and g["target"] == "temple-worship", str(g))

    # themes + «Аа»: «Вперёд ›» is a control of the bar (its size stays), in the theme's accent colour
    pg.goto(f"{BASE}/{LANG}/vigraha-tattva/", wait_until="networkidle"); pg.wait_for_timeout(600)
    bars()
    fs0 = qa.reading_eval(pg, GEO)["fs"]
    pg.evaluate("document.documentElement.style.setProperty('--reader-zoom','1.22')"); pg.wait_for_timeout(200)
    fs1 = qa.reading_eval(pg, GEO)["fs"]
    chk(dev, "«Вперёд ›» keeps its size with «Аа» (a bar control, not the text)", abs(fs1 - fs0) < 0.5, f"{fs0} -> {fs1}")
    pg.evaluate("document.documentElement.style.removeProperty('--reader-zoom')")
    pg.evaluate("document.documentElement.setAttribute('data-reader-theme','night')"); pg.wait_for_timeout(200)
    g = qa.reading_eval(pg, GEO)
    chk(dev, "night theme: gold «Вперёд ›»", g["color"] == "rgb(227, 160, 60)", str(g))
    if dev in ("iphone14", "ipad-portrait"):
        shot("4-night")
    pg.evaluate("document.documentElement.setAttribute('data-reader-theme','sepia')"); pg.wait_for_timeout(200)
    g = qa.reading_eval(pg, GEO)
    chk(dev, "sepia theme: accent «Вперёд ›»", g["color"] == "rgb(150, 87, 0)", str(g))
    if dev in ("iphone14", "ipad-portrait"):
        shot("5-sepia")
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
