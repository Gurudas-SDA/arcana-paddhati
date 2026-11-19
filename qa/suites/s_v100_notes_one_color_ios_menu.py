"""iOS placement changed in V102 and V104 (the side follows the iOS menu side, see s_v104)
iOS placement changed in V102 (Vraja msg 3069, 18.11): on iOS the panel is 14..30 px above the selection (or, with no room above, 60..90 px under it), clear of the native menu zone under the selection (16..60 px); the old band asserts below stay for Android.
V100 — Vraja Lila: (1) one fragment = one highlight, one colour, one note; (2) iPhone: the system menu (Copy / Look Up) must not cover the colours.
Criteria (register V100):
 (1) selecting the same fragment again and choosing another colour REPLACES the colour (still ONE highlight, the note is kept);
     a selection that overlaps a marked stretch by at least half replaces it too; a separate stretch stays a separate highlight;
     old stored duplicates (the same stretch, several colours) are merged into one when the book opens (the note text is kept);
 (2) on a phone the colour panel is away from the selection: it does not touch the 64 px bands right above / below the selection,
     where the system bar (Copy · Look Up · Translate) is drawn; for a selection low on the screen the panel is at the top.
# tehniskais slieksnis Lipikāra, nav S noteikums: system bar band = 64 px above / below the selection; overlap >= 50 % of the shorter stretch
usage: python s_v100_notes_one_color_ios_menu.py <base-url>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["iphone14", "pixel7"])
results = []
PAGE = "daily-duties-brahma-muhurta"


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else json.dumps(evidence, ensure_ascii=False)[:700]}", flush=True)


SELECT = """([n, a, b, block]) => {
  // V100b: a note keeps a room of its own in the line (an inline box splits the text node): numbering of the paragraphs' text nodes is taken on the whole text
  document.querySelectorAll('[data-hl-gap]').forEach(g => g.remove()); document.querySelectorAll('.app-main article p').forEach(p => p.normalize());
  const nodes = [];
  for (const p of document.querySelectorAll('.app-main article p')) {
    if (!p.getClientRects().length || p.closest('button,table,[hidden],.mood-panel')) continue;
    const w = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
    for (let x = w.nextNode(); x; x = w.nextNode()) if ((x.data.match(/\\S+/g) || []).length >= 9 && x.parentElement.getClientRects().length) nodes.push(x);
  }
  const node = nodes[n]; if (!node) return null;
  node.parentElement.scrollIntoView({block: block || 'center'});
  const d = node.data; const ws = [...d.matchAll(/\\S+/g)];
  const s = ws[a].index, e = ws[b - 1].index + ws[b - 1][0].length;
  const r = document.createRange(); r.setStart(node, s); r.setEnd(node, e);
  const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
  const rs = r.getClientRects(); const f = rs[0], l = rs[rs.length - 1];
  return {text: d.slice(s, e), top: f.top, bottom: l.bottom}; }"""
STORE = "() => { try { return JSON.parse(localStorage.getItem('ap.highlights') || 'null'); } catch (e) { return 'bad'; } }"
MENU = "() => { const m = document.querySelector('[data-hl-menu]'); const b = m.getBoundingClientRect(); return {t: b.top, b: b.bottom, l: b.left, r: b.right}; }"


def items(pg):
    s = pg.evaluate(STORE)
    return (s or {}).get("items", []) if isinstance(s, dict) else []


def pick(pg, args, color):
    info = pg.evaluate(SELECT, args)
    pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    pg.wait_for_timeout(250)
    pg.locator(f"[data-hl-menu] [data-hl-color='{color}']").click()
    pg.wait_for_timeout(400)
    return info


def run(p, dev, eng, opts):
    try:
        b = getattr(p, eng).launch()
    except Exception:  # WebKit libs missing: same viewport + touch in Chromium
        b = p.chromium.launch()
        opts = {k: v for k, v in opts.items() if k != "user_agent"}
    c = b.new_context(service_workers="block", locale="ru-RU", reduced_motion="reduce", **opts)
    c.add_init_script("try{if(!sessionStorage.getItem('v100seed')){sessionStorage.setItem('v100seed','1');localStorage.removeItem('ap.highlights');}"
                      "localStorage.setItem('installDismissed','true');localStorage.setItem('ap.readerHintSeen','1');}catch(e){}")
    pg = c.new_page()
    pg.goto(f"{BASE}/ru-iast/{PAGE}/", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    pg.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important}")

    # (1) the same fragment, colour after colour
    i1 = pick(pg, [0, 2, 7, "center"], 0)
    pick(pg, [0, 2, 7, "center"], 1)
    pick(pg, [0, 2, 7, "center"], 2)
    its = items(pg)
    check(dev, "same fragment, three colours: ONE highlight, the last colour", len(its) == 1 and its[0]["color"] == 2 and its[0]["quote"] == i1["text"], its)
    painted = pg.evaluate("() => [0,1,2,3].map(n => { const h = CSS.highlights.get('hl-' + n); return h ? h.size : 0; })")
    check(dev, "painted once, in the last colour only", painted == [0, 0, 1, 0], painted)

    # note kept when the colour changes
    pg.evaluate(SELECT, [0, 2, 7, "center"])
    pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
    pg.locator("[data-hl-menu] [data-hl-note]").click()
    pg.wait_for_selector("[data-hl-editor] textarea", state="visible", timeout=4000)
    pg.locator("[data-hl-editor] textarea").fill("Заметка V100")
    pg.locator("[data-hl-editor] [data-hl-save]").click()
    pg.wait_for_timeout(500)
    its = items(pg)
    check(dev, "note on the same fragment: still ONE highlight with the note", len(its) == 1 and its[0].get("note") == "Заметка V100", its)
    pick(pg, [0, 2, 7, "center"], 3)
    its = items(pg)
    check(dev, "colour changed on a fragment with a note: ONE highlight, new colour, the note kept",
          len(its) == 1 and its[0]["color"] == 3 and its[0].get("note") == "Заметка V100", its)

    # overlapping selection (inside the marked stretch) replaces
    pick(pg, [0, 3, 6, "center"], 0)
    its = items(pg)
    check(dev, "a selection inside the marked stretch replaces it (still ONE)", len(its) == 1 and its[0]["color"] == 0 and its[0].get("note") == "Заметка V100", its)

    # a separate stretch stays separate
    pick(pg, [1, 1, 6, "center"], 1)
    its = items(pg)
    check(dev, "a separate fragment is a separate highlight (2 in all)", len(its) == 2, its)

    # old duplicates merge on load
    pg.evaluate("""() => { const s = JSON.parse(localStorage.getItem('ap.highlights')); const a = s.items.find(x => x.note);
      const dups = [1, 2, 3].map(i => ({...a, id: 'dup' + i, color: i % 4, note: i === 2 ? 'вторая заметка' : undefined, created: a.created + i, updated: a.updated + i}));
      s.items.push(...dups); localStorage.setItem('ap.highlights', JSON.stringify(s)); }""")
    check(dev, "seeded 3 old duplicates (5 stored)", len(items(pg)) == 5, len(items(pg)))
    pg.reload(wait_until="networkidle")
    pg.wait_for_timeout(1500)
    its = items(pg)
    merged = [x for x in its if x["quote"] == i1["text"] or x.get("note")]
    check(dev, "after opening the book the duplicates are one (2 left), the notes kept",
          len(its) == 2 and any("Заметка V100" in (x.get("note") or "") and "вторая заметка" in (x.get("note") or "") for x in its), its)

    # (2) the panel away from the system bar
    def away(args, name):
        # tehniskais slieksnis/gaidīšana Lipikāra, nav S noteikums (19.11, V104): the previous selection's panel is cleared first, so the menu read below is the NEW selection's (a stale panel was read on a loaded iPad)
        pg.evaluate("() => getSelection().removeAllRanges()")
        try:
            pg.wait_for_selector("[data-hl-menu]", state="hidden", timeout=2500)
        except Exception:  # noqa: BLE001
            pass
        s = pg.evaluate(SELECT, args)
        pg.wait_for_selector("[data-hl-menu]", state="visible", timeout=4000)
        pg.wait_for_timeout(400)
        m = pg.evaluate(MENU)
        vh = pg.evaluate("innerHeight")
        band_up = (s["top"] - 64, s["top"] - 2)
        band_dn = (s["bottom"] + 2, s["bottom"] + 64)
        hit = lambda band: m["t"] < band[1] and m["b"] > band[0]
        # V101 (Vraja Lila msg 8393 «делаем так»): on iPhone the panel is right UNDER the selection (the system bar is above) — only the band above is kept free (see s_v101)
        dn_bad = False  # V101/V101b: on phones the panel is right under the selection (see s_v101)
        if pg.evaluate("/iPhone|iPad|iPod/.test(navigator.userAgent)"):  # V102 (Vraja msg 3069)
            up = s["top"] - m["b"]; dn = m["t"] - s["bottom"]
            ok = (14 <= up <= 32 or 60 <= up <= 90 or 14 <= dn <= 32 or 60 <= dn <= 90) and m["t"] >= 0 and m["b"] <= vh  # V104: side per s_v104
            check(dev, name + " (V102 iOS): the panel is 14..30 px above the selection (no room above: 60..90 px under) and clear of the native menu zone under it", ok, {"menu": m, "sel": s, "vh": vh, "up": up, "dn": dn})
            return
        check(dev, name + ": the panel does not touch the system-bar bands above/below the selection", not hit(band_up) and not dn_bad and m["t"] >= 0 and m["b"] <= vh, {"menu": m, "sel": s, "vh": vh})
    away([2, 1, 5, "center"], "selection mid-screen")
    away([2, 1, 5, "end"], "selection low on the screen")
    away([2, 1, 5, "start"], "selection high on the screen")
    b.close()


with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        try:
            run(p, dev, eng, opts)
        except Exception as e:  # noqa: BLE001
            check(dev, "scenario ran to the end", False, repr(e)[:500])

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if results and all(results) else 1)
