"""Every subsection opened from «Содержание» shows its heading at the top of the
screen 3 s after the jump (Satkirti 06.10, v7.1 item 11 / v7.2 verifier "heads").
Ported from the verifier scenario v72/heads2.py.
usage: python s11_headings_after_jump.py <base-url>    devices: QA_DEVICES (touch devices)
QA_FAST=1: only the last subsection of every chapter (the hardest case: end of chapter)."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
U = BASE + "/ru-iast/"
D = json.load(open(os.path.join(qa.DATA, "book.ru-iast.json"), encoding="utf-8"))
SUBS = [(s["id"], ss["id"]) for s in D["sections"] for ss in (s.get("subsections") or [])]
if qa.fast():
    last = {}
    for t in SUBS:
        last[t[0]] = t
    SUBS = list(last.values())
res = []


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {'' if ok else info}", flush=True)


def run(p, dev, eng, o):
    b = getattr(p, eng).launch()
    c = b.new_context(locale="ru-RU", **o)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    pg = c.new_page()

    def bars_shown():
        return pg.evaluate("document.querySelector('[data-reader-action=contents]').getBoundingClientRect().top") >= 0

    def reveal():
        if not bars_shown():
            vp = pg.viewport_size
            pg.touchscreen.tap(8, vp["height"] // 2); pg.wait_for_timeout(700)
            if not bars_shown():
                pg.touchscreen.tap(vp["width"] // 2, vp["height"] // 2); pg.wait_for_timeout(700)

    def open_contents():
        reveal(); pg.locator("[data-reader-action=contents]").tap(); pg.wait_for_timeout(900)

    def tapel(js):
        pg.evaluate("s=>{const e=eval(s); e.scrollIntoView({block:'center'})}", js); pg.wait_for_timeout(250)
        r = pg.evaluate("s=>{const e=eval(s); const r=(e.querySelector('span')||e).getBoundingClientRect(); return [r.left+Math.min(r.width/2,40), r.top+r.height/2]}", js)
        pg.touchscreen.tap(*r); pg.wait_for_timeout(700)

    pg.goto(U + "introduction/", wait_until="networkidle"); pg.wait_for_timeout(1200)
    bad = []
    for ch, sid in SUBS:
        try:
            if not pg.evaluate("!!document.querySelector('.mobile-menu')"):
                try:
                    open_contents()
                except Exception:
                    pg.keyboard.press("Escape"); pg.wait_for_timeout(500); reveal()
                    pg.evaluate("document.querySelector('[data-reader-action=contents]').click()"); pg.wait_for_timeout(900)
            if not pg.evaluate("!!document.querySelector('.mobile-menu')"):
                bad.append((ch, sid, "menu did not open")); continue
            CHB = f"document.querySelector('.mobile-menu [data-toc-chapter=\"{ch}\"]')"
            vis = lambda: pg.evaluate(f"(()=>{{const e={CHB}; return !!(e && e.getClientRects().length)}})()")
            if not vis():
                for gid in pg.evaluate("[...document.querySelectorAll('.mobile-menu [data-toc-group]')].map(g=>g.getAttribute('data-toc-group'))"):
                    if vis():
                        break
                    G = f"document.querySelector('.mobile-menu [data-toc-group=\"{gid}\"]')"
                    if pg.evaluate(f"{G}.getAttribute('aria-expanded')") != "true":
                        tapel(G)
                        if not vis():
                            tapel(G)
            # Two-tap contents (v7.5, Satkirti 07.10): the 1st tap on a chapter only highlights it,
            # the 2nd tap expands it — the same as for the groups above and the subsection below.
            for _ in range(2):
                if pg.evaluate(f"{CHB}.getAttribute('aria-expanded')") == "true":
                    break
                tapel(CHB)
            A = f"document.querySelector('#toc-ch-{ch} a[href*=\"#{sid}\"]')"
            if not pg.evaluate(f"!!{A}"):
                bad.append((ch, sid, "subsection row not found")); pg.keyboard.press("Escape"); continue
            u0 = pg.url
            tapel(A)
            if pg.evaluate("!!document.querySelector('.mobile-menu')") and pg.url == u0:
                tapel(A)  # two-tap contents
            pg.wait_for_timeout(3000)
            st = pg.evaluate(f"""(()=>{{const h=document.getElementById({json.dumps(sid)}); if(!h) return null; const hh=h.querySelector('h1,h2,h3,h4')||h; const r=hh.getBoundingClientRect();
                const pe=document.elementFromPoint(Math.min(innerWidth-2,r.left+20), r.top+Math.min(r.height/2,12)); const visible=!!(pe&&hh.contains(pe));
                return {{visible, top:Math.round(r.top), menu:!!document.querySelector('.mobile-menu'), path:location.pathname.split('/').slice(-2)[0]}}}})()""")
            ok = bool(st) and not st["menu"] and 0 <= st["top"] <= 80 and st["path"] == ch and st["visible"]
            if not ok:
                bad.append((ch, sid, st))
        except Exception as e:
            bad.append((ch, sid, "ERR " + str(e)[:100]))
            try:
                pg.goto(U + "introduction/", wait_until="networkidle"); pg.wait_for_timeout(800)
            except Exception:
                pass
    chk(dev, f"11 contents → subsection: heading at the top after 3 s ({len(SUBS) - len(bad)}/{len(SUBS)})", not bad, str(bad[:5]))
    b.close()


with sync_playwright() as p:
    for dev, eng, o in qa.devices(["pixel7", "s23fe", "iphone14", "ipad-portrait", "ipad-landscape"]):
        print(dev, flush=True)
        try:
            run(p, dev, eng, o)
        except Exception as e:
            chk(dev, "EXCEPTION", False, str(e)[:600])
print()
print(f"{sum(res)}/{len(res)} passed")
