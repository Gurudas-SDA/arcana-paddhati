"use client";

// V110 (Vraja Lila msg 8612–8614): a quiet strip at the bottom, above the
// reader's bottom bar, about a new version of the book (lib/swUpdate.ts).
import { t, type UiDict } from "@/lib/i18n";
import { applyUpdate, retryUpdate, useSwUpdate } from "@/lib/swUpdate";

export default function UpdateBanner({ ui }: { ui: UiDict }) {
  const u = useSwUpdate();
  if (u.phase === "idle") return null;
  const text =
    u.phase === "loading"
      ? t(ui, "update.loading").replace("{n}", String(u.pct))
      : u.phase === "ready"
        ? t(ui, "update.ready")
        : u.phase === "failed"
          ? t(ui, "update.failed")
          : t(ui, "update.done");
  const action = u.phase === "ready" ? { label: t(ui, "update.apply"), run: applyUpdate } : u.phase === "failed" ? { label: t(ui, "update.retry"), run: retryUpdate } : null;
  return (
    <div className="update-banner no-print" data-update-banner="" data-update-phase={u.phase} data-no-reader-tap="" role="status" aria-live="polite">
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
}
