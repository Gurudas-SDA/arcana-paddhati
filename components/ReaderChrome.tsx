"use client";

/**
 * Reading mode (Apple Books style; Satkirti's choice of 05.10.2026, variant Б).
 *
 * While reading only the text is on screen, with a faint line at the bottom
 * («Глава 8 · 35 %»). A tap / click on EMPTY space or plain text shows the
 * menu: the top bar «Содержание» · «Поиск» · «Аа» and the bottom bar
 * («‹ Назад» · «Глава N из M · %» · «Вперёд ›»). Another tap hides
 * it. The bars also appear on a small scroll back up and at the end of a
 * chapter; they hide on scrolling down and after ~4 s without interaction
 * (never while the «Аа» panel or the contents are open).
 *
 * UI rule 1 (refined 05.10.2026): interactive elements (list rows ↔ picture,
 * links, buttons, verse chips, «Настроение Гурудева», pictures — the Deities
 * included) never toggle the menu; if something is highlighted, the first
 * tap on empty space only clears the highlight (components/Hotspots.tsx), the
 * next one toggles the menu. A tap that ends a text selection does nothing.
 * Exception (Reader v7.5, Satkirti 07.10.2026): the parampara portraits are
 * page — a tap on the photo toggles the menu like a tap on empty space.
 *
 * The cover (05.10.2026, Satkirti on Android): a tap on ANY point of the
 * cover — the picture included — shows / hides the menu; only real controls
 * (links, buttons, the install banner's buttons) keep their own function.
 *
 * Back (UI rule 6): the «Аа» panel is a history entry; "back" to it opens it
 * again, so Back retraces every step (lib/navHistory.ts).
 *
 * Bookmark (variant A, Vraja Lila msg 5380, 20.10.2026): a 4th button — a
 * ribbon — in the top bar before «Аа». A tap sets a bookmark on the place on
 * screen (chapter + subsection, lib/bookmarks.ts) and shows a toast
 * «Закладка поставлена · Отменить»; a tap on a place that has one removes it
 * (rule 10.1). Before it is set, a window asks its name (V34, Satkirti msg 5866,
 * Vraja Lila msg 5869): the subsection's (chapter's) name, which can be changed;
 * the bookmark keeps the exact block at the top of the screen (msg 5872). It only writes to the device: no history step, «Назад» never
 * touches it (rule 10.2); works offline. Not on the cover / part pages.
 *
 * Bottom bar — chapter navigation (V17, Vraja Lila msg 796 / 5635 / 5639,
 * 20.10.2026; «Стандарты» 0а): «‹ Назад» and «Вперёд ›» at the screen edges go
 * to the previous / next page of the contents (lib/book.ts readingOrder: the
 * chapters and the parts' pages, in the contents' order), in «Страницы» and in
 * «Лента» (there: a jump to the chapter's start, as from the contents). On the
 * first page there is no «‹ Назад», on the last no «Вперёд ›» (absent, not
 * pale). No «where we are / %» line in the bar (the faint status line at the
 * bottom of the page stays) and no own history notes; the system / browser
 * Back still retraces the steps (lib/navHistory.ts). The bars' texts are not
 * selectable (Reader v7: Chrome on Android would look the word up).
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { takeEarlyTap } from "@/lib/earlyTap";
import { exitGhost } from "@/lib/exitGhost";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import { chapterNeighbours, readingOrder, type TocPart, type TocSection } from "@/lib/book";
import { localeHref, parsePath, t, type UiDict } from "@/lib/i18n";
import {
  BOOKMARK_TOAST_END_EVENT,
  BOOKMARK_TOAST_EVENT,
  BOOKMARKS_EVENT,
  bookmarkOnScreen,
  captureBookmarkBlock,
  defaultBookmarkName,
  ownName,
  readBookmarks,
  toggleBookmark,
  writeBookmarks,
  type Bookmark,
} from "@/lib/bookmarks";
import BookmarkNameDialog from "@/components/BookmarkNameDialog";
import { captureReadingPlace } from "@/lib/readingPlace";
import { stripBasePath } from "@/lib/basePath";
import { main as mainEl, pushOverlay, recordScroll } from "@/lib/navHistory";
import { followBookLink, readingHref, readingSection } from "@/lib/readingFlow";
import { useReadingSubsection } from "@/lib/readingPosition";
import { searchMarkOn } from "@/lib/searchMark";
import {
  setShowAllTranslations,
  setShowAllWbw,
  useShowAllTranslations,
  useShowAllWbw,
} from "@/lib/translationsPref";
import {
  LAYOUTS,
  SIZES,
  THEMES,
  setReaderLayout,
  setReaderTheme,
  stepReaderSize,
  useReaderLayout,
  useReaderSize,
  useReaderTheme,
  type ReaderTheme,
} from "@/lib/readerPrefs";

/** Taps that start or end on these never toggle the menu. */
const NO_TOGGLE = [
  "a", "button", "input", "textarea", "select", "option", "label", "summary",
  "[role=button]", "[role=dialog]", "[role=switch]", "[role=slider]", "[contenteditable]",
  // A numbered picture (.hs-img under its overlay) acts only through its
  // parts; its empty area is page (Reader v7.1, UI rule 1).
  // A parampara portrait (and its ornament) is page: a tap on it toggles the
  // bars like empty space (Reader v7.5, Satkirti 07.10.2026 — the old
  // exception for this photo is cancelled).
  "img:not(.hs-img):not(.portrait-img)", "svg:not(.hs-overlay):not(.portrait-ornament):not(.portrait-frame-lines)",
  "picture:not(.portrait-picture)", "video", "canvas",
  ".hs-text", ".hs-cell", ".hs-hit", ".hs-peek", ".hs-inert",
  ".mood-toggle", ".verse-chips", ".mantra-chips", "[data-no-reader-tap]",
].join(",");

