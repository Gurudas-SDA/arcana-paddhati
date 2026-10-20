"use client";

// Bookmarks on the device (plan «Закладки» B1/B3, Vraja Lila msg 5316 p. 7):
//   ap.bookmarks = {v: 1, items: [{id, section, anchor, block, lang, time}]}
// newest first, at most 500. The second line of a row is NOT stored as text:
// only the anchor; the line is taken from the current language's contents when
// shown. The reading place (lib/readingPlace.ts) never goes in here.
// Setting one: variant A (Vraja Lila msg 5380) — the ribbon button in the top
// bar (components/ReaderChrome.tsx); a second tap on the same place removes it.
import { liveLang } from "./i18n";

export const BOOKMARKS_KEY = "ap.bookmarks";
export const BOOKMARKS_MAX = 500;
/** Fired on window after every write (the button and the list follow it). */
export const BOOKMARKS_EVENT = "ap:bookmarks";

export interface Bookmark {
  id: string;
  section: string;
  anchor: string | null;
  block: number;
  lang: string;
  time: number;
}

let mem: Bookmark[] = [];

export function readBookmarks(): Bookmark[] {
  let items = mem;
  try {
    const raw = localStorage.getItem(BOOKMARKS_KEY);
    if (raw) {
      const v = JSON.parse(raw) as { v?: number; items?: unknown };
      if (v && v.v === 1 && Array.isArray(v.items)) {
        items = (v.items as Bookmark[]).filter((b) => b && typeof b.section === "string" && typeof b.id === "string");
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

/** Set the bookmark on this place, or remove it if it is there (rule 10.1).
 *  Returns whether it was added and the list before (for «Отменить»). */
export function toggleBookmark(section: string, anchor: string | null, block: number, lang: string): { added: boolean; before: Bookmark[] } {
  const before = readBookmarks();
  const here = bookmarkAt(before, section, anchor);
  if (here) {
    writeBookmarks(before.filter((b) => b.id !== here.id));
    return { added: false, before };
  }
  const now = Date.now();
  const id = `${now.toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
  writeBookmarks([{ id, section, anchor, block, lang: liveLang(lang), time: now }, ...before]);
  return { added: true, before };
}
