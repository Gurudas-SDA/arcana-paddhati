"use client";

/**
 * Browser history model (UI rule 6: the phone's "back" returns to the previous
 * place). The page scrolls inside `.app-main`, not the window, so the browser
 * cannot restore the reading position by itself — we do it here.
 *
 * This module is the ONLY writer of window.history (Phase 3: WebKit allows
 * 100 pushState/replaceState calls per 10 s; beyond that it throws and the
 * contents stop opening rows). Rules:
 *   - a real action (navigation, expand, collapse, opening an overlay) is
 *     exactly ONE write: the push (or replace) carries the entry's final state;
 *   - highlighting, the list's scroll offset, the query, the followed result
 *     and the reading position are NEVER written to history: they live in the
 *     entry's record (below), keyed by its `apId`.
 *
 * history.state keeps what an entry IS (always spread in, next to Next.js'
 * own keys, so its router keeps treating the entry as its own):
 *   apId    — unique id of this history entry (monotonic counter + random
 *             suffix; never reused, also not after "back" and a new step)
 *   apKey   — id of the reading place; overlays share their place's key
 *   apMenu  — the mobile menu (contents / search) is open on this entry
 *   apDepth — how many menu entries are stacked (contents opened = 1, each
 *             part expanded in it = +1); closing the menu pops all of them
 *   apAa    — the reader's «Аа» panel is open on this entry
 *   apBook  — the entry belongs to the continuous book
 *   moodOverlay — the «Настроение» window is open on this entry
 *
 * The entry's record (one per apId, in memory and in sessionStorage, last
 * 200 entries, evicted as a whole) keeps how the entry LOOKED:
 *   scroll  — the reading area's offset (shared by entries with the same apKey:
 *             the latest one wins, as an overlay sits on its place)
 *   view    — apLit (highlighted row), apNav (list scroll), apResult (the
 *             search result followed), apQuery, apParts (open lists), apExp
 * Entries from before this model (no apId) keep their view keys in
 * history.state and their offset in the old "ap.scroll" store: both are read,
 * never written. Without storage, or past the 200 entries, a step still
 * opens with the right URL, place and menu; only the highlight, the open
 * lists and the list's offset fall back to the default view.
 *
 * Every step the reader takes PUSHES an entry, always inside the tap itself
 * (never "back, then push": Chrome on Android marks entries pushed without a
 * user gesture as skippable, and its Back button then jumps over them — it
 * threw the reader back to the cover). So Back retraces the steps one by one.
 * A push that fails (WebKit's quota) is therefore never retried later: the
 * action still happens, it only has no step of its own. A replace that fails
 * is retried for the same entry only, so a retry can never add a step.
 */

export const MAIN_SELECTOR = ".app-main";
export const QUERY_STORE = "ap.searchQuery";
const ENTRY_STORE = "ap.entries";
const SEQ_STORE = "ap.entrySeq";
/** Read-only: reading offsets of entries made before apId (by apKey). */
const LEGACY_SCROLL_STORE = "ap.scroll";
const MAX_ENTRIES = 200;

/** Keys of how an entry looked: kept in its record, never in history.state. */
export const VIEW_KEYS = ["apLit", "apNav", "apResult", "apQuery", "apParts", "apExp"];

type State = Record<string, unknown> | null;
type Data = Record<string, unknown>;
interface EntryRecord {
  /** apKey of the entry (its reading place). */
  key?: string;
  scroll?: number;
  /** Order of the last scroll record (the latest of a place wins). */
  at?: number;
  /** View keys; null = dropped (hides an older value in history.state). */
  view?: Data;
}
/** Why a write happens. Only "action" writes are bound to the reader's taps. */
export type WriteReason = "action" | "load" | "scroll" | "identity" | "retry";

const state = (): State => (window.history.state as State) ?? null;
const isString = (v: unknown): v is string => typeof v === "string";

// ---- entry records -----------------------------------------------------------

