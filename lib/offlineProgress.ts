"use client";

// Progress of the background offline download (service worker v6, public/sw.js):
// the worker posts {type: "precache-progress", done, total, complete, failed,
// failedKinds, final} (failures: Vraja Lila msg 5318, «Видимая загрузка»); the
// page pings it ("precache-continue") on load and every minute, so the
// download resumes on every visit until the whole book is stored.
import { useSyncExternalStore } from "react";
import { OFFLINE_SAVE_KEY } from "./homeCards";

/** Files the worker could not store, by kind (public/sw.js failKind). */
export interface FailedKinds {
  text?: number;
  images?: number;
  transcripts?: number;
  other?: number;
}

export interface OfflineProgress {
  done: number;
  total: number;
  complete: boolean;
  /** Files that could not be stored in this run (0 while none failed). */
  failed: number;
  failedKinds: FailedKinds;
  /** The run has ended (complete, or ended with failures). */
  final: boolean;
}

let current: OfflineProgress | null = null;
/** Is a service worker registered here? "no" in a browser that blocks it
 *  (e.g. a private window, test browsers): nothing will be saved. */
export type SwRegistered = "unknown" | "yes" | "no";
let registered: SwRegistered = "unknown";
const listeners = new Set<() => void>();
let started = false;

/** What the cover shows about saving (lib/homeCards.ts OFFLINE_SAVE_KEY), kept
 *  on the device so the count never resets and the place is reserved before
 *  first paint. Written here for every progress message, on any page. */
export interface OfflineSave {
  s: "loading" | "partial" | "done" | "seen";
  d: number;
  t: number;
  f: number;
  k: FailedKinds;
}

let memSave: OfflineSave | null = null;
let saveSnap: OfflineSave | null | undefined;

export function readOfflineSave(): OfflineSave | null {
  try {
    const v = JSON.parse(localStorage.getItem(OFFLINE_SAVE_KEY) || "null");
    return v && typeof v.s === "string" ? (v as OfflineSave) : memSave;
  } catch {
    return memSave;
  }
}

export function writeOfflineSave(v: OfflineSave) {
  memSave = v;
  saveSnap = v;
  try {
    localStorage.setItem(OFFLINE_SAVE_KEY, JSON.stringify(v));
  } catch {
    // no storage: kept in memory until reload
  }
  listeners.forEach((l) => l());
}

// «Готово» is shown once (Vraja Lila msg 5318): only after a download the reader
// saw; once the whole book has been saved («seen»), later version downloads
// stay silent — the complete older copy keeps serving offline meanwhile.
function storeProgress(p: OfflineProgress) {
  const prev = readOfflineSave();
  const seen = prev?.s === "seen";
  let s: OfflineSave["s"];
  if (p.complete) s = prev && (prev.s === "loading" || prev.s === "partial" || prev.s === "done") ? "done" : "seen";
  else if (seen) s = "seen";
  else s = p.final && p.failed > 0 ? "partial" : "loading";
  if (seen && s === "seen") return;
  const d = p.total > 0 ? p.done : prev?.d ?? 0;
  const t = p.total > 0 ? p.total : prev?.t ?? 0;
  writeOfflineSave({ s, d, t, f: p.failed, k: p.failedKinds });
}

function ping() {
  try {
    navigator.serviceWorker?.controller?.postMessage({ type: "precache-continue" });
  } catch {
    // no service worker
  }
}

/** Called once after the service worker is registered (InstallBanner). */
export function startOfflineSync() {
  if (started || typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;
  started = true;
  navigator.serviceWorker.addEventListener("message", (e: MessageEvent) => {
    const d = e.data as { type?: string } & Partial<OfflineProgress>;
    if (d?.type !== "precache-progress" || typeof d.done !== "number" || typeof d.total !== "number") return;
    current = {
      done: d.done,
      total: d.total,
      complete: !!d.complete,
      failed: typeof d.failed === "number" ? d.failed : 0,
      failedKinds: d.failedKinds && typeof d.failedKinds === "object" ? d.failedKinds : {},
      final: !!d.final,
    };
    storeProgress(current);
    listeners.forEach((l) => l());
  });
  navigator.serviceWorker.ready.then(() => ping()).catch(() => {});
  navigator.serviceWorker.addEventListener("controllerchange", ping);
  window.setInterval(ping, 60_000);
}

/** InstallBanner hands its register() promise: once settled, whether a
 *  registration really exists (a blocked worker "registers" without one). */
export function noteRegistration(p: Promise<unknown>) {
  const set = (v: SwRegistered) => {
    registered = v;
    listeners.forEach((l) => l());
  };
  p.then(() => navigator.serviceWorker.getRegistration()).then(
    (r) => set(r ? "yes" : "no"),
    () => set("no"),
  );
}

/** The stored save state (re-renders on every change). */
export function useOfflineSave(): OfflineSave | null {
  return useSyncExternalStore(
    subscribe,
    () => {
      if (saveSnap === undefined) saveSnap = readOfflineSave();
      return saveSnap;
    },
    () => null,
  );
}

export function useSwRegistered(): SwRegistered {
  return useSyncExternalStore(subscribe, () => registered, () => "unknown");
}

function subscribe(l: () => void) {
  listeners.add(l);
  return () => listeners.delete(l);
}

export function useOfflineProgress(): OfflineProgress | null {
  return useSyncExternalStore(subscribe, () => current, () => null);
}
