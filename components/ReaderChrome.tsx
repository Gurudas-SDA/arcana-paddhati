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
 * Bottom bar (Satkirti, 06.10.2026): no progress slider; «‹ Назад» and
 * «Вперёд ›» at the screen edges are the browser's Back / Forward — the same
 * step-by-step history — because iPhone / iPad have no system Back button
 * (on Android they duplicate it).
 *
 * The two buttons are never `disabled` (Reader v7, Satkirti on Android,
 * 06.10.2026): a tap on a disabled button is not handled by the page, and
 * Chrome on Android then treats it as a tap on the plain word «Вперёд» and
 * opens its own bar at the bottom of the screen (Google «Touch to Search» —
 * «строка, связанная с интернетом»). Without a step to go to, the button is
 * only dimmed and says so in a short note; the bars' texts are not
 * selectable (no word to look up).
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import { type TocPart, type TocSection } from "@/lib/book";
import { parsePath, t, type UiDict } from "@/lib/i18n";
import { main as mainEl, pushOverlay } from "@/lib/navHistory";
import { searchMarkOn } from "@/lib/searchMark";
import {
  setShowAllTranslations,
  setShowAllWbw,
  useShowAllTranslations,
  useShowAllWbw,
} from "@/lib/translationsPref";
import {
  SIZES,
  THEMES,
  setReaderTheme,
  stepReaderSize,
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
  "img:not(.hs-img):not(.portrait-img)", "svg:not(.hs-overlay):not(.portrait-ornament)",
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
/** Scroll back up by this much shows the bars ("a small scroll up"). */
const SHOW_ON_UP_PX = 48;
/** Scroll down by this much hides them. */
const HIDE_ON_DOWN_PX = 24;
/** The one-time hint stays this long. */
const HINT_MS = 6000;
const HINT_KEY = "ap.readerHintSeen";

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
  return !!document.querySelector(".hs-row[data-active], .hs-img-faded") || searchMarkOn();
}

