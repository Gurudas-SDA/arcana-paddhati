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
  NO_COLOR,
  COLOR_KEYS,
  HL_CARD_EVENT,
  HL_EDIT_EVENT,
  HL_EVENT,
  HL_IMPORT_EVENT,
  HL_NOTE_MAX,
  HL_REVEAL_EVENT,
  HL_TOAST_EVENT,
  coveredBy,
  dedupeHighlights,
  upsertHighlight,
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
  /** V92: the selection runs from one section into another — a note is kept per section, so only «Копировать» works */
  cross?: boolean;
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
      if (!root.contains(b)) {
        // V92: extended past the section: keep our menu (copy only) instead of letting it vanish
        const rs = r.getClientRects();
        const l = rs.length ? rs[rs.length - 1] : r.getBoundingClientRect();
        const f0 = rs.length ? rs[0] : l;
        return {
          section: root.getAttribute("data-book-section") ?? section ?? "", start: 0, end: 0, quote: s.toString().trim(), before: "", after: "",
          rect: { left: Math.min(f0.left, l.left), right: l.right, top: f0.top, bottom: l.bottom }, inMood: null, cross: true,
        };
      }
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
  const gapsRef = useRef<Map<string, HTMLElement>>(new Map());
  const moRef = useRef<MutationObserver | null>(null);
  const [markers, setMarkers] = useState<{ id: string; x: number; y: number; nc: boolean }[]>([]);
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
    // V100: old duplicates (one stretch, several colours) become one
    const all = readHighlights();
    const merged = dedupeHighlights(all);
    if (merged.length !== all.length) writeHighlights(merged);
    read();
    window.addEventListener(HL_EVENT, read);
    window.addEventListener("storage", read);
    return () => {
      window.removeEventListener(HL_EVENT, read);
      window.removeEventListener("storage", read);
    };
  }, []);

  // --- the room for a note's sign (V100b, Vraja Lila msg 8357 variant B: «иконка не будет загораживать текст?»)
  // An empty inline box right after the fragment's last letter, as wide as the sign: the line makes room for it, so the sign never covers a letter.
  // It holds no text (the book's text, the offsets and the copied text are unchanged).
  const clearGaps = () => {
    document.querySelectorAll("[data-hl-gap]").forEach((g) => g.remove());
    gapsRef.current = new Map();
    moRef.current?.takeRecords();
  };
  const placeGaps = (res: Resolved[]) => {
    for (const r of res) {
      if (!r.h.note) continue;
      try {
        const at = document.createRange();
        at.setStart(r.range.endContainer, r.range.endOffset);
        at.collapse(true);
        const g = document.createElement("span");
        g.setAttribute("data-hl-gap", "");
        g.setAttribute("data-hl-ui", "");
        g.setAttribute("aria-hidden", "true");
        g.className = "hl-gap";
        at.insertNode(g);
        gapsRef.current.set(r.h.id, g);
      } catch {
        // the place cannot hold it: the sign is drawn at the end of the fragment as before
      }
    }
    moRef.current?.takeRecords();
  };

  // --- painting
  const paint = useCallback(() => {
    const reg = registry();
    hasApi.current = !!reg;
    const list = itemsRef.current;
    // V100b: the room kept in the line for the note's sign is drawn anew every time
    clearGaps();
    // No highlights at all: nothing to find or draw (the reader pays nothing for the feature until he uses it).
    if (!list.length) {
      if (resolved.current.length && reg) for (let i = 0; i < COLORS; i++) reg.delete(`hl-${i}`);
      if (resolved.current.length && reg) reg.delete("hl-nc");
      if (resolved.current.length) document.querySelectorAll("[data-hl-dot]").forEach((b) => b.removeAttribute("data-hl-dot"));
      resolved.current = [];
      setMarkers((prev) => (prev.length ? [] : prev));
      return;
    }
    const res: Resolved[] = [];
    const lostNow = new Map<string, boolean>();
    const byColor: Range[][] = Array.from({ length: COLORS }, () => []);
    const ncRanges: Range[] = [];
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
        if (h.color >= 0) byColor[h.color].push(r);
        else ncRanges.push(r);
        res.push({ h, root: c.root, range: r });
      }
    }
    resolved.current = res;
    placeGaps(res);
    if (reg) {
      for (let i = 0; i < COLORS; i++) {
        if (byColor[i].length) reg.set(`hl-${i}`, makeHighlight(byColor[i]));
        else reg.delete(`hl-${i}`);
      }
      // a note without a colour: a light dotted underline under the fragment (with the sign at its end)
      if (ncRanges.length) reg.set("hl-nc", makeHighlight(ncRanges));
      else reg.delete("hl-nc");
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
    const out: { id: string; x: number; y: number; nc: boolean }[] = [];
    const m = mainEl();
    const vh = window.innerHeight;
    for (const r of resolved.current) {
      if (!r.h.note) continue;
      const gap = gapsRef.current.get(r.h.id);
      const gr = gap && gap.isConnected ? gap.getBoundingClientRect() : null;
      const rs = r.range.getClientRects();
      if (!rs.length) continue;
      const last = gr && gr.width > 0 ? { top: gr.top, bottom: gr.bottom, height: gr.height, right: gr.left } : rs[rs.length - 1];
      if (last.bottom < 0 || last.top > vh) continue;
      if (m && !r.root.closest(".mood-overlay")) {
        const mr = m.getBoundingClientRect();
        if (last.bottom < mr.top || last.top > mr.bottom) continue;
      }
      out.push({ id: r.h.id, x: last.right, y: last.top + last.height / 2, nc: r.h.color === NO_COLOR });
    }
    setMarkers((prev) => (prev.length === out.length && prev.every((p, i) => p.id === out[i].id && p.nc === out[i].nc && Math.abs(p.x - out[i].x) < 1 && Math.abs(p.y - out[i].y) < 1) ? prev : out));
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
    moRef.current = mo;
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
    // V101 (Vraja Lila msg 8393-8396; phones and tablets: iPhone/iPad Safari, Android Chrome): the system bar (Copy · Look Up · Translate / Chrome's floating bar) is
    // ABOVE the selection, so the panel goes right UNDER it (a small gap, the lower selection handle stays free); no room below -> above the selection, higher than
    // the system bar; no room there either -> as in V100. A computer (mouse) keeps the placement above the selection.
    el.toggleAttribute("data-hl-under", phone);
    if (phone) {
      const gap = parseFloat(getComputedStyle(el).marginTop) || 16; // CSS: .hl-menu[data-hl-under] margin-top = var(--space-16)
      const SYS_BAR = 56; // tehniskais slieksnis: the system bar's height
      const vv = window.visualViewport;
      const visTop = vv ? vv.offsetTop : 0;
      let visBottom = vv ? vv.offsetTop + vv.height : vh;
      const bar = document.querySelector(".reader-bar-bottom");
      if (bar) visBottom = Math.min(visBottom, bar.getBoundingClientRect().top);
      // V102 (Vraja Lila msg 3064/3066 real iPhone + decision msg 8444 «меню над выделением»): iOS's own menu (Copy / Look Up / Translate, ~43 px high) came out BELOW the selection
      // (16..60 px under it) and covered the colours. The page cannot tell which side iOS picks, so on iOS the panel goes NEAR ABOVE the selection (IOS_ABOVE px over its top; the system
      // menu usually sits under it then); no room above (top bar / page top) -> UNDER the selection, IOS_CLEAR px from it, clear of the system menu zone below.
      const ios = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
      const IOS_ABOVE = 16; // tehniskais slieksnis Lipikāra: gap above the selection (upper handle ~8 px), as V101 under it
      const IOS_CLEAR = 72; // tehniskais slieksnis Lipikāra: fallback under the selection: 16 (handle) + 43 (system menu, measured on Vraja's screenshot) + 13 spare
      const topBar = document.querySelector(".reader-bar-top");
      const barBottom = topBar ? topBar.getBoundingClientRect().bottom : 0;
      const roomTop = Math.max(visTop, barBottom) + 8;
      // V104 (Vraja Lila msg 3106-3109, real iPhone 19.11): the system menu is not always BELOW the selection. Seen on the device: a one-line selection -> menu under it (5 frames);
      // a selection over two lines (lower on the page) -> menu OVER it, and the panel 16 px above fell on it. The page cannot ask iOS, so by what was seen: one line -> menu under the
      // selection, several lines -> menu over it (the other way when it has no room: IOS_ZONE px). The panel goes to the OTHER side, IOS_ABOVE px from the selection; no room there ->
      // the free side beyond the menu zone (IOS_CLEAR px).
      let lines = 1;
      if (ios) {
        const sel = window.getSelection();
        const rects = sel && sel.rangeCount ? Array.from(sel.getRangeAt(0).getClientRects()).filter((q) => q.width > 1 && q.height > 1) : [];
        const mids = rects.map((q) => (q.top + q.bottom) / 2).sort((x, y) => x - y);
        lines = mids.filter((m, i) => i === 0 || m - mids[i - 1] > 8).length || 1;
      }
      const IOS_ZONE = 64; // tehniskais slieksnis Lipikāra: room the system menu needs next to the selection (16 + 43 + spare)
      const menuBelow = lines === 1 ? r.bottom + IOS_ZONE <= visBottom - 8 : !(r.top - IOS_ZONE >= roomTop);
      const underAt = (d: number) => r.bottom + d;
      const aboveAt = (d: number) => r.top - d - h;
      let iosTop = -1;
      if (ios) {
        if (menuBelow) {
          if (aboveAt(IOS_ABOVE) >= roomTop) iosTop = aboveAt(IOS_ABOVE) - gap;
          else if (underAt(IOS_CLEAR) + h <= visBottom - 8) iosTop = underAt(IOS_CLEAR) - gap;
        } else {
          if (underAt(IOS_ABOVE) + h <= visBottom - 8) iosTop = underAt(IOS_ABOVE) - gap;
          else if (aboveAt(IOS_CLEAR) >= roomTop) iosTop = aboveAt(IOS_CLEAR) - gap;
        }
      } else if (r.bottom + gap + h <= visBottom - 8) iosTop = r.bottom - 0;
      else if (r.top - gap - SYS_BAR - h >= visTop + 8) iosTop = r.top - gap - SYS_BAR - h - gap;
      if (iosTop >= 0) {
        const lx = Math.max(16, Math.min((r.left + r.right) / 2 - w / 2, vw - w - 16));
        if (Math.abs(lx - menu.x) > 0.5 || Math.abs(iosTop - menu.y) > 0.5) setMenu({ sel: menu.sel, x: lx, y: iosTop });
        return;
      }
      el.removeAttribute("data-hl-under"); // no room on either side: the V100 placement (no margin)
    }
    if (phone) {
      // V100 (Vraja Lila, iPhone): the system's own bar (Copy · Look Up · Translate) sits right above or below the selection and covered the
      // colours. On a phone the panel is kept AWAY from the selection: fixed at the bottom of the screen, or at the top when the selection is low.
      const low = vh - h - 12;
      top = r.bottom > low - 8 ? 8 : low;
    }
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
    upsertHighlight({
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

  const colorButtons = ({ current, onPick, kind, disabled }: { current?: number; onPick: (i: number) => void; kind: string; disabled?: boolean }) => (
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
          disabled={disabled}
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
    else if (e.sel) {
      if (e.color >= 0 || note) create(e.sel, e.color, note);
      else {
        // V100b: no colour and no note = nothing to keep: the marked place is cleared
        const cov = coveredBy(readHighlights(), { lang, section: e.sel.section, mood: e.sel.mood, start: e.sel.start, end: e.sel.end });
        if (cov.length) writeHighlights(readHighlights().filter((x) => !cov.some((c) => c.id === x.id)));
      }
    }
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
            {menu.sel.cross && <p className="hl-hint" data-hl-hint="">{t(ui, "hl.cross")}</p>}
            {colorButtons({ kind: "menu", disabled: menu.sel.cross, onPick: (i) => { create(menu.sel, i); closeMenu(); } })}
            <div className="hl-actions">
              <button
                type="button"
                className="hl-action"
                data-hl-note=""
                disabled={menu.sel.cross}
                onClick={() => {
                  const old = coveredBy(itemsRef.current, { lang, section: menu.sel.section, mood: menu.sel.mood, start: menu.sel.start, end: menu.sel.end })
                    .sort((a, b) => b.updated - a.updated)[0];
                  setEditor({ sel: menu.sel, color: old?.color ?? NO_COLOR, note: old?.note ?? "", quote: menu.sel.quote, inMood: menu.sel.inMood });
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
              {colorButtons({ kind: "card", current: cardItem.color, onPick: (i) => (cardItem.color === i ? (cardItem.note ? updateHighlight(cardItem.id, { color: NO_COLOR }) : (removeHighlight(cardItem.id, labels), setCard(null))) : updateHighlight(cardItem.id, { color: i })) })}
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
          data-hl-nocolor={m.nc ? "" : undefined}
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
            {colorButtons({ kind: "editor", current: editor.color, onPick: (i) => setEditor({ ...editor, color: editor.color === i ? NO_COLOR : i }) })}
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
