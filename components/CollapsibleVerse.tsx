"use client";

import React, { useId, useState } from "react";
import { parseWbw, sanskritLang } from "@/lib/book";
import { useShowAllTranslations, useShowAllWbw } from "@/lib/translationsPref";

/**
 * Open state of one verse panel: the sidebar's "show all" switch sets the
 * default; a tap overrides it for this verse until the switch changes again.
 */
function usePanel(showAll: boolean): [boolean, () => void] {
  // Per-verse choice, valid only for the global setting it was made under.
  const [override, setOverride] = useState<{ open: boolean; under: boolean } | null>(null);
  const open = override && override.under === showAll ? override.open : showAll;
  return [open, () => setOverride({ open: !open, under: showAll })];
}

function Chip({
  label,
  open,
  controls,
  onClick,
}: {
  label: string;
  open: boolean;
  controls: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-expanded={open}
      aria-controls={controls}
      onClick={onClick}
      className={`verse-chip inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] leading-4 select-none transition-colors ${
        open
          ? "border-[#B8860B] bg-[#F5E6C8] text-[#8B6508] font-semibold"
          : "border-[#E8DCC8] bg-white text-[#B8860B]/80 hover:border-[#B8860B]/60 hover:text-[#B8860B]"
      }`}
    >
      <svg
        aria-hidden="true"
        width="9"
        height="9"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={`verse-chevron ${open ? "rotate-180" : ""}`}
      >
        <polyline points="6 9 12 15 18 9" />
      </svg>
      {label}
    </button>
  );
}

/**
 * A verse with collapsible panels: word-by-word meanings and/or a translation,
 * each toggled by its own chip under the verse (tapping the Sanskrit text also
 * toggles the translation). The panels are always in the HTML (only
 * `hidden`), so print, search engines and the full-text index still see them.
 * The sidebar's "Show all …" switches set the defaults.
 */
export default function CollapsibleVerse({
  sanskrit,
  translation,
  wbw,
  translationLabel,
  wbwLabel,
}: {
  /** The rendered Sanskrit block. */
  sanskrit: React.ReactNode;
  translation?: string;
  /** "word — meaning; word — meaning; …" */
  wbw?: string;
  /** Localised chip labels. */
  translationLabel: string;
  wbwLabel: string;
}) {
  const [trOpen, toggleTr] = usePanel(useShowAllTranslations());
  const [wbwOpen, toggleWbw] = usePanel(useShowAllWbw());
  const trId = useId();
  const wbwId = useId();
  const hasTr = !!translation;
  const hasWbw = !!wbw;

  // The Sanskrit text toggles the translation (or, without one, word-by-word).
  const textToggles = hasTr ? "tr" : "wbw";
  const textOpen = hasTr ? trOpen : wbwOpen;
  const toggleFromText = hasTr ? toggleTr : toggleWbw;

  const onClick = () => {
    // Selecting text inside the verse must not toggle it.
    const sel = window.getSelection();
    if (sel && !sel.isCollapsed && sel.toString().trim() !== "") return;
    toggleFromText();
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      toggleFromText();
    }
  };

  return (
    <div className="my-5">
      <div
        role="button"
        tabIndex={0}
        aria-expanded={textOpen}
        aria-controls={textToggles === "tr" ? trId : wbwId}
        onClick={onClick}
        onKeyDown={onKeyDown}
        className="verse-toggle cursor-pointer rounded-sm"
      >
        {sanskrit}
      </div>
      <div className="verse-chips -mt-1 mb-1 flex flex-wrap gap-1.5">
        {hasWbw && <Chip label={wbwLabel} open={wbwOpen} controls={wbwId} onClick={toggleWbw} />}
        {hasTr && <Chip label={translationLabel} open={trOpen} controls={trId} onClick={toggleTr} />}
      </div>
      {hasWbw && (
        <p
          id={wbwId}
          hidden={!wbwOpen}
          className="verse-panel verse-wbw text-[14px] leading-relaxed mt-2 pl-4 border-l border-[#B8860B]/50 ml-1 text-[#2C1810]"
        >
          {parseWbw(wbw).map((pair, i) => (
            <React.Fragment key={i}>
              {i > 0 && "; "}
              <i lang={sanskritLang(pair.word)} className="wbw-word">
                {pair.word}
              </i>
              {pair.meaning && ` — ${pair.meaning}`}
            </React.Fragment>
          ))}
        </p>
      )}
      {hasTr && (
        <p
          id={trId}
          hidden={!trOpen}
          className="verse-panel verse-translation translation text-[15px] leading-relaxed mt-2 pl-4 border-l border-[#999] ml-1"
        >
          {translation}
        </p>
      )}
    </div>
  );
}
