// Postbuild: set <html lang> in the exported pages of non-default languages.
// The root layout has no route params and always renders lang="en"; pages under
// out/<lang>/ get the language's htmlLang (lib/languages.json, e.g. ru-iast -> ru)
// when its book exists — otherwise the page shows English text and keeps "en".
import { existsSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = join(root, "out");
const languages = JSON.parse(
  readFileSync(join(root, "lib", "languages.json"), "utf8")
);

function htmlFiles(dir) {
  const files = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) files.push(...htmlFiles(p));
    else if (name.endsWith(".html")) files.push(p);
  }
  return files;
}

for (const { code, htmlLang } of languages) {
  if (code === "en") continue;
  const dir = join(outDir, code);
  if (!existsSync(dir)) continue;
  if (!existsSync(join(root, "data", `book.${code}.json`))) {
    console.log(`html lang: ${code} — no translation, pages stay lang="en"`);
    continue;
  }
  let n = 0;
  for (const file of htmlFiles(dir)) {
    const html = readFileSync(file, "utf8");
    const patched = html.replace(/<html lang="en"/, `<html lang="${htmlLang}"`);
    if (patched !== html) {
      writeFileSync(file, patched);
      n++;
    }
  }
  console.log(`html lang: ${code} — ${n} page(s) set to lang="${htmlLang}"`);
}
