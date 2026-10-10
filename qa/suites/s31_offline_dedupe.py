"""A71 (10.10.2026): the offline cache (SW precache) without duplicates — and offline still works.
Satkirti's law 06.10: after the first visit EVERYTHING works offline (iPad/iPhone/Android/computer).

Measured before (out/lv: 26 pages, ~20 MB in the manifest): every page stored index.html (~300–440 KB)
AND index.txt (the full RSC payload, byte-identical to the flight chunks already inlined in index.html)
AND __next._index.txt (the root layout with the whole contents, ~180 KB, the SAME bytes on every page).
Now (scripts/build-precache.mjs + public/sw.js):
  * index.txt is not downloaded: the worker rebuilds it offline from the cached page's inline
    `self.__next_f.push([1,"…"])` chunks (the client asks for it when a link is followed before its
    segment prefetch finished — e.g. «След. глава»);
  * byte-identical files of one download group (same extension) are stored once; the manifest's
    `aliases` {url: canonical url} let the worker answer the others from the canonical copy.

A  size: for every language the manifest holds ≤ 60 % of the bytes of that language's files in out/
   (pages + RSC payloads + search index; __next._full.txt never counted — it was never precached).
B  no file lost: every out/ file of the book is in the manifest, or an alias of a byte-identical
   manifest file, or an index.txt equal to its index.html's inline flight chunks (Python mirror of sw.js).
C  browser, offline (chromium: context offline; webkit: the suite's own server killed): after the first
   visit (precache complete) every index.txt and every aliased file of lv + ru-iast answers through the
   worker with the exact bytes of out/; chromium also: 5 chapters × 2 languages open by direct URL,
   from «Содержание» (two taps), «След. глава ›» (client navigation, needs index.txt) and «Назад».
usage: python s31_offline_dedupe.py <base> [chromium|webkit]
"""
import collections
import hashlib
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
import server as qa_server  # noqa: E402

ENG = sys.argv[2] if len(sys.argv) > 2 else "chromium"
LANGS = ["lv", "ru-iast"]
LANG_DIRS = ["ru", "ru-iast", "lv", "de", "fr", "es", "it", "uk", "hu"]
LIMIT = 0.60
res = []


