"use client";

import { useEffect, useLayoutEffect, useState, useSyncExternalStore } from "react";
import { currentEntry, overlayHook, placeKey } from "@/lib/navHistory";

/**
 * V81 (Vraja Lila msg 7706 / 7735): the bottom bar's «‹ Вернуться» / «Вперёд ›» go along the reader's path, i.e. along the
 * real browser history. The browser does not say whether a step back / forward exists, so the entries of this tab are
 * counted here: a list of the history entries' ids (lib/navHistory.ts apId) and the place in it, kept in sessionStorage
 * (the tab's history survives a reload, so does this list). A new entry cuts off what lay ahead (as the browser does); a step
 * to an entry already in the list only moves the place. Overlays (menu, «Аа», «Настроение») are not steps of the path.
 * Opened directly: one entry — both buttons are inactive.
 */
const STORE = "ap.pathSteps";
const MAX = 300;
/** `gaps[id]`: how many overlay (menu) entries lie in the history right BEFORE the place `id` (V82, Vraja Lila msg 7769):
 *  a place chosen in the open contents has the menu's entries under it (rule 6: the phone's «back» reopens the menu), but
 *  «‹ Вернуться» / «Вперёд ›» step along the PLACES, so they jump over those entries (history.go(±(1 + gap))). */
type Path = {
  ids: string[];
  at: number;
  gaps?: Record<string, number>;
  /** V84 (Vraja Lila msg 7779, 7780): address of every place (pathname + search + hash), to make a step forward that the
   *  browser can no longer make. */
  urls?: Record<string, string>;
  /** V84: index of the place that had an overlay (menu, «Аа», «Настроение») pushed on it while a step forward lay ahead:
   *  the browser threw its «forward» entries away, so from this place on «Вперёд ›» is made by opening the place again. */
  cut?: number;
  /** V87 (Vraja Lila msg 7789, Nr.3 B): reading-place key (navHistory apKey) of every place. An overlay entry (menu, «Аа»)
   *  shares its place's key, so when the browser's «назад» lands on an overlay the path knows which place lies under it. */
  keys?: Record<string, string>;
};

function read(): Path {
  try {
    const p = JSON.parse(sessionStorage.getItem(STORE) ?? "null") as Path | null;
    if (p && Array.isArray(p.ids) && typeof p.at === "number" && p.at >= 0 && p.at < p.ids.length) return p;
  } catch {
    // storage unavailable
  }
  return { ids: [], at: -1 };
}

let memory: Path | null = null;
function path(): Path {
  return (memory ??= read());
}

/** The menu is left for a place: `depth` menu entries stay under the place that is about to be pushed. */
let pendingGap: { depth: number; at: number } | null = null;
export function noteMenuGap(depth: number) {
  pendingGap = depth > 0 ? { depth, at: performance.now() } : null;
}

/** How many history entries one step of the path spans (1 + the menu entries between the two places). */
export function pathStepDistance(dir: "back" | "forward"): number {
  const p = path();
  const target = dir === "back" ? p.at : p.at + 1;
  const id = p.ids[target];
  return 1 + (id ? (p.gaps?.[id] ?? 0) : 0);
}

function save(p: Path) {
  try {
    sessionStorage.setItem(STORE, JSON.stringify(p));
  } catch {
    // storage unavailable: memory only
  }
}

/** V84: an overlay was pushed on the current place: the browser's «forward» entries are gone. */
function noteOverlayPush() {
  const p = path();
  if (p.at < 0 || p.at >= p.ids.length - 1) return;
  p.cut = Math.min(p.cut ?? p.at, p.at);
  save(p);
}
overlayHook.fn = noteOverlayPush;

/** V84: the next step forward must be made by opening the place (the browser has no entry for it). */
function forwardLost(p: Path): boolean {
  return p.cut !== undefined && p.at >= p.cut && p.at < p.ids.length - 1;
}

/** V84: where «Вперёд ›» leads when the browser cannot go there itself (null: it can, or the address is unknown). */
export function pathReplayUrl(): string | null {
  const p = path();
  if (!forwardLost(p)) return null;
  return p.urls?.[p.ids[p.at + 1]] ?? null;
}

