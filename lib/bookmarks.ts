"use client";

// Bookmarks on the device (plan «Закладки» B1/B3, Vraja Lila msg 5316 p. 7):
//   ap.bookmarks = {v: 1, items: [{id, section, anchor, block, lang, time}]}
// newest first, at most 500. The second line of a row is NOT stored as text:
// only the anchor; the line is taken from the current language's contents when
// shown. The reading place (lib/readingPlace.ts) never goes in here. Setting a
// bookmark (A / B / V) is not built yet — this is the list only.
import { liveLang } from "./i18n";

export const BOOKMARKS_KEY = "ap.bookmarks";
export const BOOKMARKS_MAX = 500;

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
}
