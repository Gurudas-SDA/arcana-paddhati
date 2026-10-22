# Design system — Arcana-paddhati

> «Мы не строим дизайн для красоты, мы строим масштабируемую, самоподдерживающуюся, гибкую
> дизайн-систему-инфраструктуру» — Vraja Lila, msg 6106 (22.10.2026).

So: **tokens → components → use.** A colour, radius, spacing or timing lives in ONE place (`tokens.css`); a
component reads only tokens (`components.css`, `*.tsx`); the book uses the component. No duplicated styles: a
style that a master component has is not written again elsewhere.

Started 22.10.2026 (V40, Vraja Lila msg 6091–6094 / 6103: «начни собирать их в папке design-system — так они
будут централизованно обитать там»; «подобные элементы и поведение документируй в design system… создаём
понемногу мастер-токены»). Grows step by step: an element comes here when it is made a master element; the
rest of the book keeps its own styles until then.

| File | What |
|---|---|
| `tokens.css` | master tokens — colours, radii, spacing, motion (CSS custom properties `--ds-*`) |
| `components.css` | the master components' styles; read only `--ds-*` tokens |
| `Pill.tsx` | the toggle chip (React) |

Both CSS files are imported at the top of `app/globals.css`. Colours follow the reading themes (`--rd-*`,
white / sepia / night) and the WCAG accent `--ap-gold` of V33 when it is present (fallback: today's gold), so a
colour change is made once, in `tokens.css`.

## Tokens

| Token | Value | Use |
|---|---|---|
| `--ds-accent` | `var(--ap-gold, #B8860B)` | gold: icons, a chip's text, frames |
| `--ds-accent-deep` | `var(--ap-gold, #8B6508)` | gold text on the cream fill (open state) |
| `--ds-accent-soft` | `#D4A843` | the soft chip's frame |
| `--ds-fill` / `--ds-fill-soft` | `#F5E6C8` / `#FDF8F0` | open / picked fill; the soft chip at rest |
| `--ds-line` | `#E8DCC8` | thin frames and lines |
| `--ds-band` | `var(--rd-row-stripe)` | tables' alternating row; the «В этом разделе» box |
| `--ds-band-active` | `var(--rd-row-active)` | a marked row (one block) |
| `--ds-row-lit` / `--ds-row-hover` | `#FAF3E8` / `#FDF8F0` | lit / hovered row of «Содержание» |
| `--ds-text` / `--ds-text-muted` | `var(--rd-fg)` / `var(--rd-muted)` | text; labels and numbers |
| `--ds-radius-pill` / `-band` / `-block` | `9999px` / `4px` / `6px` | chip; band and box; marked row |
| `--ds-target` | `44px` | minimum tap target |
| `--ds-box-pad` | `10px 14px 6px` | inside the box |
| `--ds-dur-fast` / `--ds-dur-slide`, `--ds-ease` | `150ms` / `220ms`, `ease` | colour and arrow; menu and bars |

## Components

### Pill — toggle chip (`Pill.tsx`, `.ds-pill`) — V40
- **Look:** a rounded chip with an arrow and a label. `tone="outline"`: white with a thin `--ds-line` frame,
  gold text; `tone="soft"`: cream with a `--ds-accent-soft` frame. `size="sm"` 11 px / `size="md"` 12 px.
- **States:** rest · hover (frame gold) · open (`data-open`: frame gold, fill `--ds-fill`, text `--ds-accent-deep`).
  **The size never changes:** the same font weight, frame width and padding in every state — only colour and
  fill (Vraja msg 6091: «фиксированный размер и меняется только интенсивность цвета и заливка»).
- **Behaviour:** `chevron="down"` — the arrow turns 180° smoothly around its centre (`transform`, 150 ms) when the
  chip opens its panel below; `chevron="right"` — opens a window, the arrow stays.
- **Used:** verse chips «пословно» / «перевод» and the mantra «пословно» chip (`components/CollapsibleVerse.tsx`),
  «Настроение Гурудева» (`components/MoodBlock.tsx`). New chips of this kind use `Pill`.
- **Test:** `qa/suites/s89_pill_master_v40.py`.

### One block — a lit / marked row (`.ds-one-block`) — V36, V36b, V38c
- **Rule** (Vraja msg 1290, 5962, 1321–1322, 6100–6101): a highlighted row is ONE rectangle over the whole row —
  number + text (lists), name + arrow (contents) — never separate bands for its parts; a banded (striped) row and a
  plain row light in the same width as the band.
- **How:** the row element carries the colour (`--ds-band-active` in lists, `--ds-row-lit` in «Содержание»);
  its parts are transparent (`.ds-one-block > *`). Lists: radius `--ds-radius-block`; the contents keep square rows
  with the gold left line.
- **Used:** marked list rows (V36, `app/globals.css` `.hs-row[data-active]`), the lit section row of «Содержание»
  (V38c, `components/Sidebar.tsx` `[data-toc-group-row]`).
- **Tests:** `s82_one_block_highlight_v36.py`, `s87_section_row_one_highlight_v38c.py`.

