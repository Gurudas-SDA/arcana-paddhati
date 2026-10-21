"use client";

// Bookmarks on the device (plan «Закладки» B1/B3, Vraja Lila msg 5316 p. 7):
//   ap.bookmarks = {v: 1, items: [{id, section, anchor, block, lang, time, name?}]}
// newest first, at most 500. The second line of a row is NOT stored as text:
// only the anchor; the line is taken from the current language's contents when
// shown. The reading place (lib/readingPlace.ts) never goes in here.
// Setting one: variant A (Vraja Lila msg 5380) — the ribbon button in the top
// bar (components/ReaderChrome.tsx); a second tap on the same place removes it.
// Name (V34, Satkirti msg 5866, Vraja Lila msg 5869): setting one opens a window
// with the chapter's (subsection's) name, which can be changed; the pencil on a
// row of «Закладки» opens it again. Only a name that differs from that default
// is stored (`name`); old bookmarks and unchanged names have none and show as
// before (chapter + subsection, in the current language).
import { liveLang, parsePath } from "./i18n";
import { stripBasePath } from "./basePath";
import { BLOCKS } from "./readingMode";
import { main } from "./navHistory";
import { readingSection } from "./readingFlow";

export const BOOKMARKS_KEY = "ap.bookmarks";
export const BOOKMARKS_MAX = 500;
/** The longest name the window takes. */
export const BOOKMARK_NAME_MAX = 120;
/** Fired on window after every write (the button and the list follow it). */
export const BOOKMARKS_EVENT = "ap:bookmarks";
/** «Закладка убрана · Отменить» asked from elsewhere (the «Закладки» list,
 *  Vraja Lila msg 5439/5440 variant 2а): detail = {undo: list before}. The top
 *  bar (components/ReaderChrome.tsx) shows its own toast for it — one toast. */
export const BOOKMARK_TOAST_EVENT = "ap:bookmark-toast";
/** Fired by the top bar when its bookmark toast is over (time out or «Отменить»). */
export const BOOKMARK_TOAST_END_EVENT = "ap:bookmark-toast-end";

export interface Bookmark {
  id: string;
  section: string;
  anchor: string | null;
  block: number;
  lang: string;
  time: number;
  /** The reader's own name (V34); absent = the chapter's / subsection's name. */
  name?: string;
}

type NamedPart = { title: string; num: string | null };

/** The window's default name: the subsection's name (with its number), or the
 *  chapter's when the place has no subsection — as the «Закладки» rows read. */
export function defaultBookmarkName(sec: NamedPart & { subsections: ({ id: string } & NamedPart)[] }, anchor: string | null): string {
  const sub = anchor ? sec.subsections.find((x) => x.id === anchor) : undefined;
  const part: NamedPart = sub ?? sec;
  return part.num ? `${part.num}. ${part.title}` : part.title;
}

/** A name worth keeping: trimmed, not empty, not the default one. */
export function ownName(name: string | undefined, defaultName: string): string | undefined {
  const n = (name ?? "").trim().slice(0, BOOKMARK_NAME_MAX);
  return n && n !== defaultName.trim() ? n : undefined;
}

let mem: Bookmark[] = [];

export function readBookmarks(): Bookmark[] {
  let items = mem;
  try {
    const raw = localStorage.getItem(BOOKMARKS_KEY);
    if (raw) {
      const v = JSON.parse(raw) as { v?: number; items?: unknown };
      if (v && v.v === 1 && Array.isArray(v.items)) {
        items = (v.items as Bookmark[])
          .filter((b) => b && typeof b.section === "string" && typeof b.id === "string")
          .map((b) => (b.name === undefined || (typeof b.name === "string" && b.name.trim()) ? b : { ...b, name: undefined }));
      }
    }
  } catch {
    // storage unavailable
  }
  return items.map((b) => ({ ...b, lang: liveLang(b.lang) })).sort((a, b) => b.time - a.time);
}

export function writeBookmarks(items: Bookmark[]) {
  mem = [...items].sort((a, b) => b.time - a.time).slice(0, BOOKMARKS_MAX);
  try {
    localStorage.setItem(BOOKMARKS_KEY, JSON.stringify({ v: 1, items: mem }));
  } catch {
    // no storage: in memory until reload
  }
  try {
    window.dispatchEvent(new Event(BOOKMARKS_EVENT));
  } catch {
    // no window (server)
  }
}

