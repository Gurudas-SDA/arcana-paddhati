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
  /** Shown after the source line, e.g. for a private recording without public links. */
  note?: string;
  /** Language of title/note when not English (BCP 47; default "en"). */
  lang?: string;
}

/** One more candidate quote of a "mood" block (shown after the chosen one in the overlay). */
export interface MoodQuote {
  quote: string;
  translation?: string;
  /** "machine" when `translation` is a machine translation. */
  translation_note?: string;
  source?: MoodSource;
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
  /** "list" block: explicit number label per line (e.g. picture numbers "4, 5"); "" = unnumbered.
   *  "paired-list" block (table layout): number label per row, e.g. the numbers of the illustration. */
  numbers?: string[];
  /** "mood" block: Gurudev's own words (English, verbatim). */
  quote?: string;
  /** "mood" block: "machine" when `translation` is a machine translation. */
  translation_note?: string;
  source?: MoodSource;
  /** "mood" block: the other quotes for this block (shown after the chosen one in the overlay, best first). */
  more?: MoodQuote[];
  /** "table" block: column headings (the first column labels each row, e.g. the year). */
  header?: string[];
  /** "table" block: rows; `highlight` marks a row (e.g. a year with Puruṣottama-māsa), `badge` is shown with it. */
  rows?: TableRow[];
}

/** One row of a "table" block. */
export interface TableRow {
  cells: string[];
  highlight?: boolean;
  /** Short label shown on a highlighted row (phone cards) — e.g. "Puruṣottama-māsa". */
  badge?: string;
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

/**
 * A part of the book (Part I "Temple worship", II "Home worship", …): a
 * grouping level above the chapters. `sections` lists the ids of its
 * chapters in order; an empty list = part still in preparation. Front matter
 * belongs to no part and comes before Part I.
 */
export interface Part {
  id: string;
  title: string;
  sections: string[];
}

export interface Book {
  title: string;
  subtitle: string;
  parts?: Part[];
  sections: Section[];
}

/** Slim part shape for client components; numeral = "I", "II", … */
export interface TocPart {
  id: string;
  title: string;
  numeral: string;
  sections: string[];
}

/** One row of the reading order: a part heading or a section. */
export type TocItem = { kind: "part"; id: string } | { kind: "section"; id: string };

/**
 * Reading order of sections and part headings: sections in book order; each
 * part's heading is placed just before its first section (parts without
 * sections — in preparation — right after the previous part's sections,
 * remaining ones at the end).
 */
export function tocLayout(sectionIds: string[], parts: { id: string; sections: string[] }[]): TocItem[] {
  const partOf = new Map<string, number>();
  parts.forEach((p, i) => p.sections.forEach((id) => partOf.set(id, i)));
  const out: TocItem[] = [];
  let emitted = 0;
  for (const id of sectionIds) {
    const p = partOf.get(id);
    if (p !== undefined) {
      while (emitted <= p) out.push({ kind: "part", id: parts[emitted++].id });
    } else if (emitted > 0) {
      // A section outside any part after Part I has started: flush empty parts first.
      while (emitted < parts.length && parts[emitted].sections.length === 0) {
        out.push({ kind: "part", id: parts[emitted++].id });
      }
    }
    out.push({ kind: "section", id });
  }
  while (emitted < parts.length) out.push({ kind: "part", id: parts[emitted++].id });
  return out;
}

/** 1 -> "I", 4 -> "IV", … (part numbers). */
export function toRoman(n: number): string {
  const table: [number, string][] = [
    [1000, "M"], [900, "CM"], [500, "D"], [400, "CD"], [100, "C"], [90, "XC"],
    [50, "L"], [40, "XL"], [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"],
  ];
  let out = "";
  for (const [v, s] of table) {
    while (n >= v) {
      out += s;
      n -= v;
    }
  }
  return out;
}

/** Slim table-of-contents shape passed to client components (no body text). */
export interface TocSection {
  id: string;
  title: string;
  page: string;
  /** Chapter number ("1", "2", …). See sectionNumbers(). */
  num: string | null;
  /** num = "2.1", "2.2", … */
  subsections: { id: string; title: string; num: string | null }[];
}

/**
 * Chapter numbers computed from the section order (never stored in the book
 * texts, so every language gets the same numbers): every section is numbered,
 * front matter included (Introduction 1, Maṅgalācaraṇa 2, then the chapters
 * of Part I 3, 4, …; owner's decision 2026-10-02).
 */
export function sectionNumbers(sections: { page: string }[]): (number | null)[] {
  return sections.map((_, i) => i + 1);
}

/** "2.1"-style number of the i-th (0-based) subsection of chapter `num`. */
export function subsectionNumber(num: number | string | null, i: number): string | null {
  return num == null ? null : `${num}.${i + 1}`;
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
