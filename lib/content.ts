// Server-only (build-time) loading of the book and UI strings per language.
// Do not import from client components: it reads data/ with node:fs.
//
// Fallbacks, so the site builds before every translation exists:
//   data/book.<lang>.json missing -> English book (data/book.json)
//   section missing in a translation -> English section with the same id
//   data/ui.<lang>.json missing / key missing -> data/ui.en.json
// Adding a translation file therefore only needs a rebuild.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import {
  sectionNumbers,
  subsectionNumber,
  toRoman,
  tocLayout,
  type Book,
  type Section,
  type TocPart,
  type TocSection,
} from "./book";
import {
  DEFAULT_LANG,
  LANGUAGES,
  getLanguage,
  type LocaleData,
  type UiDict,
} from "./i18n";

const DATA_DIR = join(process.cwd(), "data");

const jsonCache = new Map<string, unknown>();

function readJson<T>(file: string): T | null {
  if (jsonCache.has(file)) return jsonCache.get(file) as T | null;
  const path = join(DATA_DIR, file);
  const value = existsSync(path)
    ? (JSON.parse(readFileSync(path, "utf8")) as T)
    : null;
  jsonCache.set(file, value);
  return value;
}

function bookFile(lang: string) {
  return lang === DEFAULT_LANG ? "book.json" : `book.${lang}.json`;
}

const englishBook = () => readJson<Book>(bookFile(DEFAULT_LANG))!;

/** True if data/book.<lang>.json exists (always true for English). */
export function hasBook(lang: string): boolean {
  return readJson<Book>(bookFile(lang)) !== null;
}

/** Codes of all languages whose book data exists. */
export function availableLanguages(): string[] {
  return LANGUAGES.filter((l) => hasBook(l.code)).map((l) => l.code);
}

/** The book in `lang`, or the English book if that translation is missing. */
export function getBook(lang: string): Book {
  return readJson<Book>(bookFile(lang)) ?? englishBook();
}

/** English section ids — the same ids are used in every language. */
export function getSectionIds(): string[] {
  return englishBook().sections.map((s) => s.id);
}

/** True if section `id` is shown in English on a `lang` page because that
 *  translation does not have it yet (the page then says so in `lang`). */
export function isFallbackSection(lang: string, id: string): boolean {
  if (lang === DEFAULT_LANG) return false;
  const own = readJson<Book>(bookFile(lang));
  return !own || !own.sections.some((s) => s.id === id);
}

export function getSection(lang: string, id: string): Section | undefined {
  return (
    getBook(lang).sections.find((s) => s.id === id) ??
    englishBook().sections.find((s) => s.id === id)
  );
}

/**
 * Parts of the book: structure (ids, chapter lists) from the English book,
 * titles from the translation where present.
 */
export function getParts(lang: string): TocPart[] {
  const local = getBook(lang).parts ?? [];
  return (englishBook().parts ?? []).map((p, i) => ({
    id: p.id,
    title: local.find((l) => l.id === p.id)?.title ?? p.title,
    numeral: toRoman(i + 1),
    sections: p.sections,
  }));
}

export function getPart(lang: string, id: string): TocPart | undefined {
  return getParts(lang).find((p) => p.id === id);
}

/** Part ids — each part has its own page (/<part>/, /<lang>/<part>/). */
export function getPartIds(): string[] {
  return (englishBook().parts ?? []).map((p) => p.id);
}

/** Chapter number of section `id` ("1", "2", …), null if unknown.
 *  Computed from the English section order, so it is the same in every language. */
export function getSectionNumber(id: string): string | null {
  const sections = englishBook().sections;
  const i = sections.findIndex((s) => s.id === id);
  if (i < 0) return null;
  const n = sectionNumbers(sections)[i];
  return n == null ? null : String(n);
}

/**
 * The page after `id` in reading order (the order of the contents): chapters,
 * plus the parts that have no chapters yet (their page is the place in the
 * order). Same logic as the former «След. глава ›» of the reader's bottom
 * bar (before Reader UI v5). Undefined after the last chapter and for pages
 * outside the order (the cover, parts with chapters).
 */
export function getNextChapter(
  lang: string,
  id: string,
): { id: string; title: string; num: string | null; part: string | null } | undefined {
  const parts = getParts(lang);
  const partById = new Map(parts.map((p) => [p.id, p]));
  const order: string[] = [];
  for (const item of tocLayout(getSectionIds(), parts)) {
    if (item.kind === "section") order.push(item.id);
    else if (partById.get(item.id)?.sections.length === 0) order.push(item.id);
  }
  const i = order.indexOf(id);
  const next = i >= 0 ? order[i + 1] : undefined;
  if (!next) return undefined;
  const part = partById.get(next);
  if (part) return { id: next, title: part.title, num: null, part: part.numeral };
  const s = getSection(lang, next);
  return s ? { id: next, title: s.title, num: getSectionNumber(next), part: null } : undefined;
}

/** Table of contents in English order, titles from the translation where present. */
export function getToc(lang: string): TocSection[] {
  return getSectionIds().map((id) => {
    const s = getSection(lang, id)!;
    const num = getSectionNumber(id);
    return {
      id: s.id,
      title: s.title,
      page: s.page,
      num,
      subsections: (s.subsections ?? []).map((sub, i) => ({
        id: sub.id,
        title: sub.title,
        num: subsectionNumber(num, i),
      })),
    };
  });
}

/**
 * True if any verse of the book as shown in `lang` (incl. English fallback
 * sections) has word-by-word meanings. Decides whether the sidebar offers
 * the "Show all word-by-word" switch.
 */
export function hasWordByWord(lang: string): boolean {
  return getSectionIds().some((id) => {
    const s = getSection(lang, id)!;
    return [s.content, ...(s.subsections ?? []).map((sub) => sub.content)].some(
      (blocks) => blocks.some((b) => b.type === "verse" && !!b.wbw)
    );
  });
}

/** UI strings for `lang`, each missing key falling back to English. */
export function getUi(lang: string): UiDict {
  const en = readJson<UiDict>(`ui.${DEFAULT_LANG}.json`) ?? {};
  if (lang === DEFAULT_LANG) return en;
  return { ...en, ...(readJson<UiDict>(`ui.${lang}.json`) ?? {}) };
}

/** <html lang> for pages of `lang`: English when the text falls back to English. */
export function htmlLangFor(lang: string): string {
  return hasBook(lang) ? (getLanguage(lang)?.htmlLang ?? lang) : DEFAULT_LANG;
}

/**
 * TOC + UI strings for every language that has any data of its own.
 * Languages without data are left out; the client falls back to English.
 */
export function getLocales(): Record<string, LocaleData> {
  const out: Record<string, LocaleData> = {};
  for (const { code } of LANGUAGES) {
    if (code !== DEFAULT_LANG && !hasBook(code) && !readJson(`ui.${code}.json`)) {
      continue;
    }
    out[code] = {
      toc: getToc(code),
      parts: getParts(code),
      ui: getUi(code),
      hasWbw: hasWordByWord(code),
    };
  }
  return out;
}
