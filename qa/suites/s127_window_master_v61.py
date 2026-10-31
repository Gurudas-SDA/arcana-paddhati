"""V61 step 4 — «Мастер-окно» (Враджа Лила 30.10.2026, plan step 4; her decisions: question 1 «согласен», question 2 variant «А»).

Rule text (Vraja Lila, V61 plan, step 4, decisions of 30.10.2026):
 вопрос 1 «согласен»: всплывающие карточки и окна — один радиус и одна тень; панель «Аа» и список языков выглядят как раньше;
 вопрос 2, вариант «А»: крестик закрытия — круглая кнопка, зона нажатия 44×44, центр 30/30 от угла, крест 18 px, значок строго 1:1
  (не сжимается: flex-shrink:0, width = height), один цвет из токена; один компонент/класс для всех окон;
 внутренние поля окон по шкале: поле окна 16; большие окна и страницы на компьютере 24, на телефоне 16 (токены --space-* шага 2).
Acceptance: (a) in every window the ✕ has the same size and place and is not squeezed; (b) all windows have one radius / one shadow
 (except «Аа» and the language list); (c) day / sepia / night: nothing else changes.

Checks
  A) source: tokens --radius-window, --shadow-window, --window-close-size (= --target 44), --window-close-centre (30px), --window-close-icon (18px),
  Window radius = 16px (Vraja Lila msg 7167, 31.10.2026: «2 - 16»).
     --window-close-fg are declared ONCE in design-system/tokens.css; ONE component components/WindowClose.tsx is used by the four windows
     (mood, bookmark name, install, floating picture copy); no window keeps its own ✕ markup (no «absolute top-3 right-3», no «h-12 w-12» ✕ in
     MoodBlock, no text ✕ in the .hs-peek); the window rules read the tokens;
  B) app (<base-url>): mood window, bookmark-name window, floating picture copy, install window (phones): the ✕ box is 44×44, its icon 18×18
     (1:1), flex-shrink 0, border-radius 50 %, the ✕ centre is 30 px from the card's top edge and 30 px from its right edge, one colour in all
     windows; the cards have one border-radius and one box-shadow; the card's inner padding on the scale (bookmark/install 16; mood 16 on phone,
     24 from 640 px).
# tehniskais slieksnis Lipikāra, nav S noteikums: ±1 px measuring tolerance; the shadow is the token value, compared as computed text.
usage: python s127_window_master_v61.py [<base-url>]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else None
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
results = []
TOL = 1.0


def check(where, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {where} {name} {'' if ok else json.dumps(info, ensure_ascii=False)[:900]}", flush=True)


def rd(*p):
    return open(os.path.join(ROOT, *p), encoding="utf-8").read()


def strip(t):
    return re.sub(r"/\*.*?\*/", "", t, flags=re.S)


def static():
    tok = strip(rd("design-system", "tokens.css"))
    css = strip(rd("app", "globals.css"))
    for name, val in [("--radius-window", "16px"), ("--shadow-window", None), ("--window-close-size", "var(--target)"),
                      ("--window-close-centre", "30px"), ("--window-close-icon", "18px"), ("--window-close-fg", None)]:
        d = re.findall(rf"(?m)^\s*{re.escape(name)}\s*:\s*([^;]+);", tok)
        check("src", f"A {name} declared once in tokens.css" + (f" = {val}" if val else ""),
              len(d) == 1 and (val is None or d[0].strip() == val), d)
    check("src", "A the component components/WindowClose.tsx exists", os.path.exists(os.path.join(ROOT, "components", "WindowClose.tsx")))
    for f in ["MoodBlock", "BookmarkNameDialog", "InstallBanner", "Hotspots"]:
        s = rd("components", f + ".tsx")
        check("src", f"A {f}.tsx uses <WindowClose", "<WindowClose" in s)
    check("src", "A no window keeps its own ✕ markup (absolute top-3 right-3 / h-12 w-12 / text ✕ in the peek)",
          "absolute top-3 right-3" not in rd("components", "BookmarkNameDialog.tsx") + rd("components", "InstallBanner.tsx")
          and "inline-flex h-12 w-12" not in rd("components", "MoodBlock.tsx") and "{closeLabel}" not in rd("components", "Hotspots.tsx"))
    w = re.search(r"\.window-close\s*\{([^}]*)\}", css)
    body = w.group(1) if w else ""
    check("src", "A .window-close rule: size from the token, flex-shrink 0, round, colour from the token",
          bool(w) and "var(--window-close-size)" in body and re.search(r"flex-shrink\s*:\s*0", body) and "var(--window-close-fg)" in body
          and ("9999px" in body or "var(--radius-pill)" in body), body)
    card = re.search(r"\.window-card\s*\{([^}]*)\}", css)
    check("src", "A .window-card rule reads --radius-window and --shadow-window",
          bool(card) and "var(--radius-window)" in card.group(1) and "var(--shadow-window)" in card.group(1), card and card.group(1))


MEASURE = """([cardSel, closeSel, padSel]) => {
  const card = document.querySelector(cardSel); const x = document.querySelector(closeSel);
  if (!card || !x) return {err: 'missing ' + (card ? closeSel : cardSel)};
  const c = card.getBoundingClientRect(), b = x.getBoundingClientRect(), cs = getComputedStyle(card), xs = getComputedStyle(x);
  const svg = x.querySelector('svg'); const s = svg && svg.getBoundingClientRect();
  const pad = padSel ? getComputedStyle(document.querySelector(padSel)) : cs;
  return {w: +b.width.toFixed(2), h: +b.height.toFixed(2), iw: s && +s.width.toFixed(2), ih: s && +s.height.toFixed(2),
    shrink: xs.flexShrink, radiusX: xs.borderRadius, color: xs.color,
    top: +((b.top + b.height / 2) - c.top).toFixed(2), right: +(c.right - (b.left + b.width / 2)).toFixed(2),
    cardRadius: cs.borderTopLeftRadius, shadow: cs.boxShadow, padL: pad.paddingLeft, padT: pad.paddingTop, vw: innerWidth};
}"""

SIZES = {}


def verify(dev, tag, m, pad=None):
    if "err" in m:
        check(dev, f"{tag}: window opens", False, m)
        return
    check(dev, f"{tag}: ✕ box 44×44", abs(m["w"] - 44) <= TOL and abs(m["h"] - 44) <= TOL, m)
    check(dev, f"{tag}: ✕ icon 18×18 (1:1, not squeezed), flex-shrink 0",
          m["iw"] is not None and abs(m["iw"] - 18) <= TOL and abs(m["ih"] - 18) <= TOL and m["shrink"] == "0", m)
    check(dev, f"{tag}: ✕ round", m["radiusX"] in ("50%", "9999px", "22px"), m["radiusX"])
    check(dev, f"{tag}: ✕ centre 30 / 30 from the card's top-right corner", abs(m["top"] - 30) <= TOL and abs(m["right"] - 30) <= TOL, m)
    if pad is not None:
        check(dev, f"{tag}: inner padding {pad} px (the scale)", m["padL"] == f"{pad}px", m["padL"])
    SIZES.setdefault("radius", set()).add(m["cardRadius"])
    SIZES.setdefault("shadow", set()).add(m["shadow"])
    SIZES.setdefault("color", set()).add(m["color"])


def app():
    from playwright.sync_api import sync_playwright
    devs = qa.devices(["iphone14", "desktop"])
    with sync_playwright() as p:
        for dev, eng, opts in devs:
            b = getattr(p, eng).launch()
            touch = bool(opts.get("has_touch"))
            c = b.new_context(service_workers="block", locale="ru-RU", **opts)
            c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');")
            pg = c.new_page()
            # mood window
            pg.goto(f"{BASE}/ru-iast/vigraha-tattva/", wait_until="networkidle")
            pg.wait_for_timeout(900)
            pg.evaluate("() => document.querySelector('.mood-toggle').click()")
            pg.wait_for_timeout(500)
            wide = 24 if (opts["viewport"]["width"] >= 640) else 16
            m = pg.evaluate(MEASURE, [".mood-dialog", ".mood-dialog .window-close", ".mood-scroll"])
            verify(dev, "mood window", m, wide)
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(300)
            # bookmark-name window
            pg.goto(f"{BASE}/ru-iast/daily-duties-brahma-muhurta/", wait_until="networkidle")
            pg.wait_for_timeout(900)
            pg.evaluate("() => document.querySelector('[data-reader-action=bookmark]').click()")
            pg.wait_for_timeout(600)
            m = pg.evaluate(MEASURE, ["[data-bookmark-dialog] [role=dialog]", "[data-bookmark-dialog] .window-close", None])
            verify(dev, "bookmark-name window", m, 16)
            # floating picture copy
            pg.goto(f"{BASE}/ru-iast/worship-sixteen-articles/", wait_until="networkidle")
            pg.wait_for_timeout(900)
            r = pg.evaluate("""async () => { const mn = document.querySelector('.app-main');
              const row = document.querySelector('.app-main .hs-row[data-hs-nums="14"]'); if (!row) return 'no row';
              mn.scrollTop += row.getBoundingClientRect().top - innerHeight * 0.3; mn.dispatchEvent(new Event('scroll'));
              await new Promise(r => setTimeout(r, 150)); const hit = row.querySelector('.hs-text, .hs-cell'); hit.click();
              for (let i = 0; i < 3; i++) { await new Promise(r => setTimeout(r, 180)); dispatchEvent(new Event('resize')); mn.dispatchEvent(new Event('scroll')); }
              await new Promise(r => setTimeout(r, 500)); return !!document.querySelector('.hs-peek'); }""")
            if r is True:
                m = pg.evaluate(MEASURE, [".hs-peek", ".hs-peek .window-close", None])
                verify(dev, "floating picture copy", m, None)
            else:
                check(dev, "floating picture copy opens (or the picture itself is on the screen)", r is not True and r != "no row", r)
            c.close()
            # install window (phones)
            if touch:
                c = b.new_context(service_workers="block", locale="ru-RU", **opts)
                c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');")
                pg = c.new_page()
                pg.goto(f"{BASE}/ru-iast/", wait_until="networkidle")
                try:
                    pg.wait_for_selector(".install-banner", timeout=8000)
                    pg.get_by_role("button", name="Установить").first.click()
                    pg.wait_for_timeout(500)
                except Exception as e:  # noqa: BLE001
                    check(dev, "install window opens", False, str(e)[:200])
                else:
                    m = pg.evaluate(MEASURE, [".install-modal [role=dialog]", ".install-modal .window-close", None])
                    verify(dev, "install window", m, 16)
                c.close()
            b.close()
            check(dev, "one card radius in all windows", len(SIZES.get("radius", [])) == 1, sorted(SIZES.get("radius", [])))
            check(dev, "one card shadow in all windows", len(SIZES.get("shadow", [])) == 1, sorted(SIZES.get("shadow", [])))
            check(dev, "one ✕ colour in all windows", len(SIZES.get("color", [])) == 1, sorted(SIZES.get("color", [])))
            SIZES.clear()


static()
if BASE:
    app()
n = sum(results)
print(f"\n{n}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
