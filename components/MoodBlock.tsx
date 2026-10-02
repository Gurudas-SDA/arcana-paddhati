"use client";

import React, { useId, useState } from "react";
import type { MoodSource } from "@/lib/book";

/** Localised labels of the mood block (data/ui.<lang>.json, keys mood.*). */
export interface MoodLabels {
  button: string;
  words: string;
  translation: string;
  machine: string;
  transcript: string;
  audio: string;
}

/** Paragraphs of a quote ("\n\n"-separated; "[…]" marks an omission). */
function Paragraphs({ text, className }: { text: string; className: string }) {
  return (
    <>
      {text.split("\n\n").map((para, i) => (
        <p key={i} className={`${className} ${para.trim() === "[…]" ? "text-[#8B6508] not-italic" : ""}`}>
          {para}
        </p>
      ))}
    </>
  );
}

/**
 * "Mood — Gurudev": a verbatim quote of Gurudev (English, his own words) on the
 * inner mood of the action described below it, with a translation and source.
 * Collapsed by default (independent of the sidebar switches). The panel is
 * always in the HTML (hidden by CSS until opened: .mood-panel in globals.css,
 * not the `hidden` attribute, whose !important preflight rule would win over
 * the print rule), so print shows it expanded.
 */
export default function MoodBlock({
  quote,
  translation,
  machine,
  source,
  labels,
}: {
  quote: string;
  translation?: string;
  /** The translation is a machine translation (not the Academy's). */
  machine?: boolean;
  source?: MoodSource;
  labels: MoodLabels;
}) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const sourceLine = source
    ? [source.title, source.date, source.nr ? `№ ${source.nr}` : "", source.timecode]
        .filter(Boolean)
        .join(" · ")
    : "";

  return (
    <div className="mood my-4">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((o) => !o)}
        className={`mood-toggle inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[12px] leading-4 select-none transition-colors ${
          open
            ? "border-[#B8860B] bg-[#F5E6C8] text-[#8B6508] font-semibold"
            : "border-[#D4A843] bg-[#FDF8F0] text-[#8B6508] hover:border-[#B8860B] hover:bg-[#F5E6C8]"
        }`}
      >
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
        {labels.button}
      </button>
      <div
        id={panelId}
        data-open={open ? "" : undefined}
        className="mood-panel mt-2 rounded-sm border-l-2 border-[#B8860B] bg-[#FDF8F0] px-4 py-3 sm:px-5"
      >
        <p className="mood-label mb-1 text-[11px] font-semibold uppercase tracking-wider text-[#8B6508]">
          {labels.words}
        </p>
        <div lang="en" className="mood-quote space-y-3">
          <Paragraphs text={quote} className="text-[15px] leading-7 text-[#2C1810]" />
        </div>
        {translation && (
          <div className="mt-4 border-t border-[#E8DCC8] pt-3">
            <p className="mood-label mb-1 text-[11px] font-semibold uppercase tracking-wider text-[#8B6508]">
              {labels.translation}
              {machine && (
                <span className="ml-2 font-normal normal-case tracking-normal text-[#5C3D2E]/80">
                  ({labels.machine})
                </span>
              )}
            </p>
            <div className="mood-translation translation space-y-3">
              <Paragraphs text={translation} className="text-[15px] leading-7" />
            </div>
          </div>
        )}
        {source && (
          <p className="mood-source mt-4 border-t border-[#E8DCC8] pt-2 text-[12px] leading-5 text-[#5C3D2E]">
            <span lang="en">{sourceLine}</span>
            {source.transcript_url && (
              <>
                {" · "}
                <a
                  href={source.transcript_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#8B6508] underline decoration-[#D4A843] underline-offset-2 hover:text-[#B8860B]"
                >
                  {labels.transcript}
                </a>
              </>
            )}
            {source.audio_url && (
              <>
                {" · "}
                <a
                  href={source.audio_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#8B6508] underline decoration-[#D4A843] underline-offset-2 hover:text-[#B8860B]"
                >
                  {labels.audio}
                </a>
              </>
            )}
          </p>
        )}
      </div>
    </div>
  );
}
