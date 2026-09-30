import React from "react";
import { sanskritLang, type ContentItem, type Section, type Subsection } from "@/lib/book";
import { t, type UiDict } from "@/lib/i18n";
import CollapsibleVerse from "@/components/CollapsibleVerse";

/** Localised labels of the verse panel chips. */
interface VerseLabels {
  translation: string;
  wbw: string;
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

/** A "list" block: one item per line, rendered as a numbered list 1) 2) 3). */
function NumberedList({ content }: { content: string }) {
  const items = content.split("\n").filter((line) => line.trim() !== "");
  const width = String(items.length).length > 1 ? "w-7" : "w-5";
  return (
    <ol role="list" className="my-4 space-y-1 text-[15px] leading-7 text-[#1a1a1a]">
      {items.map((line, i) => (
        <li key={i} className="flex gap-2">
          <span className={`${width} shrink-0 text-right tabular-nums text-[#5C3D2E]`}>
            {i + 1})
          </span>
          <span className="min-w-0">{line}</span>
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
          {item.content}
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
          <span className="min-w-0">{item.content}</span>
        </p>
      );

    case "list":
      return <NumberedList key={index} content={item.content ?? ""} />;

    case "paired-list":
      if (item.layout === "vertical") {
        return (
          <div className="my-4 space-y-4" key={index}>
            {item.items?.map((pair, i) => (
              <div key={i}>
                <p lang={sanskritLang(pair.label)} className="sanskrit text-base leading-relaxed text-[#1a1a1a]">{pair.label}</p>
                <p className="translation text-[14px] leading-relaxed ml-8">{pair.value}</p>
              </div>
            ))}
          </div>
        );
      }
      return (
        <div className="my-4 grid gap-y-0.5" style={{ gridTemplateColumns: "auto 1fr" }} key={index}>
          {item.items?.map((pair, i) => (
            <React.Fragment key={i}>
              <span className="pr-8 py-0.5 text-[15px]">{pair.label}</span>
              <span className="py-0.5 text-[15px]">{pair.value}</span>
            </React.Fragment>
          ))}
        </div>
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
                  {line}
                  {li < arr.length - 1 && <br />}
                </React.Fragment>
              ))
            : item.content}
        </p>
      );
  }
}

function ContentBlocks({ items, labels }: { items: ContentItem[]; labels: VerseLabels }) {
  const long = items.length >= LONG_CONTENT_BLOCKS;
  return (
    <>
      {items.map((item, idx) => (
        <ContentBlock
          key={idx}
          item={item}
          index={idx}
          labels={labels}
          separated={long && idx > 0 && item.type === "subtitle"}
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
