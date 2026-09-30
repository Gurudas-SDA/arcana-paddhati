"use client";

import React, { useMemo } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { normalizeText, type SearchEntry, type TocSection } from "@/lib/book";
import { localeHref, parsePath, t, type UiDict } from "@/lib/i18n";

interface SidebarProps {
  sections: TocSection[];
  /** Language of the current URL (links stay in it). */
  lang: string;
  ui: UiDict;
  languageSwitcher: React.ReactNode;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onSearchFocus: () => void;
  /** Full-text index; null while not (yet) loaded — then titles are searched. */
  searchEntries: SearchEntry[] | null;
  onClose: () => void;
}

interface PreparedEntry {
  entry: SearchEntry;
  nTitle: string;
  nText: string;
  /** nText[i] came from entry.text[map[i]] */
  map: number[];
}

interface Snippet {
  before: string;
  match: string;
  after: string;
}

interface SearchResult {
  entry: SearchEntry;
  snippet: Snippet;
}

const MAX_RESULTS = 50;
const SNIPPET_BEFORE = 50;
const SNIPPET_AFTER = 80;

function prepare(entry: SearchEntry): PreparedEntry {
  let nText = "";
  const map: number[] = [];
  for (let i = 0; i < entry.text.length; i++) {
    const n = normalizeText(entry.text[i]);
    for (let k = 0; k < n.length; k++) map.push(i);
    nText += n;
  }
  return { entry, nTitle: normalizeText(entry.title), nText, map };
}

function makeSnippet(p: PreparedEntry, pos: number, qLen: number): Snippet {
  const text = p.entry.text;
  if (pos < 0) {
    // Title-only match: show the beginning of the text.
    const limit = SNIPPET_BEFORE + SNIPPET_AFTER;
    if (text.length <= limit) return { before: "", match: "", after: text };
    return {
      before: "",
      match: "",
      after: text.slice(0, limit).replace(/\s+\S*$/, "") + "…",
    };
  }
  const mStart = p.map[pos];
  const mEnd = p.map[pos + qLen - 1] + 1;
  let start = Math.max(0, mStart - SNIPPET_BEFORE);
  let end = Math.min(text.length, mEnd + SNIPPET_AFTER);
  // Snap to word boundaries.
  if (start > 0) {
    const sp = text.indexOf(" ", start);
    if (sp !== -1 && sp < mStart) start = sp + 1;
  }
  if (end < text.length) {
    const sp = text.lastIndexOf(" ", end);
    if (sp > mEnd) end = sp;
  }
  return {
    before: (start > 0 ? "…" : "") + text.slice(start, mStart),
    match: text.slice(mStart, mEnd),
    after: text.slice(mEnd, end) + (end < text.length ? "…" : ""),
  };
}

