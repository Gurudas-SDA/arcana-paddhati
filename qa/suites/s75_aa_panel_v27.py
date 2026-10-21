"""V27 — the «Аа» panel (Vraja Lila msg 5769–5779, 21.10.2026; saskarnes autors, «Стандарты» 0а).

Rule text (verbatim, Vraja Lila):
  «не обрезай это окно, пока что есть место уместить весь контент этого окна»;
  «язык (выбор языка) перемести перед размером текста… он должен быть первой функцией»;
  «когда это окно открыто, фон так же должен затемнятся на 60%»;
  «и те же 60% во время выбора языка».
The 60 % dimming is the one the other windows already have (V18: black 60 %, no blur — s68).

Checks (each device; phones also turned):
  1. order: the language field is the panel's first function — above «Размер текста» (DOM order and on screen);
  2. not cut while there is room: the whole content shows without inner scrolling when it fits between the panel's
     top and the screen's bottom; when it does not fit, the panel uses the screen down to its bottom edge
     # tehniskais slieksnis Lipikāra, nav S noteikums: bottom margin 8 px (±1 px), «fits» = top + content + 8 ≤ height;
  3. panel open: the page behind is dimmed black 60 %, no blur; a tap on the dimming closes the panel;
  4. language list open: its dimming is the same black 60 %, no blur — in all three backgrounds;
  5. V27b (Vraja Lila msg 5876 «затемнение дублируется… затемнения всегда должны быть 60%»): the language list over the
     «Аа» panel adds no second dimming — a page pixel beside both has the same colour as with the «Аа» panel alone
     # tehniskais slieksnis Lipikāra, nav S noteikums: each RGB channel within ±2.
  6. V27c (Vraja Lila msg 1172: with the «Аа» panel open the top bar (Содержание/Поиск/Аа) is dimmed too, exactly like
     under the language list — one 60 % dimming over everything, the panel itself above it): a top-bar pixel (its own
     background, left edge, mid height) is 40 % of its colour before the panel opened
     # tehniskais slieksnis Lipikāra, nav S noteikums: each RGB channel within ±6 of 0.4 × before.
usage: python s75_aa_panel_v27.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
PAGE = "vigraha-tattva"
DIM = "rgba(0, 0, 0, 0.6)"
results = []


def turned(name, eng, opts):
    o = dict(opts)
    v = o["viewport"]
    o["viewport"] = {"width": v["height"], "height": v["width"]}
    return (name + "-landscape", eng, o)


DEVICES = qa.devices(["iphone14", "pixel7", "s23fe", "iphone-se", "ipad-portrait", "desktop"])
DEVICES += [turned(n, e, o) for n, e, o in DEVICES if n in ("iphone14", "pixel7")]


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


def shot_px(pg, pt):
    import io
    from PIL import Image
    im = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
    sx = im.width / pg.viewport_size["width"]
    return im.getpixel((int(pt[0] * sx), int(pt[1] * sx)))


BAR_PT = """() => { const b = document.querySelector('.reader-bar-top').getBoundingClientRect();
  return [3, Math.round(b.top + b.height / 2)]; }"""


def show_bars(pg):
    for _ in range(4):
        if pg.evaluate("!!document.querySelector('.reader-chrome[data-shown]')"):
            return
        pg.evaluate("""() => { const m = document.querySelector('.app-main'); const r = m.getBoundingClientRect();
          const o = {bubbles: true, isPrimary: true, button: 0, pointerId: 1, pointerType: 'mouse', clientX: r.left + 20, clientY: r.top + r.height / 2};
          const t = document.elementFromPoint(o.clientX, o.clientY) || m;
          t.dispatchEvent(new PointerEvent('pointerdown', o)); t.dispatchEvent(new PointerEvent('pointerup', o)); }""")
        pg.wait_for_timeout(450)


PANEL = """async () => { const p = document.querySelector('.reader-panel'); if (!p) return null;
  await Promise.all(p.getAnimations().map(a => a.finished.catch(() => null))); const r = p.getBoundingClientRect();
  const lang = p.querySelector('[data-lang-trigger]'), size = p.querySelector('[data-reader-size]');
  const labels = [...p.querySelectorAll('.reader-panel-label')].map(e => e.textContent.trim());
  return {top: r.top, bottom: r.bottom, sh: p.scrollHeight, ch: p.clientHeight, vh: innerHeight,
    langFirst: !!(lang && size && (lang.compareDocumentPosition(size) & Node.DOCUMENT_POSITION_FOLLOWING)),
    langY: lang && Math.round(lang.getBoundingClientRect().top), sizeY: size && Math.round(size.getBoundingClientRect().top), labels}; }"""

DIMMING = """(sel) => { const d = document.querySelector(sel); if (!d) return null; const c = getComputedStyle(d); const r = d.getBoundingClientRect();
  return {bg: c.backgroundColor, filter: c.backdropFilter || c.webkitBackdropFilter || 'none', l: r.left, t: r.top, r: r.right, b: r.bottom, w: innerWidth, h: innerHeight}; }"""

with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        c = b.new_context(service_workers="block", locale="ru-RU", **opts)
        c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');")
        pg = c.new_page()
        pg.goto(f"{BASE}/ru-iast/{PAGE}/", wait_until="networkidle")
        pg.wait_for_timeout(900)
        show_bars(pg)
        bar_pt = pg.evaluate(BAR_PT)
        bar_before = shot_px(pg, bar_pt)
        pg.evaluate("document.querySelector('[data-reader-action=aa]').click()")
        pg.wait_for_timeout(500)
        s = pg.evaluate(PANEL)
        if not s:
            check(dev, "«Аа» panel opens", False, "no .reader-panel")
            c.close()
            b.close()
            continue
        # 6. V27c: the top bar is under the same 60 % dimming
        bar_after = shot_px(pg, bar_pt)
        check(dev, "«Аа» open: the top bar dimmed too — 40 % of its colour (one 60 % dimming over everything)",
              all(abs(a - 0.4 * b0) <= 6 for a, b0 in zip(bar_after, bar_before)), {"pt": bar_pt, "before": bar_before, "after": bar_after})
        # 1. language first
        check(dev, "«Язык» is the first function — before «Размер текста»",
              s["langFirst"] and s["langY"] < s["sizeY"], s)
        # 2. not cut while there is room
        fits = s["top"] + s["sh"] + 8 <= s["vh"] + 0.5
        if fits:
            check(dev, "the whole content shows (it fits on the screen) — no inner scrolling", s["sh"] <= s["ch"] + 1, s)
        else:
            check(dev, "content taller than the screen: the panel reaches down to the screen's bottom (8 px)",
                  abs(s["bottom"] - (s["vh"] - 8)) <= 1.5, s)
        # 3. dimming behind the panel
        d = pg.evaluate(f"({DIMMING})('.reader-panel-backdrop')")
        check(dev, "panel open: the page behind dimmed black 60 %, no blur, the whole screen",
              d and d["bg"] == DIM and d["filter"] in ("none", "") and d["l"] <= 0 and d["t"] <= 0 and d["r"] >= d["w"] and d["b"] >= d["h"], d)
        # 5. V27b: one dimming layer — the page pixel left of the panel / below the list, panel only vs panel + list
        def px(pt):
            import io
            from PIL import Image
            im = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
            sx = im.width / pg.viewport_size["width"]
            return im.getpixel((int(pt[0] * sx), int(pt[1] * sx)))
        spot = pg.evaluate("""() => { const p = document.querySelector('.reader-panel').getBoundingClientRect();
          return p.left > 24 ? [Math.round(p.left / 2), Math.round(innerHeight * 0.55)] : [8, Math.round(innerHeight - 30)]; }""")
        pg.wait_for_timeout(300)
        one = px(spot)
        pg.evaluate("document.querySelector('.reader-panel [data-lang-trigger]').click()")
        pg.wait_for_timeout(500)
        # the spot must lie outside the list card
        out = pg.evaluate(f"""(() => {{ const c = document.querySelector('.lang-card[role=listbox]').getBoundingClientRect();
          return !({spot[0]} >= c.left && {spot[0]} <= c.right && {spot[1]} >= c.top && {spot[1]} <= c.bottom); }})()""")
        two = px(spot)
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(400)
        check(dev, "language list over «Аа»: one dimming (page pixel same as with «Аа» alone, ±2)",
              out and all(abs(a - b) <= 2 for a, b in zip(one, two)), {"spot": spot, "outsideList": out, "aaOnly": one, "aaAndList": two})
        # 4. language list: same 60 % in every background
        for theme in ("white", "sepia", "night"):
            pg.evaluate(f"document.querySelector('[data-reader-theme-btn={theme}]') && document.querySelector('[data-reader-theme-btn={theme}]').click()")
            pg.wait_for_timeout(200)
            pg.evaluate("document.querySelector('.reader-panel [data-lang-trigger]').click()")
            pg.wait_for_timeout(400)
            ld = pg.evaluate(f"({DIMMING})('.lang-backdrop[data-lang-backdrop]')")
            check(dev, f"language list ({theme}): dimming black 60 %, no blur", ld and ld["bg"] == DIM and ld["filter"] in ("none", ""), ld)
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(350)
        pg.evaluate("document.querySelector('[data-reader-theme-btn=white]') && document.querySelector('[data-reader-theme-btn=white]').click()")
        pg.wait_for_timeout(200)
        # a tap on the dimming closes the panel
        still = pg.evaluate("!!document.querySelector('.reader-panel')")
        pt = pg.evaluate("""() => { const p = document.querySelector('.reader-panel').getBoundingClientRect();
          return p.left > 40 ? [Math.round(p.left / 2), Math.round(innerHeight / 2)] : [Math.round(innerWidth / 2), Math.round(Math.min(innerHeight - 70, p.bottom + (innerHeight - p.bottom) / 2))]; }""") if still else None
        if pt:
            hit = pg.evaluate(f"(() => {{ const e = document.elementFromPoint({pt[0]}, {pt[1]}); return e ? e.className : null; }})()")
            if opts.get("has_touch"):
                pg.touchscreen.tap(pt[0], pt[1])
            else:
                pg.mouse.click(pt[0], pt[1])
            pg.wait_for_timeout(500)
            closed = not pg.evaluate("!!document.querySelector('.reader-panel')")
            check(dev, "a tap on the dimming closes the panel", closed and "reader-panel-backdrop" in str(hit), {"pt": pt, "hit": hit, "closed": closed})
        else:
            check(dev, "a tap on the dimming closes the panel", False, "panel closed before the tap")
        c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
