"""Reader v7.4 (Satkirti 06.10 23:15–23:33, 07.10 12:34–13:07): parampara + ārati songs.
  a) Contents: Обложка → Гуру-парампара (Шри Панча-таттва first, Satkirti 07.10 13:35) → Мангалачарана → ВВЕДЕНИЕ; the parampara has 8 pages,
     one guru each, in this order, exact captions; no Gour Govinda Svāmī; no visible heading,
     no number; «След. глава ›» → Мангалачарана.
  b) every portrait is shown whole: the framed oval picture is only scaled (object-fit: contain,
     rendered aspect = natural aspect), never cropped by its box or by the screen; portrait +
     caption fit on one screen (one guru per screen).
  c) maṅgala-ārati (5 songs) and gaura-ārati (2 songs) with IAST, «пословно» and «перевод».
usage: python s22_parampara_songs.py <base-url> [shots-dir]   devices: QA_DEVICES"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import qa  # noqa: E402
from lint_content import PARAMPARA_EN, PARAMPARA_RU  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
SHOTS = sys.argv[2] if len(sys.argv) > 2 else None
U = BASE + "/ru-iast/"
DEVICES = qa.devices(["pixel7", "iphone14", "s23fe", "iphone-se", "ipad-portrait", "ipad-landscape", "ipad-mini", "desktop", "mac-safari"])
res = []

PORTRAITS = """() => [...document.querySelectorAll('.app-main figure.portrait-page')].map(f => {
  const i = f.querySelector('img.portrait-img'), c = f.querySelector('figcaption');
  const r = i.getBoundingClientRect(), cs = getComputedStyle(i);
  return {cap: c.textContent.trim(), nw: i.naturalWidth, nh: i.naturalHeight, w: r.width, h: r.height,
          complete: i.complete, fit: cs.objectFit, clip: cs.clipPath, ovx: getComputedStyle(f).overflow,
          alt: i.alt, sw: document.documentElement.scrollWidth, vw: innerWidth};
})"""

ONE_SCREEN = """k => { const f = document.querySelectorAll('.app-main figure.portrait-page')[k];
  const m = document.querySelector('.app-main'); f.scrollIntoView({block: 'start'});
  const i = f.querySelector('img').getBoundingClientRect(), c = f.querySelector('figcaption').getBoundingClientRect();
  const bar = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--reader-pad-bottom')) || 0;
  return {imgTop: i.top, imgL: i.left, imgR: i.right, capBottom: c.bottom, vh: innerHeight, vw: innerWidth}; }"""


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else info}", flush=True)


def shot(pg, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        pg.screenshot(path=os.path.join(SHOTS, name + ".png"))


def run(p, dev, eng, o):
    b = getattr(p, eng).launch()
    c = b.new_context(locale="ru-RU", service_workers="block", **o)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    def goto(url):
        # let the router's link prefetches finish first: leaving a page with prefetches in flight makes
        # WebKit report each aborted fetch as a page error («… due to access control checks»)
        try:
            pg.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        pg.wait_for_timeout(300)
        pg.goto(url, wait_until="networkidle")
    try:
        # a) contents order
        goto(U); time.sleep(0.6)
        pg.evaluate("document.querySelector('[data-reader-action=contents]') && document.querySelector('[data-reader-action=contents]').click()")
        time.sleep(0.6)
        order = pg.evaluate("[...document.querySelectorAll('aside nav [data-toc-cover], aside nav .toc-scroll > ul > li')].map(l=>l.innerText.trim().split('\\n')[0].trim()).filter(Boolean).slice(0,4)")
        chk(dev, "a contents: Обложка → Гуру-парампара → Мангалачарана → ВВЕДЕНИЕ",
            order == ["Обложка", "Гуру-парампара", "Мангалачарана", "ВВЕДЕНИЕ"], order)

        # a) the parampara pages
        goto(U + "parampara/"); time.sleep(0.8)
        pg.wait_for_function("[...document.querySelectorAll('.app-main img.portrait-img')].every(i => i.complete && i.naturalWidth > 0)", timeout=20000)
        ps = pg.evaluate(PORTRAITS)
        caps = [x["cap"] for x in ps]
        chk(dev, "a Śrī Pañca-tattva page first (Satkirti 07.10 13:35)", caps[:1] == ["Шри Панча-таттва"], caps[:1])
        chk(dev, "a 8 parampara pages in order with exact captions", caps == PARAMPARA_RU, caps)
        txt = pg.evaluate("document.querySelector('.app-main').innerText")
        chk(dev, "a no Gour Govinda Svāmī", "Гоур" not in txt and "Gour" not in txt)
        vis = pg.evaluate("""[...document.querySelectorAll('.app-main h1, .app-main h2, .app-main h3, .app-main .heading-num')]
            .filter(e => { const r = e.getBoundingClientRect(); return r.width > 2 && r.height > 2; }).map(e => e.innerText)""")
        chk(dev, "a no visible heading / number on the portrait pages", vis == [], vis)
        nxt = pg.evaluate("(()=>{const a=document.querySelector('.chapter-next');return a?a.innerText.replace(/\\s+/g,' '):''})()")
        chk(dev, "a «След. глава ›» after the parampara = Мангалачарана", "Мангалачарана" in nxt, nxt)

        # b) portraits shown whole
        bad = [(x["cap"][:20], x["fit"], round(x["w"] / x["h"], 4), round(x["nw"] / x["nh"], 4))
               for x in ps if not (x["complete"] and x["nw"] > 0 and x["fit"] == "contain" and x["clip"] == "none"
                                   and abs(x["w"] / x["h"] - x["nw"] / x["nh"]) < 0.01)]
        chk(dev, "b every portrait scaled as a whole (object-fit contain, aspect kept, no clip)", not bad, bad)
        chk(dev, "b alt = caption", all(x["alt"] == x["cap"] for x in ps))
        chk(dev, "b no horizontal page scroll", ps and ps[0]["sw"] <= ps[0]["vw"] + 1, ps[0] if ps else None)
        off = []
        for k in range(len(ps)):
            g = pg.evaluate(ONE_SCREEN, k); time.sleep(0.15)
            g = pg.evaluate(ONE_SCREEN, k)
            if not (g["imgTop"] >= -1 and g["imgL"] >= -1 and g["imgR"] <= g["vw"] + 1 and g["capBottom"] <= g["vh"] + 1):
                off.append((k + 1, {kk: round(v) for kk, v in g.items()}))
            if SHOTS and k in (0, 1, 4, 8):
                shot(pg, f"{dev}-parampara-{k:02d}")
        chk(dev, "b portrait + caption on one screen, inside the screen (each guru)", not off, off)

        # a) English captions
        goto(BASE + "/parampara/"); time.sleep(0.6)
        en = [x["cap"] for x in pg.evaluate(PORTRAITS)]
        chk(dev, "a EN captions exact", en == PARAMPARA_EN, en)

        # c) songs
        for sid, n, first, title in (("mangala-arati-songs", 5, "saṁsāra-dāvānala-līḍha-loka-", "Шри Гурваштака"),
                                     ("gaura-arati-songs", 2, "jaya jaya gorācāṅdera āratiko śobhā", "Шри Гаура-арати"),
                                     # v7.6 (07.10): Kārtika bhajans — 3 songs, 8 + 9 + 13 = 30 verses
                                     ("kartika-bhajans", 3, "namāmīśvaraṁ sac-cid-ānanda-rūpaṁ", "Шри Дамодараштака")):
            goto(U + sid + "/"); time.sleep(0.6)
            info = pg.evaluate("""() => ({subs: [...document.querySelectorAll('.app-main section[data-subsection] h2')].map(h => h.innerText),
                sk: [...document.querySelectorAll('.app-main .sanskrit')].map(e => e.innerText),
                chips: [...document.querySelectorAll('.app-main .verse-chips')].map(c => c.innerText)})""")
            chips = info["chips"]
            ok_chips = chips and all(("пословно" in x.lower() and "перевод" in x.lower()) for x in chips)
            chk(dev, f"c {sid}: {n} songs, IAST, every verse with «пословно» + «перевод»",
                len(info["subs"]) == n and any(title in s for s in info["subs"]) and info["sk"] and info["sk"][0].startswith(first)
                and len(chips) == len(info["sk"]) and ok_chips,
                (info["subs"], info["sk"][:1], len(chips), len(info["sk"]), chips[:2]))
            if SHOTS and sid == "gaura-arati-songs":
                pg.locator(".app-main .verse-chip").first.click(); time.sleep(0.4)
                shot(pg, f"{dev}-gaura-arati")
        if SHOTS:
            goto(U + "mangalacarana/"); time.sleep(0.6)
            shot(pg, f"{dev}-mangalacarana")
        chk(dev, "no page errors", not errs, errs[:2])
    finally:
        b.close()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        print("==", dev, flush=True)
        run(p, dev, eng, o)
print(f"{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
