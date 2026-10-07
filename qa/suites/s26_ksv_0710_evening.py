"""Reader v7.8 — КСВ Satkirti 07.10.2026 вечер (20:49–21:51), «Правила интерфейса книг.md» §11.
  1  «Показать весь пословный перевод» / «Показать все переводы» only in the «Аа» panel (and they work)
  2  the language menu only in the «Аа» panel
  3  «Содержание» = fixed part (title, search, «Обложка») + scrolling list
  4  every contents row (cover, chapter, group heading, chapter with subsections, subsection) reacts to a
     tap at the far left AND the far right of its highlight strip (1st tap = highlight, §10)
  5  a row opened near the bottom (2nd tap): its rows come into view / the row goes up as far as it can
  6  tilak list: a tap on the place, the mantra or the gap between them marks the row — the place AND the
     mantra get the band — and lights exactly that spot (rows 1–12); «tat prakṣālana-toyaṁ tu / vāsudevāya
     mūrdhani» and «oṁ vāsudevāya namaḥ» light the crown (Tilak-13); the crown on the picture marks the mantra
  7  short mantras («oṁ … namaḥ», one line ≤ 6 words) have no «пословно» — every page, RU and EN
  8  search: the found word is marked in every result (all its occurrences), and after opening a result
     it is marked in the text (CSS highlight) and in view; the next tap only clears it
  9  parampara: the oval without the rhombi (design 1), WebP shown with the PNG as fallback
 v7.8.1 (Codex review of v7.8):
 10  the search mark goes on every step away — Back, Forward, a Link (keyboard, no tap), a pushState URL change —
     and the first tap on the new place is not eaten by it
 11  without the CSS Custom Highlight API the found word is wrapped in a visible mark, removed by the next tap
 12  parampara offline (service worker): the WebP portraits load; WebP failing → the PNG is shown
 13  the keyboard (Tab) reaches the «Аа» switches and the language menu; Space toggles a switch
 14  the second tap opens every contents row type (chapter, subsection, chapter with subsections, group, cover)
usage: python s26_ksv_0710_evening.py <base-url>   devices: QA_DEVICES"""
import json
import os
import sys
from urllib.parse import unquote

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
L = "ru-iast"
DEVICES = qa.devices(["pixel7", "iphone14", "ipad-portrait", "ipad-landscape", "desktop", "mac-safari"])
res = []

# pages with short mantras (lib/book.ts isShortMantra; qa.is_short_mantra)
SHORT_PAGES = ["daily-duties-brahma-muhurta", "offering-bhoga", "worship-sixteen-articles", "main-worship-sixteen-items",
               "arcana-sri-guru", "maha-abhiseka", "arcana-procedure"]
# JS mirror of isShortMantra
IS_SHORT = r"""(t) => { const s = (t || '').replace(/[⟦⟧]/g, '').trim().normalize('NFC'); if (!s || s.includes('\n')) return false;
  const w = s.split(/\s+/); const B = ['oṁ','aiṁ','klīṁ','śrīṁ','hrīṁ','rāṁ'].map(x => x.normalize('NFC'));
  return w.length >= 2 && w.length <= 6 && B.includes(w[0].toLowerCase()) && /(namaḥ|svāhā|phaṭ)[.!]?$/.test(s.normalize('NFC')); }"""


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else info}", flush=True)


