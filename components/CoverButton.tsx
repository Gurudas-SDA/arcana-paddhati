"use client";

import type { ReactNode } from "react";

/** The cover was tapped: the reader chrome (components/ReaderChrome.tsx) fades to the first page after it. */
export const COVER_OPEN_EVENT = "ap:cover-open";

/**
 * V81 (Vraja Lila msg 7729): a tap on the cover opens the page after it (the «Эпиграф») with a fade. A real <button>
 * (not a bare element with a pointerup listener: on iOS a tap on a non-link element gives no click, and the mockup
 * worked only through pointerup). The picture inside keeps its alt text as the button's name. The Chaitanya Academy
 * logo drawn over the cover takes no taps (pointer-events: none), so a tap on it reaches this button too.
 */
export default function CoverButton({ children }: { children: ReactNode }) {
  return (
    <button type="button" className="home-cover-btn" onClick={() => window.dispatchEvent(new Event(COVER_OPEN_EVENT))}>
      {children}
    </button>
  );
}
