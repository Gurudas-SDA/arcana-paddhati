import React from "react";
import {
  parseInline,
  sanskritLang,
  stripInline,
  type ContentItem,
  type Section,
  type Subsection,
} from "@/lib/book";
import { t, type UiDict } from "@/lib/i18n";
import CollapsibleVerse from "@/components/CollapsibleVerse";
import MoodBlock, { type MoodLabels } from "@/components/MoodBlock";

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
 *  to match the numbers of an illustration ("4, 5", gaps); "" = no number (–). */
function NumberedList({ content, numbers }: { content: string; numbers?: string[] }) {
  const items = content.split("\n").filter((line) => line.trim() !== "");
  const labels = items.map((_, i) =>
    numbers ? (numbers[i] ? `${numbers[i]})` : "–") : `${i + 1})`,
  );
  const longest = Math.max(...labels.map((l) => l.length));
  const width = longest > 3 ? "w-12" : longest > 2 ? "w-7" : "w-5";
  return (
    <ol role="list" className="my-4 space-y-1 text-[15px] leading-7 text-[#1a1a1a]">
      {items.map((line, i) => (
        <li key={i} className="flex gap-2">
          <span className={`${width} shrink-0 whitespace-nowrap text-right tabular-nums text-[#5C3D2E]`}>
            {labels[i]}
          </span>
          <span className="min-w-0">
            <Inline text={line} />
          </span>
        </li>
      ))}
    </ol>
  );
}

function ContentBlock({
  item,
  index,
  labels,
  separated = false,
}: {
  item: ContentItem;
  index: number;
  labels: VerseLabels;
  /** Draw a rule above this block (used for h3 groups in long content). */
  separated?: boolean;
}) {
  switch (item.type) {
    case "verse": {
      const isInlineMantra = item.translation === undefined;
      const sanskrit = item.sanskrit && (
        <div lang={sanskritLang(item.sanskrit)} className={`sanskrit text-base leading-relaxed text-[#1a1a1a] ${isInlineMantra ? 'ml-8' : ''} mb-2`}>
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
              {item.translation}
            </p>
          )}
        </div>
      );
    }

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
      return <NumberedList key={index} content={item.content ?? ""} numbers={item.numbers} />;

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
                  {stripInline(pair.label)}
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
        <div className="my-4 grid gap-y-0.5" style={{ gridTemplateColumns: "auto 1fr" }} key={index}>
          {item.items?.map((pair, i) => (
            <React.Fragment key={i}>
              <span className="pr-8 py-0.5 text-[15px]">
                <Inline text={pair.label} />
              </span>
              <span className="py-0.5 text-[15px]">
                <Inline text={pair.value} />
              </span>
            </React.Fragment>
          ))}
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
          labels={labels.mood}
        />
      );

    case "image":
      return (
        <img
          key={index}
          src={`/arcana-paddhati/images/${item.src}`}
          alt={item.alt || ""}
          className="book-image"
          style={{ maxWidth: "420px" }}
        />
      );

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

function ContentBlocks({ items, labels }: { items: ContentItem[]; labels: VerseLabels }) {
  // A leading "mood" block (Gurudev's quote) does not count as content for
  // the layout rules below: the next block is still the "first" one.
  const lead = items.findIndex((item) => item.type !== "mood");
  const offset = lead < 0 ? items.length : lead;
  const long = items.length - offset >= LONG_CONTENT_BLOCKS;
  return (
    <>
      {items.map((item, idx) => (
        <ContentBlock
          key={idx}
          item={item}
          index={Math.max(0, idx - offset)}
          labels={labels}
          separated={long && idx > offset && item.type === "subtitle"}
        />
      ))}
    </>
  );
}

function SubsectionBlock({
  subsection,
  separated,
  labels,
}: {
  subsection: Subsection;
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
        {subsection.title}
      </h2>
      <ContentBlocks items={subsection.content} labels={labels} />
    </section>
  );
}

export default function SectionContent({ section, ui }: SectionContentProps) {
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
      more: t(ui, "mood.more"),
      showAll: t(ui, "mood.showAll"),
    },
  };
  return (
    <article className="max-w-3xl mx-auto px-6 py-8 sm:px-10 sm:py-12">
      {/* Section title */}
      <header className="mb-8">
        <h1 className={H1_CLASS} style={HEADING_FONT}>
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
      </header>

      {/* Main content */}
      {section.content.length > 0 && (
        <div>
          <ContentBlocks items={section.content} labels={labels} />
        </div>
      )}

      {/* Subsections */}
      {section.subsections &&
        section.subsections.length > 0 &&
        section.subsections.map((sub, i) => (
          <SubsectionBlock
            key={sub.id}
            subsection={sub}
            labels={labels}
            separated={i > 0 || section.content.length > 0}
          />
        ))}
    </article>
  );
}
