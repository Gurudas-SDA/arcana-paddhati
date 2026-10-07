// Book types and client-safe helpers. Loading the book (per language) is
// server-only: see lib/content.ts.

export interface PairedItem {
  label: string;
  value: string;
  /** Word-by-word of the mantra in this row (a «пословно» chip). */
  wbw?: string;
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
  /** "sources" block (the source line of an intro chapter): links per line of `content`, shown after that line. */
  links?: (SourceLinks | null)[];
  /** "portrait" block (parampara page): the name under the portrait (`src` = the framed oval picture). */
  caption?: string;
}

/** Transcript / audio links of one lecture in a "sources" block. */
export interface SourceLinks {
  transcript_url?: string;
  audio_url?: string;
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
  /** "portraits": a parampara section — one portrait per screen/page, no visible heading
   *  (Satkirti 06.10/07.10.2026: portrait + caption only, no headings, no page numbers). */
  layout?: string;
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
  /** Head of the front-matter group (the Introduction): ids of the chapters
   *  inside it (Emblem, Vigraha-tattva). See frontGroup(). */
  members?: string[];
  /** A chapter inside the front-matter group: the group head's id. */
  group?: string;
}

/**
 * The Introduction is an expandable group of the contents, like a part
 * (Satkirti, 06.10.2026): the front matter (the sections before Part I's
 * first chapter, outside any part) — its first section is the group's head
 * ("Introduction"), the rest are its chapters (Emblem, Vigraha-tattva,
 * Maṅgalācaraṇa) and have no chapter numbers of their own.
 */
export function frontGroup(
  sectionIds: string[],
  parts: { sections: string[] }[],
): { head: string; members: string[] } | null {
  const inPart = new Set(parts.flatMap((p) => p.sections));
  const front: string[] = [];
  for (const id of sectionIds) {
    if (inPart.has(id)) break;
    front.push(id);
  }
  // Front matter before the Introduction (the Maṅgalācaraṇa — Satkirti,
  // 06.10.2026: cover → maṅgalācaraṇa → Introduction) stands on its own.
  const at = front.indexOf(INTRO_ID);
  const h = at >= 0 ? at : 0;
  const members = front.slice(h + 1);
  return members.length >= 1 ? { head: front[h], members } : null;
}

/** Id of the Introduction (head of the front-matter group). */
export const INTRO_ID = "introduction";

/** Sections before Part I's first chapter, outside any part (no chapter numbers). */
export function frontMatter(sectionIds: string[], parts: { sections: string[] }[]): string[] {
  const inPart = new Set(parts.flatMap((p) => p.sections));
  const front: string[] = [];
  for (const id of sectionIds) {
    if (inPart.has(id)) break;
    front.push(id);
  }
  return front;
}

/**
 * Chapter numbers computed from the section order (never stored in the book
 * texts, so every language gets the same numbers). The front matter (the
 * Introduction group: Introduction, Emblem, Vigraha-tattva, Maṅgalācaraṇa)
 * has no chapter numbers (Satkirti, 06.10.2026); the chapters of the parts
 * are numbered 1, 2, … in reading order.
 */
export function sectionNumbers(
  sections: { id: string }[],
  parts: { sections: string[] }[] = [],
): (number | null)[] {
  // All the front matter (Maṅgalācaraṇa, the Introduction group) is unnumbered.
  const front = new Set(parts.length ? frontMatter(sections.map((s) => s.id), parts) : []);
  let n = 0;
  return sections.map((s) => (front.has(s.id) ? null : ++n));
}

/** "2.1"-style number of the i-th (0-based) subsection of chapter `num`;
 *  in an unnumbered chapter (front matter) simply "1", "2", …. */
export function subsectionNumber(num: number | string | null, i: number): string {
  return num == null ? String(i + 1) : `${num}.${i + 1}`;
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

/**
 * A short mantra (Satkirti 07.10.2026, Reader v7.8): one line, at most 6 words,
 * beginning with a bīja (oṁ, aiṁ, klīṁ, śrīṁ, hrīṁ, rāṁ — or the same in
 * Cyrillic) and ending in namaḥ / svāhā / phaṭ — «oṁ keśavāya namaḥ». Such a
 * mantra has no «пословно» button in the reader (its words are self-evident);
 * the data keep their word-by-word text.
 */
const BIJA = new Set(["oṁ", "aiṁ", "klīṁ", "śrīṁ", "hrīṁ", "rāṁ", "ом̇", "аим̇", "клӣм̇", "ш́рӣм̇", "хрӣм̇", "ра̄м̇"].map((b) => b.normalize("NFC")));
const MANTRA_END = new RegExp(`(${["namaḥ", "svāhā", "phaṭ", "намах̣", "сва̄ха̄", "пхат̣"].map((e) => e.normalize("NFC")).join("|")})[.!]?$`);
export function isShortMantra(text: string | undefined): boolean {
  const s = stripInline(text ?? "").trim().normalize("NFC");
  if (!s || s.includes("\n")) return false;
  const words = s.split(/\s+/);
  return words.length >= 2 && words.length <= 6 && BIJA.has(words[0].toLowerCase()) && MANTRA_END.test(s);
}

/** Where `nq` (a normalizeText()-ed query) occurs in `text`: [start, end) ranges of
 *  the ORIGINAL text, matched as normalizeText does (case and diacritics ignored). */
export function matchRanges(text: string, nq: string): [number, number][] {
  if (!nq) return [];
  let n = "";
  const map: number[] = [];
  for (let i = 0; i < text.length; i++) {
    const c = normalizeText(text[i]);
    for (let k = 0; k < c.length; k++) map.push(i);
    n += c;
  }
  const out: [number, number][] = [];
  for (let at = n.indexOf(nq); at >= 0; at = n.indexOf(nq, at + nq.length)) {
    out.push([map[at], map[at + nq.length - 1] + 1]);
  }
  return out;
}
