"use client";

import { useEffect, useRef, useState } from "react";
import { main } from "./navHistory";
import { readingSection } from "./readingFlow";

/** Contents and the footer use the same reading line and chapter scope. */
const READING_LINE = 0.205;
const CLICK_LOCK_MS = 1000;

/** Undefined means the chapter has not mounted; null means its introduction. */
export function readingSubsection(ids: string[]): string | null | undefined {
  const root = readingSection();
  if (!root) return undefined;
  const blocks = ids.map((id) => root.querySelector<HTMLElement>(`[id="${CSS.escape(id)}"]`))
    .filter((block): block is HTMLElement => block !== null);
  if (ids.length && !blocks.length) return undefined;
  const line = window.innerHeight * READING_LINE;
  let current: string | null = null;
  for (const block of blocks) {
    if (block.getBoundingClientRect().top <= line) current = block.id;
  }
  return current;
}

/** A hash seeds arrival only; geometry wins as soon as it is available.
 *  Only an explicit subsection selection briefly holds the chosen row. */
export function useReadingSubsection(pathKey: string, idsKey: string): [string | null, (id: string) => void] {
  const [place, setPlace] = useState<{ pathKey: string; id: string | null }>({ pathKey, id: null });
  const lock = useRef<{ pathKey: string; until: number }>({ pathKey, until: 0 });
  useEffect(() => {
    const ids = idsKey ? idsKey.split("|") : [];
    const scroller = main();
    let frame = 0;
    let retry: number | undefined;
    let unlock: number | undefined;
    const settle: number[] = [];
    let attempts = 0;
    const update = (id: string | null) => setPlace(previous =>
      previous.pathKey === pathKey && previous.id === id ? previous : { pathKey, id });
    try {
      const hash = decodeURIComponent(window.location.hash.slice(1));
      if (ids.includes(hash)) update(hash);
    } catch { /* Invalid hashes do not prevent a geometry measurement. */ }
    const measure = () => {
      frame = 0;
      const remaining = lock.current.pathKey === pathKey ? lock.current.until - Date.now() : 0;
      if (remaining > 0) {
        window.clearTimeout(unlock);
        unlock = window.setTimeout(measure, remaining + 1);
        return;
      }
      const id = readingSubsection(ids);
      if (id !== undefined) update(id);
      else if (attempts++ < 20) {
        window.clearTimeout(retry);
        retry = window.setTimeout(measure, 100);
      }
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(measure); };
    const onPop = () => {
      lock.current.until = 0;
      schedule();
    };
    measure();
    [80, 240, 500].forEach(ms => settle.push(window.setTimeout(measure, ms)));
    scroller?.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    window.addEventListener("hashchange", schedule);
    window.addEventListener("popstate", onPop);
    const observer = new ResizeObserver(schedule);
    if (scroller) observer.observe(scroller);
    return () => {
      scroller?.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      window.removeEventListener("hashchange", schedule);
      window.removeEventListener("popstate", onPop);
      observer.disconnect();
      cancelAnimationFrame(frame);
      window.clearTimeout(retry);
      window.clearTimeout(unlock);
      settle.forEach(timer => window.clearTimeout(timer));
    };
  }, [pathKey, idsKey]);
  const select = (id: string) => {
    lock.current = { pathKey, until: Date.now() + CLICK_LOCK_MS };
    setPlace({ pathKey, id });
  };
  return [place.pathKey === pathKey ? place.id : null, select];
}
