"use client";

import React from "react";

interface ContentItem {
  type: string;
  content?: string;
  sanskrit?: string;
  translation?: string;
  src?: string;
  alt?: string;
  items?: { label: string; value: string }[];
}

interface Subsection {
  id: string;
  title: string;
  content: ContentItem[];
}

interface Section {
  id: string;
  title: string;
  subtitle?: string | null;
  page: string;
  content: ContentItem[];
  subsections: Subsection[];
}

interface SectionContentProps {
  section: Section;
}

function ContentBlock({ item, index }: { item: ContentItem; index: number }) {
  switch (item.type) {
    case "verse":
      return (
        <div className="my-5" key={index}>
          {item.sanskrit && (
            <div className="sanskrit text-base leading-relaxed text-[#1a1a1a] mb-2">
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
          )}
          {item.translation && (
            <p className="translation text-[15px] leading-relaxed mt-1 pl-4 border-l border-[#999] ml-1">
              {item.translation}
            </p>
          )}
        </div>
      );

    case "subtitle":
      return (
        <p
          className="text-lg leading-7 text-[#1a1a1a] my-4 font-bold"
          key={index}
          style={{ fontFamily: "var(--font-noto-serif, Georgia, serif)" }}
        >
          {item.content}
        </p>
      );

    case "instruction":
      return (
        <p
          className="text-[15px] leading-7 text-[#1a1a1a] my-3"
          key={index}
        >
          &#9656; {item.content}
        </p>
      );

    case "paired-list":
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
          {item.content}
        </p>
      );
  }
}

function SubsectionBlock({ subsection }: { subsection: Subsection }) {
  return (
    <div id={subsection.id} className="mt-10 scroll-mt-6">
      <h3
        className="text-xl font-normal mb-4 text-[#1a1a1a]"
        style={{ fontFamily: "var(--font-noto-serif, Georgia, serif)" }}
      >
        {subsection.title}
      </h3>
      {subsection.content.map((item, idx) => (
        <ContentBlock key={idx} item={item} index={idx} />
      ))}
    </div>
  );
}

export default function SectionContent({ section }: SectionContentProps) {
  return (
    <article className="max-w-3xl mx-auto px-6 py-8 sm:px-10 sm:py-12">
      {/* Section title */}
      <header className="mb-8">
        <h1
          className="text-2xl sm:text-3xl font-semibold text-[#1a1a1a]"
          style={{
            fontFamily: "var(--font-noto-serif, Georgia, serif)",
          }}
        >
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
      <div className="mb-8">
        {section.content.map((item, idx) => (
          <ContentBlock key={idx} item={item} index={idx} />
        ))}
      </div>

      {/* Subsections */}
      {section.subsections &&
        section.subsections.length > 0 &&
        section.subsections.map((sub) => (
          <SubsectionBlock key={sub.id} subsection={sub} />
        ))}
    </article>
  );
}
