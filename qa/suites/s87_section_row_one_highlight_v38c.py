"""V38c — the lit section in «Содержание» is ONE highlight over the whole row (Vraja Lila msg 1321 / 1322, 22.10.2026
~00:09; saskarnes autors, «Стандарты» 0а).

Rule text (Vraja Lila's remark, as passed on — nodots-izpildei 22.10 00:20 п.4, verbatim):
 «выделение раздела в меню разделено на 2 сектора (название + кнопка-стрелка) со стыком цвета — сделать ОДНО выделение
  на всю строку (то же правило «одной подложкой», nodots 17:48)»
Rule text (nodots-izpildei 21.10 17:48, Vraja Lila msg 1290, verbatim): «такие выделения — ОДНИМ блоком/подложкой … в
 ОДНОМ прямоугольнике … не по отдельности».
Criterion (verbatim): «выделенный раздел — один сплошной фон».

Checks, per device, for the Introduction and the part «Храмовый стандарт» (each opened from its name — V37):
  A  the menu opened on the section's page: the lit row's name and arrow ▸ show the same background colour (what is
     painted under each of them), and it is the highlight colour (not the panel's white);
  B  the moment a section's name is tapped (the 150 ms pick-light, data-menu-picked — set as the app sets it), the
     name and the arrow are still one colour: the whole row lights, no seam;
  C  a row that is not lit has no background of its own on either part.
usage: python s87_section_row_one_highlight_v38c.py <base-url>
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from toc import Contents  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
LANG = "ru-iast"
GROUPS = [("introduction", "Введение"), ("temple-worship", "Храмовый стандарт")]
WHITE = "rgb(255, 255, 255)"
results = []

# The colour painted under an element = its own background or the first ancestor's with one.
PAINT = """(gid) => { const nav = document.querySelector('.mobile-menu[data-open] nav'); if (!nav) return null;
  const paint = (e) => { for (let n = e; n && n !== document.body; n = n.parentElement) { const c = getComputedStyle(n).backgroundColor;
      if (c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent') return c; } return 'none'; };
  const name = nav.querySelector(`[data-toc-group="${gid}"]`), arrow = nav.querySelector(`[data-toc-toggle="${gid}"]`);
  if (!name || !arrow) return null;
  return {lit: name.hasAttribute('data-toc-lit'), name: paint(name), arrow: paint(arrow),
          nameOwn: getComputedStyle(name).backgroundColor, arrowOwn: getComputedStyle(arrow).backgroundColor}; }"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:600]}", flush=True)


def run(browser, dev, opts):
    touch = opts.get("has_touch", False)
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1');localStorage.setItem('installDismissed','true')}catch(e){}")
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    flow = Contents(pg, qa.TocMode("default"), touch)
    try:
        for gid, title in GROUPS:
            pg.goto(f"{BASE}/{LANG}/{gid}/", wait_until="networkidle")
            pg.wait_for_timeout(1200)
            flow.contents()
            pg.wait_for_selector(".mobile-menu[data-open] nav", timeout=5000)
            pg.wait_for_timeout(500)
            pg.mouse.move(1, 1)   # no hover over the row (desktop)
            pg.wait_for_timeout(200)
            a = pg.evaluate(PAINT, gid)
            check(dev, f"A «{title}»: lit row — name and arrow one background, the highlight colour",
                  a is not None and a["lit"] and a["name"] == a["arrow"] and a["name"] not in ("none", WHITE), a)
            pg.evaluate("""(gid) => { const n = document.querySelector(`.mobile-menu[data-open] [data-toc-group="${gid}"]`);
              document.querySelectorAll('.mobile-menu [data-menu-picked]').forEach((x) => x.removeAttribute('data-menu-picked'));
              n.setAttribute('data-menu-picked', ''); }""", gid)
            pg.wait_for_timeout(400)
            b = pg.evaluate(PAINT, gid)
            check(dev, f"B «{title}»: the tap's pick-light — the whole row one colour (no seam name | arrow)",
                  b is not None and b["name"] == b["arrow"] and b["name"] not in ("none", WHITE), b)
            other = [g for g, _ in GROUPS if g != gid][0]
            o = pg.evaluate(PAINT, other)
            check(dev, f"C not lit «{other}»: no own background on name or arrow",
                  o is not None and not o["lit"] and o["name"] == o["arrow"], o)
            pg.evaluate("(() => { const d = document.querySelector('.mobile-menu[data-open] > .sidebar-backdrop'); if (d) d.click(); })()")
            pg.wait_for_timeout(700)
        check(dev, "no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(dev, "scenario ran", False, str(error)[:300])
    finally:
        c.close()


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "pixel7", "desktop"]):
        b = getattr(p, eng).launch()
        run(b, dev, opts)
        b.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
