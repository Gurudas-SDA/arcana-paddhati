"""Independent per-rule verifier (Правила интерфейса §1–§9), one run per device.
Ported from the verifier scenarios (verify1/run_dev.py, v72/run_dev.py).
usage: python s10_rules_verifier.py <base-url>      devices: QA_DEVICES
Lines: [PASS]/[FAIL] <device> <§rule> | <check> | <evidence>;  [INFO] lines are measurements only."""
import sys, os, json, math, time, traceback
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402  (device profiles, repo paths)
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/") + "/"
RU = BASE + "ru-iast/"
TOTAL = [0, 0]


def profiles(p):
    """Playwright's built-in descriptors (viewport WITH browser toolbars) under canonical names."""
    d = p.devices
    s23 = dict(d["Pixel 7"]); s23.update(viewport={"width": 360, "height": 780}, device_scale_factor=3, screen={"width": 360, "height": 780})
    return {
        "pixel7": ("chromium", dict(d["Pixel 7"])),
        "s23fe": ("chromium", s23),
        "iphone14": ("webkit", dict(d["iPhone 14"])),
        "ipad-portrait": ("webkit", dict(d["iPad (gen 7)"])),
        "ipad-landscape": ("webkit", dict(d["iPad (gen 7) landscape"])),
        "ipad-mini": ("webkit", dict(d["iPad Mini"])),
        "desktop": ("chromium", dict(viewport={"width": 1440, "height": 900})),
        "mac-safari": ("webkit", dict(viewport={"width": 1440, "height": 900})),
    }


def ctx(p, name, **kw):
    eng, opts = profiles(p)[name]
    opts = dict(opts); opts.pop("default_browser_type", None); opts.update(kw)
    b = getattr(p, eng).launch()
    c = b.new_context(**opts)
    return b, c


def shot(page, name):
    d = os.environ.get("QA_SHOTS")
    if not d:
        return ""
    path = os.path.join(d, name + ".png"); os.makedirs(d, exist_ok=True)
    page.screenshot(path=path); return path


