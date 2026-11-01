"""V63 — close ✕ line 1.5 px and hover / press = --surface-hover (Vraja Lila decisions, gl.13 review 01.11.2026).

Rule text (Vraja Lila, V61 plan, decisions accepted 30.10.2026; «правила дизайн-системы для главы 13», 13.x):
 вопрос 2, вариант «А» (msg 1983): «принимаю» — крест 18 px, линия 1,5 px, один цвет на тему из токена;
 вопрос 3 (msg 1948): наведение — один оттенок на тему; «наведение на строку, крестик и кнопку — --surface-hover»,
  «подложка при нажатии и наведении — круг».
Acceptance: (a) computed stroke-width of the ✕ icon = 1.5 in all 4 windows (mood, bookmark name, floating picture copy, install);
 (b) hover and press background of the ✕ = value of --surface-hover in light / sepia / night; (c) night: ✕ colour on the hover
 background >= 3:1 (s81 thresholds stay); (d) no hard 1.5 in the component: the line comes from the token --window-close-stroke.
# tehniskais slieksnis Lipikāra, nav S noteikums: ±0.01 stroke tolerance; contrast 3:1 = WCAG 1.4.11 (as s81).
# mans pieņēmums: «нажатие» (:active) = tas pats --surface-hover kā uz hover (rule text names one shade for hover and press).
usage: python s132_window_close_v63.py [<base-url>]
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


def check(where, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {where} {name} {'' if ok else json.dumps(info, ensure_ascii=False)[:900]}", flush=True)


def rd(*p):
    return open(os.path.join(ROOT, *p), encoding="utf-8").read()


def strip(t):
    return re.sub(r"/\*.*?\*/", "", t, flags=re.S)


def lum(rgb):
    def f(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def rgb(s):
    n = [float(x) for x in re.findall(r"[\d.]+", s)[:3]]
    return tuple(n)


def static():
    tok = strip(rd("design-system", "tokens.css"))
    css = strip(rd("app", "globals.css"))
    d = re.findall(r"(?m)^\s*--window-close-stroke\s*:\s*([^;]+);", tok)
    check("src", "D token --window-close-stroke = 1.5 declared once in tokens.css", len(d) == 1 and d[0].strip() == "1.5", d)
    tsx = rd("components", "WindowClose.tsx")
    check("src", "D WindowClose.tsx keeps no hard strokeWidth", "strokeWidth" not in tsx, "strokeWidth present")
    svg = re.search(r"\.window-close svg\s*\{([^}]*)\}", css)
    check("src", "D .window-close svg reads stroke-width from the token", bool(svg) and "var(--window-close-stroke)" in svg.group(1), svg and svg.group(1))
    for sel in [r"\.window-close:hover", r"\.window-close:active", r"\.hs-peek \.window-close:hover", r"\.hs-peek \.window-close:active"]:
        m = re.search(r"(?:^|[},]\s*)" + sel + r"\s*(?:,[^{}]*)?\{([^}]*)\}", css)
        check("src", f"B {sel.replace(chr(92), '')} uses --surface-hover", bool(m) and "var(--surface-hover)" in m.group(1) and "gold-light" not in m.group(1), m and m.group(1))


PROBE = """([closeSel]) => {
  const x = document.querySelector(closeSel); if (!x) return {err: 'missing ' + closeSel};
  const l = x.querySelector('line'); const p = document.createElement('i');
  p.style.cssText = 'position:absolute;width:0;height:0;background:var(--surface-hover)'; x.parentElement.appendChild(p);
  const hov = getComputedStyle(p).backgroundColor; p.remove();
  let n = x.parentElement, bg = 'rgba(0, 0, 0, 0)';
  while (n) { const c = getComputedStyle(n).backgroundColor; if (!/rgba\\(.*, 0\\)$/.test(c) && c !== 'transparent') { bg = c; break; } n = n.parentElement; }
  return {stroke: getComputedStyle(l).strokeWidth, hov, fg: getComputedStyle(x).color, cardBg: bg, bgNow: getComputedStyle(x).backgroundColor};
}"""
BG = "(s) => getComputedStyle(document.querySelector(s)).backgroundColor"


def verify(dev, theme, tag, pg, sel, mouse=True, hover_xy=None):
    m = pg.evaluate(PROBE, [sel])
    if "err" in m:
        check(dev, f"{theme} {tag}: window opens", False, m)
        return
    check(dev, f"{theme} {tag}: ✕ stroke-width = 1.5", abs(float(m["stroke"].replace("px", "")) - 1.5) <= 0.01, m)
    if mouse:
        box = pg.locator(sel).bounding_box()
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        pg.mouse.move(cx, cy)
        pg.wait_for_timeout(350)
        h = pg.evaluate(BG, sel)
        check(dev, f"{theme} {tag}: hover background = --surface-hover", h == m["hov"], {"hover": h, "want": m["hov"]})
        pg.mouse.down()
        pg.wait_for_timeout(350)
        a = pg.evaluate(BG, sel)
        check(dev, f"{theme} {tag}: pressed background = --surface-hover", a == m["hov"], {"active": a, "want": m["hov"]})
        if theme == "night":
            r = ratio(rgb(m["fg"]), rgb(m["hov"]))
            check(dev, f"night {tag}: ✕ on hover background >= 3:1", r >= 3, round(r, 2))
            r2 = ratio(rgb(m["fg"]), rgb(m["cardBg"]))
            check(dev, f"night {tag}: ✕ on card >= 3:1", r2 >= 3, round(r2, 2))


def app():
    from playwright.sync_api import sync_playwright
    devs = qa.devices(["iphone14", "desktop"])
    with sync_playwright() as p:
        for dev, eng, opts in devs:
            b = getattr(p, eng).launch()
            touch = bool(opts.get("has_touch"))
            themes = ["white", "sepia", "night"] if not touch else ["white", "night"]
            for theme in themes:
                c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce", **opts)
                c.add_init_script(f"localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerTheme','{theme}');")
                pg = c.new_page()
                hov = not touch
                pg.goto(f"{BASE}/ru-iast/vigraha-tattva/", wait_until="networkidle")
                pg.wait_for_timeout(900)
                pg.evaluate("() => document.querySelector('.mood-toggle').click()")
                pg.wait_for_timeout(500)
                verify(dev, theme, "mood window", pg, ".mood-dialog .window-close", hov)
                pg.mouse.up()
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(300)
                pg.goto(f"{BASE}/ru-iast/daily-duties-brahma-muhurta/", wait_until="networkidle")
                pg.wait_for_timeout(900)
                pg.evaluate("() => document.querySelector('[data-reader-action=bookmark]').click()")
                pg.wait_for_timeout(600)
                verify(dev, theme, "bookmark-name window", pg, "[data-bookmark-dialog] .window-close", hov)
                pg.mouse.up()
                pg.goto(f"{BASE}/ru-iast/worship-sixteen-articles/", wait_until="networkidle")
                pg.wait_for_timeout(900)
                r = pg.evaluate("""async () => { const mn = document.querySelector('.app-main');
                  const row = document.querySelector('.app-main .hs-row[data-hs-nums="14"]'); if (!row) return 'no row';
                  mn.scrollTop += row.getBoundingClientRect().top - innerHeight * 0.3; mn.dispatchEvent(new Event('scroll'));
                  await new Promise(r => setTimeout(r, 150)); const hit = row.querySelector('.hs-text, .hs-cell'); hit.click();
                  for (let i = 0; i < 3; i++) { await new Promise(r => setTimeout(r, 180)); dispatchEvent(new Event('resize')); mn.dispatchEvent(new Event('scroll')); }
                  await new Promise(r => setTimeout(r, 500)); return !!document.querySelector('.hs-peek'); }""")
                if r is True:
                    verify(dev, theme, "floating picture copy", pg, ".hs-peek .window-close", hov)
                    pg.mouse.up()
                else:
                    check(dev, f"{theme} floating picture copy opens", False, r)
                c.close()
                if touch:
                    c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce", **opts)
                    c.add_init_script(f"localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('ap.readerTheme','{theme}');")
                    pg = c.new_page()
                    pg.goto(f"{BASE}/ru-iast/", wait_until="networkidle")
                    try:
                        pg.wait_for_selector(".install-banner", timeout=8000)
                        pg.get_by_role("button", name="Установить").first.click()
                        pg.wait_for_timeout(500)
                    except Exception as e:  # noqa: BLE001
                        check(dev, f"{theme} install window opens", False, str(e)[:200])
                    else:
                        verify(dev, theme, "install window", pg, ".install-modal .window-close", False)
                    c.close()
            b.close()


static()
if BASE:
    app()
n = sum(results)
print(f"\n{n}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
