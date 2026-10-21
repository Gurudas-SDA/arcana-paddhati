"""Search field on iPhone (Vraja Lila msg 5316 p. 3, 20.10.2026).

Rule text (verbatim): «Поле поиска: font-size 16 px и подсказка placeholder-[#8B6508].»
(16 px: Safari on iPhone does not zoom the page when the field gets focus.)
p. 3а (verbatim): «ФОКУС в поле поиска — ТОЛЬКО если перед ним отдельным коммитом все проверки «панель .mobile-menu[data-open]
есть в DOM» переведены на отдельный признак открытости (например .mobile-menu[data-open]).»
Focus check: «Поиск» focuses the field INSIDE the tap (window.event is the tap's event when focus() runs) —
Safari opens the keyboard only for a focus made during the user's gesture; a focus from a timer is not one.
usage: python s51_search_field.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from toc import Contents  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        c = b.new_context(service_workers="block", locale="ru-RU", **opts)
        c.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
        pg = c.new_page()
        pg.goto(f"{BASE}/ru-iast/arcana-procedure/", wait_until="networkidle")
        pg.wait_for_timeout(800)
        Contents(pg, qa.TocMode("default"), opts.get("has_touch", False)).contents()
        pg.wait_for_timeout(400)
        st = pg.evaluate("""() => { const i = document.querySelector('input.search-input'); if (!i) return null;
          // WebKit has no getComputedStyle(…, '::placeholder'): the ::placeholder rule that applies to the field
          let rule = null;
          for (const sh of document.styleSheets) { let rs; try { rs = sh.cssRules; } catch (e) { continue; }
            const walk = list => { for (const r of list) { if (r.cssRules) walk(r.cssRules);
              if (r.selectorText && r.selectorText.includes('::placeholder')) { const sel = r.selectorText.split('::placeholder')[0];
                try { if (sel && i.matches(sel)) rule = r.style.color; } catch (e) {} } } };
            walk(rs); }
          return {size: parseFloat(getComputedStyle(i).fontSize), ph: getComputedStyle(i, '::placeholder').color, rule}; }""")
        check(dev, "search field font-size ≥ 16 px", st and st["size"] >= 16, st)
        ok_ph = lambda v: (v or "").replace(" ", "").lower() in ("rgb(150,87,0)", "rgba(150,87,0,1)", "#965700", "var(--ap-gold)")  # V33 (Vraja Lila msg 5907): --ap-gold #965700, was #8B6508
        check(dev, "placeholder colour --ap-gold #965700", st and (ok_ph(st["ph"]) or (eng == "webkit" and ok_ph(st["rule"]))), st)
        c.close()
        c = b.new_context(service_workers="block", locale="ru-RU", **opts)
        c.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
        pg = c.new_page()
        # 3а/3: «Поиск» focuses the field during the tap itself
        pg.goto(f"{BASE}/ru-iast/arcana-procedure/", wait_until="networkidle")
        pg.wait_for_timeout(800)
        pg.evaluate("""() => { window.__focusIn = []; const f = HTMLElement.prototype.focus;
          HTMLElement.prototype.focus = function () { if (this.matches && this.matches('input[type=search]'))
            window.__focusIn.push(window.event ? window.event.type : null); return f.apply(this, arguments); }; }""")
        flow = Contents(pg, qa.TocMode("default"), opts.get("has_touch", False))
        flow.bars()
        btn = pg.locator("[data-reader-action=search]")
        (btn.tap if opts.get("has_touch") else btn.click)()
        pg.wait_for_timeout(600)
        fin = pg.evaluate("window.__focusIn")
        act = pg.evaluate("document.activeElement && document.activeElement.matches('input[type=search]')")
        check(dev, "«Поиск»: the field is focused inside the tap (keyboard at once on iPhone)", act and fin and fin[0] is not None, {"focus calls (event)": fin, "active": act})
        open_attr = pg.locator(".mobile-menu[data-open]").count()
        check(dev, "3а the open menu carries [data-open]", open_attr == 1, open_attr)
        c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
