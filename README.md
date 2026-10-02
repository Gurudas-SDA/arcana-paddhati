# Arcana Paddhati

A reading app (installable PWA) for the temple manual *Arcana Paddhati — The Process of Deity Worship*.
Every section of the book has its own URL (`/arcana-paddhati/<section-id>/`, subsections as `#<subsection-id>` anchors),
and the sidebar search covers titles and the full text, ignoring diacritics.

Built with Next.js (App Router) as a fully static export and hosted on GitHub Pages.

## Where the content lives

- **`data/book.json`** — the whole book: `{ title, subtitle, sections: [{ id, title, subtitle, page, content, subsections: [{ id, title, content }] }] }`.
  Content blocks: `verse` (`sanskrit`, optional `translation`), `instruction`, `text`, `subtitle`, `paired-list` (`items`, `layout`), `image` (`src`, `alt`).
- `public/images/` — images referenced by `image` blocks.
- `lib/book.ts` — TypeScript types for the book and helpers; `lib/content.ts` — build-time loading per language.

## Languages

English stays at `/<section>/`; other languages live at `/<lang>/` and `/<lang>/<section>/` with the same section ids.
The list (code, menu name, `<html lang>`) is `lib/languages.json`: `ru`, `ru-iast` (Russian, verses in IAST), `lv`, `de`, `fr`, `es`, `it`, `uk`.

- `data/book.<lang>.json` — the translated book (same shape and ids as `book.json`). If it is missing the pages
  are still built with the English text and the language menu marks the language "(EN)"; adding the file only needs a rebuild.
- `data/ui.en.json` — all interface strings (flat key → string). `data/ui.<lang>.json` may override any subset; missing keys fall back to English.
- The chosen language is remembered in `localStorage` and applied only on the start page `/`; otherwise the URL decides.
- `scripts/patch-html-lang.mjs` (postbuild) sets `<html lang>` in `out/<lang>/` pages, since the root layout has no route params.

Section and subsection `id`s become URLs and anchors — changing one breaks existing links.

## Editing and building

```bash
npm ci            # install dependencies
npm run dev       # local preview at http://localhost:3000/arcana-paddhati/
npm run lint
npm run build     # static site in out/
```

`npm run build` / `npm run dev` first run `scripts/build-search-index.mjs`, which writes one search index per language
with data, `public/search-index.<lang>.json` (generated, not committed).

## Print and Kindle editions

The book is kept in three formats: the app, a print PDF (A5) and a Kindle edition (EPUB 3 + AZW3).
After every content change:

```bash
npm run build && npm run formats      # app, then PDF + EPUB + AZW3 for ru and en
```

`npm run formats` (`scripts/formats/build_formats.py`) writes straight into `../Арчана-паддхати — книга/`
(`1 Приложение`, `2 Для печати`, `3 Kindle`). Other languages: `python scripts/formats/build_formats.py --lang ru,en,lv`;
only some formats: `--formats print` / `epub,azw3`. Needs Chrome (headless, no window), Python with PyMuPDF and fontTools,
Calibre (`ebook-convert`) and Noto Serif fonts (Windows ships them).

## Deploying

Push to `main`. The workflow `.github/workflows/deploy.yml` builds the site and publishes `out/` to GitHub Pages.
