"""Shared real-click fixtures for Contents expectations, without app overrides."""
import qa

STATE = """() => {
 const nav = document.querySelector('.mobile-menu nav');
 return {url: location.pathname + location.hash, menu: !!nav,
   lit: nav ? [...nav.querySelectorAll('[data-toc-lit]')].map(e=>e.dataset.tocRow) : [],
   open: nav ? [...nav.querySelectorAll('[aria-expanded=true][data-toc-group],[aria-expanded=true][data-toc-chapter]')]
      .map(e=>e.dataset.tocGroup || e.dataset.tocChapter).sort() : [],
   history: history.length, pushes: window.__qaTocPushes || 0};
}"""

def marks_place(state, langs=('ru', 'ru-iast', 'en', 'lv', 'de', 'fr', 'es', 'it', 'uk', 'hu', 'pt', 'lt')):
    """The contents mark exactly the place being read (Satkirti 13.10.2026).

    The mark is derived from the reading position and no longer remembers which
    row was tapped, so a trace cannot compare it value by value: that would only
    re-test the position and would re-encode the old rule. What must hold at
    every step is the invariant below.

    Exactly one row is marked, and it is the row that stands for where the
    reader is, at the deepest level the contents are currently showing:

      * a subsection of the chapter in the URL, or that chapter's own row;
      * a group heading, when the group IS the page (e.g. «Введение»), or when
        the branch holding the reader is collapsed and the chapter's row is
        therefore not on screen. The mark rises to the nearest visible
        ancestor, as in Apple Books and Kindle;
      * «Обложка» on the cover;
      * nothing at all while the contents are closed.

    A group heading whose branch is OPEN may not carry the mark: the chapter's
    own row is right there and must carry it.
    """
    lit = state['lit']
    if not state['menu']:
        return lit == []
    if len(lit) != 1:
        return False
    row = lit[0]
    pathname = state['url'].split('#')[0]
    # English has no language segment: strip the harness's app prefix before
    # deciding whether this is the cover or a chapter.
    if qa.PREFIX and (pathname == qa.PREFIX or pathname.startswith(qa.PREFIX + '/')):
        pathname = pathname[len(qa.PREFIX):]
    path = [p for p in pathname.split('/') if p]
    section = path[-1] if path and path[-1] not in langs else ''
    if row == 'cover':
        return section == ''
    if section == '':
        return False
    if row == 'sec:' + section or row.startswith('sub:' + section + '#'):
        return True
    if row.startswith('grp:'):
        group = row[4:]
        return group == section or group not in state['open']
    return False


def marks_chapter_top(page, state, chapter):
    """A chapter-top tap keeps the chapter mark unless its first block already
    crosses the reading line (song chapters, or a taller viewport).
    URL, top, expanded list and action counts are checked by the caller.
    """
    sub_at_line = page.evaluate("""id => {
      const link = document.querySelector(`#toc-ch-${CSS.escape(id)} a`);
      const hash = link ? new URL(link.href).hash.slice(1) : '';
      const block = hash ? document.querySelector('[data-reader-current]')?.querySelector(`#${CSS.escape(decodeURIComponent(hash))}`) : null;
      return !!block && block.getBoundingClientRect().top <= innerHeight * 0.205;
    }""", chapter)
    return marks_place(state) if sub_at_line else state['lit'] == ['sec:' + chapter]


EMPTY_POINT = """root => {
 const main=document.querySelector('.app-main'), mr=main.getBoundingClientRect();
 const bad=e=>!e || !!e.closest('a,button,input,select,summary,[role=button],img,svg,.hs-text,.hs-figure,.verse-chips,.mood-toggle,[data-no-reader-tap]');
 for(const e of root.querySelectorAll('h1,h2,p')) {
   if(e.closest('[data-hs-row]') || e.querySelector('a,button,.hs-text')) continue;
   const r=e.getBoundingClientRect();
   if(r.width<100 || r.top<90 || r.top>innerHeight-180 || r.bottom<100) continue;
   const point={x:r.left+Math.min(r.width/2,70),y:r.top+Math.min(r.height/2,18)};
   if(!bad(document.elementFromPoint(point.x,point.y))) return point;
 }
 for(const y of [140,260,400,innerHeight*.65]) {
   const point={x:mr.left+30,y};
   if(!bad(document.elementFromPoint(point.x,point.y))) return point;
 }
 return {x:mr.left+6,y:innerHeight/2};
}"""


def locator_navigates(locator):
    """Rows that can open another page: chapters, subsections, cover, parts."""
    try:
        return locator.evaluate("e => !!e.closest('.mobile-menu') && !!e.closest('a[href],[data-toc-chapter],[data-toc-row],[data-toc-toggle]')")
    except Exception:
        return False


