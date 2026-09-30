// Global "show all" preferences of verse panels (client-side): "Show all
// translations" and "Show all word-by-word". Each is stored in localStorage
// under its own key; default off, i.e. the panels start collapsed. Components
// subscribe through the hooks below; the static HTML always renders "off".
import { useSyncExternalStore } from "react";

function createBooleanPref(storageKey: string, changeEvent: string) {
  /** Last value set in this page (used when localStorage is unavailable). */
  let memory: boolean | null = null;

  function read(): boolean {
    try {
      return localStorage.getItem(storageKey) === "1";
    } catch {
      return false; // storage unavailable
    }
  }

  function set(value: boolean) {
    try {
      if (value) localStorage.setItem(storageKey, "1");
      else localStorage.removeItem(storageKey);
    } catch {
      // storage unavailable — the choice lasts until the next reload
    }
    memory = value;
    window.dispatchEvent(new Event(changeEvent));
  }

  function snapshot(): boolean {
    const stored = read();
    return memory !== null && stored !== memory ? memory : stored;
  }

  function subscribe(onChange: () => void) {
    const onStorage = (e: StorageEvent) => {
      if (e.key === storageKey) {
        memory = null;
        onChange();
      }
    };
    window.addEventListener(changeEvent, onChange);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener(changeEvent, onChange);
      window.removeEventListener("storage", onStorage);
    };
  }

  function useValue(): boolean {
    return useSyncExternalStore(subscribe, snapshot, () => false);
  }

  return { set, useValue };
}

const translations = createBooleanPref("arcanaShowTranslations", "arcana:show-translations");
const wordByWord = createBooleanPref("arcanaShowWbw", "arcana:show-wbw");

export const setShowAllTranslations = translations.set;
export const setShowAllWbw = wordByWord.set;

export function useShowAllTranslations(): boolean {
  return translations.useValue();
}

export function useShowAllWbw(): boolean {
  return wordByWord.useValue();
}
