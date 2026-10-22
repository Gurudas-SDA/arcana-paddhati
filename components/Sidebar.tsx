"use client";

import { useOfflineProgress, useOfflineSave } from "@/lib/offlineProgress";
import {
  BOOKMARK_TOAST_END_EVENT,
  BOOKMARKS_EVENT,
  bookmarkAt,
  defaultBookmarkName,
  hasExactPlace,
  ownName,
  placeBookmark,
  readBookmarks,
  removeBookmark,
  renameBookmark,
  type Bookmark,
} from "@/lib/bookmarks";
import BookmarkNameDialog from "@/components/BookmarkNameDialog";
import React, {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  matchRanges,
  normalizeText,
  tocLayout,
  type SearchEntry,
  type TocPart,
  type TocSection,
} from "@/lib/book";
import { localeHref, parsePath, t, type UiDict } from "@/lib/i18n";
import { BASE_PATH } from "@/lib/basePath";
import {
  entryView,
  guardRouterPushes,
  isMenuEntry,
  main as mainEl,
  menuDepth,
  patchState,
  pushOverlay,
  pushPlace,
  setView,
} from "@/lib/navHistory";
import { setPendingSearchMark } from "@/lib/searchMark";
import { bookTarget, followBookLink, readingHref } from "@/lib/readingFlow";
import { useReadingSubsection } from "@/lib/readingPosition";

