"""КСВ 15.10.2026 (Satkirti, iPad, India, slow hotel wifi): «Содержание» → «1.2. Совершите омовение» — the row
says «загружается», the cover stays; at the same time the panel shows «Книга сохраняется для чтения без
интернета: 76 %». The book WAS fully stored before («А зачем ей загружаться»).

Scenario (the real one): release A opened online → the whole book stored (complete cache) → a new release B is
published (as a real build: every page and RSC payload has a new hash, Next.js's build id is in each of them)
→ the network is slow (QA_SLOW_KBPS, default 200 KB/s ≈ 1.6 Mbit/s, QA_SLOW_MS latency 150 ms, shared by all
requests like one wifi link) → the page is reloaded, worker B installs and downloads in the background →
the reader opens the contents and taps a chapter.

Acceptance (Satkirti's words): «Нажал на главу — она открылась сразу, даже пока книга ещё сохраняется для
чтения без интернета»:
  1) the tapped chapter is shown (URL + heading, contents closed) ≤ QA_OPEN_BUDGET_S (2 s) after the tap;
  2) an update downloads only what changed: after release C (a text edit in one chapter) the download is at
     most QA_UPDATE_MB (5 MB) — not the whole book in every language again (274 of 298 MB, 2458 of 2672
     files: Next.js's random build id was in every page and RSC payload; scripts/stable-build-id.mjs);
  3) the network drops during the tap (server gone, nothing cached for the chapter is not the case here —
     the chapter IS stored): the chapter still opens from the stored book.
usage: python s40_chapter_during_update.py <base-url>   (the base is ignored: the suite runs its OWN
       throttled server on out/, like s20 webkit)   devices: QA_DEVICES (default ipad-portrait, iphone14)"""
import functools
import http.server
import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
import server as qa_server  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

KBPS = float(os.environ.get("QA_SLOW_KBPS", "200"))
LAT = float(os.environ.get("QA_SLOW_MS", "150")) / 1000
BUDGET = float(os.environ.get("QA_OPEN_BUDGET_S", "2"))
UPDATE_MB = float(os.environ.get("QA_UPDATE_MB", "5"))
DEVICES = qa.devices(["ipad-portrait", "iphone14"])
L = "ru-iast"
res = []


def stable_build_id():
    """(id in out/, id derived from the client code as scripts/stable-build-id.mjs does it)."""
    import base64
    import hashlib
    static = os.path.join(qa.OUT, "_next", "static")
    ids = [n for n in sorted(os.listdir(static)) if n not in ("chunks", "media") and os.path.isdir(os.path.join(static, n))]

    def files(d, prefix=""):
        out = []
        for n in sorted(os.listdir(d)):
            p = os.path.join(d, n)
            out += files(p, prefix + n + "/") if os.path.isdir(p) else [prefix + n]
        return out
    h = hashlib.sha256()
    for sub in ("chunks", "media"):
        d = os.path.join(static, sub)
        if os.path.isdir(d):
            for rel in files(d):
                h.update((sub + "/" + rel).encode()); h.update(b"\0")
                h.update(open(os.path.join(d, rel), "rb").read()); h.update(b"\0")
    want = base64.urlsafe_b64encode(h.digest()).decode().rstrip("=")[:21]
    return (ids[0] if len(ids) == 1 else ids), want


_have, _want = stable_build_id()
STABLE_ID = _have == _want


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {info}", flush=True)


class Link:
    """One shared slow link (token bucket): every response body is sent in chunks paced by it."""

    def __init__(self):
        self.rate = 0.0  # bytes/s; 0 = unlimited
        self.lat = 0.0
        self.lock = threading.Lock()
        self.next_free = 0.0
        self.bytes = 0
        self.files = 0
        self.down = False

    def send(self, n):
        with self.lock:
            self.bytes += n
            if not self.rate:
                return 0.0
            now = time.time()
            start = max(now, self.next_free)
            self.next_free = start + n / self.rate
            return self.next_free - now


