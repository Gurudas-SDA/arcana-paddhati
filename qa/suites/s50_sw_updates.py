"""Service worker: updates arrive by themselves (Vraja Lila msg 5316 p. 2, 20.10.2026; Satkirti's iPad showed
the old Panca-tattva while the new version was not downloaded in full).

Rule text (msg 5316 p. 2, verbatim): «Service worker (берёт управление при частичной загрузке; 1 с — только офлайн;
updateViaCache:'none' + reg.update() + одна перезагрузка при controllerchange).»

Checks:
  A (sw.js) the install never fails on purpose to keep the previous version; skipWaiting always;
  B (sw.js) online navigation is network-first with the normal timeout — no short «stored page» cut;
  C (browser) the registration has updateViaCache 'none';
  D (browser) the page asks for an update (registration.update) on open;
  E (browser) a new worker taking over a page served by an old one reloads the page exactly once.
usage: python s50_sw_updates.py <base-url>
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
DEVICES = qa.devices(["pixel7", "desktop"])
results = []


def check(dev, name, ok, evidence=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


sw = open(os.path.join(qa.REPO, "public", "sw.js"), encoding="utf-8").read()
install = sw[sw.index("self.addEventListener('install'"):sw.index("self.addEventListener('activate'")]
check("src", "A install: no failing on purpose, skipWaiting always",
      "throw" not in install and re.search(r"await precacheCore\([^;]*;\s*await self\.skipWaiting\(\)", install),
      install[:400])
nav = sw[sw.index("async function handleNavigation"):sw.index("async function handleRsc")]
check("src", "B online navigation: network first with NETWORK_TIMEOUT_MS only (no stored-page short cut)",
      "STORED_TIMEOUT_MS" not in sw and "NETWORK_TIMEOUT_MS" in nav and "isOffline()" in nav, "")

UPD = """(() => { window.__upd = 0; const P = window.ServiceWorkerRegistration && ServiceWorkerRegistration.prototype;
  if (P) { const u = P.update; P.update = function () { window.__upd++; return u.apply(this, arguments); }; } })()"""

with sync_playwright() as p:
    for dev, eng, opts in DEVICES:
        b = getattr(p, eng).launch()
        c = b.new_context(service_workers="allow", **opts)
        c.add_init_script("localStorage.setItem('ap.readerHintSeen','1');sessionStorage.setItem('s50n',(+sessionStorage.getItem('s50n')||0)+1);" + UPD)
        pg = c.new_page()
        pg.goto(f"{BASE}/ru-iast/", wait_until="networkidle")
        try:
            pg.wait_for_function("navigator.serviceWorker.controller !== null", timeout=60000)
        except Exception:
            pass
        reg = pg.evaluate("""async () => { const r = await navigator.serviceWorker.getRegistration();
          return r ? {via: r.updateViaCache, ctrl: !!navigator.serviceWorker.controller} : null; }""")
        check(dev, "C registration updateViaCache = 'none'", reg and reg["via"] == "none", reg)
        pg.reload(wait_until="networkidle")
        pg.wait_for_timeout(1500)
        check(dev, "D an update check on open (registration.update)", pg.evaluate("window.__upd || 0") >= 1, pg.evaluate("window.__upd || 0"))
        # E: the page was served by a worker (controller); a new worker takes over -> exactly one reload.
        ctrl = pg.evaluate("!!navigator.serviceWorker.controller")
        n0 = pg.evaluate("+sessionStorage.getItem('s50n')")
        pg.evaluate("""() => { const e = navigator.serviceWorker; e.dispatchEvent(new Event('controllerchange'));
          e.dispatchEvent(new Event('controllerchange')); }""")
        pg.wait_for_timeout(3000)
        pg.wait_for_load_state("networkidle")
        pg.wait_for_timeout(1500)
        n1 = pg.evaluate("+sessionStorage.getItem('s50n')")
        check(dev, "E controllerchange (page had a worker) -> the page reloads exactly once", ctrl and n1 - n0 == 1,
              {"controller": ctrl, "loads before": n0, "after": n1})
        c.close()
        b.close()

print(f"{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
