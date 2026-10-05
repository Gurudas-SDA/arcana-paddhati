"use client";

/**
 * Reader preferences of the «Аа» panel: text size and background
 * (white / sepia / night). Kept in localStorage (every access in try/catch;
 * a session without storage keeps them in memory until reload) and applied
 * to <html>: `data-reader-theme` and the CSS variable `--reader-zoom`
 * (see app/globals.css). The same keys are read by the inline script in
 * app/layout.tsx before first paint, so a reload never flashes white at night.
 */
import { useSyncExternalStore } from "react";
import { SIZE_KEY, THEME_KEY } from "@/lib/readerPrefsKeys";

export const THEMES = ["white", "sepia", "night"] as const;
export type ReaderTheme = (typeof THEMES)[number];

/** Text size steps (zoom factor of the reading column). */
export const SIZES = [0.85, 0.92, 1, 1.1, 1.2, 1.32, 1.46, 1.6];

const EVENT = "ap:readerprefs";

const memory: Record<string, string> = {};

function read(key: string): string | null {
  try {
    const v = localStorage.getItem(key);
    if (v !== null) return v;
  } catch {
    // storage unavailable
  }
  return memory[key] ?? null;
}

function write(key: string, value: string) {
  memory[key] = value;
  try {
    localStorage.setItem(key, value);
  } catch {
    // storage unavailable: kept in memory until reload
  }
  applyReaderPrefs();
  window.dispatchEvent(new Event(EVENT));
}

function themeSnapshot(): ReaderTheme {
  const v = read(THEME_KEY);
  return (THEMES as readonly string[]).includes(v ?? "") ? (v as ReaderTheme) : "white";
}

function sizeSnapshot(): number {
  const v = Number(read(SIZE_KEY));
  return SIZES.includes(v) ? v : 1;
}

/** Put the stored preferences on <html>. */
export function applyReaderPrefs() {
  const root = document.documentElement;
  const theme = themeSnapshot();
  if (theme === "white") root.removeAttribute("data-reader-theme");
  else root.setAttribute("data-reader-theme", theme);
  root.style.setProperty("--reader-zoom", String(sizeSnapshot()));
}

function subscribe(onChange: () => void) {
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

export function useReaderTheme(): ReaderTheme {
  return useSyncExternalStore(subscribe, themeSnapshot, () => "white");
}

export function useReaderSize(): number {
  return useSyncExternalStore(subscribe, sizeSnapshot, () => 1);
}

export function setReaderTheme(theme: ReaderTheme) {
  write(THEME_KEY, theme);
}

/** One step smaller (-1) or larger (+1). */
export function stepReaderSize(dir: -1 | 1) {
  const i = SIZES.indexOf(sizeSnapshot());
  const next = SIZES[Math.min(SIZES.length - 1, Math.max(0, (i < 0 ? 2 : i) + dir))];
  write(SIZE_KEY, String(next));
}
