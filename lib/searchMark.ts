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
 * it lies off screen. Like a picture highlight (UI §1), the next tap on the page
 * only clears it; so do "back" / "forward".
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
  document.documentElement.removeAttribute(ATTR);
  document.documentElement.removeAttribute(SEARCH_SCROLL_ATTR);
}

/** True while a found word is marked on the page. */
export function searchMarkOn(): boolean {
  return document.documentElement.hasAttribute(ATTR);
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
  const reg = registry();
  if (!reg) return true; // no Highlight API (old Safari): the result still opens
  const H = (globalThis as unknown as { Highlight: HighlightCtor }).Highlight;
  reg.set(NAME, new H(range));
  document.documentElement.setAttribute(ATTR, "");
  // Off screen (a long subsection): bring the word into view.
  const rect = range.getBoundingClientRect();
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