export default function Sidebar({
  sections,
  lang,
  ui,
  languageSwitcher,
  searchQuery,
  onSearchChange,
  onSearchFocus,
  searchEntries,
  onClose,
}: SidebarProps) {
  const pathname = usePathname();
  const selectedId = parsePath(pathname).sectionId;
  const sectionHref = (sectionId: string, anchor?: string) =>
    localeHref(lang, sectionId, anchor);

  const prepared = useMemo(
    () => (searchEntries ? searchEntries.map(prepare) : null),
    [searchEntries]
  );

  const normalizedQuery = normalizeText(searchQuery.trim());

  // Full-text results (once the index is loaded).
  const results = useMemo<SearchResult[] | null>(() => {
    if (!normalizedQuery || !prepared) return null;
    const titleHits: SearchResult[] = [];
    const textHits: SearchResult[] = [];
    for (const p of prepared) {
      const inTitle = p.nTitle.includes(normalizedQuery);
      const pos = p.nText.indexOf(normalizedQuery);
      if (!inTitle && pos < 0) continue;
      const hit = {
        entry: p.entry,
        snippet: makeSnippet(p, pos, normalizedQuery.length),
      };
      (inTitle ? titleHits : textHits).push(hit);
    }
    return [...titleHits, ...textHits].slice(0, MAX_RESULTS);
  }, [prepared, normalizedQuery]);

  // Title-only filtering (before the index has loaded, or if it failed).
  const filteredSections = sections.filter((section) => {
    if (!normalizedQuery) return true;
    const matchesTitle = normalizeText(section.title).includes(normalizedQuery);
    const matchesSubsection = section.subsections?.some((sub) =>
      normalizeText(sub.title).includes(normalizedQuery)
    );
    return matchesTitle || matchesSubsection;
  });

  return (
    <aside className="flex flex-col h-full bg-white border-r border-[#E8DCC8]">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-[#E8DCC8]">
        <div className="flex items-center gap-2 min-w-0">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#B8860B"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          </svg>
          <h2
            className="text-lg font-semibold truncate"
            style={{ color: "#B8860B" }}
          >
            {t(ui, "sidebar.contents")}
          </h2>
        </div>
        {/* Language menu (mobile has it in the page header instead) */}
        <div className="hidden lg:block">{languageSwitcher}</div>
        {/* Mobile close button */}
        <button
          onClick={onClose}
          className="lg:hidden p-1 rounded hover:bg-[#F5E6C8] transition-colors"
          aria-label={t(ui, "sidebar.closeMenu")}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#2C1810"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      {/* Search */}
      <div className="px-4 py-3 border-b border-[#E8DCC8]">
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#B8860B"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            placeholder={t(ui, "search.placeholder")}
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            onFocus={onSearchFocus}
            className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-[#E8DCC8] bg-[#FDF8F0] text-[#2C1810] placeholder-[#B8860B]/50 focus:outline-none focus:border-[#B8860B] focus:ring-1 focus:ring-[#B8860B]/30 transition-colors"
          />
          {searchQuery && (
            <button
              onClick={() => onSearchChange("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#5C3D2E] hover:text-[#2C1810]"
              aria-label={t(ui, "search.clear")}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Sections list / search results */}
      <nav className="flex-1 overflow-y-auto sidebar-scroll py-2">
        {results ? (
          results.length === 0 ? (
            <p className="px-5 py-4 text-sm text-[#5C3D2E] italic">
              {t(ui, "search.noResults")}
            </p>
          ) : (
            <ul className="space-y-0.5">
              {results.map(({ entry, snippet }) => (
                <li key={`${entry.section}#${entry.anchor ?? ""}`}>
                  <Link
                    href={sectionHref(entry.section, entry.anchor)}
                    onClick={onClose}
                    className="block w-full text-left px-5 py-3 border-l-3 border-transparent hover:bg-[#FDF8F0] transition-colors"
                  >
                    <span className="block text-sm leading-snug text-[#2C1810]">
                      {entry.title}
                    </span>
                    {entry.anchor && (
                      <span className="block text-xs text-[#B8860B]/80 mt-0.5">
                        {entry.sectionTitle}
                      </span>
                    )}
                    {(snippet.before || snippet.match || snippet.after) && (
                      <span className="block text-xs leading-relaxed text-[#5C3D2E] mt-1">
                        {snippet.before}
                        {snippet.match && (
                          <mark className="bg-[#F5E6C8] text-[#2C1810] rounded-sm">
                            {snippet.match}
                          </mark>
                        )}
                        {snippet.after}
                      </span>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          )
        ) : filteredSections.length === 0 ? (
          <p className="px-5 py-4 text-sm text-[#5C3D2E] italic">
            {t(ui, "search.noSections")}
          </p>
        ) : (
          <ul className="space-y-0.5">
            {filteredSections.map((section) => {
              const isSelected = selectedId === section.id;
              return (
                <li key={section.id}>
                  <Link
                    href={sectionHref(section.id)}
                    onClick={onClose}
                    aria-current={isSelected ? "page" : undefined}
                    className={`w-full text-left px-5 py-3 flex items-start justify-between gap-2 transition-colors ${
                      isSelected
                        ? "bg-[#FAF3E8] border-l-3 border-[#B8860B]"
                        : "hover:bg-[#FDF8F0] border-l-3 border-transparent"
                    }`}
                  >
                    <span
                      className={`text-sm leading-snug ${
                        isSelected
                          ? "font-semibold text-[#B8860B]"
                          : "text-[#2C1810]"
                      }`}
                    >
                      {section.title}
                    </span>
                    {section.page && (
                      <span className="text-xs text-[#B8860B]/60 shrink-0 mt-0.5">
                        {section.page}
                      </span>
                    )}
                  </Link>

                  {/* Subsections - show when selected */}
                  {isSelected &&
                    section.subsections &&
                    section.subsections.length > 0 && (
                      <ul className="ml-6 border-l border-[#E8DCC8]">
                        {section.subsections.map((sub) => (
                          <li key={sub.id}>
                            <Link
                              href={sectionHref(section.id, sub.id)}
                              onClick={onClose}
                              className="block w-full text-left px-4 py-2 text-xs text-[#5C3D2E] hover:text-[#B8860B] hover:bg-[#FDF8F0] transition-colors"
                            >
                              {sub.title}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    )}
                </li>
              );
            })}
          </ul>
        )}
      </nav>
    </aside>
  );
}
