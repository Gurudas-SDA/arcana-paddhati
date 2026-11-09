"""V91 — Vraja Lila 09.11 msg 2841/2843/7933/7934/7940 («по заметкам - вариант А ... сделай где видно 3 строчки»), variant A3.
Side panel, tab «Заметки», the card of a note:
 (1) shows ONLY the note's text (no chapter / place line; «Пуджари / Харибол» is the note text, its line break stays);
 (2) a note without text: the highlighted text is the card's title (Vraja Lila msg 7933);
 (3) the text is cut at 3 lines with «…» (a long note AND a long highlighted text); a short one stays short;
 (4) the date DD.MM.YYYY stays (msg 7934); the handle, the pencil and the bin stay.
# tehniskais slieksnis Lipikāra, nav S noteikums: settle 300-900 ms
usage: python s161_note_card_v91.py <base-url>
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7", "desktop"])
results = []
PAGE = "daily-duties-brahma-muhurta"
SELECT = """() => {
  const p = [...document.querySelectorAll('.app-main article p')].find(x => x.getClientRects().length && (x.textContent.match(/\\S+/g) || []).length >= 9 && !x.closest('button,table,[hidden],.mood-panel'));
  if (!p) return null; p.scrollIntoView({block: 'center'});
  const w = document.createTreeWalker(p, NodeFilter.SHOW_TEXT); let n = w.nextNode(); while (n && (n.data.match(/\\S+/g) || []).length < 9) n = w.nextNode();
  const ws = [...n.data.matchAll(/\\S+/g)]; const r = document.createRange(); r.setStart(n, ws[2].index); r.setEnd(n, ws[7].index + ws[7][0].length);
  const s = getSelection(); s.removeAllRanges(); s.addRange(r); return true; }"""
SEED = """() => { const o = JSON.parse(localStorage.getItem('ap.highlights')); const b = o.items[0];
  const mk = (id, quote, note, k) => ({...b, id, quote, note, start: k * 40, end: k * 40 + 30, created: 1762473600000 + k});
  const long = 'Здесь я записал, как проходит утренний обход: сначала омовение Божеств, потом одевание, подношение цветов и гирлянд, затем арати и киртан; нужно уточнить у пуджари порядок подношений и сверить с описанием в этой главе, а также спросить про время омовения зимой и летом.';
  const longq = 'saṁsāra-dāvānala-līḍha-loka-trāṇāya kāruṇya-ghanāghanatvam prāptasya kalyāṇa-guṇārṇavasya vande guroḥ śrī-caraṇāravindam mahāprabhoḥ kīrtana-nṛtya-gīta';
  o.items = [mk('n-short', 'QQQ-quote-one', 'Пуджари\\nХарибол', 1), mk('n-long', 'QQQ-quote-two', long, 2), mk('n-empty', 'Короткое выделение без заметки', '', 3), mk('n-emptylong', longq, '', 4)];
  o.items.forEach(i => { if (!i.note) delete i.note; });
  localStorage.setItem('ap.highlights', JSON.stringify(o)); }"""
ROWS = """() => [...document.querySelectorAll('[data-note-row]')].map(r => {
  const body = r.querySelector('[data-note-body]'); const cs = body ? getComputedStyle(body) : null;
  return {id: r.dataset.noteId, text: r.textContent, body: body ? body.textContent : null, clamp: cs ? cs.webkitLineClamp : null,
          lines: body ? Math.round(body.getBoundingClientRect().height / parseFloat(cs.lineHeight)) : 0,
          place: !!r.querySelector('[data-note-place]'), quote: !!r.querySelector('[data-note-quote]'),
          date: (r.querySelector('[data-note-date]') || {}).textContent || '', pencil: !!r.querySelector('[data-note-edit]'),
          bin: !!r.querySelector('[data-note-delete]'), handle: !!r.querySelector('[data-bookmark-handle]'),
          overflow: r.getBoundingClientRect().right > innerWidth + 1}; })"""


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


def run(p, dev, eng, opts):
    b = getattr(p, eng).launch()
    c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce", **opts)
    c.add_init_script("try{if(!sessionStorage.getItem('v91seed')){sessionStorage.setItem('v91seed','1');localStorage.removeItem('ap.highlights');}"
                      "localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');}catch(e){}")
    pg = c.new_page()
    pg.goto(f"{BASE}/ru-iast/{PAGE}/", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    pg.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important}")
    pg.evaluate(SELECT)
    pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    pg.locator("[data-hl-menu] [data-hl-color='1']").click()
    pg.wait_for_timeout(500)
    pg.evaluate(SEED)
    pg.reload(wait_until="networkidle")
    pg.wait_for_timeout(1000)
    pg.evaluate("() => { if (!document.querySelector('[data-sidebar-tabs]')) document.querySelector('[data-reader-action=contents]').click(); }")
    pg.wait_for_selector("[data-sidebar-tab]", timeout=8000)
    pg.wait_for_timeout(500)
    pg.evaluate("() => document.querySelector('[data-sidebar-tab=notes]').click()")
    pg.wait_for_timeout(600)
    rows = {r["id"]: r for r in pg.evaluate(ROWS)}
    check(dev, "4 cards", len(rows) == 4, list(rows))
    s, l, e, el = (rows.get(k, {}) for k in ("n-short", "n-long", "n-empty", "n-emptylong"))
    check(dev, "(1) no chapter / place line on any card", rows and not any(r["place"] for r in rows.values()), [r["place"] for r in rows.values()])
    check(dev, "(1) a note with text: the card shows the note, not the highlighted text", s.get("body") == "Пуджари\nХарибол" and not s.get("quote") and "QQQ" not in s.get("text", "x") and "QQQ" not in l.get("text", "x"), s)
    check(dev, "(1) «Пуджари / Харибол» keeps its two lines", s.get("lines") == 2, s)
    check(dev, "(2) a note without text: the highlighted text is the title", e.get("body") == "Короткое выделение без заметки" and el.get("body", "").startswith("saṁsāra-dāvānala"), [e.get("body"), el.get("body")])
    check(dev, "(3) a long note is cut at 3 lines with «…»", l.get("lines") == 3 and l.get("clamp") == "3", l)
    check(dev, "(3) a long highlighted text of a note without text is cut at 3 lines", el.get("lines") == 3 and el.get("clamp") == "3", el)
    check(dev, "(3) a short card stays short (1 line)", e.get("lines") == 1, e)
    check(dev, "(4) the date DD.MM.YYYY, the handle, the pencil and the bin stay on every card",
          all(re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", r["date"]) and r["pencil"] and r["bin"] and r["handle"] for r in rows.values()), list(rows.values())[:1])
    check(dev, "cards do not go past the right edge (rule 161)", not any(r["overflow"] for r in rows.values()))
    b.close()


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        try:
            run(p, dev, eng, opts)
        except Exception as ex:  # noqa: BLE001
            check(dev, "scenario ran to the end", False, repr(ex)[:400])

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
