# Contributing (UX/UI changes)

Thank you for helping with the interface of the Arcana Paddhati book app.

1. Fork https://github.com/Gurudas-SDA/arcana-paddhati and clone your fork.
2. Create a branch from `staging` (never from `main`): `git checkout -b ux/<short-topic> upstream/staging`.
3. Run the app locally: `npm install`, then `npm run dev`, and open http://localhost:3000/arcana-paddhati/ (the base path is required).
4. Check desktop and mobile widths (browser DevTools device toolbar).
5. Before pushing run `npm run lint` and `npm run build`.
6. Open a pull request **to `staging`, never to `main`**, and fill in the PR template (problem, what changed, screens checked, before/after screenshots).
7. One topic per PR. Nothing on your branch or fork is published; only maintainers merge.

Rules:
- Do not change content: texts, translations, Sanskrit, quotations (`data/`, `public/transcripts/`). Layout, styles, components and interaction only.
- Do not change section ids (they are URLs) and do not hard-code `/arcana-paddhati`; use `lib/basePath.ts`.
- No secrets or personal files in commits.

Interface rules: the book's UI rules were agreed with the book's author and are summarised in a separate document ("Правила интерфейса книг.md", in Russian) that maintainers send to contributors directly. If an idea contradicts a rule, describe it in the PR as a proposal; do not implement it without the author's explicit approval.
