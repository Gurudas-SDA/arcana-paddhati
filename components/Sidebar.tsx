"use client";

import { useOfflineProgress } from "@/lib/offlineProgress";
import React, {
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  normalizeText,
  tocLayout,
  type SearchEntry,
  type TocPart,
  type TocSection,
} from "@/lib/book";
import { localeHref, parsePath, t, type UiDict } from "@/lib/i18n";
import {
  isMenuEntry,
  main as mainEl,
  menuDepth,
  patchState,
  pushOverlay,
  pushPlace,
} from "@/lib/navHistory";
import {
  setShowAllTranslations,
  setShowAllWbw,
  useShowAllTranslations,
  useShowAllWbw,
} from "@/lib/translationsPref";

interface SidebarProps {
  sections: TocSection[];
  /** Parts (I, II, …) grouping the chapters; headings in the contents list. */
  parts: TocPart[];
  /** Language of the current URL (links stay in it). */
  lang: string;
  ui: UiDict;
  /** The language's book has word-by-word data (else its switch is hidden). */
  hasWbw: boolean;
  languageSwitcher: React.ReactNode;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onSearchFocus: () => void;
  /** Full-text index; null while not (yet) loaded — then titles are searched. */
  searchEntries: SearchEntry[] | null;
  onClose: () => void;
  /**
   * Menu only: a link (contents link or search result) is being followed out
   * of the menu. The menu's history entries stay, so "back" from the new
   * place reopens the menu as it was (UI rule 6). Also marks menu mode: each
   * part expanded in the contents is then a history entry of its own.
   */
  /** `navigating`: another page is being opened (the menu stays until it is shown). */
  onLeave?: (navigating?: boolean) => void;
}

interface PreparedEntry {
  entry: SearchEntry;
  nTitle: string;
  nText: string;
  /** nText[i] came from entry.text[map[i]] */
  map: number[];
}

interface Snippet {
  before: string;
  match: string;
  after: string;
}

interface SearchResult {
  entry: SearchEntry;
  snippet: Snippet;
}

const MAX_RESULTS = 50;
const SNIPPET_BEFORE = 50;
const SNIPPET_AFTER = 80;

function prepare(entry: SearchEntry): PreparedEntry {
  let nText = "";
  const map: number[] = [];
  for (let i = 0; i < entry.text.length; i++) {
    const n = normalizeText(entry.text[i]);
    for (let k = 0; k < n.length; k++) map.push(i);
    nText += n;
  }
  return { entry, nTitle: normalizeText(entry.title), nText, map };
}

/** Clause boundaries of `text`: the index where each clause starts (after
 *  ". ", "; ", ": ", "! ", "? " or a line break), plus text.length. */
function clauseStarts(text: string): number[] {
  const starts = [0];
  const re = /[.!?;:…]\s+|\n+/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    const at = m.index + m[0].length;
    if (at < text.length) starts.push(at);
  }
  starts.push(text.length);
  return starts;
}

/** Search excerpt made of whole clauses only — never a cut-off fragment
 *  with "…" (UI rule: no truncated texts). The window SNIPPET_BEFORE /
 *  SNIPPET_AFTER around the match is snapped to clause boundaries: inward
 *  where the match allows it, outward only for the clause holding the match. */
function makeSnippet(p: PreparedEntry, pos: number, qLen: number): Snippet {
  const text = p.entry.text;
  const starts = clauseStarts(text);
  const ends = starts.slice(1).map((i) => text.slice(0, i).trimEnd().length);
  if (pos < 0) {
    // Title-only match: the first clauses of the text.
    const limit = SNIPPET_BEFORE + SNIPPET_AFTER;
    let end = ends[0];
    for (const e of ends) {
      if (e > limit) break;
      end = e;
    }
    return { before: "", match: "", after: text.slice(0, end) };
  }
  const mStart = p.map[pos];
  const mEnd = p.map[pos + qLen - 1] + 1;
  const winStart = Math.max(0, mStart - SNIPPET_BEFORE);
  const winEnd = Math.min(text.length, mEnd + SNIPPET_AFTER);
  // Start: first clause start inside the window (and not after the match);
  // otherwise the start of the clause holding the match.
  let start = 0;
  for (const st of starts) {
    if (st > mStart) break;
    start = st;
    if (st >= winStart) break;
  }
  // End: last clause end inside the window (and not before the match's end);
  // otherwise the end of the clause holding the match's end.
  let end = text.length;
  for (let k = 0; k < ends.length; k++) {
    if (ends[k] < mEnd) continue;
    end = ends[k];
    if (k + 1 >= ends.length || ends[k + 1] > winEnd) break;
  }
  return {
    before: text.slice(start, mStart),
    match: text.slice(mStart, mEnd),
    after: text.slice(mEnd, end),
  };
}

/** Scroll-spy line: the subsection block crossing this band (about 20% from
 *  the top of the viewport) is the one "in view". */
const SPY_ROOT_MARGIN = "-20% 0px -79% 0px";
/** After a click on a subsection link (or a hash change) the spy is paused
 *  this long, so the chosen item stays active while the page scrolls to it. */