def run(p, dev, eng, o):
    b = getattr(p, eng).launch()
    c = b.new_context(locale="ru-RU", service_workers="block", **o)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    pg = c.new_page()
    touch = o.get("has_touch", False)
    vw = o["viewport"]
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    def tapxy(x, y, ms=350):
        (pg.touchscreen.tap if touch else pg.mouse.click)(x, y)
        pg.wait_for_timeout(ms)

    def tap(sel_or_loc, ms=350):
        loc = pg.locator(sel_or_loc).first if isinstance(sel_or_loc, str) else sel_or_loc
        loc.scroll_into_view_if_needed()
        loc.tap() if touch else loc.click()
        pg.wait_for_timeout(ms)

    def goto(path, ms=700):
        pg.goto(f"{BASE}/{L}/{path}", wait_until="networkidle")
        pg.wait_for_timeout(ms)

    def bars():
        if pg.locator(".reader-chrome[data-shown]").count() == 0:
            tapxy(vw["width"] - 6, vw["height"] / 2, 500)

    def contents():
        for _ in range(3):
            if pg.locator(".mobile-menu").count():
                return
            bars()
            try:
                tap("[data-reader-action=contents]", 800)
            except Exception:
                pass

    def close_menu():
        if pg.locator(".mobile-menu").count():
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(500)

    lit = lambda: pg.evaluate("() => [...document.querySelectorAll('.mobile-menu nav [data-toc-lit]')].map(e => e.getAttribute('data-toc-row'))")

    # ---------- 1 + 2: switches and language only in «Аа» ----------
    goto("kartika-bhajans/")
    contents()
    m = pg.evaluate("""() => { const a = document.querySelector('.mobile-menu aside');
        return {sw: a.querySelectorAll('[role=switch]').length, sel: a.querySelectorAll('select').length,
                txt: /пословный перевод|все переводы/i.test(a.innerText)}; }""")
    chk(dev, "1/2 «Содержание»: no «Показать…» switches, no language menu", m["sw"] == 0 and m["sel"] == 0 and not m["txt"], str(m))
    close_menu()
    bars()
    tap("[data-reader-action=aa]", 500)
    a = pg.evaluate("""() => { const p = document.querySelector('.reader-panel'); if (!p) return null;
        return {wbw: !!p.querySelector('[data-reader-switch=wbw]'), tr: !!p.querySelector('[data-reader-switch=tr]'),
                sel: p.querySelectorAll('select').length, txt: p.innerText}; }""")
    chk(dev, "1/2 «Аа»: both switches and the language menu", a and a["wbw"] and a["tr"] and a["sel"] == 1
        and "пословный" in a["txt"] and "переводы" in a["txt"], str(a)[:200])
    if a and a["wbw"]:
        n0 = pg.evaluate("document.querySelectorAll('.app-main .verse-wbw:not([hidden])').length")
        tap(".reader-panel [data-reader-switch=wbw]", 500)
        n1 = pg.evaluate("document.querySelectorAll('.app-main .verse-wbw:not([hidden])').length")
        on = pg.get_attribute(".reader-panel [data-reader-switch=wbw]", "aria-checked")
        tap(".reader-panel [data-reader-switch=wbw]", 500)
        n2 = pg.evaluate("document.querySelectorAll('.app-main .verse-wbw:not([hidden])').length")
        chk(dev, "1 «Аа» switch «весь пословный перевод» opens / closes every word-by-word panel", n0 == 0 and n1 >= 20 and n2 == 0 and on == "true", (n0, n1, n2, on))
        tap(".reader-panel [data-reader-switch=tr]", 500)
        t1 = pg.evaluate("document.querySelectorAll('.app-main .verse-panel:not(.verse-wbw):not([hidden])').length")
        tap(".reader-panel [data-reader-switch=tr]", 500)
        t2 = pg.evaluate("document.querySelectorAll('.app-main .verse-panel:not(.verse-wbw):not([hidden])').length")
        chk(dev, "1 «Аа» switch «все переводы» opens / closes every translation", t1 >= 20 and t2 == 0, (t1, t2))
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)

    # ---------- 3: fixed part ----------
    contents()
    f = pg.evaluate("""() => { const nav = document.querySelector('.mobile-menu nav'); const sc = nav.querySelector('.toc-scroll');
        const cov = nav.querySelector('[data-toc-cover]'); const r0 = cov.getBoundingClientRect().top;
        const fits = sc.scrollHeight <= sc.clientHeight + 2; sc.scrollTop = sc.scrollHeight; const r1 = cov.getBoundingClientRect().top;
        const first = sc.querySelector('[data-toc-row]');
        return {fits, inScroll: sc.contains(cov), moved: Math.abs(r1 - r0), scrolled: sc.scrollTop,
                firstRow: first && first.textContent.trim(), coverTop: r1, scTop: sc.getBoundingClientRect().top}; }""")
    chk(dev, "3 «Обложка» in the fixed part (does not scroll), list scrolls under it from «Гуру-парампара»",
        not f["inScroll"] and f["moved"] < 1 and (f["scrolled"] > 50 or f["fits"]) and f["firstRow"] == "Гуру-парампара" and f["coverTop"] < f["scTop"], str(f))
    pg.evaluate("document.querySelector('.mobile-menu .toc-scroll').scrollTop = 0")

    # ---------- 4: full-width rows ----------
    tap(".mobile-menu [data-toc-cover]")          # base view
    # open «Введение» and part I, and chapter 1's list (to have every row type)
    for sel in (".mobile-menu [data-toc-group=introduction]", ".mobile-menu [data-toc-group=temple-worship]",
                ".mobile-menu button[data-toc-chapter=daily-duties-brahma-muhurta]"):
        for _ in range(3):
            if pg.locator(sel).count() and pg.get_attribute(sel, "aria-expanded") == "true":
                break
            if pg.locator(sel).count():
                tap(sel)
    rows = pg.evaluate("""() => [...document.querySelectorAll('.mobile-menu nav [data-toc-row]')].map(e => e.getAttribute('data-toc-row'))""")
    kinds = {}
    for r in rows:
        k = r.split(":")[0]
        kinds.setdefault(k, []).append(r)
    sample = []
    for k, rs in kinds.items():
        sample += rs if k == "grp" else rs[:2] + rs[-1:]
    # «Обложка» last: its first tap resets the contents to the base view (everything closed)
    sample = [r for r in sample if r != "cover"] + (["cover"] if "cover" in sample else [])
    bad = []
    for r in sample:
        for side in ("right", "left"):
            q = pg.evaluate("""([r, side]) => { const el = [...document.querySelectorAll('.mobile-menu nav [data-toc-row]')].find(e => e.getAttribute('data-toc-row') === r);
                if (!el) return null; el.scrollIntoView({block: 'center'}); const b = el.getBoundingClientRect();
                const aside = document.querySelector('.mobile-menu aside').getBoundingClientRect();
                return {x: side === 'right' ? Math.min(b.right, aside.right) - 6 : b.left + 4, y: b.top + b.height / 2, l: b.left, w: b.width, aw: aside.width}; }""", [r, side])
            if not q:
                bad.append((r, "missing"))
                continue
            # first move the highlight elsewhere (the row must not be the armed one)
            # (a plain chapter link: its first tap only highlights — «Обложка» would collapse the lists)
            cur = lit()
            other = next(x for x in ("sec:parampara", "sec:mangalacarana", "grp:introduction") if x != r and x not in cur)
            pg.evaluate("""(o) => { const el = [...document.querySelectorAll('.mobile-menu nav [data-toc-row]')].find(e => e.getAttribute('data-toc-row') === o); el && el.click(); }""", other)
            pg.wait_for_timeout(200)
            q = pg.evaluate("""([r, side]) => { const el = [...document.querySelectorAll('.mobile-menu nav [data-toc-row]')].find(e => e.getAttribute('data-toc-row') === r);
                if (!el) return null; el.scrollIntoView({block: 'center'}); const b = el.getBoundingClientRect(); const aside = document.querySelector('.mobile-menu aside').getBoundingClientRect();
                return {x: side === 'right' ? Math.min(b.right, aside.right) - 6 : b.left + 4, y: b.top + b.height / 2, w: b.width, aw: aside.width}; }""", [r, side])
            if not q:
                bad.append((r, side, "row gone"))
                continue
            tapxy(q["x"], q["y"], 300)
            got = lit()
            if got != [r] or q["w"] < q["aw"] * 0.6 and not r.startswith("sub:"):
                bad.append((r, side, got, round(q["w"]), round(q["aw"])))
            if not pg.locator(".mobile-menu").count():
                contents()
    chk(dev, f"4 every row type reacts over its full strip, left and right edge ({len(sample)} rows: {', '.join(sorted(kinds))})",
        not bad and {"cover", "grp", "sec", "sub"} <= set(kinds), str(bad[:4]))
    # (no Escape before the next goto: its history.go(-n) would land after the new page loaded)

    # ---------- 5: auto-scroll on opening near the bottom ----------
    goto("introduction/", 300)     # (a goto to the URL shown is a reload: it keeps that menu step)
    goto("kartika-bhajans/")
    contents()
    tap(".mobile-menu [data-toc-cover]")
    REVEAL = """(sel) => { const sc = document.querySelector('.mobile-menu .toc-scroll'); const row = document.querySelector(sel);
        const li = row.closest('li'); const n = sc.getBoundingClientRect(), g = li.getBoundingClientRect(), r = row.getBoundingClientRect();
        return {allIn: g.bottom <= n.bottom + 1, rowTop: Math.round(r.top - n.top), atEnd: sc.scrollTop + sc.clientHeight >= sc.scrollHeight - 2,
                kids: li.querySelectorAll('ul [data-toc-row]').length}; }"""
    for name, sel in (("part IV", ".mobile-menu [data-toc-group=festivals-vows]"),
                      ("chapter 16", ".mobile-menu button[data-toc-chapter=kartika-bhajans]")):
        loc = pg.locator(sel)
        if not loc.count():
            chk(dev, f"5 {name}: row present", False, (sel, pg.url, pg.locator(".mobile-menu").count(),
                pg.evaluate("() => [...document.querySelectorAll('.mobile-menu [data-toc-row]')].map(e => e.getAttribute('data-toc-row')).join(' ')")))
            continue
        if loc.get_attribute("aria-expanded") == "true":     # close it first (two taps)
            tap(loc); tap(loc)
        # bring the row to the bottom of the list's view, then open it
        pg.evaluate("""(sel) => { const sc = document.querySelector('.mobile-menu .toc-scroll'); const row = document.querySelector(sel);
            sc.scrollTop += row.getBoundingClientRect().bottom - sc.getBoundingClientRect().bottom + 4; }""", sel)
        pg.wait_for_timeout(200)
        bb = loc.bounding_box()
        tapxy(bb["x"] + 30, bb["y"] + bb["height"] / 2, 300)
        tapxy(bb["x"] + 30, bb["y"] + bb["height"] / 2, 600)
        st = pg.evaluate(REVEAL, sel)
        chk(dev, f"5 {name} opened at the bottom → its rows in view (or the row at the top / list at its end)",
            st["kids"] > 0 and (st["allIn"] or st["rowTop"] <= 2) and st["rowTop"] >= -1, str(st))

    # ---------- 6: tilak rows + crown ----------
    # (no #anchor: the anchor keeper would pull the page back to the heading for 4 s after load)
    goto("daily-duties-brahma-muhurta/", 1500)
    STATE = """() => { const rows = [...document.querySelectorAll('.hs-row')];
        const act = rows.filter(r => r.hasAttribute('data-active')).map(r => r.getAttribute('data-hs-nums'));
        const masks = [...document.querySelectorAll('.hs-figure mask image')].map(x => x.getAttribute('href').split('/').pop());
        return {act, masks, bars: document.documentElement.hasAttribute('data-reader-bars')}; }"""
    BAND = """(n) => { const r = document.querySelector('.hs-row[data-hs-nums="' + n + '"]:not(span)'); if (!r) return null;
        const cells = [...r.children]; const place = cells[1], mantra = cells[2].querySelector('.hs-text');
        const bg = (e) => e ? getComputedStyle(e).backgroundColor : null;
        return {place: bg(place), mantra: bg(mantra), num: bg(cells[0])}; }"""
    POINTS = """(n) => { const r = document.querySelector('.hs-row[data-hs-nums="' + n + '"]:not(span)'); r.scrollIntoView({block: 'center'});
        const cells = [...r.children]; const lab = cells[1], man = cells[2].querySelector('.hs-text');
        const range = document.createRange(); range.selectNodeContents(lab); const lr = range.getClientRects(); const last = lr[lr.length - 1];
        const mr = man.getClientRects()[0];
        return {label: {x: last.left + Math.min(10, last.width / 2), y: last.top + last.height / 2},
                mantra: {x: mr.left + mr.width / 2, y: mr.top + mr.height / 2},
                gap: {x: (last.right + mr.left) / 2, y: mr.top + mr.height / 2, w: mr.left - last.right}}; }"""
    bad = []
    banded = 0
    for n in range(1, 13):
        for where in ("label", "mantra", "gap"):
            pts = pg.evaluate(POINTS, str(n))
            pg.wait_for_timeout(150)
            pts = pg.evaluate(POINTS, str(n))
            if where == "gap" and pts["gap"]["w"] < 8:
                bad.append((n, "no gap between place and mantra", pts["gap"]["w"]))
                continue
            p_ = pts[where]
            tapxy(p_["x"], p_["y"], 450)
            st = pg.evaluate(STATE)
            band = pg.evaluate(BAND, str(n))
            ok_band = band and all(v and v not in ("rgba(0, 0, 0, 0)", "transparent") for v in band.values())
            if ok_band:
                banded += 1
            if st["act"] != [str(n)] or st["masks"] != [f"Tilak-{n:02d}.png"] or st["bars"] or not ok_band:
                bad.append((n, where, st, band))
            tapxy(p_["x"], p_["y"], 350)           # the same row again: off
            if pg.evaluate(STATE)["act"]:
                bad.append((n, where, "2nd tap did not clear"))
                pg.keyboard.press("Escape")
    chk(dev, "6 tilak rows 1–12: place / mantra / gap → this row (place AND mantra banded) + exactly its spot", not bad and banded == 36, str(bad[:3]))
    # right of the mantra: page (UI §1)
    q = pg.evaluate("""() => { const r = document.querySelector('.hs-row[data-hs-nums="1"]:not(span)'); r.scrollIntoView({block: 'center'});
        const m = r.children[2].querySelector('.hs-text').getClientRects()[0]; const rr = r.getBoundingClientRect();
        return {x: Math.min(m.right + 40, rr.right - 4), y: m.top + m.height / 2, room: rr.right - m.right}; }""")
    if q["room"] > 30:
        tapxy(q["x"], q["y"], 400)
        chk(dev, "6 right of the mantra stays page (no row marked)", pg.evaluate(STATE)["act"] == [], str(pg.evaluate(STATE)))
        if pg.evaluate(STATE)["bars"]:
            tapxy(q["x"], q["y"], 400)
    # crown: the verse lines and the inline mantra
    crown = []
    for label, js in (("verse «tat prakṣālana-toyaṁ tu»", "span.hs-row[data-hs-nums='13'] .hs-text"),
                      ("verse «vāsudevāya mūrdhani»", "span.hs-row[data-hs-nums='13'] .hs-text:last-of-type"),
                      ("«oṁ vāsudevāya namaḥ»", "p span.hs-row[data-hs-nums='13'] .hs-text")):
        el = pg.locator(f".app-main {js}")
        txt = el.first.inner_text() if el.count() else ""
        if not el.count():
            crown.append((label, "missing"))
            continue
        tap(el.first, 500)
        st = pg.evaluate(STATE)
        bg = el.first.evaluate("e => getComputedStyle(e).backgroundColor")
        if st["masks"] != ["Tilak-13.png"] or st["act"] != ["13"] or bg in ("rgba(0, 0, 0, 0)", "transparent"):
            crown.append((label, txt, st, bg))
        tap(el.first, 350)
    chk(dev, "6 crown: «tat prakṣālana-toyaṁ tu / vāsudevāya mūrdhani» and «oṁ vāsudevāya namaḥ» → marked + the crown (Tilak-13)", not crown, str(crown[:3]))
    # the crown on the picture → the mantra «oṁ vāsudevāya namaḥ» marked (the instruction under the picture)
    pg.evaluate("() => document.querySelector('.hs-figure').scrollIntoView({block: 'center'})")
    pg.wait_for_timeout(400)
    pt = pg.evaluate("""() => { const g = [...document.querySelectorAll('.hs-figure .hs-hit')].find(x => x.getAttribute('aria-label') === '13');
        const r = g.querySelector('ellipse').getBoundingClientRect(); return {x: r.left + r.width / 2, y: r.top + r.height / 2}; }""")
    tapxy(pt["x"], pt["y"], 1200)
    st = pg.evaluate("""() => { const a = [...document.querySelectorAll('.hs-row[data-active]')];
        return {n: a.length, txt: a.map(r => r.textContent.trim()), inView: a.every(r => { const b = r.getBoundingClientRect(); return b.top >= 0 && b.bottom <= innerHeight; }),
                masks: [...document.querySelectorAll('.hs-figure mask image')].map(x => x.getAttribute('href').split('/').pop())}; }""")
    chk(dev, "6 crown on the picture → «oṁ vāsudevāya namaḥ» marked, in view", st["n"] == 1 and "vāsudevāya namaḥ" in st["txt"][0]
        and st["inView"] and "Tilak-13.png" in st["masks"], str(st))

    # ---------- 7: short mantras without «пословно» (RU and EN) ----------
    if dev in ("pixel7", "iphone14", "desktop"):
        bad = []
        n_short = n_long = 0
        for lang in ("ru-iast", "en"):
            for sid in SHORT_PAGES:
                pg.goto(f"{BASE}/{lang}/{sid}/", wait_until="domcontentloaded")
                pg.wait_for_timeout(300)
                r = pg.evaluate("""(isShort) => { isShort = eval(isShort); const out = {bad: [], short: 0, long: 0};
                    for (const chip of document.querySelectorAll('.app-main .verse-chip')) {
                      const panel = document.getElementById(chip.getAttribute('aria-controls'));
                      if (!panel || !panel.classList.contains('verse-wbw')) continue;
                      let text;
                      const mc = chip.closest('.mantra-chips');
                      if (mc) text = [...mc.parentElement.childNodes].filter(n => n !== mc && !(n.classList && n.classList.contains('verse-panel'))).map(n => n.textContent).join('');
                      else { const v = chip.closest('.verse-chips').parentElement; const sk = v && v.querySelector('.sanskrit'); text = sk ? sk.innerText : ''; }
                      if (isShort(text)) out.bad.push(text.trim().slice(0, 40)); else out.long++;
                    }
                    // short mantras shown (verses and table mantras)
                    for (const e of document.querySelectorAll('.app-main .sanskrit, .app-main .sa-inline')) if (isShort(e.innerText)) out.short++;
                    return out; }""", IS_SHORT)
                n_short += r["short"]
                n_long += r["long"]
                bad += [f"{lang}/{sid}: {t}" for t in r["bad"]]
        chk(dev, f"7 short mantras have no «пословно» (RU+EN, {len(SHORT_PAGES)} chapters; {n_short} short shown, {n_long} other «пословно» kept)",
            not bad and n_short >= 60 and n_long >= 20, str(bad[:4]))

    # ---------- 8: search marks ----------
    goto("")
    bars()
    tap("[data-reader-action=search]", 1200)
    pg.keyboard.type("Jayati")
    try:
        pg.wait_for_function("() => document.querySelectorAll('.mobile-menu [data-result]').length > 0", timeout=15000)
    except Exception:
        pass
    pg.wait_for_timeout(400)
    r = pg.evaluate("""() => { const rs = [...document.querySelectorAll('.mobile-menu [data-result]')];
        const per = rs.map(a => { const t = a.innerText.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '');
            const occ = (t.match(/jayati/g) || []).length; const marks = [...a.querySelectorAll('mark.search-mark')];
            return {occ, marks: marks.length, ok: marks.every(m => m.textContent.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '') === 'jayati'),
                    bg: marks[0] ? getComputedStyle(marks[0]).backgroundColor : null}; });
        return {n: rs.length, per}; }""")
    okm = r["n"] > 0 and all(x["marks"] == x["occ"] and x["occ"] > 0 and x["ok"] for x in r["per"])
    bg = r["per"][0]["bg"] if r["per"] else None
    alpha = float(bg.split(",")[3].strip(" )")) if bg and bg.count(",") == 3 else 1.0
    chk(dev, f"8 results: every occurrence of «Jayati» marked ({r['n']} results), clearly visible band", okm and bg and alpha >= 0.4, str(r)[:300])
    tap(".mobile-menu [data-result]", 300)
    try:
        pg.wait_for_function("() => document.documentElement.hasAttribute('data-search-hl')", timeout=10000)
    except Exception:
        pass
    pg.wait_for_timeout(800)
    h = pg.evaluate("""() => { const hl = window.CSS && CSS.highlights && CSS.highlights.get('search-hit');
        if (!hl) return {on: document.documentElement.hasAttribute('data-search-hl'), api: !!(window.CSS && CSS.highlights)};
        const r = [...hl][0]; const b = r.getBoundingClientRect();
        return {on: document.documentElement.hasAttribute('data-search-hl'), api: true, text: r.toString(), inView: b.top >= 0 && b.bottom <= innerHeight && b.height > 0}; }""")
    chk(dev, "8 opened result: «jayati» marked in the text, in view", h.get("on") and h.get("api") and (h.get("text") or "").lower() == "jayati" and h.get("inView"), str(h))
    tapxy(vw["width"] - 6, vw["height"] / 2, 500)
    after = pg.evaluate("() => ({on: document.documentElement.hasAttribute('data-search-hl'), bars: document.documentElement.hasAttribute('data-reader-bars')})")
    chk(dev, "8 next tap only clears the mark (menu stays hidden)", not after["on"] and not after["bars"], str(after))

    # ---------- 9: parampara oval without rhombi, WebP ----------
    goto("parampara/", 1200)
    pp = pg.evaluate("""() => [...document.querySelectorAll('.portrait-page img')].map(i => ({src: i.currentSrc.split('/').pop(), ok: i.complete && i.naturalWidth > 0,
        pic: !!i.closest('picture.portrait-picture')}))""")
    chk(dev, "9 parampara: 9 portraits shown from WebP (PNG fallback in <picture>)",
        len(pp) == 9 and all(x["ok"] and x["pic"] and x["src"].endswith(".webp") for x in pp), str(pp[:3]))
    tap_ = pg.evaluate("() => { const i = document.querySelector('.portrait-page img'); i.scrollIntoView({block: 'center'}); const b = i.getBoundingClientRect(); return {x: b.left + b.width / 2, y: b.top + b.height / 2}; }")
    pg.wait_for_timeout(500)         # a tap right after a scroll only stops the page (ReaderChrome)
    b0 = pg.evaluate("document.documentElement.hasAttribute('data-reader-bars')")
    tapxy(tap_["x"], tap_["y"], 500)
    b1 = pg.evaluate("document.documentElement.hasAttribute('data-reader-bars')")
    chk(dev, "9 a tap on the portrait still toggles the menu (§10)", b0 != b1, (b0, b1))

    chk(dev, "no page errors", not errs, str(errs[:3]))
    b.close()


