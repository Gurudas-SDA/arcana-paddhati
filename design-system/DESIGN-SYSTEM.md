# Arcana-paddhati — Design System (working document)

> **One document.** It replaces Vraja Lila's DS V1.x file as a separate document (V56, 30.10.2026) and describes the book **as it is in `main`** —
> where Vraja Lila chose «живое / как сейчас» (30.10.2026 13:09–13:14) the LIVE value is written, not the V1.2 draft's. Change a value → change the code,
> its test and this file in the same step. History of the V56 merge: `Vraja_Lila/faili/2026.10.30_V56 Журнал хода работ.md`.
> `design-system/README.md` stays as the **log of behaviours and decisions** (V40–V47: chip, one block, section row, focus, AutoFill, panels).

- **Product:** Arcana-paddhati — reading app for *Arcana Paddhati — The Process of Deity Worship*; installable PWA, static Next.js export.
- **Themes:** White (no attribute), Sepia, Dark; set as `html[data-reader-theme="sepia|night"]` (67 lines use it — the name stays).
- **Source of truth:** the code (`app/globals.css`, `design-system/tokens.css`, `design-system/components.css`, components). This file follows it.

---

## 1 · Foundations

Three inks per theme; everything else is made from them.

| | page | ink | gold |
|---|---|---|---|
| White | `#FFFFFF` | `#1A1A1A` | `#965700` |
| Sepia | `#EFE6D2` | `#2A2016` | `#965700` |
| Dark | `#16130F` | `#E4DCCF` | `#E3A03C` |

Four moves make every other colour: (1) **gold at an alpha** → the six bands (translucent: the stripe underneath shows through);
(2) **gold mixed into the ink** → `accent-num`, `mantra-fg` (opaque); (3) **gold mixed into a surface** → the paused saving bar, the Sepia picked-language row (opaque);
(4) **a fixed warm neutral** → fills, hovers, hairlines, panels, tracks.

**One gold** (V47): `--ap-gold` is the only gold — every gold element and every gold word or number. An icon and its label are the same ink.
The old golds `#D4A843`, `#B8860B`, `#8B6508`, `#E8B04A`, `#E6D3A8` are gone from the interface (0 in CSS and components).
They remain only in the **print formats** (`scripts/formats/build_formats.py`, PDF/EPUB) — out of scope of the interface.
Parampara portrait frames: the data now say `var(--ap-gold)` (V56 step 2; the app already drew them with the token).

**Known accessibility limits** (recorded, not changed unless Vraja Lila decides): gold on a band fails AA (3.93 / 3.33 / 4.87 on selected, 2.93 / 2.60 / 3.23 on a search hit)
→ text on a band is `text-primary`, gold goes on icon or rail; `text-muted` is not for the loud Dark bands (3.3:1 on a hit); Sepia's gold `#965700` is at its floor (4.62:1);
the chip's resting frame is invisible on Sepia (1.09:1); `accent-60` is decoration only; the Dark switch knob on the ON track is white on `#E3A03C` = 2.24:1 (see §6, waiting for a decision).

---

## 2 · Tokens

**Names.** Two names exist for one value: the **role name** (new code, DS V1.2) and the **live name** (still used in 138 + 87 + 26 + 8 + 4 places: `--ap-*`, `--rd-*`, `--ds-*`, `--color-*`, `--lang-*`).
Role names are **aliases** declared at the end of `design-system/tokens.css` (`--accent: var(--ap-gold)` …; 37 pairs in `qa/lib/ds_aliases.json`, guarded by `qa/suites/s124_token_aliases_v56.py`: same value in all three themes).
The old names are swept out step by step (decision 7 «постепенно»), each step with its own test. Do not create a role name that has no live token of the same value.

### Gold and accent
| Role name | Live name | White | Sepia | Dark | Use |
|---|---|---|---|---|---|
| `accent` | `--ap-gold` | `#965700` | `#965700` | `#E3A03C` | every gold element, focus line, field frame, rail |
| `accent-on-dark` | `--ap-gold-on-dark` | `#E3A03C` | ↑ | ↑ | gold on a dark surface in any theme (toast, Undo) |
| `accent-band-from` / `-to` | `--ap-band-1` / `--ap-band-2` | `#A56000` / `#965700` | ↑ | ↑ | the «Install» band gradient and the bookmark dialog button; white text 4.91 → 5.74:1 |
| `accent-60` | `--ds-accent-soft` | gold 60 % | ↑ | ↑ | the soft chip's frame (decoration) |
| `accent-num` | `--ap-num` | `#7D4B05` | `#804C04` | `#B07D31` | section numbers «4.11.»: gold mixed toward the text (80 %; Dark 75 % toward the page) |
| `accent-label` | `--ap-label` | `#7A5E38` | ↑ | `#BBAE9A` | part labels, «Закладки» tab, loading note |
| `mantra-fg` | `--rd-mantra-fg` | `#643F0A` | `#603C0B` | `#E3A03C` | mantra text (gold mixed into the text 60 % / 50 %; Dark full accent) |
| `mantra-rule` | `--rd-mantra-rule` | accent | ↑ | ↑ | rule beside a mantra, the ❀ |

