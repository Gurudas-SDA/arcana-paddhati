// Start screen (Vraja Lila 20.10.2026, ДА msg 5520): the Chaitanya Academy sign
// on white while the first page gets ready. CA_LOADER_CSS / CA_LOADER_SVG are
// Vraja Lila's code VERBATIM (msg 762, «Заставка CA-loader v2», file
// Vraja_Lila/faili/2026.10.20_Заставка CA-loader v2 — код Враджа Лилы (msg 762).html):
// frame 0 = the sign at its own size = the iOS startup picture (public/splash/,
// scripts/splash_images.py). Do not edit them — a new version comes from Vraja Lila.
// The layer around it (SPLASH_CSS, SPLASH_SCRIPT) is ours: app/layout.tsx puts it
// first in <body>; components/AppShell.tsx calls window.__apSplashDone() once the
// page is hydrated and drawn (no artificial delay).

export const CA_LOADER_CSS = `
.ca-loader{
  --ca-size: 200px;
  --ca-color: #e10e15;

  /* rigid rotation of the whole symbol */
  --ca-spin-dur: 19s;
  --ca-spin-dir: normal;
  --ca-spin-ease: linear;

  /* trail running along the arms. The cycle rests on the symbol at
     its original size and dips from there, so frame 0 is the logo.
     1.13 is the largest scale at which no two dots touch. */
  --ca-scale-rest: 1;
  --ca-scale-dip: 0.8;
  --ca-trail-dur: 1.15s;
  --ca-trail-ease: ease-in-out;
  --ca-step-radial: 55ms;
  --ca-step-arm: 45ms;

  width: var(--ca-size);
  height: var(--ca-size);
  display: block;
  overflow: visible;
}

.ca-orbit{
  transform-box: view-box;
  transform-origin: 50% 50%;
  animation-name: ca-spin;
  animation-duration: var(--ca-spin-dur);
  animation-direction: var(--ca-spin-dir);
  animation-timing-function: var(--ca-spin-ease);
  animation-iteration-count: infinite;
}

.ca-dot{
  fill: var(--ca-color);
  transform-box: fill-box;
  transform-origin: center;
  animation-name: ca-trail;
  animation-duration: var(--ca-trail-dur);
  animation-timing-function: var(--ca-trail-ease);
  animation-iteration-count: infinite;
  animation-delay: calc(
    var(--i) * var(--ca-step-radial) +
    var(--a) * var(--ca-step-arm)
  );
}

@keyframes ca-spin{
  to { transform: rotate(360deg); }
}

@keyframes ca-trail{
  0%, 100% { transform: scale(var(--ca-scale-rest)); }
  50%      { transform: scale(var(--ca-scale-dip)); }
}

@media (prefers-reduced-motion: reduce){
  .ca-orbit, .ca-dot{ animation-name: none; }
}
`;

