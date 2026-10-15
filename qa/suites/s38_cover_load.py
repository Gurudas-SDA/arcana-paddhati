"""Cover load speed (Satkirti КСВ 14.10.2026: «на айпаде загружается очень долго»).

The cover must become interactive quickly on a slow tablet: a tap on the empty edge
opens the menu within COVER_BUDGET_S seconds of navigation start. Measured in Chromium
with device emulation and 4x CPU throttling (CDP), because WebKit has no CPU throttle.
Also reports the bytes the cover downloads (by resource type) as evidence.
usage: python s38_cover_load.py <base-url>
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
COVER = f"{BASE}/ru-iast/"
COVER_BUDGET_S = float(os.environ.get("QA_COVER_BUDGET_S", "3"))
CPU_SLOWDOWN = 4
DEVICES = qa.devices(["ipad-portrait", "iphone14", "pixel7"])
results = []

HYDRATED = """() => { const m = document.querySelector('.app-main');
  return !!m && Object.keys(m).some(k => k.startsWith('__reactFiber') || k.startsWith('__reactProps')); }"""
BARS = "() => document.documentElement.hasAttribute('data-reader-bars')"


def check(dev, name, ok, evidence):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dev} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


def measure(p, opts):
    """One cold load of the cover: returns timings (s, from navigation start) and bytes."""
    br = p.chromium.launch()
    ctx = br.new_context(service_workers="block", **opts)
    ctx.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
    pg = ctx.new_page()
    cdp = ctx.new_cdp_session(pg)
    cdp.send("Network.enable")
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": CPU_SLOWDOWN})
    types, sizes = {}, {}
    cdp.on("Network.responseReceived", lambda e: types.__setitem__(e["requestId"], (e["type"], e["response"]["url"])))
    cdp.on("Network.loadingFinished", lambda e: sizes.__setitem__(e["requestId"], e["encodedDataLength"]))
    pg.goto(COVER, wait_until="commit")
    t_hyd = t_menu = None
    deadline = time.time() + 40
    while time.time() < deadline:
        if pg.evaluate(HYDRATED):
            t_hyd = pg.evaluate("performance.now()") / 1000
            break
        pg.wait_for_timeout(50)
    if t_hyd is not None:
        vw = pg.viewport_size
        x, y = vw["width"] - 6, vw["height"] // 2
        while time.time() < deadline:
            if opts.get("has_touch"):
                pg.touchscreen.tap(x, y)
            else:
                pg.mouse.click(x, y)
            for _ in range(10):
                pg.wait_for_timeout(50)
                if pg.evaluate(BARS):
                    t_menu = pg.evaluate("performance.now()") / 1000
                    break
            if t_menu is not None:
                break
            pg.wait_for_timeout(200)  # the first tap may land before handlers; try again
    nav = pg.evaluate("(() => { const n = performance.getEntriesByType('navigation')[0]; return n ? {dcl: n.domContentLoadedEventEnd / 1000, load: n.loadEventEnd / 1000} : {}; })()")
    try:
        pg.wait_for_load_state("networkidle", timeout=30000)
    except Exception:
        pass
    by_type, files = {}, []
    for rid, n in sizes.items():
        t, url = types.get(rid, ("Other", "?"))
        by_type[t] = by_type.get(t, 0) + n
        files.append((n, url.replace(BASE, "")))
    files.sort(reverse=True)
    br.close()
    return dict(hydrated_s=t_hyd and round(t_hyd, 2), menu_s=t_menu and round(t_menu, 2),
                dcl_s=round(nav.get("dcl", 0), 2), load_s=round(nav.get("load", 0), 2),
                mb_total=round(sum(sizes.values()) / 1e6, 2),
                mb_by_type={k: round(v / 1e6, 2) for k, v in sorted(by_type.items(), key=lambda kv: -kv[1])},
                top5=[(round(n / 1e6, 2), u[:90]) for n, u in files[:5]])


with sync_playwright() as p:
    for dev, _eng, opts in DEVICES:
        print(dev, flush=True)
        try:
            m = measure(p, opts)
            ok = m["menu_s"] is not None and m["menu_s"] <= COVER_BUDGET_S
            check(dev, f"cover interactive (tap -> menu) <= {COVER_BUDGET_S:g} s at {CPU_SLOWDOWN}x CPU (Chromium emulation)", ok, m)
        except Exception as e:
            check(dev, "EXCEPTION", False, str(e)[:600])

fails = [r for r in results if not r]
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