/** V84: the page about to open is the place after the current one (not a new place that cuts the path off). */
let replaying: number | null = null;
export function noteReplay() {
  replaying = performance.now();
}

/** Note the current entry; returns the state of the two buttons. */
export function notePathStep(): { back: boolean; forward: boolean } {
  const p = path();
  const { id, overlay } = currentEntry();
  if (overlay) {
    // V87 (Nr.3 B): the browser's «назад» landed on the menu / panel entry over an earlier place (the page shown is that
    // place): the path stands on THAT place, so «Вперёд ›» stays active (it closes the menu and opens the place left).
    let key = "";
    try { key = placeKey(); } catch { key = ""; }
    const under = key ? p.ids.findIndex((x) => p.keys?.[x] === key) : -1;
    if (under >= 0 && under !== p.at) {
      p.at = under;
      save(p);
    }
  } else {
    const known = p.ids.indexOf(id);
    if (known >= 0) {
      p.at = known;
    } else if (replaying !== null && performance.now() - replaying < 15000 && p.at < p.ids.length - 1) {
      const old = p.ids[p.at + 1];
      p.ids[p.at + 1] = id;
      p.at += 1;
      replaying = null;
      if (p.gaps) delete p.gaps[old];
      if (p.urls) delete p.urls[old];
    } else {
      p.ids = [...p.ids.slice(0, p.at + 1), id].slice(-MAX);
      p.at = p.ids.length - 1;
      p.cut = undefined;
      replaying = null;
      if (pendingGap && performance.now() - pendingGap.at < 30000) {
        p.gaps = { ...(p.gaps ?? {}), [id]: pendingGap.depth };
      }
      pendingGap = null;
      if (p.gaps) {
        const keep = new Set(p.ids);
        for (const k of Object.keys(p.gaps)) if (!keep.has(k)) delete p.gaps[k];
      }
    }
    p.urls = { ...(p.urls ?? {}), [id]: window.location.pathname + window.location.search + window.location.hash };
    try { p.keys = { ...(p.keys ?? {}), [id]: placeKey() }; } catch { /* no key: no overlay lookup for this place */ }
    const live = new Set(p.ids);
    for (const k of Object.keys(p.urls)) if (!live.has(k)) delete p.urls[k];
    for (const k of Object.keys(p.keys ?? {})) if (!live.has(k)) delete p.keys![k];
    save(p);
  }
  // A step forward the browser cannot make needs the place's address; without it the button stays inactive.
  const forward = p.at >= 0 && p.at < p.ids.length - 1 && (!forwardLost(p) || !!p.urls?.[p.ids[p.at + 1]]);
  return { back: p.at > 0, forward };
}

/** V89 (Vraja Lila msg 7859, Nr.4 C): the last state of the two buttons. The reader's chrome is built again for every page, and its
 *  buttons started inactive (grey) for ~0.1-0.5 s until the path was read: now a page starts with the state the previous one had. */
let lastSteps = { back: false, forward: false };

/** V89 (Nr.4 C): «‹ Вернуться» / «Вперёд ›» was pressed and its page has not arrived yet: a short, unobtrusive indicator on the
 *  pressed button (components/ReaderChrome.tsx, app/globals.css) instead of the grey buttons. */
