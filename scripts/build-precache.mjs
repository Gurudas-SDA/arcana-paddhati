// Postbuild: write out/precache-manifest.json for full offline use of the PWA,
// and stamp the build version into out/sw.js.
//
// Why: the service worker used to precache only the start page, so in an
// installed PWA offline only pages already visited online worked. Client-side
// navigation in `output: "export"` mode fetches RSC payload files
// (<route>/index.txt?_rsc=… and segment files <route>/__next.<segment>.txt?_rsc=…),
// which were missing offline — tapping a section did nothing.
//
// The manifest lists every URL the book needs offline (pages as directory URLs,
// RSC payloads, /_next/static assets, search indexes, icons, media pictures). Its
// `version` is a hash of all listed files; it is injected into out/sw.js so the
// SW file changes on every content change and the browser installs the new SW.
//
// Must run after patch-html-lang.mjs (it hashes the final HTML).
import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

// Production "/arcana-paddhati/"; staging build "/arcana-paddhati/staging/" (NEXT_PUBLIC_BASE_PATH).
const BASE = (process.env.NEXT_PUBLIC_BASE_PATH || "/arcana-paddhati") + "/";
const VERSION_PLACEHOLDER = "__PRECACHE_VERSION__";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = join(root, "out");

// V49 (Vraja Lila msg 6363/6364): font files offline = only our own cut (app/fonts, copied byte for byte by
// next/font/local). The full Google Noto Serif files (next/font/google, 8 files, ~447 KB) are a fallback for a
// character outside the cut — not stored offline; online the SW still caches one the moment a page uses it.
const OWN_FONTS = new Set(
  readdirSync(join(root, "app", "fonts"))
    .filter((n) => n.endsWith(".woff2"))
    .map((n) => createHash("sha1").update(readFileSync(join(root, "app", "fonts", n))).digest("hex"))
);
function googleFallbackFont(rel) {
  if (!rel.startsWith("_next/static/media/") || !rel.endsWith(".woff2")) return false;
  return !OWN_FONTS.has(createHash("sha1").update(readFileSync(join(outDir, rel))).digest("hex"));
}

// V50 (Vraja Lila msg 6368 «почисти»): PNG / JPG pictures the pages never load are not stored offline (the files
// stay in public/ — the PDF / EPUB and the WebP-failure fallback use them; online the network still serves them):
//  - the original of a picture that has a WebP the page shows (lib/webp-images.json keys; the cover.jpg behind
//    HomePage's <picture> WebP srcset; a parampara photo's PNG `fallback` next to its `webp`,
//    lib/parampara-portraits.json) — <picture> takes the WebP; the PNG only on a WebP load error (PortraitImg);
//  - a media picture no built file names at all (ca-logo.png / ca-logo.svg: PDF / EPUB only; the app draws the
//    logo as inline SVG, components/CaLogo.tsx).
// Hotspot masks (media/hotspots/**.png) are loaded by the pages — kept.
const readLib = (n) => JSON.parse(readFileSync(join(root, "lib", n), "utf8"));
const RASTER_BACKUPS = new Set(["media/cover/cover.jpg"]);
for (const k of Object.keys(readLib("webp-images.json"))) if (/\.(png|jpe?g)$/i.test(k)) RASTER_BACKUPS.add("media/" + k);
for (const v of Object.values(readLib("parampara-portraits.json").portraits ?? {}))
  if (v && v.webp && v.fallback) RASTER_BACKUPS.add("media/" + v.fallback);
let unnamedMedia = null; // media pictures whose file name appears in no built page / payload / asset
function unreferencedMedia(rel) {
  if (!rel.startsWith("media/") || rel.startsWith("media/hotspots/") || !/\.(png|jpe?g|svg)$/i.test(rel)) return false;
  if (unnamedMedia === null) {
    const cands = walk(join(outDir, "media"))
      .map((p) => relative(outDir, p).split(sep).join("/"))
      .filter((r) => !r.startsWith("media/hotspots/") && /\.(png|jpe?g|svg)$/i.test(r));
    const left = new Set(cands.map((r) => r.split("/").pop()));
    for (const p of walk(outDir)) {
      if (!left.size) break;
      if (!/\.(html|txt|js|css|json|webmanifest)$/.test(p) || p.endsWith("precache-manifest.json")) continue;
      const text = readFileSync(p, "utf8");
      for (const n of [...left]) if (text.includes(n)) left.delete(n);
    }
    unnamedMedia = new Set(cands.filter((r) => left.has(r.split("/").pop())));
  }
  return unnamedMedia.has(rel);
}

