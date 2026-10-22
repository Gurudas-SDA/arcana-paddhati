"""КСВ 22.10.2026 (Satkirti msg 6133, verbatim): «не вижу Заключение в айпаде».
«Заключение» was live since 22.10 05:10 (a775b8e); an iPad that had the book stored kept showing the old book.

Acceptance (Satkirti's words, from msg 6133): the new version of the book (here: «Заключение» in «Содержание») is
seen on the iPad that already has the book stored — after opening the book again, and when the book is brought
back from the background — without waiting for the whole new version to download.

Measured 22.10.2026 (WebKit iPad, the 21.10 build d6bbb71 stored, then the 406252a build served): with the
first byte after 4 s (poor wifi) 5 reloads in 104 s all showed the OLD contents (the old worker answered its
stored page after its 3 s cut while the new version was installing); brought back from the background
(visibilitychange) the page reloaded itself only when the new version had its core: +176 s at 200 KB/s,
+856 s at 40 KB/s.

Scenario: release A (out/) opened online -> the whole book stored -> release B is published (a new sw.js
version; every page and RSC payload has a new hash, the ru-iast cover carries a marker) -> every answer's
first byte comes after QA_TTFB_MS (4000; # tehniskais slieksnis Lipikāra, nav S noteikums):
  1) reload, read 15 s (the first open tells the browser about B), reload again: the second shows B;
  2) after that first open + 15 s, the book closed and opened again (a new page): shows B;
  3) the book brought back from the background (no reload by the reader): the page shows B by itself
     within QA_RESUME_BUDGET_S (60 s; # tehniskais slieksnis Lipikāra, nav S noteikums) — before, only after
     the new version's core was downloaded (233 files of ru-iast).
usage: python s92_update_reaches_open_book.py <base-url>   (the base is ignored: own server on out/)
devices: QA_DEVICES (default ipad-portrait)"""
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

TTFB = float(os.environ.get("QA_TTFB_MS", "4000")) / 1000
# the reader stays on the page a little before the next open (the browser checks sw.js meanwhile)
READ_MS = int(os.environ.get("QA_READ_MS", "15000"))  # tehniskais slieksnis Lipikāra, nav S noteikums
RESUME_BUDGET = float(os.environ.get("QA_RESUME_BUDGET_S", "60"))
DEVICES = qa.devices(["ipad-portrait"])
L = "ru-iast"
MARK = '<meta name="qa-release" content="B">'
res = []


