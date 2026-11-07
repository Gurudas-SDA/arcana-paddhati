"use client";

import { useEffect, useState } from "react";
import { currentEntry, overlayHook } from "@/lib/navHistory";

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
  if (!overlay) {
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
    const live = new Set(p.ids);
    for (const k of Object.keys(p.urls)) if (!live.has(k)) delete p.urls[k];
    save(p);
  }
  // A step forward the browser cannot make needs the place's address; without it the button stays inactive.
  const forward = p.at >= 0 && p.at < p.ids.length - 1 && (!forwardLost(p) || !!p.urls?.[p.ids[p.at + 1]]);
  return { back: p.at > 0, forward };
}

/** The two buttons' state for the current place; `key` changes with every page. */
export function usePathSteps(key: string): { back: boolean; forward: boolean } {
  const [s, setS] = useState({ back: false, forward: false });
  useEffect(() => {
    const upd = () => {
      const n = notePathStep();
      setS((o) => (o.back === n.back && o.forward === n.forward ? o : n));
    };
    // The entry of a page made by the router gets its id a tick later (lib/navHistory.ts identity).
    const timers = [window.setTimeout(upd, 0), window.setTimeout(upd, 120)];
    const onPop = () => window.setTimeout(upd, 0);
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