const CLICK_LOCK_MS = 1000;

function hashId(): string | null {
  const h = window.location.hash.slice(1);
  if (!h) return null;
  try {
    return decodeURIComponent(h);
  } catch {
    return h;
  }
}

/**
 * Id of the current subsection of the shown section: from the URL hash, and
 * while scrolling from the subsection block crossing the spy line
 * (IntersectionObserver). null while in the section's introductory text.
 */
function useActiveSubsection(
  pathname: string,
  subIds: string[]
): [string | null, (id: string) => void] {
  const [active, setActive] = useState<string | null>(null);
  const lockUntil = useRef(0);
  const idsKey = subIds.join("|");

  // Reset when the page changes (render-time adjustment, no effect needed).
  const [lastPath, setLastPath] = useState(pathname);
  if (pathname !== lastPath) {
    setLastPath(pathname);
    setActive(null);
  }

  useEffect(() => {
    const ids = idsKey ? idsKey.split("|") : [];
    if (ids.length === 0) return;
    const known = new Set(ids);
    const visible = new Set<string>();
    let observer: IntersectionObserver | null = null;
    let retry: number | undefined;

    const fromHash = () => {
      const id = hashId();
      if (id && known.has(id)) {
        lockUntil.current = Date.now() + CLICK_LOCK_MS;
        setActive(id);
      }
    };

    const attach = (attempt: number) => {
      const els = ids
        .map((id) => document.getElementById(id))
        .filter((el): el is HTMLElement => el !== null);
      if (els.length === 0) {
        // Content of a freshly navigated page may not be mounted yet.
        if (attempt < 20) {
          retry = window.setTimeout(() => attach(attempt + 1), 100);
        }
        return;
      }
      fromHash();
      const obs = new IntersectionObserver(
        (entries) => {
          for (const e of entries) {
            if (e.isIntersecting) visible.add(e.target.id);
            else visible.delete(e.target.id);
          }
          if (Date.now() < lockUntil.current) return;
          const current = ids.find((id) => visible.has(id));
          // Nothing on the line: keep the last one unless we are back above
          // the first subsection (the section's introductory text).
          if (current) setActive(current);
          else {
            const first = els[0].getBoundingClientRect().top;
            if (first > window.innerHeight * 0.2) setActive(null);
          }
        },
        { rootMargin: SPY_ROOT_MARGIN, threshold: 0 }
      );
      els.forEach((el) => obs.observe(el));
      observer = obs;
    };

    attach(0);
    window.addEventListener("hashchange", fromHash);
    window.addEventListener("popstate", fromHash);
    return () => {
      window.clearTimeout(retry);
      observer?.disconnect();
      window.removeEventListener("hashchange", fromHash);
      window.removeEventListener("popstate", fromHash);
    };
  }, [pathname, idsKey]);

  const select = (id: string) => {
    lockUntil.current = Date.now() + CLICK_LOCK_MS;
    setActive(id);
  };
  return [active, select];
}

/** sessionStorage key: parts the reader expanded / collapsed by hand. */
const PARTS_STORE = "toc-parts-open";
const PARTS_EVENT = "arcana:toc-parts";
/** Last state set in this page (used when sessionStorage is unavailable). */
let partsMemory = "{}";

function partsSnapshot(): string {
  try {
    return sessionStorage.getItem(PARTS_STORE) ?? partsMemory;
  } catch {
    return partsMemory;
  }
}

