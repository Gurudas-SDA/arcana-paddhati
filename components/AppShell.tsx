"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import InstallBanner from "@/components/InstallBanner";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import type { SearchEntry } from "@/lib/book";
import {
  QUERY_STORE,
  isMenuEntry,
  main as mainEl,
  patchState,
  placeKey,
  pushOverlay,
  recordScroll,
  savedScroll,
} from "@/lib/navHistory";
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
  const searchQueryRef = useRef("");
  useEffect(() => {
    searchQueryRef.current = searchQuery;
  }, [searchQuery]);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchIndexes, setSearchIndexes] = useState<Record<string, IndexState>>({});
  const indexRequested = useRef<Set<string>>(new Set());

  // The mobile menu is a history entry (UI rule 6): opening it pushes an
  // entry on top of the current place, so the phone's "back" closes it; a
  // search result keeps that entry, so "back" from the result reopens the menu
  // with the same query. Back/forward set the menu from the entry's state.
  const afterPop = useRef<(() => void) | null>(null);

  const openMenu = () => {
    try {
      if (!isMenuEntry()) pushOverlay({ apMenu: true });
    } catch {
      // history unavailable: the menu still opens
    }
    setMobileMenuOpen(true);
  };

  /** Close from the UI (the close button, backdrop, Esc): pop our entry. */
  const closeMenu = useCallback(() => {
    setMobileMenuOpen(false);
    if (isMenuEntry()) window.history.back();
  }, []);

  /**
   * Leave the menu for a place that should REPLACE it in history (a contents
   * link): pop the menu entry first, then go. Otherwise the menu entry would
   * sit between the two places and "back" would reopen the menu.
   */
  const closeMenuThen = useCallback((go: () => void) => {
    setMobileMenuOpen(false);
    if (!isMenuEntry()) {
      go();
      return;
    }
    let done = false;
    const run = () => {
      if (done) return;
      done = true;
      window.clearTimeout(timer);
      afterPop.current = null;
      go();
    };
    afterPop.current = run;
    const timer = window.setTimeout(run, 400);
    window.history.back();
  }, []);

  /** Leave the menu from a search result: keep its entry (with the query). */
  const leaveMenuForResult = useCallback(() => {
    try {
      if (isMenuEntry()) patchState({ apQuery: searchQueryRef.current });
      sessionStorage.setItem(QUERY_STORE, searchQueryRef.current);
    } catch {
      // storage unavailable
    }
    setMobileMenuOpen(false);
  }, []);

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
      if (e.key === "Escape" && document.querySelector(".mobile-menu")) {
        closeMenu();
      }
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [closeMenu]);

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

  // Reading position: the content scrolls inside .app-main, which the browser
  // does not restore on back/forward. It is recorded per history entry and put
  // back on popstate (with the menu and the query of a menu entry).
  const loadIndexRef = useRef(loadSearchIndex);
  useEffect(() => {
    loadIndexRef.current = loadSearchIndex;
  }, [loadSearchIndex]);
  useEffect(() => {
    const m = mainEl();
    if (!m) return;
    const onScroll = () => recordScroll();
    m.addEventListener("scroll", onScroll, { passive: true });

    const reopenMenu = (st: Record<string, unknown> | null) => {
      let q = typeof st?.apQuery === "string" ? st.apQuery : null;
      if (q === null) {
        try {
          q = sessionStorage.getItem(QUERY_STORE);
        } catch {
          q = null;
        }
      }
      if (q) {
        setSearchQuery(q);
        loadIndexRef.current();
      }
      setMobileMenuOpen(true);
    };

    const onPop = (e: PopStateEvent) => {
      const st = (e.state as Record<string, unknown> | null) ?? null;
      if (isMenuEntry(st)) reopenMenu(st);
      else setMobileMenuOpen(false);
      const pending = afterPop.current;
      if (pending) {
        // After Next.js' own popstate handler (registered later, runs after
        // this one): its traverse would otherwise override the navigation.
        window.setTimeout(pending, 0);
        return;
      }
      // Put the place back after Next.js has rendered the entry's page.
      const target = savedScroll(st);
      const hash = window.location.hash.slice(1);
      const apply = () => {
        const el = mainEl();
        if (!el) return;
        if (target !== undefined) {
          el.scrollTop = target;
        } else if (hash) {
          let id = hash;
          try {
            id = decodeURIComponent(hash);
          } catch {
            // keep raw
          }
          document.getElementById(id)?.scrollIntoView({ block: "start" });
        } else {
          el.scrollTop = 0;
        }
      };
      requestAnimationFrame(apply);
      for (const ms of [60, 160, 320, 600]) window.setTimeout(apply, ms);
    };
    window.addEventListener("popstate", onPop);

    // Reloaded (or restored from the page cache) on a menu entry.
    if (isMenuEntry()) reopenMenu(window.history.state);
    return () => {
      m.removeEventListener("scroll", onScroll);
      window.removeEventListener("popstate", onPop);
    };
  }, []);

  // Each new entry gets its place key once its page is shown.
  useEffect(() => {
    try {
      placeKey();
    } catch {
      // history unavailable
    }
  }, [pathname]);

  const searchIndex = searchIndexes[contentLang];
  const entries = Array.isArray(searchIndex) ? searchIndex : null;

  const switcherProps = { lang, sectionId, available, ui };

  const sidebarProps = {
    sections,
    parts,
    lang,
    ui,
    hasWbw,
    languageSwitcher: <LanguageSwitcher {...switcherProps} block />,
    searchQuery,
    onSearchChange: (q: string) => {
      setSearchQuery(q);
      try {
        sessionStorage.setItem(QUERY_STORE, q);
      } catch {
        // storage unavailable
      }
    },
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
        <div className="mobile-menu no-print fixed inset-0 z-40 lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/30 sidebar-backdrop"
            onClick={closeMenu}
            aria-hidden="true"
          />
          {/* Sidebar panel */}
          <div className="fixed inset-y-0 left-0 z-50 w-80 max-w-[85vw] sidebar-transition">
            <Sidebar
              {...sidebarProps}
              onClose={closeMenu}
              onLeave={(kind, e, go) => {
                if (kind === "result") {
                  leaveMenuForResult();
                  return;
                }
                // Contents link: the new place replaces the menu entry.
                e.preventDefault();
                closeMenuThen(go);
              }}
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
            onClick={openMenu}
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
