# Arcana Paddhati

A reading app (installable PWA) for the temple manual *Arcana Paddhati — The Process of Deity Worship*.
Every section of the book has its own URL (`/arcana-paddhati/<section-id>/`, subsections as `#<subsection-id>` anchors),
and the sidebar search covers titles and the full text, ignoring diacritics.

Built with Next.js (App Router) as a fully static export and hosted on GitHub Pages.

## Where the content lives

- **`data/book.json`** — the whole book: `{ title, subtitle, sections: [{ id, title, subtitle, page, content, subsections: [{ id, title, content }] }] }`.
  Content blocks: `verse` (`sanskrit`, optional `translation`), `instruction`, `text`, `subtitle`, `paired-list` (`items`, `layout`), `image` (`src`, `alt`).
- `public/images/` — images referenced by `image` blocks.
- `lib/book.ts` — TypeScript types for the book and helpers.

Section and subsection `id`s become URLs and anchors — changing one breaks existing links.

## Editing and building

```bash
npm ci            # install dependencies
npm run dev       # local preview at http://localhost:3000/arcana-paddhati/
npm run lint
npm run build     # static site in out/
```

`npm run build` / `npm run dev` first run `scripts/build-search-index.mjs`, which writes the search index
`public/search-index.json` from `data/book.json` (generated, not committed).

## Deploying

Push to `main`. The workflow `.github/workflows/deploy.yml` builds the site and publishes `out/` to GitHub Pages.
