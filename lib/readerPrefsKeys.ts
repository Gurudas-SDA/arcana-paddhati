// Storage keys of the reader preferences (lib/readerPrefs.ts) and the inline
// <head> script that applies them before first paint (app/layout.tsx, a
// server component — hence a module without React).
export const THEME_KEY = "ap.readerTheme";
export const SIZE_KEY = "ap.readerSize";

/** Inline script for <head>: applies the stored preferences before first paint. */
export const READER_PREFS_SCRIPT = `(function(){try{var d=document.documentElement,t=localStorage.getItem(${JSON.stringify(
  THEME_KEY,
)}),z=localStorage.getItem(${JSON.stringify(
  SIZE_KEY,
)});if(t==="sepia"||t==="night")d.setAttribute("data-reader-theme",t);if(z&&/^[0-9.]+$/.test(z))d.style.setProperty("--reader-zoom",z)}catch(e){}})();`;
