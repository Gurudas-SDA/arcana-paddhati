// Postbuild: flatten RSC segment-prefetch files in out/ to the names the
// client router requests.
//
// Why: in `output: "export"` mode the client fetches a segment as
//   <route>/__next.<segment path with "/" replaced by ".">.txt
// e.g. /ru/offering-bhoga/__next.$d$slug.$d$section.__PAGE__.txt
// (convertSegmentPathToStaticExportFilename in next/dist/shared/lib/
// segment-cache/segment-value-encoding.js). The exporter calls the same
// function, but on Windows it gets the segment path from path.relative(), which
// uses "\" — so the "/"→"." replacement does nothing and path.join() writes
// nested folders instead: __next.$d$slug/$d$section/__PAGE__.txt. Every
// prefetch of a nested segment then 404s (and the precache manifest lists the
// wrong names, so those payloads are missing offline). Linux builds (CI) are
// already flat; there this script finds nothing and changes nothing.
//
// Must run before build-precache.mjs (the manifest lists the final names).
import { existsSync, readdirSync, renameSync, rmSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const outDir = join(dirname(fileURLToPath(import.meta.url)), "..", "out");
if (!existsSync(outDir)) {
  console.error("fix-segment-paths: out/ missing — run next build first");
  process.exit(1);
}

let moved = 0;
let conflicts = 0;

// Files below a "__next.*" folder, as paths relative to that folder.
function filesUnder(dir, prefix = "") {
  const files = [];
  for (const name of readdirSync(dir).sort()) {
    if (name === "desktop.ini") continue;
    const p = join(dir, name);
    if (statSync(p).isDirectory()) files.push(...filesUnder(p, prefix + name + "/"));
    else files.push(prefix + name);
  }
  return files;
}

function walk(dir) {
  for (const name of readdirSync(dir).sort()) {
    const p = join(dir, name);
    if (!statSync(p).isDirectory()) continue;
    if (name.startsWith("__next.")) {
      for (const rel of filesUnder(p)) {
        // "__next.$d$slug" + "/" + "$d$section/__PAGE__.txt"
        const flat = `${name}.${rel.split("/").join(".")}`;
        const dest = join(dir, flat);
        if (existsSync(dest)) {
          conflicts++;
          console.error(`fix-segment-paths: ${dest} already exists, keeping both`);
          continue;
        }
        renameSync(join(p, ...rel.split("/")), dest);
        moved++;
      }
      // Only Explorer/OneDrive desktop.ini files can be left now.
      if (!conflicts) rmSync(p, { recursive: true, force: true });
    } else {
      walk(p);
    }
  }
}

walk(outDir);
if (conflicts) process.exit(1);
console.log(`fix-segment-paths: flattened ${moved} segment files` + (moved ? "" : " (already flat)"));
