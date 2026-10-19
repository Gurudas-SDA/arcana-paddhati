"use client";

// Where the reader stopped (Vraja Lila msg 5316 p. 5, plan «Закладки» B1,
// 20.10.2026): kept on the device, silently — nothing on screen changes here.
// The cover's «Продолжить» card (components/ResumeCard.tsx) reads it.
//   ap.readingPlace = {v: 1, section, anchor (subsection id or null), block,
//                      offset, lang, time}
// Written when scrolling stops (~1 s) and when the page is hidden/closed. The
// section and the subsection anchor are the same in all 12 languages; block +
// offset apply only in the language they were taken in. The cover never
// writes (it is not a reading place), so «Обложка» does not erase the place.
// No storage (private mode, blocked): kept in memory until reload.
import { capturePlace } from "./readingMode";
import { readingSubsection } from "./readingPosition";
import { liveLang } from "./i18n";
import { READING_PLACE_KEY } from "./homeCards";

export { READING_PLACE_KEY };

export interface ReadingPlace {
  v: 1;
  section: string;
  anchor: string | null;
  block: number;
  offset: number;
  lang: string;
  time: number;
}

let mem: ReadingPlace | null = null;

function valid(v: unknown): v is ReadingPlace {
  const p = v as ReadingPlace;
  return !!p && p.v === 1 && typeof p.section === "string" && typeof p.lang === "string";
}

/** The stored place; a retired language becomes its replacement (liveLang: ru -> ru-iast). */
export function readReadingPlace(): ReadingPlace | null {
  let p: ReadingPlace | null = mem;
  try {
    const raw = localStorage.getItem(READING_PLACE_KEY);
    if (raw) {
      const v: unknown = JSON.parse(raw);
      if (valid(v)) p = v;
    }
  } catch {
    // storage unavailable
  }
  return p ? { ...p, lang: liveLang(p.lang) } : null;
}

/** Take the place of the chapter on screen (chapter by chapter); null on the cover. */
export function captureReadingPlace(lang: string, subsectionIds: string[]): ReadingPlace | null {
  const place = capturePlace();
  if (!place) return null;
  const sub = readingSubsection(subsectionIds);
  return {
    v: 1,
    section: place.sectionId,
    anchor: sub ?? null,
    block: place.index,
    offset: Math.round(place.delta),
    lang: liveLang(lang),
    time: Date.now(),
  };
}

export function saveReadingPlace(p: ReadingPlace) {
  mem = p;
  try {
    localStorage.setItem(READING_PLACE_KEY, JSON.stringify(p));
  } catch {
    // no storage: in memory until reload
  }
}