export const CA_LOADER_SVG = `<svg class="ca-loader" viewBox="0 0 83.22854 83.22854" role="img" aria-label="Loading">
  <g class="ca-orbit">
    <circle class="ca-dot" style="--i:0;--a:0" cx="29.71738" cy="29.6713" r="7.14143"/>
    <circle class="ca-dot" style="--i:0;--a:1" cx="53.51116" cy="29.6713" r="7.14143"/>
    <circle class="ca-dot" style="--i:0;--a:2" cx="53.51116" cy="53.39563" r="7.14143"/>
    <circle class="ca-dot" style="--i:0;--a:3" cx="29.71738" cy="53.39563" r="7.14143"/>
    <circle class="ca-dot" style="--i:1;--a:0" cx="41.61427" cy="17.85358" r="5.86303"/>
    <circle class="ca-dot" style="--i:1;--a:1" cx="65.37496" cy="41.61427" r="5.86303"/>
    <circle class="ca-dot" style="--i:1;--a:2" cx="41.61427" cy="65.37496" r="5.86303"/>
    <circle class="ca-dot" style="--i:1;--a:3" cx="17.85358" cy="41.61427" r="5.86303"/>
    <circle class="ca-dot" style="--i:2;--a:0" cx="67.66727" cy="27.41957" r="5.28995"/>
    <circle class="ca-dot" style="--i:3;--a:0" cx="61.4075" cy="14.81186" r="4.84912"/>
    <circle class="ca-dot" style="--i:4;--a:0" cx="52.59092" cy="6.87693" r="3.0858"/>
    <circle class="ca-dot" style="--i:5;--a:0" cx="42.71634" cy="2.38048" r="2.38048"/>
    <circle class="ca-dot" style="--i:2;--a:1" cx="55.80897" cy="67.66727" r="5.28995"/>
    <circle class="ca-dot" style="--i:3;--a:1" cx="68.41668" cy="61.4075" r="4.84912"/>
    <circle class="ca-dot" style="--i:4;--a:1" cx="76.35161" cy="52.59092" r="3.0858"/>
    <circle class="ca-dot" style="--i:5;--a:1" cx="80.84807" cy="42.71634" r="2.38048"/>
    <circle class="ca-dot" style="--i:2;--a:2" cx="15.56127" cy="55.80897" r="5.28995"/>
    <circle class="ca-dot" style="--i:3;--a:2" cx="21.82104" cy="68.41668" r="4.84912"/>
    <circle class="ca-dot" style="--i:4;--a:2" cx="30.63763" cy="76.35161" r="3.0858"/>
    <circle class="ca-dot" style="--i:5;--a:2" cx="40.5122" cy="80.84807" r="2.38048"/>
    <circle class="ca-dot" style="--i:2;--a:3" cx="27.41957" cy="15.56127" r="5.28995"/>
    <circle class="ca-dot" style="--i:3;--a:3" cx="14.81186" cy="21.82104" r="4.84912"/>
    <circle class="ca-dot" style="--i:4;--a:3" cx="6.87693" cy="30.63763" r="3.0858"/>
    <circle class="ca-dot" style="--i:5;--a:3" cx="2.38048" cy="40.5122" r="2.38048"/>
  </g>
</svg>`;

/** Ours: the white layer, the leaving animation, the safety net.
 *  - leaving (.ap-splash-out): the sign 450 ms ease-out opacity 1→0 + scale 1→1.6,
 *    the white layer fades with it; then the layer is hidden and emptied;
 *  - reduced motion: the sign stays still (Vraja Lila's own rule above) and only fades;
 *  - never in the way: no pointer events (a tap reaches the page), not printed;
 *  - safety: if the script never runs (or the page never signals), CSS alone fades
 *    the layer out after 4 s, so it can never hold the page hidden. Its keyframes
 *    have a name of their own: with the same name the leaving would only change
 *    the delay of the running animation — it would end at once, unseen. */
export const SPLASH_CSS = `#ap-splash{position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;background:#fff;pointer-events:none;animation:ap-splash-safety 450ms ease-out 4s forwards}
#ap-splash[hidden]{display:none}
#ap-splash.ap-splash-out{animation:ap-splash-bg 450ms ease-out forwards}
#ap-splash .ap-splash-sign{display:block;will-change:transform,opacity}
/* V53 (Vraja Lila msg 6433): on a phone the sign is 15 % smaller (200 px x 0.85 = 170 px); same proportions
   and centre; tablet and computer (from 640 px, the app's phone breakpoint) keep Vraja Lila's own 200 px. */
@media (max-width: 639px){#ap-splash .ca-loader{--ca-size:170px}}
#ap-splash.ap-splash-out .ap-splash-sign{animation:ap-splash-sign 450ms ease-out forwards}
@keyframes ap-splash-bg{to{opacity:0;visibility:hidden}}
@keyframes ap-splash-safety{to{opacity:0;visibility:hidden}}
@keyframes ap-splash-sign{from{opacity:1;transform:scale(1)}to{opacity:0;transform:scale(1.6)}}
@media (prefers-reduced-motion: reduce){#ap-splash.ap-splash-out .ap-splash-sign{animation:none}}
@media print{#ap-splash{display:none}}`;

/** Right after the layer in <body>: window.__apSplashDone() starts the leaving
 *  animation (AppShell, after hydration + first frame); 4 s at the latest. */
export const SPLASH_SCRIPT = `(function(){var s=document.getElementById("ap-splash");if(!s)return;var go=false,gone=false;function fin(){if(gone)return;gone=true;s.hidden=true;s.innerHTML="";s.className=""}function end(){if(go)return;go=true;s.className="ap-splash-out";s.addEventListener("animationend",function(e){if(e.target===s)fin()});setTimeout(fin,700)}window.__apSplashDone=end;setTimeout(end,4000)})();`;
