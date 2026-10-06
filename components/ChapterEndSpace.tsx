"use client";

import { useEffect, useRef } from "react";

/**
 * Room after the end of a chapter with subsections (Reader v7.2): just
 * enough that the LAST subsection's heading can be brought to the top of the
 * screen when it is opened from the contents (before, a short last
 * subsection stayed 184–350 px down — there was nothing left to scroll).
 * Every earlier subsection has more text after it, so it fits too.
 * «След. глава ›» stays right after the text; with a long last subsection
 * no room is added at all.
 */
export default function ChapterEndSpace() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    const main = el?.closest<HTMLElement>(".app-main");
    const article = el?.previousElementSibling;
    if (!el || !main || !article) return;
    let raf = 0;
    const fit = () => {
      raf = 0;
      const subs = article.querySelectorAll<HTMLElement>("[data-subsection]");
      const last = subs[subs.length - 1];
      if (!last) return;
      const mr = main.getBoundingClientRect();
      const margin = parseFloat(getComputedStyle(last).scrollMarginTop) || 0;
      const lastTop = last.getBoundingClientRect().top - mr.top + main.scrollTop - margin;
      const current = el.offsetHeight;
      const maxWithout = main.scrollHeight - current - main.clientHeight;
      const need = Math.max(0, Math.ceil(lastTop - maxWithout) + 2);
      if (Math.abs(need - current) > 1) el.style.height = `${need}px`;
    };
    const schedule = () => {
      if (!raf) raf = requestAnimationFrame(fit);
    };
    fit();
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(schedule) : null;
    ro?.observe(article);
    ro?.observe(main);
    window.addEventListener("resize", schedule);
    return () => {
      ro?.disconnect();
      window.removeEventListener("resize", schedule);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);
  return <div ref={ref} className="chapter-end-space no-print" aria-hidden="true" />;
}
