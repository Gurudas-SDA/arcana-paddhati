// Language configuration and helpers shared by server and client code.
// The language list lives in lib/languages.json (also read by scripts/*.mjs).
import { Fragment, createElement, type ReactNode } from "react";
import languages from "./languages.json";
import { BASE_PATH } from "./basePath";
import type { TocPart, TocSection } from "./book";

export interface Language {
  code: string;
  /** Native name shown in the language menu. */
  name: string;
  /** Value for <html lang> (e.g. "ru-iast" -> "ru"). */
  htmlLang: string;
  /**
   * Retired language: not offered in the language menu, not built (no pages,
   * no search index); its old URLs (redirect pages, scripts/retired-lang-redirects.mjs)
   * and a saved choice of it lead to this language instead. Its data files
   * (data/book.<code>.json, ui.<code>.json) stay in git, so it can come back by
   * removing this field (Satkirti 05.10.2026: one Russian only — "ru-iast";
   * S 23.10.2026 Padomnieks 934–941: «Оставляю два языка: английский и русский…
   * оставить версию с IAST» — the other nine -> English).
   */
  replacedBy?: string;
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

/** Every language the book has ever had (retired ones included: their codes are still recognised). */
export const LANGUAGES = languages as Language[];
export const DEFAULT_LANG = "en";
export const LANG_STORAGE_KEY = "arcanaLang";

/** The book's languages: offered in the language menu and built (retired ones left out). */
export const OFFERED_LANGUAGES = LANGUAGES.filter((l) => !l.replacedBy);
/** Built languages that live under /<code>/ (every offered one except the default). */
export const PREFIXED_LANGUAGES = OFFERED_LANGUAGES.filter((l) => l.code !== DEFAULT_LANG);

/** The language to show for `code` (a retired one -> its replacement). */
export function liveLang(code: string): string {
  return getLanguage(code)?.replacedBy ?? code;
}

/** Retired language code -> the language shown instead. */
export const RETIRED_LANGS: Record<string, string> = Object.fromEntries(
  LANGUAGES.filter((l) => l.replacedBy).map((l) => [l.code, l.replacedBy as string]),
);

/**
 * Inline <head> script (app/layout.tsx), before first paint: a saved retired
 * language becomes its replacement, and a page of a retired language (here only
 * the 404 page: retired languages are not built, their known URLs are redirect
 * pages of their own) is replaced by the same page in the replacement — the
 * default language has no /<code>/ prefix (/de/x/ -> /x/, /ru/x/ -> /ru-iast/x/).
 */
export const LANG_REDIRECT_SCRIPT = `(function(){try{var m=${JSON.stringify(
  Object.fromEntries(Object.entries(RETIRED_LANGS).map(([c, to]) => [c, to === DEFAULT_LANG ? "" : to + "/"])),
)},k=${JSON.stringify(LANG_STORAGE_KEY)},d=${JSON.stringify(DEFAULT_LANG)},h=function(x){return Object.prototype.hasOwnProperty.call(m,x)};try{var s=localStorage.getItem(k);if(s&&h(s))localStorage.setItem(k,m[s]?m[s].slice(0,-1):d)}catch(e){}var b=${JSON.stringify(BASE_PATH + "/")},p=location.pathname;if(p.indexOf(b)!==0)return;var r=p.slice(b.length),i=r.indexOf("/"),c=i<0?r:r.slice(0,i);if(h(c))location.replace(b+m[c]+(i<0?"":r.slice(i+1))+location.search+location.hash)}catch(e){}})();`;

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
