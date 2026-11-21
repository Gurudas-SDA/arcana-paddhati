"use client";

// V110 (Vraja Lila msg 8612–8614, variant «а»): the reader learns about a NEW
// version of the book instead of silently staying on the old one over a slow
// network: «Загружается новая версия книги — N %» → «Доступна новая версия
// книги» + «Обновить» → (after the switch) «Книга обновлена»; «Не удалось
// загрузить новую версию — повторить» when the install is interrupted.
// Progress comes from the NEW worker (public/sw.js: «sw-update-progress» — the
// core download); the offline behaviour (older complete cache) is not touched.
import { useSyncExternalStore } from "react";

export type SwUpdatePhase = "idle" | "loading" | "ready" | "failed" | "done";
export interface SwUpdateState {
  phase: SwUpdatePhase;
  /** 0–100 while loading. */
  pct: number;
}

const UPDATED_KEY = "ap.swUpdatedAt";
const DONE_SHOW_MS = 3000;

let state: SwUpdateState = { phase: "idle", pct: 0 };
const listeners = new Set<() => void>();
let reg: ServiceWorkerRegistration | null = null;
let tracked: ServiceWorker | null = null;
let doneTimer: number | undefined;
let started = false;

function set(next: SwUpdateState) {
  if (next.phase === state.phase && next.pct === state.pct) return;
  state = next;
  listeners.forEach((l) => l());
}

function showDone() {
  set({ phase: "done", pct: 100 });
  window.clearTimeout(doneTimer);
  doneTimer = window.setTimeout(() => set({ phase: "idle", pct: 0 }), DONE_SHOW_MS);
}

/** An update, not a first install: the page already has a worker. */
function isUpdate() {
  return !!navigator.serviceWorker.controller;
}

function track(w: ServiceWorker | null) {
  if (!w || !isUpdate()) return;
  tracked = w;
  const sync = () => {
    if (tracked !== w) return;
    if (w.state === "installing") set({ phase: "loading", pct: state.phase === "loading" ? state.pct : 0 });
    else if (w.state === "installed") set({ phase: "ready", pct: 100 });
    else if (w.state === "activated") showDone(); // took over (the page reloads, or is the new book already)
    else if (w.state === "redundant") {
      // superseded by a newer worker (then updatefound follows) or interrupted
      window.setTimeout(() => {
        if (tracked !== w) return;
        if (reg?.installing || reg?.waiting) return;
        set({ phase: "failed", pct: 0 });
      }, 0);
    }
  };
  w.addEventListener("statechange", sync);
  sync();
}

/** Called once after the registration (components/InstallBanner.tsx). */
export function startSwUpdate(registration: Promise<ServiceWorkerRegistration | undefined>) {
  if (started || typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;
  started = true;
  // after a reload caused by an update: «Книга обновлена»
  try {
    const at = Number(localStorage.getItem(UPDATED_KEY)) || 0;
    if (at) {
      localStorage.removeItem(UPDATED_KEY);
      if (Date.now() - at < 10 * 60 * 1000) showDone();
    }
  } catch {
    // no storage
  }
  navigator.serviceWorker.addEventListener("message", (e: MessageEvent) => {
    const d = e.data as { type?: string; done?: number; total?: number; final?: boolean };
    if (d?.type !== "sw-update-progress" || typeof d.done !== "number" || typeof d.total !== "number") return;
    if (!isUpdate() || state.phase === "ready" || state.phase === "done") return;
    const pct = d.total > 0 ? Math.min(100, Math.floor((d.done / d.total) * 100)) : 100;
    // a progress message means a new version is installing (even if this page missed updatefound)
    set({ phase: "loading", pct: Math.max(pct, state.phase === "loading" ? state.pct : 0) });
  });
  registration
    .then((r) => {
      if (!r) return;
      reg = r;
      if (r.installing) track(r.installing);
      else if (r.waiting && isUpdate()) {
        tracked = r.waiting;
        set({ phase: "ready", pct: 100 });
      }
      r.addEventListener("updatefound", () => track(r.installing));
    })
    .catch(() => {});
}

/** InstallBanner: the page is about to reload because the new version took over. */
export function noteUpdatedReload() {
  try {
    localStorage.setItem(UPDATED_KEY, String(Date.now()));
  } catch {
    // no storage
  }
}

/** InstallBanner: the new version took over a page that is already the new book (no reload). */
export function noteUpdatedInPlace() {
  showDone();
}

/** «Обновить»: switch to the waiting version and reload. */
export function applyUpdate() {
  noteUpdatedReload();
  const w = reg?.waiting ?? tracked;
  try {
    w?.postMessage({ type: "skip-waiting" });
  } catch {
    // ignore
  }
  // controllerchange reloads (InstallBanner); if it does not come, reload anyway
  window.setTimeout(() => window.location.reload(), 2500);
}

/** «Повторить»: ask the browser to look for the new version again. */
export function retryUpdate() {
  set({ phase: "loading", pct: 0 });
  reg?.update().catch(() => set({ phase: "failed", pct: 0 }));
  // nothing new found within a while (offline / still the same failure): say so again
  window.setTimeout(() => {
    if (state.phase === "loading" && state.pct === 0 && !reg?.installing && !reg?.waiting) set({ phase: "failed", pct: 0 });
  }, 8000);
}

function subscribe(l: () => void) {
  listeners.add(l);
  return () => listeners.delete(l);
}

export function useSwUpdate(): SwUpdateState {
  return useSyncExternalStore(subscribe, () => state, () => ({ phase: "idle", pct: 0 }) as SwUpdateState);
}
