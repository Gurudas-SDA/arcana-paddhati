"""Contents reading-place regressions from the PR2 fixes specification.

Real phone touches, native scroll events and measured geometry. No app overrides.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa
from toc import Contents
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/")
CHAPTER = "arcana-procedure"
results = []


def check(device, name, ok, evidence):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {device} {name} {json.dumps(evidence, ensure_ascii=False)}", flush=True)


def fresh(browser, options, anchor="11-gandha"):
    context = browser.new_context(service_workers="block", **options)
    context.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
    page = context.new_page()
    flow = Contents(page, qa.TocMode("default"), options.get("has_touch", False))
    page.goto(f"{BASE}/ru-iast/{CHAPTER}/#{anchor}", wait_until="networkidle")
    qa.wait_for_book_chapter(page, CHAPTER)
    page.wait_for_timeout(1100)
    return context, page, flow


def read_to(page, anchor):
    # Cancel arrival holding with a real touch, then move the real scroller.
    page.touchscreen.tap(page.viewport_size["width"] - 6, 400)
    page.evaluate("""id => {
      const main = document.querySelector('.app-main');
      const target = (document.querySelector('[data-reader-current]') || document).querySelector(`[id="${CSS.escape(id)}"]`);
      main.scrollTop += target.getBoundingClientRect().top - 110;
    }""", anchor)
    page.wait_for_timeout(1100)


ROW_VISIBILITY = """id => {
  const nav = document.querySelector('.mobile-menu[data-open] .toc-scroll');
  const row = nav.querySelector(`[data-toc-chapter="${CSS.escape(id)}"]`);
  const first = nav.querySelector(`#toc-ch-${CSS.escape(id)} [data-toc-row]`);
  const n = nav.getBoundingClientRect();
  const measure = el => {
    const r = el.getBoundingClientRect();
    const visible = Math.max(0, Math.min(r.bottom,n.bottom)-Math.max(r.top,n.top));
    return {top:r.top,bottom:r.bottom,height:r.height,fraction:visible/r.height};
  };
  return {navTop:n.top,navBottom:n.bottom,scrollTop:nav.scrollTop,row:measure(row),first:measure(first)};
}"""


def opened_chapters(browser, device, options):
    context, page, flow = fresh(browser, options)
    try:
        read_to(page, "14-dipa")
        flow.contents()
        before = page.evaluate(ROW_VISIBILITY, CHAPTER)
        flow.tap(flow.chapter("arcana-sri-guru"), wait=1000)
        after = page.evaluate(ROW_VISIBILITY, "arcana-sri-guru")
        check(device, "s37_opened_chapter_visible: expanded 4 → collapsed 5",
              before["first"]["height"] > 0 and after["row"]["fraction"] == 1 and after["first"]["fraction"] == 1,
              {"beforeChapter4": before, "afterChapter5": after})

        book = json.load(open(os.path.join(qa.DATA, "book.ru-iast.json"), encoding="utf-8"))
        groups = {sid: part["id"] for part in book["parts"] for sid in part["sections"]}
        groups.update({"gaudiya-emblem": "introduction", "vigraha-tattva": "introduction"})
        for chapter in book["sections"]:
            if not chapter.get("subsections"):
                continue
            sid = chapter["id"]
            group = flow.group(groups[sid]) if sid in groups else None
            if group is not None and group.count() and group.get_attribute("aria-expanded") != "true":
                flow.tap(group)
            row = flow.chapter(sid)
            if row.get_attribute("aria-expanded") == "true":
                flow.tap(row)
            flow.tap(row, wait=1000)
            geometry = page.evaluate(ROW_VISIBILITY, sid)
            check(device, f"s37_opened_chapter_visible: {sid}",
                  geometry["row"]["fraction"] == 1 and geometry["first"]["fraction"] == 1, geometry)
    finally:
        context.close()


def mark_follows_reading(browser, device, options):
    for arrival, target, number in [("11-gandha", "14-dipa", "4.14"), ("2-svagata", "6-madhuparka", "4.6")]:
        context, page, flow = fresh(browser, options, arrival)
        try:
            read_to(page, target)
            flow.contents()
            page.wait_for_timeout(1100)
            state = flow.state()
            footer = page.locator(".reader-status > span:not(.reader-location-group)").inner_text().split(" · ", 1)[0]
            geometry = qa.reading_eval(page, """(root,id) => {
              const line=innerHeight*0.205;
              const block=root.querySelector(`[id="${CSS.escape(id)}"]`);
              return {top:block.getBoundingClientRect().top,line};
            }""", target)
            check(device, f"s37_mark_follows_reading: {arrival} → {target}",
                  geometry["top"] <= geometry["line"] and state["lit"] == [f"sub:{CHAPTER}#{target}"]
                  and footer == f"Глава {number}",
                  {"state": state, "footer": footer, "geometry": geometry})
        finally:
            context.close()


def close_keeps_place(browser, device, options):
    for how in ("x", "backdrop"):
        context, page, flow = fresh(browser, options, "2-svagata")
        try:
            # Observe the restored entry before the app's popstate listener.
            # A jump subsequently corrected by the app still moves the book.
            observer = """(() => {
              window.__qaClosePops=[];
              addEventListener('popstate', e => {
                const records=new Map(JSON.parse(sessionStorage.getItem('ap.entries') || '[]'));
                const rec=records.get(e.state?.apId);
                let best=typeof rec?.scroll==='number' ? rec : undefined;
                if(rec?.key) for(const other of records.values()) {
                  if(other.key===rec.key && typeof other.scroll==='number' && (other.at??0)>(best?.at??-1)) best=other;
                }
                window.__qaClosePops.push({scroll:document.querySelector('.app-main').scrollTop,
                  savedScroll:best?.scroll ?? null, hash:location.hash,
                  entryId:e.state?.apId, scrollRestoration:history.scrollRestoration});
              });
            })()"""
            # Reload solely to register the observer before application code.
            page.add_init_script(observer)
            page.reload(wait_until="networkidle")
            qa.wait_for_book_chapter(page, CHAPTER)
            page.wait_for_timeout(1100)
            loaded = page.evaluate("""() => ({scroll:document.querySelector('.app-main').scrollTop,
              entryId:history.state?.apId, scrollRestoration:history.scrollRestoration})""")
            read_to(page, "6-madhuparka")
            scroll = lambda: page.locator(".app-main").evaluate("el => el.scrollTop")
            before = scroll()
            flow.contents()
            opened = scroll()
            page.wait_for_timeout(300)  # Flush the entry records used by the observation.
            if how == "x":
                flow.tap(page.locator('.mobile-menu[data-open] button[aria-label="Закрыть меню"]'), wait=700)
            else:
                page.touchscreen.tap(options["viewport"]["width"] - 6, 400)
                page.wait_for_timeout(700)
            closed = scroll()
            page.touchscreen.tap(options["viewport"]["width"] - 6, 400)
            page.wait_for_timeout(50)
            touched = scroll()
            page.wait_for_timeout(2000)
            later = scroll()
            pops = page.evaluate("window.__qaClosePops")
            positions = [opened, closed, touched, later] + [pop["scroll"] for pop in pops]
            displacement = max(abs(value - before) for value in positions)
            check(device, f"s37_close_toc_keeps_place: {how}",
                  not flow.state()["menu"] and displacement <= 8,
                  {"loadedAndHydrated": loaded, "before": before, "opened": opened, "closed": closed, "touched": touched,
                   "later": later, "pops": pops, "maxDisplacement": displacement})
        finally:
            context.close()


def reload_keeps_place(browser, device, options):
    context, page, flow = fresh(browser, options, "2-svagata")
    try:
        read_to(page, "6-madhuparka")
        before = page.locator(".app-main").evaluate("el => el.scrollTop")
        before_footer = page.locator(".reader-status > span:not(.reader-location-group)").inner_text().split(" · ", 1)[0]
        page.reload(wait_until="networkidle")
        qa.wait_for_book_chapter(page, CHAPTER)
        page.wait_for_timeout(1100)
        restored = page.locator(".app-main").evaluate("el => el.scrollTop")
        flow.contents()
        page.wait_for_timeout(1100)
        after_open = page.locator(".app-main").evaluate("el => el.scrollTop")
        footer = page.locator(".reader-status > span:not(.reader-location-group)").inner_text().split(" · ", 1)[0]
        state = flow.state()
        displacement = max(abs(restored - before), abs(after_open - before))
        check(device, "s37_reload_keeps_place: reading 4.6",
              before_footer == "Глава 4.6" and displacement <= 8 and footer == "Глава 4.6"
              and state["lit"] == [f"sub:{CHAPTER}#6-madhuparka"],
              {"before": before, "restored": restored, "afterContentsOpened": after_open,
               "maxDisplacement": displacement, "beforeFooter": before_footer, "footer": footer,
               "state": state, "scrollRestoration": page.evaluate("history.scrollRestoration")})
    finally:
        context.close()


with sync_playwright() as playwright:
    for device, engine, options in qa.devices(["iphone14", "pixel7"]):
        browser = getattr(playwright, engine).launch()
        try:
            opened_chapters(browser, device, options)
            mark_follows_reading(browser, device, options)
            close_keeps_place(browser, device, options)
            reload_keeps_place(browser, device, options)
        except Exception as error:
            check(device, "s37 suite exception", False, repr(error))
        finally:
            browser.close()

print(f"s37: {sum(results)}/{len(results)} passed", flush=True)
sys.exit(0 if results and all(results) else 1)
