/** Navigation within the continuous book. URLs and anchors stay unchanged;
 *  manual scrolling replaces the current place, explicit links push one. */
import { BASE_PATH, stripBasePath } from "./basePath";
import { localeHref, parsePath } from "./i18n";
import { main, recordScroll } from "./navHistory";

interface Arrival {
  href: string;
  state: Record<string, unknown>;
  scroll?: number;
}

let arrival: Arrival | null = null;

/** Only our metadata is passed to the native History API. Next.js supplies
 *  its own router keys and updates usePathname through its documented API. */
export function readingState(): Record<string, unknown> {
  return Object.fromEntries(Object.entries(window.history.state ?? {}).filter(([key]) => key.startsWith("ap")));
}

export function beginReadingArrival(href: string, scroll?: number) {
  if (arrival) return false;
  arrival = { href, state: readingState(), scroll };
  return true;
}

export function finishReadingArrival() {
  const pending = arrival;
  arrival = null;
  return pending;
}

export function bookTarget(sectionId: string | null, anchor?: string): HTMLElement | null {
  const book = document.querySelector<HTMLElement>("[data-continuous-book]");
  if (!book) return null;
  const section = book.querySelector<HTMLElement>(`[data-book-section="${CSS.escape(sectionId ?? "")}"]`);
  if (!section) return null;
  return anchor ? section.querySelector<HTMLElement>(`[id="${CSS.escape(anchor)}"]`) : section;
}

/** Content of the current reading place. .app-main remains the scroller;
 *  it is not a chapter selector in the continuous book. */
export function readingSection(): HTMLElement | null {
  const scroller = main();
  if (!scroller?.querySelector('[data-continuous-book]')) return scroller;
  const place = parsePath(stripBasePath(window.location.pathname) || '/');
  return bookTarget(place.sectionId);
}

export function readingAnchor(id: string): HTMLElement | null {
  return readingSection()?.querySelector<HTMLElement>(`[id="${CSS.escape(id)}"]`) ?? null;
}

export function bookOffset(target: HTMLElement): number {
  const scroller = main();
  if (!scroller) return 0;
  const margin = parseFloat(getComputedStyle(target).scrollMarginTop) || 0;
  return Math.max(0, scroller.scrollTop + target.getBoundingClientRect().top - scroller.getBoundingClientRect().top - margin);
}

/** Returns false on a standalone page or a link outside this language's book. */
export function followBookLink(href: string, before?: (moved: boolean) => void): boolean {
  const url = new URL(href, window.location.href);
  if (url.origin !== window.location.origin || !url.pathname.startsWith(BASE_PATH + "/")) return false;
  const to = parsePath(stripBasePath(url.pathname) || "/");
  const book = document.querySelector<HTMLElement>("[data-continuous-book]");
  if (!book || book.dataset.bookLang !== to.lang) return false;
  let anchor: string | undefined;
  try { anchor = decodeURIComponent(url.hash.slice(1)) || undefined; } catch { return false; }
  const target = bookTarget(to.sectionId, anchor);
  const scroller = main();
  if (!target || !scroller) return false;
  const offset = bookOffset(target);
  const from = parsePath(stripBasePath(window.location.pathname) || "/");
  const changedPage = from.sectionId !== to.sectionId;
  const moved = window.location.pathname !== url.pathname || window.location.hash !== url.hash || Math.abs(scroller.scrollTop - offset) > 8;
  before?.(moved);
  if (moved) {
    recordScroll();
    const state: Record<string, unknown> = changedPage ? {} : readingState();
    for (const key of ["apKey", "apMenu", "apQuery", "apDepth", "apParts", "apExp", "apAa", "apNav"]) delete state[key];
    window.history.pushState({ ...state, apBook: true }, "", url.pathname + url.search + url.hash);
  }
  scroller.scrollTop = offset;
  window.dispatchEvent(new HashChangeEvent("hashchange"));
  return true;
}

export function readingHref(lang: string, sectionId: string | null): string {
  return `${BASE_PATH}${localeHref(lang, sectionId)}`;
}
