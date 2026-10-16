// Postbuild: replace Next.js's random build id in out/ with one derived from
// the client code (the files in out/_next/static/chunks and media).
//
// Why (КСВ 15.10.2026, Satkirti's iPad: «1.2. Совершите омовение» stayed
// «загружается» while «Книга сохраняется… 76 %» — the book had been stored
// completely the day before): `next build` writes a NEW random build id into
// every page and every RSC payload (`"b":"<id>"`), so after each release every
// one of them (2458 of 2672 files, ~274 of 298 MB, all 11 languages) had a new
// hash in precache-manifest.json and the service worker downloaded the whole
// book again instead of copying the unchanged files from the stored version.
// Apart from the id, two builds of the same source are byte-identical
// (checked 15.10.2026: local build vs the production files of e9e88a5).
//
// The id still changes whenever the client code changes (then Next.js's
// version-skew check reloads a page of the old build, as before); a release
// that only changes text changes only the pages whose text changed.
//
// Must run after next build and before build-precache.mjs (it hashes the
// final files). No-op when the id is already stable.
import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, renameSync, statSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const outDir = join(dirname(fileURLToPath(import.meta.url)), "..", "out");
const staticDir = join(outDir, "_next", "static");
if (!existsSync(staticDir)) {
  console.error("stable-build-id: out/_next/static missing — run next build first");
  process.exit(1);
}

function files(dir, prefix = "") {
  const out = [];
  for (const name of readdirSync(dir).sort()) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...files(p, prefix + name + "/"));
    else out.push(prefix + name);
  }
  return out;
}

// The build id is the name of the one folder in _next/static besides chunks/ and media/.
const ids = readdirSync(staticDir).filter((n) => !["chunks", "media"].includes(n) && statSync(join(staticDir, n)).isDirectory());
if (ids.length !== 1) {
  console.error(`stable-build-id: expected one build-id folder in out/_next/static, found: ${ids.join(", ") || "none"}`);
  process.exit(1);
}
const oldId = ids[0];

const hash = createHash("sha256");
for (const sub of ["chunks", "media"]) {
  const dir = join(staticDir, sub);
  if (!existsSync(dir)) continue;
  for (const rel of files(dir)) hash.update(sub + "/" + rel).update("\0").update(readFileSync(join(dir, rel))).update("\0");
}
// Same length and alphabet as Next.js's id (21 url-safe characters).
const newId = hash.digest("base64url").slice(0, 21);
if (newId === oldId) {
  console.log(`stable-build-id: ${newId} (already stable)`);
  process.exit(0);
}

let changed = 0;
for (const rel of files(outDir)) {
  if (!/\.(html|txt|js|json)$/.test(rel)) continue;
  const p = join(outDir, rel);
  const text = readFileSync(p, "utf8");
  if (!text.includes(oldId)) continue;
  writeFileSync(p, text.split(oldId).join(newId));
  changed++;
}
renameSync(join(staticDir, oldId), join(staticDir, newId));
console.log(`stable-build-id: ${oldId} -> ${newId} in ${changed} files`);