def ck(name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {ENG} {name} {'' if ok else info}", flush=True)


man = json.load(open(os.path.join(qa.OUT, "precache-manifest.json"), encoding="utf-8"))
P = qa.PREFIX + "/"
aliases = man.get("aliases", {})


def url_file(u):
    rel = u[len(P):]
    if rel == "" or rel.endswith("/"):
        rel += "index.html"
    return os.path.join(qa.OUT, *rel.split("/"))


def rel_url(rel):
    return P + (rel[:-len("index.html")] if rel.endswith("index.html") else rel)


FLIGHT = re.compile(r'<script[^>]*>self\.__next_f\.push\((\[[\s\S]*?\])\)</script>')


def flight_from_html(path):
    out = []
    for m in FLIGHT.finditer(open(path, encoding="utf-8").read()):
        a = json.loads(m.group(1))
        if a[0] == 1:
            out.append(a[1])
        elif a[0] != 0:
            return None
    return "".join(out).encode("utf-8") if out else None


def lang_of(rel):
    if rel.startswith("search-index."):
        return rel[len("search-index."):-len(".json")]
    first = rel.split("/")[0]
    return first if first in LANG_DIRS and "/" in rel else None


# ---------- A + B (static) ----------
if ENG == "chromium":
    inman = set(man["urls"])
    size = collections.Counter()
    for u, g in zip(man["urls"], man["groups"]):
        size[g] += os.path.getsize(url_file(u))
    full = collections.Counter()
    lost = []
    for dp, _, fs in os.walk(qa.OUT):
        for f in fs:
            rel = os.path.relpath(os.path.join(dp, f), qa.OUT).replace(os.sep, "/")
            if f == "desktop.ini" or f.endswith(".map") or f == "__next._full.txt" or rel in ("sw.js", "precache-manifest.json"):
                continue
            if rel == "404.html" or rel.startswith(("404/", "_not-found/")):
                continue
            lg = lang_of(rel)
            if lg:
                full[lg] += os.path.getsize(os.path.join(dp, f))
            u = rel_url(rel)
            if u in inman:
                continue
            if u in aliases:
                same = open(os.path.join(dp, f), "rb").read() == open(url_file(aliases[u]), "rb").read()
                if not same:
                    lost.append(u + " (alias differs)")
                continue
            if f == "index.txt" and os.path.exists(os.path.join(dp, "index.html")):
                if flight_from_html(os.path.join(dp, "index.html")) != open(os.path.join(dp, f), "rb").read():
                    lost.append(u + " (not rebuildable from index.html)")
                continue
            lost.append(u)
    for lg in LANG_DIRS:
        r = size[lg] / full[lg] if full[lg] else 1
        ck(f"A size {lg}: manifest {size[lg] / 1e6:.2f} MB of {full[lg] / 1e6:.2f} MB = {r:.0%} (≤ {LIMIT:.0%})", r <= LIMIT)
    print(f"  [INFO] {ENG} manifest total {man['bytes'] / 1e6:.1f} MB, {len(man['urls'])} URLs, {len(aliases)} aliases", flush=True)
    ck(f"B no file lost (manifest / alias of identical bytes / index.txt rebuildable): {len(lost)} lost", not lost, lost[:5])

# ---------- C (browser, offline) ----------
from playwright.sync_api import sync_playwright  # noqa: E402

SRV = None
if ENG == "webkit":
    port = qa_server.free_port()
    SRV = subprocess.Popen([sys.executable, os.path.join(qa.QA_DIR, "lib", "server.py"), str(port)])
    time.sleep(1.5)
    BASE = f"http://127.0.0.1:{port}{qa.PREFIX}"
else:
    BASE = sys.argv[1].rstrip("/")
ORIGIN = BASE[: -len(qa.PREFIX)]


def sha(path):
    return hashlib.sha1(open(path, "rb").read()).hexdigest()


# what the client may ask for offline: every page's index.txt + every alias, of the two languages
want = {}
for lg in LANGS:
    for u, g in zip(man["urls"], man["groups"]):
        if g == lg and u.endswith("/"):
            want[u + "index.txt"] = sha(os.path.join(url_file(u)[: -len("index.html")], "index.txt"))
    for a in aliases:
        if a.startswith(P + lg + "/"):
            want[a] = sha(url_file(a))

COMPLETE = """async()=>{for(const k of await caches.keys()){if(!k.startsWith('arcana-paddhati-'))continue;
  const c=await caches.open(k);if(await c.match('/arcana-paddhati/__precache-complete__'))return true}return false}"""
FETCH = """async(w)=>{const bad=[];for(const [u,h] of Object.entries(w)){try{const x=await fetch(u+'?_rsc=q',{headers:{RSC:'1'}});
  const b=await x.arrayBuffer();const d=[...new Uint8Array(await crypto.subtle.digest('SHA-1',b))].map(v=>v.toString(16).padStart(2,'0')).join('');
  if(x.status!==200||d!==h)bad.push(u+' '+x.status)}catch(e){bad.push(u+' '+e)}}return bad}"""
SHOWN = "() => !!(document.querySelector('.app-main h1')||document.querySelector('.app-main img')) && !/не сохранена|not yet stored/.test(document.body.innerText)"

with sync_playwright() as p:
    b = getattr(p, ENG).launch()
    o = qa.DEVICES["pixel7" if ENG == "chromium" else "iphone14"][1]
    c = b.new_context(service_workers="allow", **o)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    pg = c.new_page()
    t0 = time.time()
    pg.goto(BASE + "/lv/", wait_until="load")
    pg.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller", timeout=120000)
    done = False
    while time.time() - t0 < 420:
        done = pg.evaluate(COMPLETE)
        if done:
            break
        pg.evaluate("navigator.serviceWorker.controller&&navigator.serviceWorker.controller.postMessage({type:'precache-continue'})")
        pg.wait_for_timeout(4000)
    ck(f"C first visit: precache complete ({time.time() - t0:.0f}s)", done)
    if SRV:
        SRV.kill(); SRV.wait(); time.sleep(0.5)
    else:
        c.set_offline(True)
    bad = pg.evaluate(FETCH, want)
    ck(f"C offline: {len(want)} index.txt + aliased payloads (lv, ru-iast) answer with the exact bytes of out/", not bad, bad[:4])
    if ENG == "chromium":
        touch = o.get("has_touch", False)

        def menu():
            return pg.locator(".mobile-menu").count() == 1

        def contents():
            for _ in range(4):
                if menu():
                    return
                if pg.locator(".reader-chrome[data-shown]").count() == 0:
                    vw = pg.viewport_size
                    (pg.touchscreen.tap if touch else pg.mouse.click)(vw["width"] - 6, vw["height"] / 2)
                    pg.wait_for_timeout(450)
                try:
                    btn = pg.locator("[data-reader-action=contents]")
                    btn.tap(timeout=3000) if touch else btn.click(timeout=3000)
                except Exception:
                    pass
                pg.wait_for_timeout(800)

        for lg in LANGS:
            chapters = [u for u, g in zip(man["urls"], man["groups"]) if g == lg and u.endswith("/") and u.count("/") == 4][:5]
            badd = []
            for u in chapters:
                try:
                    pg.goto(ORIGIN + u, wait_until="load", timeout=20000)
                    pg.wait_for_timeout(300)
                    if not pg.evaluate(SHOWN) or not pg.url.endswith(u):
                        badd.append(u)
                except Exception as e:
                    badd.append(u + " " + str(e)[:60])
            ck(f"C offline {lg}: 5 chapters open by direct URL", not badd, badd)
            # «Содержание» → a chapter of another page (two taps)
            start = chapters[0]
            pg.goto(ORIGIN + start, wait_until="load")
            pg.wait_for_timeout(800)
            contents()
            rid = pg.evaluate("""(cur)=>{const r=[...document.querySelectorAll('.mobile-menu nav a[data-toc-row^="sec:"]')]
              .find(a=>new URL(a.href).pathname!==cur);return r?r.getAttribute('data-toc-row'):null}""", start)
            ok_toc = False
            target = None
            pg.evaluate("window.__spa = 1")   # survives only a client navigation (no full page load)
            if rid:
                row = pg.locator(f".mobile-menu nav [data-toc-row='{rid}']")
                target = pg.evaluate(f"() => new URL(document.querySelector(\".mobile-menu nav [data-toc-row='{rid}']\").href).pathname")
                row.scroll_into_view_if_needed()
                for _ in range(2):
                    row.tap() if touch else row.click()
                    pg.wait_for_timeout(500)
                try:
                    pg.wait_for_function(f"() => location.pathname === {target!r} && !document.querySelector('.mobile-menu')", timeout=15000)
                    pg.wait_for_timeout(500)
                    ok_toc = pg.evaluate(SHOWN) and pg.evaluate("window.__spa === 1")
                except Exception:
                    pass
            ck(f"C offline {lg}: «Содержание» → {target} opens (client navigation, no reload)", ok_toc, pg.url)
            # «След. глава ›» (client navigation; the router asks for index.txt)
            before = pg.url
            pg.evaluate("window.__spa = 1")
            pg.evaluate("document.querySelector('.app-main').scrollTop=1e9")
            pg.wait_for_timeout(500)
            pg.evaluate("document.querySelector('[data-chapter-next]')&&document.querySelector('[data-chapter-next]').click()")
            try:
                pg.wait_for_function(f"() => location.href !== {before!r}", timeout=10000)
                pg.wait_for_timeout(1500)
                ok_next = pg.evaluate(SHOWN) and pg.evaluate("window.__spa === 1")
            except Exception:
                ok_next = False
            ck(f"C offline {lg}: «След. глава ›» opens the next chapter (client navigation, no reload)", ok_next, pg.url)
            # «Назад»
            pg.go_back()
            pg.wait_for_timeout(1500)
            ck(f"C offline {lg}: «Назад» returns to {target}", pg.url.split("#")[0].endswith(target or "?") and pg.evaluate(SHOWN), pg.url)
    b.close()
print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
