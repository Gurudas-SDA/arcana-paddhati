"use client";

/**
 * One-tap Contents is the reader default. The existing switch retains the
 * previous two-tap interaction for comparison:
 *
 *   ?toc=one  — one tap: the row does its function and stays highlighted
 *   ?toc=two  — the previous two-tap behaviour
 *
 * The choice is remembered in localStorage, so the query is needed once.
 */
import { useSyncExternalStore } from "react";

const KEY = "ap.tocTap";

/** Resolved once per page load: the query wins and is remembered, else storage. */
let resolved: boolean | null = null;

function resolve(): boolean {
  if (resolved !== null) return resolved;
  let value = true;
  try {
    value = localStorage.getItem(KEY) !== "two";
  } catch {
    // storage unavailable
  }
  try {
    const q = new URLSearchParams(window.location.search).get("toc");
    if (q === "one" || q === "two") {
      value = q === "one";
      try {
        localStorage.setItem(KEY, value ? "one" : "two");
      } catch {
        // storage unavailable: the query still applies to this session
      }
    }
  } catch {
    // no URL access
  }
  resolved = value;
  return value;
}

/** Nothing changes it while the page lives, so there is nothing to subscribe to. */
const subscribe = () => () => {};

/** true: one tap does the row's function. false: the previous two-tap mode. */
export function useOneTapToc(): boolean {
  return useSyncExternalStore(subscribe, resolve, () => true);
}
