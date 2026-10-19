"use client";

// «Видимая загрузка книги на телефон» (Vraja Lila msg 5317/5318): the state of
// saving the book for offline reading, under the cover only — never inside a
// chapter. Count in parts («84 из 214») and a segmented bar, no percentages
// (the worker counts files, not bytes), no time estimate, no «download now».
// Its place is reserved before first paint (lib/homeCards.ts), so the cover
// does not jump when it appears.
import { useEffect, useState } from "react";
import {
  type FailedKinds,
  useOfflineProgress,
  useOfflineSave,
  useSwRegistered,
  writeOfflineSave,
} from "@/lib/offlineProgress";

export interface OfflineSaveLabels {
  loading: string;
  loadingNote: string;
  paused: string;
  pausedNote: string;
  done: string;
  doneNote: string;
  hide: string;
  count: string;
  partial: string;
  partialWhat: string;
  textOk: string;
  textMissing: string;
  retry: string;
  kinds: Record<keyof FailedKinds, string>;
}

const SEGMENTS = 20;

type View = "loading" | "paused" | "partial" | "done";

function fill(s: string, vars: Record<string, string | number>) {
  return s.replace(/\{(\w+)\}/g, (m, k: string) => (k in vars ? String(vars[k]) : m));
}

function Track({ done, total, idle }: { done: number; total: number; idle: boolean }) {
  const f = total > 0 ? Math.min(1, done / total) * SEGMENTS : 0;
  const full = Math.floor(f);
  const part = f - full;
  return (
    <div className={`home-save-track${idle ? " is-idle" : ""}`} aria-hidden="true">
      {Array.from({ length: SEGMENTS }, (_, i) => (
        <i
          key={i}
          className={i < full ? "on" : i === full && part > 0 ? "part" : undefined}
          style={i === full && part > 0 ? ({ "--part": `${Math.round(part * 100)}%` } as React.CSSProperties) : undefined}
        />
      ))}
    </div>
  );
}

export default function OfflineSaveCard({ labels }: { labels: OfflineSaveLabels }) {
  useOfflineProgress();
  const save = useOfflineSave();
  const registered = useSwRegistered();
  const [mounted, setMounted] = useState(false);
  const [reserved, setReserved] = useState(false);
  const [online, setOnline] = useState(true);
  // «Готово» stays for this visit once shown (it is stored as «seen» at once).
  const [doneShown, setDoneShown] = useState(false);
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    setMounted(true);
    setReserved(document.documentElement.hasAttribute("data-home-save"));
    setOnline(navigator.onLine !== false);
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  let view: View | null = null;
  if (mounted && !hidden) {
    if (doneShown || save?.s === "done") view = "done";
    else if (save?.s === "loading") view = online ? "loading" : "paused";
    else if (save?.s === "partial") view = online ? "loading" : "paused";
    else if (!save && reserved && registered !== "no") view = online ? "loading" : "paused";
  }

  useEffect(() => {
    if (save?.s === "done" && !hidden) {
      setDoneShown(true);
      writeOfflineSave({ ...save, s: "seen" });
    }
  }, [save, hidden]);

  useEffect(() => {
    if (!mounted) return;
    const root = document.documentElement;
    if (view) root.setAttribute("data-home-save", "");
    else root.removeAttribute("data-home-save");
  }, [mounted, view]);

  const d = save?.d ?? 0;
  const t = save?.t ?? 0;
  const count = t > 0 ? fill(labels.count, { done: d, total: t }) : "";

  let body = null;
  if (view === "done") {
    body = (
      <>
        <div className="home-save-done">
          <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
            <path d="M20 6L9 17l-5-5" />
          </svg>
          <p className="home-save-title">{labels.done}</p>
          <button
            type="button"
            className="home-save-hide"
            onClick={(e) => {
              e.stopPropagation();
              setHidden(true);
              setDoneShown(false);
            }}
          >
            {labels.hide}
          </button>
        </div>
        <p className="home-save-note">{labels.doneNote}</p>
      </>
    );
  } else if (view) {
    const title = view === "loading" ? labels.loading : view === "paused" ? labels.paused : labels.partial;
    let note = view === "loading" ? labels.loadingNote : labels.pausedNote;
    body = (
      <>
        <div className="home-save-top">
          <span className="home-save-title">{title}</span>
          {count && <span className="home-save-count">{count}</span>}
        </div>
        <Track done={d} total={t} idle={view === "paused"} />
        <p className="home-save-note">{note}</p>
      </>
    );
  }

  return (
    <div className="home-save-slot" data-home-save-view={view ?? undefined}>
      {body && (
        <div className="home-save" role="status" aria-live="polite">
          {body}
        </div>
      )}
    </div>
  );
}
