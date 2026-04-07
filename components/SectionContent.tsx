"use client";

import React from "react";

interface ContentItem {
  type: string;
  content?: string;
  sanskrit?: string;
  translation?: string;
  src?: string;
  alt?: string;
}

interface Subsection {
  id: string;
  title: string;
  content: ContentItem[];
}

interface Section {
  id: string;
  title: string;
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
            <p className="sanskrit text-base leading-relaxed text-[#1a1a1a] mb-2">
              {item.sanskrit}
            </p>
          )}
          {item.translation && (
            <p className="translation text-[15px] leading-relaxed mt-1">
              {item.translation}
            </p>
          )}
        </div>
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
        className="text-lg font-bold mb-3 pb-2 border-b border-[#ccc] text-[#1a1a1a]"
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
          className="text-2xl sm:text-3xl font-bold text-[#1a1a1a]"
          style={{
            fontFamily: "var(--font-noto-serif, Georgia, serif)",
          }}
        >
          {section.title}
        </h1>
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