HL_STATE = """() => ({hl: document.documentElement.hasAttribute('data-search-hl'),
    own: document.documentElement.hasAttribute('data-search-hl-own'),
    fb: document.querySelectorAll('.search-hit-fb').length,
    api: !!(window.CSS && CSS.highlights && CSS.highlights.get && CSS.highlights.get('search-hit')),
    bars: document.documentElement.hasAttribute('data-reader-bars')})"""
NO_HL_API = """try { Object.defineProperty(window.CSS, 'highlights', {value: undefined, configurable: true}); } catch (e) {}
try { delete window.Highlight; } catch (e) {} try { window.Highlight = undefined; } catch (e) {}"""
PORTRAITS = """() => [...document.querySelectorAll('.portrait-page img')].map(i => ({src: (i.currentSrc || i.src).split('/').pop(),
    ok: i.complete && i.naturalWidth > 0}))"""


def run_v781(p, dev, eng, o):
    """Reader v7.8.1 (Codex review of v7.8): search mark cleanup on every kind of step away + fallback without
    the Highlight API, offline WebP portraits, PNG fallback when WebP fails, keyboard into «Аа», second tap of
    every contents row type."""
    touch = o.get("has_touch", False)
    vw = o["viewport"]
    b = getattr(p, eng).launch()

    def ctx(init=None, sw="block"):
        c = b.new_context(locale="ru-RU", service_workers=sw, **o)
        c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
        if init:
            c.add_init_script(init)
        return c

    def helpers(pg):
        def tapxy(x, y, ms=350):
            (pg.touchscreen.tap if touch else pg.mouse.click)(x, y)
            pg.wait_for_timeout(ms)

        def tap(sel, ms=350):
            loc = pg.locator(sel).first if isinstance(sel, str) else sel
            loc.scroll_into_view_if_needed()
            loc.tap() if touch else loc.click()
            pg.wait_for_timeout(ms)

        def bars():
            if pg.locator(".reader-chrome[data-shown]").count() == 0:
                tapxy(vw["width"] - 6, vw["height"] / 2, 500)
        return tapxy, tap, bars

    def open_result(pg, tap, bars, q="Jayati"):
        bars()
        tap("[data-reader-action=search]", 1200)
        pg.keyboard.type(q)
        pg.wait_for_function("() => document.querySelectorAll('.mobile-menu [data-result]').length > 0", timeout=15000)
        pg.wait_for_timeout(400)
        tap(".mobile-menu [data-result]", 300)
        try:
            pg.wait_for_function("() => document.documentElement.hasAttribute('data-search-hl')", timeout=10000)
        except Exception:
            pass
        pg.wait_for_timeout(800)

    def first_tap_toggles_bars(pg, tapxy):
        pg.wait_for_timeout(600)
        b0 = pg.evaluate("document.documentElement.hasAttribute('data-reader-bars')")
        tapxy(vw["width"] - 6, vw["height"] / 2, 500)
        b1 = pg.evaluate("document.documentElement.hasAttribute('data-reader-bars')")
        return b0 != b1, (b0, b1)

    def clean(s):
        return not s["hl"] and not s["own"] and s["fb"] == 0 and not s["api"]

    # ---------- 10: search mark cleared by Back, Forward and a forward step (Link) ----------
    if dev in ("pixel7", "iphone14", "desktop", "mac-safari"):
        c = ctx()
        pg = c.new_page()
        tapxy, tap, bars = helpers(pg)
        pg.goto(f"{BASE}/{L}/", wait_until="networkidle")
        pg.wait_for_timeout(600)
        open_result(pg, tap, bars)
        on = pg.evaluate(HL_STATE)
        res_url = pg.url
        chk(dev, "10 (setup) result opened with the word marked", on["hl"], str(on))
        # forward step through a Link without a pointer (keyboard Enter on «След. глава ›»)
        has_next = pg.locator(".app-main .chapter-next-link").count() > 0
        if has_next:
            pg.locator(".app-main .chapter-next-link").first.focus()
            pg.keyboard.press("Enter")
            try:
                pg.wait_for_url(lambda u: u.split("#")[0] != res_url.split("#")[0], timeout=8000)
            except Exception:
                pass
            pg.wait_for_timeout(900)
            st = pg.evaluate(HL_STATE)
            chk(dev, "10 Link to the next chapter (keyboard, no tap) → mark gone on the new page", pg.url != res_url and clean(st), (pg.url[-40:], st))
            ok, info = first_tap_toggles_bars(pg, tapxy)
            chk(dev, "10 after the Link: the first tap on the new page is not eaten (menu toggles)", ok, info)
        else:
            chk(dev, "10 result page has «След. глава ›»", False, pg.url)
        # router.push-like step: a pushState to another chapter's URL from the marked page
        pg.goto(f"{BASE}/{L}/", wait_until="networkidle")
        pg.wait_for_timeout(500)
        open_result(pg, tap, bars)
        if pg.evaluate(HL_STATE)["hl"]:
            pg.evaluate("() => { history.pushState(history.state, '', location.pathname + '#qa-v781-elsewhere'); }")
            pg.wait_for_timeout(400)
            st = pg.evaluate(HL_STATE)
            chk(dev, "10 URL change by pushState (hash to elsewhere) → mark and scroll ownership gone", clean(st), str(st))
            pg.go_back()
            pg.wait_for_timeout(500)
        # Back: mark gone; the first tap there is not eaten
        pg.goto(f"{BASE}/{L}/kartika-bhajans/", wait_until="networkidle")
        pg.wait_for_timeout(500)
        open_result(pg, tap, bars)
        on = pg.evaluate(HL_STATE)["hl"]
        pg.go_back()
        pg.wait_for_timeout(1200)
        st = pg.evaluate(HL_STATE)
        chk(dev, "10 Back from the marked result → no mark", on and clean(st), (on, st))
        # step back until the page (out of the menu), then Forward to the result page
        for _ in range(3):
            if not pg.locator(".mobile-menu").count():
                break
            pg.go_back()
            pg.wait_for_timeout(700)
        pg.go_forward()
        pg.wait_for_timeout(1200)
        st = pg.evaluate(HL_STATE)
        chk(dev, "10 Forward → no stale mark", clean(st), str(st))
        if not pg.locator(".mobile-menu").count():
            ok, info = first_tap_toggles_bars(pg, tapxy)
            chk(dev, "10 after Back / Forward: the first tap is not eaten", ok, info)
        c.close()

    # ---------- 11: no CSS Custom Highlight API → <mark> fallback ----------
    if dev in ("pixel7", "desktop", "mac-safari"):
        c = ctx(NO_HL_API)
        pg = c.new_page()
        tapxy, tap, bars = helpers(pg)
        pg.goto(f"{BASE}/{L}/", wait_until="networkidle")
        pg.wait_for_timeout(600)
        api = pg.evaluate("() => !!(window.CSS && CSS.highlights) || typeof window.Highlight === 'function'")
        open_result(pg, tap, bars)
        fb = pg.evaluate("""() => { const m = [...document.querySelectorAll('.app-main .search-hit-fb')];
            const t = m.map(x => x.textContent).join('').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '');
            const r = m[0] ? m[0].getBoundingClientRect() : null;
            return {n: m.length, t, hl: document.documentElement.hasAttribute('data-search-hl'),
                    inView: !!r && r.top >= 0 && r.bottom <= innerHeight && r.height > 0,
                    bg: m[0] ? getComputedStyle(m[0]).backgroundColor : null}; }""")
        chk(dev, "11 no Highlight API: the found word wrapped in a visible mark, in view",
            not api and fb["n"] > 0 and fb["t"] == "jayati" and fb["hl"] and fb["inView"]
            and fb["bg"] not in (None, "rgba(0, 0, 0, 0)", "transparent"), (api, fb))
        txt0 = pg.evaluate("() => document.querySelector('.app-main article').textContent")
        tapxy(vw["width"] - 6, vw["height"] / 2, 500)
        st = pg.evaluate(HL_STATE)
        txt1 = pg.evaluate("() => document.querySelector('.app-main article').textContent")
        chk(dev, "11 fallback: the next tap removes the mark, text unchanged, menu stays hidden",
            fb["n"] > 0 and st["fb"] == 0 and not st["hl"] and not st["bars"] and txt0 == txt1, str(st))
        c.close()

    # ---------- 12: parampara WebP offline (SW) and PNG fallback when WebP fails ----------
    if dev in ("pixel7", "desktop"):
        c = ctx(sw="allow")
        pg = c.new_page()
        pg.goto(f"{BASE}/{L}/", wait_until="load")
        try:
            pg.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller", timeout=90000)
            cached = pg.evaluate("""async () => { const want = [...Array(9).keys()]; let n = 0;
                for (const k of await caches.keys()) { const c = await caches.open(k);
                  for (const r of await c.keys()) if (/\\/images\\/.*\\.webp$/.test(r.url)) n++; } return n; }""")
            c.set_offline(True)
            pg.goto(f"{BASE}/{L}/parampara/", wait_until="load", timeout=30000)
            pg.wait_for_timeout(1500)
            pp = pg.evaluate(PORTRAITS)
            chk(dev, "12 offline (SW): the 9 parampara portraits load from WebP",
                len(pp) == 9 and all(x["ok"] and x["src"].endswith(".webp") for x in pp), (cached, pp[:3]))
        except Exception as e:
            chk(dev, "12 offline (SW): the 9 parampara portraits load from WebP", False, repr(e)[:200])
        c.close()
        c = ctx()
        c.route("**/*.webp", lambda r: r.abort())
        pg = c.new_page()
        pg.goto(f"{BASE}/{L}/parampara/", wait_until="load")
        pg.wait_for_timeout(2000)
        pp = pg.evaluate(PORTRAITS)
        chk(dev, "12 WebP fails to load → the PNG is shown (9 portraits, naturalWidth > 0)",
            len(pp) == 9 and all(x["ok"] and x["src"].endswith(".png") for x in pp), str(pp[:3]))
        c.close()

    # ---------- 13: keyboard reaches the «Аа» controls ----------
    if dev == "desktop":
        c = ctx()
        pg = c.new_page()
        tapxy, tap, bars = helpers(pg)
        pg.goto(f"{BASE}/{L}/kartika-bhajans/", wait_until="networkidle")
        pg.wait_for_timeout(600)
        bars()
        tap("[data-reader-action=aa]", 600)
        seen = set()
        for _ in range(60):
            pg.keyboard.press("Tab")
            k = pg.evaluate("""() => { const a = document.activeElement; if (!a || !a.closest('.reader-panel')) return null;
                return a.getAttribute('data-reader-switch') ? 'sw:' + a.getAttribute('data-reader-switch') : a.tagName === 'SELECT' ? 'select' : 'other'; }""")
            if k:
                seen.add(k)
            if {"sw:wbw", "sw:tr", "select"} <= seen:
                break
        chk(dev, "13 Tab reaches the «Аа» switches (пословный / переводы) and the language menu", {"sw:wbw", "sw:tr", "select"} <= seen, str(sorted(seen)))
        if "sw:wbw" in seen:
            # focus it again and toggle with the keyboard
            pg.focus(".reader-panel [data-reader-switch=wbw]")
            before = pg.get_attribute(".reader-panel [data-reader-switch=wbw]", "aria-checked")
            pg.keyboard.press("Space")
            pg.wait_for_timeout(400)
            after = pg.get_attribute(".reader-panel [data-reader-switch=wbw]", "aria-checked") if pg.locator(".reader-panel").count() else None
            chk(dev, "13 the switch toggles from the keyboard (Space)", before != after and after is not None, (before, after))
        c.close()

    # ---------- 14: second tap of every contents row type ----------
    if dev in ("pixel7", "iphone14", "desktop", "mac-safari"):
        c = ctx()
        pg = c.new_page()
        tapxy, tap, bars = helpers(pg)
        LIT = "() => [...document.querySelectorAll('.mobile-menu nav [data-toc-lit]')].map(e => e.getAttribute('data-toc-row'))"
        ROW = """(r) => { const el = [...document.querySelectorAll('.mobile-menu nav [data-toc-row]')].find(e => e.getAttribute('data-toc-row') === r);
            if (!el) return null; el.scrollIntoView({block: 'center'}); const b = el.getBoundingClientRect();
            return {x: b.left + Math.min(40, b.width / 2), y: b.top + b.height / 2, tag: el.tagName, exp: el.getAttribute('aria-expanded'),
                    href: el.getAttribute('href')}; }"""

        def prepare():
            pg.goto(f"{BASE}/{L}/kartika-bhajans/", wait_until="networkidle")
            pg.wait_for_timeout(500)
            for _ in range(3):
                if pg.locator(".mobile-menu").count():
                    break
                bars()
                try:
                    tap("[data-reader-action=contents]", 800)
                except Exception:
                    pass
            for sel in (".mobile-menu [data-toc-group=introduction]", ".mobile-menu [data-toc-group=temple-worship]",
                        ".mobile-menu button[data-toc-chapter=daily-duties-brahma-muhurta]"):
                for _ in range(3):
                    if pg.locator(sel).count() and pg.get_attribute(sel, "aria-expanded") == "true":
                        break
                    if pg.locator(sel).count():
                        tap(sel)

        prepare()
        rows = pg.evaluate("""() => [...document.querySelectorAll('.mobile-menu nav [data-toc-row]')].map(e => ({r: e.getAttribute('data-toc-row'),
            tag: e.tagName, exp: e.getAttribute('aria-expanded')}))""")
        pick = {}
        for x in rows:
            r = x["r"]
            if r == "cover":
                pick.setdefault("cover", r)
            elif r == "sec:mangalacarana":     # a chapter without subsections (a link)
                pick["chapter"] = r
            elif r.startswith("grp:"):
                pick.setdefault("group heading", r)
            elif r.startswith("sub:"):
                pick.setdefault("subsection", r)
            elif r.startswith("sec:") and x["exp"] is not None:
                pick.setdefault("chapter with subsections", r)
            elif r.startswith("sec:") and x["tag"] == "A" and r != "sec:kartika-bhajans":   # (not the page shown)
                pick.setdefault("chapter", r)
        bad = []
        for kind in ("chapter", "subsection", "chapter with subsections", "group heading", "cover"):
            r = pick.get(kind)
            if not r:
                bad.append((kind, "no row"))
                continue
            prepare()
            other = next(x for x in ("sec:parampara", "sec:mangalacarana", "grp:introduction") if x != r and x not in pg.evaluate(LIT))
            pg.evaluate("""(o) => { const el = [...document.querySelectorAll('.mobile-menu nav [data-toc-row]')].find(e => e.getAttribute('data-toc-row') === o); el && el.click(); }""", other)
            pg.wait_for_timeout(250)
            u0 = pg.url
            q = pg.evaluate(ROW, r)
            if not q:
                bad.append((kind, r, "row gone"))
                continue
            tapxy(q["x"], q["y"], 400)
            q1 = pg.evaluate(ROW, r)
            if pg.evaluate(LIT) != [r] or pg.url != u0 or not q1 or q1["exp"] != q["exp"]:
                bad.append((kind, r, "1st tap", pg.evaluate(LIT), pg.url[-30:], q1 and q1["exp"]))
                continue
            tapxy(q1["x"], q1["y"], 1200)
            if q["exp"] is not None:      # disclosure: the 2nd tap opens / closes it
                q2 = pg.evaluate(ROW, r)
                if not q2 or q2["exp"] == q["exp"]:
                    bad.append((kind, r, "2nd tap did not toggle", q["exp"], q2 and q2["exp"]))
            else:                          # a link: the 2nd tap opens it
                want = (q["href"] or "").rstrip("/")
                if pg.url == u0 or not unquote(pg.url).split("?")[0].rstrip("/").endswith(unquote(want).rsplit("/arcana-paddhati", 1)[-1].rstrip("/")):
                    bad.append((kind, r, "2nd tap did not open", want[-40:], pg.url[-40:]))
        chk(dev, f"14 second tap opens every contents row type ({', '.join(f'{k}={v}' for k, v in pick.items())})", not bad and len(pick) == 5, str(bad[:3]))
        c.close()
    b.close()


