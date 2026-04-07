"use client";

import React from "react";

interface ContentItem {
  type: string;
  content?: string;
  sanskrit?: string;
  translation?: string;
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
        <div className="verse-card my-6" key={index}>
          {item.sanskrit && (
            <p className="sanskrit text-base leading-relaxed text-[#2C1810] mb-3">
              {item.sanskrit}
            </p>
          )}
          {item.translation && (
            <p className="text-sm leading-relaxed text-[#5C3D2E] mt-2 pl-3 border-l-2 border-[#E8DCC8]">
              {item.translation}
            </p>
          )}
        </div>
      );

    case "instruction":
      return (
        <div className="instruction-step my-4" key={index}>
          <p className="text-[15px] leading-7 text-[#2C1810]">
            {item.content}
          </p>
        </div>
      );

    case "text":
    default:
      return (
        <p
          className="text-[15px] leading-7 text-[#2C1810] my-4"
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
        className="text-lg font-semibold mb-4 pb-2 border-b border-[#E8DCC8]"
        style={{ color: "#B8860B" }}
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
          className="text-2xl sm:text-3xl font-bold mb-2"
          style={{
            fontFamily: "var(--font-noto-serif, Georgia, serif)",
            color: "#2C1810",
          }}
        >
          {section.title}
        </h1>
        {section.page && (
          <p className="text-sm text-[#B8860B]">Page {section.page}</p>
        )}
        <div className="mt-4 h-px bg-gradient-to-r from-[#B8860B] via-[#D4A843] to-transparent" />
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
