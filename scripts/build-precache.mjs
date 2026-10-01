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

const BASE = "/arcana-paddhati/";
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

const hash = createHash("sha256");
let totalBytes = 0;
const urls = [];
const counts = { pages: 0, rsc: 0, static: 0, other: 0 };
for (const rel of entries) {
  const buf = readFileSync(join(outDir, rel));
  hash.update(rel).update("\0").update(buf).update("\0");
  totalBytes += buf.length;
  const url = toUrl(rel);
  urls.push(url);
  if (url.endsWith("/")) counts.pages++;
  else if (url.endsWith(".txt")) counts.rsc++;
  else if (url.startsWith(BASE + "_next/static/")) counts.static++;
  else counts.other++;
}
const version = hash.digest("hex").slice(0, 16);

writeFileSync(
  join(outDir, "precache-manifest.json"),
  JSON.stringify({ version, bytes: totalBytes, urls })
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
