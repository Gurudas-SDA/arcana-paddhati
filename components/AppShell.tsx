"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { flushSync } from "react-dom";
import Sidebar, { restoreParts } from "@/components/Sidebar";
import InstallBanner from "@/components/InstallBanner";
import ReaderChrome from "@/components/ReaderChrome";
import type { SearchEntry } from "@/lib/book";
import { SEARCH_SCROLL_ATTR } from "@/lib/searchMark";
import {
  QUERY_STORE,
  entryView,
  isMenuEntry,
  main as mainEl,
  menuDepth,
  patchState,
  placeKey,
  pushOverlay,
  recordScroll,
  savedScroll,
  setView,
} from "@/lib/navHistory";
import {
  DEFAULT_LANG,
  LANG_STORAGE_KEY,
  getLanguage,
  isLangCode,
  liveLang,
  localeHref,
  parsePath,
  t,
  type LocaleData,
} from "@/lib/i18n";
import { BASE_PATH, stripBasePath } from "@/lib/basePath";
import { beginReadingArrival, bookTarget, readingAnchor, readingSection } from "@/lib/readingFlow";
import { readerLayout, useReaderLayout } from "@/lib/readerPrefs";
import { BOOK_EVENT, BOOK_SEGMENT, bookHref, capturePlace, keepPlace, restorePlace } from "@/lib/readingMode";

/** A link's place: its pathname (no trailing slash) + hash — what a navigation opens. */
const placeOf = (href: string): string => {
  try {
    const u = new URL(href, window.location.href);
    return u.pathname.replace(/\/+$/, "") + u.hash;
  } catch {
    return href;
  }
};

/** Whole book in one scroll (PR #2): off by default (Satkirti 14.10.2026 msg
 *  3480: chapter by chapter, as in Kindle); since A89 the «Аа» option
 *  «Прокручивать» (lib/readingMode.ts, Gurudas reading standard A3). */
const scrollMode = () => readerLayout() === "scroll";

/** A65 (Codex 10.10): a page that has not come by now is given up. The КСВ
 *  phone's slowest real load was 19 s, so the menu waits longer than that. */
const NAV_FAIL_MS = 25000;