/** On the cover only real controls keep their function; the picture is page. */
const NO_TOGGLE_COVER = [
  "a", "button", "input", "textarea", "select", "option", "label", "summary",
  "[role=button]", "[role=dialog]", "[role=switch]", "[role=slider]", "[contenteditable]",
  "[data-no-reader-tap]",
].join(",");

/** Bars hide after this long without interaction. */
const AUTO_HIDE_MS = 4000;
/** The chapter's start: the reading area is this close to it (V17). */
const EDGE_PX = 4;
/** Scroll down by this much hides them. */
const HIDE_ON_DOWN_PX = 24;
/** The one-time hint stays this long. */
const HINT_MS = 6000;
const HINT_KEY = "ap.readerHintSeen";
/** The bookmark toast («Закладка поставлена · Отменить») stays this long. */
const BOOKMARK_TOAST_MS = 4000;

const THEME_SWATCH: Record<ReaderTheme, string> = {
  white: "#FFFFFF",
  sepia: "#EFE6D2",
  night: "#16130F",
};

function selText(): string {
  try {
    return window.getSelection()?.toString().trim() ?? "";
  } catch {
    return "";
  }
}

/** Something on a numbered picture / list is highlighted. */
function highlightOn(): boolean {
  return !!readingSection()?.querySelector(".hs-row[data-active], .hs-img-faded") || searchMarkOn();
}

/** A window of its own is open (contents/search drawer, «Настроение Гурудева», install instructions). */
function overlayOpen(): boolean {
  return !!document.querySelector(".mobile-menu[data-open], .mood-overlay, .install-modal, .bookmark-name-modal");
}

/**
 * Where the reading area is in the chapter being read (V17, Vraja Lila msg 5645,
 * 20.10.2026): at its very start, or at its end (the room after the end,
 * .chapter-end-space, is not reading). «Страницы»: the page; «Лента»: the
 * chapter's own section of the book.
 */
function chapterEdges(): { start: boolean; end: boolean } {
  const m = mainEl();
  if (!m) return { start: false, end: false };
  const root = readingSection();
  if (!root || root === m) {
    const spaces = m.querySelectorAll<HTMLElement>(".chapter-end-space");
    const sp = spaces[spaces.length - 1];
    const max = Math.max(0, m.scrollHeight - m.clientHeight - (sp ? sp.offsetHeight : 0));
    return { start: m.scrollTop <= EDGE_PX, end: max > 120 && m.scrollTop >= max - 2 };
  }
  const mr = m.getBoundingClientRect();
  const r = root.getBoundingClientRect();
  const margin = parseFloat(getComputedStyle(root).scrollMarginTop) || 0;
  const sp = root.querySelector<HTMLElement>(".chapter-end-space")?.offsetHeight ?? 0;
  return { start: r.top - mr.top >= margin - EDGE_PX, end: r.bottom - sp <= mr.bottom + 2 };
}

function isPanelEntry(): boolean {
  try {
    return (window.history.state as Record<string, unknown> | null)?.apAa === true;
  } catch {
    return false;
  }
}

