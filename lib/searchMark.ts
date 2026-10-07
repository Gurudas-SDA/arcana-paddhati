/**
 * The found word marked at the place a search result opens (Reader v7.8,
 * Satkirti 07.10.2026: «после открытия результата найденное слово
 * подсвечено в тексте»).
 *
 * A result tap (components/Sidebar.tsx) leaves a pending mark: the normalized
 * query and the place (section, anchor). Once that place is shown, the first
 * visible occurrence of the query inside it (the subsection, else the page's
 * article) is painted with the CSS Custom Highlight API (`::highlight(search-hit)`
 * in app/globals.css) — the page's DOM is not changed — and brought into view if
 * it lies off screen. Without that API (older Safari / WebView) the word is wrapped
 * in a <mark class="search-mark search-hit-fb"> instead, unwrapped again on clear
 * (Reader v7.8.1). Like a picture highlight (UI §1), the next tap on the page
 * only clears it; so do "back" / "forward" and any other step to another place
 * (a link, a router push, a new #anchor) — else the mark of a page no longer shown
 * would eat the next page's first tap and stop its anchor alignment (v7.8.1).
 */
import { normalizeText } from "@/lib/book";

const NAME = "search-hit";
const ATTR = "data-search-hl";
/** Set while the mark took over the scroll position (AppShell's anchor keeper stops). */
export const SEARCH_SCROLL_ATTR = "data-search-hl-own";

interface Pending {
  nq: string;
  sectionId: string;
  anchor?: string;
  since: number;
  until: number;
}

let pending: Pending | null = null;
let timer: number | undefined;
let listening = false;
/** Where the mark was put (pathname + #anchor): any other place clears it. */
let markedAt: { path: string; hash: string } | null = null;
/** The fallback marks (no Highlight API), unwrapped on clear. */
let fbMarks: HTMLElement[] = [];
const FB_CLASS = "search-hit-fb";

type HighlightCtor = new (...ranges: Range[]) => unknown;
function registry(): { set: (n: string, h: unknown) => void; delete: (n: string) => void } | null {
  const c = (globalThis as unknown as { CSS?: { highlights?: unknown } }).CSS;
  const H = (globalThis as unknown as { Highlight?: HighlightCtor }).Highlight;
  if (!c?.highlights || !H) return null;
  return c.highlights as { set: (n: string, h: unknown) => void; delete: (n: string) => void };
}

/** Remove the mark (and the scroll ownership). */
export function clearSearchMark() {
  registry()?.delete(NAME);
  unwrapFallback();
  markedAt = null;
  document.documentElement.removeAttribute(ATTR);
  document.documentElement.removeAttribute(SEARCH_SCROLL_ATTR);
}

/** True while a found word is marked on the page. */
export function searchMarkOn(): boolean {
  return document.documentElement.hasAttribute(ATTR);
}

function unwrapFallback() {
  const marks = fbMarks;
  fbMarks = [];
  for (const m of marks) {
    const parent = m.parentNode;
    if (!parent) continue;
    while (m.firstChild) parent.insertBefore(m.firstChild, m);
    parent.removeChild(m);
    // the split text node joins its first part again (the node React keeps)
    parent.normalize();
  }
}

/** No Highlight API: wrap each text piece of `range` in a <mark>. */
function wrapFallback(range: Range) {
  const nodes: Text[] = [];
  const root = range.commonAncestorContainer;
  if (root.nodeType === Node.TEXT_NODE) nodes.push(root as Text);
  else {
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode() as Text | null; n; n = w.nextNode() as Text | null) {
      if (range.intersectsNode(n)) nodes.push(n);
    }
  }
  for (let node of nodes) {
    const from = node === range.startContainer ? range.startOffset : 0;
    const to = node === range.endContainer ? range.endOffset : node.data.length;
    if (to <= from) continue;
    if (to < node.data.length) node.splitText(to);
    if (from > 0) node = node.splitText(from);
    const m = document.createElement("mark");
    m.className = `search-mark ${FB_CLASS}`;
    node.parentNode?.insertBefore(m, node);
    m.appendChild(node);
    fbMarks.push(m);
  }
}

function here(): { path: string; hash: string } {
  return { path: window.location.pathname.replace(/\/+$/, ""), hash: window.location.hash };
}

/** A step to another place (link, router push, back / forward, new #anchor) clears the mark. */
function onUrlChange() {
  if (!markedAt) return;
  const h = here();
  if (h.path !== markedAt.path || (h.hash && h.hash !== markedAt.hash)) clearSearchMark();
}

function visibleText(node: Text): boolean {
  const el = node.parentElement;
  if (!el || el.closest("[hidden], .sr-only, script, style, .mood-overlay")) return false;
  return el.getClientRects().length > 0;
}

