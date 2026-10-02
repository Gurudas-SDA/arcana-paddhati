"use client";

import React, { useId, useState } from "react";
import type { MoodQuote, MoodSource } from "@/lib/book";

/** Localised labels of the mood block (data/ui.<lang>.json, keys mood.*). */
export interface MoodLabels {
  button: string;
  words: string;
  translation: string;
  machine: string;
  transcript: string;
  audio: string;
  /** "More quotes" button: opens the first FIRST_MORE alternatives (" (N)" appended, N = all alternatives). */
  more: string;
  /** "Show all" button below them: opens the remaining alternatives (" (N)" appended). */
  showAll: string;
}

/** How many alternatives the "More quotes" button opens (the rest are behind "Show all"). */
const FIRST_MORE = 3;

/** Pill toggle button with a chevron (the "More quotes" / "Show all" buttons). */
function MoreToggle({
  open,
  controls,
  onClick,
  className,
  children,
}: {
  open: boolean;
  controls: string;
  onClick: () => void;
  className: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-expanded={open}
      aria-controls={controls}
      onClick={onClick}
      className={`${className} inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[12px] leading-4 select-none transition-colors ${
        open
          ? "border-[#B8860B] bg-[#F5E6C8] text-[#8B6508] font-semibold"
          : "border-[#D4A843] bg-white text-[#8B6508] hover:border-[#B8860B] hover:bg-[#F5E6C8]"
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
      {children}
    </button>
  );
}

/** One alternative quote, separated from the previous one by a dotted rule. */
function AltQuote({ m, labels }: { m: MoodQuote; labels: MoodLabels }) {
  return (
    <div className="mood-alt mt-4 border-t-2 border-dotted border-[#D4A843] pt-3">
      <QuoteBody
        quote={m.quote}
        translation={m.translation || undefined}
        machine={m.translation_note === "machine"}
        source={m.source}
        labels={labels}
      />
    </div>
  );
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

/** Gurudev's words (EN), the translation and the source line with links. */
function QuoteBody({
  quote,
  translation,
  machine,
  source,
  labels,
}: {
  quote: string;
  translation?: string;
  machine?: boolean;
  source?: MoodSource;
  labels: MoodLabels;
}) {
  const sourceLine = source
    ? [source.title, source.date, source.nr ? `№ ${source.nr}` : "", source.timecode]
        .filter(Boolean)
        .join(" · ")
    : "";
  return (
    <>
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
    </>
  );
}

/**
 * "Mood — Gurudev": a verbatim quote of Gurudev (English, his own words) on the
 * inner mood of the action described below it, with a translation and source.
 * Collapsed by default (independent of the sidebar switches). The panel is
 * always in the HTML (hidden by CSS until opened: .mood-panel in globals.css,
 * not the `hidden` attribute, whose !important preflight rule would win over
 * the print rule), so print shows it expanded. Inside it, "More quotes (N)"
 * opens the first FIRST_MORE other candidate quotes (`more`, best first) and,
 * when there are more, a "Show all (N)" button below them opens the rest; all
 * of them are screen-only (hidden in print — the print/Kindle book has them in
 * an appendix instead).
 */
export default function MoodBlock({
  quote,
  translation,
  machine,
  source,
  more,
  labels,
}: {
  quote: string;
  translation?: string;
  /** The translation is a machine translation (not the Academy's). */
  machine?: boolean;
  source?: MoodSource;
  /** The other candidate quotes for this block (best first), behind the "More quotes" button. */
  more?: MoodQuote[];
  labels: MoodLabels;
}) {
  const [open, setOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [restOpen, setRestOpen] = useState(false);
  const panelId = useId();
  const moreId = useId();
  const restId = useId();

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
        <QuoteBody
          quote={quote}
          translation={translation}
          machine={machine}
          source={source}
          labels={labels}
        />
        {more && more.length > 0 && (
          <div className="mood-more mt-4 border-t border-[#E8DCC8] pt-3">
            <MoreToggle
              open={moreOpen}
              controls={moreId}
              onClick={() => setMoreOpen((o) => !o)}
              className="mood-more-toggle"
            >
              {`${labels.more} (${more.length})`}
            </MoreToggle>
            <div id={moreId} data-open={moreOpen ? "" : undefined} className="mood-more-panel">
              {more.slice(0, FIRST_MORE).map((m, i) => (
                <AltQuote key={i} m={m} labels={labels} />
              ))}
              {more.length > FIRST_MORE && (
                <div className="mood-rest mt-4 border-t-2 border-dotted border-[#D4A843] pt-3">
                  <MoreToggle
                    open={restOpen}
                    controls={restId}
                    onClick={() => setRestOpen((o) => !o)}
                    className="mood-more-toggle mood-rest-toggle"
                  >
                    {`${labels.showAll} (${more.length})`}
                  </MoreToggle>
                  <div id={restId} data-open={restOpen ? "" : undefined} className="mood-more-panel">
                    {more.slice(FIRST_MORE).map((m, i) => (
                      <AltQuote key={FIRST_MORE + i} m={m} labels={labels} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