interface SidebarProps {
  sections: TocSection[];
  /** Parts (I, II, …) grouping the chapters; headings in the contents list. */
  parts: TocPart[];
  /** Language of the current URL (links stay in it). */
  lang: string;
  ui: UiDict;
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
  onLeave?: (navigating?: boolean, href?: string) => void;
  /** A65: the page of a followed link is loading (the menu waits for it). */
  navigating?: boolean;
  /** A65 (Codex 10.10): that page did not come (load failed / timed out) — the
   *  tapped row says so quietly; one more tap on it tries again. */
  navFailed?: boolean;
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

function hashId(): string | null {
  const h = window.location.hash.slice(1);
  if (!h) return null;
  try {
    return decodeURIComponent(h);
  } catch {
    return h;
  }
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
  // paint, so it never flashes closed). Not on a menu step that already keeps
  // its open lists (reload, "back" / "forward" to it): there the saved state
  // is put back exactly — a group the reader collapsed stays collapsed
  // (Reader v7.6.1, Codex review of v7.5).
  useLayoutEffect(() => {
    if (!currentPartId) return;
    try {
      const st = window.history.state as Record<string, unknown> | null;
      if (isMenuEntry(st) && typeof entryView(st).apParts === "string") return;
    } catch {
      // history unavailable: arrival as usual
    }
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

/** Every group and every chapter list of the contents closed: the base view
 *  (Reader v7.5, Satkirti 07.10.2026: «Обложка» works like home). */
function baseParts(parts: TocPart[], sections: TocSection[]): Record<string, boolean> {
  const st: Record<string, boolean> = {};
  parts.forEach((p) => (st[p.id] = false));
  sections.forEach((s) => {
    if (s.members?.length) st[s.id] = false;
    if ((s.subsections?.length ?? 0) > 0) st[chapterKey(s.id)] = false;
  });
  return st;
}

/** Entry view key (lib/navHistory.ts): scroll offset of the contents / results list. */
const NAV_SCROLL = "apNav";
/** Entry view key: the search result the reader followed out of this menu step. */
const RESULT_KEY = "apResult";

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

/** The search query's occurrences in `text` marked (Reader v7.8, Satkirti
 *  07.10.2026: the found word stands out in every result). */
function Marked({ text, nq }: { text: string; nq: string }) {
  const ranges = matchRanges(text, nq);
  if (!ranges.length) return <>{text}</>;
  const out: React.ReactNode[] = [];
  let at = 0;
  ranges.forEach(([a, b], k) => {
    if (a > at) out.push(text.slice(at, a));
    out.push(
      <mark key={k} className="search-mark" data-search-mark="">
        {text.slice(a, b)}
      </mark>,
    );
    at = b;
  });
  if (at < text.length) out.push(text.slice(at));
  return <>{out}</>;
}

/** Keep the opened row and its first child visible (rule 9.13). A chapter
 *  collapsing above it can leave its top clipped even when the branch fits
 *  below; native scroll anchoring does not necessarily compensate in full. */
function revealOpened(nav: HTMLElement | null, rowId: string): boolean {
  if (!nav) return false;
  const row = [...nav.querySelectorAll<HTMLElement>("[data-toc-row]")].find((el) => el.dataset.tocRow === rowId);
  const group = row?.closest("li");
  if (!row || !group) return false;
  const n = nav.getBoundingClientRect();
  const g = group.getBoundingClientRect();
  if (row.getBoundingClientRect().top >= n.top && g.bottom <= n.bottom + 1) return false;
  const before = nav.scrollTop;
  const align = () => {
    // Round toward the visible side on scrollers with integral scrollTop.
    nav.scrollTop = Math.floor(nav.scrollTop + row.getBoundingClientRect().top - n.top);
  };
  const correct = () => {
    const r = row.getBoundingClientRect();
    const first = group.querySelector<HTMLElement>("ul [data-toc-row]")?.getBoundingClientRect();
    if (r.top < n.top || r.bottom > n.bottom || (first && first.bottom > n.bottom)) align();
  };
  align();
  correct();
  correct();
  return nav.scrollTop !== before;
}

export default function Sidebar({
  sections,
  parts,
  lang,
  ui,
  searchQuery,
  onSearchChange,
  onSearchFocus,
  searchEntries,
  onClose,
  onLeave: onLeaveProp,
  navigating = false,
  navFailed = false,
}: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchInputRef = useRef<HTMLInputElement>(null);
  /** The scrolling list of the contents / search results. */
  const navRef = useRef<HTMLElement>(null);

  /** The menu entry keeps the list's scroll offset: "back" to it reopens the
   *  contents / results exactly where the reader left them. */
  const saveNavScroll = () => {
    try {
      if (isMenuEntry()) setView({ [NAV_SCROLL]: navRef.current?.scrollTop ?? 0 });
    } catch {
      // history unavailable
    }
  };
  /** A65: the row whose page is loading (marked «загружается…» while `navigating`). */
  const [loadingRow, setLoadingRow] = useState<string | null>(null);
  const onLeave = onLeaveProp
    ? (navigating?: boolean, row?: HTMLElement | null) => {
        saveNavScroll();
        if (navigating) setLoadingRow(row?.dataset.tocRow ?? row?.dataset.result ?? null);
        onLeaveProp(navigating, (row as HTMLAnchorElement | null | undefined)?.href);
      }
    : undefined;
  /** Props of a row while its page loads: the mark for the eye and for screen readers. */
  const loadingProps = (id: string) =>
    navigating && loadingRow === id ? { "data-toc-loading": "", "aria-busy": true as const } : {};
  const loadingNote = (id: string) =>
    navigating && loadingRow === id ? (
      // The visible mark only; screen readers hear «загружается» from the live
      // region outside the menu (AppShell, A65 a11y — not inside aria-busy).
      <span className="toc-loading-note">
        <span aria-hidden="true" className="toc-loading-spin" />
        {t(ui, "sidebar.loading")}
      </span>
    ) : navFailed && loadingRow === id ? (
      // The load failed: nothing busy any more, so one tap opens the row
      // again (the live region announces the same text).
      <span className="toc-loading-note toc-failed-note" data-toc-failed="">
        {t(ui, "sidebar.loadFailed")}
      </span>
    ) : null;

  // Put the list's scroll offset of this menu entry back: on mount (the menu
  // reopened by "back" or a reload) and on "back" between menu steps. Applied
  // a few times while the restored rows (expanded parts / chapters) settle.
  useLayoutEffect(() => {
    let timers: number[] = [];
    const apply = () => {
      const v = entryView()[NAV_SCROLL];
      if (typeof v === "number" && navRef.current) {
        // This entry recorded where the list stood: putting the reader back
        // exactly where he was wins over anything else (rule 10). Bringing the
        // place being read into view would move the list under him.
        navRef.current.scrollTop = v;
        return;
      }
      // Nothing recorded: a freshly opened contents comes to the reader, with
      // the row he is reading in view (Apple Books / Kindle).
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
  const [activeSubId, selectSub] = useReadingSubsection(pathname, subIds.join("|"));

  /**
   * ONE TAP (Satkirti 13.10.2026, «всем управляем стандартом»): a tap on a row
   * does the row's work at once, and the highlight in the contents means one
   * thing only — the place being read. It comes from the reading position (the
   * chapter of the URL, which the continuous book keeps current, and
   * `activeSubId` from the scroll spy), never from where the reader tapped.
   * This is how Apple Books and Kindle mark the current chapter, and it keeps
   * rule 9 literally: after «Назад» the highlight still shows the place being
   * read, because taps do not move it. The earlier two-tap mode is gone.
   */
  /** Row highlighted: the place being read. Nothing else moves it. */
  const lit = (_id: string, byDefault: boolean) => byDefault;
  /**
   * One step in the contents: highlight `id` and (optionally) set what is
   * open — as a NEW history entry (menu depth +1), so "back" returns to the
   * step before exactly as it was.
   */
  const step = (id: string, open?: Record<string, boolean>) => {
    if (open) setPartsState(open);
    try {
      const st = window.history.state as Record<string, unknown> | null;
      if (!isMenuEntry(st)) return;
      saveNavScroll();
      if (navigating) {
        // A page is loading (A65): this choice will replace it — no step of its
        // own in history, so the new page is ONE entry on top of the menu's.
        setView({ apParts: partsSnapshot() }, [RESULT_KEY, "apExp"]);
      } else {
        // One write: the step's entry with its own view.
        pushOverlay(
          {
            // Proposal: a menu attached to a chapter navigation is not stacked
            // over the previous reading place. Closing it keeps this chapter.
            apDepth: st?.apDepth === 0 ? 0 : menuDepth(st) + 1,
          },
          { apParts: partsSnapshot() },
          [RESULT_KEY, "apExp"],
        );
      }
    } catch {
      // history unavailable: the highlight still shows
    }
  };
  const chapterArrival = useRef<{
    sectionId: string;
    rowId: string;
    parts: Record<string, boolean>;
    query: string;
  } | null>(null);
  useEffect(() => {
    const cancel = () => { chapterArrival.current = null; };
    window.addEventListener("popstate", cancel);
    return () => window.removeEventListener("popstate", cancel);
  }, []);
  useLayoutEffect(() => {
    const arrival = chapterArrival.current;
    if (!arrival || selectedId !== arrival.sectionId) return;
    chapterArrival.current = null;
    setPartsState(arrival.parts);
    // Navigation already pushed the action's entry. Attach its expanded
    // contents to that entry without adding a highlight/overlay-only step.
    patchState({
      apMenu: true,
      apDepth: 0,
      apParts: JSON.stringify(arrival.parts),
      apQuery: arrival.query,
      [NAV_SCROLL]: navRef.current?.scrollTop ?? 0,
    });
    mainEl()?.scrollTo({ top: 0 });
    // Rule 9.13: the arrival collapses the chapter left (its list closes
    // above the tapped row). WebKit has no scroll anchoring, so the row moved
    // up out of the list (iPhone: 96 px above it) whenever the page came later
    // than the tap's own reveal (+120 ms). Reveal it again now.
    setOpenedRow({ id: arrival.rowId, at: Date.now() });
  }, [pathname, selectedId]);
  useOfflineProgress();
  // Vraja Lila msg 5318 (state 5): the same wording and the same count in parts as on the cover, shorter.
  const offlineSave = useOfflineSave();

  const normalizedQuery = normalizeText(searchQuery.trim());

  // Tabs «Содержание · Закладки» (Vraja Lila msg 5316 p. 7, plan «Закладки» B3):
  // the tab is part of the entry's view (setView), so «Назад» comes back to it.
  const [tab, setTab] = useState<"contents" | "bookmarks">("contents");
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  useEffect(() => {
    try {
      if (entryView().apTab === "bookmarks") setTab("bookmarks");
    } catch {
      // history unavailable
    }
  }, []);
  useEffect(() => {
    if (tab === "bookmarks") setBookmarks(readBookmarks());
  }, [tab]);
  // Removed with the icon on its row (Vraja Lila msg 5439/5440, variant 2а): the
  // row stays in place, pale, with an empty icon, until the top bar's toast
  // «Закладка убрана · Отменить» is over; «Отменить» puts it back.
  const [paleRows, setPaleRows] = useState<Record<string, Bookmark>>({});
  useEffect(() => {
    if (tab !== "bookmarks") return;
    const update = () => setBookmarks(readBookmarks());
    const over = () => setPaleRows({});
    window.addEventListener(BOOKMARKS_EVENT, update);
    window.addEventListener(BOOKMARK_TOAST_END_EVENT, over);
    return () => {
      window.removeEventListener(BOOKMARKS_EVENT, update);
      window.removeEventListener(BOOKMARK_TOAST_END_EVENT, over);
    };
  }, [tab]);
  const bookmarkRows = useMemo(() => {
    const pale = Object.values(paleRows).filter((p) => !bookmarks.some((b) => b.id === p.id));
    return [...bookmarks, ...pale].sort((a, b) => b.time - a.time);
  }, [bookmarks, paleRows]);
  const removeBookmarkRow = (b: Bookmark) => {
    setPaleRows((cur) => ({ ...cur, [b.id]: b }));
    removeBookmark(b.id);
  };
  const chooseTab = (next: "contents" | "bookmarks") => {
    setTab(next);
    try {
      if (next === "bookmarks") setView({ apTab: "bookmarks" });
      else setView({}, ["apTab"]);
    } catch {
      // history unavailable
    }
  };
  /** A renamed bookmark (V34, Vraja Lila msg 5869): only its name — no chapter
   *  line, no date («никаких мелких шрифтов»). */
  const bookmarkLine = (b: Bookmark) => {
    const sec = sections.find((x) => x.id === b.section);
    if (!sec) return null;
    if (b.name) return { head: b.name, second: null, named: true };
    const head = sec.num ? `${sec.num}. ${sec.title}` : sec.title;
    const sub = b.anchor ? sec.subsections.find((x) => x.id === b.anchor) : undefined;
    return { head, second: sub ? (sub.num ? `${sub.num}. ${sub.title}` : sub.title) : null, named: false };
  };
  /** The pencil on a row: the same name window (V34). */
  const [renaming, setRenaming] = useState<{ id: string; name: string; def: string } | null>(null);
  const askRename = (b: Bookmark) => {
    const sec = sections.find((x) => x.id === b.section);
    if (!sec) return;
    const def = defaultBookmarkName(sec, b.anchor ?? null);
    setRenaming({ id: b.id, name: b.name ?? def, def });
  };
  const confirmRename = (name: string) => {
    const r = renaming;
    setRenaming(null);
    if (r) renameBookmark(r.id, ownName(name, r.def));
  };
  const showBookmarks = tab === "bookmarks" && !normalizedQuery;
  // The bookmark on the place being read (Vraja Lila msg 5436): the same place
  // the ribbon button shows as set (chapter + subsection from the scroll spy;
  // no subsection — the chapter). Several there — the newest (the list is
  // newest first). Lit exactly like the current row of «Содержание» (rule 9.2).
  const litBookmarkId = selectedId ? bookmarkAt(bookmarks, selectedId, activeSubId ?? null)?.id : undefined;
  const bookmarksRef = useRef<HTMLDivElement>(null);
  // Opening the tab brings the lit bookmark into view, as «Содержание» does (9.12).
  useLayoutEffect(() => {
    if (!showBookmarks) return;
    const box = bookmarksRef.current;
    const row = box?.querySelector<HTMLElement>("[data-bookmark-lit]");
    if (!box || !row) return;
    const n = box.getBoundingClientRect();
    const r = row.getBoundingClientRect();
    if (r.top >= n.top && r.bottom <= n.bottom) return;
    box.scrollTop += r.top - n.top - (n.height - r.height) / 2;
  }, [showBookmarks, bookmarks, litBookmarkId]);

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
    anchor: string | undefined,
    fromSearch = false,
  ) => {
    const strip = (p: string) => p.replace(/\/+$/, "");
    const samePage = strip(localeHref(lang, sectionId)) === strip(pathname);
    // A search result: the found word is marked at the place it opens (Reader v7.8).
    if (fromSearch && normalizedQuery) setPendingSearchMark(normalizedQuery, sectionId, anchor);
    try {
      // "Back" to the results scrolls to this one again (Reader v7.2).
      if (onLeave && isMenuEntry()) setView({ [RESULT_KEY]: `${sectionId}#${anchor ?? ""}` });
    } catch {
      // history unavailable
    }
    if (followBookLink(`${BASE_PATH}${sectionHref(sectionId, anchor)}`, (moved) => {
      if (moved) onLeave?.();
      else onClose();
    })) {
      e.preventDefault();
      return;
    }
    if (!samePage) {
      // The Link navigates (a new entry on top of the menu's).
      onLeave?.(true, e.currentTarget as HTMLElement);
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
    if (followBookLink(`${BASE_PATH}${href}`, (moved) => {
      if (moved) onLeave?.();
      else onClose();
    })) {
      e.preventDefault();
      return;
    }
    const strip = (p: string) => p.replace(/\/+$/, "");
    if (strip(href) !== strip(pathname)) {
      // The Link navigates (a new entry on top of the menu's).
      if (onLeave) onLeave(true, e.currentTarget as HTMLElement);
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

  const prepared = useMemo(
    () => (searchEntries ? searchEntries.map(prepare) : null),
    [searchEntries]
  );

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
  const [isPartOpen] = usePartsOpen(selectedId, currentPartId);

  /** The row just opened by its second tap: its list is brought into view once rendered. */
  const [openedRow, setOpenedRow] = useState<{ id: string; at: number } | null>(null);
  useLayoutEffect(() => {
    if (!openedRow) return;
    const run = () => {
      if (revealOpened(navRef.current, openedRow.id)) saveNavScroll();
    };
    run();
    // again once fonts / the rows' heights settle
    const t = window.setTimeout(run, 120);
    return () => window.clearTimeout(t);
  }, [openedRow]);

  // Menu: its history entry keeps the parts (and chapters) as they are now
  // (for "back"). A fresh opening (no saved state yet) starts with only the
  // current chapter expanded; "back" / reload put the saved state back.
  useLayoutEffect(() => {
    if (!onLeave) return;
    try {
      const st = window.history.state as Record<string, unknown> | null;
      if (typeof entryView(st).apParts === "string") return;
      resetChapters();
      if (isMenuEntry(st)) setView({ apParts: partsSnapshot() });
    } catch {
      // history unavailable
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /**
   * A part heading, the Introduction or a chapter with subsections tapped
   * (`id`: part id or chapterKey; `rowId`: its highlight id). First tap:
   * highlight only. Second tap on the highlighted row: expand / collapse.
   * Each is a step of its own (Reader v7.5, Satkirti 07.10.2026).
   */
  const onDisclosureTap = (id: string, rowId: string, sectionId?: string) => {
    if (sectionId && !isPartOpen(id)) {
      const open = { ...parseParts(partsSnapshot()), [id]: true };
      if (bookTarget(sectionId)) {
        saveNavScroll();
        let navigated = false;
        const view = () => ({ apParts: JSON.stringify(open), apQuery: searchQuery, [NAV_SCROLL]: navRef.current?.scrollTop ?? 0 });
        // One write: the chapter's entry carries the expanded contents.
        followBookLink(readingHref(lang, sectionId), (moved) => {
          navigated = moved;
          if (!moved) step(rowId, open);
        }, () => ({ state: { apMenu: true, apDepth: 0 }, view: view() }));
        setPartsState(open);
        if (!navigated) setView(view());
        setOpenedRow({ id: rowId, at: Date.now() });
        return;
      }
      if (selectedId === sectionId) {
        const main = mainEl();
        if (hashId() || (main && main.scrollTop > 0)) {
          saveNavScroll();
          setPartsState(open);
          // One write: the chapter top's entry carries the expanded contents.
          pushPlace(`${BASE_PATH}${sectionHref(sectionId)}`, { apMenu: true, apDepth: 0 }, { apParts: partsSnapshot() });
          window.dispatchEvent(new HashChangeEvent("hashchange"));
          main?.scrollTo({ top: 0 });
        } else {
          step(rowId, open);
        }
      } else {
        saveNavScroll();
        chapterArrival.current = { sectionId, rowId, parts: open, query: searchQuery };
        setPartsState(open);
        // A refused push (WebKit's quota) must not become a page error.
        guardRouterPushes();
        router.push(sectionHref(sectionId), { scroll: false });
      }
      setOpenedRow({ id: rowId, at: Date.now() });
      return;
    }
    const opening = !isPartOpen(id);
    const open = { ...parseParts(partsSnapshot()), [id]: opening };
    if (chapterArrival.current) chapterArrival.current.parts = open;
    step(rowId, open);
    if (opening) setOpenedRow({ id: rowId, at: Date.now() });
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

  // "Back" from a result to the search (UI rule 6; Reader v7.2 — WebKit): the
  // query comes back at once, the results only when the index has loaded
  // (slow on iPhone). Once they are rendered, the list's offset of this step
  // is put back and the followed result is brought into view.
  const restoreUntil = useRef(0);
  useEffect(() => {
    restoreUntil.current = performance.now() + 6000;
    const onPop = () => {
      restoreUntil.current = performance.now() + 6000;
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  useEffect(() => {
    if (!results || results.length === 0) return;
    if (performance.now() > restoreUntil.current) return;
    const apply = () => {
      const nav = navRef.current;
      const st = window.history.state as Record<string, unknown> | null;
      if (!nav || !st || !isMenuEntry(st)) return;
      const view = entryView(st);
      const v = view[NAV_SCROLL];
      if (typeof v === "number") nav.scrollTop = v;
      const key = view[RESULT_KEY];
      if (typeof key !== "string") return;
      const row = [...nav.querySelectorAll<HTMLElement>("[data-result]")].find(
        (el) => el.dataset.result === key
      );
      if (!row) return;
      const n = nav.getBoundingClientRect();
      const r = row.getBoundingClientRect();
      if (r.top >= n.top && r.bottom <= n.bottom) return;
      nav.scrollTop += r.top - n.top - (n.height - r.height) / 2;
    };
    apply();
    requestAnimationFrame(apply);
    const timers = [80, 250, 600].map((ms) => window.setTimeout(apply, ms));
    return () => timers.forEach((id) => window.clearTimeout(id));
  }, [results]);

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
   * A chapter with subsections is a disclosure row: the approved two-tap
   * mode only expands/collapses it. The one-tap proposal also navigates to
   * its top on opening, keeping the list visible for the next pick.
   * A chapter without subsections is a link. Rows are at
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
        ? "bg-[#FAF3E8] border-l-3 border-[var(--ap-gold)]"
        : "hover:bg-[#FDF8F0] border-l-3 border-transparent"
    }`;
    const label = (
      <span
        className={`text-sm leading-snug ${
          rowLit ? "font-semibold text-[var(--ap-gold)]" : "text-[#2C1810]"
        }`}
      >
        {section.num && <span className="heading-num">{`${section.num}.`}</span>}
        {section.title}
      </span>
    );
    const subClass = (active: boolean) =>
      // Full panel width (Reader v7.8.2): the indent is padding inside the row, so the tap target and
      // the highlight band start at the panel's left edge, like the chapters and parts.
      `sidebar-link relative flex items-center min-h-[44px] w-full text-left pl-[39px] pr-4 py-2 text-xs border-l-3 transition-colors ${
        active
          ? "bg-[#FAF3E8] border-[var(--ap-gold)] text-[var(--ap-gold)] font-semibold"
          : "border-transparent text-[#5C3D2E] hover:text-[var(--ap-gold)] hover:bg-[#FDF8F0]"
      }`;
    return (
      <li key={section.id}>
        {hasSubs ? (
          // First tap: highlight only; second tap: expand / collapse its list
          // (Reader v7.5). The chevron is part of the row (the same two taps).
          <div className="relative">
            <button
              type="button"
              onClick={() => onDisclosureTap(key, rowId, section.id)}
              aria-expanded={isOpen}
              aria-controls={isOpen ? listId : undefined}
              aria-current={isSelected ? "page" : undefined}
              data-toc-chapter={section.id}
              data-toc-lit={rowLit ? "" : undefined}
              data-toc-row={rowId}
              className={`${rowClass} pr-12`}
            >
              {label}
            </button>
            <span aria-hidden="true" className="pointer-events-none absolute right-0 top-0 flex h-[44px] w-[44px] items-center justify-center">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" style={{ color: "var(--ap-gold)" }} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={`shrink-0 transition-transform ${isOpen ? "rotate-90" : ""}`}>
                <polyline points="9 6 15 12 9 18" />
              </svg>
            </span>
          </div>
        ) : (
          <Link
            href={sectionHref(section.id)}
            onClick={(e) => {
              leaveTo(e, sectionHref(section.id));
            }}
            aria-current={isSelected ? "page" : undefined}
            data-toc-lit={rowLit ? "" : undefined}
            data-toc-row={rowId}
            {...loadingProps(rowId)}
            className={rowClass}
          >
            {label}
            {loadingNote(rowId)}
          </Link>
        )}

        {/* Subsections of an expanded chapter */}
        {isOpen && (
          <ul id={listId}>
            {section.subsections.map((sub) => {
              const isActive = isSelected && activeSubId === sub.id;
              const subRow = `sub:${section.id}#${sub.id}`;
              const subLit = lit(subRow, isActive);
              return (
                <li key={sub.id}>
                  <Link
                    href={sectionHref(section.id, sub.id)}
                    onClick={(e) => {
                      if (isSelected) selectSub(sub.id);
                      followLink(e, section.id, sub.id);
                    }}
                    aria-current={isActive ? "location" : undefined}
                    data-toc-lit={subLit ? "" : undefined}
                    data-toc-row={subRow}
                    {...loadingProps(subRow)}
                    className={subClass(subLit)}
                  >
                    {/* the guide line of the list (was the list's own left border, 24px in) */}
                    <span aria-hidden="true" className="pointer-events-none absolute left-[21px] top-0 bottom-0 border-l border-[#E8DCC8]" />
                    <span>
                      {sub.num && <span className="heading-num">{`${sub.num}.`}</span>}
                      {sub.title}
                    </span>
                    {loadingNote(subRow)}
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
   * the Introduction. V37 (Vraja Lila msg 1306 / 1308, 21.10.2026): the
   * section's NAME opens the section's own page (its text / its list), the way
   * a chapter row opens its chapter; arriving there, the group is lit and
   * expanded (usePartsOpen: the current group is open), so the menu opened
   * again shows the section and its chapters. The arrow ▸ at the right is a
   * separate control: it only expands / collapses the chapters (a step of the
   * menu, no navigation).
   */
  const renderGroupHeading = (
    groupId: string,
    label: React.ReactNode,
    name: string,
    isOpen: boolean,
    listId: string,
    byDefault: boolean,
  ) => {
    const headId = `grp:${groupId}`;
    const on = lit(headId, byDefault);
    const href = sectionHref(groupId);
    return (
      // V38c (Vraja Lila msg 1321 / 1322, 22.10.2026): the lit section is ONE highlight over
      // the whole row — name and arrow ▸ share the row's background (no seam between two
      // sectors; the «одной подложкой» rule, msg 1290). Hover and the 150 ms pick-light
      // (data-menu-picked, globals.css) also colour the whole row.
      <div
        data-toc-group-row={groupId}
        className={`flex items-stretch border-l-3 transition-colors ${
          on ? "border-[var(--ap-gold)] bg-[#FAF3E8]" : "border-transparent hover:bg-[#FDF8F0]"
        }`}
      >
        <Link
          href={href}
          onClick={(e) => {
            // The section opens expanded (its chapters ready in the menu).
            const cur = parseParts(partsSnapshot());
            if (cur[groupId] === false) {
              delete cur[groupId];
              setPartsState(cur);
            }
            leaveTo(e, href);
          }}
          aria-current={selectedId === groupId ? "page" : undefined}
          data-toc-group={groupId}
          data-toc-lit={on ? "" : undefined}
          data-toc-row={headId}
          {...loadingProps(headId)}
          className={`sidebar-link flex flex-1 min-w-0 min-h-[44px] flex-col justify-center pl-5 pr-1 py-2 text-left hover:text-[var(--ap-gold)] transition-colors ${
            on ? "text-[var(--ap-gold)]" : "text-[#9C7A4E]"
          }`}
        >
          <span className="text-[11px] uppercase tracking-[0.12em] font-semibold leading-snug">{label}</span>
          {loadingNote(headId)}
        </Link>
        {/* The arrow: expand / collapse only (a 44 px target of its own). */}
        <button
          type="button"
          onClick={() => onDisclosureTap(groupId, headId)}
          aria-expanded={isOpen}
          aria-controls={isOpen ? listId : undefined}
          aria-label={name}
          data-toc-toggle={groupId}
          className={`sidebar-link flex min-h-[44px] w-[44px] shrink-0 items-center justify-center hover:text-[var(--ap-gold)] transition-colors ${
            on ? "text-[var(--ap-gold)]" : "text-[#9C7A4E]"
          }`}
        >
          <svg
            aria-hidden="true"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`shrink-0 transition-transform ${isOpen ? "rotate-90" : ""}`}
          >
            <polyline points="9 6 15 12 9 18" />
          </svg>
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
        {renderGroupHeading(head.id, head.title, head.title, isOpen, listId, here)}
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
            stroke="currentColor" style={{ color: "var(--ap-gold)" }}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          </svg>
          <h2
            className="contents-title text-lg font-semibold leading-snug break-words"
            style={{ color: "var(--ap-gold)" }}
          >
            {t(ui, "sidebar.contents")}
          </h2>
        </Link>
        {/* Mobile close button */}
        <button
          onClick={onClose}
          className="sidebar-close p-1 rounded text-[#2C1810] hover:bg-[#F5E6C8] transition-colors"
          aria-label={t(ui, "sidebar.closeMenu")}
        >
          {/* V33: currentColor, so the dark background repaints it (was a fixed #2C1810: 1.0:1 on the dark panel) */}
          <svg
            width="20"
            height="20"
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
      </div>
        {/* The language menu is only in the reader's «Аа» panel (Reader v7.8). */}
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
            stroke="currentColor" style={{ color: "var(--ap-gold)" }}
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
            className="search-input ds-field w-full pl-9 pr-3 py-2 text-[16px] rounded-lg bg-[#FDF8F0] text-[#2C1810] placeholder-[var(--ap-gold)]"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => onSearchChange("")}
              className="search-clear absolute right-3 top-1/2 -translate-y-1/2 text-[#5C3D2E] hover:text-[#2C1810]"
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

      {!normalizedQuery && (
        <div className="sidebar-tabs shrink-0 flex border-b border-[#E8DCC8]" role="tablist" data-sidebar-tabs="">
          {(["contents", "bookmarks"] as const).map((k) => (
            <button
              key={k}
              type="button"
              role="tab"
              aria-selected={tab === k}
              data-sidebar-tab={k}
              onClick={() => chooseTab(k)}
              className={`flex-1 px-3 py-2.5 text-sm transition-colors border-b-2 ${
                tab === k ? "border-[var(--ap-gold)] text-[#2C1810] font-semibold" : "border-transparent text-[#5C3D2E]"
              }`}
            >
              {t(ui, k === "contents" ? "sidebar.contents" : "sidebar.bookmarks")}
            </button>
          ))}
        </div>
      )}

      {/* The «show all» switches are in the «Аа» panel (Reader v7.8). */}
      {offlineSave && (offlineSave.s === "loading" || offlineSave.s === "partial") && offlineSave.t > 0 && (
        <p className="px-5 py-1.5 border-b border-[#E8DCC8] text-[11px] text-[#5C3D2E] flex items-center gap-2" data-offline-progress="">
          <span>{t(ui, offlineSave.s === "partial" ? "offline.save.partial" : "offline.save.loading")}</span>
          <span className="ml-auto tabular-nums text-[#6B5440]">
            {t(ui, "offline.save.countShort", { done: String(offlineSave.d), total: String(offlineSave.t) })}
          </span>
        </p>
      )}

      {/* Contents (Reader v7.8, Satkirti 07.10.2026): a fixed part — the title,
          the search and «Обложка» — and the list that scrolls under it. */}
      {showBookmarks && (
        <div ref={bookmarksRef} className="flex-1 min-h-0 overflow-y-auto" role="tabpanel" data-bookmarks-list="">
          {bookmarkRows.length === 0 ? (
            <p className="px-5 py-4 text-sm text-[#5C3D2E]" data-bookmarks-empty="">
              {t(ui, "bookmarks.empty")}
            </p>
          ) : (
            bookmarkRows.map((b) => {
              const line = bookmarkLine(b);
              if (!line) return null;
              // Its own block in this language (msg 5872): the chapter, then the block
              // put in place by lib/bookmarks.ts; otherwise the subsection, as before.
              const exact = hasExactPlace(b, lang);
              const href = sectionHref(b.section, exact ? undefined : (b.anchor ?? undefined));
              const isLit = b.id === litBookmarkId;
              const isPale = !bookmarks.some((x) => x.id === b.id);
              // Lit = the look of the current row in «Содержание»: background,
              // gold left bar, gold semibold title (one sign, rule 9.2). Every
              // row keeps a 3px left bar (transparent) so the text never moves.
              const titleClass = isLit ? "font-semibold text-[var(--ap-gold)]" : "";
              return (
                <div
                  key={b.id}
                  data-bookmark-row=""
                  data-bookmark-id={b.id}
                  data-bookmark-lit={isLit ? "" : undefined}
                  data-bookmark-faded={isPale ? "" : undefined}
                  className={`relative border-b border-[#E8DCC8] border-l-3 transition-colors ${
                    isLit ? "bg-[#FAF3E8] border-l-[var(--ap-gold)]" : "border-l-transparent hover:bg-[#FDF8F0]"
                  }`}
                >
                <Link
                  href={href}
                  onClick={(e) => {
                    leaveTo(e, href);
                    if (exact) placeBookmark(b);
                  }}
                  aria-current={isLit ? "location" : undefined}
                  className={`sidebar-link block w-full text-left pl-5 pr-[96px] py-3 transition-opacity ${isPale ? "opacity-45" : ""}`}
                >
                  {/* One line each, «…» at the end (V34, Vraja Lila msg 5869: «не должно рябить в глазах»). */}
                  <span className={`block truncate text-sm ${titleClass || "text-[#2C1810]"}`} data-bookmark-title="" data-bookmark-named={line.named ? "" : undefined}>{line.head}</span>
                  {line.second && <span className={`block truncate text-sm ${titleClass || "text-[#5C3D2E]"}`} data-bookmark-second="">{line.second}</span>}
                  {!line.named && (
                    <span className="block text-[11px] text-[#6B5440]" data-bookmark-date="">
                      {new Date(b.time).toLocaleDateString(lang === "en" ? "en" : lang.split("-")[0])}
                    </span>
                  )}
                </Link>
                {/* The pencil (V34, Vraja Lila msg 5869): left of the remove icon; opens the
                    name window. A 44px target. Its line thin like the other thin icons (1.5)
                    and drawn at the right side of its target, a little closer to the remove
                    icon (Vraja Lila msg 5897); the two targets still do not overlap. The drawing is
                    moved down 0.56 of its 24 units so its middle (y 2.9…20) is the icon's middle,
                    level with the bookmark icon (Vraja Lila msg 5939). */}
                <button
                  type="button"
                  className="absolute right-[44px] top-1/2 -translate-y-1/2 flex h-[44px] w-[44px] items-center justify-end pr-[3px] text-[#8B6508] disabled:cursor-default"
                  onClick={() => askRename(b)}
                  disabled={isPale}
                  aria-label={t(ui, "bookmark.rename")}
                  title={t(ui, "bookmark.rename")}
                  data-bookmark-rename=""
                >
                  <svg aria-hidden="true" width="18" height="18" viewBox="0 -0.56 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={isPale ? "opacity-45" : undefined}>
                    <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z" />
                    <path d="M14 6l3 3" />
                  </svg>
                </button>
                {/* The ribbon of the top bar, filled (Vraja Lila msg 5439/5440, frame 1):
                    a tap removes this bookmark (2а); a 44px target, outside the row link. */}
                <button
                  type="button"
                  className="absolute right-0 top-1/2 -translate-y-1/2 flex h-[44px] w-[44px] items-center justify-center text-[var(--ap-gold)] disabled:cursor-default"
                  onClick={() => removeBookmarkRow(b)}
                  disabled={isPale}
                  aria-label={t(ui, "reader.bookmarkRemove")}
                  title={t(ui, "reader.bookmarkRemove")}
                  data-bookmark-remove=""
                >
                  <svg aria-hidden="true" width="18" height="20" viewBox="0 0 18 20" fill={isPale ? "none" : "currentColor"} stroke="currentColor" strokeWidth="2" strokeLinejoin="round" className={isPale ? "opacity-45" : undefined}>
                    <path d="M3 1.5h12v17l-6-4.6-6 4.6z" />
                  </svg>
                </button>
                </div>
              );
            })
          )}
        </div>
      )}
      {renaming && (
        <BookmarkNameDialog
          ui={ui}
          mode="rename"
          initial={renaming.name}
          onConfirm={confirmRename}
          onCancel={() => setRenaming(null)}
        />
      )}
      <nav className="flex-1 min-h-0 flex flex-col" hidden={showBookmarks || undefined}>
      {!normalizedQuery && (
        <div className="toc-fixed shrink-0 pt-2 pb-1 border-b border-[#E8DCC8]">
          <Link
            href={localeHref(lang)}
            onClick={(e) => {
              // «Обложка»: one tap opens the cover and resets the contents to
              // its base view (every group and chapter closed).
              setPartsState(baseParts(parts, sections));
              if (isMenuEntry()) setView({ apParts: partsSnapshot() });
              leaveTo(e, localeHref(lang));
            }}
            aria-current={selectedId === null ? "page" : undefined}
            data-toc-cover=""
            data-toc-lit={lit("cover", selectedId === null) ? "" : undefined}
            data-toc-row="cover"
            {...loadingProps("cover")}
            className={`sidebar-link w-full text-left px-5 py-3 flex items-center gap-2 transition-colors ${
              lit("cover", selectedId === null)
                ? "bg-[#FAF3E8] border-l-3 border-[var(--ap-gold)]"
                : "hover:bg-[#FDF8F0] border-l-3 border-transparent"
            }`}
          >
            <svg
              aria-hidden="true"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor" style={{ color: "var(--ap-gold)" }}
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
                  ? "font-semibold text-[var(--ap-gold)]"
                  : "text-[#2C1810]"
              }`}
            >
              {t(ui, "sidebar.cover")}
            </span>
            {loadingNote("cover")}
          </Link>
        </div>
      )}
      <div ref={navRef as React.RefObject<HTMLDivElement>} className="toc-scroll flex-1 min-h-0 overflow-y-auto sidebar-scroll py-2">
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
                    data-result={`${entry.section}#${entry.anchor ?? ""}`}
                    {...loadingProps(`${entry.section}#${entry.anchor ?? ""}`)}
                    onClick={(e) => {
                      followLink(e, entry.section, entry.anchor, true);
                    }}
                    data-toc-lit={lit(entry.anchor ? `sub:${entry.section}#${entry.anchor}` : `sec:${entry.section}`, false) ? "" : undefined}
                    className={lit(entry.anchor ? `sub:${entry.section}#${entry.anchor}` : `sec:${entry.section}`, false)
                      ? "block w-full text-left px-5 py-3 border-l-3 border-[var(--ap-gold)] bg-[#FAF3E8] transition-colors"
                      : "block w-full text-left px-5 py-3 border-l-3 border-transparent hover:bg-[#FDF8F0] transition-colors"}
                  >
                    <span className="block text-sm leading-snug text-[#2C1810]">
                      <Marked text={entry.title} nq={normalizedQuery} />
                    </span>
                    {entry.anchor && (
                      <span className="block text-xs text-[var(--ap-gold)] mt-0.5">
                        {entry.sectionTitle}
                      </span>
                    )}
                    {(snippet.before || snippet.match || snippet.after) && (
                      <span className="block text-xs leading-relaxed text-[#5C3D2E] mt-1">
                        <Marked text={snippet.before + snippet.match + snippet.after} nq={normalizedQuery} />
                      </span>
                    )}
                    {loadingNote(`${entry.section}#${entry.anchor ?? ""}`)}
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
                        `${part.numeral}. ${part.title}`,
                        isOpen,
                        listId,
                        // V37: the part's own page is lit on its heading (the one highlight).
                        isPartSelected || (!isOpen && currentPartId === part.id),
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
                                  leaveTo(e, sectionHref(part.id));
                                }}
                                data-toc-lit={lit(`part:${part.id}`, false) ? "" : undefined}
                                data-toc-row={`part:${part.id}`}
                                {...loadingProps(`part:${part.id}`)}
                                className={`sidebar-link w-full text-left px-5 py-3 block border-l-3 transition-colors ${
                                  lit(`part:${part.id}`, false)
                                    ? "bg-[#FAF3E8] border-[var(--ap-gold)]"
                                    : "hover:bg-[#FDF8F0] border-transparent"
                                }`}
                              >
                                <span
                                  className={`text-sm leading-snug italic ${
                                    lit(`part:${part.id}`, false) ? "text-[var(--ap-gold)]" : "text-[#5C3D2E]"
                                  }`}
                                >
                                  {t(ui, "part.empty")}
                                </span>
                                {loadingNote(`part:${part.id}`)}
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
      </div>
      </nav>
    </aside>
  );
}
