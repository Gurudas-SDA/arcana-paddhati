"use client";

// Progress of the background offline download (service worker v6, public/sw.js):
// the worker posts {type: "precache-progress", done, total, complete}; the
// page pings it ("precache-continue") on load and every minute, so the
// download resumes on every visit until the whole book is stored.
import { useSyncExternalStore } from "react";

export interface OfflineProgress {
  done: number;
  total: number;
  complete: boolean;
}

let current: OfflineProgress | null = null;
const listeners = new Set<() => void>();
let started = false;

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
    current = { done: d.done, total: d.total, complete: !!d.complete };
    listeners.forEach((l) => l());
  });
  navigator.serviceWorker.ready.then(() => ping()).catch(() => {});
  navigator.serviceWorker.addEventListener("controllerchange", ping);
  window.setInterval(ping, 60_000);
}

function subscribe(l: () => void) {
  listeners.add(l);
  return () => listeners.delete(l);
}

export function useOfflineProgress(): OfflineProgress | null {
  return useSyncExternalStore(subscribe, () => current, () => null);
}