### Surface, text, line
| Role name | Live name | White | Sepia | Dark |
|---|---|---|---|---|
| `surface-page` | `--rd-bg` | `#FFFFFF` | `#EFE6D2` | `#16130F` |
| `surface-panel` | `--rd-panel-bg` | `#FFFFFF` | `#F6F0E2` | `#211C16` |
| `surface-bar` | `--rd-bar-bg` | `#FFFFFF` | `#EFE6D2` | `#1C1813` |
| `surface-raised` | `--ds-fill-soft` | `#FDF8F0` | `#FDF8F0` | `#211C16` |
| `surface-sunken` | `--ds-fill` | `#F5E6C8` | `#F5E6C8` | `#3A2F1F` |
| `surface-hover` | `--rd-hover` | `#F5E6C8` | `#FAF5EA` | `#2E271F` |
| `surface-lang-pick` | `--lang-sel-bg` | `#F5E6C8` | `#DAC4A0` (gold 24 % over the page) | `#3A3020` |
| `text-primary` | `--rd-fg` | `#1A1A1A` | `#2A2016` | `#E4DCCF` |
| `text-muted` | `--rd-muted` | `#5C3D2E` | ↑ | `#BBAE9A` |
| `text-faint` | `--rd-faint` | `rgba(92,61,46,.75)` | `…,.80` | `rgba(187,174,154,.70)` |
| `text-lang-pick` | `--lang-sel-fg` | `#2C1810` | ↑ | `#F2E9DA` |
| `line-hairline` | `--rd-border` | `#E8DCC8` | `#DCCCAC` | `#3A3128` |
| `line-control` | `--ds-line` | `#E8DCC8` | ↑ | `#3A3128` |
| `line-field` / `line-focus` | `--ds-field-line` / `--ds-focus` | accent | ↑ | ↑ |

Empty cells of the saving bar use `#F5E6C8` (light themes, a literal in `.home-save-track`) and `--rd-hover` at night (V54); the paused fill is `color-mix(gold 35 % [Dark 40 %], track)`.
The home cards (`.home-resume`, `.home-save`) have a light frame `#E5D8BC` and white fill (literals); at night they use `--rd-panel-bg` / `--rd-border` (V54).

### Highlight bands (gold at an alpha)
| Role name | Live name | White | Sepia | Dark | Use |
|---|---|---|---|---|---|
| `highlight-stripe` | `--rd-row-stripe` | 5 % | 5 % | 4 % | zebra rows |
| `highlight-current` | `--ap-band-toc` | 10 % | 10 % | 5 % | the lit row of «Содержание» |
| `highlight-selected` | `--rd-row-active` | 26 % | 25 % | 27 % | a selected list row |
| `highlight-bookmark` | `--ap-band-flash` | 31 % | 30 % | 39 % | a bookmark's place on arrival |
| `highlight-hit-list` | `--ap-band-mark` | 40 % | 38 % | 44 % | the search word in the results |
| `highlight-hit-text` | `--ap-band-hit` | 44 % | 42 % | 44 % | the search word in the text |

Text on a band is `text-primary`, never the accent. A band is **one block over the whole row** (V36) with corner radius **6 px** (V56 step 1, Vraja Lila 30.10 13:09);
the search word in running text keeps 3 px.

### Marks, shape, motion
| Role name | Live name | Value |
|---|---|---|
| `mark-scrim` | `--lang-dim` | `rgba(0,0,0,.6)` — one layer behind every window and menu, no blur |
| toast | (literal) | `#2C1810` in every theme; its Undo in `accent-on-dark` |
| hotspot number | (literal) | `#6E1A2E` on a white 60 % pill |
| `radius-pill` | `--ds-radius-pill` | `9999px` (chip, switch, dots, swatch) |
| `target` | `--ds-target` | `44px` minimum tap target |
| `focus-w` / `focus-gap` | `--ds-focus-w` / `--ds-focus-gap` | `2px` / `2px` |
| `dur-fast` / `dur-slide` | `--ds-dur-fast` / `--ds-dur-slide` | `150ms` / `220ms` (menu and bars, both ways) |

