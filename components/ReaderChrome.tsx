"use client";

/**
 * Reading mode (Apple Books style; Satkirti's choice of 05.10.2026, variant Б).
 *
 * While reading only the text is on screen, with a faint line at the bottom
 * («Глава 8 · 35 %»). A tap / click on EMPTY space or plain text shows the
 * menu: the top bar «Содержание» · «Поиск» · «Аа» and the bottom bar (reading
 * progress slider of the chapter, previous / next chapter). Another tap hides
 * it. The bars also appear on a small scroll back up and at the end of a
 * chapter; they hide on scrolling down and after ~4 s without interaction
 * (never while the «Аа» panel or the contents are open).
 *
 * UI rule 1 (refined 05.10.2026): interactive elements (list rows ↔ picture,
 * links, buttons, verse chips, «Настроение Гурудева», pictures — the Deities
 * included) never toggle the menu; if something is highlighted, the first
 * tap on empty space only clears the highlight (components/Hotspots.tsx), the
 * next one toggles the menu. A tap that ends a text selection does nothing.
 *
 * The cover (05.10.2026, Satkirti on Android): a tap on ANY point of the
 * cover — the picture included — shows / hides the menu; only real controls
 * (links, buttons, the install banner's buttons) keep their own function.
 *
 * Back (UI rule 6): the «Аа» panel is a history entry; "back" to it opens it
 * again, so Back retraces every step (lib/navHistory.ts).
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import { tocLayout, type TocPart, type TocSection } from "@/lib/book";
import { localeHref, parsePath, t, type UiDict } from "@/lib/i18n";
import { main as mainEl, pushOverlay } from "@/lib/navHistory";
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
  "img", "svg", "picture", "video", "canvas",
  ".hs-text", ".hs-hit", ".hs-figure", ".hs-peek", ".hs-inert",
  ".mood-toggle", ".verse-chips", "[data-no-reader-tap]",
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
  return !!document.querySelector(".hs-row[data-active], .hs-img-faded");
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
  const size = useReaderSize();
  const router = useRouter();

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


  // ---- reading order: previous / next chapter -------------------------------
  const order = useMemo(() => {
    const partById = new Map(parts.map((p) => [p.id, p]));
    const ids: string[] = [];
    for (const item of tocLayout(sections.map((s) => s.id), parts)) {
      if (item.kind === "section") ids.push(item.id);
      else if (partById.get(item.id)?.sections.length === 0) ids.push(item.id);
    }
    return ids;
  }, [sections, parts]);
  const idx = sectionId ? order.indexOf(sectionId) : -1;
  const isHome = sectionId === null;
  const isHomeRef = useRef(isHome);
  useEffect(() => {
    isHomeRef.current = isHome;
  }, [isHome]);
  const prevId: string | null | undefined = idx > 0 ? order[idx - 1] : idx === 0 ? null : undefined; // null = cover
  const nextId: string | undefined = isHome ? order[0] : idx >= 0 ? order[idx + 1] : undefined;
  const section = sections.find((s) => s.id === sectionId);
  const part = parts.find((p) => p.id === sectionId);
  const pctText = `${Math.round(pct)} %`;
  const chapterShort = section?.num
    ? t(ui, "reader.chapter", { n: section.num })
    : part
      ? t(ui, "part.label", { n: part.numeral })
      : "";
  const chapterLong = section?.num
    ? t(ui, "reader.chapterOf", { n: section.num, total: String(sections.length) })
    : chapterShort;

  // ---- progress + scroll behaviour --------------------------------------------
  useEffect(() => {
    const m = mainEl();
    if (!m) return;
    quietUntil.current = performance.now() + 900;
    let last = m.scrollTop;
    let up = 0;
    let down = 0;
    let raf = 0;
    const measure = () => {
      raf = 0;
      const max = m.scrollHeight - m.clientHeight;
      setPct(max > 4 ? Math.min(100, Math.max(0, (m.scrollTop / max) * 100)) : 100);
    };
    measure();
    const onScroll = () => {
      lastScrollAt.current = performance.now();
      if (!raf) raf = requestAnimationFrame(measure);
      const top = m.scrollTop;
      const d = top - last;
      last = top;
      if (performance.now() < quietUntil.current || overlayOpen()) {
        up = down = 0;
        return;
      }
      const max = m.scrollHeight - m.clientHeight;
      if (d > 0) {
        down += d;
        up = 0;
        if (max > 120 && top >= max - 2) {
          // End of the chapter: the bars (with «next chapter») come up.
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

  const onSlide = (e: React.ChangeEvent<HTMLInputElement>) => {
    const m = mainEl();
    if (!m) return;
    quietUntil.current = performance.now() + 600;
    const v = Number(e.target.value);
    m.scrollTop = (v / 1000) * (m.scrollHeight - m.clientHeight);
    setPct(v / 10);
    arm();
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
  const chapterLink = (id: string | null, dir: "prev" | "next") => {
    const label = dir === "prev" ? t(ui, "reader.prev") : t(ui, "reader.next");
    const href = localeHref(lang, id);
    return (
      <Link
        href={href}
        onClick={(e) => {
          if (panelRef.current) {
            e.preventDefault();
            fromPanelThen(() => router.push(href));
          }
        }}
        className={`reader-btn reader-chapter-btn ${dir === "next" ? "ml-auto text-right" : ""}`}
        data-reader-nav={dir}
      >
        {dir === "prev" && <span aria-hidden="true">‹ </span>}
        {id === null ? t(ui, "reader.cover") : label}
        {dir === "next" && <span aria-hidden="true"> ›</span>}
      </Link>
    );
  };

  return (
    <div
      ref={barsRef}
      className="reader-chrome no-print"
      data-shown={shown ? "" : undefined}
      data-panel={panel ? "" : undefined}
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

      {/* Bottom bar: chapter progress slider, previous / next chapter */}
      <div className="reader-bar reader-bar-bottom" {...barEvents}>
        <div className="reader-bar-inner reader-bottom-inner">
          {!isHome && (
            <>
              <p className="reader-progress-label">
                {chapterLong ? `${chapterLong} · ${pctText}` : pctText}
              </p>
              <input
                type="range"
                min={0}
                max={1000}
                step={1}
                value={Math.round(pct * 10)}
                onChange={onSlide}
                aria-label={t(ui, "reader.progress")}
                aria-valuetext={pctText}
                className="reader-slider"
                style={{ "--reader-pct": `${pct}%` } as React.CSSProperties}
              />
            </>
          )}
          <div className="reader-nav-row">
            {prevId !== undefined && chapterLink(prevId, "prev")}
            {nextId !== undefined && chapterLink(nextId, "next")}
          </div>
        </div>
      </div>

      {/* Faint status line while reading */}
      {!isHome && (
        <p className="reader-status" aria-hidden="true">
          {chapterShort ? `${chapterShort} · ${pctText}` : pctText}
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