class Contents:
    def __init__(self, page, mode, touch):
        self.page, self.mode, self.touch = page, mode, touch
        observer = """(() => {
          if(window.__qaTocObserved)return;window.__qaTocObserved=true;window.__qaTocPushes=0;window.__qaTocWithoutGesture=[];
          const push=history.pushState;history.pushState=function(...args){window.__qaTocPushes++;if(navigator.userActivation&&!navigator.userActivation.isActive)window.__qaTocWithoutGesture.push(args[2]);return push.apply(this,args)};
          window.__qaFetching=0;const f=window.fetch;window.fetch=function(...args){window.__qaFetching++;return f.apply(this,args).finally(()=>{window.__qaFetching--})};
        })()"""
        page.add_init_script(observer);page.evaluate(observer)

    def settle(self, before_url=None, quiet_ms=1500, limit_ms=6000):
        """Chapter by chapter (no continuous book) a contents tap or Back opens
        another page: WebKit needs up to ~1.5 s for that, with no fetch in flight
        when the page was prefetched. Wait for the URL to change (or stay put
        for quiet_ms), then for fetches to finish and the page to render."""
        if self.page.evaluate("!!document.querySelector('[data-continuous-book]')"):
            return
        waited, changed = 0, False
        while waited < limit_ms:
            try:
                url, busy = self.page.evaluate("[location.href, window.__qaFetching || 0]")
            except Exception:
                url, busy = None, 1
            if url is not None and before_url is not None and url != before_url:
                changed = True
            if changed and not busy:
                self.page.wait_for_timeout(300)
                return
            if not changed and waited >= quiet_ms and not busy:
                return
            self.page.wait_for_timeout(100); waited += 100

    def state(self):
        return self.page.evaluate(STATE)

    def tap(self, locator, wait=180, right=False):
        if right and not self.mode.one:
            chapter = locator.get_attribute('data-toc-chapter')
            if chapter:
                toggle = self.page.locator(f"[data-toc-toggle='{chapter}']")
                if toggle.count(): locator = toggle
        locator.scroll_into_view_if_needed()
        box = locator.bounding_box()
        point={'x':box['width']-9 if right else min(60,box['width']/2),'y':box['height']/2}
        before, navigates = self.page.url, locator_navigates(locator)
        (locator.tap if self.touch else locator.click)(position=point)
        self.page.wait_for_timeout(wait)
        if navigates:
            self.settle(before)

    def bars(self):
        for _ in range(3):
            if self.state()['menu'] or self.page.locator('.reader-chrome[data-shown]').count(): return
            self.page.wait_for_timeout(180)  # a tap must not merely stop a scroll
            cover=self.page.locator('[data-reader-current] img.home-cover')
            if cover.count():
                (cover.tap if self.touch else cover.click)()
            else:
                p=qa.reading_eval(self.page, EMPTY_POINT)
                (self.page.touchscreen.tap if self.touch else self.page.mouse.click)(p['x'],p['y'])
            self.page.wait_for_timeout(220)

    def contents(self):
        self.bars();self.tap(self.page.locator('[data-reader-action=contents]'),wait=350)

    def group(self, id):
        return self.page.locator(f'.mobile-menu [data-toc-group="{id}"]')

    def chapter(self, id):
        return self.page.locator(f'.mobile-menu [data-toc-chapter="{id}"]')

    def row(self, id):
        return self.page.locator(f'.mobile-menu [data-toc-row="{id}"]')

    def activate(self, locator, wait=350):
        self.tap(locator,wait=wait)
        if not self.mode.one:self.tap(locator,wait=wait)

    def nav(self, direction, native=False):
        before = self.page.url
        if native:
            (self.page.go_back if direction=='back' else self.page.go_forward)()
        else:
            self.bars();self.tap(self.page.locator(f'[data-reader-nav={direction}]'),wait=0)
        self.page.wait_for_timeout(650)
        self.settle(before, quiet_ms=600)