**Corner radii — the LIVE values** (Vraja Lila 30.10 13:14 «как сейчас»; one literal per role, no radius tokens except pill/block):

| Role | Radius | Where |
|---|---|---|
| band (selected row, zebra, text band) | **6 px** | `.hs-text`, `.hs-cell-first`, `.hs-row[data-active]`, zebra rows; token `--ds-radius-block` |
| panel «Аа» | 14 px | `.reader-panel` |
| window (bookmark name, install) | 12 px (`rounded-xl`) | `BookmarkNameDialog.tsx`, `InstallBanner.tsx` |
| window «Настроение Гурудева» | 6 px (`rounded-md`) | `MoodBlock.tsx` |
| field (search, bookmark name) | 8 px (`rounded-lg`) | `.search-input`, `.bookmark-name-field` (`.ds-field`) |
| size / theme / layout buttons | 10 px | `.reader-size-btn`, `.reader-theme-btn` |
| home cards | 9 px | `.home-resume`, `.home-save` |
| search word in text | 3 px | `.search-mark` |
| saving-bar cell | 1 px | `.home-save-track i` |
| chip, switch, dots, swatch | pill | `.ds-pill`, `.reader-switch-*`, `.reader-size-dots` |
| «Содержание» rows | square | full-bleed, 3 px rail |

`corner-shape: squircle` is **not used** (not found in `app/`, `components/`, `design-system/`, `lib/`).

**Shadows (LIVE, kept — decision 30.10 13:09):** panel «Аа» `0 10px 32px rgba(0,0,0,.18)`; windows `shadow-2xl` / `shadow-xl` (Tailwind); the switch knob `0 1px 2px rgba(0,0,0,.25)`.

**Motion (LIVE):** durations in use — 150 ms (8×), 220 ms (6×), 160 ms (6×), 140 ms (4×), 180 ms and 250 ms (3× each), 200 ms and 300 ms (2× each) — a clean-up to two tokens is in §6.
Opening/closing: «Содержание» and the bars close with their own forward animation, same duration and ease (V43, `ap-menu-out`).
The «Аа» panel and the language list close by **playing the opening animation backwards** (`reader-pop … reverse forwards`, 160 / 140 ms; msg 5521) — **kept as is** (decision A, 30.10 13:13;
measured on Pixel: slow start, abrupt end, opacity step 0.16–0.3 in the last frame). A panel is opaque in every frame while it moves; only the scrim fades (V44).

### Spacing and size
No spacing tokens in the live code (literals / Tailwind). Fixed steps in use: 2, 4, 6, 8, 10, 12, 20 px; `44px` tap target; **top and bottom bars are 57 px** (`--reader-bar-top-h`, `--rd-bottom-bar-h`).
Saving bar: **cells 7 px high, gap 2 px** (decision 30.10 13:09; the card is 103 px high inside a 136 px reserved slot — the cover does not move).
Reading column is fluid: `--rd-base: clamp(18px, 13px + 0.85vw, 23px)`, 20px from 640 px, times the A−/A+ step.

### Type
One family `book` — the book's own cut of Noto Serif (3 upright + 3 italic `woff2`, weights 400–700, `app/fonts/`; V49), Noto Serif and Georgia behind it.
Chip label weight: **400** live (the draft proposes 500 — waiting for a decision, §6). Row 15 px, switch 14 px, panel label 11 px / 600 / upper case.

---

## 3 · Components (live classes → tests)

