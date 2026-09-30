// Builds public/search-index.<lang>.json for every language in lib/languages.json
// whose book exists (data/book.json for English, data/book.<lang>.json otherwise).
// One entry per section (its own body) and per subsection, with plain text.
// A language without a book has no index; the app then searches the English one.
// Runs automatically before `npm run build` / `npm run dev` (prebuild/predev).
import { existsSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const languages = JSON.parse(
  readFileSync(join(root, "lib", "languages.json"), "utf8")
);

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

function buildEntries(book) {
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
  return entries;
}

// Remove indexes of earlier builds (incl. the old single search-index.json).
rmSync(join(root, "public", "search-index.json"), { force: true });
for (const { code } of languages) {
  rmSync(join(root, "public", `search-index.${code}.json`), { force: true });
}

for (const { code } of languages) {
  const file = join(root, "data", code === "en" ? "book.json" : `book.${code}.json`);
  if (!existsSync(file)) {
    console.log(`search index: ${code} — no ${file.slice(root.length + 1)}, skipped (English fallback)`);
    continue;
  }
  const entries = buildEntries(JSON.parse(readFileSync(file, "utf8")));
  writeFileSync(join(root, "public", `search-index.${code}.json`), JSON.stringify(entries));
  console.log(`search index: ${code} — ${entries.length} entries -> public/search-index.${code}.json`);
}
