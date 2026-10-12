"use client";

import { useEffect, useLayoutEffect, useRef, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { stripBasePath } from "@/lib/basePath";
import { parsePath } from "@/lib/i18n";
import { isMenuEntry, main, patchState, recordScroll, savedScroll } from "@/lib/navHistory";
import { bookOffset, bookTarget, finishReadingArrival, followBookLink, readingHref, readingState } from "@/lib/readingFlow";

/** The whole book is exported once per language, on its cover route. Chapter
 *  links move inside it; a deep link reuses this export at its original URL. */
export default function ContinuousBook({ lang, children }: { lang: string; children: ReactNode }) {
  const pathname = usePathname();
  const root = useRef<HTMLDivElement>(null);
  const quietUntil = useRef(0);

  useLayoutEffect(() => {
    const pending = finishReadingArrival();
    if (!pending) {
      const scroll = window.history.state?.apBook ? savedScroll(window.history.state) : undefined;
      patchState({ apBook: true });
      if (scroll !== undefined) {
        quietUntil.current = performance.now() + 1000;
        main()?.scrollTo({ top: scroll });
      }
      return;
    }
    const url = new URL(pending.href, window.location.href);
    const place = parsePath(stripBasePath(url.pathname) || "/");
    let anchor: string | undefined;
    try { anchor = decodeURIComponent(url.hash.slice(1)) || undefined; } catch { /* keep the chapter reachable */ }
    const target = bookTarget(place.sectionId, anchor) ?? bookTarget(place.sectionId);
    if (!target) return;
    quietUntil.current = performance.now() + 1000;
    window.history.replaceState({ ...pending.state, apBook: true }, "", url.pathname + url.search + url.hash);
    const scroller = main();
    if (scroller) {
      scroller.scrollTop = pending.scroll === undefined ? bookOffset(target)
        : pending.state.apBook ? pending.scroll
        : bookOffset(bookTarget(place.sectionId) ?? target) + pending.scroll;
    }
  }, []);

  // A shared scope for content probes and accessible reading-location tools.
  // URL tracking is independent of the full book's scroll container.
  useLayoutEffect(() => {
    const current = parsePath(stripBasePath(window.location.pathname) || '/').sectionId ?? '';
    root.current?.querySelectorAll<HTMLElement>('[data-book-section]').forEach((section) => {
      if (section.dataset.bookSection === current) section.setAttribute('data-reader-current', '');
      else section.removeAttribute('data-reader-current');
    });
  }, [pathname]);

  useEffect(() => {
    const scroller = main();
    const book = root.current;
    if (!scroller || !book) return;
    let frame = 0;
    const sections = [...book.querySelectorAll<HTMLElement>("[data-book-section]")];
    const sync = () => {
      frame = 0;
      if (isMenuEntry() || performance.now() < quietUntil.current) return;
      const line = scroller.getBoundingClientRect().top + scroller.clientHeight * 0.2;
      const current = sections.find((section) => {
        const box = section.getBoundingClientRect();
        return box.top <= line && box.bottom > line;
      });
      if (!current) return;
      const id = current.dataset.bookSection || null;
      const place = parsePath(stripBasePath(window.location.pathname) || "/");
      if (place.sectionId === id) return;
      window.history.replaceState(readingState(), "", readingHref(lang, id) + window.location.search);
      recordScroll();
    };
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(sync); };
    const onPop = () => { quietUntil.current = performance.now() + 1000; };
    scroller.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("popstate", onPop);
    window.addEventListener("hashchange", onPop);
    return () => {
      scroller.removeEventListener("scroll", onScroll);
      window.removeEventListener("popstate", onPop);
      window.removeEventListener("hashchange", onPop);
      cancelAnimationFrame(frame);
    };
  }, [lang]);

  return (
    <div
        ref={root}
        className="continuous-book"
        data-continuous-book=""
        data-book-lang={lang}
        onClickCapture={(event) => {
          if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
          const link = (event.target as Element).closest<HTMLAnchorElement>("a[href]");
          if (!link || link.target || link.hasAttribute("download")) return;
          if (followBookLink(link.href)) event.preventDefault();
        }}
    >
      {children}
    </div>
  );
}