/** The bookmark on this place: same chapter and same subsection (any language). */
export function bookmarkAt(items: Bookmark[], section: string, anchor: string | null): Bookmark | undefined {
  return items.find((b) => b.section === section && (b.anchor ?? null) === (anchor ?? null));
}

/** The bookmark on this exact place (V34, Vraja Lila msg 5881: «в разделе может
 *  быть несколько закладок»): the same block of the same chapter, taken in this
 *  language. A place without a measured block (0) falls back to chapter +
 *  subsection among such bookmarks. Rule 10.1 applies to this place. */
export function bookmarkAtPlace(items: Bookmark[], section: string, block: number, lang: string, anchor: string | null): Bookmark | undefined {
  if (block > 0) return items.find((b) => b.section === section && b.block === block && liveLang(b.lang) === liveLang(lang));
  return items.find((b) => b.section === section && !(b.block > 0) && (b.anchor ?? null) === (anchor ?? null));
}

/** Remove one bookmark (the icon on its row in «Закладки») and show the top
 *  bar's toast «Закладка убрана · Отменить», which can put the list back. */
export function removeBookmark(id: string) {
  const before = readBookmarks();
  writeBookmarks(before.filter((b) => b.id !== id));
  try {
    window.dispatchEvent(new CustomEvent(BOOKMARK_TOAST_EVENT, { detail: { undo: before } }));
  } catch {
    // no window (server)
  }
}

/** Rename one bookmark (the pencil in «Закладки», V34); `name` undefined = back
 *  to the chapter's / subsection's name. No toast, no history step. */
export function renameBookmark(id: string, name: string | undefined) {
  const items = readBookmarks();
  if (!items.some((b) => b.id === id)) return;
  writeBookmarks(items.map((b) => {
    if (b.id !== id) return b;
    const next = { ...b };
    if (name) next.name = name;
    else delete next.name;
    return next;
  }));
}

/** Set the bookmark on this place, or remove it if it is there (rule 10.1).
 *  Returns whether it was added and the list before (for «Отменить»). */
