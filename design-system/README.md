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
| `--ds-band` | `var(--rd-row-stripe)` | tables' alternating row |
| `--ds-band-active` | `var(--rd-row-active)` | a marked row (one block) |
| `--ds-row-lit` / `--ds-row-hover` | `#FAF3E8` / `#FDF8F0` | lit / hovered row of «Содержание» |
| `--ds-text` / `--ds-text-muted` | `var(--rd-fg)` / `var(--rd-muted)` | text; labels and numbers |
| `--ds-radius-pill` / `-band` / `-block` | `9999px` / `4px` / `6px` | chip; band; marked row |
| `--ds-target` | `44px` | minimum tap target |
| `--ds-dur-fast` / `--ds-dur-slide`, `--ds-ease` | `150ms` / `220ms`, `ease` | colour and arrow; menu and bars |
| `--ds-focus` / `--ds-focus-w` / `--ds-focus-gap` | `var(--ap-gold)` / `2px` / `2px` | THE focus line: colour, width, outline offset of a frameless control (V43) |
| `--ds-field-line` | `var(--ap-gold)` | a text field's 1 px frame (WCAG 1.4.11 ≥ 3:1, V33) |

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
  (V38c; since V45 one button, `components/Sidebar.tsx` `[data-toc-group-row]`).
- **Tests:** `s82_one_block_highlight_v36.py`, `s87_section_row_one_highlight_v38c.py`.

### Section row of «Содержание» — ONE button (`components/Sidebar.tsx` `renderGroupHeading`) — V45
- **Rule** (Vraja Lila msg 6178 / 1412, 22.10.2026; replaces V37 «the name opens the section's page» and V39 «В этом
  разделе»): the row of a section (Введение, Храмовый стандарт, Домашний стандарт, Стандарт для проповеднических
  центров, Праздники, обеты и песни арати) is ONE button over the whole row: a tap anywhere expands its chapters, the
  next one folds them. It never leads anywhere, the reading place stays. The arrow ▸ is only the state's icon inside
  the row (turns 90° when open; `pointer-events: none`), exactly like a chapter with subsections.
- **No section pages:** a section has no page of its own — no «В этом разделе» box (removed with its component and
  styles), «‹ Назад» / «Вперёд ›» step only through text (`lib/book.ts` `readingOrder`: chapters, and a section only
  while it still has text of its own). A part in preparation shows one line of text in the menu, not a link.
  In «Лента» the parts' headings stay in place between the chapters (the contents' order).
- **Highlight:** the lit row is one element, so one background by construction (V38c).
- **Test:** `qa/suites/s97_section_row_one_button_v45.py`.

### Cover — bottom bar with «Вперёд ›» only — V45
- **Rule** (Vraja Lila msg 6191, replaces V38b «only the top bar»): a tap on the cover brings out both bars; the
  bottom one holds only «Вперёд ›» → the first page after the cover; there «‹ Назад» returns to the cover and
  «Вперёд ›» goes on. (`chapterNeighbours(order, null)`.)
- **Test:** `qa/suites/s97_section_row_one_button_v45.py` (part D).

### Focus — ONE line, one style (`:focus-visible`, `.ds-field`) — V43
- **Rule** (Vraja Lila 22.10.2026: «двойные рамки всё ещё там (на поиске тоже)»): a focused control shows ONE line,
  never two — no outline or ring beside a frame of its own, no outline + ring together. One colour (`--ds-focus` =
  the theme's accent `--ap-gold`), one width (`--ds-focus-w` 2 px), everywhere.
- **How:**
  - a control **without** a frame (buttons, links, rows, icons): one outline `--ds-focus-w solid --ds-focus`,
    `--ds-focus-gap` away (rows of «Содержание» draw it inside, `-2px`); no Tailwind `ring-*` / `outline-*` of its own;
  - a control **with** a frame — the text field `.ds-field` (search in «Содержание», the bookmark's name) and
    `Pill`: no outline, no ring; its own 1 px frame turns `--ds-focus` and thickens inward by an inset shadow
    (1 px border + 1 px inset = one 2 px line; the text does not move, the size does not change);
  - the focus line appears at once (no colour transition on it).
- **Before** (live 22.10): the bookmark field — gold border + the global outline 2 px with a 2 px gap; the search
  field — the same (V33 a496284 not released); verse chips — grey frame + gold outline beside it; rows — rings at
  40 % / outlines at 55 %.
- **New fields** use `.ds-field`; never add `focus:ring-*` / `focus:outline-*` to a component.
- **Test:** `qa/suites/s93_one_focus_frame_v43.py`.

### Text field without iOS AutoFill — V43
- **Rule** (Vraja Lila 22.10.2026, iPhone: «autofill пока вижу»): a field for the book's own text (the bookmark's
  name) must not get Safari's «AutoFill Contact» bar.
- **Why it came:** Safari ignores `autocomplete="off"` for contact AutoFill; it decides by the field's `name` / `id`,
  its placeholder and the text of its label (reported triggers: a dash in `name` — «bm-title-field»; words like
  «Name» / «Title»).
- **How** (all of them, each harmless): `name="search"` and an `id` without a dash or contact word (`bmsearch`);
  `type="search"` (its ✕ hidden); no placeholder; `autocomplete="off"` on the field and its form; the label and the
  window's title written with U+200D (zero-width joiner) between the letters — people and screen readers read the same
  word, Safari's word match does not find it. A `contenteditable` box was not chosen (no native maxlength,
  select-all, Enter and IME handling; worse for screen readers).
- **Checked:** the attributes only (`qa/suites/s95_bookmark_autofill_v43.py`, Playwright WebKit has no AutoFill);
  the real check is on an iPhone (Vraja Lila).

### Panels: opening and closing — V43
- **Rule** (Vraja Lila 22.10.2026: «при клике панели выдвигаются с хорошей плавностью ease, но при повторном клике
  задвигаются обратно дёргано и мерцают»; earlier msg 5521): a panel closes exactly as smoothly as it opens —
  the same duration (`--ds-dur-slide` 220 ms) and the same ease (`--ds-ease`), one movement, no flash.
- **Bars** (top / bottom): one CSS transition (`transform 220ms ease`) both ways — measured
  symmetric (frames one way, never `display:none` half way).
- **Solid while moving — V44** (Vraja Lila 22.10.2026, msg 6163–6168: while the bottom bar slid, the next verse showed
  through «‹ Back / Forward ›»): a sliding panel (top / bottom bar, «Содержание») is an OPAQUE sheet in every frame —
  it moves only by `transform`; NO `opacity` on the panel or its background (hidden = moved fully off screen). A fade,
  if ever needed, goes on the panel's content only, never on the sheet. Only the dimming behind «Содержание» fades.
  Test: `qa/suites/s96_bars_opaque_while_moving_v44.py`.
- **«Содержание»:** opening `ap-menu-in` (forwards); closing its own `ap-menu-out` played **forwards** with the same
  ease (not the opening in reverse — reversing also reverses the ease: slow start, abrupt end). The panel is removed
  from the page only on its `animationend` (a timer is only a safety net): closing makes the page busy for
  150–250 ms (the history step back), and the old timer, counted from the start of closing, cut the slide to
  25–170 ms — the panel vanished half way. Without a picked row the slide-back starts in the same frame as closing;
  the panel has its own layer (`will-change: transform`). The bottom bar comes back once with the bars' transition.
- **Test:** `qa/suites/s94_panels_close_smooth_v43.py` (frames every ~16 ms; with s65, s66, s86).