export default function ReaderChrome({
  ui,
  lang,
  sectionId,
  sections,
  parts,
  available,
  hasWbw,
  menuOpen,
  menuClosing = false,
  onOpenContents,
  onOpenSearch,
}: {
  ui: UiDict;
  lang: string;
  sectionId: string | null;
  sections: TocSection[];
  parts: TocPart[];
  available: string[];
  /** The language's book has word-by-word data (else its switch is hidden). */
  hasWbw: boolean;
  /** The contents / search drawer is open. */
  menuOpen: boolean;
  /** The drawer is closed for the page but still sliding back (components/AppShell.tsx, V16). */
  menuClosing?: boolean;
  onOpenContents: () => void;
  /** Also from the open «Аа» panel: the menu then replaces its history entry. */
  onOpenSearch: () => void;
}) {
  const [shown, setShown] = useState(false);
  const [panel, setPanel] = useState(false);
  const [pct, setPct] = useState(0);
  const [hint, setHint] = useState(false);
  const theme = useReaderTheme();
  const showAllWbw = useShowAllWbw();
  const showAllTranslations = useShowAllTranslations();
  const size = useReaderSize();
  const layout = useReaderLayout();
  /** The drawer is on screen (open, or sliding back): the bottom bar stays above
   *  its dimming (V19, Vraja Lila 20.10.2026). */
  const menuShown = menuOpen || menuClosing;
  const router = useRouter();
  /** The contents' pages in order, and this page's neighbours (V17). */
  const order = useMemo(() => readingOrder(sections.map((s) => s.id), parts), [sections, parts]);
  const { prev: prevPage, next: nextPage } = chapterNeighbours(order, sectionId);

  // Mirrors of the state for the (long-lived) event listeners.
  const shownRef = useRef(false);
  const panelRef = useRef(false);
  const menuRef = useRef(menuOpen);
  const atEnd = useRef(false);
  const hover = useRef(false);
  const quietUntil = useRef(0);
  const hideTimer = useRef<number | undefined>(undefined);
  const lastScrollAt = useRef(0);
  const barsRef = useRef<HTMLDivElement>(null);
  /** «Аа» panel: closes the way it opened, backwards (lib/exitGhost.ts, Vraja Lila msg 5521). */
  const panelNodeRef = useCallback((node: HTMLDivElement | null) => {
    if (!node) return;
    return () => exitGhost(node, "reader-panel-out", 160);
  }, []);

  const panelBackdropRef = useCallback((node: HTMLDivElement | null) => {
    if (!node) return;
    return () => exitGhost(node, "reader-panel-backdrop reader-panel-backdrop-out", 160);
  }, []);

  // A new page: reading mode again (render-time adjustment, no effect) —
  // unless "back" returned to a step of that page with the «Аа» panel open.
  const [lastPath, setLastPath] = useState(`${lang}/${sectionId ?? ""}`);
  /** «‹ Назад» / «Вперёд ›» was pressed: the next page keeps the bars (V17). */
  const [chapterSwitch, setChapterSwitch] = useState(false);
  const [popPanelKey, setPopPanelKey] = useState<string | null>(null);
  const pathKey = `${lang}/${sectionId ?? ""}`;
  if (pathKey !== lastPath) {
    setLastPath(pathKey);
    const keepPanel = popPanelKey === pathKey;
    setPopPanelKey(null);
    // After «‹ Назад» / «Вперёд ›» the bars simply stay where they are (V17,
    // Vraja Lila msg 5645: «нечего не дёргается»); in «Лента» the address
    // follows the reading — the bars follow the scroll there, not the address.
    setShown(keepPanel || (chapterSwitch && shown) || (layout === "scroll" && shown));
    setChapterSwitch(false);
    setPanel(keepPanel);
    setPct(0);
  }

  const pathKeyRef = useRef(pathKey);
  useEffect(() => {
    pathKeyRef.current = pathKey;
  }, [pathKey]);

  useEffect(() => {
    shownRef.current = shown;
    panelRef.current = panel;
    menuRef.current = menuOpen;
    const root = document.documentElement;
    if (shown) root.setAttribute("data-reader-bars", "");
    else root.removeAttribute("data-reader-bars");
    // the «Аа» panel is open: the language list then uses its dimming alone (V27b)
    if (panel) root.setAttribute("data-aa-open", "");
    else root.removeAttribute("data-aa-open");
  }, [shown, panel, menuOpen]);

  const clearTimer = () => window.clearTimeout(hideTimer.current);

  /** (Re)start the auto-hide countdown when nothing holds the bars open. */
  const arm = useCallback(() => {
    clearTimer();
    if (!shownRef.current || panelRef.current || menuRef.current || atEnd.current || hover.current) return;
    // At the chapter's start or end the bars stay (V17, Vraja Lila msg 5645).
    if (!isHomeRef.current) {
      const edge = chapterEdges();
      if (edge.start || edge.end) return;
    }
    const active = document.activeElement;
    if (active && barsRef.current?.contains(active) && active.matches(":focus-visible")) return;
    hideTimer.current = window.setTimeout(() => {
      if (panelRef.current || menuRef.current || hover.current) return;
      shownRef.current = false;
      setShown(false);
    }, AUTO_HIDE_MS);
  }, []);

  const show = useCallback(() => {
    shownRef.current = true;
    setShown(true);
    setHint(false);
    arm();
  }, [arm]);

  /** Close the «Аа» panel from the UI: pop its history entry (rule 6). */
  const closePanel = useCallback(() => {
    panelRef.current = false;
    setPanel(false);
    if (isPanelEntry()) window.history.back();
  }, []);

  const hide = useCallback(() => {
    clearTimer();
    if (panelRef.current) closePanel();
    shownRef.current = false;
    setShown(false);
  }, [closePanel]);

  // Re-arm when a panel / the drawer closes.
  useEffect(() => {
    if (shown && !panel && !menuOpen) arm();
    if (panel || menuOpen) clearTimer();
  }, [shown, panel, menuOpen, arm]);

  useEffect(() => () => clearTimer(), []);


  const isHome = sectionId === null;
  const isHomeRef = useRef(isHome);
  useEffect(() => {
    isHomeRef.current = isHome;
  }, [isHome]);

  const section = sections.find((s) => s.id === sectionId);
  const part = parts.find((p) => p.id === sectionId);
  const currentPart = part ?? parts.find((p) => p.sections.includes(sectionId ?? ""));
  const [subId] = useReadingSubsection(pathKey, section?.subsections.map((sub) => sub.id).join("|") ?? "");
  const subNumber = section?.subsections.find((sub) => sub.id === subId)?.num;

  // ---- bookmark (variant A) ------------------------------------------------------
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [bmToast, setBmToast] = useState<{ added: boolean; undo: Bookmark[] } | null>(null);
  const bmToastTimer = useRef<number | undefined>(undefined);
  useEffect(() => {
    const update = () => setBookmarks(readBookmarks());
    const id = window.setTimeout(update, 0);
    // A bookmark removed from the «Закладки» list (Vraja Lila msg 5439/5440,
    // variant 2а): the same toast as for this button, with «Отменить».
    const removedElsewhere = (e: Event) => {
      const undo = (e as CustomEvent<{ undo?: Bookmark[] }>).detail?.undo;
      if (!Array.isArray(undo)) return;
      window.clearTimeout(bmToastTimer.current);
      setBmToast({ added: false, undo });
      bmToastTimer.current = window.setTimeout(() => setBmToast(null), BOOKMARK_TOAST_MS);
    };
    window.addEventListener(BOOKMARKS_EVENT, update);
    window.addEventListener(BOOKMARK_TOAST_EVENT, removedElsewhere);
    window.addEventListener("storage", update);
    return () => {
      window.clearTimeout(id);
      window.clearTimeout(bmToastTimer.current);
      window.removeEventListener(BOOKMARKS_EVENT, update);
      window.removeEventListener(BOOKMARK_TOAST_EVENT, removedElsewhere);
      window.removeEventListener("storage", update);
    };
  }, []);
  // The toast is over (time out, «Отменить» or replaced by none): the «Закладки»
  // list drops the rows it kept pale until now.
  const bmToastOn = !!bmToast;
  useEffect(() => {
    if (!bmToastOn) window.dispatchEvent(new Event(BOOKMARK_TOAST_END_EVENT));
  }, [bmToastOn]);
  // The place on screen (V34, msg 5872/5881/5882): the ribbon is filled when a
  // bookmark of this chapter is on screen (or ±1 block from the top) — «примерно
  // на том же месте»; several bookmarks per subsection. Measured when scrolling stops.
  const [hereId, setHereId] = useState<string | null>(null);
  const sectionKey = section?.id ?? "";
  const subKey = subId ?? null;
  useEffect(() => {
    const m = mainEl();
    let timer: number | undefined;
    const measure = () => {
      try {
        setHereId(sectionKey ? (bookmarkOnScreen(readBookmarks(), sectionKey, lang, subKey)?.id ?? null) : null);
      } catch {
        setHereId(null);
      }
    };
    const onScroll = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(measure, 150);
    };
    const first = window.setTimeout(measure, 300);
    m?.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.clearTimeout(first);
      window.clearTimeout(timer);
      m?.removeEventListener("scroll", onScroll);
    };
  }, [pathKey, layout, bookmarks, sectionKey, subKey, lang]);
  const bookmarkHere = hereId ? bookmarks.find((b) => b.id === hereId) : undefined;
  /** The name window of a bookmark about to be set (V34). */
  const [bmAsk, setBmAsk] = useState<{ section: string; anchor: string | null; block: number; name: string } | null>(null);
  const showBmToast = (added: boolean, before: Bookmark[]) => {
    setBookmarks(readBookmarks());
    window.clearTimeout(bmToastTimer.current);
    setBmToast({ added, undo: before });
    bmToastTimer.current = window.setTimeout(() => setBmToast(null), BOOKMARK_TOAST_MS);
  };
  /** Remove the bookmark on the place on screen, or ask the name of a new one
   *  (V34); storage only, no history step. */
  const onBookmark = () => {
    if (!section) return;
    let place = null;
    try {
      place = captureReadingPlace(lang, section.subsections.map((sub) => sub.id));
    } catch {
      // not measurable now: chapter + subsection are enough
    }
    const anchor = subId ?? place?.anchor ?? null;
    let block = place && place.section === section.id ? place.block : 0;
    try {
      // The exact place (msg 5872): the block at the top of what is visible.
      block = captureBookmarkBlock() ?? block;
    } catch {
      // not measurable now
    }
    // A bookmark about here: the tap removes it (rule 10.1; Vraja Lila msg 5882).
    let here: Bookmark | undefined;
    try {
      here = bookmarkOnScreen(readBookmarks(), section.id, lang, anchor);
    } catch {
      here = undefined;
    }
    if (here) {
      const { added, before } = toggleBookmark(section.id, here.anchor ?? null, here.block, lang);
      showBmToast(added, before);
      return;
    }
    setBmAsk({ section: section.id, anchor, block, name: defaultBookmarkName(section, anchor) });
  };
  const confirmBookmark = (name: string) => {
    const ask = bmAsk;
    setBmAsk(null);
    if (!ask) return;
    const { added, before } = toggleBookmark(ask.section, ask.anchor, ask.block, lang, ownName(name, ask.name));
    showBmToast(added, before);
  };
  const undoBookmark = () => {
    window.clearTimeout(bmToastTimer.current);
    if (bmToast) writeBookmarks(bmToast.undo);
    setBookmarks(readBookmarks());
    setBmToast(null);
  };
  // «82 %» never breaks (Reader v7.1: on Android the «%» wrapped to a second line).
  const pctText = `${Math.round(pct)} %`;
  // Chapters with numbers (the Introduction group has none — Satkirti 06.10.2026):
  // there the status line names the chapter itself, with the subsection's
  // number after it («Эмблема Гаудия-матха 2»), so it never reads as a
  // chapter before Chapter 1. In a numbered chapter the number stays whole:
  // «Глава 10.4», never «Глава 10 · 10.4».
  const chapterShort = section?.num
    ? t(ui, "reader.chapter", { n: subNumber ?? section.num })
    : part
      ? t(ui, "part.label", { n: part.numeral })
      : [section?.title, subNumber].filter(Boolean).join(" ");
  const partTitle = section?.num ? currentPart?.title : undefined;

  // ---- progress + scroll behaviour --------------------------------------------
  useEffect(() => {
    const m = mainEl();
    if (!m) return;
    quietUntil.current = performance.now() + 900;
    // Only the reader's own scrolling shows / hides the bars: a scroll made by
    // the app (a picture part tapped → its list row scrolled into view, an
    // anchor jump, a restored place) never does (Reader v7.1, UI rule 1: the
    // menu appears only from the reader's gesture).
    let userAt = -1e9;
    const userGesture = () => {
      userAt = performance.now();
    };
    const onPointerMove = (e: PointerEvent) => {
      if (e.buttons) userGesture(); // dragging the scrollbar / text
    };
    const onKeyScroll = (e: KeyboardEvent) => {
      if (["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End", " "].includes(e.key)) userGesture();
    };
    m.addEventListener("touchmove", userGesture, { passive: true });
    m.addEventListener("wheel", userGesture, { passive: true });
    m.addEventListener("pointermove", onPointerMove, { passive: true });
    document.addEventListener("keydown", onKeyScroll);
    let last = m.scrollTop;
    let down = 0;
    let raf = 0;
    // The room after a chapter's end (.chapter-end-space) is not reading:
    // the chapter ends (100 %) where its text ends.
    const maxScroll = () => {
      const spaces = m.querySelectorAll<HTMLElement>(".chapter-end-space");
      const sp = spaces[spaces.length - 1];
      return Math.max(0, m.scrollHeight - m.clientHeight - (sp ? sp.offsetHeight : 0));
    };
    const measure = () => {
      raf = 0;
      const max = maxScroll();
      // Whole percents (all the status line shows): a scroll frame that does
      // not change the number does not re-render the chrome. Every frame did,
      // and on a busy phone that render held back the next scroll event, so
      // the bars came late to the reader's scroll up (s01, A89 push 16.10).
      setPct(max > 4 ? Math.round(Math.min(100, Math.max(0, (m.scrollTop / max) * 100))) : 100);
    };
    measure();
    // The bars and the reader's scrolling (V17, Vraja Lila msg 796 / 5645): at
    // the chapter's start and at its end they are out; reading on (down) takes
    // them away; scrolling up from the end takes them away too; they come back
    // only on a tap, at the chapter's end, or back at the chapter's start.
    const onScroll = () => {
      lastScrollAt.current = performance.now();
      if (!raf) raf = requestAnimationFrame(measure);
      const top = m.scrollTop;
      const d = top - last;
      last = top;
      // Momentum after a swipe keeps counting for a while (no touchmove then).
      if (performance.now() < quietUntil.current || overlayOpen() || performance.now() - userAt > 1500) {
        down = 0;
        return;
      }
      if (isHomeRef.current) return;
      const edge = chapterEdges();
      if (d > 0) {
        down += d;
        if (edge.end) {
          // End of the chapter: the bars come up (once — they stay while here).
          atEnd.current = true;
          if (!shownRef.current) show();
          else clearTimer();
          return;
        }
        if (down > HIDE_ON_DOWN_PX && shownRef.current && !panelRef.current) {
          down = 0;
          clearTimer();
          shownRef.current = false;
          setShown(false);
        }
      } else if (d < 0) {
        down = 0;
        if (atEnd.current && !edge.end) {
          // Leaving the chapter's end upwards takes away the bars it brought.
          atEnd.current = false;
          if (shownRef.current && !panelRef.current) {
            clearTimer();
            shownRef.current = false;
            setShown(false);
          }
        }
        if (edge.start && !shownRef.current) {
          // Back at the chapter's start: the bars are out again.
          show();
        }
      }
    };
    m.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      m.removeEventListener("scroll", onScroll);
      m.removeEventListener("touchmove", userGesture);
      m.removeEventListener("wheel", userGesture);
      m.removeEventListener("pointermove", onPointerMove);
      document.removeEventListener("keydown", onKeyScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [pathKey, show, arm]);

  // A chapter page that opens at its start has the bars out (V17, Vraja Lila
  // msg 5645); one that opens elsewhere (Back to a place in it, a link to a
  // subsection) gets the usual auto-hide once its place is restored.
  useEffect(() => {
    if (isHome) return;
    // Once, shortly after the page opens (its place is set by then); the
    // reader's own taps decide — a tap before that is never overruled.
    let touched = false;
    const onDown = () => {
      touched = true;
    };
    document.addEventListener("pointerdown", onDown, { capture: true, passive: true });
    const check = (mayShow: boolean) => {
      if (touched) mayShow = false;
      if (panelRef.current || menuRef.current) return;
      const edge = chapterEdges();
      // A link to a subsection (#…) is not the chapter's start.
      if (mayShow && edge.start && !window.location.hash && layout !== "scroll") {
        clearTimer();
        if (!shownRef.current) {
          shownRef.current = true;
          setShown(true);
        }
      } else {
        arm();
      }
    };
    const timers = [window.setTimeout(() => check(true), 450), window.setTimeout(() => check(false), 1300)];
    return () => {
      timers.forEach((id) => window.clearTimeout(id));
      document.removeEventListener("pointerdown", onDown, { capture: true });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathKey]);

  // Programmatic scrolls (back/forward restore, anchor jumps) do not count.
  useEffect(() => {
    const quiet = () => {
      quietUntil.current = performance.now() + 900;
    };
    const onPop = () => {
      quiet();
      if (isPanelEntry()) {
        // "Back" to the step where the «Аа» panel was open: open it again
        // (also once the entry's page is rendered, if it is another page).
        const at = parsePath(stripBasePath(window.location.pathname) || "/");
        const key = `${at.lang}/${at.sectionId ?? ""}`;
        setPopPanelKey(key === pathKeyRef.current ? null : key);
        clearTimer();
        panelRef.current = true;
        setPanel(true);
        shownRef.current = true;
        setShown(true);
        setHint(false);
      } else {
        setPopPanelKey(null);
        panelRef.current = false;
        setPanel(false);
      }
    };
    window.addEventListener("popstate", onPop);
    window.addEventListener("hashchange", quiet);
    return () => {
      window.removeEventListener("popstate", onPop);
      window.removeEventListener("hashchange", quiet);
    };
  }, []);

  // ---- tap / click on empty space toggles the menu -----------------------------
  useEffect(() => {
    const m = mainEl();
    if (!m) return;
    let start: {
      x: number;
      y: number;
      at: number;
      sel: string;
      hl: boolean;
      target: EventTarget | null;
      afterScroll: boolean;
    } | null = null;
    const blocked = (t: EventTarget | null) =>
      !(t instanceof Element) || !!t.closest(isHomeRef.current ? NO_TOGGLE_COVER : NO_TOGGLE);
    const onDown = (e: PointerEvent) => {
      if (!e.isPrimary || e.button !== 0) {
        start = null;
        return;
      }
      const now = performance.now();
      start = {
        x: e.clientX,
        y: e.clientY,
        at: now,
        sel: selText(),
        hl: highlightOn(),
        target: e.target,
        afterScroll: now - lastScrollAt.current < 150,
      };
    };
    const onCancel = () => {
      start = null;
    };
    const onUp = (e: PointerEvent) => {
      const s = start;
      start = null;
      if (!s || !e.isPrimary) return;
      if (Math.hypot(e.clientX - s.x, e.clientY - s.y) > 10) return; // a drag / scroll
      if (performance.now() - s.at > 600) return; // long press (selection)
      if (s.afterScroll) return; // the tap stopped a moving page
      if (blocked(s.target) || blocked(e.target)) return; // its own function
      if (s.sel || selText()) return; // ends or makes a text selection
      if (s.hl) return; // this tap only clears the highlight (Hotspots.tsx)
      if (overlayOpen()) return;
      setHint(false);
      if (panelRef.current || shownRef.current) hide();
      else show();
    };
    m.addEventListener("pointerdown", onDown, true);
    m.addEventListener("pointercancel", onCancel, true);
    m.addEventListener("pointerup", onUp);
    // §7: a tap made before this handler existed (slow first hydration) still
    // counts, once, under the same conditions as onUp (lib/earlyTap.ts).
    const early = takeEarlyTap();
    if (
      early &&
      performance.now() - early.at < 4000 &&
      early.t instanceof Node && m.contains(early.t) &&
      !blocked(early.t) && !blocked(early.u) &&
      !selText() && !highlightOn() && !overlayOpen() &&
      !panelRef.current && !shownRef.current
    ) {
      setHint(false);
      show();
    }
    return () => {
      m.removeEventListener("pointerdown", onDown, true);
      m.removeEventListener("pointercancel", onCancel, true);
      m.removeEventListener("pointerup", onUp);
    };
  }, [show, hide]);

  // ---- keyboard: Esc closes the panel / hides the bars ---------------------------
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape" || e.defaultPrevented || overlayOpen()) return;
      if (panelRef.current) {
        closePanel();
        arm();
      } else if (shownRef.current) {
        hide();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [closePanel, hide, arm]);

  // ---- one-time hint («Коснитесь свободного места — появится меню») -------------
  useEffect(() => {
    if (isHome) return;
    let seen = false;
    try {
      seen = localStorage.getItem(HINT_KEY) === "1";
      if (!seen) localStorage.setItem(HINT_KEY, "1");
    } catch {
      seen = true; // no storage: do not repeat it on every page
    }
    if (seen) return;
    const on = window.setTimeout(() => setHint(true), 800);
    const off = window.setTimeout(() => setHint(false), 800 + HINT_MS);
    return () => {
      window.clearTimeout(on);
      window.clearTimeout(off);
    };
  }, [isHome]);
  const [finePointer, setFinePointer] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(hover: hover) and (pointer: fine)");
    const upd = () => setFinePointer(mq.matches);
    const id = window.setTimeout(upd, 0);
    mq.addEventListener("change", upd);
    return () => {
      window.clearTimeout(id);
      mq.removeEventListener("change", upd);
    };
  }, []);

  // ---- actions --------------------------------------------------------------
  const openPanel = () => {
    if (panelRef.current) {
      closePanel();
      arm();
      return;
    }
    try {
      pushOverlay({ apAa: true });
    } catch {
      // history unavailable: the panel still opens
    }
    panelRef.current = true;
    setPanel(true);
    clearTimer();
  };

  /** «Листать» / «Прокручивать» (A89): the panel closes (its history entry
   *  popped first), then the layout changes — the app shell shows the other
   *  export at the same place (components/AppShell.tsx). */
  const chooseLayout = (next: (typeof LAYOUTS)[number]) => {
    if (next === layout) return;
    let done = false;
    const go = () => {
      if (done) return;
      done = true;
      setReaderLayout(next);
    };
    panelRef.current = false;
    setPanel(false);
    if (isPanelEntry()) {
      window.addEventListener("popstate", () => window.setTimeout(go, 0), { once: true });
      window.setTimeout(go, 700);
      window.history.back();
    } else {
      go();
    }
  };

  /**
   * Leave the «Аа» panel for another step (chapter, language, contents):
   * the panel's history entry stays under the new one, so "back" returns to
   * the panel (never "back, then push" — see lib/navHistory.ts).
   */
  const fromPanelThen = (go: () => void) => {
    if (panelRef.current) {
      panelRef.current = false;
      setPanel(false);
    }
    go();
  };

  const barEvents = {
    onPointerEnter: (e: React.PointerEvent) => {
      // A real mouse only (WebKit reports compat "mouse" pointers for taps).
      if (e.pointerType === "mouse" && window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
        hover.current = true;
        clearTimer();
      }
    },
    onPointerLeave: () => {
      if (hover.current) {
        hover.current = false;
        arm();
      }
    },
    onPointerDown: () => arm(),
    onFocus: (e: React.FocusEvent) => {
      // Keyboard (Tab) into the hidden bars shows them.
      if ((e.target as Element).matches(":focus-visible") && !shownRef.current) show();
      else clearTimer();
    },
    onBlur: () => window.setTimeout(arm, 0),
  };

  const sizeIdx = SIZES.indexOf(size);
  /** «‹ Назад» / «Вперёд ›»: the previous / next page of the contents (V17).
   *  «Лента»: a jump to the chapter's start inside the book, as from the
   *  contents (lib/readingFlow.ts followBookLink — a history entry, so the
   *  system Back returns). «Страницы»: that chapter's page, at its very top
   *  (the reading area stays mounted across pages, so Next.js' own scroll
   *  would leave it a little below its top). */
  const goChapter = (id: string) => {
    arm();
    setChapterSwitch(true);
    if (followBookLink(readingHref(lang, id))) return;
    recordScroll();
    const from = window.location.pathname;
    const t0 = performance.now();
    const toTop = () => {
      const m = mainEl();
      if (m) m.scrollTop = 0;
    };
    const wait = () => {
      if (window.location.pathname !== from) {
        toTop();
        requestAnimationFrame(toTop);
        for (const ms of [60, 160, 320]) window.setTimeout(toTop, ms);
      } else if (performance.now() - t0 < 4000) {
        requestAnimationFrame(wait);
      }
    };
    router.push(localeHref(lang, id), { scroll: false });
    requestAnimationFrame(wait);
  };

  return (
    <div
      ref={barsRef}
      className="reader-chrome no-print"
      data-shown={shown ? "" : undefined}
      data-panel={panel ? "" : undefined}
      // Also while the drawer slides back: the bottom bar stays above its fading dimming (V16 fix).
      data-menu={menuShown ? "" : undefined}
    >
      {/* Top bar: contents · search · Аа */}
      <div className="reader-bar reader-bar-top" {...barEvents}>
        <div className="reader-bar-inner">
          <button
            type="button"
            className="reader-btn"
            onClick={() => fromPanelThen(onOpenContents)}
            data-reader-action="contents"
          >
            <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="8" y1="6" x2="21" y2="6" />
              <line x1="8" y1="12" x2="21" y2="12" />
              <line x1="8" y1="18" x2="21" y2="18" />
              <line x1="3" y1="6" x2="3.01" y2="6" />
              <line x1="3" y1="12" x2="3.01" y2="12" />
              <line x1="3" y1="18" x2="3.01" y2="18" />
            </svg>
            <span>{t(ui, "reader.contents")}</span>
          </button>
          <button
            type="button"
            className="reader-btn"
            onClick={() => fromPanelThen(onOpenSearch)}
            data-reader-action="search"
          >
            <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="7" />
              <line x1="20" y1="20" x2="16.2" y2="16.2" />
            </svg>
            <span>{t(ui, "reader.search")}</span>
          </button>
          {!isHome && section && (
            <button
              type="button"
              className="reader-btn reader-bookmark ml-auto"
              aria-pressed={!!bookmarkHere}
              aria-label={t(ui, bookmarkHere ? "reader.bookmarkRemove" : "reader.bookmarkAdd")}
              title={t(ui, bookmarkHere ? "reader.bookmarkRemove" : "reader.bookmarkAdd")}
              onClick={() => {
                arm();
                onBookmark();
              }}
              data-reader-action="bookmark"
            >
              <svg aria-hidden="true" width="18" height="20" viewBox="0 0 18 20" fill={bookmarkHere ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinejoin="round">
                <path d="M3 1.5h12v17l-6-4.6-6 4.6z" />
              </svg>
            </button>
          )}
          <button
            type="button"
            className={`reader-btn reader-aa${!isHome && section ? "" : " ml-auto"}`}
            aria-label={t(ui, "reader.textSettings")}
            aria-expanded={panel}
            title={t(ui, "reader.textSettings")}
            onClick={openPanel}
            data-reader-action="aa"
          >
            <span aria-hidden="true" className="reader-aa-small">A</span>
            <span aria-hidden="true" className="reader-aa-big">A</span>
          </button>
        </div>
      </div>

      {/* «Аа» panel: language, text size, background. The page behind is dimmed
          black 60 % like the other windows (V27, Vraja Lila msg 5769–5779; V18);
          a tap on the dimming = a tap on the page (closes the panel). */}
      {panel && (
        <div
          ref={panelBackdropRef}
          className="reader-panel-backdrop"
          data-no-reader-tap=""
          aria-hidden="true"
          onClick={() => hide()}
        />
      )}
      {panel && (
        <div ref={panelNodeRef} className="reader-panel" role="group" aria-label={t(ui, "reader.textSettings")} {...barEvents}>
          <div className="reader-panel-head">
            <p className="reader-panel-title">{t(ui, "reader.textSettings")}</p>
            <button
              type="button"
              className="reader-panel-close"
              aria-label={t(ui, "reader.close")}
              onClick={() => {
                closePanel();
                arm();
              }}
            >
              <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          {/* The language first (V27, Vraja Lila msg 5769–5779: «он должен быть первой функцией»). */}
          <p className="reader-panel-label">{t(ui, "language.label")}</p>
          <LanguageSwitcher
            lang={lang}
            sectionId={sectionId}
            available={available}
            ui={ui}
            block
            onNavigate={fromPanelThen}
          />
          <p className="reader-panel-label">{t(ui, "reader.size")}</p>
          <div className="reader-size-row">
            <button
              type="button"
              className="reader-size-btn"
              aria-label={t(ui, "reader.smaller")}
              title={t(ui, "reader.smaller")}
              disabled={sizeIdx === 0}
              onClick={() => stepReaderSize(-1)}
              data-reader-size="-"
            >
              <span aria-hidden="true" style={{ fontSize: 14 }}>A</span>
              <span aria-hidden="true">−</span>
            </button>
            <span className="reader-size-value" aria-live="polite">
              {`${Math.round(size * 100)} %`}
              <span className="reader-size-dots" aria-hidden="true">
                {SIZES.map((s, i) => (
                  <span key={s} data-on={i <= sizeIdx ? "" : undefined} />
                ))}
              </span>
            </span>
            <button
              type="button"
              className="reader-size-btn"
              aria-label={t(ui, "reader.larger")}
              title={t(ui, "reader.larger")}
              disabled={sizeIdx === SIZES.length - 1}
              onClick={() => stepReaderSize(1)}
              data-reader-size="+"
            >
              <span aria-hidden="true" style={{ fontSize: 20 }}>A</span>
              <span aria-hidden="true">+</span>
            </button>
          </div>
          <p className="reader-panel-label">{t(ui, "reader.background")}</p>
          <div className="reader-theme-row">
            {THEMES.map((th) => (
              <button
                key={th}
                type="button"
                className="reader-theme-btn"
                aria-pressed={theme === th}
                onClick={() => setReaderTheme(th)}
                data-reader-theme-btn={th}
              >
                <span aria-hidden="true" className="reader-swatch" style={{ background: THEME_SWATCH[th] }} />
                <span>{t(ui, `reader.bg.${th}`)}</span>
              </button>
            ))}
          </div>
          <p className="reader-panel-label">{t(ui, "reader.layout")}</p>
          <div className="reader-theme-row" role="group" aria-label={t(ui, "reader.layout")}>
            {LAYOUTS.map((m) => (
              <button
                key={m}
                type="button"
                className="reader-theme-btn"
                aria-pressed={layout === m}
                onClick={() => chooseLayout(m)}
                data-reader-layout-btn={m}
              >
                <span>{t(ui, `reader.layout.${m}`)}</span>
              </button>
            ))}
          </div>
          {/* Verse panels open everywhere (Reader v7.8, Satkirti 07.10.2026: moved
              here from «Содержание»). The label and the switch act; nothing else. */}
          <div className="reader-switches">
            {(
              [
                ...(hasWbw ? [["wbw", "sidebar.showAllWbw", showAllWbw, setShowAllWbw]] : []),
                ["tr", "sidebar.showAllTranslations", showAllTranslations, setShowAllTranslations],
              ] as [string, string, boolean, (v: boolean) => void][]
            ).map(([id, key, on, set]) => (
                <button
                  key={id}
                  type="button"
                  role="switch"
                  aria-checked={on}
                  className="reader-switch"
                  data-reader-switch={id}
                  onClick={() => set(!on)}
                >
                  <span className="reader-switch-label">{t(ui, key)}</span>
                  <span aria-hidden="true" className="reader-switch-track" data-on={on ? "" : undefined}>
                    <span className="reader-switch-knob" />
                  </span>
                </button>
              ))}
          </div>
        </div>
      )}

      {/* Bottom bar: «‹ Назад» · «Вперёд ›» — the previous / next page of the contents (V17) */}
      <div className="reader-bar reader-bar-bottom" {...barEvents}>
        <div className="reader-bar-inner reader-nav-row">
          {prevPage && (
            <button
              type="button"
              className="reader-btn reader-history-btn"
              onClick={() => goChapter(prevPage)}
              data-reader-nav="back"
              data-chapter-target={prevPage}
            >
              <span aria-hidden="true" className="reader-history-arrow">‹</span>
              <span>{t(ui, "reader.back")}</span>
            </button>
          )}
          {nextPage && (
            <button
              type="button"
              className="reader-btn reader-history-btn"
              onClick={() => goChapter(nextPage)}
              data-reader-nav="forward"
              data-chapter-target={nextPage}
            >
              <span>{t(ui, "reader.forward")}</span>
              <span aria-hidden="true" className="reader-history-arrow">›</span>
            </button>
          )}
        </div>
      </div>

      {/* Faint status line while reading */}
      {!isHome && (
        <p className="reader-status" aria-hidden="true">
          {partTitle && <span className="reader-location-group">{`${partTitle}: `}</span>}
          <span>{chapterShort ? `${chapterShort} · ${pctText}` : pctText}</span>
        </p>
      )}

      {bmToast && (
        <div className="reader-toast" role="status" data-bookmark-toast="">
          <span>{t(ui, bmToast.added ? "bookmark.added" : "bookmark.removed")}</span>
          <span aria-hidden="true">{"\u00a0·"}</span>
          <button type="button" className="reader-toast-undo" onClick={undoBookmark}>
            {t(ui, "bookmark.undo")}
          </button>
        </div>
      )}

      {bmAsk && (
        <BookmarkNameDialog
          ui={ui}
          mode="add"
          initial={bmAsk.name}
          onConfirm={confirmBookmark}
          onCancel={() => setBmAsk(null)}
        />
      )}

      {hint && (
        <p className="reader-hint" role="status">
          {t(ui, finePointer ? "reader.hintMouse" : "reader.hintTouch")}
        </p>
      )}
    </div>
  );
}