def run_one(DEV):
    R = []          # results
    def rec(rule, check, ok, ev):
        R.append(dict(rule=rule, check=check, ok=ok, ev=ev))
        tag = "PASS" if ok else ("FAIL" if ok is False else "INFO")
        if ok is not None:
            TOTAL[0 if ok else 1] += 1
        print(f"  [{tag}] {DEV} {rule} | {check} | {str(ev)[:300]}", flush=True)

    EXT = []
    def on_req(r):
        u = r.url
        if not (u.startswith(BASE.split("/arcana")[0]) or u.startswith("data:") or u.startswith("blob:")):
            EXT.append(u)

    with sync_playwright() as p:
        b, c = ctx(p, DEV)
        touch = profiles(p)[DEV][1].get("has_touch", False)
        c.add_init_script("try{localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
        pg = c.new_page()
        pg.on("request", on_req)
        VW = pg.viewport_size["width"]; VH = pg.viewport_size["height"]

        def wait(s=0.45): time.sleep(s)
        def tap(x, y, s=0.5):
            if touch: pg.touchscreen.tap(x, y)
            else: pg.mouse.click(x, y)
            wait(s)
        def bars(): return pg.evaluate("document.documentElement.hasAttribute('data-reader-bars')")
        def menu_open(): return pg.evaluate("!!document.querySelector('.mobile-menu')")
        def active_rows(): return pg.evaluate("[...document.querySelectorAll('.hs-row[data-active]')].map(r=>r.innerText.trim().slice(0,40))")
        def go(path):
            pg.goto(RU + path, wait_until="networkidle"); wait(0.8)
            # dismiss install banner
            pg.evaluate("""()=>{const el=[...document.querySelectorAll('main *')].find(e=>e.children.length<=3 && /Установить приложение/.test(e.textContent||'') && e.querySelector('button'));
              if(!el) return; const bs=[...el.closest('div').parentElement.querySelectorAll('button')]; const x=bs[bs.length-1]; if(x) x.click();}""")
            wait(0.4)
            if bars():  # make sure reading mode
                pg.keyboard.press("Escape"); wait(0.3)
        def el_center(sel, idx=0):
            return pg.evaluate("""([s,i])=>{const e=document.querySelectorAll(s)[i]; if(!e) return null; const r=e.getClientRects()[0]||e.getBoundingClientRect(); return {x:r.left+r.width/2,y:r.top+r.height/2,w:r.width,h:r.height,l:r.left,r:r.right,t:r.top,b:r.bottom}}""", [sel, idx])
        def scroll_into(sel, idx=0, block="center"):
            pg.evaluate("""([s,i,b])=>{const e=document.querySelectorAll(s)[i]; e && e.scrollIntoView({block:b})}""", [sel, idx, block]); wait(0.5)
        def show_bars():
            for k in range(3):
                if bars(): return True
                if active_rows():
                    tap(*empty_point()[:2])
                pt = empty_point()
                tap(pt[0], pt[1])
            if not bars(): rec("helper", "не удалось показать меню тапом", False, f"url={pg.url} pt={empty_point()}")
            return bars()
        def empty_point():
            # a point whose element is plain page (not NO_TOGGLE) -- right page margin at mid-screen
            return pg.evaluate("""()=>{
              const NO='a,button,input,[role=button],[role=dialog],img,svg,.hs-text,.hs-hit,.hs-figure,.hs-peek,.mood-toggle,.verse-chips,[data-no-reader-tap],.reader-bar,.reader-status';
              for (let y=Math.round(innerHeight*0.45); y<innerHeight-70; y+=17) for (const x of [innerWidth-5, 5]) {
                const e=document.elementFromPoint(x,y);
                if(e && !e.closest(NO) && e.closest('.app-main') && [[-28,0],[0,-28],[0,28],[-28,-28],[-28,28]].every(([dx,dy])=>{const f=document.elementFromPoint(Math.max(1,x+dx),y+dy); return f && !f.closest(NO)})) return [x,y,e.tagName+'.'+(e.className||'').toString().slice(0,30)];
              }
              for (let y=Math.round(innerHeight*0.45); y>70; y-=17) for (const x of [innerWidth-5, 5]) {
                const e=document.elementFromPoint(x,y);
                if(e && !e.closest(NO) && e.closest('.app-main')) return [x,y,e.tagName+'.'+(e.className||'').toString().slice(0,30)];
              } return [innerWidth-6, Math.round(innerHeight/2), 'fallback'];}""")

        # ================= COVER =================
        try:
            go("")
            rec("§9 обложка", "скриншот обложки", None, shot(pg, f"{DEV}_cover"))
            cov = el_center("img.home-cover")
            rec("§9 обложка", "размер обложки (px, доля экрана по высоте)", None, f"{cov['w']:.0f}x{cov['h']:.0f}, h/VH={cov['h']/VH:.2f}, w/VW={cov['w']/VW:.2f}")
            tap(cov["x"], cov["y"])
            b1 = bars()
            tap(cov["x"], cov["y"] + 30)
            b2 = bars()
            rec("§7 обложка: касание в любом месте показывает меню", "тап по картинке обложки → меню, ещё тап → скрыто", b1 and not b2, f"после 1-го тапа bars={b1}, после 2-го={b2}, точка=({cov['x']:.0f},{cov['y']:.0f})")
            tap(VW / 2, 8 if VH > 0 else 8)
            rec("§7 обложка", "тап у верхнего края (пустое поле) → меню", bars(), f"bars={bars()}")
        except Exception as e:
            rec("§7 обложка", "ошибка теста", False, traceback.format_exc()[-300:])

        # translate=no
        tr = pg.evaluate("({h:document.documentElement.getAttribute('translate'),b:document.body.getAttribute('translate'),m:document.querySelector('meta[name=google]')?.content, cls:document.documentElement.className.includes('notranslate')})")
        rec("§8 без предложения перевода", "html/body translate=no, meta google=notranslate", tr["h"] == "no" and tr["b"] == "no" and tr["m"] == "notranslate", tr)

        # ================= CHAPTER: Tilak =================
        def hotspot_suite(path, label, expect_inert=False, deity_nums=()):
            go(path)
            m = pg.evaluate("document.querySelector('.app-main').scrollTop")
            # list -> image, every row
            nrows = pg.evaluate("document.querySelectorAll('.hs-row').length")
            bad = []; ok_n = 0; style = None
            for i in range(nrows):
                pg.evaluate("i=>{const r=document.querySelectorAll('.hs-row')[i]; r.scrollIntoView({block:'center'})}", i); wait(0.35)
                pt = pg.evaluate("""i=>{const r=document.querySelectorAll('.hs-row')[i]; const t=r.querySelector('.hs-text'); const q=t.getClientRects()[0];
                     return {x:q.left+Math.min(q.width/2,20), y:q.top+q.height/2, num:(r.querySelector('.nl-num')||r.querySelector('span'))?.textContent.trim()}}""", i)
                tap(pt["x"], pt["y"], 0.6)
                st = pg.evaluate("""i=>{const rows=[...document.querySelectorAll('.hs-row')]; const a=rows.map((r,k)=>r.hasAttribute('data-active')?k:-1).filter(k=>k>=0);
                    const lit=[...document.querySelectorAll('.hs-figure .hs-lit')]; const masks=[...document.querySelectorAll('.hs-figure mask image')].map(x=>x.getAttribute('href').split('/').pop());
                    const fig=[...document.querySelectorAll('.hs-figure img.hs-img-faded')].length;
                    const t=rows[i].querySelector('.hs-text'); const cs=getComputedStyle(t); const rc=getComputedStyle(rows[i]);
                    return {a, lit:lit.length, masks, faded:fig, bg:cs.backgroundColor, bl:rc.borderLeftWidth+' '+rc.borderLeftStyle, bars:document.documentElement.hasAttribute('data-reader-bars')}}""", i)
                num = (pt["num"] or "").rstrip(").").replace(" ", "")
                exp = [x.strip() for x in num.split(",") if x.strip()]
                mask_nums = [mm.rsplit("-", 1)[-1].replace(".png", "").lstrip("0") for mm in st["masks"]]
                # 02-1 style
                mask_nums = [mm.split(".")[0].split("-",1)[1].replace("-", ".").lstrip("0") if mm.count("-") >= 2 else mm.rsplit("-",1)[1].replace(".png","").lstrip("0") for mm in st["masks"]]
                good = st["a"] == [i] and st["lit"] == 1 and st["faded"] >= 1 and not st["bars"] and (not exp or sorted(mask_nums) == sorted(exp))
                if style is None: style = st
                if good: ok_n += 1
                else: bad.append(dict(row=i, num=num, **{k: st[k] for k in ("a", "lit", "masks", "faded", "bars")}))
                # second tap on same row resets
                tap(pt["x"], pt["y"], 0.5)
                if active_rows():
                    bad.append(dict(row=i, num=num, err="повторный тап не снял подсветку"))
                    tap(*empty_point()[:2]);
                    if bars(): pg.keyboard.press("Escape")
            rec(f"§2/§5 {label}: строка → ровно один предмет", f"все {nrows} строк по очереди (номер строки = маска предмета, 1 подсветка, меню не открылось, повторный тап снимает)", not bad, f"ok {ok_n}/{nrows}; ошибки={bad[:6]}")
            if style:
                rec(f"§2 {label}: отметка строки", "computed style активной строки", None, f"bg .hs-text={style['bg']}, border-left строки={style['bl']}")
            shot(pg, f"{DEV}_{label}_rowlast")
            # image -> list, every spot
            spots = pg.evaluate("[...document.querySelectorAll('.hs-figure .hs-hit')].map(g=>g.getAttribute('aria-label'))")
            badi = []; oki = 0; barsspots = []
            for n in spots:
                pg.evaluate("()=>document.querySelector('.hs-figure').scrollIntoView({block:'center'})"); wait(0.4)
                if active_rows():
                    tap(*empty_point()[:2]); wait(0.2)
                pt = pg.evaluate("""n=>{const g=[...document.querySelectorAll('.hs-figure .hs-hit')].find(x=>x.getAttribute('aria-label')===n);
                   const shapes=[...g.querySelectorAll('ellipse,circle')];
                   for(const s of shapes.reverse()){const r=s.getBoundingClientRect();
                     for(let fy=0.5;fy>0.05;fy-=0.1) for(const fx of [0.5,0.35,0.65,0.2,0.8]){const x=r.left+r.width*fx,y=r.top+r.height*fy; const e=document.elementFromPoint(x,y);
                       if(e && e.closest('.hs-hit')===g) return {x,y};}}
                   return null}""", n)
                if not pt:
                    badi.append(dict(spot=n, err="нет видимой точки для касания")); continue
                tap(pt["x"], pt["y"], 1.3)
                st = pg.evaluate("""()=>{const rows=[...document.querySelectorAll('.hs-row')]; const a=rows.filter(r=>r.hasAttribute('data-active'));
                   const vh=innerHeight; return {n:a.length, txt:a.map(r=>(r.querySelector('.nl-num')||r).textContent.trim().slice(0,12)), inview:a.map(r=>{const q=r.getBoundingClientRect(); return q.top>=0&&q.bottom<=vh}), lit:document.querySelectorAll('.hs-figure .hs-lit').length, bars:document.documentElement.hasAttribute('data-reader-bars')}}""")
                numsok = any(n in [x.strip() for x in t.split(')')[0].split(',')] for t in st["txt"])
                if st["bars"]: barsspots.append(n)
                if st["n"] >= 1 and numsok and all(st["inview"]) and st["lit"] == 1:
                    oki += 1
                else:
                    badi.append(dict(spot=n, **st))
                tap(*empty_point()[:2], 0.3)
                if bars(): pg.keyboard.press("Escape"); wait(0.2)
            rec(f"§2/§9 {label}: часть рисунка → строка (подсветка + прокрутка)", f"все {len(spots)} предметов рисунка", not badi, f"ok {oki}/{len(spots)}; ошибки={badi[:6]}")
            rec(f"§1 {label}: касание рисунка не открывает меню", f"после тапа по предмету (и автопрокрутки к строке) меню скрыто", not barsspots, f"меню появилось после тапа по предметам: {barsspots} из {len(spots)}")
            for dn in deity_nums:
                rec(f"§8 эмблема: Божество {dn} нажимается", "наличие hs-hit", dn in spots and not any(x.get('spot') == dn for x in badi), f"spots={spots}")
            # inert (Deities)
            inert = pg.evaluate("document.querySelectorAll('.hs-figure .hs-inert').length")
            if expect_inert:
                pg.evaluate("()=>document.querySelector('.hs-figure').scrollIntoView({block:'center'})"); wait(0.4)
                pts = pg.evaluate("""()=>{const out=[]; for(const p of document.querySelectorAll('.hs-figure .hs-inert')){const r=p.getBoundingClientRect();
                    for(let fy=0.3;fy<0.8;fy+=0.1){const x=r.left+r.width/2,y=r.top+r.height*fy; const e=document.elementFromPoint(x,y); if(e===p){out.push({x,y});break;}}} return out}""")
                res = []
                for q in pts:
                    bb = bars(); tap(q["x"], q["y"]); res.append(dict(pt=(round(q["x"]), round(q["y"])), active=active_rows(), bars_before=bb, bars_after=bars()))
                ok = bool(pts) and all(not r["active"] and r["bars_before"] == r["bars_after"] for r in res)
                rec(f"§3 {label}: Божества не реагируют", f"тап по {len(pts)} инертным зонам", ok, res)
            else:
                rec(f"§3 {label}", "инертных зон", None, inert)
            # numbering alignment §8
            al = pg.evaluate("""()=>{const a=document.querySelector('.reader-article')||document.querySelector('main article')||document.querySelector('main');
                const ps=[...a.querySelectorAll('p')].filter(p=>p.offsetParent&&!p.closest('.hs-row')&&!p.closest('.verse-panel')&&getComputedStyle(p).textAlign!='center'); const pl=Math.min(...ps.map(p=>p.getBoundingClientRect().left));
                const nums=[...document.querySelectorAll('.hs-row .nl-num, .hs-row > span:first-child')].map(n=>n.getBoundingClientRect().left);
                return {textLeft:pl, numMin:Math.min(...nums), numMax:Math.max(...nums), count:nums.length}}""")
            rec(f"§8 {label}: номера не выступают влево", "min(left номеров) ≥ left основного текста", al["numMin"] >= al["textLeft"] - 1, al)
            # empty part of a row (right of the text AND of the row's own controls, e.g. the «пословно» chip —
            # a tap there opens the chip, correctly; v7.3: the point used to land on the new chip)
            gap = pg.evaluate("""()=>{for(const r of document.querySelectorAll('.hs-row')){const rr=r.getBoundingClientRect(); const ts=[...r.querySelectorAll('.hs-text')].flatMap(t=>[...t.getClientRects()]);
                const bt=[...r.querySelectorAll('button, a, .mantra-chips, .verse-chips, [data-no-reader-tap]')].flatMap(t=>[...t.getClientRects()]); const right=Math.max(...ts.concat(bt).map(q=>q.right)); if(rr.right-right>40 && rr.top>80 && rr.bottom<innerHeight-60){const q=ts[ts.length-1]; return {x:(right+rr.right)/2,y:q.top+q.height/2}}} return null}""")
            if not gap:
                pg.evaluate("()=>document.querySelector('.hs-row').scrollIntoView({block:'center'})"); wait(0.4)
                gap = pg.evaluate("""()=>{for(const r of document.querySelectorAll('.hs-row')){const rr=r.getBoundingClientRect(); const ts=[...r.querySelectorAll('.hs-text')].flatMap(t=>[...t.getClientRects()]);
                const bt=[...r.querySelectorAll('button, a, .mantra-chips, .verse-chips, [data-no-reader-tap]')].flatMap(t=>[...t.getClientRects()]); const right=Math.max(...ts.concat(bt).map(q=>q.right)); if(rr.right-right>40 && rr.top>80 && rr.bottom<innerHeight-60){const q=ts[ts.length-1]; return {x:(right+rr.right)/2,y:q.top+q.height/2}}} return null}""")
            if gap:
                b0 = bars(); tap(gap["x"], gap["y"]); a = active_rows(); b1 = bars()
                rec(f"§1 {label}: пустая часть строки не активна", "тап справа от текста строки", not a and b1 != b0, f"pt=({gap['x']:.0f},{gap['y']:.0f}) active={a} bars {b0}->{b1}")
                if bars(): pg.keyboard.press("Escape"); wait(0.3)

        try:
            hotspot_suite("daily-duties-brahma-muhurta/", "Tilak")
        except Exception:
            rec("§2 Tilak", "ошибка теста", False, traceback.format_exc()[-400:])
        try:
            hotspot_suite("worship-sixteen-articles/", "Parafernalia", expect_inert=True)
        except Exception:
            rec("§2 Parafernalia", "ошибка теста", False, traceback.format_exc()[-400:])
        try:
            hotspot_suite("main-worship-sixteen-items/", "Parafernalia2", expect_inert=True)
        except Exception:
            rec("§2 Parafernalia2", "ошибка теста", False, traceback.format_exc()[-400:])
        try:
            hotspot_suite("gaudiya-emblem/", "Emblem", deity_nums=("10", "11", "12"))
        except Exception:
            rec("§2 Emblem", "ошибка теста", False, traceback.format_exc()[-400:])

        # ---- highlight/menu interplay, scroll, peek (Tilak)
        try:
            go("daily-duties-brahma-muhurta/")
            idx = pg.evaluate("document.querySelectorAll('.hs-row').length-1")
            pg.evaluate("i=>document.querySelectorAll('.hs-row')[i].scrollIntoView({block:'center'})", idx); wait(0.4)
            q = el_center(".hs-row:last-of-type .hs-text") or pg.evaluate("""()=>{const r=[...document.querySelectorAll('.hs-row')].pop().querySelector('.hs-text').getClientRects()[0]; return {x:r.left+10,y:r.top+r.height/2}}""")
            q = pg.evaluate("""()=>{const r=[...document.querySelectorAll('.hs-row')].pop().querySelector('.hs-text').getClientRects()[0]; return {x:r.left+10,y:r.top+r.height/2}}""")
            tap(q["x"], q["y"], 0.8)
            a1 = active_rows()
            peek = pg.evaluate("!!document.querySelector('.hs-peek')")
            fig = el_center(".hs-figure")
            rec("§2 маленькая копия", "строка внизу списка, рисунок вне экрана → .hs-peek", None if fig and fig["b"] > 0 and fig["t"] < VH else peek, f"active={a1}, peek={peek}, figure top/bottom={fig and (round(fig['t']), round(fig['b']))}")
            # scroll does not clear
            pg.evaluate("(()=>{const f=document.querySelector('.hs-figure').getBoundingClientRect(); document.querySelector('.app-main').scrollBy(0, Math.max(250, f.bottom+60))})()"); wait(0.7)
            a2 = active_rows(); peek2 = pg.evaluate("!!document.querySelector('.hs-peek')")
            rec("§2 прокрутка не снимает подсветку", "scrollBy 250 после активации", bool(a2), f"active после прокрутки={a2}")
            if peek2:
                shot(pg, f"{DEV}_peek")
                cb = el_center(".hs-peek-close")
                tap(cb["x"], cb["y"])
                rec("§2/§4 копия закрывается ✕", "тап ✕ на .hs-peek", not pg.evaluate("!!document.querySelector('.hs-peek')"), f"✕ at ({cb['x']:.0f},{cb['y']:.0f}), size {cb['w']:.0f}x{cb['h']:.0f}; highlight still={active_rows()}")
            else:
                rec("§2 маленькая копия", "после прокрутки копия не появилась", False if a2 else None, f"peek={peek2}")
            # first tap on empty clears highlight only, second shows menu
            if not active_rows():
                tap(q["x"], q["y"], 0.6)
            pt = empty_point()
            tap(pt[0], pt[1]); s1 = (active_rows(), bars())
            tap(pt[0], pt[1]); s2 = (active_rows(), bars())
            rec("§1 подсветка: 1-е касание снимает, 2-е — меню", "два тапа по пустому полю", (not s1[0]) and (not s1[1]) and s2[1], f"pt={pt}; после 1-го: active={s1[0]} bars={s1[1]}; после 2-го: bars={s2[1]}")
            if bars(): pg.keyboard.press("Escape"); wait(0.3)
        except Exception:
            rec("§1/§2 interplay", "ошибка теста", False, traceback.format_exc()[-400:])

        # ---- tap on empty / plain text toggles menu, no function
        try:
            go("daily-duties-brahma-muhurta/")
            pt = empty_point()
            tap(pt[0], pt[1]); b1 = bars()
            side = dict(wbw=pg.evaluate("document.querySelectorAll('.verse-panel:not([hidden])').length"), mood=pg.evaluate("!!document.querySelector('.mood-overlay')"), act=active_rows())
            shot(pg, f"{DEV}_menu_shown")
            bb = pg.evaluate("""()=>{const r=s=>{const e=document.querySelector(s); if(!e) return null; const q=e.getBoundingClientRect(); return [Math.round(q.left),Math.round(q.top),Math.round(q.right),Math.round(q.bottom)]};
                return {back:r('[data-reader-nav=back]'),fwd:r('[data-reader-nav=forward]'),contents:r('[data-reader-action=contents]'),search:r('[data-reader-action=search]'),aa:r('[data-reader-action=aa]'),vw:innerWidth,vh:innerHeight}}""")
            tap(pt[0], pt[1]); b2 = bars()
            rec("§1 пустое поле → только меню", "тап по пустому полю: меню вкл/выкл, ни одна функция текста не включилась", b1 and not b2 and side["wbw"] == 0 and not side["mood"] and not side["act"], f"pt={pt} bars {b1}->{b2}; side={side}")
            edge_ok = bb["back"] and bb["back"][0] <= 24 and bb["fwd"] and bb["vw"] - bb["fwd"][2] <= 24 and bb["contents"][0] <= 24 and bb["vw"] - bb["aa"][2] <= 24
            rec("§7 кнопки у самых краёв", "left «Назад»/«Содержание», right «Вперёд»/«Аа» (≤24px от края)", bool(edge_ok), bb)
            # plain text
            tp = pg.evaluate("""()=>{const NO='a,button,[role=button],img,svg,.hs-text,.mood-toggle,.verse-chips,.sa-inline,b,strong';
                for(const p of document.querySelectorAll('.app-main li, .app-main p')){const r=p.getBoundingClientRect(); if(r.top<100||r.bottom>innerHeight-80) continue;
                  for(let x=r.left+15;x<r.right-10;x+=10){const y=r.top+10; const e=document.elementFromPoint(x,y); if(e && !e.closest(NO) && (e===p||p.contains(e))) return {x,y,tag:e.tagName,txt:p.textContent.slice(0,30)}}} return null}""")
            if tp:
                tap(tp["x"], tp["y"]); b3 = bars(); tap(tp["x"], tp["y"]); b4 = bars()
                rec("§1 касание обычного текста → меню", "тап по слову абзаца", b3 and not b4, f"{tp} bars {b3}->{b4}")
        except Exception:
            rec("§1 empty", "ошибка теста", False, traceback.format_exc()[-400:])

        # ---- full-width reading, shlokas centered
        try:
            lay = pg.evaluate("""()=>{const ps=[...document.querySelectorAll('.app-main p, .app-main li')].filter(p=>p.offsetParent); const L=Math.min(...ps.map(p=>p.getBoundingClientRect().left)), R=Math.max(...ps.map(p=>p.getBoundingClientRect().right));
                const v=document.querySelector('.verse-text'); const fs=parseFloat(getComputedStyle(ps.find(p=>p.closest('li'))||ps[0]).fontSize);
                return {left:Math.round(L), right:Math.round(innerWidth-R), vw:innerWidth, verseAlign:v&&getComputedStyle(v).textAlign, bodyFont:fs}}""")
            rec("§7 чтение на весь экран, шлоки по центру", "поля слева/справа, text-align шлоки, размер шрифта", lay["verseAlign"] == "center", lay)
        except Exception:
            rec("§7 layout", "ошибка", False, traceback.format_exc()[-300:])

        # ---- verse chips (word-by-word)
        try:
            go("daily-duties-brahma-muhurta/")
            scroll_into(".verse-chip", 0)
            chips = pg.evaluate("[...document.querySelectorAll('.verse-chip')].map(c=>c.textContent.trim())")
            i = next((k for k, t in enumerate(chips) if "пословно" in t.lower()), None)
            q = el_center(".verse-chip", i)
            b0 = bars(); tap(q["x"], q["y"]); n1 = pg.evaluate("document.querySelectorAll('.verse-wbw:not([hidden])').length"); b1 = bars()
            tap(q["x"], q["y"]); n2 = pg.evaluate("document.querySelectorAll('.verse-wbw:not([hidden])').length")
            rec("§1 кнопка «пословно» включает только свою функцию", "тап по чипу открывает/закрывает, меню не меняется", n1 == 1 and n2 == 0 and b0 == b1, f"chip='{chips[i]}' wbw {n1}->{n2}, bars {b0}->{b1}")
        except Exception:
            rec("§1 chips", "ошибка", False, traceback.format_exc()[-300:])

        # ---- mood overlay
        try:
            go("daily-duties-brahma-muhurta/")
            scroll_into(".mood-toggle")
            q = el_center(".mood-toggle"); b0 = bars()
            tap(q["x"], q["y"], 0.8)
            dlg = pg.evaluate("""()=>{const d=document.querySelector('.mood-dialog'); if(!d) return null; const r=d.getBoundingClientRect(); const c=document.querySelector('.mood-close').getBoundingClientRect();
               const links=[...d.querySelectorAll('a[data-transcript-link]')].map(a=>a.getAttribute('href'));
               return {l:Math.round(r.left),t:Math.round(r.top),w:Math.round(r.width),h:Math.round(r.height),vw:innerWidth,vh:innerHeight, close:[Math.round(c.left),Math.round(c.top),Math.round(c.width)], closeTxt:document.querySelector('.mood-close').getAttribute('aria-label'), links, nclose:d.querySelectorAll('button').length}}""")
            shot(pg, f"{DEV}_mood")
            rec("§8 окно «Настроение»: крупное, с полями", "размер диалога относительно экрана", None if dlg else False, dlg)
            rec("§1 «Настроение» не открывает меню", "bars до/после", dlg is not None and bars() == b0, f"bars {b0}->{bars()}")
            # scroll containment
            m0 = pg.evaluate("document.querySelector('.app-main').scrollTop")
            cx, cy = dlg["l"] + dlg["w"] / 2, dlg["t"] + dlg["h"] / 2
            try:
                pg.mouse.move(cx, cy)
                for _ in range(8): pg.mouse.wheel(0, 800); wait(0.08)
                wait(0.4)
                pg.mouse.move(8, 8)
                for _ in range(4): pg.mouse.wheel(0, 800); wait(0.08)
                wait(0.4)
            except Exception as e:
                rec("§4 прокрутка не выходит за окно", "колесо недоступно в mobile WebKit — проверены только стили блокировки", None, str(e)[:80])
            m1 = pg.evaluate("document.querySelector('.app-main').scrollTop")
            ms = pg.evaluate("({sc:document.querySelector('.mood-scroll').scrollTop, ob:getComputedStyle(document.querySelector('.mood-scroll')).overscrollBehaviorY, mainOv:getComputedStyle(document.querySelector('.app-main')).overflowY})")
            rec("§4 прокрутка не выходит за окно", "колесо ×8 в окне + ×4 на фоне; scrollTop .app-main", m0 == m1, f"main {m0}->{m1}; {ms}")
            # close via X
            tap(dlg["close"][0] + dlg["close"][2] / 2, dlg["close"][1] + dlg["close"][2] / 2, 0.6)
            c1 = pg.evaluate("!!document.querySelector('.mood-overlay')")
            rec("§4 окно закрывается ✕", "тап ✕", not c1, f"overlay после ✕={c1}; ✕ size={dlg['close'][2]}px; кнопок в диалоге={dlg['nclose']}")
            # reopen, back closes
            url0 = pg.url
            tap(q["x"], q["y"], 0.8)
            o = pg.evaluate("!!document.querySelector('.mood-overlay')")
            pg.go_back(); wait(0.8)
            rec("§4 «назад» закрывает окно", "page.go_back при открытом окне", o and not pg.evaluate("!!document.querySelector('.mood-overlay')") and pg.url == url0, f"opened={o}, after back overlay={pg.evaluate('!!document.querySelector(\".mood-overlay\")')}, url same={pg.url==url0}")
            # transcript link opens inside app (same origin)
            if dlg["links"]:
                tap(q["x"], q["y"], 0.8)
                href = dlg["links"][0]
                same = href.startswith("/arcana-paddhati/transcripts/") or href.startswith(BASE + "transcripts/")
                lk = el_center(".mood-dialog a[data-transcript-link]")
                pg.evaluate("document.querySelector('.mood-dialog a[data-transcript-link]').scrollIntoView({block:'center'})"); wait(0.3)
                lk = el_center(".mood-dialog a[data-transcript-link]")
                npages = len(c.pages)
                t0=time.time(); tap(lk["x"], lk["y"], 0.2)
                # pg.wait_for_timeout (not time.sleep): Playwright updates pg.url only while it processes events
                while "/transcripts/" not in pg.url and time.time()-t0<20: pg.wait_for_timeout(200)
                dt=time.time()-t0
                try: pg.wait_for_load_state("load", timeout=20000)
                except Exception: pass
                shot(pg, f"{DEV}_transcript")
                rec("§8 транскрипт открывается внутри приложения", "тап ссылки «транскрипт» в окне", same and len(c.pages) == npages and "/transcripts/" in pg.url, f"href={href}, url={pg.url}, новых вкладок={len(c.pages)-npages}, время до смены URL={dt:.1f}s")
                pg.go_back(); wait(0.8)
        except Exception:
            rec("§4 mood", "ошибка", False, traceback.format_exc()[-400:])

        # ---- Aa
        try:
            go("daily-duties-brahma-muhurta/")
            show_bars()
            fs0 = pg.evaluate("parseFloat(getComputedStyle(document.querySelector('.app-main article li') || document.querySelector('.app-main article p')).fontSize)")
            q = el_center("[data-reader-action=aa]"); tap(q["x"], q["y"])
            q = el_center('[data-reader-size="+"]'); tap(q["x"], q["y"])
            fs1 = pg.evaluate("parseFloat(getComputedStyle(document.querySelector('.app-main article li') || document.querySelector('.app-main article p')).fontSize)")
            shot(pg, f"{DEV}_aa")
            q = el_center(".reader-panel-close"); tap(q["x"], q["y"])
            closed = not pg.evaluate("!!document.querySelector('.reader-panel')")
            rec("§7 «Аа» меняет размер текста", "font-size до/после «A+»; панель закрывается ✕", fs1 > fs0 and closed, f"{fs0}px -> {fs1}px; panel closed={closed}")
            # reset
            pg.evaluate("try{localStorage.clear(); localStorage.setItem('ap.readerHintSeen','1')}catch(e){}")
        except Exception:
            rec("§7 Aa", "ошибка", False, traceback.format_exc()[-300:])

        # ---- next chapter link
        try:
            go("daily-duties-brahma-muhurta/")
            pg.evaluate("document.querySelector('.app-main').scrollTop=1e9"); wait(0.8)
            nx = pg.evaluate("""()=>{const a=document.querySelector('[data-chapter-next]'); if(!a) return null; const r=a.getBoundingClientRect(); return {txt:a.innerText.replace(/\\s+/g,' ').trim(), href:a.getAttribute('href'), x:r.left+Math.min(r.width/2,60), y:r.top+r.height/2, inview:r.bottom<=innerHeight&&r.top>=0}}""")
            shot(pg, f"{DEV}_chapter_end")
            u_before = pg.url; tap(nx["x"], nx["y"], 0.2); t0 = time.time()
            while pg.url == u_before and time.time() - t0 < 10: time.sleep(0.2)
            nav_dt = time.time() - t0; wait(1.0)
            st = pg.evaluate("({u:location.pathname, top:document.querySelector('.app-main').scrollTop, h1:document.querySelector('.app-main h1, .app-main h2')?.textContent})")
            rec("§9 «След. глава ›» в конце главы", "текст ссылки содержит «След. глава» и название; тап ведёт на начало следующей главы", "След. глава" in nx["txt"] and "daily-deity-schedule" in st["u"] and st["top"] < 5, f"link='{nx['txt']}', после тапа {st}, смена URL через {nav_dt:.1f}s")
        except Exception:
            rec("§9 next", "ошибка", False, traceback.format_exc()[-300:])

        # ---- Contents / path / back-forward
        def state():
            return pg.evaluate("""()=>{const m=document.querySelector('.mobile-menu'); const lit=m?[...m.querySelectorAll('[data-toc-lit]')].map(e=>e.textContent.trim().slice(0,28)):[];
              const exp=m?[...m.querySelectorAll('[aria-expanded=true]')].map(e=>(e.getAttribute('data-toc-group')||e.getAttribute('data-toc-chapter')||e.getAttribute('data-toc-toggle')||'?')):[];
              const q=m?.querySelector('input[type=search]')?.value||'';
              return location.pathname.replace('/arcana-paddhati/ru-iast','')+(m?' [menu lit='+JSON.stringify(lit)+' exp='+JSON.stringify([...new Set(exp)])+(q?' q='+q:'')+']':'')}""")
        def toc_tap(sel_js, s=0.6):
            q = pg.evaluate("""s=>{const e=eval(s); if(!e) return null; e.scrollIntoView({block:'center'}); const r=(e.querySelector('span')||e).getBoundingClientRect(); return {x:r.left+Math.min(r.width/2,40),y:r.top+r.height/2}}""", sel_js)
            wait(0.25)
            q = pg.evaluate("""s=>{const e=eval(s); if(!e) return null; const r=(e.querySelector('span')||e).getBoundingClientRect(); return {x:r.left+Math.min(r.width/2,40),y:r.top+r.height/2}}""", sel_js)
            if not q: return False
            tap(q["x"], q["y"], s); return True
        try:
            go("")
            path = [state()]
            show_bars(); q = el_center("[data-reader-action=contents]"); tap(q["x"], q["y"], 0.7)
            path.append(state())
            toc_txt = pg.evaluate("document.querySelector('.mobile-menu').innerText")
            rec("§9 нет строки «Начало главы»", "текст оглавления (до раскрытий)", "Начало главы" not in toc_txt, f"{'Начало главы' in toc_txt}")
            INTRO = "document.querySelector('.mobile-menu [data-toc-group=introduction]')"
            toc_tap(INTRO); s_open = state()
            members = pg.evaluate("""()=>{const l=document.getElementById('toc-grp-introduction'); return l?[...l.querySelectorAll(':scope > li')].map(li=>({t:li.textContent.trim().slice(0,40), num:!!li.querySelector('.heading-num')})):null}""")
            toc_tap(INTRO); s_closed = pg.evaluate("!document.getElementById('toc-grp-introduction')")
            rec("§9 «Введение» раскрывается/сворачивается", "тап раскрывает 2 пункта без номеров (v7.1: Эмблема, Виграха-таттва), повторный тап сворачивает", bool(members) and [m["t"][:8] for m in members] and len(members) == 2 and not any(m["num"] for m in members) and s_closed, f"members={members}, collapsed={s_closed}")
            toc_tap(INTRO); path.append(state())
            EMB = "[...document.querySelectorAll('#toc-grp-introduction a, #toc-grp-introduction [data-toc-chapter]')].find(a=>/Эмблема/.test(a.textContent))"
            toc_tap(EMB); s1 = state(); toc_tap(EMB, 1.2); path.append(state())
            # chapter with subsections: first tap expands, not navigates
            show_bars(); q = el_center("[data-reader-action=contents]"); tap(q["x"], q["y"], 0.7)
            path.append(state())
            lit_here = pg.evaluate("[...document.querySelectorAll('.mobile-menu [data-toc-lit]')].map(e=>e.textContent.trim().slice(0,30))")
            rec("§9 в «Содержании» подсвечено место, где был", "после открытия главы «Эмблема» и повторного открытия «Содержания»", any("Эмблема" in x for x in lit_here), lit_here)
            # part heading
            PART = "document.querySelector('.mobile-menu [data-toc-group]:not([data-toc-group=introduction])')"
            toc_tap(PART); part_state = pg.evaluate("""()=>{const e=document.querySelector('.mobile-menu [data-toc-group]:not([data-toc-group=introduction])'); return {t:e.textContent.trim(), lit:e.hasAttribute('data-toc-lit'), exp:e.getAttribute('aria-expanded'), bg:getComputedStyle(e.parentElement).backgroundColor, color:getComputedStyle(e).color}}""")
            rec("§9 главы-разделы подсвечиваются как подглавы", "тап заголовка раздела", part_state["lit"], part_state)
            path.append(state())
            CH = "document.querySelector('.mobile-menu [data-toc-chapter=daily-duties-brahma-muhurta]')"
            u0 = pg.url; toc_tap(CH, 0.8)
            chs = pg.evaluate("""()=>{const e=document.querySelector('.mobile-menu [data-toc-chapter=daily-duties-brahma-muhurta]'); return {exp:e?.getAttribute('aria-expanded'), subs:document.getElementById('toc-ch-daily-duties-brahma-muhurta')?.children.length||0, menu:!!document.querySelector('.mobile-menu')}}""")
            rec("§7 глава с подразделами: 1-е касание раскрывает", "URL не меняется, список подразделов открыт", pg.url == u0 and chs["exp"] == "true" and chs["subs"] > 0, f"url same={pg.url==u0}, {chs}")
            toc_txt2 = pg.evaluate("document.querySelector('.mobile-menu').innerText")
            rec("§9 нет строки «Начало главы» (раскрытая глава)", "текст оглавления", "Начало главы" not in toc_txt2, "Начало главы" in toc_txt2)
            path.append(state())
            SUB = "document.querySelector('#toc-ch-daily-duties-brahma-muhurta li:nth-child(2) a')"
            toc_tap(SUB); toc_tap(SUB, 1.2)
            path.append(state())
            shot(pg, f"{DEV}_after_toc_nav")
            # back via app button step by step
            back_seq = [state()]
            for k in range(10):
                show_bars()
                q = el_center("[data-reader-nav=back]") if not menu_open() else None
                if q: tap(q["x"], q["y"], 1.0)
                else:
                    # inside menu the reader bar is covered; use system back as user would
                    pg.go_back(); wait(1.0)
                s = state(); back_seq.append(("app " if q else "sys ") + s)
                if s == "/" or s.startswith("/ ") and "menu" not in s: break
            rec("§6/§7/§9 «Назад» пошагово (кнопки приложения; в меню — системная)", "последовательность шагов назад", None, back_seq)
            fwd_seq = [state()]
            for k in range(10):
                if menu_open():
                    pg.go_forward(); wait(1.0); how = "sys "
                else:
                    show_bars(); q = el_center("[data-reader-nav=forward]"); tap(q["x"], q["y"], 1.0); how = "app "
                s = state(); fwd_seq.append(how + s)
                if "daily-duties" in s and "menu" not in s: break
            rec("§9 «Вперёд» пошагово", "последовательность шагов вперёд", None, fwd_seq)
            rec("§7 путь (вперёд записанный)", "состояния при прохождении", None, path)
            # system back only
            sys_seq = [state()]
            for k in range(10):
                pg.go_back(); wait(1.0); s = state(); sys_seq.append(s)
                if s == "/": break
            rec("§6 системная «назад» пошагово", "page.go_back до обложки", None, sys_seq)
        except Exception:
            rec("§7/§9 contents/path", "ошибка", False, traceback.format_exc()[-500:])

        # ---- Search: Enter closes keyboard, back returns to search with query
        try:
            go("introduction/")
            show_bars(); q = el_center("[data-reader-action=search]"); tap(q["x"], q["y"], 1.0)
            foc = pg.evaluate("document.activeElement?.type")
            pg.keyboard.type("тилак", delay=40); wait(1.5)
            pg.keyboard.press("Enter"); wait(0.5)
            blurred = pg.evaluate("document.activeElement?.type!=='search'")
            nres = pg.evaluate("document.querySelectorAll('.mobile-menu nav li a').length")
            rec("§6 Enter закрывает клавиатуру", "после Enter поле не в фокусе", blurred, f"focus before={foc}, blurred={blurred}, results={nres}")
            shot(pg, f"{DEV}_search")
            R0 = "document.querySelector('.mobile-menu nav li a[href*=\"daily-duties\"]') || document.querySelector('.mobile-menu nav li a')"
            u_b = pg.url; toc_tap(R0, 0.3); t0 = time.time()
            while pg.url == u_b and time.time() - t0 < 10: time.sleep(0.2)
            wait(1.0)
            u = pg.url
            pg.go_back(); wait(1.2)
            st = state()
            rec("§6 «назад» к поиску с запросом", "после открытия результата и go_back", "q=тилак" in st, f"result url={u.split('/arcana-paddhati')[-1]}, after back: {st}")
        except Exception:
            rec("§6 search", "ошибка", False, traceback.format_exc()[-300:])

        # ---- ellipsis scan
        try:
            found = []
            for path_ in ["", "introduction/", "daily-duties-brahma-muhurta/", "worship-sixteen-articles/", "major-festivals/"]:
                go(path_)
                show_bars()
                q = el_center("[data-reader-action=contents]"); tap(q["x"], q["y"], 0.6)
                f = pg.evaluate("""()=>{const out=[]; for(const e of document.querySelectorAll('body *')){ if(!e.offsetParent && getComputedStyle(e).position!=='fixed') continue; const cs=getComputedStyle(e);
                     if((cs.textOverflow==='ellipsis' && e.scrollWidth>e.clientWidth+1) || (cs.webkitLineClamp && cs.webkitLineClamp!=='none' && e.scrollHeight>e.clientHeight+1)) out.push('CLIP '+e.tagName+'.'+e.className.toString().slice(0,40)+': '+e.textContent.slice(0,50));
                     for(const n of e.childNodes){ if(n.nodeType===3 && n.textContent.includes('…') && !e.closest('.app-main article, .mood-quote, .mood-translation')) out.push('TEXT '+e.tagName+': '+n.textContent.trim().slice(0,80));}}
                   return out}""")
                for x in f: found.append(path_ + " :: " + x)
                pg.keyboard.press("Escape")
            rec("§4 нет обрезанных надписей «…»", "CSS ellipsis/line-clamp с переполнением + «…» вне текста книги (страницы+меню)", not any(x.split(" :: ")[1].startswith("CLIP") for x in found), found[:15])
        except Exception:
            rec("§4 ellipsis", "ошибка", False, traceback.format_exc()[-300:])

        rec("§8 нет внешних запросов", "все запросы за прогон", not EXT, EXT[:10])
        b.close()


for _dev, _eng, _o in qa.devices(["pixel7", "s23fe", "iphone14", "ipad-portrait", "ipad-landscape", "ipad-mini", "desktop", "mac-safari"]):
    print(_dev, flush=True)
    try:
        run_one(_dev)
    except Exception as e:
        print(f"  [FAIL] {_dev} EXCEPTION {str(e)[:600]}", flush=True); TOTAL[1] += 1
print(); print(f"{TOTAL[0]}/{TOTAL[0] + TOTAL[1]} passed")
