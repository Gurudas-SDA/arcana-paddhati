"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Sidebar, { restoreParts } from "@/components/Sidebar";
import InstallBanner from "@/components/InstallBanner";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import ReaderChrome from "@/components/ReaderChrome";
import type { SearchEntry } from "@/lib/book";
import {
  QUERY_STORE,
  isMenuEntry,
  main as mainEl,
  menuDepth,
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
  liveLang,
  localeHref,
  parsePath,
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
  /** Time of the last back / forward (its saved place wins over the anchor). */
  const poppedAt = useRef(-1e9);
  const [searchIndexes, setSearchIndexes] = useState<Record<string, IndexState>>({});
  const indexRequested = useRef<Set<string>>(new Set());

  // The mobile menu is a history entry (UI rule 6): opening it pushes an
  // entry on top of the current place, so the phone's "back" closes it; each
  // part expanded in it is one more entry (Sidebar.tsx). Leaving the menu for
  // a place (contents link, search result) keeps its entries, so "back" from
  // that place reopens the menu exactly as it was (same query, same parts).
  // Back/forward set the menu from the entry's state (lib/navHistory.ts).
  const openMenu = () => {
    try {
      const st = window.history.state as Record<string, unknown> | null;
      if (isMenuEntry()) {
        // already a menu entry
      } else if (st?.apAa === true) {
        // From the «Аа» panel: the menu takes the panel's place in history.
        patchState({ apMenu: true, apDepth: 1 }, ["apAa", "apParts", "apExp", "apQuery", "apNav"]);
      } else {
        pushOverlay({ apMenu: true, apDepth: 1 });
      }
    } catch {
      // history unavailable: the menu still opens
    }
    setMobileMenuOpen(true);
  };

  /** Close from the UI (the close button, backdrop, Esc): pop all menu entries. */
  const closeMenu = useCallback(() => {
    setMobileMenuOpen(false);
    const d = menuDepth();
    if (d > 0) window.history.go(-d);
  }, []);

  /**
   * Leave the menu for a place (link or result): keep its entries (with the query).
   * `navigating` — another page is opening: the menu stays on screen until that
   * page is rendered (Reader v7.1: on a slow device the old page — often the
   * cover — flashed for 2–3 s between the menu and the chapter).
   */
  const [leaving, setLeaving] = useState(false);
  const leaveTimer = useRef<number | undefined>(undefined);
  const leaveMenu = useCallback((navigating?: boolean) => {
    try {
      if (isMenuEntry()) patchState({ apQuery: searchQueryRef.current });
      sessionStorage.setItem(QUERY_STORE, searchQueryRef.current);
    } catch {
      // storage unavailable
    }
    window.clearTimeout(leaveTimer.current);
    if (navigating) {
      setLeaving(true);
      // Safety net: never keep the menu if the page does not come.
      leaveTimer.current = window.setTimeout(() => {
        setLeaving(false);
        setMobileMenuOpen(false);
      }, 8000);
      return;
    }
    setLeaving(false);
    setMobileMenuOpen(false);
  }, []);
  // The new page is rendered: now the menu goes.
  const [leftFrom, setLeftFrom] = useState(pathname);
  if (leftFrom !== pathname) {
    setLeftFrom(pathname);
    if (leaving) {
      setLeaving(false);
      setMobileMenuOpen(false);
    }
  }
  useEffect(() => {
    if (!leaving) window.clearTimeout(leaveTimer.current);
  }, [leaving]);

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
    if (isLangCode(stored) && liveLang(stored) !== DEFAULT_LANG) {
      router.replace(localeHref(liveLang(stored)));
    }
  }, [pathname, router]);

  // A retired language (only reachable by an old link inside the app):
  // the same place in its replacement. Full page loads are redirected
  // earlier by LANG_REDIRECT_SCRIPT (app/layout.tsx).
  useEffect(() => {
    const target = liveLang(lang);
    if (target !== lang) router.replace(localeHref(target, sectionId) + window.location.hash);
  }, [lang, sectionId, router]);

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
      setLeaving(false);
      poppedAt.current = performance.now();
      if (isMenuEntry(st)) {
        if (typeof st?.apParts === "string") restoreParts(st.apParts);
        reopenMenu(st);
      } else setMobileMenuOpen(false);
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

  // An anchor jump (contents → subsection, link with #hash) keeps the heading
  // at the top while pictures and fonts above it load and push it down
  // (Reader v7.1, Satkirti on iPad: the heading ended at the bottom of the
  // screen). Re-aligned for a few seconds; any touch / wheel / key of the
  // reader stops it. Not after back / forward: their saved place wins.
  useEffect(() => {
    let stopKeeper: (() => void) | null = null;
    const keep = () => {
      stopKeeper?.();
      stopKeeper = null;
      if (performance.now() - poppedAt.current < 1500) return;
      let id = window.location.hash.slice(1);
      if (!id) return;
      try {
        id = decodeURIComponent(id);
      } catch {
        // keep raw
      }
      const m = mainEl();
      if (!m) return;
      const until = performance.now() + 4000;
      let stopped = false;
      const timers: number[] = [];
      const align = () => {
        if (stopped) return;
        if (performance.now() > until) return stop();
        const el = document.getElementById(id);
        if (!el) return;
        const margin = parseFloat(getComputedStyle(el).scrollMarginTop) || 0;
        const d = el.getBoundingClientRect().top - m.getBoundingClientRect().top - margin;
        if (Math.abs(d) > 2) m.scrollTop += d;
      };
      const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(align) : null;
      const article = m.querySelector("article") ?? m.firstElementChild;
      if (ro && article) ro.observe(article);
      const onLoad = () => align();
      m.addEventListener("load", onLoad, true);
      const stop = () => {
        if (stopped) return;
        stopped = true;
        ro?.disconnect();
        m.removeEventListener("load", onLoad, true);
        for (const ev of ["touchstart", "wheel", "keydown", "pointerdown"]) m.removeEventListener(ev, stop);
        for (const tm of timers) window.clearTimeout(tm);
      };
      for (const ev of ["touchstart", "wheel", "keydown", "pointerdown"])
        m.addEventListener(ev, stop, { passive: true });
      for (const ms of [0, 60, 150, 300, 600, 1000, 1500, 2200, 3000, 3900]) timers.push(window.setTimeout(align, ms));
      document.fonts?.ready.then(align).catch(() => {});
      stopKeeper = stop;
    };
    const id = window.setTimeout(keep, 0);
    window.addEventListener("hashchange", keep);
    return () => {
      window.clearTimeout(id);
      window.removeEventListener("hashchange", keep);
      stopKeeper?.();
    };
  }, [pathname]);

  // Each new entry gets its place key once its page is shown.
  useEffect(() => {
    try {
      placeKey();
    } catch {
      // history unavailable
    }
  }, [pathname]);

  /** «Поиск» in the reader's top bar: the contents panel with the search box focused. */
  const openSearch = () => {
    openMenu();
    let tries = 0;
    const focus = () => {
      const input = document.querySelector<HTMLInputElement>(".mobile-menu input[type=search]");
      if (input) input.focus();
      else if (tries++ < 10) window.setTimeout(focus, 30);
    };
    window.setTimeout(focus, 0);
  };

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
      {/* Reading mode: the menu bars appear on a tap on empty space
          (components/ReaderChrome.tsx). Before <main> so Tab reaches them first. */}
      <ReaderChrome
        ui={ui}
        lang={lang}
        sectionId={sectionId}
        sections={sections}
        parts={parts}
        available={available}
        menuOpen={mobileMenuOpen}
        onOpenContents={openMenu}
        onOpenSearch={openSearch}
      />

      {/* Contents / search panel (all screen sizes) */}
      {mobileMenuOpen && (
        <div className="mobile-menu no-print fixed inset-0 z-40" data-leaving={leaving ? "" : undefined}>
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
              onLeave={leaveMenu}
            />
          </div>
        </div>
      )}

      {/* Main content area */}
      <main className="app-main flex-1 overflow-y-auto">
        <InstallBanner ui={ui} />
        {/* Content */}
        {children}
      </main>
    </div>
  );
}
