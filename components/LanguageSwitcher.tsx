"use client";

import React, { useCallback, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { exitGhost } from "@/lib/exitGhost";
import { useRouter } from "next/navigation";
import {
  LANG_STORAGE_KEY,
  OFFERED_LANGUAGES,
  localeHref,
  t,
  type UiDict,
} from "@/lib/i18n";

/**
 * Language menu in the book's style (Vraja Lila msg 5418, variant 1; dimmed
 * page behind the list — msg 5423). A field «🌐 Русский ⌄» like the other «Аа»
 * buttons; a tap opens a card by the field with all languages (ARIA listbox),
 * the current one on a cream base with a gold ✓. A tap on the dimmed page,
 * Esc or a choice closes it; the focus returns to the field.
 *
 * Switching itself is unchanged: it keeps the current section (and subsection
 * anchor); the choice is remembered in localStorage, but the URL always
 * decides which language is shown.
 */
type Place = { left: number; width: number; top: number; maxHeight: number };

const GAP = 8;
/** .lang-option min-height (48) × rows + card padding (2 × 6) + border (2). */
const cardHeight = (rows: number) => rows * 48 + 14;

function placeBy(el: HTMLElement, rows: number): Place {
  const r = el.getBoundingClientRect();
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const width = Math.min(Math.max(r.width, 240), vw - 2 * GAP);
  const left = Math.min(Math.max(r.left, GAP), vw - width - GAP);
  const maxHeight = vh - 2 * GAP;
  const h = Math.min(cardHeight(rows), maxHeight);
  // Low field (the usual place, bottom of the «Аа» panel): the card ends at
  // the field's bottom edge and grows upwards; a high field: it starts at the
  // field's top. Either way it stays on screen (moved, never cut), and a
  // screen too low for all rows (phone turned) scrolls the list.
  const want = r.bottom >= vh / 2 ? r.bottom - h : r.top;
  const top = Math.min(Math.max(want, GAP), vh - h - GAP);
  return { left, width, top: Math.max(top, GAP), maxHeight };
}

export default function LanguageSwitcher({
  lang,
  sectionId,
  available,
  ui,
  block = false,
  onNavigate,
}: {
  lang: string;
  sectionId: string | null;
  /** Languages whose translated text exists; others are marked. */
  available: string[];
  ui: UiDict;
  /** Full-width variant (own row in the «Аа» panel / desktop sidebar). */
  block?: boolean;
  /** Runs the navigation (e.g. after closing the «Аа» panel's history entry). */
  onNavigate?: (go: () => void) => void;
}) {
  const router = useRouter();
  const uid = useId();
  const listId = `${uid}-list`;
  const labelId = `${uid}-label`;
  const optId = (code: string) => `${uid}-opt-${code}`;
  const triggerRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  // The list and its dimming close the way they opened, backwards (lib/exitGhost.ts, Vraja Lila msg 5521).
  const setListRef = useCallback((node: HTMLUListElement | null) => {
    listRef.current = node;
    if (!node) return;
    return () => {
      listRef.current = null;
      exitGhost(node, "lang-card lang-card-out", 140);
    };
  }, []);
  const backdropRef = useCallback((node: HTMLDivElement | null) => {
    if (!node) return;
    return () => exitGhost(node, "lang-backdrop lang-backdrop-out", 140);
  }, []);
  const [place, setPlace] = useState<Place | null>(null);
  const open = place !== null;
  const curIndex = Math.max(0, OFFERED_LANGUAGES.findIndex((l) => l.code === lang));
  const [active, setActive] = useState(curIndex);

  const label = (code: string, name: string) =>
    available.includes(code) ? name : `${name} ${t(ui, "language.fallbackSuffix")}`;
  const current = OFFERED_LANGUAGES[curIndex];

  const openList = useCallback(() => {
    if (!triggerRef.current) return;
    setActive(curIndex);
    setPlace(placeBy(triggerRef.current, OFFERED_LANGUAGES.length));
  }, [curIndex]);

  const closeList = useCallback(() => {
    setPlace(null);
    triggerRef.current?.focus({ preventScroll: true });
  }, []);

  const choose = (next: string) => {
    setPlace(null);
    if (next === lang) {
      triggerRef.current?.focus({ preventScroll: true });
      return;
    }
    try {
      localStorage.setItem(LANG_STORAGE_KEY, next);
    } catch {
      // storage unavailable — the URL still carries the language
    }
    const href = localeHref(next, sectionId) + (sectionId ? window.location.hash : "");
    if (onNavigate) onNavigate(() => router.push(href));
    else router.push(href);
  };

  // The list is open: one dimming only — the «Аа» panel's steps aside (V27b, app/globals.css).
  useEffect(() => {
    if (!open) return;
    const root = document.documentElement;
    root.setAttribute("data-lang-open", "");
    return () => root.removeAttribute("data-lang-open");
  }, [open]);

  // Focus the list when it opens; the current language in view.
  useEffect(() => {
    if (!open) return;
    const l = listRef.current;
    if (!l) return;
    l.focus({ preventScroll: true });
    const cur = l.querySelector<HTMLElement>('[aria-selected="true"]');
    if (cur) {
      const top = cur.offsetTop - (l.clientHeight - cur.offsetHeight) / 2;
      l.scrollTop = Math.max(0, top);
    }
  }, [open]);

  // Keep the active row visible while moving with the arrows.
  useEffect(() => {
    if (!open) return;
    const el = listRef.current?.children[active] as HTMLElement | undefined;
    el?.scrollIntoView?.({ block: "nearest" });
  }, [active, open]);

  // The screen turns / resizes: the field moves, the card follows it.
  useEffect(() => {
    if (!open) return;
    const re = () => triggerRef.current && setPlace(placeBy(triggerRef.current, OFFERED_LANGUAGES.length));
    window.addEventListener("resize", re);
    window.visualViewport?.addEventListener("resize", re);
    return () => {
      window.removeEventListener("resize", re);
      window.visualViewport?.removeEventListener("resize", re);
    };
  }, [open]);

  const onListKey = (e: React.KeyboardEvent) => {
    const n = OFFERED_LANGUAGES.length;
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setActive((i) => Math.min(n - 1, i + 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setActive((i) => Math.max(0, i - 1));
        break;
      case "Home":
        e.preventDefault();
        setActive(0);
        break;
      case "End":
        e.preventDefault();
        setActive(n - 1);
        break;
      case "Enter":
      case " ":
        e.preventDefault();
        choose(OFFERED_LANGUAGES[active].code);
        break;
      case "Escape":
        // Only the list closes — the «Аа» panel stays (its Esc handler skips
        // a prevented event).
        e.preventDefault();
        e.stopPropagation();
        closeList();
        break;
      case "Tab":
        e.preventDefault();
        closeList();
        break;
    }
  };

  const onTriggerKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      openList();
    }
  };

  return (
    <div className={`lang-field-wrap ${block ? "flex w-full" : "inline-flex"}`}>
      <span id={labelId} className="sr-only">
        {t(ui, "language.label")}
      </span>
      <button
        ref={triggerRef}
        type="button"
        className={`lang-field ${block ? "w-full" : ""}`}
        data-lang-trigger=""
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        aria-labelledby={`${labelId} ${uid}-value`}
        title={t(ui, "language.label")}
        onClick={() => (open ? closeList() : openList())}
        onKeyDown={onTriggerKey}
      >
        <svg
          className="lang-field-globe"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="2" y1="12" x2="22" y2="12" />
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
        </svg>
        <span id={`${uid}-value`} className="lang-field-value" lang={current?.htmlLang}>
          {current ? label(current.code, current.name) : lang}
        </span>
        <svg
          className="lang-field-chevron"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      {open &&
        place &&
        createPortal(
          <>
            <div
              ref={backdropRef}
              className="lang-backdrop"
              data-lang-backdrop=""
              data-no-reader-tap=""
              aria-hidden="true"
              onClick={closeList}
            />
            <ul
              ref={setListRef}
              id={listId}
              role="listbox"
              tabIndex={-1}
              aria-labelledby={labelId}
              aria-activedescendant={optId(OFFERED_LANGUAGES[active].code)}
              className="lang-card"
              data-no-reader-tap=""
              style={{
                left: place.left,
                width: place.width,
                top: place.top,
                maxHeight: place.maxHeight,
              }}
              onKeyDown={onListKey}
            >
              {OFFERED_LANGUAGES.map((l, i) => {
                const sel = l.code === lang;
                return (
                  <li
                    key={l.code}
                    id={optId(l.code)}
                    role="option"
                    aria-selected={sel}
                    data-lang={l.code}
                    data-active={i === active ? "" : undefined}
                    lang={l.htmlLang}
                    className="lang-option"
                    onClick={() => choose(l.code)}
                    onPointerMove={(e) => e.pointerType === "mouse" && setActive(i)}
                  >
                    <span className="lang-option-name">{label(l.code, l.name)}</span>
                    {sel && (
                      <span className="lang-option-check" data-lang-check="" aria-hidden="true">
                        ✓
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          </>,
          document.body,
        )}
    </div>
  );
}
