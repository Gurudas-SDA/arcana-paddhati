import React from "react";
import { transcriptLinkProps } from "@/lib/transcripts";
import {
  parseInline,
  sanskritLang,
  stripInline,
  subsectionNumber,
  type ContentItem,
  type Section,
  type Subsection,
  type TableRow,
} from "@/lib/book";
import { t, type UiDict } from "@/lib/i18n";
import CollapsibleVerse, { MantraWbw } from "@/components/CollapsibleVerse";

/** A short mantra in a table row («⟦oṁ keśavāya namaḥ⟧», also Cyrillic). */
const MANTRA_RE = /(namaḥ|намах̣)⟧/;
import MoodBlock, { type MoodLabels } from "@/components/MoodBlock";
import { HotspotFigure, HotspotHit, HotspotProvider, HotspotRow } from "@/components/Hotspots";
import { hotspotsFor, labelNumbers } from "@/lib/hotspots";

/** Localised labels of the verse panel chips and of the mood block. */
interface VerseLabels {
  translation: string;
  wbw: string;
  mood: MoodLabels;
}

interface SectionContentProps {
  section: Section;
  /** UI strings of the page's language (verse panel chips). */
  ui: UiDict;
  /** Chapter number ("2"); every section has one (null/absent = unnumbered). */
  num?: string | null;
  /** Shown under the title, e.g. "translation in preparation — shown in English". */
  note?: string;
  /** After the last block: the «След. глава ›» link (components/NextChapter.tsx). */
  after?: React.ReactNode;
}

/** Heading scale, one weight + size per level, used everywhere:
 *  h1 section title > h2 subsection title > h3 in-text subtitle block. */
const HEADING_FONT = { fontFamily: "var(--font-noto-serif, Georgia, serif)" };
const H1_CLASS = "text-2xl sm:text-3xl font-semibold leading-tight text-[#1a1a1a]";
const H2_CLASS = "text-xl sm:text-[22px] font-semibold leading-snug text-[#1a1a1a]";
const H3_CLASS = "text-[17px] font-semibold leading-snug text-[#2C1810]";
/** Thin beige rule (same colour as the sidebar border). */
const RULE_CLASS = "border-t border-[#E8DCC8]";
/** Content lists with at least this many blocks get a rule before each
 *  in-text subtitle (h3) group except the first element. */
const LONG_CONTENT_BLOCKS = 8;

/** Running text with ⟦…⟧ runs rendered as inline Sanskrit (see .sa-inline in globals.css). */
function Inline({ text }: { text: string }) {
  return (
    <>
      {parseInline(text).map((run, i) =>
        run.sanskrit ? (
          <span key={i} lang={sanskritLang(run.text)} className="sa-inline">
            {run.text}
          </span>
        ) : (
          <React.Fragment key={i}>{run.text}</React.Fragment>
        ),
      )}
    </>
  );
}

/** A "bullet-list" block: one item per line, rendered as a compact bulleted list. */
function BulletList({ content }: { content: string }) {
  const items = content.split("\n").filter((line) => line.trim() !== "");
  return (
    <ul role="list" className="my-3 ml-5 space-y-0.5 text-[15px] leading-7 text-[#1a1a1a]">
      {items.map((line, i) => (
        <li key={i} className="flex gap-2">
          <span aria-hidden="true" className="shrink-0 select-none text-[#B8860B]">
            &ndash;
          </span>
          <span className="min-w-0">
            <Inline text={line} />
          </span>
        </li>
      ))}
    </ul>
  );
}

/** A "list" block: one item per line, rendered as a numbered list 1) 2) 3).
 *  Optional `numbers` (one label per line) overrides the running number, e.g.
 *  to match the numbers of an illustration ("4, 5", gaps); "" = no number (–).
 *  Sub-items ("2.1)" … "2.6)") never stick out to the left of the main column
 *  of numbers: they are indented to the main items' text line (rule of
 *  06.10.2026, Satkirti). Label widths are in em, so they scale with «Аа». */
