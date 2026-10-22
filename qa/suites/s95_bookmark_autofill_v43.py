"""V43 p.1 — the bookmark's name field without iOS «AutoFill Contact» (Vraja Lila 22.10.2026, iPhone screenshots
1792651216877 / 1792651217013 / 1792651217063; saskarnes autors, «Стандарты» 0а).

Vraja Lila's words (verbatim): «autofill пока вижу» — on a real iPhone the window «Rename the bookmark» still shows the
iOS bar «AutoFill Contact» above the keyboard (after V38 d73ce16: autocomplete off, a search-type field).

Safari ignores autocomplete="off" for contact AutoFill and decides by the field's name / id, its placeholder and the
text of its label (reported: a dash in the name — «bm-title-field»; «Name» / «Title» words). Playwright's WebKit has no
Safari AutoFill, so this test checks ONLY the attributes; the real check is Vraja Lila's, on an iPhone.

Checks, per device, for «Новая закладка» (ribbon) and «Переименовать» (pencil), in RU and EN:
  A  name / id: no dash, no contact word (name, title, contact, first, last, full, user, mail, tel, phone, address,
     nick, имя, назв), the name contains «search»;
  B  no placeholder; autocomplete="off" on the field and its form;
  C  the label and the window title, as raw text, contain no contact word (Name / Название / Rename / Переименовать) —
     the letters are joined by U+200D; the text a person reads (joiners removed) is unchanged;
  D  typing still works: a new name is saved (the joiners never reach the bookmark).
usage: python s95_bookmark_autofill_v43.py <base-url>
"""
import json
import os
import re
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
CH = "daily-duties-brahma-muhurta"
OTHER = "arcana-procedure"
SEED = [{"id": "b-af", "section": OTHER, "anchor": "2-svagata", "block": 0, "lang": "ru-iast", "time": 1792000000000, "name": "Утро"}]
MENU = ".mobile-menu[data-open]"
CONTACT = re.compile(r"name|title|contact|fname|lname|first|last|full|user|mail|tel|phone|address|nick|имя|имен|назв|nom|név", re.I)
WANT = {"ru-iast": {"label": "Название", "add": "Новая закладка", "rename": "Переименовать закладку"},
        "en": {"label": "Name", "add": "New bookmark", "rename": "Rename the bookmark"}}
results = []

FIELD = """() => { const d = document.querySelector('[data-bookmark-dialog]'); if (!d) return null;
  const inp = d.querySelector('[data-bookmark-dialog-input]'); const lab = inp && inp.labels && inp.labels[0];
  const h = d.querySelector('#bookmark-name-title');
  return {id: inp.id, name: inp.getAttribute('name') || '', ph: inp.getAttribute('placeholder'), ac: inp.getAttribute('autocomplete'),
          formAc: inp.form ? inp.form.getAttribute('autocomplete') : null, type: inp.type,
          label: lab ? lab.textContent : null, title: h ? h.textContent : null}; }"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


def stored(pg):
    return pg.evaluate("(JSON.parse(localStorage.getItem('ap.bookmarks') || 'null') || {items: []}).items")


def field_checks(pg, dev, what, lang, mode):
    f = pg.evaluate(FIELD)
    if not f:
        check(dev, f"{what}: the window opens", False)
        return
    check(dev, f"A {what}: name / id without a dash or contact word; name has «search»",
          "-" not in f["id"] and "-" not in f["name"] and not CONTACT.search(f["id"]) and not CONTACT.search(f["name"])
          and "search" in f["name"].lower(), f)
    check(dev, f"B {what}: no placeholder, autocomplete off (field and form)",
          not f["ph"] and f["ac"] == "off" and f["formAc"] == "off", f)
    raw_ok = f["label"] is not None and f["title"] is not None and not CONTACT.search(f["label"]) and not CONTACT.search(f["title"])
    read = {k: (f[k] or "").replace("‍", "") for k in ("label", "title")}
    check(dev, f"C {what}: label / title raw text has no contact word; read text unchanged",
          raw_ok and read["label"] == WANT[lang]["label"] and read["title"] == WANT[lang][mode],
          {"raw": [f["label"], f["title"]], "read": read})


def run(browser, dev, opts):
    touch = opts.get("has_touch", False)
    c = browser.new_context(service_workers="block", locale="ru-RU", **opts)
    c.add_init_script("if (!sessionStorage.getItem('qaSeeded')) { localStorage.setItem('ap.readerHintSeen','1');"
                      "localStorage.setItem('installDismissed','true');"
                      f"localStorage.setItem('ap.bookmarks', JSON.stringify({json.dumps({'v': 1, 'items': SEED}, ensure_ascii=False)}));"
                      "sessionStorage.setItem('qaSeeded','1'); }")
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        for lang in ("ru-iast", "en"):
            pg.goto(f"{BASE}/{CH}/" if lang == "en" else f"{BASE}/{lang}/{CH}/", wait_until="networkidle")   # EN = the root
            pg.wait_for_timeout(1200)
            pg.locator("[data-reader-action=bookmark]").evaluate("b => b.click()")
            pg.wait_for_timeout(500)
            field_checks(pg, dev, f"{lang} «Новая закладка»", lang, "add")
            pg.locator("[data-bookmark-dialog-cancel]").evaluate("b => b.click()")
            pg.wait_for_timeout(400)
            pg.locator("[data-reader-action=contents]").evaluate("b => b.click()")
            pg.wait_for_timeout(700)
            tab = pg.locator(f"{MENU} [data-sidebar-tab=bookmarks]")
            if tab.count() and tab.get_attribute("aria-selected") != "true":
                tab.evaluate("b => b.click()")
                pg.wait_for_timeout(400)
            pg.locator(f"{MENU} [data-bookmark-id=b-af] [data-bookmark-rename]").evaluate("b => b.click()")
            pg.wait_for_timeout(500)
            field_checks(pg, dev, f"{lang} «Переименовать»", lang, "rename")
            if lang == "ru-iast":
                pg.locator("[data-bookmark-dialog-input]").fill("Утро V43")
                pg.locator("[data-bookmark-dialog-confirm]").evaluate("b => b.click()")
                pg.wait_for_timeout(400)
                names = {b["id"]: b.get("name") for b in stored(pg)}
                check(dev, "D typing a new name saves it (no joiners in the bookmark)", names.get("b-af") == "Утро V43", names)
            else:
                pg.locator("[data-bookmark-dialog-cancel]").evaluate("b => b.click()")
                pg.wait_for_timeout(300)
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(300)
        check(dev, "no page errors", not errors, errors[:3])
    except Exception as error:
        traceback.print_exc()
        check(dev, "scenario ran", False, str(error)[:300])
    finally:
        c.close()


with sync_playwright() as p:
    for dev, eng, opts in qa.devices(["iphone14", "desktop"]):
        b = getattr(p, eng).launch()
        run(b, dev, opts)
        b.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
