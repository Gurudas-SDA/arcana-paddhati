"""Vraja Lila 20.10.2026 (owner of the interface, «Стандарты» 0а) — four notes, one scenario:

1. msg 5391 «нажимая вне поля, modal окно так же должно закрываться, не только нажимая на крестик»:
   the «Настроение Гурудева» window closes on a tap / click on the darkened backdrop, by the same path as
   its ✕ (its history entry is popped: afterwards history.state has no moodOverlay and the reading place
   is unchanged); a tap inside the window and a drag that starts inside and ends over the backdrop do NOT
   close it; Esc closes it (desktop).
2. msg 5392 «отцентровать картинку (на телефоне она не по центру сейчас)»: every numbered picture
   (tilak, paraphernalia, emblem) as SERVED (the WebP / PNG the page really shows) has its drawing in the
   middle: left and right empty margins differ by at most 1.5 % of the width
   # tehniskais slieksnis Lipikāra, nav S noteikums (1.5 %)
3. msg 5398/5399 «здесь списки… но нету разделения строк, как например у тилаки»: in every two-column list
   (paired-list, not vertical) each entry is one row element (.pl-row / .hs-row) and every second row has
   the same soft band as the tilak list (background not transparent).
4. msg 5400 «перед подразделом (например Bathing & Dressing) не хватает сепаратора-линии»: a group heading
   (h3) right before such a list has a top rule, unless it is the first block under the section heading.
5. msg 5393/5402 «кнопка „следующая глава" … меняет размеры» / band past the right edge: the «Next chapter»
   button box lies inside the text column (its right edge ≤ the rule above it), so its pressed band never
   runs past the screen edge.

usage: python s57_vraja_1020.py <base-url>   devices: QA_DEVICES"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
res = []
MOOD_PAGE = "daily-duties-brahma-muhurta"          # has «Gurudev's mood» blocks and the tilak picture
PICTURE_PAGES = ["daily-duties-brahma-muhurta", "worship-sixteen-articles", "gaudiya-emblem"]
LIST_PAGES = [("", "main-worship-sixteen-items"), ("ru-iast", "main-worship-sixteen-items")]
NEXT_PAGE = "daily-duties-brahma-muhurta"


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else info}", flush=True)


def url(lang, sid):
    return f"{BASE}/{lang + '/' if lang else ''}{sid}/"


def ink_margins(data):
    im = Image.open(io.BytesIO(data)).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    box = ImageOps.invert(bg.convert("L")).point(lambda v: 255 if v > 30 else 0).getbbox()
    return box[0], im.size[0] - box[2], im.size[0]


def run(p, dev, eng, o):
    b = getattr(p, eng).launch()
    c = b.new_context(locale="en-US", **o)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    pg = c.new_page()
    touch = o.get("has_touch", False)

    def tap(x, y):
        (pg.touchscreen.tap if touch else pg.mouse.click)(x, y)

    # ---- 1. mood window: backdrop closes like ✕ --------------------------------------------------
    pg.goto(url("", MOOD_PAGE), wait_until="networkidle")
    pg.wait_for_timeout(800)

    spot = {}

    def open_mood():
        pg.evaluate("()=>document.querySelector('.mood-toggle').scrollIntoView({block:'center'})")
        pg.wait_for_timeout(400)
        spot["before"] = place()
        r = pg.evaluate("()=>{const r=document.querySelector('.mood-toggle').getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}}")
        tap(r["x"], r["y"])
        pg.wait_for_timeout(700)
        return pg.evaluate("()=>!!document.querySelector('.mood-dialog')")

    def place():
        return pg.evaluate("()=>({top:(document.querySelector('.app-main')||{}).scrollTop||0, href:location.href})")

    if not open_mood():
        chk(dev, "1 mood window opens", False, "window did not open")
    else:
        d = pg.evaluate("()=>{const r=document.querySelector('.mood-dialog').getBoundingClientRect();return {l:r.left,t:r.top,r:r.right,b:r.bottom,vw:innerWidth,vh:innerHeight}}")
        tap((d["l"] + d["r"]) / 2, (d["t"] + d["b"]) / 2)
        pg.wait_for_timeout(500)
        chk(dev, "1 tap inside the window keeps it open", pg.evaluate("()=>!!document.querySelector('.mood-dialog')"))
        if not touch:
            pg.mouse.move((d["l"] + d["r"]) / 2, (d["t"] + d["b"]) / 2)
            pg.mouse.down()
            pg.mouse.move(max(2, d["l"] / 2), (d["t"] + d["b"]) / 2, steps=8)
            pg.mouse.up()
            pg.wait_for_timeout(400)
            chk(dev, "1 drag from inside released over the backdrop keeps it open",
                pg.evaluate("()=>!!document.querySelector('.mood-dialog')"))
        # a point on the backdrop: below the window if there is room, else left of it
        bx, by = (d["vw"] / 2, (d["b"] + d["vh"]) / 2) if d["vh"] - d["b"] > 16 else (max(2, d["l"] / 2), (d["t"] + d["b"]) / 2)
        tap(bx, by)
        pg.wait_for_timeout(800)
        closed = not pg.evaluate("()=>!!document.querySelector('.mood-overlay')")
        chk(dev, "1 tap on the backdrop closes the window", closed, f"point {bx:.0f},{by:.0f}")
        if closed:
            st = pg.evaluate("()=>!!(history.state&&history.state.moodOverlay)")
            after, before = place(), spot["before"]
            chk(dev, "1 backdrop close pops the window's history entry (like ✕)", not st, "history.state.moodOverlay still set")
            chk(dev, "1 reading place unchanged after backdrop close",
                after["href"] == before["href"] and abs(after["top"] - before["top"]) <= 2, f"{before} -> {after}")
        if not touch:
            if open_mood():
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(600)
                chk(dev, "1 Esc closes the window", not pg.evaluate("()=>!!document.querySelector('.mood-overlay')"))

    # ---- 2. numbered pictures: drawing centred -------------------------------------------------------
    for sid in PICTURE_PAGES:
        pg.goto(url("", sid), wait_until="networkidle")
        pg.wait_for_timeout(600)
        srcs = pg.evaluate("()=>[...new Set([...document.querySelectorAll('.hs-figure img')].map(i=>i.currentSrc||i.src))]")
        if not srcs:
            chk(dev, f"2 {sid}: numbered picture present", False, "no .hs-figure img")
        for s in srcs:
            r = pg.request.get(s)
            left, right, w = ink_margins(r.body())
            chk(dev, f"2 {s.rsplit('/', 1)[-1]} drawing centred", abs(left - right) <= 0.015 * w,
                f"left {left}px, right {right}px of {w}px")

    # ---- 3 + 4. two-column lists: bands + rule before group headings (EN + RU-IAST) -------------------
    for lang, sid in LIST_PAGES:
        pg.goto(url(lang, sid), wait_until="networkidle")
        pg.wait_for_timeout(600)
        info = pg.evaluate("""()=>{
          const grids=[...document.querySelectorAll('.reader-article div.grid')].filter(g=>/fit-content/.test(g.style.gridTemplateColumns));
          const transparent=c=>c==='rgba(0, 0, 0, 0)'||c==='transparent';
          return grids.map(g=>{
            const kids=[...g.children];
            const rows=kids.filter(k=>k.classList.contains('pl-row')||k.classList.contains('hs-row'));
            const striped=rows.filter((k,i)=>i%2===1).every(k=>!transparent(getComputedStyle(k).backgroundColor));
            const plain=rows.filter((k,i)=>i%2===0).every(k=>transparent(getComputedStyle(k).backgroundColor));
            const h=g.previousElementSibling;
            let head=null;
            if(h&&h.tagName==='H3'){
              const prev=h.previousElementSibling;
              const first=!prev||/^H[12]$/.test(prev.tagName)||prev.classList.contains('mood')||!!prev.querySelector('h2');
              head={text:h.innerText.trim(), first, rule:parseFloat(getComputedStyle(h).borderTopWidth)>=1};
            }
            return {n:kids.length, rows:rows.length, striped, plain, head};
          });
        }""")
        tag = lang or "en"
        chk(dev, f"3 {tag}/{sid}: two-column lists found", len(info) >= 2, f"{len(info)} lists")
        for i, g in enumerate(info):
            chk(dev, f"3 {tag} list {i + 1}: every entry is one row with alternating band",
                g["rows"] == g["n"] and g["rows"] > 1 and g["striped"] and g["plain"], str(g))
            h = g["head"]
            if h and not h["first"]:
                chk(dev, f"4 {tag} list {i + 1}: rule above «{h['text'][:30]}»", h["rule"], str(h))

    # ---- 5. «Next chapter» inside the screen. V17 (Vraja Lila msg 796): the block at the chapter's end is
    #      gone; the next chapter is the bottom bar's «Вперёд ›» — its band stays inside the screen ----------
    pg.goto(url("", NEXT_PAGE), wait_until="networkidle")
    pg.wait_for_timeout(900)
    n = pg.evaluate("""()=>{const a=document.querySelector('[data-reader-nav=forward]'); if(!a) return null;
      const r=a.getBoundingClientRect();
      return {right:r.right, left:r.left, col:innerWidth, vw:innerWidth, block:document.querySelectorAll('.chapter-next').length}}""")
    if n is None:
        chk(dev, "5 «Next chapter» present", False, "no [data-reader-nav=forward]")
    else:
        chk(dev, "5 «Next chapter» (bar «Вперёд ›») inside the screen, no block at the chapter's end", n["right"] <= n["col"] + 0.5 and n["left"] >= 0 and n["block"] == 0, str(n))
    b.close()


with sync_playwright() as p:
    for dev, eng, o in qa.devices(["iphone14", "pixel7", "desktop"]):
        try:
            run(p, dev, eng, o)
        except Exception as e:  # noqa: BLE001
            chk(dev, "scenario ran", False, repr(e)[:300])
print(f"s57: {sum(res)}/{len(res)} PASS")
sys.exit(0 if res and all(res) else 1)
