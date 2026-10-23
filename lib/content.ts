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
  frontGroup,
  sectionNumbers,
  subsectionNumber,
  toRoman,
  type Book,
  type Section,
  type TocPart,
  type TocSection,
} from "./book";
import {
  DEFAULT_LANG,
  LANGUAGES,
  t,
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
function hasBook(lang: string): boolean {
  return readJson<Book>(bookFile(lang)) !== null;
}

/** Codes of all languages whose book data exists. */
export function availableLanguages(): string[] {
  return LANGUAGES.filter((l) => hasBook(l.code)).map((l) => l.code);
}

/** The book in `lang`, or the English book if that translation is missing. */
function getBook(lang: string): Book {
  return readJson<Book>(bookFile(lang)) ?? englishBook();
}

/** English section ids — the same ids are used in every language. */
export function getSectionIds(): string[] {
  return englishBook().sections.map((s) => s.id);
}

/** True if section `id` is shown in English on a `lang` page because that
 *  translation does not have it yet (the page then says so in `lang`). */
function isFallbackSection(lang: string, id: string): boolean {
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
  const n = sectionNumbers(sections, englishBook().parts ?? [])[i];
  return n == null ? null : String(n);
}

/** Table of contents in English order, titles from the translation where present. */
export function getToc(lang: string): TocSection[] {
  const group = getFrontGroup();
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
      ...(group && id === group.head ? { members: group.members } : {}),
      ...(group && group.members.includes(id) ? { group: group.head } : {}),
      // V45: a section without text of its own is not a page of «Назад» / «Вперёд».
      ...((s.content ?? []).length === 0 && (s.subsections ?? []).length === 0 ? { noText: true } : {}),
    };
  });
}

/** The Introduction group of the contents (lib/book.ts frontGroup()). */
function getFrontGroup(): { head: string; members: string[] } | null {
  return frontGroup(getSectionIds(), englishBook().parts ?? []);
}

/**
 * True if any verse of the book as shown in `lang` (incl. English fallback
 * sections) has word-by-word meanings. Decides whether the sidebar offers
 * the "Show all word-by-word" switch.
 */
function hasWordByWord(lang: string): boolean {
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

/** UI strings for `keys` in `lang`. A key this language has not got yet shows
 *  the English text; per the book's fallback convention the first such string
 *  of a group gets the «(EN)» suffix (language.fallbackSuffix) — Vraja Lila
 *  msg 5316/5318: new interface labels RU + EN by hand, no machine translation. */
export function uiWithFallback(lang: string, keys: string[]): { strings: Record<string, string>; fallback: boolean } {
  const ui = getUi(lang);
  const own = lang === DEFAULT_LANG ? ui : (readJson<UiDict>(`ui.${lang}.json`) ?? {});
  const strings: Record<string, string> = {};
  let fallback = false;
  for (const k of keys) {
    strings[k] = ui[k] ?? k;
    if (!(k in own)) fallback = true;
  }
  return { strings, fallback };
}

/** First section of the book after the cover and the front pages: the Introduction. */
const MACHINE_NOTE_SECTION = "introduction";

/**
 * The line under a section's heading (or undefined):
 *  - an English section shown in another language's book → «section.fallback»;
 *  - «Стандарты» 76 (Satkirti 18.10.2026 msg 4507/4509): a machine-translated language has, at the start
 *    of the book in its own language, the line «Перевод выполнен машинно и ещё не проверен носителем
 *    языка» (ui.<lang>.json «book.machineNote»; only the 9 machine-translated languages have the key —
 *    remove it when a native speaker has checked the language). The cover stays only the cover
 *    («Стандарты» 25), so the line is at the top of the Introduction.
 */
export function sectionNote(lang: string, id: string): string | undefined {
  const ui = getUi(lang);
  if (isFallbackSection(lang, id)) return t(ui, "section.fallback");
  if (id === MACHINE_NOTE_SECTION && lang !== DEFAULT_LANG) {
    const own = readJson<UiDict>(`ui.${lang}.json`);
    if (own?.["book.machineNote"]) return own["book.machineNote"];
  }
  return undefined;
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
