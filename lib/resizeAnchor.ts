import { main } from "./navHistory";

/** V60 (Vraja Lila 28.10.2026, msg 6949; Android): turning the phone while reading re-wraps the text, but the scroll
 *  offset stayed the same number — so the screen showed another place, in the whole-book scroll even another chapter
 *  (the offset was clamped to the shorter book and the address followed it to the last chapters).
 *  The text block at the reading line (and how far inside it) is remembered while scrolling; when the reading area
 *  changes size it is put back at the same line, for a while (pictures and fonts may still move the text) or until
 *  the reader touches the page. While this runs the book does not rename the chapter (resizeSettling). */
const LINE = 0.2;
const SETTLE_MS = 1200;
const ARTICLE = "article";
const CONTAINER = "article, section, [data-book-section], .continuous-book, .app-main";

let settleUntil = 0;

/** True while a kept place is being put back after a resize. */
export function resizeSettling(): boolean {
  return performance.now() < settleUntil;
}

interface Anchor {
  block: HTMLElement;
  ratio: number;
  w: number;
  h: number;
}

export function keepPlaceOnResize(): () => void {
  let anchor: Anchor | null = null;
  let frame = 0;
  const timers: number[] = [];
  const lineOf = (m: HTMLElement) => m.getBoundingClientRect().top + m.clientHeight * LINE;

  const capture = () => {
    frame = 0;
    const m = main();
    if (!m || resizeSettling()) return;
    const r = m.getBoundingClientRect();
    const line = lineOf(m);
    // Bars and panels may lie over the text: the deepest element under the line inside the chapter's text.
    let block: HTMLElement | null = null;
    for (const el of document.elementsFromPoint(r.left + r.width / 2, line)) {
      if (!(el instanceof HTMLElement) || !m.contains(el) || !el.closest(ARTICLE)) continue;
      if (el.matches(CONTAINER)) break;
      block = el;
      break;
    }
    if (!block) return;
    const b = block.getBoundingClientRect();
    if (!b.height) return;
    anchor = { block, ratio: Math.min(1, Math.max(0, (line - b.top) / b.height)), w: m.clientWidth, h: m.clientHeight };
  };
  const schedule = () => { if (!frame) frame = requestAnimationFrame(capture); };

  const stop = () => { settleUntil = 0; timers.forEach((t) => window.clearTimeout(t)); timers.length = 0; };
  const events = ["touchstart", "wheel", "keydown", "pointerdown"] as const;

  const apply = () => {
    const m = main();
    if (!m || !anchor || !anchor.block.isConnected) return;
    const b = anchor.block.getBoundingClientRect();
    if (!b.height) return;
    const d = b.top + anchor.ratio * b.height - lineOf(m);
    if (Math.abs(d) > 1) m.scrollTop += d;
  };

  const onResize = () => {
    const m = main();
    if (!m || !anchor) return;
    if (m.clientWidth === anchor.w && Math.abs(m.clientHeight - anchor.h) < 1) return;
    settleUntil = performance.now() + SETTLE_MS + 100;
    timers.forEach((t) => window.clearTimeout(t));
    timers.length = 0;
    apply();
    requestAnimationFrame(apply);
    for (const ms of [60, 160, 320, 600, 1000]) timers.push(window.setTimeout(apply, ms));
    timers.push(window.setTimeout(() => { settleUntil = 0; schedule(); }, SETTLE_MS));
  };

  const scroller = main();
  scroller?.addEventListener("scroll", schedule, { passive: true });
  window.addEventListener("resize", onResize);
  window.visualViewport?.addEventListener("resize", onResize);
  for (const ev of events) window.addEventListener(ev, stop, { passive: true, capture: true });
  const observer = typeof ResizeObserver !== "undefined" ? new ResizeObserver(onResize) : null;
  if (scroller) observer?.observe(scroller);
  const first = window.setTimeout(schedule, 300);
  return () => {
    scroller?.removeEventListener("scroll", schedule);
    window.removeEventListener("resize", onResize);
    window.visualViewport?.removeEventListener("resize", onResize);
    for (const ev of events) window.removeEventListener(ev, stop, { capture: true });
    observer?.disconnect();
    cancelAnimationFrame(frame);
    window.clearTimeout(first);
    stop();
  };
}