| Component | Live class / file | Rule (decision) | Guard |
|---|---|---|---|
| Chip (toggle) | `.ds-pill`, `design-system/Pill.tsx` | size never changes between states (V40) | `s89` |
| One block (marked row) | `.ds-one-block`, `.hs-row[data-active]` | one band over number + text, radius 6 px (V36, V56) | `s82`, `s122` |
| Section row of «Содержание» | `components/Sidebar.tsx` `[data-toc-group-row]` | one button; square row + 3 px rail (V38c, V45) | `s87`, `s97` |
| Tabs «Содержание / Закладки» | `.sidebar-tabs` | 2 px accent rule under the selected tab; label `#2C1810` semibold | behaviour: `s52 s54 s55 s60 s71 s84`; **style: no test** |
| Focus | `:focus-visible`, `.ds-field` | ONE line (V43) | `s93` |
| Field | `.search-input`, `.bookmark-name-field` | frame in gold; bookmark field has no placeholder (iOS AutoFill, V43); search field has a gold placeholder | `s93 s95 s51` |
| Panel «Аа» | `.reader-panel` | language first, not cut, scrim 60 % (V27) | `s75` |
| Size / theme buttons, dots | `.reader-size-btn`, `.reader-theme-btn`, `.reader-size-dots` | picked = accent frame + 1 px inset | `s75` (partly); **style: no test** |
| Switch | `.reader-switch*` | 40×24 track, 18 px knob | `s26` |
| Language menu | `.lang-field`, `.lang-card` | V6, V59 | `s56`, `s116` |
| Saving card | `.home-save*` | V2 §0; cells 7/2; night on tokens (V54) | `s49 s64 s99 s111` |
| «Продолжить чтение» | `.home-resume*` | V10, V29 | `s58 s77` |
| Bookmark | `ReaderChrome.tsx`, `BookmarkNameDialog.tsx` | V4, V12, V34, V38 | `s54 s55 s60 s71 s84 s95` |
| Windows and scrim | `.install-backdrop`, `.mood-dialog` | 60 % scrim, ✕ on the top line (V18) | `s68` |
| Bars | `ReaderChrome.tsx` | opaque while moving (V44); stay at the chapter edges (V55) | `s96`, `s107` |
| Hint | `.reader-hint` | wholly above the bottom bar (V46) | `s98` |
| Portrait frame | `components/MaskedPortrait.tsx` | stroke `var(--ap-gold)`; manifest says the same (V56) | `s22`, `s123` |
| Splash | `#ap-splash` | V23, V53 | `s63`, `s110` |
| Italic, fonts | `app/fonts/*.woff2` | V49 | `s53`, `s102` |

The draft's «SectionBox / В этом разделе» is **not in the book** (removed in V45); its test `s91` no longer exists.

---

## 4 · House rules

- **One accent** — a lighter gold is the same token at a lower alpha or mixed, never a second hex.
- **An icon and its label are one ink**; icons sit inline beside text.
- **A control's box is fixed:** pressed and selected change fill and intensity only — never size, padding, border width or weight.
- **A panel closes with its own animation, never a flash;** a sliding panel is opaque in every frame; only the scrim fades; the scrim is one layer.
- **One focus line** — never two (no `focus:ring-*` / `focus:outline-*` next to a frame).
- **Only `transform`, `opacity` and paint animate;** never layout.
- **Contrast is a release gate** (`s81`), measured in all three themes.
- **Interface strings** live in `data/ui.<lang>.json` (12 languages: en, ru, ru-iast, lv, de, fr, es, it, uk, hu, pt, lt); sentence case; ❀ is the one sanctioned glyph; Sanskrit is IAST.
- Every interface change is guarded by a `qa/` test written first (red), then the fix (green) — `qa/README.md`.

---

## 5 · Decisions (Vraja Lila, V56)

| Date | Decision |
|---|---|
| 30.10 12:48 | Radii scale: first «б» (34·12·4·1), **cancelled 13:14 → «как сейчас»**. Token names: step by step, with a journal. Portrait frames: one gold. |
| 30.10 13:09 | Selected row **6 px**; saving bar **7 px / 2 px** (live); home cards **9 px** (live); shadows **live**. |
| 30.10 13:13 | Closing of «Аа» and the language list: **A — as now**. |
| 30.10 13:14 | Panel «Аа», windows, «Настроение Гурудева», fields: radii **as now**. |

---

## 6 · Waiting for a decision (not implemented)

| Item | What is needed from Vraja Lila |
|---|---|
| Dark switch knob: white on gold 2.24:1 (draft: the page ink, 8.25:1) | a frame «white / page ink» on «Аа» in Dark |
| Chip label weight 400 → 500 | a frame «400 / 500» on «пословно / перевод» |
| Hex literals → tokens (`#2C1810` 35 lines, `#5C3D2E` 30, `#E8DCC8` 23, `#F5E6C8` 21, `#FDF8F0` 17) | «yes» to a step-by-step sweep (each step = literal + its night/sepia override + a test) |
| Durations 140–180 ms → `dur-fast` | «yes» (low risk; 220 ms of panels untouched) |
| `prefers-reduced-motion` and print rules for all master components | «yes» + the existing `s65` before/after |
| Tests for tab style, size buttons, dots, window radii | none (Lipikāra writes them before touching these elements) |
| Home-card colours (`#E5D8BC`, `#FFFFFF`) → tokens | «yes» (value change: `#E5D8BC` → `#E8DCC8`, `#FFFFFF` → `#FDF8F0` would be visible) |
| Night portrait lines: `filter: brightness(.9)` on `.portrait-frame-lines` | whether the dimming is wanted |
| Print gold (`build_formats.py`: `#8B6508`, `#D4A843`) | Satkirti's formats — not the interface; ask Satkirti |