def rhombi_gone():
    """The frame's top / bottom centre (where the rhombi were) holds only the two gold lines: in the centre
    column, between the outer line and the image edge, no white-filled diamond (≥ 4 px of opaque white)."""
    from PIL import Image
    chkf = json.load(open(os.path.join(qa.REPO, "scripts", "parampara", "check.json"), encoding="utf-8"))
    bad = []
    for pgd in chkf["pages"]:
        f = os.path.join(qa.REPO, "public", "images", pgd["image"])
        im = Image.open(f).convert("RGBA")
        w, h = im.size
        pad = pgd["oval_pad"]
        for y0, y1 in ((0, int(pad)), (int(h - pad), h)):
            col = [im.getpixel((w // 2, y)) for y in range(y0, y1)]
            white = sum(1 for p in col if p[3] > 200 and min(p[:3]) > 235)
            if white >= 4:
                bad.append((pgd["id"], y0, white))
        if not os.path.isfile(f[:-4] + ".webp"):
            bad.append((pgd["id"], "no webp"))
    chk("data", "9 parampara PNGs: no rhombi at the oval's top / bottom; every PNG has its WebP", not bad, str(bad[:4]))


rhombi_gone()
with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        print(f"== {dev}", flush=True)
        try:
            run(p, dev, eng, o)
        except Exception as e:  # a crash is a failure, with its message
            chk(dev, "suite crashed", False, repr(e)[:300])
        try:
            run_v781(p, dev, eng, o)
        except Exception as e:
            chk(dev, "v7.8.1 checks crashed", False, repr(e)[:300])
print(f"s26: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