def chk(dev, name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {info}", flush=True)


class Handler(http.server.SimpleHTTPRequestHandler):
    release = "A"
    version = None
    ttfb = 0.0

    def translate_path(self, path):
        p = path.split("?", 1)[0].split("#", 1)[0]
        if p.startswith(qa.PREFIX):
            p = p[len(qa.PREFIX):] or "/"
        return super().translate_path(p)

    def end_headers(self):
        # GitHub Pages: every file max-age=600
        self.send_header("Cache-Control", "max-age=600")
        super().end_headers()

    def do_GET(self):
        if self.ttfb:
            time.sleep(self.ttfb)
        name = self.path.split("?", 1)[0]
        if self.release == "B":
            if name.endswith(("/sw.js", "/precache-manifest.json")):
                return self._release(name)
            if name in (f"{qa.PREFIX}/{L}/", f"{qa.PREFIX}/{L}/index.html"):
                return self._marked(name)
        return super().do_GET()

    def _send(self, data, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _marked(self, name):
        body = open(self.translate_path(name if name.endswith(".html") else name + "index.html"), encoding="utf-8").read()
        self._send(body.replace("</head>", MARK + "</head>", 1).encode("utf-8"), "text/html; charset=utf-8")

    def _release(self, name):
        body = open(self.translate_path(name), encoding="utf-8").read()
        v = self.version
        if name.endswith(".json"):
            m = json.loads(body)
            m["version"] = v + "b"
            m["hashes"] = [h + "b" if (u.endswith("/") or u.endswith(".txt")) else h for u, h in zip(m["urls"], m["hashes"])]
            self._send(json.dumps(m).encode("utf-8"), "application/json")
        else:
            self._send(body.replace(v, v + "b").encode("utf-8"), "application/javascript")

    def log_message(self, *a):
        pass


class Srv(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (ConnectionError, BrokenPipeError, TimeoutError)):
            return
        super().handle_error(request, client_address)


STATE = """async () => { const r = await navigator.serviceWorker.getRegistration();
  const out = {ctrl: !!navigator.serviceWorker.controller, installing: !!(r && r.installing), waiting: !!(r && r.waiting), caches: {}};
  for (const k of await caches.keys()) { if (!k.startsWith('arcana-paddhati-')) continue;
    out.caches[k] = !!(await (await caches.open(k)).match('/arcana-paddhati/__precache-complete__')); }
  return out; }"""


def is_b(pg):
    try:
        return pg.evaluate("!!document.querySelector('meta[name=qa-release]')")
    except Exception:
        return False


def store_a(pg, base, dev):
    pg.goto(f"{base}/{L}/", wait_until="load")
    pg.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller", timeout=120000)
    t0 = time.time()
    st = None
    while time.time() - t0 < 600:
        st = pg.evaluate(STATE)
        if any(st["caches"].values()):
            break
        pg.wait_for_timeout(2000)
    ok = bool(st and any(st["caches"].values()))
    # the reader's page of every later day: opened with the book already stored (a controlled page)
    pg.reload(wait_until="load")
    pg.wait_for_timeout(1500)
    ok = ok and pg.evaluate("!!navigator.serviceWorker.controller")
    chk(dev, "setup: release A stored whole, page opened from the stored book", ok, f"{time.time() - t0:.0f}s")
    return ok


def scenario(p, dev, eng, o, kind):
    version = json.load(open(os.path.join(qa.OUT, "precache-manifest.json"), encoding="utf-8"))["version"]
    H = type("H", (Handler,), {"version": version, "release": "A", "ttfb": 0.0})
    port = qa_server.free_port()
    httpd = Srv(("127.0.0.1", port), functools.partial(H, directory=qa.OUT))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}{qa.PREFIX}"
    b = getattr(p, eng).launch()
    c = b.new_context(locale="ru-RU", service_workers="allow", **o)
    c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
    pg = c.new_page()
    try:
        if not store_a(pg, base, dev):
            return
        chk(dev, f"{kind}: release A has no marker", not is_b(pg))
        H.release, H.ttfb = "B", TTFB
        t0 = time.time()
        if kind == "reload":
            seen = []
            for i in range(2):
                pg.reload(wait_until="load", timeout=120000)
                pg.wait_for_timeout(READ_MS if i == 0 else 3000)
                seen.append(is_b(pg))
            chk(dev, "1) slow first byte: the 2nd reload shows the new version", seen[-1],
                f"reloads={seen} +{time.time() - t0:.0f}s {pg.evaluate(STATE)}")
        elif kind == "reopen":
            pg.reload(wait_until="load", timeout=120000)  # the first open tells the browser about B
            pg.wait_for_timeout(READ_MS)
            pg.close()
            pg = c.new_page()
            pg.goto(f"{base}/{L}/", wait_until="load", timeout=120000)
            pg.wait_for_timeout(3000)
            chk(dev, "2) slow first byte: the book closed and opened again shows the new version", is_b(pg),
                f"+{time.time() - t0:.0f}s {pg.evaluate(STATE)}")
        else:
            loads = []
            pg.on("load", lambda: loads.append(round(time.time() - t0)))
            pg.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))")
            ok = False
            while time.time() - t0 < RESUME_BUDGET:
                pg.wait_for_timeout(2000)
                if is_b(pg):
                    ok = True
                    break
            chk(dev, f"3) brought back from the background: the new version by itself ≤ {RESUME_BUDGET:.0f} s", ok,
                f"+{time.time() - t0:.0f}s reloads at {loads} {pg.evaluate(STATE)}")
    finally:
        b.close()
        httpd.shutdown()


with sync_playwright() as p:
    for dev, eng, o in DEVICES:
        for kind in os.environ.get("QA_S92_ONLY", "reload,reopen,resume").split(","):
            try:
                scenario(p, dev, eng, o, kind)
            except Exception as e:
                chk(dev, f"{kind}: no error", False, str(e)[:300])

print(f"{sum(res)}/{len(res)} PASS")
sys.exit(0 if res and all(res) else 1)
