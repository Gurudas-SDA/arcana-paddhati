"use client";

import React from "react";
import Link from "next/link";
import { main as mainEl, recordScroll } from "@/lib/navHistory";

/**
 * The «След. глава ›» link (components/NextChapter.tsx). The book scrolls
 * inside `.app-main`, which stays mounted across pages, so Next.js' own
 * scroll would leave the next chapter a little below its top (it aligns the
 * new segment, not the page's top padding). Instead: the place in this
 * chapter is recorded for Back, and once the next chapter's URL is the
 * current one, the reading area goes to its very top.
 */
export default function NextChapterLink({
  href,
  id,
  className,
  children,
}: {
  href: string;
  id: string;
  className?: string;
  children: React.ReactNode;
}) {
  const onClick = (e: React.MouseEvent) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    recordScroll();
    const from = window.location.pathname;
    const t0 = performance.now();
    const toTop = () => {
      const m = mainEl();
      if (m) m.scrollTop = 0;
    };
    const wait = () => {
      if (window.location.pathname !== from) {
        toTop();
        requestAnimationFrame(toTop);
        for (const ms of [60, 160, 320]) window.setTimeout(toTop, ms);
      } else if (performance.now() - t0 < 4000) {
        requestAnimationFrame(wait);
      }
    };
    requestAnimationFrame(wait);
  };
  return (
    <Link href={href} scroll={false} onClick={onClick} className={className} data-chapter-next={id}>
      {children}
    </Link>
  );
}
