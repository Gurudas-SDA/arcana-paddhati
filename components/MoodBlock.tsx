"use client";

import React, { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { MoodQuote, MoodSource } from "@/lib/book";

/** Localised labels of the mood block (data/ui.<lang>.json, keys mood.*). */
export interface MoodLabels {
  button: string;
  words: string;
  translation: string;
  machine: string;
  transcript: string;
  audio: string;
  /** Close control of the overlay (aria-label / tooltip of the ✕). */
  close: string;
}

const HEADING_FONT = { fontFamily: "var(--font-noto-serif, Georgia, serif)" };

/** Focusable elements inside the dialog (focus trap). */
const FOCUSABLE = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Place the (fixed) overlay over exactly the visible area. Without zoom this is
 * a no-op (the CSS `inset-0` / 100dvh box is right). With a pinch-zoomed page
 * the box gets the visual viewport's position, the size of the unzoomed screen
 * and a counter-scale, so it looks as if the page were not zoomed.
 */
function fitToVisualViewport(el: HTMLElement) {
  const vv = window.visualViewport;
  const zoomed =
    vv && (Math.abs(vv.scale - 1) > 0.01 || Math.abs(vv.offsetTop) > 0.5 || Math.abs(vv.offsetLeft) > 0.5);
  if (!vv || !zoomed) {
    for (const k of ["top", "left", "right", "bottom", "width", "height", "transform", "transformOrigin"] as const) {
      el.style[k] = "";
    }
    return;
  }
  const s = vv.scale;
  Object.assign(el.style, {
    top: `${vv.offsetTop}px`,
    left: `${vv.offsetLeft}px`,
    right: "auto",
    bottom: "auto",
    width: `${vv.width * s}px`,
    height: `${vv.height * s}px`,
    transform: `scale(${1 / s})`,
    transformOrigin: "0 0",
  });
}

/** One alternative quote, separated from the previous one by a dotted rule. */
function AltQuote({ m, labels }: { m: MoodQuote; labels: MoodLabels }) {
  return (
    <div className="mood-alt mt-4 border-t-2 border-dotted border-[#D4A843] pt-3">
      <QuoteBody
        quote={m.quote}
        translation={m.translation || undefined}
        machine={m.translation_note === "machine"}
        source={m.source}
        labels={labels}
      />
    </div>
  );
}

/** Paragraphs of a quote ("\n\n"-separated; "[…]" marks an omission). */
function Paragraphs({ text, className }: { text: string; className: string }) {
  return (
    <>
        {text.split("\n\n").map((para, i) => (
          <p key={i} className={`${className} ${para.trim() === "[…]" ? "text-[#8B6508] not-italic" : ""}`}>
            {para}
          </p>
        ))}
    </>
  );
}

/** Gurudev's words (EN), the translation and the source line with links (each link only when its URL is set;
 *  a private recording has none and carries a `note` instead). */
function QuoteBody({
  quote,
  translation,
  machine,
  source,
  labels,
}: {
  quote: string;
  translation?: string;
  machine?: boolean;
  source?: MoodSource;
  labels: MoodLabels;
}) {
  const sourceLine = source
    ? [source.title, source.date, source.nr ? `№ ${source.nr}` : "", source.timecode, source.note]
        .filter(Boolean)
        .join(" · ")
    : "";
  return (
    <>
      <p className="mood-label mb-1 text-[11px] font-semibold uppercase tracking-wider text-[#8B6508]">
        {labels.words}
      </p>
      <div lang="en" className="mood-quote space-y-3">
        <Paragraphs text={quote} className="text-[15px] leading-7 text-[#2C1810]" />
      </div>
      {translation && (
        <div className="mt-4 border-t border-[#E8DCC8] pt-3">
          <p className="mood-label mb-1 text-[11px] font-semibold uppercase tracking-wider text-[#8B6508]">
            {labels.translation}
            {machine && (
              <span className="ml-2 font-normal normal-case tracking-normal text-[#5C3D2E]/80">
                ({labels.machine})
              </span>
            )}
          </p>
          <div className="mood-translation translation space-y-3">
            <Paragraphs text={translation} className="text-[15px] leading-7" />
          </div>
        </div>
      )}
      {source && (
        <p className="mood-source mt-4 border-t border-[#E8DCC8] pt-2 text-[12px] leading-5 text-[#5C3D2E]">
          <span lang={source.lang || "en"}>{sourceLine}</span>
          {source.transcript_url && (
            <>
              {" · "}
              <a
                href={source.transcript_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#8B6508] underline decoration-[#D4A843] underline-offset-2 hover:text-[#B8860B]"
              >
                {labels.transcript}
              </a>
            </>
          )}
          {source.audio_url && (
            <>
              {" · "}
              <a
                href={source.audio_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#8B6508] underline decoration-[#D4A843] underline-offset-2 hover:text-[#B8860B]"
              >
                {labels.audio}
              </a>
            </>
          )}
        </p>
      )}
    </>
  );
}

/**
 * "Mood — Gurudev": verbatim quotes of Gurudev (English, his own words) on the
 * inner mood of the action described below them, with a translation and source.
 *
 * Screen: a button ("Gurudev's mood · N") opens ALL quotes at once in a focused
 * overlay — full screen on phones, a centred modal from 640px up. The overlay has
 * its own scroll container (overscroll-behavior: contain) and the page behind it
 * is locked (the .app-main scroller and, for iOS Safari, the body via
 * position: fixed with the saved scroll offset), so a fast flick stops at the
 * first / last quote. Close: the ✕ in the header (the only visible control, on
 * every device), plus Esc, a tap on the backdrop, or the browser / Android back
 * button (opening pushes a history entry; closing pops it). After closing, the
 * reader is back exactly where he was and focus returns to the button.
 *
 * The overlay covers the VISUAL viewport: if the reader has pinch-zoomed the
 * page (or iOS left the visual viewport offset after the keyboard), a plain
 * `fixed inset-0` box is laid out in the zoomed layout viewport and its ✕ ends
 * up off-screen. fitToVisualViewport() places it over exactly the visible area
 * and scales it back to normal size, so the ✕ is always in the top corner.
 *
 * Print: the chosen quote is always in the HTML (.mood-panel, hidden on screen,
 * shown by the print rule in globals.css); the other quotes are not printed
 * (the print/Kindle book has them in an appendix).
 */
export default function MoodBlock({
  quote,
  translation,
  machine,
  source,
  more,
  title,
  labels,
}: {
  quote: string;
  translation?: string;
  /** The translation is a machine translation (not the Academy's). */
  machine?: boolean;
  source?: MoodSource;
  /** The other quotes for this block (best first), shown after the chosen one. */
  more?: MoodQuote[];
  /** Title of the (sub)section (header of the overlay). */
  title: string;
  labels: MoodLabels;
}) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  /** A history entry was pushed for the open overlay (Back closes it). */
  const pushed = useRef(false);
  const titleId = useId();
  const dialogId = useId();
  const count = 1 + (more?.length ?? 0);

  const openOverlay = () => {
    try {
      // Same URL; Next.js' internal history state is kept (spread in), so its router treats it as its own entry.
      window.history.pushState({ ...(window.history.state ?? {}), moodOverlay: true }, "");
      pushed.current = true;
    } catch {
      pushed.current = false;
    }
    setOpen(true);
  };

  /** Close from the UI: pop our history entry (if any) and close. */
  const requestClose = useCallback(() => {
    if (pushed.current) {
      pushed.current = false;
      window.history.back();
    }
    setOpen(false);
  }, []);

  // Before paint: put the overlay over the visible area (see fitToVisualViewport);
  // again when the visible area moves or changes (pan, toolbar, rotation) but not when the
  // reader zooms inside the open overlay.
  useLayoutEffect(() => {
    if (!open || !overlayRef.current) return;
    const el = overlayRef.current;
    const vv = window.visualViewport;
    const scaleAtOpen = vv?.scale ?? 1;
    fitToVisualViewport(el);
    if (!vv) return;
    const onResize = () => {
      if (Math.abs(vv.scale - scaleAtOpen) < 0.01) fitToVisualViewport(el);
    };
    vv.addEventListener("resize", onResize);
    vv.addEventListener("scroll", onResize);
    return () => {
      vv.removeEventListener("resize", onResize);
      vv.removeEventListener("scroll", onResize);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const html = document.documentElement;
    const body = document.body;
    const main = document.querySelector<HTMLElement>(".app-main");
    const shell = document.querySelector<HTMLElement>(".app-shell");
    const mainTop = main?.scrollTop ?? 0;
    const winY = window.scrollY;
    const toggle = buttonRef.current;
    const prev = {
      main: main?.style.overflow ?? "",
      html: html.style.overflow,
      body: body.getAttribute("style"),
    };
    // Lock the page behind: the content scroller, the root and (iOS Safari) the body.
    if (main) main.style.overflow = "hidden";
    html.style.overflow = "hidden";
    Object.assign(body.style, {
      position: "fixed",
      top: `-${winY}px`,
      left: "0",
      right: "0",
      width: "100%",
      overflow: "hidden",
    });
    if (shell) shell.inert = true;
    closeRef.current?.focus({ preventScroll: true });

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        requestClose();
        return;
      }
      if (e.key !== "Tab" || !dialogRef.current) return;
      const items = Array.from(dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => el.getClientRects().length > 0,
      );
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement;
      if (e.shiftKey && (active === first || !dialogRef.current.contains(active))) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && (active === last || !dialogRef.current.contains(active))) {
        e.preventDefault();
        first.focus();
      }
    };
    const onPop = () => {
      pushed.current = false;
      setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    window.addEventListener("popstate", onPop);

    return () => {
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("popstate", onPop);
      if (shell) shell.inert = false;
      if (main) main.style.overflow = prev.main;
      html.style.overflow = prev.html;
      if (prev.body === null) body.removeAttribute("style");
      else body.setAttribute("style", prev.body);
      window.scrollTo(0, winY);
      // Back to exactly where the reader was (again after the router has handled popstate).
      const restore = () => {
        if (main && main.scrollTop !== mainTop) main.scrollTop = mainTop;
      };
      restore();
      requestAnimationFrame(restore);
      window.setTimeout(restore, 150);
      toggle?.focus({ preventScroll: true });
    };
  }, [open, requestClose]);

  const overlay = (
    <div ref={overlayRef} className="mood-overlay no-print fixed inset-0 z-[60] flex items-stretch justify-center sm:items-center sm:p-6">
      <div className="mood-backdrop absolute inset-0" onClick={requestClose} aria-hidden="true" />
      <div
        ref={dialogRef}
        id={dialogId}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="mood-dialog relative flex w-full flex-col bg-[#FDF8F0] shadow-xl sm:max-w-2xl sm:rounded-md sm:border sm:border-[#E8DCC8]"
      >
        <header className="mood-dialog-head flex shrink-0 items-center gap-3 border-b border-[#E8DCC8] bg-[#FDF8F0] px-4 py-2.5 sm:rounded-t-md sm:px-6">
          <div className="min-w-0 flex-1">
            <p className="mood-label text-[11px] font-semibold uppercase tracking-wider text-[#8B6508]">
              {labels.button}
              {count > 1 && <span className="font-normal">{` · ${count}`}</span>}
            </p>
            <h2
              id={titleId}
              className="truncate text-[16px] font-semibold leading-snug text-[#1a1a1a]"
              style={HEADING_FONT}
            >
              {title}
            </h2>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={requestClose}
            aria-label={labels.close}
            title={labels.close}
            className="mood-close -mr-1 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-[#8B6508] transition-colors hover:bg-[#F5E6C8]"
          >
            <svg
              aria-hidden="true"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.25"
              strokeLinecap="round"
            >
              <line x1="6" y1="6" x2="18" y2="18" />
              <line x1="18" y1="6" x2="6" y2="18" />
            </svg>
          </button>
        </header>
        <div className="mood-scroll min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-6 sm:py-5">
          <div className="rounded-sm border-l-2 border-[#B8860B] bg-white/60 px-4 py-3 sm:px-5">
            <QuoteBody quote={quote} translation={translation} machine={machine} source={source} labels={labels} />
            {more?.map((m, i) => <AltQuote key={i} m={m} labels={labels} />)}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="mood my-4">
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? dialogId : undefined}
        onClick={openOverlay}
        className={`mood-toggle inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[12px] leading-4 select-none transition-colors ${
          open
            ? "border-[#B8860B] bg-[#F5E6C8] text-[#8B6508] font-semibold"
            : "border-[#D4A843] bg-[#FDF8F0] text-[#8B6508] hover:border-[#B8860B] hover:bg-[#F5E6C8]"
        }`}
      >
        <svg
          aria-hidden="true"
          width="10"
          height="10"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="9 6 15 12 9 18" />
        </svg>
        {labels.button}
        {count > 1 && <span className="font-normal">{` · ${count}`}</span>}
      </button>
      {/* Print only: the chosen quote inline (hidden on screen, see .mood-panel in globals.css). */}
      <div className="mood-panel mt-2 rounded-sm border-l-2 border-[#B8860B] bg-[#FDF8F0] px-4 py-3 sm:px-5">
        <QuoteBody quote={quote} translation={translation} machine={machine} source={source} labels={labels} />
      </div>
      {open && createPortal(overlay, document.body)}
    </div>
  );
}
