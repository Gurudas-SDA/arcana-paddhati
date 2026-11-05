"use client";

// Highlights and notes (V71, Vraja Lila 04.11 msg 2360/2362: «утверждаю, делаем в книгу»; «в файл только заметки, закладки не будем пока что»;
// the proposal «V70 выделение и заметки», variant A with the corrections 04.11):
//   ap.highlights = {v: 1, items: [Highlight]} — on the device, like ap.bookmarks (lib/bookmarks.ts), at most 2000, a note at most 2000 signs.
// The place is the text itself, not a page: the chapter (+ the subsection it is in), the offsets inside the chapter's
// flat text (only text a reader may mark: see `allowed`), the quote and a few words before / after. When the chapter's
// text changed the place is searched by the quote and its neighbours; not found = «место изменилось» (`lost`),
// the note is kept. The page's DOM is never changed: the colours are drawn with the CSS Custom Highlight API (::highlight(hl-N)),
// as the search does (lib/searchMark.ts).
import { liveLang } from "./i18n";

export const HL_KEY = "ap.highlights";
export const HL_BACKUP_KEY = "ap.highlights.backup";
export const HL_MAX = 2000;
export const HL_NOTE_MAX = 2000;
/** Fired on window after every write (the painter, the list and the markers follow it). */
export const HL_EVENT = "ap:highlights";
/** A toast asked from anywhere: detail = {text, undoLabel?, undo?: () => void, ms?}. */
export const HL_TOAST_EVENT = "ap:hl-toast";
/** The «Заметки» panel gives a chosen file to the layer: detail = {text}. */
export const HL_IMPORT_EVENT = "ap:hl-import";
/** Edit the note of a highlight: detail = {id}. */
export const HL_EDIT_EVENT = "ap:hl-edit";
/** Open the card of a highlight: detail = {id}. */
export const HL_CARD_EVENT = "ap:hl-card";
/** Try to show the pending highlight again (the list asked a place). */
export const HL_REVEAL_EVENT = "ap:hl-reveal";
export const FILE_KIND = "arcana-paddhati-notes";
export const COLORS = 4;
/** The colours' names (the hint and the label for the screen reader), in order. */
export const COLOR_KEYS = ["yellow", "green", "blue", "pink"] as const;
const CONTEXT = 32;

export interface Highlight {
  id: string;
  lang: string;
  section: string;
  /** The subsection (`section[id]`) the highlight starts in. */
  sub?: string;
  /** In the window «Настроение Гурудева»: the number of the quote (0-based) in the opened window. Offsets are inside that quote. */
  mood?: number;
  start: number;
  end: number;
  quote: string;
  before: string;
  after: string;
  color: number;
  note?: string;
  created: number;
  updated: number;
  /** The reader's own place in the list (as a bookmark's `pos`). */
  pos?: number;
  /** The quote was not found any more (the chapter's text changed). */
  lost?: boolean;
  /** Where inside the section the quote stood: a verse line, the word-by-word panel, or the plain text. */
  kind?: "verse" | "poslovno";
}

let mem: Highlight[] = [];

function valid(h: unknown): h is Highlight {
  const x = h as Highlight;
  return !!x && typeof x.id === "string" && typeof x.section === "string" && typeof x.lang === "string" &&
    typeof x.quote === "string" && x.quote.length > 0 && Number.isFinite(x.start) && Number.isFinite(x.end) &&
    Number.isInteger(x.color) && x.color >= 0 && x.color < COLORS;
}

/** The list order: not placed by hand first (book order is the caller's, here newest first), then the placed ones by `pos`. */
export function sortHighlights<T extends Highlight>(items: T[], bookOrder?: (section: string) => number): T[] {
  const placed = (h: Highlight) => typeof h.pos === "number";
  return [...items].sort((a, b) => {
    if (placed(a) !== placed(b)) return placed(a) ? 1 : -1;
    if (placed(a) && placed(b) && a.pos !== b.pos) return (a.pos as number) - (b.pos as number);
    if (bookOrder) {
      const d = bookOrder(a.section) - bookOrder(b.section);
      if (d) return d;
      if (a.start !== b.start) return a.start - b.start;
    }
    return b.created - a.created;
  });
}

