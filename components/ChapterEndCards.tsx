"use client";

import { useEffect, useRef, useState } from "react";
import type { TocSection } from "@/lib/book";
import { t, type UiDict } from "@/lib/i18n";
import { main as mainEl } from "@/lib/navHistory";

type Geo = { left: number; width: number; padL: string; padR: string };

/** Gap between the cards and the bottom bar's top edge, and between the text's end and the cards (px). */
const ABOVE_BAR = 8;
const BELOW_TEXT = 12;
/** The bottom bar's height (.reader-bar-bottom: border 1 + padding 6 + 6 + a 44 px button), without the safe area. */
const BAR_H = 57;

/**
 * V81 (Vraja Lila msg 7729, mockup 6): at the end of a chapter the cards «‹ Пред. глава» / «След. глава ›» (variant A:
 * the label 16 px, the title 13 px, weight 400). They are fixed above the bottom bar, stand at the text column's edges and
 * appear only when the reader has scrolled to the end of the chapter (scrolling back removes them). The room under the
 * text so that no line stays under them is a spacer after the article (components/SectionContent.tsx,
 * .chapter-end-cards-space); its height — the cards' height + 29 px — is in --chapter-end-cards-space, set here.
 * One card (the first page: only «След. глава», the last: only «Пред. глава») keeps the width it has in a pair and stays at
 * its own edge. «Страницы» only: in «Лента» the bottom bar steps through the chapters. The bottom bar itself is not touched.
 */
export default function ChapterEndCards({
  ui,
  sections,
  sectionId,
  prevPage,
  nextPage,
  goChapter,
  suspended,
}: {
  ui: UiDict;
  sections: TocSection[];
  sectionId: string | null;
  /** string = a page; null = the cover (no card for it); undefined = none. */
  prevPage: string | null | undefined;
  nextPage: string | null | undefined;
  goChapter: (id: string | null) => void;
  /** The contents / «Аа» panel is open. */
  suspended: boolean;
}) {
  const [geo, setGeo] = useState<Geo | null>(null);
  const [atEnd, setAtEnd] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  const prevId = typeof prevPage === "string" ? prevPage : null;
  const nextId = nextPage ?? null;
  const hasGeo = geo !== null;
  const live = sectionId !== null && (prevId !== null || nextId !== null);

  useEffect(() => {
    const root = document.documentElement;
    const main = mainEl();
    if (!live || !main) return;
    let raf = 0;
    const measure = () => {
      raf = 0;
      const art = main.querySelector<HTMLElement>("article.reader-article");
      if (!art || main.querySelector("[data-continuous-book]")) {
        setGeo(null);
        setAtEnd(false);
        root.style.removeProperty("--chapter-end-cards-space");
        return;
      }
      const r = art.getBoundingClientRect();
      const cs = getComputedStyle(art);
      const next: Geo = { left: Math.round(r.left * 100) / 100, width: Math.round(r.width * 100) / 100, padL: cs.paddingLeft, padR: cs.paddingRight };
      setGeo((g) => (g && g.left === next.left && g.width === next.width && g.padL === next.padL && g.padR === next.padR ? g : next));
      const h = boxRef.current ? boxRef.current.offsetHeight : 0;
      if (h) root.style.setProperty("--chapter-end-cards-space", `${h + ABOVE_BAR + BELOW_TEXT + BAR_H - 48}px`);
      setAtEnd(main.scrollTop >= main.scrollHeight - main.clientHeight - 4);
    };
    const schedule = () => {
      if (!raf) raf = requestAnimationFrame(measure);
    };
    measure();
    main.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(schedule) : null;
    ro?.observe(main);
    if (boxRef.current) ro?.observe(boxRef.current);
    // The page's article is replaced when the chapter changes (the reading area stays mounted).
    const mo = new MutationObserver(schedule);
    mo.observe(main, { childList: true, subtree: true });
    return () => {
      main.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      ro?.disconnect();
      mo.disconnect();
      if (raf) cancelAnimationFrame(raf);
      root.style.removeProperty("--chapter-end-cards-space");
    };
  }, [live, sectionId, hasGeo]);

  if (!live || !geo) return null;
  const title = (id: string) => sections.find((s) => s.id === id)?.title ?? "";
  const show = atEnd && !suspended;
  return (
    <div
      ref={boxRef}
      className="chapter-end-cards no-print"
      data-show={show ? "" : undefined}
      aria-hidden={show ? undefined : true}
      style={{ left: geo.left, width: geo.width, paddingLeft: geo.padL, paddingRight: geo.padR }}
    >
      <div className="chapter-end-cards-row">
        {prevId !== null && (
          <button type="button" className="chapter-end-card" data-dir="prev" data-reader-nav="back" data-chapter-target={prevId} onClick={() => goChapter(prevId)}>
            <span className="chapter-end-card-label">{`‹ ${t(ui, "reader.prevChapter")}`}</span>
            <span className="chapter-end-card-title">{title(prevId)}</span>
          </button>
        )}
        {nextId !== null && (
          <button type="button" className="chapter-end-card" data-dir="next" data-reader-nav="forward" data-chapter-target={nextId} onClick={() => goChapter(nextId)}>
            <span className="chapter-end-card-label">{`${t(ui, "reader.nextChapter")} ›`}</span>
            <span className="chapter-end-card-title">{title(nextId)}</span>
          </button>
        )}
      </div>
    </div>
  );
}
