// Closing animation for a panel React removes at once (Vraja Lila msg 5521,
// 20.10.2026: the top menus slid / faded in smoothly but vanished in one frame).
// The panel's state stays simple (open / closed, as every test and the history
// steps expect); when React detaches the node, a visual copy of it is left in
// its place and plays the opening animation backwards — the same easing and
// duration on the way back — then removes itself. The copy is inert: no role,
// no id, no data-/aria- attributes, no pointer events, hidden from assistive
// technology, so for the page and for the tests the panel is closed at once.

const reduced = () => {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
};

/** Leave a copy of `node` (about to be removed) that plays `className`'s
 *  exit animation, then disappears (animationend, at the latest after `ms` + 80). */
export function exitGhost(node: HTMLElement | null, className: string, ms: number) {
  if (!node || !node.parentNode || !node.isConnected || reduced()) return;
  const ghost = node.cloneNode(true) as HTMLElement;
  for (const el of [ghost, ...Array.from(ghost.querySelectorAll<HTMLElement>("*"))]) {
    for (const a of Array.from(el.attributes)) {
      if (a.name === "id" || a.name === "role" || a.name === "tabindex" || a.name.startsWith("data-") || a.name.startsWith("aria-")) {
        el.removeAttribute(a.name);
      }
    }
  }
  ghost.className = className;
  ghost.setAttribute("aria-hidden", "true");
  ghost.setAttribute("inert", "");
  ghost.setAttribute("data-exit-ghost", "");
  node.parentNode.insertBefore(ghost, node.nextSibling);
  ghost.scrollTop = node.scrollTop;
  let done = false;
  const remove = () => {
    if (done) return;
    done = true;
    ghost.remove();
  };
  ghost.addEventListener("animationend", (e) => {
    if (e.target === ghost) remove();
  });
  window.setTimeout(remove, ms + 80);
}