export function readHighlights(): Highlight[] {
  let items = mem;
  try {
    const raw = localStorage.getItem(HL_KEY);
    if (raw) {
      const v = JSON.parse(raw) as { v?: number; items?: unknown };
      if (v && v.v === 1 && Array.isArray(v.items)) items = (v.items as unknown[]).filter(valid) as Highlight[];
    }
  } catch {
    // storage unavailable
  }
  return items.map((h) => ({ ...h, lang: liveLang(h.lang) }));
}

/** True when the list was stored (false = no room / private mode: the reader is told, nothing is lost silently). */
export function writeHighlights(items: Highlight[]): boolean {
  const next = items.slice(0, HL_MAX);
  let stored = true;
  try {
    localStorage.setItem(HL_KEY, JSON.stringify({ v: 1, items: next }));
  } catch {
    stored = false;
  }
  mem = next;
  try {
    window.dispatchEvent(new Event(HL_EVENT));
  } catch {
    // no window (server)
  }
  return stored;
}

export function newId(): string {
  try {
    return `h${crypto.randomUUID().replace(/-/g, "").slice(0, 16)}`;
  } catch {
    return `h${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
  }
}

export function toast(text: string, undo?: () => void, ms = 4000, undoLabel?: string) {
  try {
    window.dispatchEvent(new CustomEvent(HL_TOAST_EVENT, { detail: { text, undo, ms, undoLabel } }));
  } catch {
    // no window
  }
}

export function addHighlight(h: Omit<Highlight, "id" | "created" | "updated"> & { id?: string }): Highlight {
  const now = Date.now();
  const item: Highlight = { ...h, id: h.id ?? newId(), created: now, updated: now };
  writeHighlights([item, ...readHighlights()]);
  return item;
}

export function updateHighlight(id: string, patch: Partial<Highlight>) {
  const items = readHighlights();
  if (!items.some((h) => h.id === id)) return;
  writeHighlights(items.map((h) => (h.id === id ? { ...h, ...patch, updated: Date.now() } : h)));
}

/** Remove one highlight and show «Выделение убрано · Отменить». */
export function removeHighlight(id: string, labels: { removed: string; undo: string }) {
  const before = readHighlights();
  if (!before.some((h) => h.id === id)) return;
  writeHighlights(before.filter((h) => h.id !== id));
  toast(labels.removed, () => writeHighlights(before), 4000, labels.undo);
}

/** The list in the reader's own order (same as reorderBookmarks): `ids` are the rows SHOWN, top to bottom. With a filter on, only
 *  those change places among the places they occupied — the others keep their order. Every item then gets its `pos`. */
export function reorderHighlights(ids: string[], currentOrder: string[]) {
  const items = readHighlights();
  const byId = new Map(items.map((h) => [h.id, h]));
  const order = currentOrder.filter((id) => byId.has(id));
  for (const h of items) if (!order.includes(h.id)) order.push(h.id);
  const shown = new Set(ids);
  const slots = order.map((id, i) => (shown.has(id) ? i : -1)).filter((i) => i >= 0);
  const next = [...order];
  slots.forEach((slot, k) => {
    if (ids[k]) next[slot] = ids[k];
  });
  writeHighlights(next.map((id, i) => ({ ...(byId.get(id) as Highlight), pos: i })));
}

// ---------------------------------------------------------------------------------------------- the text of a chapter

/** What is never marked: buttons (the verse's / the mood's controls), tables, pictures and their captions, the printed copy of the mood,
 *  the transcript source line, the program's own windows. */
export const FORBIDDEN =
  "button, table, svg, figcaption, script, style, .sr-only, .mood-panel, .mood-source, [data-hl-skip], [data-hl-ui], input, textarea, select, [aria-hidden=true]";

export interface TextIndex {
  root: Element;
  text: string;
  nodes: { node: Text; start: number; end: number }[];
}

function allowed(n: Text, root: Element, inMood: boolean): boolean {
  const el = n.parentElement;
  if (!el) return false;
  if (el.closest(FORBIDDEN)) return false;
  if (inMood) return true;
  return !!el.closest("article") && !el.closest(".mood-overlay");
}

/** The flat text of `root` that may be marked (hidden stretches count: the word-by-word panel is part of it). */
export function textIndex(root: Element): TextIndex {
  const inMood = !!root.closest(".mood-overlay");
  const nodes: TextIndex["nodes"] = [];
  let text = "";
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode() as Text | null; n; n = w.nextNode() as Text | null) {
    if (!n.data || !allowed(n, root, inMood)) continue;
    nodes.push({ node: n, start: text.length, end: text.length + n.data.length });
    text += n.data;
  }
  return { root, text, nodes };
}

export function rangeAt(idx: TextIndex, s: number, e: number): Range | null {
  if (e <= s || s < 0 || e > idx.text.length) return null;
  const a = idx.nodes.find((x) => s >= x.start && s < x.end);
  const b = idx.nodes.find((x) => e > x.start && e <= x.end);
  if (!a || !b) return null;
  const r = document.createRange();
  r.setStart(a.node, s - a.start);
  r.setEnd(b.node, e - b.start);
  return r;
}

/** The offset in the flat text for a DOM point (a text node + offset, or an element + child index). */
export function offsetOf(idx: TextIndex, node: Node, offset: number): number {
  const p = document.createRange();
  try {
    p.setStart(node, offset);
  } catch {
    return idx.text.length;
  }
  p.collapse(true);
  for (const x of idx.nodes) {
    if (x.node === node) return x.start + Math.min(offset, x.node.data.length);
    const er = document.createRange();
    er.selectNodeContents(x.node);
    const c = er.comparePoint(p.startContainer, p.startOffset);
    if (c < 0) return x.start;
    // inside or on an edge: on the start edge it is this node's start, on the end edge the next node's (the same flat offset)
    if (c === 0 && p.compareBoundaryPoints(Range.START_TO_START, er) === 0) return x.start;
  }
  return idx.text.length;
}

/** Where the highlight is now: its stored offsets if the quote is still there, else the best occurrence of the quote
 *  (the words around it decide), else null («место изменилось»). */
export function locate(text: string, h: Pick<Highlight, "start" | "end" | "quote" | "before" | "after">): [number, number] | null {
  if (text.slice(h.start, h.end) === h.quote) return [h.start, h.end];
  let best: { at: number; score: number } | null = null;
  for (let at = text.indexOf(h.quote); at >= 0; at = text.indexOf(h.quote, at + 1)) {
    let score = 0;
    const bef = text.slice(Math.max(0, at - h.before.length), at);
    for (let i = 1; i <= Math.min(bef.length, h.before.length); i++) {
      if (bef[bef.length - i] === h.before[h.before.length - i]) score++;
      else break;
    }
    const aft = text.slice(at + h.quote.length, at + h.quote.length + h.after.length);
    for (let i = 0; i < Math.min(aft.length, h.after.length); i++) {
      if (aft[i] === h.after[i]) score++;
      else break;
    }
    if (!best || score > best.score || (score === best.score && Math.abs(at - h.start) < Math.abs(best.at - h.start))) best = { at, score };
  }
  return best ? [best.at, best.at + h.quote.length] : null;
}

/** The part of `text` between s and e as a highlight's place fields (trimmed of white space at both ends). */
export function placeFields(text: string, s: number, e: number): Pick<Highlight, "start" | "end" | "quote" | "before" | "after"> | null {
  while (s < e && /\s/.test(text[s])) s++;
  while (e > s && /\s/.test(text[e - 1])) e--;
  if (e <= s) return null;
  return {
    start: s,
    end: e,
    quote: text.slice(s, e),
    before: text.slice(Math.max(0, s - CONTEXT), s),
    after: text.slice(e, e + CONTEXT),
  };
}

// ---------------------------------------------------------------------------------------------- the file

export function fileName(d = new Date()): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `Арчана-паддхати — заметки ${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}.json`;
}

/** The file holds ONLY the highlights and notes — never bookmarks (Vraja Lila msg 2362). */
export function buildFile(items: Highlight[]): string {
  return JSON.stringify({ app: "arcana-paddhati", kind: FILE_KIND, v: 1, saved: new Date().toISOString(), items }, null, 1);
}

export interface Import {
  ok: boolean;
  /** valid items of the file */
  items: Highlight[];
  skipped: number;
}

export function parseFile(text: string): Import {
  try {
    const d = JSON.parse(text) as { kind?: string; v?: number; items?: unknown };
    if (!d || d.kind !== FILE_KIND || typeof d.v !== "number" || d.v > 1 || !Array.isArray(d.items)) return { ok: false, items: [], skipped: 0 };
    const items: Highlight[] = [];
    let skipped = 0;
    for (const x of d.items as unknown[]) {
      if (valid(x)) {
        const h = x as Highlight;
        items.push({
          id: h.id, lang: h.lang, section: h.section, sub: typeof h.sub === "string" ? h.sub : undefined, mood: Number.isInteger(h.mood) ? h.mood : undefined,
          start: h.start, end: h.end, quote: h.quote, before: typeof h.before === "string" ? h.before : "", after: typeof h.after === "string" ? h.after : "",
          color: h.color, note: typeof h.note === "string" && h.note ? h.note.slice(0, HL_NOTE_MAX) : undefined,
          created: Number.isFinite(h.created) ? h.created : Date.now(), updated: Number.isFinite(h.updated) ? h.updated : Date.now(),
          pos: Number.isFinite(h.pos) ? h.pos : undefined, lost: undefined, kind: h.kind === "verse" || h.kind === "poslovno" ? h.kind : undefined,
        });
      } else skipped++;
    }
    return { ok: true, items, skipped };
  } catch {
    return { ok: false, items: [], skipped: 0 };
  }
}

const sameSpot = (a: Highlight, b: Highlight) =>
  a.lang === b.lang && a.section === b.section && a.start === b.start && a.end === b.end && a.quote === b.quote;
const sameAll = (a: Highlight, b: Highlight) => sameSpot(a, b) && a.color === b.color && (a.note ?? "") === (b.note ?? "");

export interface Preview {
  total: number;
  /** added by «Добавить» */
  add: Highlight[];
  fresh: number;
  dup: number;
  /** same place, other colour / text: both are kept by default */
  conflict: number;
  skipped: number;
}

/** What «Добавить» would do: nothing is written. A note is "already there" when the id is the same or everything is the same. */
export function previewImport(existing: Highlight[], file: Import): Preview {
  const add: Highlight[] = [];
  let fresh = 0;
  let dup = 0;
  let conflict = 0;
  const ids = new Set(existing.map((h) => h.id));
  for (const h of file.items) {
    if (ids.has(h.id) || existing.some((x) => sameAll(x, h))) {
      dup++;
      continue;
    }
    if (existing.some((x) => sameSpot(x, h))) conflict++;
    else fresh++;
    add.push(h);
  }
  return { total: file.items.length, add, fresh, dup, conflict, skipped: file.skipped };
}

/** Add: nothing existing is removed. Returns how many were added (the limit is told, not cut silently) and the list before. */
export function applyAdd(add: Highlight[]): { added: number; before: Highlight[]; stored: boolean; room: number } {
  const before = readHighlights();
  const room = Math.max(0, HL_MAX - before.length);
  const take = add.slice(0, room);
  if (!take.length) return { added: 0, before, stored: true, room };
  const stored = writeHighlights([...before, ...take]);
  if (!stored) writeHighlights(before);
  return { added: stored ? take.length : 0, before, stored, room };
}

/** Replace all (two confirmations in the UI): the old list is kept in `ap.highlights.backup` until the toast is over. */
export function applyReplace(file: Import): { before: Highlight[]; stored: boolean } {
  const before = readHighlights();
  try {
    localStorage.setItem(HL_BACKUP_KEY, JSON.stringify({ v: 1, items: before }));
  } catch {
    // no room for the copy: the undo still works from memory
  }
  const stored = writeHighlights(file.items);
  if (!stored) writeHighlights(before);
  return { before, stored };
}

export function dropBackup() {
  try {
    localStorage.removeItem(HL_BACKUP_KEY);
  } catch {
    // ignore
  }
}

// ---------------------------------------------------------------------------------------------- the place to show next

let pendingReveal: { id: string; until: number } | null = null;

/** The list asked for this highlight: the layer scrolls to it and lights it once its chapter is shown. */
export function setPendingReveal(id: string) {
  pendingReveal = { id, until: Date.now() + 9000 };
  try {
    window.dispatchEvent(new Event(HL_REVEAL_EVENT));
  } catch {
    // no window
  }
}

export function takePendingReveal(): string | null {
  if (!pendingReveal) return null;
  if (Date.now() > pendingReveal.until) {
    pendingReveal = null;
    return null;
  }
  return pendingReveal.id;
}

export function clearPendingReveal() {
  pendingReveal = null;
}

/** The date at the bottom of a card (bookmarks and notes), in every language: DD.MM.YYYY (Vraja Lila msg 7428: 01.11.2026). */
export function cardDate(ms: number): string {
  const d = new Date(ms);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()}`;
}
