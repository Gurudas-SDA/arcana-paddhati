"use client";

// V110 (Vraja Lila msg 8612–8614): a quiet strip at the bottom, above the
// reader's bottom bar, about a new version of the book (lib/swUpdate.ts).
// V112 (Vraja Lila msg 8621): on the cover the strip stands IN the page under the
// cards (HomePage.tsx, `inline`), a --space-8 below them, the cards' width; the
// fixed strip is hidden there (app/globals.css /*@v112*/). The inline strip tells
// the cover its height (html[data-update-strip] + --update-banner-h), so the cover
// is sized for it and the block rises a little when the bars come out (CSS).
import { useEffect, useRef } from "react";
import { t, type UiDict } from "@/lib/i18n";
import { applyUpdate, retryUpdate, useSwUpdate } from "@/lib/swUpdate";

export default function UpdateBanner({ ui, inline = false }: { ui: UiDict; inline?: boolean }) {
  const u = useSwUpdate();
  const ref = useRef<HTMLDivElement>(null);
  const on = u.phase !== "idle";
  useEffect(() => {
    const el = ref.current;
    if (!inline || !on || !el) return;
    const root = document.documentElement;
    const size = () => root.style.setProperty("--update-banner-h", `${el.offsetHeight}px`);
    size();
    root.setAttribute("data-update-strip", "");
    const ro = new ResizeObserver(size);
    ro.observe(el);
    return () => {
      ro.disconnect();
      root.removeAttribute("data-update-strip");
      root.style.removeProperty("--update-banner-h");
    };
  }, [inline, on]);
  if (!on) return null;
  const text =
    u.phase === "loading"
      ? t(ui, "update.loading").replace("{n}", String(u.pct))
      : u.phase === "ready"
        ? t(ui, "update.ready")
        : u.phase === "failed"
          ? t(ui, "update.failed")
          : t(ui, "update.done");
  const action = u.phase === "ready" ? { label: t(ui, "update.apply"), run: applyUpdate } : u.phase === "failed" ? { label: t(ui, "update.retry"), run: retryUpdate } : null;
  const strip = (
    <div ref={ref} className={inline ? "update-banner update-banner-inline no-print" : "update-banner no-print"} data-update-banner="" data-update-phase={u.phase} data-no-reader-tap="" role="status" aria-live="polite">
      <span className="update-banner-text">{text}</span>
      {u.phase === "loading" && (
        <span className="update-banner-bar" aria-hidden="true">
          <i style={{ width: `${u.pct}%` }} />
        </span>
      )}
      {action && (
        <button type="button" className="update-banner-btn" data-update-action={u.phase} onClick={action.run}>
          {action.label}
        </button>
      )}
    </div>
  );
  return inline ? <div className="home-update-slot">{strip}</div> : strip;
}