/** Range of the first visible occurrence of `nq` (normalized) inside `root`. */
function findRange(root: Element, nq: string): Range | null {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let norm = "";
  const where: { node: Text; off: number }[] = [];
  for (let n = walker.nextNode() as Text | null; n; n = walker.nextNode() as Text | null) {
    if (!visibleText(n)) {
      // a hidden stretch never joins two visible words into one match
      norm += "\u0000";
      where.push({ node: n, off: 0 });
      continue;
    }
    const t = n.data;
    for (let i = 0; i < t.length; i++) {
      const c = normalizeText(t[i]);
      for (let k = 0; k < c.length; k++) {
        norm += c[k];
        where.push({ node: n, off: i });
      }
    }
  }
  const at = norm.indexOf(nq);
  if (at < 0) return null;
  const a = where[at];
  const b = where[at + nq.length - 1];
  const r = document.createRange();
  r.setStart(a.node, a.off);
  r.setEnd(b.node, b.off + 1);
  return r;
}

function onPlace(p: Pending): boolean {
  let path = window.location.pathname;
  try {
    path = decodeURI(path);
  } catch {
    // keep raw
  }
  return path.replace(/\/+$/, "").endsWith(`/${p.sectionId}`);
}

function tryApply(): boolean {
  const p = pending;
  if (!p) return true;
  if (Date.now() > p.until) {
    pending = null;
    return true;
  }
  if (!onPlace(p) || document.querySelector(".mobile-menu")) return false;
  const main = document.querySelector<HTMLElement>(".app-main");
  const root = (p.anchor && document.getElementById(p.anchor)) || main?.querySelector("article");
  if (!root || !main) return false;
  const range = findRange(root, p.nq);
  if (!range) return false;
  pending = null;
  // measured before a fallback wrap changes the DOM
  const rect = range.getBoundingClientRect();
  const reg = registry();
  if (reg) {
    const H = (globalThis as unknown as { Highlight: HighlightCtor }).Highlight;
    reg.set(NAME, new H(range));
  } else {
    // no Highlight API (older Safari / WebView): a <mark> around the word
    wrapFallback(range);
  }
  document.documentElement.setAttribute(ATTR, "");
  markedAt = here();
  if (!markedAt.hash && p.anchor) markedAt.hash = `#${encodeURIComponent(p.anchor)}`;
  // Off screen (a long subsection): bring the word into view.
  const m = main.getBoundingClientRect();
  if (rect.top < m.top + 56 || rect.bottom > m.bottom - 64) {
    document.documentElement.setAttribute(SEARCH_SCROLL_ATTR, "");
    main.scrollTop += rect.top - m.top - m.height * 0.35;
  }
  return true;
}

function listen() {
  if (listening) return;
  listening = true;
  let start: { x: number; y: number } | null = null;
  document.addEventListener(
    "pointerdown",
    (e) => {
      start = searchMarkOn() && e.isPrimary ? { x: e.clientX, y: e.clientY } : null;
    },
    true,
  );
  document.addEventListener("pointerup", (e) => {
    const s = start;
    start = null;
    if (!s || Math.hypot(e.clientX - s.x, e.clientY - s.y) > 10) return;
    // after the reader's own handlers have seen the mark (first tap only clears it)
    window.setTimeout(clearSearchMark, 0);
  });
  window.addEventListener("popstate", () => {
    // the menu closing itself right after the tap (same page, no move) is not a step away
    if (pending && Date.now() - pending.since < 1500) return;
    pending = null;
    clearSearchMark();
  });
  // Forward steps (Next <Link>, router.push / replace, a new #anchor) send no
  // popstate: watch the history calls themselves (v7.8.1).
  window.addEventListener("hashchange", onUrlChange);
  for (const k of ["pushState", "replaceState"] as const) {
    const orig = window.history[k];
    window.history[k] = function (this: History, ...args: Parameters<History["pushState"]>) {
      const r = orig.apply(this, args);
      try {
        onUrlChange();
      } catch {
        // never break navigation
      }
      return r;
    } as History["pushState"];
  }
}

/** A search result was tapped: mark `nq` at that place once it is shown. */
export function setPendingSearchMark(nq: string, sectionId: string, anchor?: string) {
  if (typeof window === "undefined" || !nq) return;
  listen();
  clearSearchMark();
  pending = { nq, sectionId, anchor, since: Date.now(), until: Date.now() + 8000 };
  window.clearInterval(timer);
  // the page shown, its pictures and fonts settled: first try soon, then keep trying a while
  timer = window.setInterval(() => {
    if (tryApply()) window.clearInterval(timer);
  }, 120);
}
