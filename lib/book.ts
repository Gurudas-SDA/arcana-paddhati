// Book types and client-safe helpers. Loading the book (per language) is
// server-only: see lib/content.ts.

export interface PairedItem {
  label: string;
  value: string;
}

export interface ContentItem {
  type: string;
  content?: string;
  sanskrit?: string;
  translation?: string;
  /** Word-by-word meanings of a verse: "word — meaning; word — meaning; …". */
  wbw?: string;
  src?: string;
  alt?: string;
  items?: PairedItem[];
  layout?: string;
}

export interface Subsection {
  id: string;
  title: string;
  content: ContentItem[];
}

export interface Section {
  id: string;
  title: string;
  subtitle?: string | null;
  page: string;
  content: ContentItem[];
  subsections: Subsection[];
}

export interface Book {
  title: string;
  subtitle: string;
  sections: Section[];
}

/** Slim table-of-contents shape passed to client components (no body text). */
export interface TocSection {
  id: string;
  title: string;
  page: string;
  subsections: { id: string; title: string }[];
}

/** One entry of public/search-index.<lang>.json (see scripts/build-search-index.mjs). */
export interface SearchEntry {
  section: string;
  anchor?: string;
  title: string;
  sectionTitle: string;
  text: string;
}

/** Lowercase and strip combining diacritics (NFD). */
export function normalizeText(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

/** Sanskrit is given in IAST or (Russian/Ukrainian editions) in Cyrillic. */
export function sanskritLang(text: string | undefined) {
  return text && /[Ѐ-ӿ]/.test(text) ? "sa-Cyrl" : "sa-Latn";
}

export interface WbwPair {
  word: string;
  /** Empty when the entry has no " — meaning" part. */
  meaning: string;
}

/** Split a verse's `wbw` string ("word — meaning; word — meaning") into pairs. */
export function parseWbw(wbw: string): WbwPair[] {
  return wbw
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const m = part.match(/^(.*?)\s+[—–-]\s+(.*)$/);
      return m ? { word: m[1].trim(), meaning: m[2].trim() } : { word: part, meaning: "" };
    });
}