// Never requested by the client router, or not part of the book.
function excluded(rel) {
  if (googleFallbackFont(rel)) return true;
  if (RASTER_BACKUPS.has(rel) || unreferencedMedia(rel)) return true;
  const name = rel.split("/").pop();
  if (name === "desktop.ini") return true;
  if (name.endsWith(".map")) return true;
  if (rel === "sw.js" || rel === "precache-manifest.json") return true;
  // Full-route payload duplicate of index.txt; the client never fetches it.
  if (name === "__next._full.txt") return true;
  // «Прокручивать» (A89): the whole-book page is only ever opened by the client
  // router (its RSC payloads below are stored); its 3.2 MB HTML per language
  // would be read only by a full load, which the network serves.
  if (/^([a-z-]+\/)?book\/index\.html$/.test(rel)) return true;
  // iOS startup pictures (public/splash/): the system takes them when the book is
  // added to the home screen, the page never requests them.
  if (rel.startsWith("splash/")) return true;
  // 404 pages are not needed offline.
  if (rel === "404.html" || rel.startsWith("404/") || rel.startsWith("_not-found/")) return true;
  return false;
}

function walk(dir) {
  const files = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) files.push(...walk(p));
    else files.push(p);
  }
  return files;
}

// Same canonical form the browser gives a Request URL.
function toUrl(rel) {
  let path = BASE + rel;
  if (path.endsWith("/index.html")) path = path.slice(0, -"index.html".length);
  return new URL(path, "https://x.invalid").pathname;
}

if (!existsSync(outDir)) {
  console.error("precache: out/ missing — run next build first");
  process.exit(1);
}

const entries = walk(outDir)
  .map((p) => relative(outDir, p).split(sep).join("/"))
  .filter((rel) => !excluded(rel))
  .sort();

// Download order (the SW fetches in this order): app shell and assets first,
// then the Russian (IAST) and English books, then the other languages, then
// the bundled transcripts — an interrupted first visit already holds the
// most-read parts.
const LANG_DIRS = ["ru", "ru-iast", "lv", "de", "fr", "es", "it", "uk", "hu", "pt", "lt"];
const LANG_FIRST = ["ru-iast", "", "ru"];
function priority(rel) {
  if (rel.startsWith("_next/")) return 0;
  if (rel.startsWith("media/")) return 1;
  if (!rel.includes("/") && !rel.endsWith(".html") && !rel.endsWith(".txt")) return 1;
  if (rel.startsWith("transcripts/")) return 20;
  const first = rel.split("/")[0];
  const code = LANG_DIRS.includes(first) ? first : "";
  const i = LANG_FIRST.indexOf(code);
  return i >= 0 ? 2 + i : 10;
}
const ordered = [...entries].sort((a, b) => priority(a) - priority(b) || (a < b ? -1 : a > b ? 1 : 0));

// Download group of each URL (SW v6, Reader v7.1): "shell" (build assets,
// icons, pictures, manifest), a language code ("en" for the root pages) for
// its pages, RSC payloads and search index, "transcripts" for the bundled
// lecture transcripts. The SW installs only the core (shell + the reader's
// language) and fetches the rest in the background.
function group(rel) {
  if (rel.startsWith("transcripts/")) return "transcripts";
  const m = /^search-index\.([a-z-]+)\.json$/.exec(rel);
  if (m) return m[1];
  if (rel.startsWith("_next/") || rel.startsWith("media/")) return "shell";
  if (!rel.includes("/")) return rel.endsWith(".html") || rel.endsWith(".txt") ? "en" : "shell";
  const first = rel.split("/")[0];
  return LANG_DIRS.includes(first) ? first : "en";
}
const groups = [];

const hash = createHash("sha256");
let totalBytes = 0;
const urls = [];
// Per-file hash: the SW copies unchanged files from the previous version's
// cache instead of downloading them again.
const hashes = [];
const counts = { pages: 0, rsc: 0, static: 0, other: 0 };
for (const rel of ordered) {
  const buf = readFileSync(join(outDir, rel));
  hash.update(rel).update("\0").update(buf).update("\0");
  hashes.push(createHash("sha1").update(buf).digest("hex").slice(0, 16));
  totalBytes += buf.length;
  const url = toUrl(rel);
  urls.push(url);
  groups.push(group(rel));
  if (url.endsWith("/")) counts.pages++;
  else if (url.endsWith(".txt")) counts.rsc++;
  else if (url.startsWith(BASE + "_next/static/")) counts.static++;
  else counts.other++;
}
const version = hash.digest("hex").slice(0, 16);

writeFileSync(
  join(outDir, "precache-manifest.json"),
  JSON.stringify({ version, bytes: totalBytes, urls, hashes, groups })
);

const swPath = join(outDir, "sw.js");
const sw = readFileSync(swPath, "utf8");
if (!sw.includes(VERSION_PLACEHOLDER)) {
  console.error("precache: version placeholder not found in out/sw.js");
  process.exit(1);
}
writeFileSync(swPath, sw.split(VERSION_PLACEHOLDER).join(version));

console.log(
  `precache: version ${version} — ${urls.length} URLs ` +
    `(${counts.pages} pages, ${counts.rsc} RSC payloads, ${counts.static} static assets, ` +
    `${counts.other} other), ${(totalBytes / 1e6).toFixed(1)} MB`
);