class Handler(http.server.SimpleHTTPRequestHandler):
    link = None
    release = "A"
    version = None

    def translate_path(self, path):
        p = path.split("?", 1)[0].split("#", 1)[0]
        if p.startswith(qa.PREFIX):
            p = p[len(qa.PREFIX):] or "/"
        return super().translate_path(p)

    def end_headers(self):
        if self.path.split("?")[0].endswith(("sw.js", "precache-manifest.json")):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        if self.link.down:
            self.close_connection = True
            return
        if self.link.lat:
            time.sleep(self.link.lat)
        name = self.path.split("?", 1)[0]
        if name.endswith(("/sw.js", "/precache-manifest.json")) and self.release != "A":
            return self._release(name)
        self.link.files += 1
        return super().do_GET()

    def _release(self, name):
        """B = a release that changes the client code: a new version, every page / RSC payload gets a new hash
        (the build id in each changes); build assets, pictures, transcripts unchanged.
        C (after B) = a text edit in ONE chapter (ru-iast «Порядок подношения бхоги»): only that chapter's files
        change — IF the build id is stable (out/ built with scripts/stable-build-id.mjs); with Next.js's random
        id every page / RSC payload changes again, as every real rebuild did before."""
        body = open(self.translate_path(name), "rb").read().decode("utf-8")
        v = self.version
        suffix = "b" if self.release == "B" else "bc"
        if name.endswith(".json"):
            m = json.loads(body)
            m["version"] = v + suffix
            out = []
            for u, h in zip(m["urls"], m["hashes"]):
                page = u.endswith("/") or u.endswith(".txt")
                if page:
                    h += "b"
                    if self.release == "C" and (not STABLE_ID or f"/{L}/offering-bhoga/" in u):
                        h += "c"
                out.append(h)
            m["hashes"] = out
            body = json.dumps(m)
        else:
            body = body.replace(v, v + suffix)
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/javascript" if name.endswith(".js") else "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def copyfile(self, source, outputfile):
        while True:
            buf = source.read(16384)
            if not buf:
                return
            wait = self.link.send(len(buf))
            if wait > 0:
                time.sleep(wait)
            outputfile.write(buf)

    def log_message(self, *a):
        pass


class Srv(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (ConnectionError, BrokenPipeError, TimeoutError)):
            return
        super().handle_error(request, client_address)


def start_server():
    link = Link()
    version = json.load(open(os.path.join(qa.OUT, "precache-manifest.json"), encoding="utf-8"))["version"]
    H = type("H", (Handler,), {"link": link, "version": version})
    port = qa_server.free_port()
    httpd = Srv(("127.0.0.1", port), functools.partial(H, directory=qa.OUT))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, H, link, f"http://127.0.0.1:{port}{qa.PREFIX}"


STATE = """async () => { const out = {caches: {}, ctrl: null};
  try { const r = await navigator.serviceWorker.getRegistration();
    out.active = r && r.active ? r.active.scriptURL : null; out.waiting = !!(r && r.waiting); out.installing = !!(r && r.installing); } catch (e) {}
  for (const k of await caches.keys()) { if (!k.startsWith('arcana-paddhati-')) continue; const c = await caches.open(k);
    out.caches[k] = {n: (await c.keys()).length, complete: !!(await c.match('/arcana-paddhati/__precache-complete__'))}; }
  out.ctrl = !!navigator.serviceWorker.controller; return out; }"""

PROGRESS = """() => { window.__prog = []; navigator.serviceWorker.addEventListener('message', e => {
  if (e.data && e.data.type === 'precache-progress') window.__prog.push(Object.assign({t: performance.now()}, e.data)); }); }"""


