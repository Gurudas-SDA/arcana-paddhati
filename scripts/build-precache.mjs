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
// RSC payloads, /_next/static assets, search indexes, icons, images). Its
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

// Never requested by the client router, or not part of the book.
function excluded(rel) {
  const name = rel.split("/").pop();
  if (name === "desktop.ini") return true;
  if (name.endsWith(".map")) return true;
  if (rel === "sw.js" || rel === "precache-manifest.json") return true;
  // Full-route payload duplicate of index.txt; the client never fetches it.
  if (name === "__next._full.txt") return true;
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
  if (rel.startsWith("images/")) return 1;
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
  if (rel.startsWith("_next/") || rel.startsWith("images/")) return "shell";
  if (!rel.includes("/")) return rel.endsWith(".html") || rel.endsWith(".txt") ? "en" : "shell";
  const first = rel.split("/")[0];
  return LANG_DIRS.includes(first) ? first : "en";
}
const groups = [];

// A71 (10.10.2026) — no duplicates in the offline cache (was ~20 MB per
// language, now ~10 MB):
//  * <route>/index.txt (the full RSC payload; the router fetches it when a link
//    is followed before its segment prefetch finished, e.g. «След. глава») is
//    byte-identical to the flight chunks inlined in <route>/index.html
//    (`self.__next_f.push([1,"…"])`). It is not downloaded: the SW rebuilds it
//    from the cached page. Skipped ONLY when the rebuild gives exactly the same
//    bytes (checked here, per file) — otherwise it stays in the manifest.
//  * Byte-identical files of one download group with the same extension (e.g.
//    __next._index.txt — the root layout with the whole contents, ~180 KB, the
//    same on every page of a language) are stored once: `aliases` maps every
//    other URL to the stored one and the SW answers it from there.
// qa/suites/s31_offline_dedupe.py checks both, and offline navigation.
const FLIGHT = /<script[^>]*>self\.__next_f\.push\((\[[\s\S]*?\])\)<\/script>/g;
function flightFromHtml(html) {
  let out = "";
  let n = 0;
  for (const m of html.matchAll(FLIGHT)) {
    const a = JSON.parse(m[1]);
    if (a[0] === 1 && typeof a[1] === "string") {
      out += a[1];
      n++;
    } else if (a[0] !== 0) return null;
  }
  return n ? out : null;
}
function rebuildable(rel, buf) {
  if (!(rel === "index.txt" || rel.endsWith("/index.txt"))) return false;
  const html = join(outDir, rel.slice(0, -"index.txt".length), "index.html");
  if (!existsSync(html)) return false;
  const flight = flightFromHtml(readFileSync(html, "utf8"));
  return flight !== null && Buffer.from(flight, "utf8").equals(buf);
}

const hash = createHash("sha256");
let totalBytes = 0;
let skippedBytes = 0;
let rebuilt = 0;
const urls = [];
// Per-file hash: the SW copies unchanged files from the previous version's
// cache instead of downloading them again.
const hashes = [];
const aliases = {};
const firstOf = new Map(); // "group|ext|sha1" -> the stored URL
const counts = { pages: 0, rsc: 0, static: 0, other: 0 };
for (const rel of ordered) {
  const buf = readFileSync(join(outDir, rel));
  // The version covers every file, stored or not.
  hash.update(rel).update("\0").update(buf).update("\0");
  const url = toUrl(rel);
  if (rebuildable(rel, buf)) {
    rebuilt++;
    skippedBytes += buf.length;
    continue;
  }
  const sha1 = createHash("sha1").update(buf).digest("hex");
  if (!url.endsWith("/")) {
    const key = `${group(rel)}|${rel.slice(rel.lastIndexOf("."))}|${sha1}`;
    const first = firstOf.get(key);
    if (first) {
      aliases[url] = first;
      skippedBytes += buf.length;
      continue;
    }
    firstOf.set(key, url);
  }
  hashes.push(sha1.slice(0, 16));
  totalBytes += buf.length;
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
  JSON.stringify({ version, bytes: totalBytes, urls, hashes, groups, aliases })
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
    `${counts.other} other), ${(totalBytes / 1e6).toFixed(1)} MB; not stored: ${rebuilt} index.txt ` +
    `(rebuilt from the page) + ${Object.keys(aliases).length} duplicates (aliases) = ${(skippedBytes / 1e6).toFixed(1)} MB`
);
