// Postbuild: a build under another basePath (staging: NEXT_PUBLIC_BASE_PATH=
// /arcana-paddhati/staging) gets the right URLs also in the static files Next
// copies from public/ unchanged: the web app manifest (start_url, icons — and
// a «STAGING» name, so an installed staging app is never mistaken for the
// book) and the bundled transcript pages (their «‹ back» link).
// Production (default basePath) — nothing to do, files stay byte-identical.
//
// Must run before build-precache.mjs (it hashes the final files).
import { existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const DEFAULT = "/arcana-paddhati";
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || DEFAULT;
const outDir = join(dirname(fileURLToPath(import.meta.url)), "..", "out");

if (basePath === DEFAULT) {
  console.log(`base path: ${basePath} (production) — static files unchanged`);
  process.exit(0);
}
if (!existsSync(outDir)) {
  console.error("apply-base-path: out/ missing — run next build first");
  process.exit(1);
}

const from = DEFAULT + "/";
const to = basePath + "/";

const manifestPath = join(outDir, "manifest.json");
const m = JSON.parse(readFileSync(manifestPath, "utf8"));
const fix = (u) => (typeof u === "string" && u.startsWith(from) ? to + u.slice(from.length) : u);
m.start_url = fix(m.start_url);
if (m.scope) m.scope = fix(m.scope);
m.icons = (m.icons || []).map((i) => ({ ...i, src: fix(i.src) }));
m.name = `${m.name} STAGING`;
m.short_name = `${m.short_name} STAGING`;
writeFileSync(manifestPath, JSON.stringify(m, null, 2) + "\n");

let n = 0;
const trDir = join(outDir, "transcripts");
if (existsSync(trDir)) {
  for (const name of readdirSync(trDir)) {
    if (!name.endsWith(".html")) continue;
    const p = join(trDir, name);
    const html = readFileSync(p, "utf8");
    const patched = html.split(`href="${from}"`).join(`href="${to}"`);
    if (patched !== html) {
      writeFileSync(p, patched);
      n++;
    }
  }
}
console.log(`base path: ${basePath} — manifest + ${n} transcript page(s) rewritten`);