let stepping: "back" | "forward" | null = null;
let steppingTimer: number | undefined;
let steppingSince = 0;
/** The buttons' state when the step began: shown (not grey) until the page of the step has arrived. */
let held = { back: false, forward: false };
const steppingSubs = new Set<() => void>();
const STEPPING_STORE = "ap.stepping";
function setStepping(v: "back" | "forward" | null) {
  if (stepping === v) return;
  stepping = v;
  if (v === null) {
    try { sessionStorage.removeItem(STEPPING_STORE); } catch { /* storage unavailable */ }
    document.documentElement.removeAttribute("data-ap-stepping");
  }
  steppingSubs.forEach((f) => f());
}
export function noteStepping(dir: "back" | "forward") {
  held = lastSteps;
  steppingSince = performance.now();
  // A step across documents (the history entry was made by a full page load) reloads the page: the new page takes the step over.
  try { sessionStorage.setItem(STEPPING_STORE, JSON.stringify({ dir, held, t: Date.now() })); } catch { /* storage unavailable */ }
  setStepping(dir);
  window.clearTimeout(steppingTimer);
  steppingTimer = window.setTimeout(() => setStepping(null), 2500); // tehniskais slieksnis Lipikāra, nav S noteikums
}
/** The step is over `after` ms from now - but the indicator is shown for 700 ms at least (a blink would not be seen). */
function endStepping(after: number) {
  if (stepping === null) return;
  window.clearTimeout(steppingTimer);
  const shownFor = performance.now() - steppingSince;
  steppingTimer = window.setTimeout(() => setStepping(null), Math.max(after, 700 - shownFor)); // tehniskais slieksnis Lipikāra
}
let steppingRestored = false;
/** A page loaded in the middle of a step (full document load) goes on with the step's indicator and the buttons' state. */
function restoreStepping() {
  if (steppingRestored) return;
  steppingRestored = true;
  try {
    const r = JSON.parse(sessionStorage.getItem(STEPPING_STORE) ?? "null") as { dir: "back" | "forward"; held: { back: boolean; forward: boolean }; t: number } | null;
    const age = r ? Date.now() - r.t : Infinity;
    if (!r || age > 2500) return;
    held = r.held;
    steppingSince = performance.now() - age;
    setStepping(r.dir);
    window.clearTimeout(steppingTimer);
    steppingTimer = window.setTimeout(() => setStepping(null), 2500 - age);
  } catch {
    // storage unavailable: no indicator
  }
}

/** The state of the two buttons read from the path without noting anything (a fresh page starts with it, before the first paint). */
function peekSteps(): { back: boolean; forward: boolean } {
  const p = path();
  let at = p.at;
  try {
    const id = (window.history.state as { apId?: string } | null)?.apId;
    const k = id ? p.ids.indexOf(id) : -1;
    if (k >= 0) at = k;
  } catch {
    // history unavailable
  }
  return { back: at > 0, forward: at >= 0 && at < p.ids.length - 1 && (!forwardLost(p) || !!p.urls?.[p.ids[at + 1]]) };
}

/** A «Вернуться» / «Вперёд» step is under way (V89: only such a step brings the highlighted row into view over a restored list offset). */
export function isStepping(): boolean {
  return stepping !== null;
}

/** The two buttons as they are drawn: while a step is under way they keep the state they had (no grey flash). */
export function stepButtons(steps: { back: boolean; forward: boolean }, under: "back" | "forward" | null) {
  return under ? held : steps;
}
export function useStepping(): "back" | "forward" | null {
  return useSyncExternalStore(
    (f) => {
      steppingSubs.add(f);
      return () => steppingSubs.delete(f);
    },
    () => stepping,
    () => null,
  );
}

/** The two buttons' state for the current place; `key` changes with every page. */
export function usePathSteps(key: string): { back: boolean; forward: boolean } {
  const [s, setS] = useState(lastSteps);
  // V89 (Nr.4 C): a page loaded afresh does not start with grey buttons - before its first paint it takes the path's state (and a step's
  // indicator) over; the hydration itself renders as the server did.
  useLayoutEffect(() => {
    restoreStepping();
    const n = peekSteps();
    lastSteps = n;
    // before the first paint on purpose: the path lives in sessionStorage (an external system), unreadable during hydration
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setS((o) => (o.back === n.back && o.forward === n.forward ? o : n));
  }, [key]);
  useEffect(() => {
    const upd = () => {
      const n = notePathStep();
      lastSteps = n;
      setS((o) => (o.back === n.back && o.forward === n.forward ? o : n));
    };
    // The entry of a page made by the router gets its id a tick later (lib/navHistory.ts identity).
    const timers = [window.setTimeout(upd, 0), window.setTimeout(upd, 120), window.setTimeout(() => endStepping(150), 120)];
    const onPop = () => {
      window.setTimeout(upd, 0);
      endStepping(1200); // a step within the same page ends here; a step to another page ends when that page has arrived
    };
    window.addEventListener("popstate", onPop);
    // V84: a jump to a subsection of the same page (menu, search) is a place of the path too.
    window.addEventListener("hashchange", onPop);
    return () => {
      timers.forEach((t) => window.clearTimeout(t));
      window.removeEventListener("popstate", onPop);
      window.removeEventListener("hashchange", onPop);
    };
  }, [key]);
  return s;
}
