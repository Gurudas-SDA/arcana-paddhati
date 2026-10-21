"""V33 — WCAG 2.1 AA without changing the book's look: one accent tone, variant B (Vraja Lila msg 5865, 5900–5907,
21.10.2026; saskarnes autors, «Стандарты» 0а).

Rule text (verbatim, Vraja Lila msg 5907): «Вариант B, делай по-красоте!»
Variant B (PDF «2026.10.21_WCAG цвета v2 — варианты A и B», Vraja_Lila/faili): one gold tone for every gold icon,
text, frame and focus ring — #965700 on the light backgrounds (white, sepia), #E3A03C on the dark one; the
«Установить» band keeps white text and a white ✕ on a darker gold (#A56000 → #965700) (msg 5900–5904: №7, 8, 12
«как было»; the icon and the word next to it of one colour); the tap areas of ✕ in the search field and ✕ of
the band 44×44, unseen; «Содержание» opened from the keyboard puts the focus into the panel (search field);
the light highlight under a finger in sepia no longer under the norm (was #E5D8BC, 4.07).
Checks (iPhone 14 WebKit, Pixel 7 + desktop Chromium; white, sepia, dark):
  - contrast WCAG 2.1 (1.4.3 text 4.5:1, large text 3:1; 1.4.11 icons, frames, focus ring 3:1), measured on the
    rendered page (getComputedStyle; a half-transparent colour is blended over the first opaque background):
    every text in «Содержание» (closed and with search results), «Вперёд ›», the status line, the top-bar icons,
    the «пословно / перевод» buttons, the «Настроение Гурудева» window, the accent on the finger highlight,
    the band «Установить» (white text, button, ✕) on its gradient (phones), ✕ of «Содержание», the focus rings;
  - the icon has the colour of the word next to it: book icon = «Содержание», magnifier = search frame;
  - tap areas: ✕ in the search field and ✕ of the band take a tap 22 px around their centre (44×44);
  - the search field has ONE frame line, also in focus (Vraja Lila msg 1233/1253: «одна рамка»), ≥ 3:1;
  - keyboard (desktop): Enter on «Содержание» → the focus is on the search field in the open panel; Escape →
    back on «Содержание». A tap on a phone does not focus the field (no keyboard pops up).
  # tehniskais slieksnis Lipikāra, nav S noteikums: 44×44 for ✕ = WCAG 2.5.5 (AAA in 2.1; «Стандарты» do not give a
  #   size); the numbers on the pictures (2.1–2.6, the small copy) are not held to 44 — neighbours overlap; the
  #   check is the unseen 12 px wider area of the maket: tap area ≥ 24 px (WCAG 2.2 2.5.8) where it was smaller.
  # tehniskais slieksnis Lipikāra: text with own opacity < 0.99 (animating, disabled, pale removed bookmark) is
  #   not measured (WCAG 1.4.3 excludes inactive controls).
usage: python s81_wcag_v33.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
THEMES = ["white", "sepia", "night"]
CHAPTER = "vigraha-tattva"
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:1200]}", flush=True)


LIB = r"""
window.__wc = (() => {
  const parse = s => { if (!s) return null; s = s.trim();
    if (s[0] === '#') { const h = s.slice(1); const f = h.length === 3 ? h.split('').map(x => x + x).join('') : h;
      return [parseInt(f.slice(0, 2), 16), parseInt(f.slice(2, 4), 16), parseInt(f.slice(4, 6), 16), 1]; }
    const m = s.match(/^rgba?\(([^)]+)\)$/);
    if (m) { const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; }
    // color(srgb …), oklab(…), color-mix results: let the browser paint it on a 1×1 canvas and read the pixel
    try { const cv = document.createElement('canvas'); cv.width = cv.height = 1; const x = cv.getContext('2d', {willReadFrequently: true});
      x.clearRect(0, 0, 1, 1); x.fillStyle = '#010203'; x.fillStyle = s; if (x.fillStyle === '#010203') return null;
      x.fillRect(0, 0, 1, 1); const d = x.getImageData(0, 0, 1, 1).data; if (!d[3]) return [0, 0, 0, 0];
      return [d[0], d[1], d[2], d[3] / 255]; } catch (e) { return null; } };
  const over = (fg, bg) => [0, 1, 2].map(i => fg[i] * fg[3] + bg[i] * (1 - fg[3])).concat(1);
  const lum = c => { const l = c.slice(0, 3).map(v => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * l[0] + 0.7152 * l[1] + 0.0722 * l[2]; };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const pageBg = () => parse(getComputedStyle(document.documentElement).getPropertyValue('--rd-bg')) || [255, 255, 255, 1];
  const bgOf = el => { const layers = [];
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor);
      if (c && c[3] > 0) { layers.push(c); if (c[3] >= 1) break; } }
    let base = layers.length && layers[layers.length - 1][3] >= 1 ? layers.pop() : pageBg();
    for (let i = layers.length - 1; i >= 0; i--) base = over(layers[i], base);
    return base; };
  const hex = c => '#' + c.slice(0, 3).map(v => Math.round(v).toString(16).padStart(2, '0')).join('');
  const opac = el => { let o = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement) o *= +getComputedStyle(e).opacity; return o; };
  const pair = (fgStr, bg) => { const fg = parse(fgStr); if (!fg) return null; const f = over(fg, bg);
    return {c: +ratio(f, bg).toFixed(2), fg: hex(f), bg: hex(bg)}; };
  const textOf = (el, need) => { const cs = getComputedStyle(el); const bg = bgOf(el); const r = pair(cs.color, bg);
    if (!r) return null; const size = parseFloat(cs.fontSize), w = +cs.fontWeight;
    r.need = need || ((size >= 24 || (size >= 18.66 && w >= 700)) ? 3 : 4.5);
    r.t = (el.textContent || el.getAttribute('aria-label') || el.tagName).trim().slice(0, 28); return r; };
  const sweep = sel => { const root = document.querySelector(sel); if (!root) return null; const out = [];
    for (const el of root.querySelectorAll('*')) {
      if (!(el instanceof HTMLElement)) continue;
      if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
      const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
      const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || cs.display === 'none') continue;
      if (el.closest('.sr-only')) continue;
      if (opac(el) < 0.99 || el.closest('[disabled],[aria-disabled="true"]')) continue;
      const t = textOf(el); if (t) out.push(t); }
    return out; };
  const hitsAround = (el, d) => { const r = el.getBoundingClientRect(); const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    const pts = [[cx - d, cy], [cx + d, cy], [cx, cy - d], [cx, cy + d]];
    return pts.map(([x, y]) => { const h = document.elementFromPoint(x, y); return !!h && (h === el || el.contains(h)); }); };
  const vars = () => { const s = getComputedStyle(document.documentElement);
    return {gold: s.getPropertyValue('--ap-gold').trim(), hover: s.getPropertyValue('--rd-hover').trim(),
            band1: s.getPropertyValue('--ap-band-1').trim(), band2: s.getPropertyValue('--ap-band-2').trim()}; };
  // the search field's frame: ONE line — no outline, no outer shadow ring (an inset shadow merges with the border)
  const oneFrame = i => { const cs = getComputedStyle(i); const sh = cs.boxShadow || 'none';
    const outer = sh !== 'none' && sh.split(/,(?![^(]*\))/).some(x => { if (/inset/.test(x)) return false;
      const col = (x.match(/(rgba?|color|oklab|oklch)\([^)]*\)/) || [''])[0]; const c = col ? parse(col) : [0, 0, 0, 1];
      if (c && c[3] === 0) return false; const lens = (x.replace(col, '').match(/-?[\d.]+px/g) || []).map(parseFloat);
      return lens.some(v => v !== 0); });
    const ol = cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0;
    const f = i.closest('form').parentElement;
    return {focused: document.activeElement === i, outline: ol ? cs.outlineStyle + ' ' + cs.outlineWidth + ' offset ' + cs.outlineOffset : 'none',
      shadow: sh, outerRing: outer, border: cs.borderTopStyle + ' ' + cs.borderTopWidth, frameC: pair(cs.borderTopColor, bgOf(f)),
      one: !ol && !outer && cs.borderTopStyle === 'solid'}; };
  return {parse, over, ratio, bgOf, pair, textOf, sweep, hitsAround, vars, hex, pageBg, oneFrame};
})();
"""


def bad(items):
    return [x for x in (items or []) if x["c"] + 1e-9 < x["need"]]


def tap(pg, touch, x, y):
    if touch:
        pg.touchscreen.tap(x, y)
    else:
        pg.mouse.click(x, y)


def bars(pg, touch):
    for _ in range(3):
        if pg.locator(".reader-btn[data-reader-action=contents]").is_visible():
            return True
        tap(pg, touch, 200, 600)
        pg.wait_for_timeout(700)
    return pg.locator(".reader-btn[data-reader-action=contents]").is_visible()


def open_menu(pg, touch):
    bars(pg, touch)
    btn = pg.locator(".reader-btn[data-reader-action=contents]")
    btn.tap() if touch else btn.click()
    pg.wait_for_selector(".mobile-menu[data-open] aside", timeout=8000)
    pg.wait_for_timeout(700)


def new_page(b, opts, theme, banner=False):
    c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce", **opts)
    init = f"localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('ap.readerTheme','{theme}');"
    init += "localStorage.setItem('ap.offlineSave', JSON.stringify({s:'seen'}));"
    if not banner:
        init += "localStorage.setItem('installDismissed','true');"
    c.add_init_script(init)
    c.add_init_script(LIB)
    return c, c.new_page()


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        touch = bool(opts.get("has_touch"))
        for theme in THEMES:
            tag = f"{theme}:"
            c, pg = new_page(b, opts, theme)
            pg.goto(f"{BASE}/ru-iast/{CHAPTER}/", wait_until="networkidle")
            pg.wait_for_timeout(900)
            v = pg.evaluate("__wc.vars()")
            want = "#e3a03c" if theme == "night" else "#965700"
            check(dev, f"{tag} one accent tone --ap-gold = {want} (variant B)", v["gold"].lower() == want, v)
            # the light highlight under a finger / an open button (--rd-hover) with the accent on it
            hv = pg.evaluate("(() => { const v = __wc.vars(); const g = __wc.parse(v.gold), h = __wc.parse(v.hover);"
                             " return g && h ? {c: +__wc.ratio(g, h).toFixed(2), gold: v.gold, hover: v.hover} : v; })()")
            check(dev, f"{tag} accent on the finger highlight ≥ 4.5", hv.get("c", 0) >= 4.5, hv)

            # top bar icons + «Вперёд ›» + status line
            bars(pg, touch)
            top = pg.evaluate("""() => [...document.querySelectorAll('.reader-bar-top .reader-btn svg')].filter(s => s.getBoundingClientRect().width)
                .map(s => { const r = __wc.pair(getComputedStyle(s).color, __wc.bgOf(s.closest('.reader-btn'))); r.need = 3; r.t = 'icon'; return r; })""")
            check(dev, f"{tag} top-bar icons ≥ 3:1", top and not bad(top), bad(top) or top[:4])
            fw = pg.evaluate("(() => { const e = document.querySelector('[data-reader-nav=forward]'); return e ? __wc.textOf(e, 4.5) : null; })()")
            check(dev, f"{tag} «Вперёд ›» ≥ 4.5", fw and not bad([fw]), fw)
            st = pg.evaluate("(() => { const e = document.querySelector('.reader-status'); return e ? __wc.textOf(e, 4.5) : null; })()")
            check(dev, f"{tag} status line (chapter · %) ≥ 4.5", st and not bad([st]), st)

            # «пословно / перевод» (closed)
            ch = pg.evaluate("""() => [...document.querySelectorAll('.verse-chip')].slice(0, 2).map(e => __wc.textOf(e, 4.5))""")
            check(dev, f"{tag} «пословно / перевод» buttons ≥ 4.5", ch and not bad(ch), bad(ch) or ch)

            # «Настроение Гурудева» window
            mood = pg.locator(".mood-toggle").first
            if mood.count():
                tg = pg.evaluate("__wc.textOf(document.querySelector('.mood-toggle'), 4.5)")
                pg.evaluate("document.querySelector('.mood-toggle').click()")
                pg.wait_for_timeout(900)
                ms = pg.evaluate("""() => { const d = document.querySelector('.mood-dialog-head'); if (!d) return null;
                    const box = d.parentElement; return [...box.querySelectorAll('.mood-label, .mood-num, .mood-close')]
                    .filter(e => e.getBoundingClientRect().width).map(e => __wc.textOf(e, e.classList.contains('mood-close') ? 3 : 4.5)); }""")
                check(dev, f"{tag} «Настроение Гурудева» button + window labels, numbers, ✕", ms is not None and not bad([tg] + ms), bad([tg] + (ms or [])) or ms)
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(600)
            c.close()

            # «Содержание»: every text, icon = word, search frame, results, ✕ tap area
            c, pg = new_page(b, opts, theme)
            pg.goto(f"{BASE}/ru-iast/{CHAPTER}/", wait_until="networkidle")
            pg.wait_for_timeout(900)
            open_menu(pg, touch)
            if touch:
                act = pg.evaluate("(document.activeElement && document.activeElement.matches('input.search-input'))")
                check(dev, f"{tag} a tap on «Содержание» does not focus the search field (no keyboard)", not act, act)
            sw = pg.evaluate("__wc.sweep('.mobile-menu[data-open] aside')")
            check(dev, f"{tag} «Содержание»: every text ≥ AA ({len(sw or [])} measured)", sw and not bad(sw), bad(sw)[:8])
            ic = pg.evaluate("""() => { const h = document.querySelector('.mobile-menu[data-open] aside h2'); const s = h.parentElement.querySelector('svg');
                const f = document.querySelector('.mobile-menu[data-open] form[role=search]'); const m = f.querySelector('svg'); const i = f.querySelector('input');
                const ab = __wc.bgOf(f.parentElement);
                const r = {title: getComputedStyle(h).color, book: getComputedStyle(s).stroke === 'none' ? null : getComputedStyle(s).color,
                  bookStroke: getComputedStyle(s).stroke, lens: getComputedStyle(m).color, lensStroke: getComputedStyle(m).stroke,
                  frame: getComputedStyle(i).borderTopColor};
                r.frameC = __wc.pair(r.frame, ab); r.lensC = __wc.pair(r.lens, __wc.bgOf(i)); r.bookC = __wc.pair(r.book || r.bookStroke, __wc.bgOf(h));
                try { r.ph = getComputedStyle(i, '::placeholder').color; r.phC = __wc.pair(r.ph, __wc.bgOf(i)); } catch (e) {}
                return r; }""")
            cx = pg.evaluate("""() => { const b = document.querySelector('.mobile-menu[data-open] aside button[aria-label]'); if (!b) return null;
                const s = b.querySelector('svg'); const st = getComputedStyle(s).stroke; const r = __wc.pair(st === 'none' ? getComputedStyle(s).color : st, __wc.bgOf(b)); r.need = 3; return r; }""")
            check(dev, f"{tag} ✕ of «Содержание» ≥ 3:1", cx and cx["c"] >= 3, cx)
            same = lambda a, b_: (a or "").replace(" ", "") == (b_ or "").replace(" ", "")
            check(dev, f"{tag} book icon = «Содержание» colour", same(ic["bookStroke"], ic["title"]) and ic["bookC"]["c"] >= 3, ic)
            check(dev, f"{tag} magnifier = search frame colour, frame ≥ 3:1", same(ic["lensStroke"], ic["frame"]) and ic["frameC"]["c"] >= 3 and ic["lensC"]["c"] >= 3, ic)
            if eng != "webkit":  # WebKit has no getComputedStyle(…, '::placeholder')
                check(dev, f"{tag} search placeholder ≥ 4.5 and = magnifier colour", ic.get("phC") and ic["phC"]["c"] >= 4.5 and same(ic["ph"], ic["lensStroke"]), ic)
            inp = pg.locator(".mobile-menu[data-open] input[type=search]")
            inp.fill("тилак")
            pg.wait_for_timeout(1800)
            of = pg.evaluate("__wc.oneFrame(document.querySelector('.mobile-menu[data-open] input[type=search]'))")
            check(dev, f"{tag} search field in focus: ONE frame line, ≥ 3:1", of["focused"] and of["one"] and of["frameC"]["c"] >= 3, of)
            pg.evaluate("document.activeElement && document.activeElement.blur()")
            pg.wait_for_timeout(300)
            of0 = pg.evaluate("__wc.oneFrame(document.querySelector('.mobile-menu[data-open] input[type=search]'))")
            check(dev, f"{tag} search field without focus: ONE frame line, ≥ 3:1", of0["one"] and of0["frameC"]["c"] >= 3, of0)
            sr = pg.evaluate("__wc.sweep('.mobile-menu[data-open] aside')")
            check(dev, f"{tag} search results: every text ≥ AA ({len(sr or [])} measured)", sr and not bad(sr), bad(sr)[:8])
            cl = pg.evaluate("""() => { const i = document.querySelector('.mobile-menu[data-open] input[type=search]'); const b = i.parentElement.querySelector('button.search-clear, button[aria-label]');
                if (!b) return null; const r = b.getBoundingClientRect(); return {w: r.width, h: r.height, hits: __wc.hitsAround(b, 21)}; }""")
            check(dev, f"{tag} ✕ in the search field: tap area 44×44", cl and all(cl["hits"]) and cl["w"] >= 44 - 0.5 and cl["h"] >= 44 - 0.5, cl)
            c.close()

            # keyboard (desktop): focus ring, focus into «Содержание», back on Escape
            if not touch:
                c, pg = new_page(b, opts, theme)
                pg.goto(f"{BASE}/ru-iast/{CHAPTER}/", wait_until="networkidle")
                pg.wait_for_timeout(900)
                pg.mouse.move(700, 450)
                got = False
                for _ in range(30):
                    pg.keyboard.press("Tab")
                    pg.wait_for_timeout(60)
                    if pg.evaluate("(document.activeElement||{}).getAttribute && document.activeElement.getAttribute('data-reader-action')") == "contents":
                        got = True
                        break
                pg.wait_for_timeout(300)
                ring = pg.evaluate("""() => { const e = document.activeElement; const cs = getComputedStyle(e);
                    const r = __wc.pair(cs.outlineColor, __wc.bgOf(e.parentElement)); r.style = cs.outlineStyle; r.width = cs.outlineWidth; return r; }""")
                check(dev, f"{tag} keyboard focus ring ≥ 3:1, solid", got and ring["c"] >= 3 and ring["style"] == "solid", ring)
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(900)
                fin = pg.evaluate("""() => { const a = document.activeElement; return {inMenu: !!a.closest('.mobile-menu[data-open]'),
                    search: a.matches('input.search-input'), tag: a.tagName, cls: (a.className || '').toString().slice(0, 60)}; }""")
                check(dev, f"{tag} Enter on «Содержание» → focus on the search field in the panel", fin["inMenu"] and fin["search"], fin)
                ir = pg.evaluate("""() => { const e = document.activeElement; if (!e || !e.matches('input.search-input')) return {one: false, frameC: {c: 0}, none: 'focus not on the search field'};
                    return __wc.oneFrame(e); }""")
                check(dev, f"{tag} keyboard focus on the search field: ONE frame line (no ring around it), ≥ 3:1", ir["one"] and ir["frameC"]["c"] >= 3, ir)
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(900)
                back = pg.evaluate("""() => { const a = document.activeElement; return {contents: a.getAttribute && a.getAttribute('data-reader-action') === 'contents', tag: a.tagName}; }""")
                check(dev, f"{tag} Escape → focus back on «Содержание»", back["contents"], back)
                c.close()

            # band «Установить» (phones): white text, button, ✕ + its tap area
            if touch and theme in ("white", "night"):
                c, pg = new_page(b, opts, theme, banner=True)
                pg.goto(f"{BASE}/ru-iast/", wait_until="networkidle")
                try:
                    pg.wait_for_selector(".install-banner", timeout=8000)
                except Exception:
                    pass
                pg.wait_for_timeout(600)
                bn = pg.evaluate("""() => { const e = document.querySelector('.install-banner'); if (!e) return null;
                    const stops = (getComputedStyle(e).backgroundImage.match(/rgba?\\([^)]+\\)/g) || []).map(__wc.parse);
                    const txt = e.querySelector('span'); const btn = e.querySelector('button'); const x = e.querySelectorAll('button')[1];
                    // the 90deg gradient's colour under each edge of the element (linear between the two stops)
                    const B = e.getBoundingClientRect(); const at = px => { const t = Math.min(1, Math.max(0, (px - B.left) / B.width));
                      return [0, 1, 2].map(i => stops[0][i] + (stops[stops.length - 1][i] - stops[0][i]) * t).concat(1); };
                    const edges = el => { const r = el.getBoundingClientRect(); return [r.left, r.right].map(at); };
                    const res = [0, 1].map(k => ({edge: k ? 'right' : 'left',
                      text: +__wc.ratio(__wc.parse(getComputedStyle(txt).color), edges(txt)[k]).toFixed(2),
                      button: +__wc.ratio(__wc.parse(getComputedStyle(btn).color), __wc.over(__wc.parse(getComputedStyle(btn).backgroundColor), edges(btn)[k])).toFixed(2),
                      x: +__wc.ratio(__wc.parse(getComputedStyle(x.querySelector('svg') || x).color), edges(x)[k]).toFixed(2)}));
                    return {gradient: stops.map(__wc.hex), stops: res, white: getComputedStyle(txt).color, hits: __wc.hitsAround(x, 21)}; }""")
                ok = bn and len(bn["stops"]) >= 2 and all(s["text"] >= 4.5 and s["button"] >= 4.5 and s["x"] >= 3 for s in bn["stops"]) \
                    and bn["white"].replace(" ", "") == "rgb(255,255,255)"
                check(dev, f"{tag} band «Установить»: white text ≥ 4.5, button ≥ 4.5, ✕ ≥ 3:1 on the whole gradient", ok, bn)
                check(dev, f"{tag} ✕ of the band: tap area 44×44", bn and all(bn["hits"]), bn and bn["hits"])
                # the install window's step numbers (same gradient tokens)
                pg.get_by_role("button", name="Установить").first.click()
                pg.wait_for_timeout(900)
                steps = pg.evaluate("""() => [...document.querySelectorAll('.bg-gradient-to-br')].filter(e => e.getBoundingClientRect().width).map(e => {
                    const st = (getComputedStyle(e).backgroundImage.match(/rgba?\\([^)]+\\)/g) || []).map(__wc.parse);
                    return st.map(s => +__wc.ratio(__wc.parse(getComputedStyle(e).color), s).toFixed(2)); })""")
                check(dev, f"{tag} install window step numbers ≥ 4.5", steps and all(min(s) >= 4.5 for s in steps if s), steps)
                c.close()

            # picture numbers 2.1–2.6 (the emblem): tap area wider than the drawn number (maket: +12 px stroke)
            if touch and theme == "white":
                c, pg = new_page(b, opts, theme)
                pg.goto(f"{BASE}/ru-iast/gaudiya-emblem/", wait_until="networkidle")
                pg.wait_for_timeout(1200)
                pg.evaluate("document.querySelector('.hs-figure').scrollIntoView({block:'start'})")
                pg.wait_for_timeout(700)
                hz = pg.evaluate("""() => [...document.querySelectorAll('.hs-figure .hs-hit')].filter(h => (h.getAttribute('aria-label') || '').startsWith('2.')).map(h => {
                    const e = h.querySelector('ellipse, circle'); const r = e.getBoundingClientRect(); const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
                    // how far out from the drawn shape a tap still lands on this item
                    let out = 0; for (let d = 0; d <= 30; d += 1) { const x = document.elementFromPoint(r.right + d, cy); if (x && h.contains(x)) out = d; else break; }
                    return {n: h.getAttribute('aria-label'), w: +(r.width + 2 * out).toFixed(1), h: +(r.height + 2 * out).toFixed(1), drawn: [+r.width.toFixed(1), +r.height.toFixed(1)]}; })""")
                check(dev, f"{tag} emblem 2.1–2.6: tap area ≥ 24 px each way", hz and len(hz) == 6 and all(z["w"] >= 24 and z["h"] >= 24 for z in hz), hz)
                c.close()
        b.close()

n_fail = results.count(False)
print(f"s81: {len(results) - n_fail}/{len(results)} PASS", flush=True)
sys.exit(1 if n_fail else 0)
