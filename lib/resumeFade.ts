// «Продолжить» on the cover: the place opens with a soft, quick fade and no jerk
// (V29, Vraja Lila msg 5783, 21.10.2026: «когда книга отводит в нужный раздел
// появляется дёргание… сделай так чтобы нужная страница открылась с мягким
// быстрым fade»). The new page used to show for a moment at its top, then jump to
// the place (lib/readingMode.ts restorePlace, the subsection anchor). Now the
// reading area is hidden at once on the tap; once the new page is there and its
// scroll has settled at the place, it fades in (app/globals.css
// html[data-resume-fade]: "out" hidden, "in" fading in). Reduced motion: the
// same without the fade — the page appears at once, already at its place.
// Lives outside React: the cover (and its card) unmounts during the move.
import { main } from "./navHistory";
import { readerLayout } from "./readerPrefs";

const ATTR = "data-resume-fade";
/** Frames the scroll must stay unchanged before the page is shown. */
const STILL_FRAMES = 6;
/** The fade's own length (app/globals.css). */
const FADE_MS = 200;
/** Never keep the reader waiting longer than this for a settled page. */
const MAX_WAIT_MS = 1500;

let run = 0;

export function startResumeFade(fromPath: string) {
  const d = document.documentElement;
  const id = ++run;
  d.setAttribute(ATTR, "out");
  const t0 = performance.now();
  let last = NaN;
  let still = 0;
  const reveal = () => {
    if (id !== run) return;
    d.setAttribute(ATTR, "in");
    window.setTimeout(() => {
      if (id === run) d.removeAttribute(ATTR);
    }, FADE_MS + 40);
  };
  const tick = () => {
    if (id !== run) return;
    const waited = performance.now() - t0;
    const m = main();
    // «Лента»: the chapter page is replaced by the whole book (components/AppShell.tsx) — wait for it.
    const book = readerLayout() !== "scroll" || !!document.querySelector("[data-continuous-book]");
    const arrived = window.location.pathname !== fromPath && !!m && book && !document.getElementById("home-resume");
    if (arrived && m) {
      const top = m.scrollTop;
      still = top === last ? still + 1 : 0;
      last = top;
      if (still >= STILL_FRAMES) {
        reveal();
        return;
      }
    }
    if (waited > MAX_WAIT_MS) {
      reveal();
      return;
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}
