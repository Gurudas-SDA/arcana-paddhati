// A tap that lands before React has attached the reader's tap handler must not
// be lost (rule §7: a tap anywhere on the cover shows the menu). The continuous
// book makes the first hydration long on slow devices (WebKit: 1-2 s), and the
// handler in ReaderChrome is attached in an effect, after hydration.
//
// This inline script runs before hydration, remembers the last plain tap
// (no drag, no long press, not right after a scroll), and hands it over once:
// ReaderChrome calls takeEarlyTap() when its own handler is in place and
// treats that tap like any other. Nothing is changed in the page before then.
export const EARLY_TAP_SCRIPT = `(function(){try{var s=null,last=null,scr=0,D=document;
function dn(e){if(!e.isPrimary||e.button!==0){s=null;return}var n=performance.now();s={x:e.clientX,y:e.clientY,at:n,t:e.target,ok:n-scr>=150}}
function up(e){var a=s;s=null;if(!a||!e.isPrimary)return;if(Math.hypot(e.clientX-a.x,e.clientY-a.y)>10||performance.now()-a.at>600||!a.ok)return;last={at:performance.now(),t:a.t,u:e.target}}
function sc(){scr=performance.now()}
D.addEventListener('pointerdown',dn,true);D.addEventListener('pointerup',up,true);D.addEventListener('scroll',sc,true);
window.__apTakeEarlyTap=function(){D.removeEventListener('pointerdown',dn,true);D.removeEventListener('pointerup',up,true);D.removeEventListener('scroll',sc,true);var x=last;last=null;window.__apTakeEarlyTap=function(){return null};return x}}catch(e){}})();`;

export interface EarlyTap {
  /** performance.now() of the pointerup */
  at: number;
  /** target of the pointerdown and of the pointerup */
  t: EventTarget | null;
  u: EventTarget | null;
}

/** The tap made before hydration, at most once per page load; null if none. */
export function takeEarlyTap(): EarlyTap | null {
  const w = window as unknown as { __apTakeEarlyTap?: () => EarlyTap | null };
  return w.__apTakeEarlyTap ? w.__apTakeEarlyTap() : null;
}