function NumberedList({ content, numbers, hsImage }: { content: string; numbers?: string[]; hsImage?: string }) {
  const items = content.split("\n").filter((line) => line.trim() !== "");
  const labels = items.map((_, i) =>
    numbers ? (numbers[i] ? `${numbers[i]})` : "–") : `${i + 1})`,
  );
  // "2.1)" under "2)", or a letter "а)" / "b)" under its number.
  const isSub = (l: string) => /^(\d+\.\d+|[a-zа-яё])\)/i.test(l);
  const width = (ls: string[]) => `${Math.max(1, ...ls.map((l) => l.length)) * 0.6}em`;
  const mainLabels = labels.filter((l) => !isSub(l));
  const mainW = width(mainLabels.length > 0 ? mainLabels : labels);
  const subW = width(labels.filter(isSub));
  return (
    <ol
      role="list"
      className="numbered-list my-4 space-y-1 text-[15px] leading-7 text-[#1a1a1a]"
      style={{ "--nl-main": mainW } as React.CSSProperties}
    >
      {items.map((line, i) => {
        const sub = isSub(labels[i]);
        const row = (
          <>
            <span
              className="nl-num shrink-0 whitespace-nowrap text-right tabular-nums text-[#5C3D2E]"
              style={{ width: sub ? subW : mainW }}
            >
              <HotspotHit focus>{labels[i]}</HotspotHit>
            </span>
            <span className="min-w-0">
              <HotspotHit>
                <Inline text={line} />
              </HotspotHit>
            </span>
          </>
        );
        const nums = hsImage ? labelNumbers(numbers?.[i]) : [];
        const cls = `flex gap-2${sub ? " nl-sub" : ""}`;
        return nums.length > 0 ? (
          <HotspotRow key={i} as="li" img={hsImage!} nums={nums} className={cls}>
            {row}
          </HotspotRow>
        ) : (
          <li key={i} className={cls}>
            {row}
          </li>
        );
      })}
    </ol>
  );
}

/** A "table" block (e.g. the Cāturmāsya calendar). From 640px: a real table
 *  (horizontal scroll inside its own box if it is ever wider than the page);
 *  on phones: one card per row, each value with its column heading. Highlighted
 *  rows get a beige band (cards: also their badge). Nothing is interactive. */
