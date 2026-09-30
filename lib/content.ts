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
import type { Book, Section, TocSection } from "./book";
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

export function getSection(lang: string, id: string): Section | undefined {
  return (
    getBook(lang).sections.find((s) => s.id === id) ??
    englishBook().sections.find((s) => s.id === id)
  );
}

/** Table of contents in English order, titles from the translation where present. */
export function getToc(lang: string): TocSection[] {
  return getSectionIds().map((id) => {
    const s = getSection(lang, id)!;
    return {
      id: s.id,
      title: s.title,
      page: s.page,
      subsections: (s.subsections ?? []).map((sub) => ({
        id: sub.id,
        title: sub.title,
      })),
    };
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
    out[code] = { toc: getToc(code), ui: getUi(code) };
  }
  return out;
}