let records: Map<string, EntryRecord> | null = null;
let clock = 0;
function store(): Map<string, EntryRecord> {
  if (records) return records;
  records = new Map();
  try {
    const raw = sessionStorage.getItem(ENTRY_STORE);
    const list: unknown = raw ? JSON.parse(raw) : null;
    if (Array.isArray(list)) {
      for (const item of list) {
        if (!Array.isArray(item) || !isString(item[0]) || !item[1] || typeof item[1] !== "object") continue;
        const rec = item[1] as EntryRecord;
        records.set(item[0], rec);
        if (typeof rec.at === "number" && rec.at > clock) clock = rec.at;
      }
    }
  } catch {
    // storage unavailable or unreadable: start empty (memory only)
  }
  return records;
}

let persistTimer: number | undefined;
let flushing = false;
function flush() {
  window.clearTimeout(persistTimer);
  persistTimer = undefined;
  try {
    sessionStorage.setItem(ENTRY_STORE, JSON.stringify([...store()]));
  } catch {
    // storage unavailable or full: the records stay in memory
  }
}
function persist() {
  if (!flushing) {
    flushing = true;
    // A reload or leaving the page right after a step keeps that step's record.
    window.addEventListener("pagehide", () => {
      if (persistTimer !== undefined) flush();
    });
  }
  window.clearTimeout(persistTimer);
  persistTimer = window.setTimeout(flush, 250);
}

/** The record of entry `id`, moved to the newest place; the oldest beyond
 *  MAX_ENTRIES is evicted whole (scroll and view together). */
function touch(id: string): EntryRecord {
  const m = store();
  const rec = m.get(id) ?? {};
  m.delete(id);
  m.set(id, rec);
  while (m.size > MAX_ENTRIES) {
    const oldest = m.keys().next().value;
    if (oldest === undefined) break;
    m.delete(oldest);
  }
  persist();
  return rec;
}

let seq = -1;
/** A new entry id: never reused (counter survives reloads in sessionStorage;
 *  the random suffix keeps ids apart even when storage is unavailable). */
