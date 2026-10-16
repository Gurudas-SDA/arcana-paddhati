/** A89: «Листать» / «Прокручивать» (Gurudas reading standard A3: pages by
 *  default MUST; a scroll option SHOULD — the mode is kept, switching keeps
 *  the position).
 *
 *  «Листать» (the default): every chapter is its own page.
 *  «Прокручивать»: the whole book in one scroll (Vraja Lila PR 2,
 *  components/ContinuousBook.tsx), exported once per language on its own
 *  route `/<lang>/book/` — the cover stays light. Chapter URLs never change:
 *  in the book the address follows the chapter being read.
 *
 *  Switching keeps the words at the top of the screen: the text block there
 *  (its index in the chapter and its distance from the top) is put back at
 *  the same place in the other export. */
import { stripBasePath } from "./basePath";
import { parsePath } from "./i18n";
import { BOOK_SEGMENT } from "./bookRoute";
import { main } from "./navHistory";
import { readingSection } from "./readingFlow";

export { BOOK_SEGMENT, bookHref } from "./bookRoute";

/** ContinuousBook announces its mount / unmount (AppShell follows it). */
export const BOOK_EVENT = "ap:book";

const BLOCKS = "article :is(h1,h2,h3,h4,p)";
const STORE = "ap.pendingPlace";

export interface Place {
  sectionId: string;
  index: number;
  delta: number;
}

let pending: Place | null = null;

/** The text block at the top of the reading area of the chapter being read. */
export function capturePlace(): Place | null {
  const scroller = main();
  const root = readingSection();
  const { sectionId } = parsePath(stripBasePath(window.location.pathname) || "/");
  if (!scroller || !root || !sectionId || sectionId === BOOK_SEGMENT) return null;
  const top = scroller.getBoundingClientRect().top;
  const blocks = [...root.querySelectorAll<HTMLElement>(BLOCKS)];
  for (let i = 0; i < blocks.length; i++) {
    const r = blocks[i].getBoundingClientRect();
    if (!r.height || r.bottom <= top + 4) continue;
    return { sectionId, index: i, delta: r.top - top };
  }
  return null;
}

/** Keep `place` for the next export of its chapter (also across a reload). */
export function keepPlace(place: Place | null) {
  pending = place;
  try {
    if (place) sessionStorage.setItem(STORE, JSON.stringify(place));
    else sessionStorage.removeItem(STORE);
  } catch {
    // storage unavailable: kept in memory
  }
}

function takePending(): Place | null {
  if (!pending) {
    try {
      const raw = sessionStorage.getItem(STORE);
      const v: unknown = raw ? JSON.parse(raw) : null;
      if (v && typeof v === "object" && typeof (v as Place).sectionId === "string") pending = v as Place;
    } catch {
      // storage unavailable
    }
  }
  return pending;
}

/** Put a kept place back once its chapter is shown (pictures may still move
 *  the text: re-applied for a while, until the reader touches the page).
 *  Returns a cancel function, or null when there is nothing to put back. */
export function restorePlace(): (() => void) | null {
  const place = takePending();
  if (!place) return null;
  const { sectionId } = parsePath(stripBasePath(window.location.pathname) || "/");
  if (sectionId !== place.sectionId) return null;
  keepPlace(null);
  let stopped = false;
  const stop = () => { stopped = true; };
  const events = ["touchstart", "wheel", "keydown", "pointerdown"] as const;
  for (const ev of events) window.addEventListener(ev, stop, { passive: true, capture: true });
  const apply = () => {
    if (stopped) return;
    const scroller = main();
    const root = readingSection();
    const block = root?.querySelectorAll<HTMLElement>(BLOCKS)[place.index];
    if (!scroller || !block) return;
    const now = block.getBoundingClientRect().top - scroller.getBoundingClientRect().top;
    scroller.scrollTop += now - place.delta;
  };
  apply();
  requestAnimationFrame(apply);
  const timers = [80, 200, 400, 700, 1100, 1600].map((ms) => window.setTimeout(apply, ms));
  const end = window.setTimeout(() => {
    for (const ev of events) window.removeEventListener(ev, stop, { capture: true });
  }, 1700);
  return () => {
    timers.forEach((t) => window.clearTimeout(t));
    window.clearTimeout(end);
    for (const ev of events) window.removeEventListener(ev, stop, { capture: true });
  };
}
