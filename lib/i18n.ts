// Language configuration and helpers shared by server and client code.
// The language list lives in lib/languages.json (also read by scripts/*.mjs).
import { Fragment, createElement, type ReactNode } from "react";
import languages from "./languages.json";
import type { TocPart, TocSection } from "./book";

export interface Language {
  code: string;
  /** Native name shown in the language menu. */
  name: string;
  /** Value for <html lang> (e.g. "ru-iast" -> "ru"). */
  htmlLang: string;
}

/** Flat key -> string map (data/ui.<lang>.json, falling back to data/ui.en.json). */
export type UiDict = Record<string, string>;

/** Per-language data handed from the server to the client shell. */
export interface LocaleData {
  toc: TocSection[];
  /** Parts (I, II, III …) grouping the chapters; see lib/book.ts tocLayout(). */
  parts: TocPart[];
  ui: UiDict;
  /** True if any verse shown in this language has word-by-word meanings. */
  hasWbw: boolean;
}

export const LANGUAGES = languages as Language[];
export const DEFAULT_LANG = "en";
/** Languages that live under /<code>/ (everything except the default). */
export const PREFIXED_LANGUAGES = LANGUAGES.filter((l) => l.code !== DEFAULT_LANG);
export const LANG_STORAGE_KEY = "arcanaLang";

export function getLanguage(code: string): Language | undefined {
  return LANGUAGES.find((l) => l.code === code);
}

export function isLangCode(code: string | null | undefined): code is string {
  return !!code && LANGUAGES.some((l) => l.code === code);
}

export function isPrefixedLang(code: string | null | undefined): code is string {
  return isLangCode(code) && code !== DEFAULT_LANG;
}

/** Split a basePath-less pathname ("/ru/intro/", "/intro/", "/") into language + section. */
export function parsePath(pathname: string): { lang: string; sectionId: string | null } {
  const segs = pathname.split("/").filter(Boolean);
  if (isPrefixedLang(segs[0])) return { lang: segs[0], sectionId: segs[1] ?? null };
  return { lang: DEFAULT_LANG, sectionId: segs[0] ?? null };
}

/** Href (without basePath) of a section — or of the language's home page — in `lang`. */
export function localeHref(lang: string, sectionId?: string | null, anchor?: string) {
  const prefix = lang === DEFAULT_LANG ? "" : `/${lang}`;
  if (!sectionId) return `${prefix}/`;
  return `${prefix}/${sectionId}/${anchor ? `#${anchor}` : ""}`;
}

/** Look up a UI string; `{name}` placeholders are replaced from `vars`. */
export function t(ui: UiDict, key: string, vars?: Record<string, string>): string {
  const s = ui[key] ?? key;
  if (!vars) return s;
  return s.replace(/\{(\w+)\}/g, (m, name: string) => vars[name] ?? m);
}

/** Like t(), but placeholders are replaced by React nodes (e.g. <strong>). */
export function tNodes(
  ui: UiDict,
  key: string,
  nodes: Record<string, ReactNode>
): ReactNode[] {
  const parts = (ui[key] ?? key).split(/\{(\w+)\}/);
  return parts.map((part, i) =>
    createElement(Fragment, { key: i }, i % 2 === 1 ? (nodes[part] ?? `{${part}}`) : part)
  );
}
