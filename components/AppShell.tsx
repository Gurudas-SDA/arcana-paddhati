"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import InstallBanner from "@/components/InstallBanner";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import type { SearchEntry } from "@/lib/book";
import {
  DEFAULT_LANG,
  LANG_STORAGE_KEY,
  getLanguage,
  isLangCode,
  localeHref,
  parsePath,
  t,
  type LocaleData,
} from "@/lib/i18n";

const searchIndexUrl = (lang: string) =>
  `/arcana-paddhati/search-index.${lang}.json`;

type IndexState = SearchEntry[] | "loading" | "error";

export default function AppShell({
  locales,
  available,
  children,
}: {
  /** TOC + UI strings per language that has data (English always present). */
  locales: Record<string, LocaleData>;
  /** Languages whose book text exists. */
  available: string[];
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { lang, sectionId } = parsePath(pathname);
  const { toc: sections, parts, ui, hasWbw } = locales[lang] ?? locales[DEFAULT_LANG];
  // Language of the text actually shown (English when a translation is missing).
  const contentLang = available.includes(lang) ? lang : DEFAULT_LANG;
  const htmlLang = getLanguage(contentLang)?.htmlLang ?? DEFAULT_LANG;

  const [searchQuery, setSearchQuery] = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchIndexes, setSearchIndexes] = useState<Record<string, IndexState>>({});
  const indexRequested = useRef<Set<string>>(new Set());

  // Close the mobile menu whenever the route changes (incl. back/forward).
  const [lastPathname, setLastPathname] = useState(pathname);
  if (pathname !== lastPathname) {
    setLastPathname(pathname);
    setMobileMenuOpen(false);
  }

  // <html lang> follows the language on client-side navigation (the static
  // HTML already has it, see scripts/patch-html-lang.mjs).
  useEffect(() => {
    document.documentElement.lang = htmlLang;
  }, [htmlLang]);

  // Start page only (also the PWA start_url): open the remembered language.
  // Any other URL is shown in the language it names.
  const langChecked = useRef(false);
  useEffect(() => {
    if (langChecked.current) return;
    langChecked.current = true;
    if (pathname !== "/") return;
    let stored: string | null = null;
    try {
      stored = localStorage.getItem(LANG_STORAGE_KEY);
    } catch {
      // storage unavailable
    }
    if (isLangCode(stored) && stored !== DEFAULT_LANG) {
      router.replace(localeHref(stored));
    }
  }, [pathname, router]);

  // Close mobile menu on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMobileMenuOpen(false);
      }
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, []);

  // Prevent body scroll when mobile menu is open
  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileMenuOpen]);

  // Full-text search index of the shown language: fetched lazily on first
  // focus of the search box (again after switching language).
  const loadSearchIndex = useCallback(() => {
    const l = contentLang;
    if (indexRequested.current.has(l)) return;
    indexRequested.current.add(l);
    setSearchIndexes((prev) => ({ ...prev, [l]: "loading" }));
    fetch(searchIndexUrl(l))
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<SearchEntry[]>;
      })
      .then((entries) => setSearchIndexes((prev) => ({ ...prev, [l]: entries })))
      .catch(() => {
        // Fall back to title-only search; allow a retry on next focus.
        indexRequested.current.delete(l);
        setSearchIndexes((prev) => ({ ...prev, [l]: "error" }));
      });
  }, [contentLang]);

  const searchIndex = searchIndexes[contentLang];
  const entries = Array.isArray(searchIndex) ? searchIndex : null;

  const switcherProps = { lang, sectionId, available, ui };

  const sidebarProps = {
    sections,
    parts,
    lang,
    ui,
    hasWbw,
    languageSwitcher: <LanguageSwitcher {...switcherProps} />,
    searchQuery,
    onSearchChange: setSearchQuery,
    onSearchFocus: loadSearchIndex,
    searchEntries: entries,
  };

  return (
    <div className="app-shell flex h-full">
      {/* Desktop sidebar */}
      <div className="no-print hidden lg:flex lg:w-80 lg:shrink-0 lg:flex-col h-full">
        <Sidebar {...sidebarProps} onClose={() => {}} />
      </div>

      {/* Mobile sidebar overlay */}
      {mobileMenuOpen && (
        <div className="no-print fixed inset-0 z-40 lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/30 sidebar-backdrop"
            onClick={() => setMobileMenuOpen(false)}
            aria-hidden="true"
          />
          {/* Sidebar panel */}
          <div className="fixed inset-y-0 left-0 z-50 w-80 max-w-[85vw] sidebar-transition">
            <Sidebar
              {...sidebarProps}
              onClose={() => setMobileMenuOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Main content area */}
      <main className="app-main flex-1 overflow-y-auto">
        <InstallBanner ui={ui} />
        {/* Mobile header */}
        <div className="no-print sticky top-0 z-30 lg:hidden flex items-center gap-3 px-4 py-3 bg-white/95 backdrop-blur-sm border-b border-[#ddd]">
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="p-2 rounded-lg hover:bg-[#F5E6C8] transition-colors"
            aria-label={t(ui, "header.openMenu")}
          >
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#2C1810"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <h1
            className="text-sm font-semibold truncate text-[#1a1a1a]"
            style={{ fontFamily: "var(--font-noto-serif, Georgia, serif)" }}
          >
            <Link
              href={localeHref(lang)}
              title={t(ui, "sidebar.cover")}
              className="hover:text-[#B8860B] transition-colors"
            >
              {t(ui, "header.title")}
            </Link>
          </h1>
          <div className="ml-auto">
            <LanguageSwitcher {...switcherProps} />
          </div>
        </div>

        {/* Content */}
        {children}
      </main>
    </div>
  );
}
