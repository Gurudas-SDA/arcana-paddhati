// Cards under the cover (Vraja Lila msg 5318 «Видимая загрузка»): the cover is
// a server page, their state lives on the device (localStorage) or comes from
// the service worker — so the inline <head> script below decides BEFORE first
// paint whether a card's place is reserved (html[data-home-save]); the cover
// is sized for it from the start and never jumps when the card appears
// (app/globals.css .home-save-slot). A server component imports this module,
// hence no React here.

/** Where the reader stopped (lib/readingPlace.ts; «Продолжить», components/ResumeCard.tsx). */
export const READING_PLACE_KEY = "ap.readingPlace";

/** Saved-for-offline state shown on the cover (components/OfflineSaveCard.tsx):
 *  {s: "loading" | "partial" | "done" | "seen", d: done, t: total, f: failed, k: failedKinds}.
 *  "done" = finished, not yet shown on the cover; "seen" = shown once, the cover stays clean. */
export const OFFLINE_SAVE_KEY = "ap.offlineSave";

/** Inline script for <head> (app/layout.tsx). Reserve the save card's place when
 *  a download is unfinished / ended with failures / finished but not yet shown,
 *  or on the very first visit (no stored state, no service worker in charge yet:
 *  the book is about to be saved). */
export const HOME_CARDS_SCRIPT = `(function(){try{var d=document.documentElement,v=null;try{v=JSON.parse(localStorage.getItem(${JSON.stringify(
  OFFLINE_SAVE_KEY,
)})||"null")}catch(e){}var s=v&&v.s;if(s?(s==="loading"||s==="partial"||s==="done"):("serviceWorker" in navigator&&!navigator.serviceWorker.controller))d.setAttribute("data-home-save","")}catch(e){}})();`;