export function toggleBookmark(section: string, anchor: string | null, block: number, lang: string, name?: string): { added: boolean; before: Bookmark[] } {
  const before = readBookmarks();
  const here = bookmarkAtPlace(before, section, block, lang, anchor);
  if (here) {
    writeBookmarks(before.filter((b) => b.id !== here.id));
    return { added: false, before };
  }
  const now = Date.now();
  const id = `${now.toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
  const item: Bookmark = { id, section, anchor, block, lang: liveLang(lang), time: now };
  if (name) item.name = name;
  writeBookmarks([item, ...before]);
  return { added: true, before };
}

// ---- the exact place (V34, Vraja Lila msg 5872) ----------------------------------
// «хочу иметь возможность делать закладку на конкретном месте в главе… мантра,
// которую я учу… поставить закладку там и назвать „Мантра при пробуждении“… и
// тогда легко вернуться конкретно к этому месту». `block` = the text block (lib/
// readingMode.ts BLOCKS) at the top of what is visible — below the top bar when
// it is out — in «Страницы» and «Лента» alike. Opening the bookmark in the same
// language brings that block back a little below the top and lights it for a
// moment; in another language (other blocks) — its subsection, as before.

/** Where the opened block stands: right below the top bar, all of it visible
 *  (Vraja Lila msg 5883 — like a chapter's title, V25). */
const PLACE_GAP_PX = 10;
/** html attribute while a bookmark's block is being put in place: the anchor
 *  keeper (components/AppShell.tsx) leaves the scroll alone meanwhile. */
export const BOOKMARK_PLACE_ATTR = "data-bookmark-place";

/** The index of the first block a reader sees at the top: the first that starts
 *  below the top bar, or one cut by it that still shows most of itself. The bar's
 *  height counts whether it is out or not, so the place does not change when
 *  the bars come and go. */
export function captureBookmarkBlock(): number | null {
  const scroller = main();
  const root = readingSection();
  if (!scroller || !root) return null;
  const bar = document.querySelector<HTMLElement>(".reader-bar-top");
  const line = scroller.getBoundingClientRect().top + (bar ? bar.offsetHeight : 0);
  const blocks = [...root.querySelectorAll<HTMLElement>(BLOCKS)];
  for (let i = 0; i < blocks.length; i++) {
    const r = blocks[i].getBoundingClientRect();
    if (!r.height || r.bottom <= line + 24) continue;
    if (r.top >= line - 8 || r.bottom - line >= r.height / 2) return i;
  }
  return null;
}

/** The bookmark keeps its own block (taken in this language, not the chapter's start). */
export function hasExactPlace(b: Bookmark, lang: string): boolean {
  return b.block > 0 && liveLang(b.lang) === liveLang(lang);
}

let stopPlacing: (() => void) | null = null;

/** After the move to the bookmark's chapter: put its block a little below the top
 *  (re-applied while pictures above it load; the reader's own touch stops it) and
 *  light it once. Gives up after 5 s if the chapter never shows. */
export function placeBookmark(b: Bookmark) {
  stopPlacing?.();
  const root = document.documentElement;
  root.setAttribute(BOOKMARK_PLACE_ATTR, "");
  const t0 = performance.now();
  let stopped = false;
  let lit = false;
  let found = 0;
  const timers: number[] = [];
  const events = ["touchstart", "wheel", "keydown", "pointerdown"] as const;
  const stop = () => {
    if (stopped) return;
    stopped = true;
    timers.forEach((t) => window.clearTimeout(t));
    for (const ev of events) window.removeEventListener(ev, onTouch, { capture: true });
    root.removeAttribute(BOOKMARK_PLACE_ATTR);
    if (stopPlacing === stop) stopPlacing = null;
  };
  // A touch inside the open contents (the tap that chose this row) does not count.
  const onTouch = (e: Event) => {
    if (performance.now() - t0 < 400) return;
    if ((e.target as Element | null)?.closest?.(".mobile-menu")) return;
    stop();
  };
  for (const ev of events) window.addEventListener(ev, onTouch, { passive: true, capture: true });
  const tick = () => {
    if (stopped) return;
    const now = performance.now();
    const here = parsePath(stripBasePath(window.location.pathname) || "/").sectionId === b.section;
    const scroller = main();
    const sec = here ? readingSection() : null;
    const block = sec?.querySelectorAll<HTMLElement>(BLOCKS)[b.block];
    if (scroller && block && (!b.anchor || sec?.querySelector(`[id="${CSS.escape(b.anchor)}"]`))) {
      if (!found) found = now;
      const bar = document.querySelector<HTMLElement>(".reader-bar-top")?.offsetHeight ?? 0;
      const d = block.getBoundingClientRect().top - scroller.getBoundingClientRect().top - bar - PLACE_GAP_PX;
      if (Math.abs(d) > 2) scroller.scrollTop += d;
      if (!lit && now - found > 250) {
        lit = true;
        block.classList.remove("bookmark-flash");
        void block.offsetWidth;
        block.classList.add("bookmark-flash");
        window.setTimeout(() => block.classList.remove("bookmark-flash"), 2700);
      }
      if (now - found > 2500) return stop();
    } else if (now - t0 > 5000) {
      return stop();
    }
    timers.push(window.setTimeout(tick, found ? 120 : 60));
  };
  stopPlacing = stop;
  requestAnimationFrame(tick);
}

/** «Примерно на том же месте» (Vraja Lila msg 5882/5883: «можем померить
 *  определённой порцией скролла»): a bookmark's block is at most this part of the
 *  reading area's height away from the reading line (just below the top bar). */
export const NEAR_SCREEN_PART = 0.5;

/** The bookmark about here: one of this chapter (this language) whose block is
 *  within NEAR_SCREEN_PART of a screen from the reading line; several — the
 *  nearest. Old bookmarks without a block: chapter + subsection, as before. */
export function bookmarkOnScreen(items: Bookmark[], section: string, lang: string, anchor: string | null): Bookmark | undefined {
  const mine = items.filter((b) => b.section === section);
  const exact = mine.filter((b) => b.block > 0 && liveLang(b.lang) === liveLang(lang));
  const scroller = main();
  const root = readingSection();
  if (exact.length && scroller && root) {
    const sr = scroller.getBoundingClientRect();
    const topBar = document.querySelector<HTMLElement>(".reader-bar-top")?.offsetHeight ?? 0;
    const line = sr.top + topBar;
    const limit = (sr.height - topBar) * NEAR_SCREEN_PART;
    const blocks = root.querySelectorAll<HTMLElement>(BLOCKS);
    let best: Bookmark | undefined;
    let bestD = Infinity;
    for (const b of exact) {
      const r = blocks[b.block]?.getBoundingClientRect();
      if (!r || !r.height) continue;
      const d = Math.abs(r.top - line);
      if (d <= limit && d < bestD) {
        bestD = d;
        best = b;
      }
    }
    if (best) return best;
  }
  return mine.find((b) => !(b.block > 0) && (b.anchor ?? null) === (anchor ?? null));
}
