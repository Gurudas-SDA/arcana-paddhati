"use client";

import React, { useId, useState } from "react";
import { useShowAllTranslations } from "@/lib/translationsPref";

/**
 * A verse whose translation is collapsed by default: the Sanskrit text is the
 * toggle. The translation is always in the HTML (only `hidden`), so print,
 * search engines and the full-text index still see it. The sidebar's
 * "Show all translations" switch sets the default; a tap on a verse overrides
 * it for that verse until the switch changes again.
 */
export default function CollapsibleVerse({
  sanskrit,
  translation,
  hint,
}: {
  /** The rendered Sanskrit block. */
  sanskrit: React.ReactNode;
  translation: string;
  /** Localised label of the "has a translation" indicator. */
  hint: string;
}) {
  const showAll = useShowAllTranslations();
  // Per-verse choice, valid only for the global setting it was made under.
  const [override, setOverride] = useState<{ open: boolean; under: boolean } | null>(null);
  const open = override && override.under === showAll ? override.open : showAll;
  const id = useId();

  const toggle = () => setOverride({ open: !open, under: showAll });

  const onClick = () => {
    // Selecting text inside the verse must not toggle it.
    const sel = window.getSelection();
    if (sel && !sel.isCollapsed && sel.toString().trim() !== "") return;
    toggle();
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      toggle();
    }
  };

  return (
    <div className="my-5">
      <div
        role="button"
        tabIndex={0}
        aria-expanded={open}
        aria-controls={id}
        onClick={onClick}
        onKeyDown={onKeyDown}
        className="verse-toggle group cursor-pointer rounded-sm"
      >
        {sanskrit}
        <span className="verse-indicator mb-1 inline-flex items-center gap-1 select-none text-[11px] leading-none text-[#B8860B]/60 group-hover:text-[#B8860B]">
          <svg
            aria-hidden="true"
            width="10"
            height="10"
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
          {hint}
        </span>
      </div>
      <p
        id={id}
        hidden={!open}
        className="verse-translation translation text-[15px] leading-relaxed mt-1 pl-4 border-l border-[#999] ml-1"
      >
        {translation}
      </p>
    </div>
  );
}
