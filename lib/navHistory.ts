"use client";

/**
 * Browser history model (UI rule 6: the phone's "back" returns to the previous
 * place). The page scrolls inside `.app-main`, not the window, so the browser
 * cannot restore the reading position by itself — we do it here.
 *
 * Our keys live next to Next.js' own keys in history.state (always spread in,
 * so its router keeps treating the entry as its own):
 *   apKey   — id of a reading place; its scroll offset is kept in `positions`
 *   apMenu  — the mobile menu (contents / search) is open on this entry
 *   apQuery — the search query shown in that menu when the reader left it
 * Overlays (menu, mood) push an entry with the same apKey: same place.
 */

export const MAIN_SELECTOR = ".app-main";
const SCROLL_STORE = "ap.scroll";
export const QUERY_STORE = "ap.searchQuery";

type State = Record<string, unknown> | null;

const state = (): State => (window.history.state as State) ?? null;

let positions: Record<string, number> | null = null;
function store(): Record<string, number> {
  if (positions) return positions;
  positions = {};
  try {
    const raw = sessionStorage.getItem(SCROLL_STORE);
    if (raw) positions = JSON.parse(raw) as Record<string, number>;
  } catch {
    // storage unavailable
  }
  return positions;
}
let persistTimer: number | undefined;
function persist() {
  window.clearTimeout(persistTimer);
  persistTimer = window.setTimeout(() => {
    try {
      const p = store();
      const keys = Object.keys(p);
      // Keep the store small: the last 200 places.
      for (const k of keys.slice(0, Math.max(0, keys.length - 200))) delete p[k];
      sessionStorage.setItem(SCROLL_STORE, JSON.stringify(p));
    } catch {
      // storage unavailable
    }
  }, 250);
}

/** Key of the current history entry (assigned once per entry). */
export function placeKey(): string {
  const s = state();
  const k = s?.apKey;
  if (typeof k === "string") return k;
  const key = Math.random().toString(36).slice(2, 10);
  window.history.replaceState({ ...(s ?? {}), apKey: key }, "");
  return key;
}

export function main(): HTMLElement | null {
  return document.querySelector<HTMLElement>(MAIN_SELECTOR);
}

/** Record the current scroll offset of the reading area for this entry. */
export function recordScroll() {
  const m = main();
  if (!m) return;
  store()[placeKey()] = m.scrollTop;
  persist();
}

/** Saved scroll offset of a history entry (undefined: never recorded). */
export function savedScroll(s: State): number | undefined {
  const k = s?.apKey;
  return typeof k === "string" ? store()[k] : undefined;
}

/**
 * A new reading place on the same page (anchor jump): a new entry with the
 * Next.js keys only — not the menu flag, not the previous place's key.
 */
export function pushPlace(url: string) {
  recordScroll();
  const rest = { ...(state() ?? {}) };
  delete rest.apKey;
  delete rest.apMenu;
  delete rest.apQuery;
  window.history.pushState(rest, "", url);
}

/** Open an overlay entry on top of the current place (same apKey). */
export function pushOverlay(extra: Record<string, unknown>) {
  placeKey();
  window.history.pushState({ ...(state() ?? {}), ...extra }, "");
}

/** Merge keys into the current entry. */
export function patchState(extra: Record<string, unknown>) {
  window.history.replaceState({ ...(state() ?? {}), ...extra }, "");
}

export function isMenuEntry(s: State = state()): boolean {
  return s?.apMenu === true;
}
