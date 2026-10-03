"use client";

import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  normalizeText,
  tocLayout,
  type SearchEntry,
  type TocItem,
  type TocPart,
  type TocSection,
} from "@/lib/book";
import { localeHref, parsePath, t, type UiDict } from "@/lib/i18n";
import {
  setShowAllTranslations,
  setShowAllWbw,
  useShowAllTranslations,
  useShowAllWbw,
} from "@/lib/translationsPref";

interface SidebarProps {
  sections: TocSection[];
  /** Parts (I, II, …) grouping the chapters; headings in the contents list. */
  parts: TocPart[];
  /** Language of the current URL (links stay in it). */
  lang: string;
  ui: UiDict;
  /** The language's book has word-by-word data (else its switch is hidden). */
  hasWbw: boolean;
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

/** Scroll-spy line: the subsection block crossing this band (about 20% from
 *  the top of the viewport) is the one "in view". */
const SPY_ROOT_MARGIN = "-20% 0px -79% 0px";
/** After a click on a subsection link (or a hash change) the spy is paused
 *  this long, so the chosen item stays active while the page scrolls to it. */
const CLICK_LOCK_MS = 1000;

function hashId(): string | null {
  const h = window.location.hash.slice(1);
  if (!h) return null;
  try {
    return decodeURIComponent(h);
  } catch {
    return h;
  }
}

/**
 * Id of the current subsection of the shown section: from the URL hash, and
 * while scrolling from the subsection block crossing the spy line
 * (IntersectionObserver). null while in the section's introductory text.
 */
function useActiveSubsection(
  pathname: string,
  subIds: string[]
): [string | null, (id: string) => void] {
  const [active, setActive] = useState<string | null>(null);
  const lockUntil = useRef(0);
  const idsKey = subIds.join("|");

  // Reset when the page changes (render-time adjustment, no effect needed).
  const [lastPath, setLastPath] = useState(pathname);
  if (pathname !== lastPath) {
    setLastPath(pathname);
    setActive(null);
  }

  useEffect(() => {
    const ids = idsKey ? idsKey.split("|") : [];
    if (ids.length === 0) return;
    const known = new Set(ids);
    const visible = new Set<string>();
    let observer: IntersectionObserver | null = null;
    let retry: number | undefined;

    const fromHash = () => {
      const id = hashId();
      if (id && known.has(id)) {
        lockUntil.current = Date.now() + CLICK_LOCK_MS;
        setActive(id);
      }
    };

    const attach = (attempt: number) => {
      const els = ids
        .map((id) => document.getElementById(id))
        .filter((el): el is HTMLElement => el !== null);
      if (els.length === 0) {
        // Content of a freshly navigated page may not be mounted yet.
        if (attempt < 20) {
          retry = window.setTimeout(() => attach(attempt + 1), 100);
        }
        return;
      }
      fromHash();
      const obs = new IntersectionObserver(
        (entries) => {
          for (const e of entries) {
            if (e.isIntersecting) visible.add(e.target.id);
            else visible.delete(e.target.id);
          }
          if (Date.now() < lockUntil.current) return;
          const current = ids.find((id) => visible.has(id));
          // Nothing on the line: keep the last one unless we are back above
          // the first subsection (the section's introductory text).
          if (current) setActive(current);
          else {
            const first = els[0].getBoundingClientRect().top;
            if (first > window.innerHeight * 0.2) setActive(null);
          }
        },
        { rootMargin: SPY_ROOT_MARGIN, threshold: 0 }
      );
      els.forEach((el) => obs.observe(el));
      observer = obs;
    };

    attach(0);
    window.addEventListener("hashchange", fromHash);
    window.addEventListener("popstate", fromHash);
    return () => {
      window.clearTimeout(retry);
      observer?.disconnect();
      window.removeEventListener("hashchange", fromHash);
      window.removeEventListener("popstate", fromHash);
    };
  }, [pathname, idsKey]);

  const select = (id: string) => {
    lockUntil.current = Date.now() + CLICK_LOCK_MS;
    setActive(id);
  };
  return [active, select];
}

/** A small on/off switch row of the sidebar. */
function PrefSwitch({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  const labelId = useId();
  // Only the label text and the switch itself act; the empty gap between
  // them is page space (UI rule 1).
  return (
    <div className="flex w-full items-center justify-between gap-3 py-1 text-xs text-[#5C3D2E]">
      <span
        id={labelId}
        onClick={() => onChange(!checked)}
        className="cursor-pointer select-none hover:text-[#2C1810] transition-colors"
      >
        {label}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-labelledby={labelId}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-4 w-7 shrink-0 items-center rounded-full transition-colors ${
          checked ? "bg-[#B8860B]" : "bg-[#E8DCC8]"
        }`}
      >
        <span
          className={`inline-block h-3 w-3 rounded-full bg-white shadow-sm transition-transform ${
            checked ? "translate-x-3.5" : "translate-x-0.5"
          }`}
        />
      </button>
    </div>
  );
}

export default function Sidebar({
  sections,
  parts,
  lang,
  ui,
  hasWbw,
  languageSwitcher,
  searchQuery,
  onSearchChange,
  onSearchFocus,
  searchEntries,
  onClose,
}: SidebarProps) {
  const pathname = usePathname();
  const selectedId = parsePath(pathname).sectionId;
  const selectedSection = sections.find((s) => s.id === selectedId);
  const subIds = useMemo(
    () => (selectedSection?.subsections ?? []).map((sub) => sub.id),
    [selectedSection]
  );
  const [activeSubId, selectSub] = useActiveSubsection(pathname, subIds);
  const showAllTranslations = useShowAllTranslations();
  const showAllWbw = useShowAllWbw();

  // Clicking the open (current) section collapses / re-expands its
  // subsection list; navigating to another section opens that one.
  const [collapsedId, setCollapsedId] = useState<string | null>(null);
  const [lastSelected, setLastSelected] = useState(selectedId);
  if (selectedId !== lastSelected) {
    setLastSelected(selectedId);
    setCollapsedId(null);
  }
  const sectionHref = (sectionId: string, anchor?: string) =>
    localeHref(lang, sectionId, anchor);

  /**
   * Click on a link to a place in the book (search result, subsection).
   * Another page: the Link navigates (Next.js scrolls to the anchor). The page
   * already shown: Next.js does nothing when the URL (with its #hash) is the
   * current one — a second tap on the same result did not move — so scroll to
   * the anchor here (and record the hash) every time.
   */
  const followLink = (e: React.MouseEvent, sectionId: string, anchor?: string) => {
    const strip = (p: string) => p.replace(/\/+$/, "");
    const samePage = strip(localeHref(lang, sectionId)) === strip(pathname);
    if (samePage) {
      e.preventDefault();
      if (anchor) {
        if (hashId() !== anchor) {
          window.history.pushState(window.history.state, "", `#${anchor}`);
        }
        // The scroll-spy re-reads the hash (also when it is unchanged).
        window.dispatchEvent(new HashChangeEvent("hashchange"));
        document.getElementById(anchor)?.scrollIntoView({ block: "start" });
      } else {
        document.querySelector(".app-main")?.scrollTo({ top: 0 });
      }
    }
    onClose();
  };

  const prepared = useMemo(
    () => (searchEntries ? searchEntries.map(prepare) : null),
    [searchEntries]
  );

  const normalizedQuery = normalizeText(searchQuery.trim());

  // Contents order: front matter, then each part heading with its chapters.
  const layout = useMemo(
    () => tocLayout(sections.map((s) => s.id), parts),
    [sections, parts]
  );
  const sectionById = useMemo(() => new Map(sections.map((s) => [s.id, s])), [sections]);
  const partById = useMemo(() => new Map(parts.map((p) => [p.id, p])), [parts]);

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
      <div className="px-5 py-4 border-b border-[#E8DCC8]">
      <div className="flex items-center justify-between gap-3">
        <Link
          href={localeHref(lang)}
          onClick={onClose}
          title={t(ui, "sidebar.cover")}
          className="flex items-center gap-2 min-w-0 rounded-sm hover:opacity-80 transition-opacity"
        >
          <svg
            aria-hidden="true"
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
            className="text-lg font-semibold leading-snug break-words"
            style={{ color: "#B8860B" }}
          >
            {t(ui, "sidebar.contents")}
          </h2>
        </Link>
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
        {/* Language menu on its own row so the title never truncates
            (mobile has it in the page header instead) */}
        <div className="hidden lg:block mt-3">{languageSwitcher}</div>
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

      {/* Verse panels: collapsed by default, these switches expand all */}
      <div className="px-5 py-2 border-b border-[#E8DCC8]">
        {hasWbw && (
          <PrefSwitch
            label={t(ui, "sidebar.showAllWbw")}
            checked={showAllWbw}
            onChange={setShowAllWbw}
          />
        )}
        <PrefSwitch
          label={t(ui, "sidebar.showAllTranslations")}
          checked={showAllTranslations}
          onChange={setShowAllTranslations}
        />
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
                    onClick={(e) => followLink(e, entry.section, entry.anchor)}
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
            {/* Book cover (the language's home page) */}
            {!normalizedQuery && (
              <li>
                <Link
                  href={localeHref(lang)}
                  onClick={onClose}
                  aria-current={selectedId === null ? "page" : undefined}
                  className={`sidebar-link w-full text-left px-5 py-3 flex items-center gap-2 transition-colors ${
                    selectedId === null
                      ? "bg-[#FAF3E8] border-l-3 border-[#B8860B]"
                      : "hover:bg-[#FDF8F0] border-l-3 border-transparent"
                  }`}
                >
                  <svg
                    aria-hidden="true"
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#B8860B"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="shrink-0"
                  >
                    <path d="M3 10.5 12 3l9 7.5" />
                    <path d="M5 9.5V21h14V9.5" />
                  </svg>
                  <span
                    className={`text-sm leading-snug ${
                      selectedId === null
                        ? "font-semibold text-[#B8860B]"
                        : "text-[#2C1810]"
                    }`}
                  >
                    {t(ui, "sidebar.cover")}
                  </span>
                </Link>
              </li>
            )}
            {(normalizedQuery
              ? filteredSections.map((s): TocItem => ({ kind: "section", id: s.id }))
              : layout
            ).map((item) => {
              if (item.kind === "part") {
                const part = partById.get(item.id);
                if (!part) return null;
                const isPartSelected = selectedId === part.id;
                return (
                  <li key={`part-${part.id}`} className="mt-2 border-t border-[#E8DCC8] pt-2">
                    <Link
                      href={sectionHref(part.id)}
                      onClick={onClose}
                      aria-current={isPartSelected ? "page" : undefined}
                      className={`sidebar-link w-full text-left px-5 py-2 block border-l-3 transition-colors ${
                        isPartSelected
                          ? "bg-[#FAF3E8] border-[#B8860B]"
                          : "hover:bg-[#FDF8F0] border-transparent"
                      }`}
                    >
                      <span className="text-[11px] uppercase tracking-[0.12em] font-semibold leading-snug text-[#9C7A4E]">
                        <span className="mr-1.5">{`${part.numeral}.`}</span>
                        {part.title}
                      </span>
                    </Link>
                  </li>
                );
              }
              const section = sectionById.get(item.id);
              if (!section) return null;
              const isSelected = selectedId === section.id;
              const hasSubs = (section.subsections?.length ?? 0) > 0;
              const isOpen =
                isSelected && hasSubs && collapsedId !== section.id;
              return (
                <li key={section.id}>
                  <Link
                    href={sectionHref(section.id)}
                    onClick={(e) => {
                      if (isSelected && hasSubs) {
                        // Toggle the list instead of reloading the page.
                        e.preventDefault();
                        setCollapsedId(isOpen ? section.id : null);
                        return;
                      }
                      onClose();
                    }}
                    aria-current={isSelected ? "page" : undefined}
                    aria-expanded={isSelected && hasSubs ? isOpen : undefined}
                    className={`sidebar-link w-full text-left px-5 py-3 flex items-start justify-between gap-2 transition-colors ${
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
                      {section.num && (
                        <span className="heading-num">{`${section.num}.`}</span>
                      )}
                      {section.title}
                    </span>
                    {isSelected && hasSubs && (
                      <svg
                        aria-hidden="true"
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="#B8860B"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className={`shrink-0 mt-0.5 transition-transform ${
                          isOpen ? "rotate-180" : ""
                        }`}
                      >
                        <polyline points="6 9 12 15 18 9" />
                      </svg>
                    )}
                  </Link>

                  {/* Subsections - shown while the current section is open */}
                  {isOpen && (
                    <ul className="ml-6 border-l border-[#E8DCC8]">
                      {section.subsections.map((sub) => {
                        const isActive = activeSubId === sub.id;
                        return (
                          <li key={sub.id}>
                            <Link
                              href={sectionHref(section.id, sub.id)}
                              onClick={(e) => {
                                selectSub(sub.id);
                                followLink(e, section.id, sub.id);
                              }}
                              aria-current={isActive ? "location" : undefined}
                              className={`sidebar-link -ml-px block w-full text-left px-4 py-2 text-xs border-l-2 transition-colors ${
                                isActive
                                  ? "bg-[#FDF8F0] border-[#B8860B]/70 text-[#B8860B] font-semibold"
                                  : "border-transparent text-[#5C3D2E] hover:text-[#B8860B] hover:bg-[#FDF8F0]"
                              }`}
                            >
                              {sub.num && (
                                <span className="heading-num">{`${sub.num}.`}</span>
                              )}
                              {sub.title}
                            </Link>
                          </li>
                        );
                      })}
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