function newId(): string {
  if (seq < 0) {
    seq = 0;
    try {
      seq = parseInt(sessionStorage.getItem(SEQ_STORE) ?? "0", 36) || 0;
    } catch {
      // storage unavailable: the suffix keeps ids unique
    }
  }
  let id: string;
  do {
    seq += 1;
    id = `${seq.toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  } while (store().has(id));
  try {
    sessionStorage.setItem(SEQ_STORE, seq.toString(36));
  } catch {
    // storage unavailable
  }
  return id;
}
const newKey = () => Math.random().toString(36).slice(2, 10);

// ---- identity of entries we did not create (Next.js router, older entries) ----

/** apId / apKey assigned to the current entry but not yet in history.state. */
let pendingIdentity: { apId: string; apKey: string } | null = null;
let identityTimer: number | undefined;
let listening = false;
function listen() {
  if (listening) return;
  listening = true;
  // A step to another entry: an identity meant for the one left is void.
  window.addEventListener("popstate", () => {
    pendingIdentity = null;
    window.clearTimeout(identityTimer);
  });
}

/** apId and apKey of the current entry. An entry made by Next.js' router (or
 *  before this model) gets them once, folded into the next write on it, or
 *  in one deferred write of its own. */
function identity(): { apId: string; apKey: string } {
  const s = state();
  if (isString(s?.apId) && isString(s?.apKey)) return { apId: s.apId, apKey: s.apKey };
  if (!pendingIdentity) {
    listen();
    pendingIdentity = { apId: isString(s?.apId) ? s.apId : newId(), apKey: isString(s?.apKey) ? s.apKey : newKey() };
    const mine = pendingIdentity;
    window.clearTimeout(identityTimer);
    identityTimer = window.setTimeout(() => {
      if (pendingIdentity !== mine) return;
      replaceEntry(() => ({ ...(state() ?? {}) }), undefined, "identity");
    }, 0);
  }
  return pendingIdentity;
}

/** Id of the current entry (assigned if it has none yet). */
export function entryId(): string {
  return identity().apId;
}

/** Key of the current entry's reading place. */
export function placeKey(): string {
  return identity().apKey;
}

// ---- the writer ----------------------------------------------------------------

const DEV = process.env.NODE_ENV !== "production";
interface DevCounter {
  inputs: number;
  writes: Record<WriteReason, number>;
  failed: number;
}
let dev: DevCounter | null = null;
/** Development build only: count the reader's inputs and every history write;
 *  an "action" write beyond the number of inputs is a regression (Phase 3:
 *  writes never exceed actions). Exposed as window.__apHistory. */
function devCount(reason: WriteReason) {
  if (!DEV) return;
  if (!dev) {
    dev = { inputs: 0, writes: { action: 0, load: 0, scroll: 0, identity: 0, retry: 0 }, failed: 0 };
    const counter = dev;
    (window as unknown as { __apHistory: DevCounter }).__apHistory = counter;
    const input = () => {
      counter.inputs += 1;
    };
    window.addEventListener("click", input, true);
    window.addEventListener(
      "keydown",
      (e) => {
        if (e.key === "Enter" || e.key === " " || e.key === "Escape") input();
      },
      true,
    );
  }
  dev.writes[reason] += 1;
  if (reason === "action" && dev.writes.action > dev.inputs) {
    const message = `[navHistory] ${dev.writes.action} action writes for ${dev.inputs} inputs: history writes exceed actions`;
    console.error(message);
    // Surfaces in the development overlay without breaking the action itself.
    window.setTimeout(() => {
      throw new Error(message);
    }, 0);
  }
}

let retry: { id: string | undefined; build: () => Data; url?: string; tries: number } | null = null;
let retryTimer: number | undefined;
function scheduleRetry() {
  window.clearTimeout(retryTimer);
  retryTimer = window.setTimeout(() => {
    const r = retry;
    retry = null;
    // Only for the same entry: the reader has gone on - nothing to repeat.
    if (!r || state()?.apId !== r.id) return;
    write("replace", r.build(), r.url, "retry", r);
  }, 1000);
}

/** True while write() calls the history (guardRouterPushes leaves its errors to it). */
let writing = false;
/** The one place that calls pushState / replaceState. False if it failed. */
function write(kind: "push" | "replace", data: Data, url: string | undefined, reason: WriteReason,
  again?: { build: () => Data; tries: number }): boolean {
  devCount(reason);
  try {
    writing = true;
    try {
      if (kind === "push") window.history.pushState(data, "", url);
      else window.history.replaceState(data, "", url);
    } finally {
      writing = false;
    }
    if (kind === "push") {
      // Another entry now: a retry or an identity meant for the one left is void.
      retry = null;
      pendingIdentity = null;
      window.clearTimeout(identityTimer);
    } else if (pendingIdentity && pendingIdentity.apId === data.apId) {
      pendingIdentity = null;
      window.clearTimeout(identityTimer);
    }
    return true;
  } catch (error) {
    if (dev) dev.failed += 1;
    const quota = error instanceof Error && error.name === "SecurityError";
    // WebKit's quota: a failed replace is repeated for the same entry once the
    // window allows (never a push: see the header). Other errors: give up.
    if (quota && kind === "replace" && again && again.tries < 12) {
      retry = { id: isString(data.apId) ? data.apId : undefined, build: again.build, url, tries: again.tries + 1 };
      scheduleRetry();
    }
    return false;
  }
}

let routerGuard = false;
/**
 * Chapter by chapter (no continuous book) opening a chapter is Next.js's own
 * router.push, whose pushState is not ours: when WebKit refuses it (its quota)
 * the error went uncaught - a page error, the menu gone. Same rule as for our
 * own pushes (see the header): the action still happens (the chapter is
 * shown), it only has no step of its own - the current entry takes the
 * chapter's URL with a replace (if that is refused too, it keeps its URL).
 * Our own write() sees its errors as before. Installed once, before the push.
 */
export function guardRouterPushes() {
  if (routerGuard || typeof window === "undefined") return;
  routerGuard = true;
  const push = window.history.pushState;
  // A method of an object: its name stays in a stack trace after minifying -
  // the guard only forwards, so it is not the writer (QA s35 tells them apart).
  const guard = {
    apRouterPushGuard(this: History, ...args: Parameters<History["pushState"]>) {
      try {
        return push.apply(this, args);
      } catch (error) {
        if (writing || !(error instanceof Error && error.name === "SecurityError")) throw error;
        if (dev) dev.failed += 1;
        try {
          window.history.replaceState(...args);
        } catch {
          // refused too: the chapter is shown, the entry keeps its URL
        }
      }
    },
  };
  window.history.pushState = guard.apRouterPushGuard as History["pushState"];
}

/** Replace the current entry with `build()` (recomputed on a retry). */
export function replaceEntry(build: () => Data, url?: string, reason: WriteReason = "action"): boolean {
  const make = () => {
    const data = { ...build() };
    const legacy: Data = {};
    for (const k of VIEW_KEYS) {
      if (k in data) legacy[k] = data[k];
      delete data[k];
    }
    if (!isString(data.apId)) {
      // The same entry keeps (or now gets) its identity in this one write.
      const own = identity();
      Object.assign(data, isString(data.apKey) ? { apId: own.apId } : own);
    }
    // An entry from before this model: its view moves into its record.
    if (Object.keys(legacy).length) {
      const rec = touch(data.apId as string);
      rec.view = { ...legacy, ...(rec.view ?? {}) };
    }
    return data;
  };
  return write("replace", make(), url, reason, { build: make, tries: 0 });
}

/** Push a new entry: a new apId (and apKey unless `data` keeps its place),
 *  its view in its own record. */
function pushEntry(data: Data, url: string | undefined, view: Data): boolean {
  const next: Data = { ...data };
  for (const k of VIEW_KEYS) delete next[k];
  next.apId = newId();
  if (!isString(next.apKey)) next.apKey = newKey();
  const rec = touch(next.apId as string);
  rec.key = next.apKey as string;
  rec.view = view;
  return write("push", next, url, "action");
}

// ---- reading position ------------------------------------------------------------

let legacyPositions: Record<string, number> | null = null;
function legacyScroll(key: unknown): number | undefined {
  if (!isString(key)) return undefined;
  if (!legacyPositions) {
    legacyPositions = {};
    try {
      const raw = sessionStorage.getItem(LEGACY_SCROLL_STORE);
      const parsed: unknown = raw ? JSON.parse(raw) : null;
      if (parsed && typeof parsed === "object") legacyPositions = parsed as Record<string, number>;
    } catch {
      // storage unavailable
    }
  }
  const v = legacyPositions[key];
  return typeof v === "number" ? v : undefined;
}

export function main(): HTMLElement | null {
  return document.querySelector<HTMLElement>(MAIN_SELECTOR);
}

/** Record the current scroll offset of the reading area for this entry
 *  (its record only: no history write). */
export function recordScroll() {
  const m = main();
  if (!m) return;
  const { apId, apKey } = identity();
  const rec = touch(apId);
  rec.key = apKey;
  rec.scroll = m.scrollTop;
  rec.at = ++clock;
}

/** Saved scroll offset of a history entry (undefined: never recorded). The
 *  latest record of the same place wins (an overlay shares its place). */
export function savedScroll(s: State): number | undefined {
  const id = s?.apId;
  const rec = isString(id) ? store().get(id) : undefined;
  if (!rec) return legacyScroll(s?.apKey);
  let best = typeof rec.scroll === "number" ? rec : undefined;
  if (rec.key) {
    for (const other of store().values()) {
      if (other.key === rec.key && typeof other.scroll === "number" && (other.at ?? 0) > (best?.at ?? -1)) best = other;
    }
  }
  return best?.scroll ?? legacyScroll(s?.apKey);
}

// ---- view of an entry ----------------------------------------------------------------

/** How entry `s` looked: its record's view over any view keys an older entry
 *  still has in history.state. Never throws; {} when nothing is known. */
export function entryView(s: State = state()): Data {
  const view: Data = {};
  if (!s) return view;
  for (const k of VIEW_KEYS) if (k in s) view[k] = s[k];
  const id = s.apId ?? (pendingIdentity && s === state() ? pendingIdentity.apId : undefined);
  const rec = isString(id) ? store().get(id) : undefined;
  if (rec?.view) {
    for (const [k, v] of Object.entries(rec.view)) {
      if (v === null) delete view[k];
      else view[k] = v;
    }
  }
  return view;
}

/** Change how the current entry looks (highlight, open lists, list scroll,
 *  query, followed result). No history write. */
export function setView(patch: Data, drop: string[] = []) {
  const rec = touch(identity().apId);
  const view: Data = { ...(rec.view ?? {}), ...patch };
  for (const k of drop) view[k] = null;
  rec.view = view;
}

// ---- steps -------------------------------------------------------------------------

const STEP_KEYS = ["apKey", "apId", "apMenu", "apDepth", "apAa"];

/**
 * A new reading place on the same page (anchor jump): a new entry with the
 * Next.js keys only — not the menu flag, not the previous place's key.
 * `extra` / `view`: the new entry's own state, in the same single write.
 */
export function pushPlace(url: string, extra: Data = {}, view: Data = {}): boolean {
  recordScroll();
  const rest: Data = { ...(state() ?? {}) };
  for (const k of STEP_KEYS) delete rest[k];
  return pushEntry({ ...rest, ...extra }, url, view);
}

/** Open an overlay entry on top of the current place (same apKey). It looks
 *  like the entry below (its view), changed by `view` and `drop`. */
export function pushOverlay(extra: Data, view: Data = {}, drop: string[] = []): boolean {
  const { apKey } = identity();
  const next: Data = { ...entryView(), ...view };
  for (const k of drop) delete next[k];
  const rest: Data = { ...(state() ?? {}) };
  delete rest.apId;
  return pushEntry({ ...rest, apKey, ...extra }, undefined, next);
}

/** A step to another place in the continuous book (lib/readingFlow.ts). */
export function pushReading(data: Data, url: string, view: Data = {}): boolean {
  const next: Data = { ...data };
  delete next.apId;
  delete next.apKey;
  return pushEntry(next, url, view);
}

/** Merge keys into the current entry (and drop the keys in `drop`). View keys
 *  go to the entry's record; history is written only when what the entry IS
 *  changes - one write. */
export function patchState(extra: Data, drop: string[] = [], reason: WriteReason = "action"): boolean {
  const viewPatch: Data = {};
  const statePatch: Data = {};
  for (const [k, v] of Object.entries(extra)) (VIEW_KEYS.includes(k) ? viewPatch : statePatch)[k] = v;
  const viewDrop = drop.filter((k) => VIEW_KEYS.includes(k));
  const stateDrop = drop.filter((k) => !VIEW_KEYS.includes(k));
  if (Object.keys(viewPatch).length || viewDrop.length) setView(viewPatch, viewDrop);
  const s = state() ?? {};
  const changes = Object.entries(statePatch).some(([k, v]) => s[k] !== v) || stateDrop.some((k) => k in s);
  if (!changes) return true;
  return replaceEntry(() => {
    const next: Data = { ...(state() ?? {}), ...statePatch };
    for (const k of stateDrop) delete next[k];
    return next;
  }, undefined, reason);
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