function DataTable({ header, rows }: { header: string[]; rows: TableRow[] }) {
  return (
    <div className="data-table my-5">
      <div className="data-table-wide hidden sm:block overflow-x-auto">
        <table className="w-full border-collapse text-[14px] leading-snug text-[#1a1a1a]">
          <thead>
            <tr>
              {header.map((h, i) => (
                <th
                  key={i}
                  scope="col"
                  className="border-b-2 border-[#D4A843] px-2 py-2 text-left align-bottom text-[12px] font-semibold text-[#5C3D2E]"
                >
                  <Inline text={h} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, ri) => (
              <tr key={ri} className={`border-b border-[#E8DCC8] ${r.highlight ? "bg-[#FBF0D9]" : ""}`}>
                {r.cells.map((c, ci) =>
                  ci === 0 ? (
                    <th key={ci} scope="row" className="px-2 py-1.5 text-left font-semibold tabular-nums">
                      <Inline text={c} />
                    </th>
                  ) : (
                    <td key={ci} className={`px-2 py-1.5 tabular-nums ${/\d/.test(c) && c.length <= (ci < r.cells.length - 1 ? 18 : 10) ? "whitespace-nowrap" : ""} ${r.highlight && ci === r.cells.length - 1 ? "font-semibold text-[#8B6508]" : ""}`}>
                      <Inline text={c} />
                    </td>
                  ),
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul role="list" className="data-table-cards sm:hidden space-y-3">
        {rows.map((r, ri) => (
          <li
            key={ri}
            className={`rounded-sm border px-3 py-2 ${r.highlight ? "border-[#D4A843] bg-[#FBF0D9]" : "border-[#E8DCC8]"}`}
          >
            <p className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-[16px] font-semibold text-[#1a1a1a]">
              <span className="tabular-nums">
                <Inline text={r.cells[0]} />
              </span>
              {r.highlight && r.badge && (
                <span className="rounded-full border border-[#B8860B] px-2 py-0.5 text-[11px] font-semibold leading-4 text-[#8B6508]">
                  {r.badge}
                </span>
              )}
            </p>
            <dl className="mt-1 grid grid-cols-[1fr_auto] gap-x-3 gap-y-0.5 text-[14px] leading-snug">
              {r.cells.slice(1).map((c, ci) => {
                // short values (dates) sit on the label's line, right-aligned; long ones (descriptions) wrap below it
                const long = c.length > 24;
                return (
                  <React.Fragment key={ci}>
                    <dt className={`text-[#5C3D2E] ${long ? "col-span-2" : ""}`}>
                      <Inline text={header[ci + 1] ?? ""} />
                    </dt>
                    <dd
                      className={
                        long
                          ? "col-span-2 m-0 mb-1 text-left"
                          : "m-0 whitespace-nowrap text-right tabular-nums"
                      }
                    >
                      <Inline text={c} />
                    </dd>
                  </React.Fragment>
                );
              })}
            </dl>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ContentBlock({
  item,
  index,
  labels,
  title,
  separated = false,
  hsImage,
}: {
  item: ContentItem;
  index: number;
  labels: VerseLabels;
  /** Title of the (sub)section the block belongs to (header of the mood overlay). */
  title: string;
  /** Draw a rule above this block (used for h3 groups in long content). */
  separated?: boolean;
  /** Numbered list linked to this picture (file name with hotspot data). */
  hsImage?: string;
}) {
  switch (item.type) {
    case "verse": {
      const isInlineMantra = item.translation === undefined;
      const sanskrit = item.sanskrit && (
        <div lang={sanskritLang(item.sanskrit)} className={`sanskrit text-base leading-relaxed text-[#1a1a1a] ${isInlineMantra ? 'ml-8' : 'verse-text'} mb-2`}>
          {item.sanskrit.split('\n\n').map((stanza, si, sarr) => (
            <p key={si} className={si < sarr.length - 1 ? "mb-3" : ""}>
              {stanza.split('\n').map((line, li, larr) => (
                <React.Fragment key={li}>
                  {line}
                  {li < larr.length - 1 && <br />}
                </React.Fragment>
              ))}
            </p>
          ))}
        </div>
      );
      // Verse with a translation and/or word-by-word: collapsible panels.
      if (sanskrit && (item.translation || item.wbw)) {
        return (
          <CollapsibleVerse
            key={index}
            sanskrit={sanskrit}
            translation={item.translation || undefined}
            wbw={item.wbw || undefined}
            translationLabel={labels.translation}
            wbwLabel={labels.wbw}
          />
        );
      }
      return (
        <div className={`${isInlineMantra ? 'my-2' : 'my-5'}`} key={index}>
          {sanskrit}
          {item.translation !== undefined && item.translation !== "" && (
            <p className="translation text-[15px] leading-relaxed mt-1 pl-4 border-l border-[#999] ml-1">
              <Inline text={item.translation} />
            </p>
          )}
        </div>
      );
    }

    case "ornament":
      // Between the prayers of the Maṅgalācaraṇa: a quiet ornament instead of
      // headings (Satkirti, 06.10.2026 — only the Sanskrit, word-by-word and
      // translation; no titles, no numbers: book etiquette).
      return (
        <div className="verse-ornament" aria-hidden="true" key={index}>
          ❁
        </div>
      );

    case "subtitle":
      return (
        <h3
          className={`${H3_CLASS} ${separated ? `${RULE_CLASS} mt-8 pt-6` : index > 0 ? "mt-6" : "mt-2"} mb-3`}
          key={index}
          style={HEADING_FONT}
        >
          <Inline text={item.content ?? ""} />
        </h3>
      );

    case "instruction":
      return (
        <p
          className="flex gap-2.5 text-[15px] leading-7 text-[#1a1a1a] my-3"
          key={index}
        >
          <span aria-hidden="true" className="shrink-0 select-none text-[#5C3D2E]">
            &bull;
          </span>
          <span className="min-w-0">
            <Inline text={item.content ?? ""} />
          </span>
        </p>
      );

    case "list":
      return <NumberedList key={index} content={item.content ?? ""} numbers={item.numbers} hsImage={hsImage} />;

    case "bullet-list":
      return <BulletList key={index} content={item.content ?? ""} />;

    case "paired-list":
      if (item.layout === "vertical") {
        return (
          <div className="my-4 space-y-4" key={index}>
            {item.items?.map((pair, i) => (
              <div key={i}>
                {/* The label is already set as Sanskrit: drop its ⟦…⟧ markers. */}
                <p lang={sanskritLang(pair.label)} className="sanskrit text-base leading-relaxed text-[#1a1a1a]">
                  {pair.wbw && MANTRA_RE.test(pair.label) ? (
                    <MantraWbw wbw={pair.wbw} label={labels.wbw}>
                      {stripInline(pair.label)}
                    </MantraWbw>
                  ) : (
                    stripInline(pair.label)
                  )}
                </p>
                <p className="translation text-[14px] leading-relaxed ml-8">
                  <Inline text={pair.value} />
                </p>
              </div>
            ))}
          </div>
        );
      }
      return (
        <div
          className="my-4 grid gap-y-0.5"
          style={{ gridTemplateColumns: item.numbers ? "auto auto 1fr" : "auto 1fr" }}
          key={index}
        >
          {item.items?.map((pair, i) => {
            const cells = (
              <>
                {/* Optional `numbers`: one label per row, e.g. the numbers of an illustration. */}
                {item.numbers && (
                  <span className="pr-2 py-0.5 text-right tabular-nums text-[15px] text-[#5C3D2E]">
                    <HotspotHit focus>{item.numbers[i] ? `${item.numbers[i]})` : "–"}</HotspotHit>
                  </span>
                )}
                <span className="pr-8 py-0.5 text-[15px]">
                  {pair.wbw && MANTRA_RE.test(pair.label) ? (
                    <MantraWbw wbw={pair.wbw} label={labels.wbw}>
                      <Inline text={pair.label} />
                    </MantraWbw>
                  ) : (
                    <HotspotHit>
                      <Inline text={pair.label} />
                    </HotspotHit>
                  )}
                </span>
                <span className="py-0.5 text-[15px]">
                  {pair.wbw && !MANTRA_RE.test(pair.label) && MANTRA_RE.test(pair.value) ? (
                    <MantraWbw wbw={pair.wbw} label={labels.wbw}>
                      <Inline text={pair.value} />
                    </MantraWbw>
                  ) : (
                    <HotspotHit>
                      <Inline text={pair.value} />
                    </HotspotHit>
                  )}
                </span>
              </>
            );
            const nums = hsImage ? labelNumbers(item.numbers?.[i]) : [];
            // Linked row: one subgrid row (highlighted as a whole); only its text is tappable.
            return nums.length > 0 ? (
              <HotspotRow key={i} img={hsImage!} nums={nums} className="col-span-full grid grid-cols-subgrid">
                {cells}
              </HotspotRow>
            ) : (
              <React.Fragment key={i}>{cells}</React.Fragment>
            );
          })}
        </div>
      );

    case "mood":
      return (
        <MoodBlock
          key={index}
          quote={item.quote ?? ""}
          translation={item.translation || undefined}
          machine={item.translation_note === "machine"}
          source={item.source}
          more={item.more}
          title={title}
          labels={labels.mood}
        />
      );

    case "table":
      return <DataTable key={index} header={item.header ?? []} rows={item.rows ?? []} />;

    case "sources": {
      // Source line of an intro chapter ("This chapter draws on Gurudev's lecture …"): one line per lecture,
      // each followed by its transcript / audio links.
      const lines = (item.content ?? "").split("\n");
      const link = (href: string, label: string, transcript = false) => (
        <>
          {" · "}
          <a
            {...(transcript ? transcriptLinkProps(href) : { href, target: "_blank", rel: "noopener noreferrer" })}
            data-transcript-link={transcript ? "" : undefined}
            className="not-italic text-[#8B6508] underline decoration-[#D4A843] underline-offset-2 hover:text-[#B8860B]"
          >
            {label}
          </a>
        </>
      );
      return (
        <p key={index} className="source-note my-3 text-[13px] italic leading-6 text-[#5C3D2E]">
          {lines.map((line, li) => {
            const l = item.links?.[li];
            return (
              <React.Fragment key={li}>
                <Inline text={line} />
                {l?.transcript_url && link(l.transcript_url, labels.mood.transcript, true)}
                {l?.audio_url && link(l.audio_url, labels.mood.audio)}
                {li < lines.length - 1 && <br />}
              </React.Fragment>
            );
          })}
        </p>
      );
    }

    case "image": {
      const hs = hotspotsFor(item.src);
      if (hs && item.src) {
        return (
          <HotspotFigure
            key={index}
            src={`/arcana-paddhati/images/${item.src}`}
            imgName={item.src}
            alt={item.alt || ""}
            data={hs}
          />
        );
      }
      return (
        <img
          key={index}
          src={`/arcana-paddhati/images/${item.src}`}
          alt={item.alt || ""}
          className="book-image"
          style={{ maxWidth: "420px" }}
        />
      );
    }

    case "text":
    default:
      return (
        <p
          className="text-[15px] leading-7 text-[#1a1a1a] my-3"
          key={index}
        >
          {item.content && item.content.includes('\n')
            ? item.content.split('\n').map((line, li, arr) => (
                <React.Fragment key={li}>
                  <Inline text={line} />
                  {li < arr.length - 1 && <br />}
                </React.Fragment>
              ))
            : <Inline text={item.content ?? ""} />}
        </p>
      );
  }
}

function ContentBlocks({ items, labels, title }: { items: ContentItem[]; labels: VerseLabels; title: string }) {
  // A leading "mood" block (Gurudev's quote) does not count as content for
  // the layout rules below: the next block is still the "first" one.
  const lead = items.findIndex((item) => item.type !== "mood");
  const offset = lead < 0 ? items.length : lead;
  const long = items.length - offset >= LONG_CONTENT_BLOCKS;
  // Numbered pictures (with hotspot data) and the numbered lists linked to
  // them: each list with `numbers` goes with the nearest such picture in the
  // same block list.
  const pictures = items.flatMap((item, idx) =>
    item.type === "image" && hotspotsFor(item.src) ? [{ idx, src: item.src! }] : [],
  );
  const linkedImage = (item: ContentItem, idx: number): string | undefined => {
    if (!pictures.length || !item.numbers || (item.type !== "list" && item.type !== "paired-list")) return undefined;
    if (item.type === "paired-list" && item.layout === "vertical") return undefined;
    return pictures.reduce((a, b) => (Math.abs(b.idx - idx) < Math.abs(a.idx - idx) ? b : a)).src;
  };
  const blocks = items.map((item, idx) => (
    <ContentBlock
      key={idx}
      item={item}
      index={Math.max(0, idx - offset)}
      labels={labels}
      title={title}
      separated={long && idx > offset && item.type === "subtitle"}
      hsImage={linkedImage(item, idx)}
    />
  ));
  return pictures.length ? <HotspotProvider>{blocks}</HotspotProvider> : <>{blocks}</>;
}

function SubsectionBlock({
  subsection,
  num,
  separated,
  labels,
}: {
  subsection: Subsection;
  /** "2.1"-style subsection number. */
  num: string | null;
  labels: VerseLabels;
  /** Rule above the subsection (every subsection but the page's first element). */
  separated: boolean;
}) {
  return (
    <section
      id={subsection.id}
      data-subsection=""
      className={`scroll-mt-6 ${separated ? `${RULE_CLASS} mt-10 pt-8` : "mt-2"}`}
    >
      <h2 className={`${H2_CLASS} mb-4`} style={HEADING_FONT}>
        {num && <span className="heading-num">{`${num}.`}</span>}
        {subsection.title}
      </h2>
      <ContentBlocks items={subsection.content} labels={labels} title={subsection.title} />
    </section>
  );
}

export default function SectionContent({ section, ui, num = null, note, after }: SectionContentProps) {
  const labels: VerseLabels = {
    translation: t(ui, "verse.translationHint"),
    wbw: t(ui, "verse.wbwHint"),
    mood: {
      button: t(ui, "mood.button"),
      words: t(ui, "mood.words"),
      translation: t(ui, "mood.translation"),
      machine: t(ui, "mood.machine"),
      transcript: t(ui, "mood.transcript"),
      audio: t(ui, "mood.audio"),
      close: t(ui, "mood.close"),
    },
  };
  return (
    <article className="reader-article">
      {/* Section title */}
      <header className="mb-8">
        <h1 className={H1_CLASS} style={HEADING_FONT}>
          {num && <span className="heading-num">{`${num}.`}</span>}
          {section.title}
        </h1>
        {section.subtitle && (
          <p
            className="text-base text-[#555] mt-2 italic"
            style={{ fontFamily: "var(--font-noto-serif, Georgia, serif)" }}
          >
            {section.subtitle}
          </p>
        )}
        <div className="mt-3 h-px bg-[#ccc]" />
        {note && <p className="section-note mt-3 text-[14px] italic leading-6 text-[#5C3D2E]">{note}</p>}
      </header>

      {/* Main content */}
      {section.content.length > 0 && (
        <div>
          <ContentBlocks items={section.content} labels={labels} title={section.title} />
        </div>
      )}

      {/* Subsections */}
      {section.subsections &&
        section.subsections.length > 0 &&
        section.subsections.map((sub, i) => (
          <SubsectionBlock
            key={sub.id}
            subsection={sub}
            num={subsectionNumber(num, i)}
            labels={labels}
            separated={i > 0 || section.content.length > 0}
          />
        ))}

      {after}
    </article>
  );
}