/** A window of its own is open (contents/search drawer, «Настроение Гурудева»). */
function overlayOpen(): boolean {
  return !!document.querySelector(".mobile-menu, .mood-overlay");
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
  const [canBack, setCanBack] = useState(true);
  const [canForward, setCanForward] = useState(true);
  /** Short note when «Назад» / «Вперёд» has no step to go to. */
  const [navNote, setNavNote] = useState<string | null>(null);
  const navNoteTimer = useRef<number | undefined>(undefined);

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

  // A new page: reading mode again (render-time adjustment, no effect) —
  // unless "back" returned to a step of that page with the «Аа» panel open.
  const [lastPath, setLastPath] = useState(`${lang}/${sectionId ?? ""}`);
  const [popPanelKey, setPopPanelKey] = useState<string | null>(null);
  const pathKey = `${lang}/${sectionId ?? ""}`;
  if (pathKey !== lastPath) {
    setLastPath(pathKey);
    const keepPanel = popPanelKey === pathKey;
    setPopPanelKey(null);
    setShown(keepPanel);
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
  }, [shown, panel, menuOpen]);

  const clearTimer = () => window.clearTimeout(hideTimer.current);

  /** (Re)start the auto-hide countdown when nothing holds the bars open. */
  const arm = useCallback(() => {
    clearTimer();
    if (!shownRef.current || panelRef.current || menuRef.current || atEnd.current || hover.current) return;
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

  // ---- history Back / Forward availability ------------------------------------
  // Navigation API (Chrome / Edge / Android): exact. Elsewhere (Safari): Back
  // when the tab has history, Forward always (a no-op at the newest step).
  useEffect(() => {
    type Nav = EventTarget & { canGoBack?: boolean; canGoForward?: boolean };
    const nav = (window as unknown as { navigation?: Nav }).navigation;
    const update = () => {
      if (nav && typeof nav.canGoBack === "boolean") {
        setCanBack(nav.canGoBack);
        setCanForward(!!nav.canGoForward);
      } else {
        setCanBack(window.history.length > 1);
        setCanForward(true);
      }
    };
    const id = window.setTimeout(update, 0);
    nav?.addEventListener("currententrychange", update);
    window.addEventListener("popstate", update);
    return () => {
      window.clearTimeout(id);
      nav?.removeEventListener("currententrychange", update);
      window.removeEventListener("popstate", update);
    };
  }, [pathKey, shown, panel, menuOpen]);
  const section = sections.find((s) => s.id === sectionId);
  const part = parts.find((p) => p.id === sectionId);
  // «82 %» never breaks (Reader v7.1: on Android the «%» wrapped to a second line).
  const pctText = `${Math.round(pct)} %`;
  // Chapters with numbers (the Introduction group has none — Satkirti 06.10.2026):
  // there the status line names the chapter itself.
  const numbered = sections.filter((s) => s.num).length;
  const chapterShort = section?.num
    ? t(ui, "reader.chapter", { n: section.num })
    : part
      ? t(ui, "part.label", { n: part.numeral })
      : (section?.title ?? "");
  const chapterLong = section?.num
    ? t(ui, "reader.chapterOf", { n: section.num, total: String(numbered) })
    : chapterShort;

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
    let up = 0;
    let down = 0;
    let raf = 0;
    // The room after a chapter's end (.chapter-end-space) is not reading:
    // the chapter ends (100 %, the bars come up) where its text ends.
    const maxScroll = () => {
      const sp = m.querySelector<HTMLElement>(".chapter-end-space");
      return Math.max(0, m.scrollHeight - m.clientHeight - (sp ? sp.offsetHeight : 0));
    };
    const measure = () => {
      raf = 0;
      const max = maxScroll();
      setPct(max > 4 ? Math.min(100, Math.max(0, (m.scrollTop / max) * 100)) : 100);
    };
    measure();
    const onScroll = () => {
      lastScrollAt.current = performance.now();
      if (!raf) raf = requestAnimationFrame(measure);
      const top = m.scrollTop;
      const d = top - last;
      last = top;
      // Momentum after a swipe keeps counting for a while (no touchmove then).
      if (performance.now() < quietUntil.current || overlayOpen() || performance.now() - userAt > 1500) {
        up = down = 0;
        return;
      }
      const max = maxScroll();
      if (d > 0) {
        down += d;
        up = 0;
        if (max > 120 && top >= max - 2) {
          // End of the chapter: the bars come up.
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
        up -= d;
        down = 0;
        if (atEnd.current) {
          atEnd.current = false;
          arm();
        }
        if (up > SHOW_ON_UP_PX && !shownRef.current) {
          up = 0;
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
        const at = parsePath(window.location.pathname.replace(/^\/arcana-paddhati(?=\/|$)/, "") || "/");
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
  /** «‹ Назад» / «Вперёд ›»: one step through the browser history; no step
   *  there — a short note instead (never a dead tap, see the top comment). */
  const historyStep = (dir: "back" | "forward") => {
    arm();
    const can = dir === "back" ? canBack : canForward;
    const note = () => {
      window.clearTimeout(navNoteTimer.current);
      setNavNote(t(ui, dir === "back" ? "reader.noBack" : "reader.noForward"));
      navNoteTimer.current = window.setTimeout(() => setNavNote(null), 2500);
    };
    if (!can) {
      note();
      return;
    }
    setNavNote(null);
    // Without the Navigation API (Safari) "can" is a guess: if the step did
    // not happen (no popstate), say so instead of a silent tap.
    const exact = typeof (window as unknown as { navigation?: { canGoForward?: boolean } }).navigation
      ?.canGoForward === "boolean";
    if (!exact) {
      let moved = false;
      const onPop = () => {
        moved = true;
      };
      window.addEventListener("popstate", onPop, { once: true });
      window.setTimeout(() => {
        window.removeEventListener("popstate", onPop);
        if (!moved) note();
      }, 450);
    }
    if (dir === "back") window.history.back();
    else window.history.forward();
  };
  useEffect(() => () => window.clearTimeout(navNoteTimer.current), []);

  return (
    <div
      ref={barsRef}
      className="reader-chrome no-print"
      data-shown={shown ? "" : undefined}
      data-panel={panel ? "" : undefined}
      data-menu={menuOpen ? "" : undefined}
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
          <button
            type="button"
            className="reader-btn reader-aa ml-auto"
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

      {/* «Аа» panel: text size, background, language */}
      {panel && (
        <div className="reader-panel" role="group" aria-label={t(ui, "reader.textSettings")} {...barEvents}>
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
          <p className="reader-panel-label">{t(ui, "language.label")}</p>
          <LanguageSwitcher
            lang={lang}
            sectionId={sectionId}
            available={available}
            ui={ui}
            block
            onNavigate={fromPanelThen}
          />
        </div>
      )}

      {/* Bottom bar: «‹ Назад» · chapter · % · «Вперёд ›» (history steps) */}
      <div className="reader-bar reader-bar-bottom" {...barEvents}>
        <div className="reader-bar-inner reader-nav-row">
          <button
            type="button"
            className="reader-btn reader-history-btn"
            onClick={() => historyStep("back")}
            aria-disabled={!canBack}
            data-reader-nav="back"
          >
            <span aria-hidden="true" className="reader-history-arrow">‹</span>
            <span>{t(ui, "reader.back")}</span>
          </button>
          <p className="reader-progress-label">
            {isHome ? "" : chapterLong ? (
              <>
                <span className="rp-long">{`${chapterLong} · ${pctText}`}</span>
                {/* Narrow phones: «5/13 · 82 %» (one line, never cut) */}
                <span className="rp-short">
                  {section?.num ? `${section.num}/${numbered} · ${pctText}` : pctText}
                </span>
              </>
            ) : (
              pctText
            )}
          </p>
          <button
            type="button"
            className="reader-btn reader-history-btn"
            onClick={() => historyStep("forward")}
            aria-disabled={!canForward}
            data-reader-nav="forward"
          >
            <span>{t(ui, "reader.forward")}</span>
            <span aria-hidden="true" className="reader-history-arrow">›</span>
          </button>
        </div>
      </div>

      {/* Faint status line while reading */}
      {!isHome && (
        <p className="reader-status" aria-hidden="true">
          {chapterShort ? `${chapterShort} · ${pctText}` : pctText}
        </p>
      )}

      {navNote && shown && (
        <p className="reader-hint reader-nav-note" role="status" data-reader-nav-note="">
          {navNote}
        </p>
      )}

      {hint && (
        <p className="reader-hint" role="status">
          {t(ui, finePointer ? "reader.hintMouse" : "reader.hintTouch")}
        </p>
      )}
    </div>
  );
}
