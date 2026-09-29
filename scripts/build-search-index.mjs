// Builds public/search-index.json from data/book.json.
// One entry per section (its own body) and per subsection, with plain text.
// Runs automatically before `npm run build` / `npm run dev` (prebuild/predev).
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const book = JSON.parse(readFileSync(join(root, "data", "book.json"), "utf8"));

function blockText(block) {
  switch (block.type) {
    case "verse":
      return [block.sanskrit, block.translation].filter(Boolean).join(" ");
    case "paired-list":
      return (block.items ?? [])
        .map((p) => `${p.label} ${p.value}`)
        .join(" ");
    case "image":
      return block.alt ?? "";
    default:
      return block.content ?? "";
  }
}

function plain(blocks) {
  return (blocks ?? [])
    .map(blockText)
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
}

const entries = [];
for (const s of book.sections) {
  entries.push({
    section: s.id,
    title: s.title,
    sectionTitle: s.title,
    text: plain([...(s.subtitle ? [{ type: "text", content: s.subtitle }] : []), ...s.content]),
  });
  for (const sub of s.subsections ?? []) {
    entries.push({
      section: s.id,
      anchor: sub.id,
      title: sub.title,
      sectionTitle: s.title,
      text: plain(sub.content),
    });
  }
}

const out = join(root, "public", "search-index.json");
writeFileSync(out, JSON.stringify(entries));
console.log(`search index: ${entries.length} entries -> public/search-index.json`);