const searchIndexUrl = (lang: string) =>
  `${BASE_PATH}/search-index.${lang}.json`;

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
  const restoredReadingPlace = useRef<string | null>(null);
  /** The reader has just chosen another layout in «Аа» (not a page load). */
  const switchedLayout = useRef(false);
  const layoutSeen = useRef<string | null>(null);
  /** When the reader last chose another layout (a back's place keeper yields). */
  const layoutChangedAt = useRef(-1e9);
  const layout = useReaderLayout();
  /** The whole book is shown (ContinuousBook announces itself). */
  const [bookShown, setBookShown] = useState(false);
  useEffect(() => {
    const check = () => setBookShown(!!document.querySelector("[data-continuous-book]"));
    // After the unmount's DOM removal too.
    const onBook = () => { check(); window.setTimeout(check, 0); };
    check();
    window.addEventListener(BOOK_EVENT, onBook);
    return () => window.removeEventListener(BOOK_EVENT, onBook);
  }, [pathname]);
  // A change of the stored layout after the page's own (hydration starts
  // from «Листать»): the reader chose it in «Аа».
  useEffect(() => {
    if (layoutSeen.current === null) {
      layoutSeen.current = readerLayout();
      return;
    }
    if (layout !== layoutSeen.current) {
      layoutSeen.current = layout;
      switchedLayout.current = true;
      layoutChangedAt.current = performance.now();
    }
  }, [layout]);
  // The app restores its own reading scroller. Browser restoration would
  // compete with it before popstate (WebKit returns to the initial offset).
  useEffect(() => {
    try {
      window.history.scrollRestoration = "manual";
    } catch {
      // A browser that disallows this setting retains its default behavior.
    }
  }, []);
  // Continuous reading is off (Satkirti 14.10.2026: chapter by chapter, as in
  // Kindle). Each chapter keeps its own page; «Прокручивать» in «Аа» switches
  // chapter pages to the whole-book export (A89, below).
  // Chapter by chapter: a reload puts the reader back where he was reading
  // (the entry's recorded scroll), not at the URL's subsection heading — as
  // Kindle and Apple Books reopen the book at the last place. A touch, wheel
  // or key of the reader stops the re-application (pictures load meanwhile).
  useEffect(() => {
    if (scrollMode()) return;
    const nav = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
    if (nav?.type !== "reload") return;
    const scroll = savedScroll(window.history.state);
    if (scroll === undefined) return;
    restoredReadingPlace.current = placeOf(window.location.href);
    let stopped = false;
    const stop = () => { stopped = true; };
    const events = ["touchstart", "wheel", "keydown", "pointerdown"] as const;
    for (const ev of events) window.addEventListener(ev, stop, { passive: true, capture: true });
    const apply = () => {
      if (stopped) return;
      const el = mainEl();
      if (el) el.scrollTop = scroll;
    };
    requestAnimationFrame(apply);
    const timers = [60, 160, 320, 600, 1000, 1600].map((ms) => window.setTimeout(apply, ms));
    const end = window.setTimeout(() => {
      for (const ev of events) window.removeEventListener(ev, stop, { capture: true });
    }, 1700);
    return () => {
      timers.forEach((t) => window.clearTimeout(t));
      window.clearTimeout(end);
      for (const ev of events) window.removeEventListener(ev, stop, { capture: true });
    };
  }, []);
  // «Прокручивать»: a chapter page is replaced by the whole book at the same
  // place (its URL kept). A switch from «Листать» keeps the words at the top.
  useEffect(() => {
    if (layout !== "scroll" || !scrollMode()) return;
    if (!sectionId || document.querySelector("[data-continuous-book]")) return;
    if (!sections.some((section) => section.id === sectionId) && !parts.some((part) => part.id === sectionId)) return;
    const scroll = savedScroll(window.history.state);
    if (switchedLayout.current) {
      switchedLayout.current = false;
      keepPlace(capturePlace());
    }
    if (!beginReadingArrival(window.location.href, scroll)) return;
    if (window.history.state?.apBook && scroll !== undefined) {
      restoredReadingPlace.current = placeOf(window.location.href);
    }
    router.replace(bookHref(lang), { scroll: false });
  }, [layout, lang, sectionId, sections, parts, router]);
  // «Листать» chosen in the book: the chapter being read on its own page, the
  // same words at the top. (Its URL is already the chapter's.)
  useEffect(() => {
    if (layout !== "page" || scrollMode() || !document.querySelector("[data-continuous-book]")) return;
    switchedLayout.current = false;
    const place = capturePlace();
    keepPlace(place);
    const at = parsePath(stripBasePath(window.location.pathname) || "/");
    if (!at.sectionId || at.sectionId === BOOK_SEGMENT) {
      router.replace(localeHref(at.lang), { scroll: false });
      return;
    }
    const href = localeHref(at.lang, at.sectionId);
    router.replace(href, { scroll: false });
    // Should the router keep the book (same URL), load the chapter page itself.
    const fallback = window.setTimeout(() => {
      if (document.querySelector("[data-continuous-book]")) window.location.replace(BASE_PATH + href);
    }, 2500);
    return () => window.clearTimeout(fallback);
  }, [layout, router]);
  // A kept place is put back once its chapter is shown in the other export.
  useEffect(() => restorePlace() ?? undefined, [pathname, bookShown]);

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
    // A menu opened now is never "loading" (Claude verifier 11.10: after a
    // replaced load the bar showed in every reopened contents).
    setLeaving(false);
    setNavFailed(false);
    setMobileMenuOpen(true);
  };

  /** Close from the UI: pop menu entries, or reveal the proposal's chapter. */
  const closeMenu = useCallback(() => {
    // ✕ / backdrop / Esc while a page loads: the load is cancelled — history.go(-d)
    // is a back navigation, which makes Next.js discard the pending one (A65).
    setLeaving(false);
    setNavFailed(false);
    setMobileMenuOpen(false);
    if (isMenuEntry() && window.history.state?.apDepth === 0) {
      // The expanded contents share the chapter navigation entry.
      // Closing the panel reveals that chapter instead of returning to cover.
      patchState({}, ["apMenu", "apDepth", "apParts", "apLit", "apNav", "apResult", "apExp"]);
      return;
    }
    const d = menuDepth();
    if (d > 0) window.history.go(-d);
  }, []);

  /**
   * Leave the menu for a place (link or result): keep its entries (with the query).
   * `navigating` — another page is opening: the menu stays on screen until that
   * page is rendered (Reader v7.1: on a slow device the old page — often the
   * cover — flashed for 2–3 s between the menu and the chapter), with a
   * loading bar at the top and «загружается…» on the tapped row (A65, КСВ
   * 07.10.2026: 0–7 s, sometimes 19 s, with no sign of loading).
   */
  const [leaving, setLeaving] = useState(false);
  const leaveTimer = useRef<number | undefined>(undefined);
  /** A65 (Codex 10.10): the tapped page never came — the client load (RSC) AND
   *  Next.js's fallback full page load both failed, or the network hangs. After
   *  NAV_FAIL_MS the loading state is cleared (no endless «busy») and the row
   *  says quietly «не удалось загрузить — коснитесь ещё раз». */
  const [navFailed, setNavFailed] = useState(false);
  const failTimer = useRef<number | undefined>(undefined);
  /** While a page is loading, taps in the contents list are ignored (A65: a
   *  repeated tap must not start the navigation again). After the safety time
   *  the reader may choose ANOTHER place: its navigation replaces the pending
   *  one (Next.js discards a pending navigation when a new one starts — its
   *  app-router-instance action queue), so history grows by one entry and the
   *  last choice wins. A tap on the place already loading never starts it again
   *  (A65 fix, Codex 10.10: after 8 s a repeated tap restarted the load). The
   *  menu and the loading signs stay until the page is shown, or until the
   *  reader closes the menu / goes back (that cancels the load). */
  const tapsLocked = useRef(false);
  /** The place being loaded (pathname + hash): the transition token of the pending navigation. */
  const pendingHref = useRef<string | null>(null);
  const leaveMenu = useCallback((navigating?: boolean, href?: string) => {
    try {
      if (isMenuEntry()) setView({ apQuery: searchQueryRef.current });
      sessionStorage.setItem(QUERY_STORE, searchQueryRef.current);
    } catch {
      // storage unavailable
    }
    window.clearTimeout(leaveTimer.current);
    window.clearTimeout(failTimer.current);
    setNavFailed(false);
    if (navigating) {
      setLeaving(true);
      tapsLocked.current = true;
      const place = href ? placeOf(href) : null;
      pendingHref.current = place;
      // Safety net: if the page does not come, a tap may start it again. The
      // menu is NOT closed here — that showed the old page for the rest of a
      // slow load (A65: loads of 19 s); the close button / backdrop still work.
      leaveTimer.current = window.setTimeout(() => {
        tapsLocked.current = false;
      }, 8000);
      // Still the same transition and no page yet: it failed — clear the
      // loading state (a page that comes later still closes the menu).
      failTimer.current = window.setTimeout(() => {
        if (pendingHref.current !== place || placeOf(window.location.href) === place) return;
        tapsLocked.current = false;
        pendingHref.current = null;
        setLeaving(false);
        setNavFailed(true);
      }, NAV_FAIL_MS);
      return;
    }
    tapsLocked.current = false;
    pendingHref.current = null;
    setLeaving(false);
    setMobileMenuOpen(false);
  }, []);
  // The new page is rendered: now the menu goes.
  const [leftFrom, setLeftFrom] = useState(pathname);
  if (leftFrom !== pathname) {
    setLeftFrom(pathname);
    // (also a page that comes after its load was given up as failed)
    if (leaving || navFailed) {
      setLeaving(false);
      setNavFailed(false);
      setMobileMenuOpen(false);
    }
  }
  // The loading state lives only in the open menu: with the menu closed (by
  // whatever path) nothing is loading — no «загружается» left in the live
  // region (Claude verifier 11.10, A65 «another row after 8 s»).
  if (!mobileMenuOpen && (leaving || navFailed)) {
    setLeaving(false);
    setNavFailed(false);
  }
  useEffect(() => {
    if (!leaving) {
      window.clearTimeout(leaveTimer.current);
      window.clearTimeout(failTimer.current);
      tapsLocked.current = false;
      pendingHref.current = null;
    }
  }, [leaving]);
  // No timer outlives the shell (A65, Codex LOW).
  useEffect(
    () => () => {
      window.clearTimeout(leaveTimer.current);
      window.clearTimeout(failTimer.current);
    },
    []
  );
  /** A65: while the tapped page loads, a tap in the contents / results list does
   *  nothing — until the safety time; after it, only a tap on the place already
   *  loading is ignored (never a second navigation to it). */
  const guardTaps = (e: React.MouseEvent) => {
    if (!leaving) return;
    const el = e.target as Element;
    const link = el.closest?.("a[href]") as HTMLAnchorElement | null;
    if (!el.closest?.("nav") && !link) return;
    if (!tapsLocked.current) {
      if (!link || !pendingHref.current || placeOf(link.href) !== pendingHref.current) return;
    }
    e.preventDefault();
    e.stopPropagation();
  };

  // <html lang> follows the language on client-side navigation (the static
  // HTML already has it, see scripts/patch-html-lang.mjs).
  useEffect(() => {
    document.documentElement.lang = htmlLang;
  }, [htmlLang]);
  useEffect(() => {
    if (!document.querySelector("[data-continuous-book]")) return;
    const section = sections.find((item) => item.id === sectionId) ?? parts.find((item) => item.id === sectionId);
    document.title = section ? t(ui, "meta.sectionTitle", { section: section.title }) : t(ui, "meta.title");
  }, [pathname, sectionId, sections, parts, ui]);

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
      if (e.key === "Escape" && document.querySelector(".mobile-menu[data-open]")) {
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
      const query = entryView(st).apQuery;
      let q = typeof query === "string" ? query : null;
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
      setNavFailed(false);
      poppedAt.current = performance.now();
      if (isMenuEntry(st)) {
        const parts = entryView(st).apParts;
        if (typeof parts === "string") restoreParts(parts);
        reopenMenu(st);
      } else setMobileMenuOpen(false);
      // Put the place back after Next.js has rendered the entry's page.
      const target = savedScroll(st);
      const hash = window.location.hash.slice(1);
      const popAt = performance.now();
      const apply = () => {
        const el = mainEl();
        if (!el) return;
        // «Аа» closed by this back, then another layout chosen: its export
        // keeps the place (A89), not this entry's old offset.
        if (layoutChangedAt.current > popAt) return;
        if (target !== undefined) {
          el.scrollTop = target;
        } else if (hash) {
          let id = hash;
          try {
            id = decodeURIComponent(hash);
          } catch {
            // keep raw
          }
          readingAnchor(id)?.scrollIntoView({ block: "start" });
        } else {
          const section = bookTarget(parsePath(stripBasePath(window.location.pathname) || "/").sectionId);
          if (section) section.scrollIntoView({ block: "start" });
          else el.scrollTop = 0;
        }
      };
      requestAnimationFrame(apply);
      for (const ms of [60, 160, 320, 600]) window.setTimeout(apply, ms);
    };
    window.addEventListener("popstate", onPop);
    // A65: the page came back from the browser's page cache (e.g. after a failed
    // client navigation fell back to a full page load, then "back") — no loading
    // state survives from before.
    const onPageShow = (e: PageTransitionEvent) => {
      if (e.persisted) {
        setLeaving(false);
        setNavFailed(false);
      }
    };
    window.addEventListener("pageshow", onPageShow);

    // Reloaded (or restored from the page cache) on a menu entry: its own open
    // lists, not the session's last ones (a reload in the middle of history —
    // Reader v7.6.1).
    if (isMenuEntry()) {
      const st = window.history.state as Record<string, unknown> | null;
      const parts = entryView(st).apParts;
      if (typeof parts === "string") restoreParts(parts);
      reopenMenu(st);
    }
    return () => {
      m.removeEventListener("scroll", onScroll);
      window.removeEventListener("popstate", onPop);
      window.removeEventListener("pageshow", onPageShow);
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
      // A reload restores the saved continuous-book position, including
      // reading farther below the URL's original subsection heading.
      if (restoredReadingPlace.current === placeOf(window.location.href)) return;
      restoredReadingPlace.current = null;
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
        // A search result's word took over the place (lib/searchMark.ts).
        if (document.documentElement.hasAttribute(SEARCH_SCROLL_ATTR)) return stop();
        if (performance.now() > until) return stop();
        const el = readingAnchor(id);
        if (!el) return;
        const margin = parseFloat(getComputedStyle(el).scrollMarginTop) || 0;
        const d = el.getBoundingClientRect().top - m.getBoundingClientRect().top - margin;
        if (Math.abs(d) > 2) m.scrollTop += d;
      };
      const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(align) : null;
      const scope = readingSection();
      const article = scope?.querySelector("article") ?? scope;
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

  // Each new entry gets its place key once its page is shown (entries made by
  // the app have it already; one made by Next.js' router gets it once).
  useEffect(() => {
    try {
      placeKey();
    } catch {
      // history unavailable
    }
  }, [pathname]);

  /** «Поиск» in the reader's top bar: the contents panel with the search box focused. */
  const openSearch = () => {
    // The index starts loading now (on iPhone it takes seconds), not on focus.
    loadSearchIndex();
    // Vraja Lila msg 5316 p. 3 (iPhone: the keyboard only on the second tap):
    // the panel is rendered synchronously and the field focused inside this
    // tap, so Safari opens the keyboard at once (a focus from a timer is not
    // a user gesture). The retry below stays for a panel that is not there.
    flushSync(() => openMenu());
    const now = document.querySelector<HTMLInputElement>(".mobile-menu[data-open] input[type=search]");
    if (now) {
      now.focus();
      return;
    }
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

  const sidebarProps = {
    sections,
    parts,
    lang,
    ui,
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
        hasWbw={hasWbw}
        menuOpen={mobileMenuOpen}
        onOpenContents={openMenu}
        onOpenSearch={openSearch}
      />

      {/* Contents / search panel (all screen sizes) */}
      {mobileMenuOpen && (
        <div
          className="mobile-menu no-print fixed inset-0 z-40"
          // Vraja Lila msg 5316 p. 3a: «the menu is open» is this attribute, not the panel's presence in the DOM.
          data-open=""
          data-leaving={leaving ? "" : undefined}
          onClickCapture={guardTaps}
        >
          {/* A65: the tapped page is loading — shown at once, until it is rendered. */}
          {leaving && (
            <div
              className="nav-progress"
              data-nav-progress=""
              role="progressbar"
              aria-label={ui["sidebar.loading"] ?? "loading"}
            />
          )}
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
              navigating={leaving}
              navFailed={navFailed}
            />
          </div>
        </div>
      )}

      {/* A65: «загружается…» for screen readers — a live region that always exists
          (announced when its text appears) and is outside the menu, so no aria-busy
          container hides it. The row itself is aria-busy (Sidebar.tsx). */}
      <div className="sr-only" role="status" aria-live="polite" data-nav-live="">
        {leaving
          ? (ui["sidebar.loading"] ?? "loading")
          : navFailed
            ? (ui["sidebar.loadFailed"] ?? "")
            : ""}
      </div>

      {/* Main content area */}
      {/* Chapter by chapter, the page itself is the place being read: the same
          marker as the continuous book's current chapter (tools and QA probes). */}
      <main className="app-main flex-1 overflow-y-auto" {...(bookShown ? {} : { "data-reader-current": "" })}>
        <InstallBanner ui={ui} />
        {/* Content */}
        {children}
      </main>
    </div>
  );
}
