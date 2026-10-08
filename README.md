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

## Print and EPUB editions

The book is kept in three formats: the app, a print PDF (A5) and an e-book (EPUB 3; Kindle takes it via Send to Kindle, no AZW3).
After every content change:

```bash
npm run build && npm run formats      # app, then PDF + EPUB for ru and en
```

`npm run formats` (`scripts/formats/build_formats.py`) writes straight into `../Арчана-паддхати — книга/`
(`1 Приложение`, `2 Для печати`, `3 EPUB`). Other languages: `python scripts/formats/build_formats.py --lang ru,en,lv`;
only some formats: `--formats print` / `epub`. Needs Chrome (headless, no window), Python with PyMuPDF and fontTools
and Noto Serif fonts (Windows ships them).

## Deploying

Push to `main` or `staging`. The workflow `.github/workflows/deploy.yml` builds BOTH branches into one
Pages artifact (Pages takes one per site): `main` → `out/` (production), `staging` → `out/staging/` (built with
`NEXT_PUBLIC_BASE_PATH=/arcana-paddhati/staging`). No `staging` branch, or a broken staging build → only `main` is published.

## Staging: darba plūsma (Gurudas, 2026-10-08)

Izmaiņas → zars `staging` → pārbaudītāji uz `/staging/` → merge `main`.

| | URL |
|---|---|
| Produkcija (Satkirti redz) | https://gurudas-sda.github.io/arcana-paddhati/ru-iast/ — zars `main` |
| Staging (pārbaudei) | https://gurudas-sda.github.io/arcana-paddhati/staging/ru-iast/ — zars `staging` |

1. Strādā zarā `staging` (`git checkout staging`), commit, `git push origin staging` (qa vārti darbojas tāpat; `--no-verify` aizliegts).
2. Gaidi Actions zaļu; pārbaudītāji (divi neatkarīgi, viens — cits modelis) pārbauda `/staging/`.
3. Tikai pēc tam: `git checkout main && git merge --no-ff staging && git push origin main`.
4. Pēc nakts/steidzama labojuma tieši `main` — `git checkout staging && git merge --no-ff main && git push origin staging` (staging nedrīkst atpalikt).

**Vienmēr `--no-ff`, nekad fast-forward:** GitHub Pages izvietojumu identificē pēc commit SHA un klusi ignorē otru
izvietojumu ar jau publicētu SHA (Actions zaļš, bet nekas nemainās — 08.10 run 37777322691). Ja main un staging ir uz
viena commita, otrā zara push neko nepublicētu. Workflow solis «Commit not yet on Pages?» tādu run padara sarkanu.

Base path: `lib/basePath.ts` (`BASE_PATH`, `stripBasePath`) — visiem URL, ko Next pats neprefiksē (`<img>`, `fetch`,
metadata ikonas, SW reģistrācija). Nekad nerakstīt `/arcana-paddhati` kodā. Service worker ņem bāzi no savas atrašanās
vietas; staging kešs `arcana-paddhati_staging-*` nesajaucas ar produkcijas `arcana-paddhati-*`, un produkcijas SW
nepieskaras `/staging/` pieprasījumiem. `scripts/apply-base-path.mjs` (postbuild) pārraksta `manifest.json`
(nosaukums «… STAGING») un transkriptu atpakaļ-saites staging būvē. Lokāli: `MSYS_NO_PATHCONV=1
NEXT_PUBLIC_BASE_PATH=/arcana-paddhati/staging npm run build` (Git Bash; bez `MSYS_NO_PATHCONV` ceļš sabojājas).
Pirms push vienmēr atkal parastais `npm run build` — qa vārti testē `out/` zem `/arcana-paddhati`.
