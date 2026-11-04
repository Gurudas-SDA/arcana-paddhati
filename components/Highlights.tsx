"use client";

/**
 * Highlights and notes in the text (V71, Vraja Lila 04.11 msg 2360/2362; variant A of «V70 выделение и заметки» with the corrections 04.11).
 * One layer for the whole reader (mounted by AppShell):
 *  - paints the saved highlights with the CSS Custom Highlight API (::highlight(hl-0…3)) — the page's DOM is not changed, so the
 *    bookmarks, the search mark, «Продолжить» and the reading place (they count paragraphs) are untouched;
 *  - a selection in the text (finger handles / mouse) shows the menu: 4 colours · «Заметка» · «Копировать»;
 *  - a tap on a painted stretch (or on its note sign) opens the card: colours, pencil, copy, bin;
 *  - the note editor, the toast «Выделение убрано · Отменить», the file load preview;
 *  - inside the window «Настроение Гурудева» the menu, the card and the editor are drawn INSIDE the window (a tap on them
 *    outside it would be taken for a tap outside the window and close it).
 * What cannot be marked: lib/highlights.ts FORBIDDEN (buttons, tables, pictures, the transcript source line, the printed copy of the mood).
 */
import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { parsePath, t, type UiDict } from "@/lib/i18n";
import { stripBasePath } from "@/lib/basePath";
import { SEARCH_SCROLL_ATTR } from "@/lib/searchMark";
import { main as mainEl } from "@/lib/navHistory";
import WindowClose from "@/components/WindowClose";
import {
  COLORS,
  COLOR_KEYS,
  HL_CARD_EVENT,
  HL_EDIT_EVENT,
  HL_EVENT,
  HL_IMPORT_EVENT,
  HL_NOTE_MAX,
  HL_REVEAL_EVENT,
  HL_TOAST_EVENT,
  addHighlight,
  applyAdd,
  applyReplace,
  clearPendingReveal,
  dropBackup,
  locate,
  offsetOf,
  parseFile,
  placeFields,
  previewImport,
  rangeAt,
  readHighlights,
  removeHighlight,
  takePendingReveal,
  textIndex,
  toast,
  updateHighlight,
  writeHighlights,
  type Highlight,
  type Import,
  type TextIndex,
} from "@/lib/highlights";

type HlRegistry = { set: (n: string, h: unknown) => void; delete: (n: string) => void; get?: (n: string) => unknown };
function registry(): HlRegistry | null {
  const c = (globalThis as unknown as { CSS?: { highlights?: unknown } }).CSS;
  const H = (globalThis as unknown as { Highlight?: unknown }).Highlight;
  return c?.highlights && H ? (c.highlights as HlRegistry) : null;
}
function makeHighlight(ranges: Range[]): unknown {
  const H = (globalThis as unknown as { Highlight: new (...r: Range[]) => unknown }).Highlight;
  return new H(...ranges);
}

interface SelInfo {
  section: string;
  sub?: string;
  mood?: number;
  kind?: "verse" | "poslovno";
  start: number;
  end: number;
  quote: string;
  before: string;
  after: string;
  /** the last line of the selection (client coordinates when it was taken) */
  rect: { left: number; right: number; top: number; bottom: number };
  inMood: HTMLElement | null;
}

/** Where a highlight is painted now: the root it was found in and its range (used by taps and the markers). */
interface Resolved {
  h: Highlight;
  root: Element;
  range: Range;
}

const COLOR_NAME_KEY = (i: number) => `hl.color.${COLOR_KEYS[i]}`;

function currentSection(): string | undefined {
  return parsePath(stripBasePath(window.location.pathname) || "/").sectionId ?? undefined;
}

/** The chapters shown now (one in «Листать», several in «Прокручивать») and the opened mood window's quotes. */
function chapterRoots(): { section: string; root: Element; mood?: number }[] {
  const out: { section: string; root: Element; mood?: number }[] = [];
  const m = document.querySelector(".app-main");
  if (!m) return out;
  const cs = [...m.querySelectorAll("[data-book-section]")];
  if (cs.length) {
    for (const c of cs) out.push({ section: c.getAttribute("data-book-section") as string, root: c });
  } else {
    const sec = currentSection();
    if (sec) out.push({ section: sec, root: m });
  }
  const sec = currentSection();
  if (sec) {
    [...document.querySelectorAll(".mood-overlay .mood-quote")].forEach((q, i) => out.push({ section: sec, root: q, mood: i }));
  }
  return out;
}

function elementOf(n: Node | null): Element | null {
  return !n ? null : n instanceof Element ? n : n.parentElement;
}

