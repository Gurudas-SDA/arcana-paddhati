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
 *   apDepth — how many menu entries are stacked (contents opened = 1, each
 *             part expanded in it = +1); closing the menu pops all of them
 *   apParts — the contents' open / closed parts on this menu entry
 *   apExp   — the part this menu entry expanded (collapsing it = "back")
 *   apAa    — the reader's «Аа» panel is open on this entry
 * Overlays (menu, «Аа», mood) push an entry with the same apKey: same place.
 *
 * Every step the reader takes PUSHES an entry, always inside the tap itself
 * (never "back, then push": Chrome on Android marks entries pushed without a
 * user gesture as skippable, and its Back button then jumps over them — it
 * threw the reader back to the cover). So Back retraces the steps one by one.
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
  delete rest.apDepth;
  delete rest.apParts;
  delete rest.apExp;
  delete rest.apAa;
  window.history.pushState(rest, "", url);
}

/** Open an overlay entry on top of the current place (same apKey). */
export function pushOverlay(extra: Record<string, unknown>) {
  placeKey();
  window.history.pushState({ ...(state() ?? {}), ...extra }, "");
}

/** Merge keys into the current entry (and drop the keys in `drop`). */
export function patchState(extra: Record<string, unknown>, drop: string[] = []) {
  const next: Record<string, unknown> = { ...(state() ?? {}), ...extra };
  for (const k of drop) delete next[k];
  window.history.replaceState(next, "");
}

/** Number of stacked menu entries on top of the place (0: menu not open). */
export function menuDepth(s: State = state()): number {
  if (s?.apMenu !== true) return 0;
  const d = s.apDepth;
  return typeof d === "number" && d >= 1 ? Math.floor(d) : 1;
}

export function isMenuEntry(s: State = state()): boolean {
  return s?.apMenu === true;
}
