// Book types and client-safe helpers. Loading the book (per language) is
// server-only: see lib/content.ts.

export interface PairedItem {
  label: string;
  value: string;
}

/** Source of a "mood" quote: the lecture it was taken from. */
export interface MoodSource {
  title: string;
  date?: string;
  /** Archive number of the lecture. */
  nr?: string;
  /** Start of the transcript block containing the quote (hh:mm:ss). */
  timecode?: string;
  transcript_url?: string;
  audio_url?: string;
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
  /** "list" block: explicit number label per line (e.g. picture numbers "4, 5"); "" = unnumbered. */
  numbers?: string[];
  /** "mood" block: Gurudev's own words (English, verbatim). */
  quote?: string;
  /** "mood" block: "machine" when `translation` is a machine translation. */
  translation_note?: string;
  source?: MoodSource;
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

/** Inline Sanskrit inside running text is marked ⟦…⟧ in the book data. */
export const INLINE_SA_OPEN = "⟦";
export const INLINE_SA_CLOSE = "⟧";

export interface TextRun {
  text: string;
  /** True for a ⟦…⟧ run (Sanskrit / mantra fragment). */
  sanskrit: boolean;
}

/** Split running text into plain and ⟦Sanskrit⟧ runs. */
export function parseInline(text: string): TextRun[] {
  const runs: TextRun[] = [];
  const re = /⟦([^⟦⟧]*)⟧/g;
  let last = 0;
  for (let m = re.exec(text); m; m = re.exec(text)) {
    if (m.index > last) runs.push({ text: text.slice(last, m.index), sanskrit: false });
    runs.push({ text: m[1], sanskrit: true });
    last = m.index + m[0].length;
  }
  if (last < text.length) runs.push({ text: text.slice(last), sanskrit: false });
  return runs;
}

/** Running text without the ⟦…⟧ markers. */
export function stripInline(text: string): string {
  return text.replace(/[⟦⟧]/g, "");
}