function takeSelection(): SelInfo | null {
  const s = window.getSelection();
  if (!s || s.rangeCount === 0 || s.isCollapsed) return null;
  const r = s.getRangeAt(0);
  const a = elementOf(r.startContainer);
  const b = elementOf(r.endContainer);
  if (!a || !b) return null;
  if (a.closest("[data-hl-ui],input,textarea,[contenteditable]") || b.closest("[data-hl-ui],input,textarea,[contenteditable]")) return null;
  let root: Element | null;
  let mood: number | undefined;
  let section = currentSection();
  const q = a.closest(".mood-overlay .mood-quote");
  if (q) {
    if (!q.contains(b)) return null;
    root = q;
    mood = [...document.querySelectorAll(".mood-overlay .mood-quote")].indexOf(q);
  } else {
    if (a.closest(".mood-overlay") || b.closest(".mood-overlay")) return null;
    const m = a.closest(".app-main");
    if (!m) return null;
    root = a.closest("[data-book-section]");
    if (root) {
      if (!root.contains(b)) return null;
      section = root.getAttribute("data-book-section") ?? section;
    } else {
      if (m.querySelector("[data-book-section]")) return null;
      root = m;
    }
  }
  if (!section || !root) return null;
  const idx = textIndex(root);
  const f = placeFields(idx.text, offsetOf(idx, r.startContainer, r.startOffset), offsetOf(idx, r.endContainer, r.endOffset));
  if (!f) return null;
  const rects = r.getClientRects();
  const last = rects.length ? rects[rects.length - 1] : r.getBoundingClientRect();
  const first = rects.length ? rects[0] : last;
  return {
    section,
    sub: mood === undefined ? a.closest("section[id]")?.id || undefined : undefined,
    mood,
    kind: a.closest(".verse-wbw") ? "poslovno" : undefined,
    ...f,
    rect: { left: Math.min(first.left, last.left), right: last.right, top: first.top, bottom: last.bottom },
    inMood: mood === undefined ? null : (a.closest(".mood-overlay") as HTMLElement | null),
  };
}

interface Props {
  ui: UiDict;
  lang: string;
}

// tehniskais slieksnis Lipikāra, nav S noteikums: a quote longer than ~2 lines is not shown in the note window (V76, Vraja Lila msg 7553 p.2)
const HL_QUOTE_SHOW_MAX = 110;

