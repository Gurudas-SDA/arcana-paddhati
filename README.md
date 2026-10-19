# Arcana Paddhati

A reading app (installable PWA) for the temple manual *Arcana Paddhati — The Process of Deity Worship*.
Every section of the book has its own URL (`/arcana-paddhati/<section-id>/`, subsections as `#<subsection-id>` anchors),
and the sidebar search covers titles and the full text, ignoring diacritics.

Built with Next.js (App Router) as a fully static export and hosted on GitHub Pages.

## Where the content lives

- **`data/book.json`** — the whole book: `{ title, subtitle, sections: [{ id, title, subtitle, page, content, subsections: [{ id, title, content }] }] }`.
  Content blocks: `verse` (`sanskrit`, optional `translation`), `instruction`, `text`, `subtitle`, `paired-list` (`items`, `layout`), `image` (`src`, `alt`).
- `public/media/` — the book's pictures (19.10.2026 layout; data `src` values are paths under it):
  - `parampara/NN-<slug>.webp` (+ `.png` fallback) — guru-paramparā portraits 00-pancha-tattva … 08-prem-prayojan;
    `parampara/photo/` — photos masked by code (scripts/parampara/replace_photo.py);
  - `hotspots/<picture>/NN.png` — per-object masks of the interactive pictures (scripts/build_hotspot_masks.py);
  - `common/` — single pictures: gaudiya-emblem, tilak, paraphernalia, ca-logo (+ conch-shankha, frame-red-cartouche: not used in the app);
  - `cover/` — cover.jpg + cover.webp / cover-440.webp (the home page shows the WebP).
- `masters/` — originals (never served), same layout, e.g. `masters/parampara/`.
- Icons, favicon and manifest.json stay in `public/`.
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

Push to `main` (qa vārti pre-push; `--no-verify` aizliegts). The workflow `.github/workflows/deploy.yml` builds
ONLY `main` → `out/` → https://gurudas-sda.github.io/arcana-paddhati/ru-iast/ (produkcija, Satkirti redz).
Staging kopija izņemta 18.10.2026 (Satkirti msg 4469 «нет необходимости в staging»): citi zari deploy neizraisa un
`/staging/` netiek būvēts — arī ja kāds izveido zaru `staging`.

GitHub Pages izvietojumu identificē pēc commit SHA un klusi ignorē otru izvietojumu ar jau publicētu SHA (Actions
zaļš, bet nekas nemainās — 08.10 run 37777322691). Workflow solis «Commit not yet on Pages?» tādu run (re-run /
workflow_dispatch tam pašam commitam) padara sarkanu; lai pārpublicētu — jauns commits `main`.

Base path: `lib/basePath.ts` (`BASE_PATH`, `stripBasePath`) — visiem URL, ko Next pats neprefiksē (`<img>`, `fetch`,
metadata ikonas, SW reģistrācija). Nekad nerakstīt `/arcana-paddhati` kodā. Service worker ņem bāzi no savas atrašanās
vietas; staging kešs `arcana-paddhati_staging-*` nesajaucas ar produkcijas `arcana-paddhati-*`, un produkcijas SW
nepieskaras `/staging/` pieprasījumiem. `scripts/apply-base-path.mjs` (postbuild) pārraksta `manifest.json`
(nosaukums «… STAGING») un transkriptu atpakaļ-saites staging būvē. Lokāli: `MSYS_NO_PATHCONV=1
NEXT_PUBLIC_BASE_PATH=/arcana-paddhati/staging npm run build` (Git Bash; bez `MSYS_NO_PATHCONV` ceļš sabojājas).
Pirms push vienmēr atkal parastais `npm run build` — qa vārti testē `out/` zem `/arcana-paddhati`.
