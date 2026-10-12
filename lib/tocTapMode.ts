"use client";

/**
 * PROPOSAL, not an approved rule (see «Правила интерфейса книг» §10).
 *
 * The approved contents behaviour is two taps: the first tap only highlights a
 * row, the second does its function. This switch lets the same build also run
 * a one-tap variant, so the two can be compared on a real device before
 * anything is decided:
 *
 *   ?toc=one  — one tap: the row does its function and stays highlighted
 *   ?toc=two  — the approved two-tap behaviour (default)
 *
 * The choice is remembered in localStorage, so the query is needed once.
 * Nothing else in the reader changes.
 */
import { useSyncExternalStore } from "react";

const KEY = "ap.tocTap";

/** Resolved once per page load: the query wins and is remembered, else storage. */
let resolved: boolean | null = null;

function resolve(): boolean {
  if (resolved !== null) return resolved;
  let value = false;
  try {
    value = localStorage.getItem(KEY) === "one";
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

/** true: one tap does the row's function (the proposal). false: two taps (the rule). */
export function useOneTapToc(): boolean {
  return useSyncExternalStore(subscribe, resolve, () => false);
}
