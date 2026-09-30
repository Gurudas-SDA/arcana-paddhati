// "Show all translations" preference (client-side). Stored in localStorage;
// default off, i.e. verse translations start collapsed. Components subscribe
// through useShowAllTranslations(); the static HTML always renders "off".
import { useSyncExternalStore } from "react";

const STORAGE_KEY = "arcanaShowTranslations";
const CHANGE_EVENT = "arcana:show-translations";

function read(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false; // storage unavailable
  }
}

export function setShowAllTranslations(value: boolean) {
  try {
    if (value) localStorage.setItem(STORAGE_KEY, "1");
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // storage unavailable — the choice lasts until the next reload
  }
  memory = value;
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

/** Last value set in this page (used when localStorage is unavailable). */
let memory: boolean | null = null;

function snapshot(): boolean {
  const stored = read();
  return memory !== null && stored !== memory ? memory : stored;
}

function subscribe(onChange: () => void) {
  const onStorage = (e: StorageEvent) => {
    if (e.key === STORAGE_KEY) {
      memory = null;
      onChange();
    }
  };
  window.addEventListener(CHANGE_EVENT, onChange);
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(CHANGE_EVENT, onChange);
    window.removeEventListener("storage", onStorage);
  };
}

export function useShowAllTranslations(): boolean {
  return useSyncExternalStore(subscribe, snapshot, () => false);
}