def run(p, dev, eng, o):
    httpd, H, link, base = start_server()
    b = getattr(p, eng).launch()
    c = b.new_context(locale="ru-RU", service_workers="allow", **o)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    touch = o.get("has_touch", False)
    pg = c.new_page()
    try:
        # ---- release A, fast network: the whole book stored ----
        pg.goto(f"{base}/{L}/", wait_until="load")
        pg.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller", timeout=120000)
        pg.evaluate("navigator.serviceWorker.controller.postMessage({type:'precache-continue'})")
        t0 = time.time()
        st = None
        while time.time() - t0 < 600:
            st = pg.evaluate(STATE)
            if any(v["complete"] for v in st["caches"].values()):
                break
            pg.wait_for_timeout(2000)
        full = st and any(v["complete"] for v in st["caches"].values())
        chk(dev, "setup: release A — the whole book stored (complete cache)", full, f"{time.time() - t0:.0f}s {st}")
        if not full:
            return
        # ---- release B published, slow network ----
        H.release = "B"
        link.rate, link.lat = KBPS * 1024, LAT
        link.bytes = 0
        pg.goto(f"{base}/{L}/", wait_until="load", timeout=120000)
        pg.evaluate(PROGRESS)
        # worker B takes over (as on Satkirti's iPad: the panel showed the download progress)
        t1 = time.time()
        while time.time() - t1 < 600:
            st = pg.evaluate(STATE)
            # worker B is active: it posts its progress (version ...b), or its cache is already complete
            if pg.evaluate("(window.__prog || []).some(m => String(m.version).endsWith('b'))") or \
                    any(k.endswith("b") and v["complete"] for k, v in st["caches"].items()):
                break
            pg.wait_for_timeout(1000)
        print(f"  info {dev} release B active after {time.time() - t1:.0f}s, downloaded {link.bytes / 1e6:.1f} MB; {st}", flush=True)
        pg.reload(wait_until="load", timeout=120000)   # page controlled by worker B
        pg.evaluate(PROGRESS)
        pg.wait_for_timeout(3000)
        # ---- the reader: contents → a chapter ----
        def menu():
            return pg.locator(".mobile-menu").count() == 1

        def contents():
            for _ in range(5):
                if menu():
                    return True
                if pg.locator(".reader-chrome[data-shown]").count() == 0:
                    vw = pg.viewport_size
                    (pg.touchscreen.tap if touch else pg.mouse.click)(vw["width"] - 6, vw["height"] / 2)
                    pg.wait_for_timeout(500)
                btn = pg.locator("[data-reader-action=contents]")
                try:
                    btn.tap(timeout=3000) if touch else btn.click(timeout=3000)
                except Exception:
                    pass
                pg.wait_for_timeout(900)
            return menu()

        def row(rid):
            return pg.locator(f".mobile-menu nav [data-toc-row='{rid}']").first

        def tap(loc):
            loc.scroll_into_view_if_needed(timeout=5000)
            box = loc.bounding_box()
            x, y = box["x"] + min(box["width"] / 2, 80), box["y"] + box["height"] / 2
            (pg.touchscreen.tap if touch else pg.mouse.click)(x, y)

        def reveal(rid, inner):
            """Tap row `rid` (a part / a chapter; one or two taps) until row `inner` is in the contents."""
            for _ in range(4):
                if row(inner).count():
                    return True
                tap(row(rid))
                pg.wait_for_timeout(500)
            return row(inner).count() > 0

        def opened(slug, sub, limit_s):
            """Contents → part I → chapter `slug` → its subsection `sub` (as Satkirti: «1.2. Совершите омовение»).
            Seconds from the tap that starts the load until the chapter is shown (URL, heading, contents
            closed); None = not within limit_s."""
            rid = f"sub:{slug}#{sub}"
            if not (reveal("grp:temple-worship", f"sec:{slug}") and reveal(f"sec:{slug}", rid)):
                return None
            t = time.time()
            for _ in range(3):   # two-tap contents: the 1st tap highlights, the 2nd opens
                tap(row(rid))
                t = time.time()
                pg.wait_for_timeout(200)
                if slug in pg.url or not menu() or pg.locator(".mobile-menu [data-toc-loading]").count():
                    break
            while time.time() - t < limit_s:
                if slug in pg.url and not menu() and pg.locator("main h1").count() > 0:
                    return round(time.time() - t, 2)
                pg.wait_for_timeout(50)
            return None

        prog = pg.evaluate("window.__prog.slice(-1)[0] || null")
        if not contents():
            chk(dev, "setup: contents open", False)
            return
        took = opened("daily-duties-brahma-muhurta", "taking-bath", 30)
        prog2 = pg.evaluate("window.__prog.slice(-1)[0] || null")
        saving = (prog or prog2) and not (prog2 or prog).get("complete")
        chk(dev, f"1 chapter «Совершите омовение» opens ≤ {BUDGET:g} s after the tap while the book is being saved (release B, {KBPS:g} KB/s, {LAT * 1000:.0f} ms)",
            took is not None and took <= BUDGET,
            f"took {took} s (None = not in 30 s); download in progress: {bool(saving)} {prog2}")
        # ---- 3) the network drops: a chapter still opens from the stored book ----
        if contents():
            link.down = True
            took3 = opened("offering-bhoga", "after-lords-meal", 30)
            link.down = False
            chk(dev, f"3 network gone during the download: a stored chapter opens ≤ {BUDGET:g} s", took3 is not None and took3 <= BUDGET, f"took {took3} s")
        # ---- 2) how much an update downloads ----
        def wait_complete(suffix):
            t2 = time.time()
            while time.time() - t2 < 600:
                st = pg.evaluate(STATE)
                if any(k.endswith(suffix) and v["complete"] for k, v in st["caches"].items()):
                    return st
                pg.evaluate("navigator.serviceWorker.controller && navigator.serviceWorker.controller.postMessage({type:'precache-continue'})")
                pg.wait_for_timeout(2000)
            return st
        link.rate = 0  # let release B finish quickly
        st = wait_complete(H.version + "b")
        print(f"  info {dev} release B (client code changed) downloaded {link.bytes / 1e6:.1f} MB in all", flush=True)
        H.release = "C"        # a text edit in one chapter
        link.bytes = 0
        pg.goto(f"{base}/{L}/", wait_until="load", timeout=120000)
        st = wait_complete(H.version + "bc")
        mb = link.bytes / 1e6
        chk(dev, f"2 a text edit in one chapter: the update downloads only the changed files (≤ {UPDATE_MB:g} MB, was the whole book: 274 MB)",
            mb <= UPDATE_MB and any(k.endswith("bc") and v["complete"] for k, v in st["caches"].items()),
            f"{mb:.1f} MB; build id stable: {STABLE_ID} ({_have} vs {_want}); {st}")
    finally:
        b.close()
        httpd.shutdown()
        httpd.server_close()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        print(f"== {dev}", flush=True)
        run(p, dev, eng, o)

print(f"RESULT {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