export default function HighlightsLayer({ ui, lang }: Props) {
  const [items, setItems] = useState<Highlight[]>([]);
  /** V72 (Vraja Lila msg 2406–2407): the visible part of the screen while the soft keyboard is up (visualViewport); null = whole screen. */
  const [vv, setVv] = useState<{ top: number; height: number } | null>(null);
  const [menu, setMenu] = useState<{ sel: SelInfo; x: number; y: number } | null>(null);
  const [editor, setEditor] = useState<{ id?: string; sel?: SelInfo; color: number; note: string; quote: string; inMood: HTMLElement | null } | null>(null);
  const [card, setCard] = useState<{ id: string; x: number; y: number; inMood: HTMLElement | null } | null>(null);
  const [tst, setTst] = useState<{ text: string; undo?: () => void; undoLabel?: string; key: number } | null>(null);
  const [imp, setImp] = useState<{ file: Import; step: "preview" | "replace" } | null>(null);
  const [impError, setImpError] = useState(false);
  const [markers, setMarkers] = useState<{ id: string; x: number; y: number }[]>([]);
  const resolved = useRef<Resolved[]>([]);
  const itemsRef = useRef<Highlight[]>([]);
  const menuRef = useRef<HTMLDivElement>(null);
  const tstTimer = useRef<number | undefined>(undefined);
  const hasApi = useRef(true);

  useEffect(() => {
    itemsRef.current = items;
  }, [items]);

  // --- the list follows the storage
  useEffect(() => {
    const read = () => setItems(readHighlights());
    read();
    window.addEventListener(HL_EVENT, read);
    window.addEventListener("storage", read);
    return () => {
      window.removeEventListener(HL_EVENT, read);
      window.removeEventListener("storage", read);
    };
  }, []);

  // --- painting
  const paint = useCallback(() => {
    const reg = registry();
    hasApi.current = !!reg;
    const list = itemsRef.current;
    // No highlights at all: nothing to find or draw (the reader pays nothing for the feature until he uses it).
    if (!list.length) {
      if (resolved.current.length && reg) for (let i = 0; i < COLORS; i++) reg.delete(`hl-${i}`);
      if (resolved.current.length) document.querySelectorAll("[data-hl-dot]").forEach((b) => b.removeAttribute("data-hl-dot"));
      resolved.current = [];
      setMarkers((prev) => (prev.length ? [] : prev));
      return;
    }
    const res: Resolved[] = [];
    const lostNow = new Map<string, boolean>();
    const byColor: Range[][] = Array.from({ length: COLORS }, () => []);
    const indexes = new Map<Element, TextIndex>();
    for (const c of chapterRoots()) {
      const mine = list.filter((h) => h.section === c.section && h.lang === lang && (h.mood ?? undefined) === c.mood);
      if (!mine.length) continue;
      const idx = indexes.get(c.root) ?? textIndex(c.root);
      indexes.set(c.root, idx);
      for (const h of mine) {
        const at = locate(idx.text, h);
        lostNow.set(h.id, !at);
        if (!at) continue;
        const r = rangeAt(idx, at[0], at[1]);
        if (!r) {
          lostNow.set(h.id, true);
          continue;
        }
        byColor[h.color].push(r);
        res.push({ h, root: c.root, range: r });
      }
    }
    resolved.current = res;
    if (reg) {
      for (let i = 0; i < COLORS; i++) {
        if (byColor[i].length) reg.set(`hl-${i}`, makeHighlight(byColor[i]));
        else reg.delete(`hl-${i}`);
      }
    }
    // the «Пословно» button gets a dot while its panel holds a highlight
    document.querySelectorAll("[data-hl-dot]").forEach((b) => b.removeAttribute("data-hl-dot"));
    for (const r of res) {
      const panel = elementOf(r.range.startContainer)?.closest(".verse-wbw");
      if (panel?.id) document.querySelector(`[aria-controls="${CSS.escape(panel.id)}"]`)?.setAttribute("data-hl-dot", "");
    }
    // «место изменилось»: remembered in the stored item (only when it differs)
    const changed = list.filter((h) => lostNow.has(h.id) && !!h.lost !== lostNow.get(h.id));
    if (changed.length) {
      writeHighlights(list.map((h) => (lostNow.has(h.id) ? { ...h, lost: lostNow.get(h.id) || undefined } : h)));
    }
    drawMarkers();
    revealPending();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang]);

  const drawMarkers = () => {
    const out: { id: string; x: number; y: number }[] = [];
    const m = mainEl();
    const vh = window.innerHeight;
    for (const r of resolved.current) {
      if (!r.h.note) continue;
      const rs = r.range.getClientRects();
      if (!rs.length) continue;
      const last = rs[rs.length - 1];
      if (last.bottom < 0 || last.top > vh) continue;
      if (m && !r.root.closest(".mood-overlay")) {
        const mr = m.getBoundingClientRect();
        if (last.bottom < mr.top || last.top > mr.bottom) continue;
      }
      out.push({ id: r.h.id, x: last.right, y: last.top + last.height / 2 });
    }
    setMarkers((prev) => (prev.length === out.length && prev.every((p, i) => p.id === out[i].id && Math.abs(p.x - out[i].x) < 1 && Math.abs(p.y - out[i].y) < 1) ? prev : out));
  };

  const revealPending = () => {
    const id = takePendingReveal();
    if (!id) return;
    const r = resolved.current.find((x) => x.h.id === id);
    if (!r) return;
    clearPendingReveal();
    const m = mainEl();
    const rect = r.range.getBoundingClientRect();
    const reg = registry();
    if (reg) {
      reg.set("hl-flash", makeHighlight([r.range]));
      window.setTimeout(() => reg.delete("hl-flash"), 1800);
    }
    if (m && !r.root.closest(".mood-overlay")) {
      const mr = m.getBoundingClientRect();
      if (rect.top < mr.top + 56 || rect.bottom > mr.bottom - 64) {
        document.documentElement.setAttribute(SEARCH_SCROLL_ATTR, "");
        m.scrollTop += rect.top - mr.top - mr.height * 0.35;
        window.setTimeout(() => document.documentElement.removeAttribute(SEARCH_SCROLL_ATTR), 1500);
      }
    }
    drawMarkers();
  };

  // repaint: the list changed, the chapter / language changed, the page's text was drawn
  useEffect(() => {
    paint();
  }, [items, paint]);
  useEffect(() => {
    let timer = 0;
    const later = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(paint, 180);
    };
    const mo = new MutationObserver(later);
    const m = document.querySelector(".app-main");
    if (m) mo.observe(m, { childList: true, subtree: true });
    const bo = new MutationObserver(later);
    bo.observe(document.body, { childList: true });
    window.addEventListener(HL_REVEAL_EVENT, later);
    window.addEventListener("popstate", later);
    window.addEventListener("resize", later);
    const poll = window.setInterval(() => {
      if (takePendingReveal()) later();
    }, 400);
    return () => {
      window.clearTimeout(timer);
      window.clearInterval(poll);
      mo.disconnect();
      bo.disconnect();
      window.removeEventListener(HL_REVEAL_EVENT, later);
      window.removeEventListener("popstate", later);
      window.removeEventListener("resize", later);
    };
  }, [paint]);
  // markers follow the scroll
  useEffect(() => {
    let raf = 0;
    const on = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(drawMarkers);
    };
    const m = document.querySelector(".app-main");
    m?.addEventListener("scroll", on, { passive: true });
    window.addEventListener("scroll", on, { passive: true });
    return () => {
      cancelAnimationFrame(raf);
      m?.removeEventListener("scroll", on);
      window.removeEventListener("scroll", on);
    };
  }, []);

  // --- the menu on a selection
  useEffect(() => {
    let timer = 0;
    const check = () => {
      const sel = takeSelection();
      if (!sel) {
        setMenu(null);
        return;
      }
      setCard(null);
      setMenu({ sel, x: 0, y: 0 });
    };
    const on = () => {
      window.clearTimeout(timer);
      const s = window.getSelection();
      if (!s || s.isCollapsed) {
        timer = window.setTimeout(() => setMenu(null), 60);
        return;
      }
      timer = window.setTimeout(check, 220);
    };
    document.addEventListener("selectionchange", on);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener("selectionchange", on);
    };
  }, []);

  // place the menu: below the selection on a phone (the system's own bar is above it), above it on a computer
  useLayoutEffect(() => {
    const el = menuRef.current;
    if (!menu || !el) return;
    const w = el.offsetWidth;
    const h = el.offsetHeight;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const phone = vw < 700 || window.matchMedia("(pointer: coarse)").matches;
    const r = menu.sel.rect;
    let top = phone ? r.bottom + 14 : r.top - h - 8;
    if (!phone && top < 8) top = r.bottom + 8;
    if (phone && top + h > vh - 8) top = Math.max(8, r.top - h - 14);
    top = Math.max(8, Math.min(top, vh - h - 8));
    let left = phone ? (vw - w) / 2 : r.left;
    left = Math.max(8, Math.min(left, vw - w - 8));
    if (Math.abs(left - menu.x) > 0.5 || Math.abs(top - menu.y) > 0.5) setMenu({ sel: menu.sel, x: left, y: top });
  }, [menu]);

  const closeMenu = () => {
    setMenu(null);
    try {
      window.getSelection()?.removeAllRanges();
    } catch {
      // no selection API
    }
  };
  const create = (sel: SelInfo, color: number, note?: string) => {
    addHighlight({
      lang, section: sel.section, sub: sel.sub, mood: sel.mood, kind: sel.kind,
      start: sel.start, end: sel.end, quote: sel.quote, before: sel.before, after: sel.after, color, note: note || undefined,
    });
  };
  const copyText = async (text: string) => {
    let done = false;
    try {
      await navigator.clipboard.writeText(text);
      done = true;
    } catch {
      try {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("data-hl-skip", "");
        document.body.appendChild(ta);
        ta.select();
        done = document.execCommand("copy");
        ta.remove();
      } catch {
        // no clipboard
      }
    }
    if (done) toast(t(ui, "hl.copied"), undefined, 1800);
  };

  // --- a tap on a painted stretch opens its card (the bars do not toggle: the tap is taken before the reader's handler)
  useEffect(() => {
    let down: { x: number; y: number; at: number } | null = null;
    const onDown = (e: PointerEvent) => {
      down = e.isPrimary ? { x: e.clientX, y: e.clientY, at: performance.now() } : null;
    };
    const hit = (x: number, y: number): Resolved | null => {
      let node: Node | null = null;
      let off = 0;
      const d = document as Document & { caretPositionFromPoint?: (x: number, y: number) => { offsetNode: Node; offset: number } | null; caretRangeFromPoint?: (x: number, y: number) => Range | null };
      if (d.caretPositionFromPoint) {
        const p = d.caretPositionFromPoint(x, y);
        if (p) { node = p.offsetNode; off = p.offset; }
      } else if (d.caretRangeFromPoint) {
        const r = d.caretRangeFromPoint(x, y);
        if (r) { node = r.startContainer; off = r.startOffset; }
      }
      if (!node) return null;
      const cands = resolved.current.filter((r) => r.root.contains(node) && !r.root.closest("[data-hl-ui]"));
      let best: Resolved | null = null;
      for (const r of cands) {
        try {
          const inside = r.range.comparePoint(node, off) === 0;
          if (!inside) continue;
        } catch {
          continue;
        }
        // is the point really over the stretch (not the empty end of a line)?
        const rs = [...r.range.getClientRects()];
        if (!rs.some((q) => x >= q.left - 2 && x <= q.right + 2 && y >= q.top - 2 && y <= q.bottom + 2)) continue;
        if (!best || r.h.updated > best.h.updated) best = r;
      }
      return best;
    };
    const onUp = (e: PointerEvent) => {
      const s = down;
      down = null;
      if (!s || !e.isPrimary) return;
      if (Math.hypot(e.clientX - s.x, e.clientY - s.y) > 10 || performance.now() - s.at > 600) return;
      const sel = window.getSelection();
      if (sel && !sel.isCollapsed) return;
      const tgt = e.target as Element | null;
      if (!tgt || tgt.closest("[data-hl-ui]")) return;
      // links, buttons and the numbered rows keep their own function (a note sign opens the card for the rows)
      if (tgt.closest("a,button,[role=button],input,textarea,.hs-row,.hs-img,table")) return;
      const r = hit(e.clientX, e.clientY);
      if (!r) return;
      e.stopPropagation();
      e.preventDefault();
      suppressClickUntil.current = performance.now() + 400;
      setMenu(null);
      setCard({ id: r.h.id, x: e.clientX, y: e.clientY, inMood: r.root.closest(".mood-overlay") as HTMLElement | null });
    };
    const swallowClick = (e: MouseEvent) => {
      if (suppressClickUntil.current > performance.now()) {
        e.stopPropagation();
        e.preventDefault();
      }
    };
    document.addEventListener("pointerdown", onDown, true);
    document.addEventListener("pointerup", onUp, true);
    document.addEventListener("click", swallowClick, true);
    return () => {
      document.removeEventListener("pointerdown", onDown, true);
      document.removeEventListener("pointerup", onUp, true);
        document.removeEventListener("click", swallowClick, true);
    };
  }, []);
  const suppressClickUntil = useRef(0);

  // --- events from the list
  useEffect(() => {
    const onEdit = (e: Event) => {
      const id = (e as CustomEvent<{ id: string }>).detail?.id;
      const h = itemsRef.current.find((x) => x.id === id);
      if (h) setEditor({ id: h.id, color: h.color, note: h.note ?? "", quote: h.quote, inMood: null });
    };
    const onCard = (e: Event) => {
      const id = (e as CustomEvent<{ id: string }>).detail?.id;
      const r = resolved.current.find((x) => x.h.id === id);
      const rs = r ? r.range.getClientRects() : null;
      const q = rs && rs.length ? rs[0] : null;
      if (r && q) setCard({ id: r.h.id, x: q.left, y: q.bottom, inMood: r.root.closest(".mood-overlay") as HTMLElement | null });
    };
    const onToast = (e: Event) => {
      const d = (e as CustomEvent<{ text: string; undo?: () => void; ms?: number; undoLabel?: string }>).detail;
      if (!d) return;
      window.clearTimeout(tstTimer.current);
      setTst({ text: d.text, undo: d.undo, undoLabel: d.undoLabel, key: Date.now() });
      tstTimer.current = window.setTimeout(() => setTst(null), d.ms ?? 4000);
    };
    const onImport = (e: Event) => {
      const text = (e as CustomEvent<{ text: string }>).detail?.text ?? "";
      const f = parseFile(text);
      if (!f.ok) {
        setImp(null);
        setImpError(true);
        return;
      }
      setImpError(false);
      setImp({ file: f, step: "preview" });
    };
    window.addEventListener(HL_EDIT_EVENT, onEdit);
    window.addEventListener(HL_CARD_EVENT, onCard);
    window.addEventListener(HL_TOAST_EVENT, onToast);
    window.addEventListener(HL_IMPORT_EVENT, onImport);
    return () => {
      window.removeEventListener(HL_EDIT_EVENT, onEdit);
      window.removeEventListener(HL_CARD_EVENT, onCard);
      window.removeEventListener(HL_TOAST_EVENT, onToast);
      window.removeEventListener(HL_IMPORT_EVENT, onImport);
      window.clearTimeout(tstTimer.current);
    };
  }, []);

  // Esc closes what is open here
  useEffect(() => {
    if (!menu && !card && !editor && !imp && !impError) return;
    const on = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (editor || imp || impError) {
        e.stopPropagation();
        setEditor(null);
        setImp(null);
        setImpError(false);
      } else if (card) setCard(null);
      else closeMenu();
    };
    window.addEventListener("keydown", on, true);
    return () => window.removeEventListener("keydown", on, true);
  }, [menu, card, editor, imp, impError]);

  const labels = { removed: t(ui, "hl.removed"), undo: t(ui, "bookmark.undo") };
  const portalTo = (node: React.ReactNode, mood: HTMLElement | null) => createPortal(node, mood ?? document.body);
  const colorName = (i: number) => t(ui, COLOR_NAME_KEY(i));
  const cardItem = card ? items.find((h) => h.id === card.id) : undefined;

  const colorButtons = ({ current, onPick, kind }: { current?: number; onPick: (i: number) => void; kind: string }) => (
    <div className="hl-colors" role="group">
      {Array.from({ length: COLORS }, (_, i) => (
        <button
          key={i}
          type="button"
          className="hl-color"
          data-hl-color={i}
          data-hl-color-kind={kind}
          data-current={current === i ? "" : undefined}
          aria-label={colorName(i)}
          aria-pressed={current === undefined ? undefined : current === i}
          title={colorName(i)}
          onClick={() => onPick(i)}
        >
          <span className="hl-dot" style={{ background: `var(--hl-${i + 1}-tone)` }} />
        </button>
      ))}
    </div>
  );
  const keepSelection = (e: React.SyntheticEvent) => e.preventDefault();
  const iconNote = (
    <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 5h16v11H9l-5 4z" /><path d="M8 9h8M8 12h5" />
    </svg>
  );
  const iconCopy = (
    <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V6a2 2 0 0 1 2-2h8" />
    </svg>
  );
  const iconEdit = (
    <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z" /><path d="M14 6l3 3" />
    </svg>
  );
  const iconBin = (
    <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" />
    </svg>
  );

  // --- the editor's save
  const saveEditor = () => {
    const e = editor;
    if (!e) return;
    const note = e.note.trim().slice(0, HL_NOTE_MAX);
    if (e.id) updateHighlight(e.id, { note: note || undefined, color: e.color });
    else if (e.sel) create(e.sel, e.color, note);
    setEditor(null);
    setMenu(null);
    try {
      window.getSelection()?.removeAllRanges();
    } catch {
      // ignore
    }
  };

  const importPreview = useMemo(() => (imp ? previewImport(readHighlights(), imp.file) : null), [imp, items]);

  const doAdd = () => {
    if (!imp || !importPreview) return;
    const r = applyAdd(importPreview.add);
    setImp(null);
    if (!r.stored) {
      toast(t(ui, "notes.import.nostore"), undefined, 5000);
      return;
    }
    if (r.added < importPreview.add.length) toast(t(ui, "notes.import.limit", { n: String(r.added) }), undefined, 6000);
    else toast(t(ui, "notes.import.added", { n: String(r.added) }), () => writeHighlights(r.before), 8000, t(ui, "bookmark.undo"));
  };
  const doReplace = () => {
    if (!imp) return;
    const r = applyReplace(imp.file);
    setImp(null);
    if (!r.stored) {
      toast(t(ui, "notes.import.nostore"), undefined, 5000);
      return;
    }
    toast(t(ui, "notes.replaced"), () => { writeHighlights(r.before); dropBackup(); }, 10000, t(ui, "bookmark.undo"));
    window.setTimeout(dropBackup, 10500);
  };

  const editorOpen = !!editor;
  useEffect(() => {
    if (!editorOpen) { setVv(null); return; }
    const v = window.visualViewport;
    if (!v) return;
    const read = () => {
      const keyboard = window.innerHeight - v.height - v.offsetTop > 80;
      setVv(keyboard ? { top: v.offsetTop, height: v.height } : null);
    };
    read();
    v.addEventListener("resize", read);
    v.addEventListener("scroll", read);
    return () => { v.removeEventListener("resize", read); v.removeEventListener("scroll", read); };
  }, [editorOpen]);

  // V76 (Vraja Lila msg 7553 p.1): the page under an open window does not scroll
  const lockOpen = !!editor || !!card || !!imp || impError;
  useEffect(() => {
    if (!lockOpen) return;
    const h = document.documentElement, b = document.body;
    const prev = [h.style.overflow, b.style.overflow];
    h.style.overflow = "hidden"; b.style.overflow = "hidden";
    // React's own onWheel/onTouchMove are passive: native non-passive listeners, so preventDefault really stops the page behind (iOS too)
    const stop = (e: Event) => { if (!(e.target as HTMLElement | null)?.closest?.("[role=dialog], textarea")) e.preventDefault(); };
    document.addEventListener("wheel", stop, { passive: false });
    document.addEventListener("touchmove", stop, { passive: false });
    return () => {
      h.style.overflow = prev[0]; b.style.overflow = prev[1];
      document.removeEventListener("wheel", stop);
      document.removeEventListener("touchmove", stop);
    };
  }, [lockOpen]);

  const modal = (inner: React.ReactNode, onClose: () => void, mood: HTMLElement | null, kind: string) =>
    portalTo(
      <div data-no-reader-tap="" data-hl-ui="" data-hl-modal={kind} className="bookmark-name-modal fixed inset-0 z-[100]" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
        <div className="bookmark-name-backdrop absolute inset-0" aria-hidden="true" onClick={onClose} />
        <div className={`absolute inset-0 flex justify-center overflow-y-auto overscroll-contain pointer-events-none ${kind === "editor" && vv ? "items-start p-2" : "items-center p-4"}`}
          style={kind === "editor" && vv ? { top: vv.top, bottom: "auto", height: vv.height } : undefined}>
          <div role="dialog" aria-modal="true" className="window-card window-card-small bg-white w-full hl-modal-card pointer-events-auto my-auto" data-hl-ui=""
            style={kind === "editor" && vv ? { maxHeight: "none" } : undefined}>
            <WindowClose onClick={onClose} label={t(ui, "reader.close")} />
            {inner}
          </div>
        </div>
      </div>,
      mood,
    );

  return (
    <>
      {menu &&
        portalTo(
          <div
            ref={menuRef}
            data-hl-ui=""
            data-hl-menu=""
            data-no-reader-tap=""
            role="toolbar"
            className="hl-menu"
            style={{ left: menu.x, top: menu.y, visibility: menu.y ? "visible" : "hidden" }}
            onPointerDown={keepSelection}
            onMouseDown={keepSelection}
          >
            {colorButtons({ kind: "menu", onPick: (i) => { create(menu.sel, i); closeMenu(); } })}
            <div className="hl-actions">
              <button
                type="button"
                className="hl-action"
                data-hl-note=""
                onClick={() => {
                  setEditor({ sel: menu.sel, color: 0, note: "", quote: menu.sel.quote, inMood: menu.sel.inMood });
                  setMenu(null);
                }}
              >
                {iconNote}
                <span>{t(ui, "hl.note")}</span>
              </button>
              <button type="button" className="hl-action" data-hl-copy="" onClick={() => { void copyText(menu.sel.quote); closeMenu(); }}>
                {iconCopy}
                <span>{t(ui, "hl.copy")}</span>
              </button>
            </div>
          </div>,
          menu.sel.inMood,
        )}

      {card && cardItem &&
        portalTo(
          <>
            <div data-hl-ui="" className="fixed inset-0 z-[90]" onClick={() => setCard(null)} />
            <div
              data-hl-ui=""
              data-hl-card=""
              data-no-reader-tap=""
              role="dialog"
              aria-label={t(ui, "hl.note")}
              className="hl-menu hl-card"
              style={{ top: Math.max(8, Math.min(card.y + 12, window.innerHeight - 240)) }}
            >
              {colorButtons({ kind: "card", current: cardItem.color, onPick: (i) => updateHighlight(cardItem.id, { color: i }) })}
              <p className="hl-card-note hl-card-note-y" data-hl-card-note="">{cardItem.note || t(ui, "hl.card.noNote")}</p>
              <div className="hl-actions hl-actions-icons">
                <button type="button" className="hl-icon" data-hl-card-edit="" aria-label={t(ui, "hl.edit")} title={t(ui, "hl.edit")}
                  onClick={() => { setEditor({ id: cardItem.id, color: cardItem.color, note: cardItem.note ?? "", quote: cardItem.quote, inMood: card.inMood }); setCard(null); }}>
                  {iconEdit}
                </button>
                <button type="button" className="hl-icon" data-hl-card-copy="" aria-label={t(ui, "hl.copy")} title={t(ui, "hl.copy")}
                  onClick={() => { void copyText(cardItem.note ? `${cardItem.quote}\n— ${cardItem.note}` : cardItem.quote); setCard(null); }}>
                  {iconCopy}
                </button>
                <button type="button" className="hl-icon" data-hl-card-delete="" aria-label={t(ui, "hl.delete")} title={t(ui, "hl.delete")}
                  onClick={() => { removeHighlight(cardItem.id, labels); setCard(null); }}>
                  {iconBin}
                </button>
              </div>
            </div>
          </>,
          card.inMood,
        )}

      {markers.map((m) => (
        <button
          key={m.id}
          type="button"
          data-hl-ui=""
          data-hl-marker=""
          className="hl-marker"
          style={{ left: m.x + 2, top: m.y - 12 }}
          aria-label={t(ui, "hl.note")}
          onClick={() => window.dispatchEvent(new CustomEvent(HL_CARD_EVENT, { detail: { id: m.id } }))}
        >
          {iconNote}
        </button>
      ))}

      {editor &&
        modal(
          <form
            data-hl-editor=""
            onSubmit={(e) => {
              e.preventDefault();
              saveEditor();
            }}
          >
            <h2 className="window-title text-lg font-bold mb-3 hl-t" style={{ fontFamily: "var(--font-book, Georgia, serif)" }}>{t(ui, "hl.editor.title")}</h2>
            {editor.quote.length <= HL_QUOTE_SHOW_MAX && <p className="hl-quote" data-hl-editor-quote="">{editor.quote}</p>}
            {colorButtons({ kind: "editor", current: editor.color, onPick: (i) => setEditor({ ...editor, color: i }) })}
            <label className="block text-sm hl-t-soft mb-1.5 mt-3" htmlFor="hl-note-field">{t(ui, "hl.editor.label")}</label>
            <div className="hl-field-wrap">
              <textarea
                id="hl-note-field"
                autoFocus
                value={editor.note}
                maxLength={HL_NOTE_MAX}
                rows={4}
                onChange={(e) => setEditor({ ...editor, note: e.target.value })}
                className="hl-field ds-field w-full rounded-lg bg-white px-3 py-2.5 text-base hl-t"
                data-hl-ui=""
              />
              <span className="hl-counter" data-hl-counter="" aria-hidden="true">{editor.note.length}/{HL_NOTE_MAX}</span>
            </div>
            <div className="mt-5 flex justify-end gap-2 flex-wrap">
              {editor.id && (
                <button type="button" data-hl-editor-delete="" className="hl-btn rounded-lg px-4 text-sm font-medium hl-t-soft"
                  onClick={() => { removeHighlight(editor.id as string, labels); setEditor(null); }}>
                  {t(ui, "hl.delete")}
                </button>
              )}
              <button type="button" data-hl-cancel="" className="hl-btn rounded-lg px-4 text-sm font-medium hl-t-soft" onClick={() => setEditor(null)}>
                {t(ui, "bookmark.dialog.cancel")}
              </button>
              <button type="submit" data-hl-save="" className="hl-btn rounded-lg px-5 text-sm font-semibold text-white bg-gradient-to-br from-[var(--ap-band-1)] to-[var(--ap-band-2)] shadow-sm">
                {t(ui, "hl.editor.save")}
              </button>
            </div>
          </form>,
          () => setEditor(null),
          editor.inMood,
          "editor",
        )}

      {imp && importPreview &&
        modal(
          <div data-hl-import="">
            <h2 className="window-title text-lg font-bold mb-3 hl-t" style={{ fontFamily: "var(--font-book, Georgia, serif)" }}>{t(ui, "notes.import.title")}</h2>
            {imp.step === "preview" ? (
              <>
                <p className="hl-t15 hl-t" data-hl-import-summary="">
                  {t(ui, "notes.import.summary", { total: String(importPreview.total), fresh: String(importPreview.fresh), dup: String(importPreview.dup), conflict: String(importPreview.conflict) })}
                </p>
                {importPreview.skipped > 0 && <p className="text-sm hl-t-soft mt-2">{t(ui, "notes.import.skipped", { n: String(importPreview.skipped) })}</p>}
                <div className="mt-4 flex flex-col gap-2">
                  <button type="button" data-hl-import-add="" disabled={importPreview.add.length === 0}
                    className="hl-btn rounded-lg px-5 text-sm font-semibold text-white bg-gradient-to-br from-[var(--ap-band-1)] to-[var(--ap-band-2)] shadow-sm disabled:opacity-50" onClick={doAdd}>
                    {t(ui, "notes.import.add", { n: String(importPreview.add.length) })}
                  </button>
                  <button type="button" data-hl-import-cancel="" className="hl-btn rounded-lg px-4 text-sm font-medium hl-t-soft" onClick={() => setImp(null)}>
                    {t(ui, "bookmark.dialog.cancel")}
                  </button>
                  <button type="button" data-hl-import-replace="" className="hl-btn px-2 text-sm underline hl-t-soft" onClick={() => setImp({ ...imp, step: "replace" })}>
                    {t(ui, "notes.import.replace", { n: String(readHighlights().length) })}
                  </button>
                </div>
              </>
            ) : (
              <>
                <p className="hl-t15 hl-t">{t(ui, "notes.replace.confirm", { n: String(readHighlights().length), m: String(imp.file.items.length) })}</p>
                <div className="mt-4 flex flex-col gap-2">
                  <button type="button" data-hl-replace-do="" className="hl-btn rounded-lg px-5 text-sm font-semibold text-white bg-gradient-to-br from-[var(--ap-band-1)] to-[var(--ap-band-2)] shadow-sm" onClick={doReplace}>
                    {t(ui, "notes.replace.do")}
                  </button>
                  <button type="button" data-hl-replace-back="" className="hl-btn rounded-lg px-4 text-sm font-medium hl-t-soft" onClick={() => setImp({ ...imp, step: "preview" })}>
                    {t(ui, "bookmark.dialog.cancel")}
                  </button>
                </div>
              </>
            )}
          </div>,
          () => setImp(null),
          null,
          "import",
        )}

      {impError &&
        modal(
          <div data-hl-import-error="">
            <h2 className="window-title text-lg font-bold mb-3 hl-t" style={{ fontFamily: "var(--font-book, Georgia, serif)" }}>{t(ui, "notes.import.title")}</h2>
            <p className="hl-t15 hl-t">{t(ui, "notes.import.bad")}</p>
            <div className="mt-4 flex justify-end">
              <button type="button" className="hl-btn rounded-lg px-5 text-sm font-semibold text-white bg-gradient-to-br from-[var(--ap-band-1)] to-[var(--ap-band-2)] shadow-sm" onClick={() => setImpError(false)}>
                {t(ui, "hl.ok")}
              </button>
            </div>
          </div>,
          () => setImpError(false),
          null,
          "error",
        )}

      {tst && (
        <div className="reader-toast" role="status" data-hl-toast="" data-hl-ui="" data-no-reader-tap="" key={tst.key}>
          <span>{tst.text}</span>
          {tst.undo && (
            <button
              type="button"
              className="reader-toast-undo"
              onClick={() => {
                const u = tst.undo;
                window.clearTimeout(tstTimer.current);
                setTst(null);
                u?.();
              }}
            >
              {tst.undoLabel ?? t(ui, "bookmark.undo")}
            </button>
          )}
        </div>
      )}
    </>
  );
}
