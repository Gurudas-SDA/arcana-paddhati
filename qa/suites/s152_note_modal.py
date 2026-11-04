"""V76 - Vraja Lila msg 7553, verbatim:
«1) под модальным окном можно "мотать" страницу... и нету overlay'a как-то странно работает само модальное окно
2) если выделенный текс огромен... может есть смысл показать только цвета и окно ввода your note, не показывать наверху в окне тот текст, который был выделен, т.к. если там огромный кусок окошка не хватит
3) когда заметка сохранена и при нажатии на неё, открывается модальное окно с цветами, заметкой и снизу 3 кнопки... это окно нужно сделать по ширине таким же как модальное окно.... сейчас оно обрублено... и контент внутри окна должен быть отцентрован а кнопки снизу должны быть распространены по ширине»
Criteria: (1) overlay fills the viewport; wheel/touch under the window does not move the page (scrollY); (2) a long quote is not shown in the
note window, a short one is; (3) the saved-note popover is as wide as the note window (+-2 px), centred, its 3 buttons fill the width.
# tehniskais slieksnis Lipikara, nav S noteikums: settle 300-900 ms; long quote = more than 110 characters
usage: python s152_note_modal.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
PAGE = "daily-duties-brahma-muhurta"
results = []


def check(dev, name, ok, ev=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else json.dumps(ev, ensure_ascii=False)[:600]}", flush=True)


SELECT = """([n, a, b]) => {
  const nodes = [];
  for (const p of document.querySelectorAll('.app-main article p')) {
    if (!p.getClientRects().length || p.closest('button,table,[hidden],.mood-panel')) continue;
    const w = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
    for (let x = w.nextNode(); x; x = w.nextNode()) if ((x.data.match(/\\S+/g) || []).length >= 25 && x.parentElement.getClientRects().length) nodes.push(x);
  }
  const node = nodes[n]; if (!node) return null;
  node.parentElement.scrollIntoView({block: 'center'});
  const d = node.data; const ws = [...d.matchAll(/\\S+/g)];
  const s = ws[a].index, e = ws[Math.min(b, ws.length) - 1].index + ws[Math.min(b, ws.length) - 1][0].length;
  const r = document.createRange(); r.setStart(node, s); r.setEnd(node, e);
  const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
  return d.slice(s, e); }"""
BOX = "(sel) => { const e = document.querySelector(sel); if (!e) return null; const b = e.getBoundingClientRect(); return {l: b.left, r: b.right, t: b.top, b: b.bottom, w: b.width}; }"


def make_note(pg, a, b, note):
    txt = pg.evaluate(SELECT, [0, a, b])
    pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    pg.locator("[data-hl-menu] [data-hl-note]").click()
    pg.wait_for_selector("[data-hl-editor] textarea", state="visible", timeout=4000)
    return txt


def run(p, dev, eng, opts):
    b = getattr(p, eng).launch()
    c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce", **opts)
    c.add_init_script("try{if(!sessionStorage.getItem('s152')){sessionStorage.setItem('s152','1');localStorage.removeItem('ap.highlights');}"
                      "localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');}catch(e){}")
    pg = c.new_page()
    pg.goto(f"{BASE}/ru-iast/{PAGE}/", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    pg.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important}")
    # short quote
    short = make_note(pg, 2, 6, "x")
    check(dev, "short quote: shown in the note window", pg.locator("[data-hl-editor-quote]").count() == 1 and len(short) <= 110, [short, pg.locator("[data-hl-editor-quote]").count()])
    vp = pg.evaluate("() => [innerWidth, innerHeight]")
    ov = pg.evaluate(BOX, ".bookmark-name-backdrop")
    check(dev, "overlay exists and covers the viewport", ov and ov["l"] <= 0.5 and ov["t"] <= 0.5 and ov["r"] >= vp[0] - 0.5 and ov["b"] >= vp[1] - 0.5, [ov, vp])
    y0 = pg.evaluate("() => scrollY")
    pg.mouse.move(vp[0] / 2, 10)
    pg.mouse.wheel(0, 600)
    pg.wait_for_timeout(400)
    pg.evaluate("() => window.scrollBy(0, 400)")
    pg.wait_for_timeout(300)
    y1 = pg.evaluate("() => scrollY")
    check(dev, "page under the window does not scroll (wheel / scroll attempt)", abs(y1 - y0) < 1, [y0, y1])
    mw = pg.evaluate(BOX, "[data-hl-modal='editor'] [role=dialog]")
    pg.locator("[data-hl-editor] textarea").fill("Заметка")
    pg.locator("[data-hl-editor] [data-hl-save]").click()
    pg.wait_for_timeout(500)
    # long quote
    pg.evaluate("() => scrollTo(0, 0)")
    long_ = make_note(pg, 0, 40, "")
    check(dev, "long quote (>110 chars): no quote block", len(long_) > 110 and pg.locator("[data-hl-editor-quote]").count() == 0, [len(long_), pg.locator("[data-hl-editor-quote]").count()])
    check(dev, "long quote: colours and the note field are there", pg.locator("[data-hl-editor] [data-hl-color-kind='editor']").count() == 4 and pg.locator("[data-hl-editor] textarea").is_visible())
    pg.locator("[data-hl-editor] [data-hl-save]").click()
    pg.wait_for_timeout(500)
    # popover
    pg.wait_for_selector("[data-hl-marker]", timeout=4000)
    pg.locator("[data-hl-marker]").first.click()
    pg.wait_for_selector("[data-hl-card]", timeout=4000)
    cb = pg.evaluate(BOX, "[data-hl-card]")
    check(dev, "popover width = note window width (+-2 px)", cb and mw and abs(cb["w"] - mw["w"]) <= 2, [cb, mw])
    check(dev, "popover is centred horizontally", cb and abs((cb["l"] + cb["r"]) / 2 - vp[0] / 2) <= 2, [cb, vp])
    btns = pg.evaluate("() => [...document.querySelectorAll('[data-hl-card] .hl-icon')].map(e => { const b = e.getBoundingClientRect(); return [b.left, b.right]; })")
    wd = [x[1] - x[0] for x in btns]
    inner = cb["w"] if cb else 0
    check(dev, "3 buttons fill the width equally", len(btns) == 3 and max(wd) - min(wd) <= 2 and sum(wd) >= inner * 0.8, [btns, inner])
    cy = pg.evaluate("() => scrollY")
    pg.mouse.wheel(0, 500)
    pg.wait_for_timeout(300)
    check(dev, "page under the popover does not scroll", abs(pg.evaluate("() => scrollY") - cy) < 1, cy)
    b.close()


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "pixel7"]):
        try:
            run(p, dev, eng, opts)
        except Exception as e:  # noqa: BLE001
            check(dev, "scenario ran to the end", False, repr(e)[:400])
print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