function parseParts(raw: string): Record<string, boolean> {
  try {
    const v = JSON.parse(raw);
    return v && typeof v === "object" ? (v as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

/** Put back the parts of a menu history entry (AppShell, on "back"). */
export function restoreParts(raw: string) {
  setPartsState(parseParts(raw));
}

function setPartsState(state: Record<string, boolean>) {
  partsMemory = JSON.stringify(state);
  try {
    sessionStorage.setItem(PARTS_STORE, partsMemory);
  } catch {
    // storage unavailable — kept in memory until reload
  }
  window.dispatchEvent(new Event(PARTS_EVENT));
}

function subscribeParts(onChange: () => void) {
  window.addEventListener(PARTS_EVENT, onChange);
  return () => window.removeEventListener(PARTS_EVENT, onChange);
}

/**
 * Open / closed state of the part groups in the contents. Collapsed by
 * default; the part holding the current page is open on every arrival at a
 * page and every time the contents mount (the mobile menu mounts anew each
 * time it opens), so the reader always sees where he is. Toggles by hand
 * last for the session (sessionStorage). The static HTML shows only the
 * current part open.
 */
function usePartsOpen(
  selectedId: string | null,
  currentPartId: string | null
): [(id: string) => boolean, (id: string) => void] {
  const raw = useSyncExternalStore(subscribeParts, partsSnapshot, () => "{}");
  const state = useMemo(() => parseParts(raw), [raw]);
  // Arrival: forget a hand-made "collapsed" of the current part (before
  // paint, so it never flashes closed).
  useLayoutEffect(() => {
    if (!currentPartId) return;
    const cur = parseParts(partsSnapshot());
    if (cur[currentPartId] === false) {
      delete cur[currentPartId];
      setPartsState(cur);
    }
  }, [selectedId, currentPartId]);
  // Chapters (key "ch:<id>") share the store: the current one is open by default.
  const isOpen = (id: string) =>
    state[id] ?? (id === currentPartId || (selectedId !== null && id === chapterKey(selectedId)));
  const toggle = (id: string) => setPartsState({ ...state, [id]: !isOpen(id) });
  return [isOpen, toggle];
}

/** history.state key: scroll offset of the contents / results list. */
const NAV_SCROLL = "apNav";
/** history.state key: the highlighted contents row of a menu step (the path). */
const PATH_LIT = "apLit";

function readPathLit(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const v = (window.history.state as Record<string, unknown> | null)?.[PATH_LIT];
    return typeof v === "string" ? v : null;
  } catch {
    return null;
  }
}

/** Scroll the contents list so that the highlighted row is fully in view
 *  (centred if it was outside). Only the list moves, never the page. */
function revealLit(nav: HTMLElement | null) {
  if (!nav) return;
  const row = nav.querySelector<HTMLElement>("[data-toc-lit]");
  if (!row) return;
  const n = nav.getBoundingClientRect();
  const r = row.getBoundingClientRect();
  if (r.top >= n.top && r.bottom <= n.bottom) return;
  nav.scrollTop += r.top - n.top - (n.height - r.height) / 2;
}

/** Store / history key of a chapter's subsection list in the contents. */
const chapterKey = (sectionId: string) => `ch:${sectionId}`;

/** A freshly opened contents: chapters as by default (only the current one
 *  open); the parts keep the reader's hand-made state. */
function resetChapters() {
  const cur = parseParts(partsSnapshot());
  let changed = false;
  for (const k of Object.keys(cur)) {
    if (k.startsWith("ch:")) {
      delete cur[k];
      changed = true;
    }
  }
  if (changed) setPartsState(cur);
}

/** A small on/off switch row of the sidebar. */
function PrefSwitch({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  const labelId = useId();
  // Only the label text and the switch itself act; the empty gap between
  // them is page space (UI rule 1).
  return (
    <div className="flex w-full items-center justify-between gap-3 py-1 text-xs text-[#5C3D2E]">
      <span
        id={labelId}
        onClick={() => onChange(!checked)}
        className="cursor-pointer select-none hover:text-[#2C1810] transition-colors"
      >
        {label}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-labelledby={labelId}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-4 w-7 shrink-0 items-center rounded-full transition-colors ${
          checked ? "bg-[#B8860B]" : "bg-[#E8DCC8]"
        }`}
      >
        <span
          className={`inline-block h-3 w-3 rounded-full bg-white shadow-sm transition-transform ${
            checked ? "translate-x-3.5" : "translate-x-0.5"
          }`}
        />
      </button>
    </div>
  );
}

export default function Sidebar({
  sections,
  parts,
  lang,
  ui,
  hasWbw,
  languageSwitcher,
  searchQuery,
  onSearchChange,
  onSearchFocus,
  searchEntries,
  onClose,
  onLeave: onLeaveProp,
}: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchInputRef = useRef<HTMLInputElement>(null);
  const navRef = useRef<HTMLElement>(null);

  /** The menu entry keeps the list's scroll offset: "back" to it reopens the
   *  contents / results exactly where the reader left them. */
  const saveNavScroll = () => {
    try {
      if (isMenuEntry()) patchState({ [NAV_SCROLL]: navRef.current?.scrollTop ?? 0 });
    } catch {
      // history unavailable
    }
  };
  const onLeave = onLeaveProp
    ? (navigating?: boolean) => {
        saveNavScroll();
        onLeaveProp(navigating);
      }
    : undefined;

  // Put the list's scroll offset of this menu entry back: on mount (the menu
  // reopened by "back" or a reload) and on "back" between menu steps. Applied
  // a few times while the restored rows (expanded parts / chapters) settle.
  useLayoutEffect(() => {
    let timers: number[] = [];
    const apply = () => {
      const v = (window.history.state as Record<string, unknown> | null)?.[NAV_SCROLL];
      if (typeof v === "number" && navRef.current) navRef.current.scrollTop = v;
      // The highlighted row (the place on the path) is always in view.
      revealLit(navRef.current);
    };
    const schedule = () => {
      timers.forEach((id) => window.clearTimeout(id));
      apply();
      requestAnimationFrame(apply);
      timers = [60, 160, 320].map((ms) => window.setTimeout(apply, ms));
    };
    schedule();
    window.addEventListener("popstate", schedule);
    return () => {
      timers.forEach((id) => window.clearTimeout(id));
      window.removeEventListener("popstate", schedule);
    };
  }, []);
  const selectedId = parsePath(pathname).sectionId;
  const selectedSection = sections.find((s) => s.id === selectedId);
  const subIds = useMemo(
    () => (selectedSection?.subsections ?? []).map((sub) => sub.id),
    [selectedSection]
  );
  const [activeSubId, selectSub] = useActiveSubsection(pathname, subIds);

  /**
   * Two-tap contents (Satkirti, 06.10.2026): the FIRST tap on an item only
   * highlights it (a chapter with subsections also expands), the SECOND tap on
   * the same item opens it — no accidental jumps. Exactly one row is
   * highlighted: the tapped one, or (before any tap) the place being read.
   * A new page or "back" forgets the tapped row.
   */
  const [tapped, setTapped] = useState<string | null>(null);
  /**
   * The path (Satkirti, 06.10.2026): every menu step (history entry) keeps the
   * row that was highlighted when the reader left it (`apLit`). "Back" to a
   * step shows that row highlighted again — where he was — and scrolled into
   * view; it is shown, not armed: the next tap on it is a first tap again.
   */
  const [pathLit, setPathLit] = useState<string | null>(readPathLit);
  const [tappedPath, setTappedPath] = useState(pathname);
  if (pathname !== tappedPath) {
    setTappedPath(pathname);
    setTapped(null);
  }
  useEffect(() => {
    const onPop = () => {
      setTapped(null);
      setPathLit(readPathLit());
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  /** Row highlighted: the tapped one, else the path's row of this menu step,
   *  else `byDefault` (the current place). */
  const lit = (id: string, byDefault: boolean) =>
    tapped !== null ? tapped === id : pathLit !== null ? pathLit === id : byDefault;
  /** Highlight `id` (a tap): it becomes this menu step's place on the path. */
  const mark = (id: string) => {
    setTapped(id);
    setPathLit(id);
    try {
      if (isMenuEntry()) patchState({ [PATH_LIT]: id });
    } catch {
      // history unavailable: the highlight still shows
    }
  };
  /** First tap on `id`: highlight only (false). Second tap: go on (true). */
  const secondTap = (e: React.MouseEvent | null, id: string): boolean => {
    if (tapped === id) return true;
    e?.preventDefault();
    mark(id);
    return false;
  };
  const showAllTranslations = useShowAllTranslations();
  const offline = useOfflineProgress();
  const showAllWbw = useShowAllWbw();

  const sectionHref = (sectionId: string, anchor?: string) =>
    localeHref(lang, sectionId, anchor);

  /**
   * Click on a link to a place in the book (search result, subsection).
   * Another page: the Link navigates (Next.js scrolls to the anchor). The page
   * already shown: Next.js does nothing when the URL (with its #hash) is the
   * current one — a second tap on the same result did not move — so scroll to
   * the anchor here every time. A jump that moves the reader is a new history
   * entry (UI rule 6: "back" returns to where he was).
   */
  const followLink = (
    e: React.MouseEvent,
    sectionId: string,
    anchor: string | undefined
  ) => {
    const strip = (p: string) => p.replace(/\/+$/, "");
    const samePage = strip(localeHref(lang, sectionId)) === strip(pathname);
    if (!samePage) {
      // The Link navigates (a new entry on top of the menu's).
      onLeave?.(true);
      return;
    }
    e.preventDefault();
    /** Scroll to the place; true when that was a move (a new entry). */
    const jump = (): boolean => {
      const main = mainEl();
      if (anchor) {
        const target = document.getElementById(anchor);
        const moves =
          hashId() !== anchor ||
          (target && main
            ? Math.abs(target.getBoundingClientRect().top - main.getBoundingClientRect().top) > 8
            : false);
        if (moves) pushPlace(`#${anchor}`);
        // The scroll-spy re-reads the hash (also when it is unchanged).
        window.dispatchEvent(new HashChangeEvent("hashchange"));
        target?.scrollIntoView({ block: "start" });
        return !!moves;
      }
      if (main && main.scrollTop > 0) {
        pushPlace(window.location.pathname);
        main.scrollTo({ top: 0 });
        return true;
      }
      return false;
    };
    if (onLeave) {
      // Same page from the menu: a move is a new entry on top of the menu's;
      // no move — just close the menu (pop its entries).
      onLeave();
      if (!jump()) onClose();
    } else {
      jump();
    }
  };

  /** A contents link (cover, part, chapter) out of the mobile menu. */
  const leaveTo = (e: React.MouseEvent, href: string) => {
    const strip = (p: string) => p.replace(/\/+$/, "");
    if (strip(href) !== strip(pathname)) {
      // The Link navigates (a new entry on top of the menu's).
      if (onLeave) onLeave(true);
      else onClose();
      return;
    }
    // The page already shown: back to its top (a step if that moves).
    e.preventDefault();
    const main = mainEl();
    if (onLeave && main && main.scrollTop > 0) {
      onLeave();
      pushPlace(window.location.pathname);
      main.scrollTo({ top: 0 });
    } else {
      onClose();
    }
  };

  /** Open a contents target from a button (a chapter row with subsections). */
  const openHref = (e: React.MouseEvent, href: string) => {
    const strip = (p: string) => p.replace(/\/+$/, "");
    if (strip(href) !== strip(pathname)) {
      if (onLeave) onLeave(true);
      else onClose();
      router.push(href);
      return;
    }
    leaveTo(e, href);
  };

  const prepared = useMemo(
    () => (searchEntries ? searchEntries.map(prepare) : null),
    [searchEntries]
  );

  const normalizedQuery = normalizeText(searchQuery.trim());

  // Contents order: front matter, then each part heading with its chapters.
  const layout = useMemo(
    () => tocLayout(sections.map((s) => s.id), parts),
    [sections, parts]
  );
  const sectionById = useMemo(() => new Map(sections.map((s) => [s.id, s])), [sections]);
  const partById = useMemo(() => new Map(parts.map((p) => [p.id, p])), [parts]);
  /** section id -> id of the part it belongs to */
  const partOfSection = useMemo(() => {
    const m = new Map<string, string>();
    parts.forEach((p) => p.sections.forEach((id) => m.set(id, p.id)));
    // The Introduction group: its chapters are listed inside it, like a part's.
    sections.forEach((s) => s.members?.forEach((id) => m.set(id, s.id)));
    return m;
  }, [parts, sections]);
  const currentPartId =
    selectedId === null
      ? null
      : partById.has(selectedId)
        ? selectedId
        : (partOfSection.get(selectedId) ??
          (sectionById.get(selectedId)?.members?.length ? selectedId : null));
  const [isPartOpen, togglePart] = usePartsOpen(selectedId, currentPartId);

  // Menu: its history entry keeps the parts (and chapters) as they are now
  // (for "back"). A fresh opening (no saved state yet) starts with only the
  // current chapter expanded; "back" / reload put the saved state back.
  useLayoutEffect(() => {
    if (!onLeave) return;
    try {
      const st = window.history.state as Record<string, unknown> | null;
      if (typeof st?.apParts === "string") return;
      resetChapters();
      if (isMenuEntry(st)) patchState({ apParts: partsSnapshot() });
    } catch {
      // history unavailable
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /**
   * A part heading or a chapter with subsections tapped (id: part id or
   * chapterKey). In the menu, expanding is a step of its own (a history
   * entry: "back" collapses it again); collapsing the group this very entry
   * expanded is "back"; any other collapse updates the entry.
   */
  const onPartTap = (id: string, markId?: string) => {
    const opening = !isPartOpen(id);
    togglePart(id);
    if (!onLeave) return;
    try {
      const st = window.history.state as Record<string, unknown> | null;
      if (!isMenuEntry(st)) return;
      if (opening) {
        saveNavScroll();
        pushOverlay({ apParts: partsSnapshot(), apExp: id, apDepth: menuDepth(st) + 1 });
      } else if (st?.apExp === id) {
        // Collapsing = "back" to the step before; the tapped heading stays
        // lit there (marked once that step is current again).
        if (markId) {
          window.addEventListener("popstate", () => window.setTimeout(() => mark(markId), 0), { once: true });
        }
        window.history.back();
      } else {
        patchState({ apParts: partsSnapshot() });
      }
    } catch {
      // history unavailable: the part still toggles
    }
  };

  // Full-text results (once the index is loaded).
  const results = useMemo<SearchResult[] | null>(() => {
    if (!normalizedQuery || !prepared) return null;
    const titleHits: SearchResult[] = [];
    const textHits: SearchResult[] = [];
    for (const p of prepared) {
      const inTitle = p.nTitle.includes(normalizedQuery);
      const pos = p.nText.indexOf(normalizedQuery);
      if (!inTitle && pos < 0) continue;
      const hit = {
        entry: p.entry,
        snippet: makeSnippet(p, pos, normalizedQuery.length),
      };
      (inTitle ? titleHits : textHits).push(hit);
    }
    return [...titleHits, ...textHits].slice(0, MAX_RESULTS);
  }, [prepared, normalizedQuery]);

  // Title-only filtering (before the index has loaded, or if it failed).
  const filteredSections = sections.filter((section) => {
    if (!normalizedQuery) return true;
    const matchesTitle = normalizeText(section.title).includes(normalizedQuery);
    const matchesSubsection = section.subsections?.some((sub) =>
      normalizeText(sub.title).includes(normalizedQuery)
    );
    return matchesTitle || matchesSubsection;
  });

  /**
   * A chapter row. A chapter with subsections is a disclosure row (like the
   * parts): a tap expands / collapses its list in the contents and does not
   * navigate (a second tap opens the chapter at its top); the list holds its
   * subsections. A chapter without subsections is a link. Rows are at
   * least 44px tall and tappable over their full width.
   */
  const renderSection = (section: TocSection) => {
    const isSelected = selectedId === section.id;
    const hasSubs = (section.subsections?.length ?? 0) > 0;
    const key = chapterKey(section.id);
    const isOpen = hasSubs && isPartOpen(key);
    const listId = `toc-ch-${section.id}`;
    const rowId = `sec:${section.id}`;
    const atStart = isSelected && activeSubId === null;
    // One highlight only: the chapter row while reading its beginning (or
    // while its list is closed), else the subsection being read. No
    // «Начало главы» row (Satkirti, 06.10.2026).
    const rowLit = lit(rowId, isSelected && (!isOpen || atStart));
    const rowClass = `sidebar-link w-full min-h-[44px] text-left px-5 py-3 flex items-start justify-between gap-2 transition-colors ${
      rowLit
        ? "bg-[#FAF3E8] border-l-3 border-[#B8860B]"
        : "hover:bg-[#FDF8F0] border-l-3 border-transparent"
    }`;
    const label = (
      <span
        className={`text-sm leading-snug ${
          rowLit ? "font-semibold text-[#B8860B]" : "text-[#2C1810]"
        }`}
      >
        {section.num && <span className="heading-num">{`${section.num}.`}</span>}
        {section.title}
      </span>
    );
    const subClass = (active: boolean) =>
      `sidebar-link -ml-px flex items-center min-h-[44px] w-full text-left px-4 py-2 text-xs border-l-2 transition-colors ${
        active
          ? "bg-[#FAF3E8] border-[#B8860B] text-[#B8860B] font-semibold"
          : "border-transparent text-[#5C3D2E] hover:text-[#B8860B] hover:bg-[#FDF8F0]"
      }`;
    return (
      <li key={section.id}>
        {hasSubs ? (
          // First tap: highlight + expand; second tap: open the chapter. The
          // chevron alone only expands / collapses the list.
          <div className="relative">
            <button
              type="button"
              onClick={(e) => {
                if (tapped === rowId) {
                  openHref(e, sectionHref(section.id));
                  return;
                }
                // The step (history entry) first, then the highlight on the
                // NEW entry — else the previous step got this row as its
                // place and "back" showed it twice (Reader v7.1).
                if (!isOpen) onPartTap(key);
                mark(rowId);
              }}
              aria-expanded={isOpen}
              aria-controls={isOpen ? listId : undefined}
              aria-current={isSelected ? "page" : undefined}
              data-toc-chapter={section.id}
              data-toc-lit={rowLit ? "" : undefined}
              className={`${rowClass} pr-12`}
            >
              {label}
            </button>
            <button
              type="button"
              onClick={() => {
                onPartTap(key, rowId);
                mark(rowId);
              }}
              aria-expanded={isOpen}
              aria-controls={isOpen ? listId : undefined}
              aria-label={section.title}
              data-toc-toggle={section.id}
              className="absolute right-0 top-0 flex h-[44px] w-[44px] items-center justify-center"
            >
              <svg
                aria-hidden="true"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#B8860B"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className={`shrink-0 transition-transform ${isOpen ? "rotate-90" : ""}`}
              >
                <polyline points="9 6 15 12 9 18" />
              </svg>
            </button>
          </div>
        ) : (
          <Link
            href={sectionHref(section.id)}
            onClick={(e) => {
              if (secondTap(e, rowId)) leaveTo(e, sectionHref(section.id));
            }}
            aria-current={isSelected ? "page" : undefined}
            data-toc-lit={rowLit ? "" : undefined}
            className={rowClass}
          >
            {label}
          </Link>
        )}

        {/* Subsections of an expanded chapter */}
        {isOpen && (
          <ul id={listId} className="ml-6 border-l border-[#E8DCC8]">
            {section.subsections.map((sub) => {
              const isActive = isSelected && activeSubId === sub.id;
              const subRow = `sub:${section.id}#${sub.id}`;
              const subLit = lit(subRow, isActive);
              return (
                <li key={sub.id}>
                  <Link
                    href={sectionHref(section.id, sub.id)}
                    onClick={(e) => {
                      if (!secondTap(e, subRow)) return;
                      if (isSelected) selectSub(sub.id);
                      followLink(e, section.id, sub.id);
                    }}
                    aria-current={isActive ? "location" : undefined}
                    data-toc-lit={subLit ? "" : undefined}
                    className={subClass(subLit)}
                  >
                    <span>
                      {sub.num && <span className="heading-num">{`${sub.num}.`}</span>}
                      {sub.title}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </li>
    );
  };

  /**
   * Heading of a group of the contents — a part («I. Храмовый стандарт») or
   * the Introduction: a tap expands / collapses it (a second tap collapses)
   * and highlights it like any other row, so the highlight always follows
   * the reader's last step (Satkirti, 06.10.2026).
   */
  const renderGroupHeading = (
    groupId: string,
    label: React.ReactNode,
    isOpen: boolean,
    listId: string,
    byDefault: boolean,
  ) => {
    const headId = `grp:${groupId}`;
    const on = lit(headId, byDefault);
    return (
      <div
        className={`px-5 py-1 border-l-3 transition-colors ${
          on ? "bg-[#FAF3E8] border-[#B8860B]" : "border-transparent"
        }`}
      >
        {/* The heading text and its chevron are the button (no invisible
            strip to the edge — UI rule 1). */}
        <button
          type="button"
          onClick={() => {
            onPartTap(groupId, headId);
            mark(headId);
          }}
          aria-expanded={isOpen}
          aria-controls={isOpen ? listId : undefined}
          data-toc-group={groupId}
          data-toc-lit={on ? "" : undefined}
          className={`inline-flex items-start gap-1.5 py-1 text-left rounded-sm hover:text-[#B8860B] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#B8860B]/40 transition-colors ${
            on ? "text-[#B8860B]" : "text-[#9C7A4E]"
          }`}
        >
          <svg
            aria-hidden="true"
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`shrink-0 mt-px transition-transform ${isOpen ? "rotate-90" : ""}`}
          >
            <polyline points="9 6 15 12 9 18" />
          </svg>
          <span className="text-[11px] uppercase tracking-[0.12em] font-semibold leading-snug">{label}</span>
        </button>
      </div>
    );
  };

  /** The Introduction group: its heading, then its chapters (no numbers). */
  const renderFrontGroup = (head: TocSection) => {
    const isOpen = isPartOpen(head.id);
    const listId = `toc-grp-${head.id}`;
    const members = (head.members ?? [])
      .map((id) => sectionById.get(id))
      .filter((s): s is TocSection => s !== undefined);
    // Default highlight: the Introduction's own page, or (group closed) a page inside it.
    const here = selectedId === head.id || (!isOpen && currentPartId === head.id);
    return (
      <li key={`grp-${head.id}`} className="mt-2 border-t border-[#E8DCC8] pt-2">
        {renderGroupHeading(head.id, head.title, isOpen, listId, here)}
        {isOpen && (
          <ul id={listId} className="space-y-0.5">
            {members.map(renderSection)}
          </ul>
        )}
      </li>
    );
  };

  return (
    <aside className="flex flex-col h-full bg-white border-r border-[#E8DCC8]">
      {/* Header */}
      <div className="px-5 py-4 border-b border-[#E8DCC8]">
      <div className="flex items-center justify-between gap-3">
        <Link
          href={localeHref(lang)}
          onClick={(e) => leaveTo(e, localeHref(lang))}
          title={t(ui, "sidebar.cover")}
          className="flex items-center gap-2 min-w-0 rounded-sm hover:opacity-80 transition-opacity"
        >
          <svg
            aria-hidden="true"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#B8860B"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          </svg>
          <h2
            className="text-lg font-semibold leading-snug break-words"
            style={{ color: "#B8860B" }}
          >
            {t(ui, "sidebar.contents")}
          </h2>
        </Link>
        {/* Mobile close button */}
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-[#F5E6C8] transition-colors"
          aria-label={t(ui, "sidebar.closeMenu")}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#2C1810"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
        {/* Language menu on its own row so the title never truncates
            (also in the reader's «Аа» panel) */}
        <div className="mt-3">{languageSwitcher}</div>
      </div>

      {/* Search. Enter / the keyboard's "Search"/"Go" key submits the form:
          the input is blurred so the on-screen keyboard closes and the live
          results stay in view (UI rule 6). */}
      <div className="px-4 py-3 border-b border-[#E8DCC8]">
        <form
          role="search"
          action="#"
          className="relative"
          onSubmit={(e) => {
            e.preventDefault();
            searchInputRef.current?.blur();
          }}
        >
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#B8860B"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            ref={searchInputRef}
            type="search"
            enterKeyHint="search"
            inputMode="search"
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
            aria-label={t(ui, "search.placeholder")}
            placeholder={t(ui, "search.placeholder")}
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            onFocus={onSearchFocus}
            className="search-input w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-[#E8DCC8] bg-[#FDF8F0] text-[#2C1810] placeholder-[#B8860B]/50 focus:outline-none focus:border-[#B8860B] focus:ring-1 focus:ring-[#B8860B]/30 transition-colors"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => onSearchChange("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#5C3D2E] hover:text-[#2C1810]"
              aria-label={t(ui, "search.clear")}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          )}
        </form>
      </div>

      {/* Verse panels: collapsed by default, these switches expand all */}
      <div className="px-5 py-2 border-b border-[#E8DCC8]">
        {hasWbw && (
          <PrefSwitch
            label={t(ui, "sidebar.showAllWbw")}
            checked={showAllWbw}
            onChange={setShowAllWbw}
          />
        )}
        <PrefSwitch
          label={t(ui, "sidebar.showAllTranslations")}
          checked={showAllTranslations}
          onChange={setShowAllTranslations}
        />
        {offline && !offline.complete && offline.total > 0 && (
          <p className="text-[11px] text-[#5C3D2E] mt-1" data-offline-progress="">
            {t(ui, "offline.progress", { n: String(Math.floor((offline.done / offline.total) * 100)) })}
          </p>
        )}
      </div>

      {/* Sections list / search results */}
      <nav ref={navRef} className="flex-1 overflow-y-auto sidebar-scroll py-2">
        {results ? (
          results.length === 0 ? (
            <p className="px-5 py-4 text-sm text-[#5C3D2E] italic">
              {t(ui, "search.noResults")}
            </p>
          ) : (
            <ul className="space-y-0.5">
              {results.map(({ entry, snippet }) => (
                <li key={`${entry.section}#${entry.anchor ?? ""}`}>
                  <Link
                    href={sectionHref(entry.section, entry.anchor)}
                    onClick={(e) => followLink(e, entry.section, entry.anchor)}
                    className="block w-full text-left px-5 py-3 border-l-3 border-transparent hover:bg-[#FDF8F0] transition-colors"
                  >
                    <span className="block text-sm leading-snug text-[#2C1810]">
                      {entry.title}
                    </span>
                    {entry.anchor && (
                      <span className="block text-xs text-[#B8860B]/80 mt-0.5">
                        {entry.sectionTitle}
                      </span>
                    )}
                    {(snippet.before || snippet.match || snippet.after) && (
                      <span className="block text-xs leading-relaxed text-[#5C3D2E] mt-1">
                        {snippet.before}
                        {snippet.match && (
                          <mark className="bg-[#F5E6C8] text-[#2C1810] rounded-sm">
                            {snippet.match}
                          </mark>
                        )}
                        {snippet.after}
                      </span>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          )
        ) : filteredSections.length === 0 ? (
          <p className="px-5 py-4 text-sm text-[#5C3D2E] italic">
            {t(ui, "search.noSections")}
          </p>
        ) : (
          <ul className="space-y-0.5">
            {/* Book cover (the language's home page) */}
            {!normalizedQuery && (
              <li>
                <Link
                  href={localeHref(lang)}
                  onClick={(e) => {
                    if (secondTap(e, "cover")) leaveTo(e, localeHref(lang));
                  }}
                  aria-current={selectedId === null ? "page" : undefined}
                  data-toc-cover=""
                  data-toc-lit={lit("cover", selectedId === null) ? "" : undefined}
                  className={`sidebar-link w-full text-left px-5 py-3 flex items-center gap-2 transition-colors ${
                    lit("cover", selectedId === null)
                      ? "bg-[#FAF3E8] border-l-3 border-[#B8860B]"
                      : "hover:bg-[#FDF8F0] border-l-3 border-transparent"
                  }`}
                >
                  <svg
                    aria-hidden="true"
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#B8860B"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="shrink-0"
                  >
                    <path d="M3 10.5 12 3l9 7.5" />
                    <path d="M5 9.5V21h14V9.5" />
                  </svg>
                  <span
                    className={`text-sm leading-snug ${
                      lit("cover", selectedId === null)
                        ? "font-semibold text-[#B8860B]"
                        : "text-[#2C1810]"
                    }`}
                  >
                    {t(ui, "sidebar.cover")}
                  </span>
                </Link>
              </li>
            )}
            {normalizedQuery
              ? filteredSections.map(renderSection)
              : layout.map((item) => {
                  if (item.kind === "section") {
                    // Chapters of a part (or of the Introduction) are listed inside its group.
                    if (partOfSection.has(item.id)) return null;
                    const section = sectionById.get(item.id);
                    if (section?.members?.length) return renderFrontGroup(section);
                    return section ? renderSection(section) : null;
                  }
                  const part = partById.get(item.id);
                  if (!part) return null;
                  const isOpen = isPartOpen(part.id);
                  const listId = `toc-part-${part.id}`;
                  const isPartSelected = selectedId === part.id;
                  const chapters = part.sections
                    .map((id) => sectionById.get(id))
                    .filter((s): s is TocSection => s !== undefined);
                  return (
                    <li key={`part-${part.id}`} className="mt-2 border-t border-[#E8DCC8] pt-2">
                      {renderGroupHeading(
                        part.id,
                        <>
                          <span className="mr-1.5">{`${part.numeral}.`}</span>
                          {part.title}
                        </>,
                        isOpen,
                        listId,
                        !isOpen && currentPartId === part.id && !isPartSelected,
                      )}
                      {isOpen && (
                        <ul id={listId} className="space-y-0.5">
                          {chapters.length > 0 ? (
                            chapters.map(renderSection)
                          ) : (
                            // A part in preparation: its one page.
                            <li>
                              <Link
                                href={sectionHref(part.id)}
                                onClick={(e) => {
                                  if (secondTap(e, `part:${part.id}`)) leaveTo(e, sectionHref(part.id));
                                }}
                                aria-current={isPartSelected ? "page" : undefined}
                                data-toc-lit={lit(`part:${part.id}`, isPartSelected) ? "" : undefined}
                                className={`sidebar-link w-full text-left px-5 py-3 block border-l-3 transition-colors ${
                                  lit(`part:${part.id}`, isPartSelected)
                                    ? "bg-[#FAF3E8] border-[#B8860B]"
                                    : "hover:bg-[#FDF8F0] border-transparent"
                                }`}
                              >
                                <span
                                  className={`text-sm leading-snug italic ${
                                    lit(`part:${part.id}`, isPartSelected) ? "text-[#B8860B]" : "text-[#5C3D2E]"
                                  }`}
                                >
                                  {t(ui, "part.empty")}
                                </span>
                              </Link>
                            </li>
                          )}
                        </ul>
                      )}
                    </li>
                  );
                })}
          </ul>
        )}
      </nav>
    </aside>
  );
}
