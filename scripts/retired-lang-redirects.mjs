// Postbuild: redirect pages for the retired languages (lib/languages.json "replacedBy").
//
// S 23.10.2026 (Padomnieks 934–941): «Оставляю два языка: английский и русский… оставить версию с IAST» —
// the book is built only in English (/) and Russian with IAST (/ru-iast/). Old links and bookmarks of the
// other languages must not break: every page a retired language had (/<code>/, /<code>/<chapter or part>/,
// /<code>/book/) gets a small static page that goes to the same place in the replacement language:
//   /ru/<x>/ -> /ru-iast/<x>/   (Cyrillic Russian -> Russian with IAST)
//   /de/<x>/ -> /<x>/           (lv, de, fr, es, it, uk, hu, pt, lt -> English, which has no prefix)
//
// Why static pages (GitHub Pages has no server redirects): each old URL answers 200 with
//   1) a script — location.replace keeps the #anchor and ?query, and turns a saved retired language
//      (localStorage "arcanaLang") into its replacement;
//   2) <meta http-equiv="refresh"> — the same without JavaScript;
//   3) <link rel="canonical"> + a plain link — for search engines and as a last resort.
// Any other URL under a retired language (unknown to this build) lands on 404.html, whose <head> runs
// LANG_REDIRECT_SCRIPT (lib/i18n.ts) with the same mapping.
// The data files of the retired languages stay in git; giving a language back = remove its "replacedBy".
// Must run before build-precache.mjs (it leaves these pages out of the offline book).
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = join(root, "out");
const BASE = (process.env.NEXT_PUBLIC_BASE_PATH || "/arcana-paddhati") + "/";
const DEFAULT_LANG = "en";
const STORAGE_KEY = "arcanaLang"; // = lib/i18n.ts LANG_STORAGE_KEY
const BOOK_SEGMENT = "book"; // = lib/bookRoute.ts BOOK_SEGMENT

const languages = JSON.parse(readFileSync(join(root, "lib", "languages.json"), "utf8"));
const retired = languages.filter((l) => l.replacedBy);
const english = JSON.parse(readFileSync(join(root, "data", "book.json"), "utf8"));
const routes = [
  "",
  ...english.sections.map((s) => s.id),
  ...(english.parts ?? []).map((p) => p.id),
  BOOK_SEGMENT,
];

const esc = (s) => s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
const storageMap = Object.fromEntries(retired.map((l) => [l.code, l.replacedBy]));

function page(lang, target) {
  const t = JSON.stringify(target);
  const script =
    `(function(){var t=${t},m=${JSON.stringify(storageMap)},k=${JSON.stringify(STORAGE_KEY)};` +
    `try{var s=localStorage.getItem(k);if(s&&Object.prototype.hasOwnProperty.call(m,s))localStorage.setItem(k,m[s])}catch(e){}` +
    `location.replace(t+location.search+location.hash)})();`;
  const a = esc(target);
  return (
    `<!doctype html><html lang="${esc(lang.htmlLang)}" translate="no"><head><meta charset="utf-8">` +
    `<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">` +
    `<title>Arcana Paddhati</title><link rel="canonical" href="${a}">` +
    `<script>${script}</script><meta http-equiv="refresh" content="0;url=${a}"></head>` +
    `<body style="font-family:Georgia,serif;background:#FDF8F0;color:#2C1810;padding:24px">` +
    `<p><a href="${a}" style="color:#965700">Arcana Paddhati ›</a></p></body></html>\n`
  );
}

let n = 0;
for (const lang of retired) {
  const prefix = lang.replacedBy === DEFAULT_LANG ? BASE : `${BASE}${lang.replacedBy}/`;
  for (const r of routes) {
    const dir = r ? join(outDir, lang.code, r) : join(outDir, lang.code);
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, "index.html"), page(lang, r ? `${prefix}${r}/` : prefix));
    n++;
  }
}
console.log(
  `retired languages: ${retired.map((l) => `${l.code}->${l.replacedBy}`).join(", ") || "none"} — ${n} redirect page(s)`
);