def history_roundtrip(browser, options, mode, check, base, lang='ru-iast'):
    """Four real steps versus seven: numeric counts AND every restored state.

    One-tap mark() updates the entry being left. Expected snapshots account
    for that trace explicitly; snapshots are never learned from Back results.
    """
    context=browser.new_context(service_workers='block',**options)
    context.add_init_script("localStorage.setItem('ap.readerHintSeen','1')")
    page=context.new_page();flow=Contents(page,mode,options.get('has_touch',False))
    chapter='arcana-procedure';sub=f'sub:{chapter}#2-svagata'
    prefix='' if lang=='en' else '/'+lang
    try:
        mode.start(page,base+prefix+'/');page.wait_for_timeout(400)
        states=[flow.state()];start=states[0]['history']
        flow.contents();states.append(flow.state())
        check('history: Contents opens one entry',states[-1]['history']==start+1)
        for kind,id,row_id in [('group','temple-worship','grp:temple-worship'),('chapter',chapter,'sec:'+chapter)]:
            loc=flow.group(id) if kind=='group' else flow.chapter(id)
            before=flow.state()
            flow.tap(loc,right=True,wait=350);after=flow.state()
            # One tap (13.10.2026): opening a chapter moves the reading place to
            # its top, so the mark follows it; expanding a group moves nobody,
            # so the mark stays where the reader is.
            check(f'history: {kind} tap marks the place being read',
                  (after['lit']==[row_id] if kind=='chapter' else after['lit']==before['lit']) if mode.one
                  else after['lit']==[row_id],str(after))
            check(f'history: {kind} first tap has exactly one action entry',after['history']==before['history']+1,str(after))
            check(f'history: {kind} first tap expands by mode',(id in after['open'])==mode.one,str(after))
            if kind=='chapter':
                top=page.evaluate(qa.READING_POSITION_JS)['top']
                check('history: chapter first tap opens its top, never a subsection',
                      after['url'].endswith('/'+chapter+'/') and '#' not in after['url'] and abs(top)<2 if mode.one else after['url']==before['url'],str(after))
            states.append(after)
            if not mode.one:
                flow.tap(loc,right=True,wait=350);after=flow.state();states.append(after)
                check(f'history: {kind} second tap expands with one entry',id in after['open'] and after['history']==before['history']+2 and after['url']==before['url'],str(after))
        check('history: subsection list visible without an extra tap',flow.row(sub).is_visible())
        before=flow.state()
        if not mode.one:
            flow.tap(flow.row(sub),wait=250);after=flow.state();states.append(after)
            check('history: legacy subsection first tap highlights only',after['lit']==[sub] and after['menu'] and after['url']==before['url'] and after['history']==before['history']+1,str(after))
        before_nav=flow.state()['history'];flow.tap(flow.row(sub),wait=500);target=flow.state();states.append(target)
        check('history: subsection opens in one navigation entry',not target['menu'] and target['url'].endswith('/'+chapter+'/#2-svagata') and target['history']==before_nav+1,str(target))
        expected=4 if mode.one else 7
        check('history: cover to subsection action count',target['history']-start==expected,str(target['history']-start))
        bad=[];back_count=0
        for want in reversed(states[:-1]):
            flow.nav('back',native=back_count%2==1);back_count+=1;got=flow.state()
            if any(got[k]!=want[k] for k in ['url','menu','open']) or not marks_place(got):bad.append({'press':back_count,'got':got,'want':want})
        check('history: Back restores every URL and open list, marking the place',not bad,str(bad[:2]))
        check('history: Back presses from subsection to cover',back_count==expected and not flow.state()['menu'] and flow.state()['url']==states[0]['url'],str(back_count))
        bad=[];forward_count=0
        for want in states[1:]:
            flow.nav('forward',native=forward_count%2==1);forward_count+=1;got=flow.state()
            if any(got[k]!=want[k] for k in ['url','menu','open']) or not marks_place(got):bad.append({'press':forward_count,'got':got,'want':want})
        check('history: Forward restores every URL and open list, marking the place',not bad,str(bad[:2]))
        check('history: Forward presses from cover to subsection',forward_count==expected and flow.state()['url']==target['url'] and not flow.state()['menu'],str(forward_count))
        flow.nav('back');before=flow.state()
        flow.tap(flow.chapter(chapter),right=True,wait=300);first=flow.state()
        if not mode.one:
            check('history: restored legacy chapter first tap only highlights',chapter in first['open'] and first['lit']==['sec:'+chapter] and first['url']==before['url'])
            flow.tap(flow.chapter(chapter),right=True,wait=300)
        after=flow.state()
        check('history: second chapter tap collapses without navigating',chapter not in after['open'] and after['url']==before['url'] and after['lit']==['sec:'+chapter],str(after))
        if page.evaluate('!!navigator.userActivation'):
            check('history: every pushState has a user gesture',page.evaluate('window.__qaTocWithoutGesture.length')==0)
        check('history: collapse pushes only its action entry',after['pushes']-before['pushes']==(1 if mode.one else 2),str(after))
        flow.nav('back');after=flow.state()
        check('history: Back restores the collapsed chapter list',chapter in after['open'] and after['url']==before['url'],str(after))

    finally:context.close()
