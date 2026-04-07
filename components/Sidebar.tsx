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

interface SidebarProps {
  sections: Section[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onClose: () => void;
}

export default function Sidebar({
  sections,
  selectedId,
  onSelect,
  searchQuery,
  onSearchChange,
  onClose,
}: SidebarProps) {
  const normalizeText = (text: string) =>
    text
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");

  const normalizedQuery = normalizeText(searchQuery);

  const filteredSections = sections.filter((section) => {
    if (!searchQuery.trim()) return true;
    const matchesTitle = normalizeText(section.title).includes(normalizedQuery);
    const matchesSubsection = section.subsections?.some((sub) =>
      normalizeText(sub.title).includes(normalizedQuery)
    );
    return matchesTitle || matchesSubsection;
  });

  return (
    <aside className="flex flex-col h-full bg-white border-r border-[#E8DCC8]">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-[#E8DCC8]">
        <div className="flex items-center gap-2">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#B8860B"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          </svg>
          <h2
            className="text-lg font-semibold"
            style={{ color: "#B8860B" }}
          >
            Contents
          </h2>
        </div>
        {/* Mobile close button */}
        <button
          onClick={onClose}
          className="lg:hidden p-1 rounded hover:bg-[#F5E6C8] transition-colors"
          aria-label="Close menu"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#2C1810"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      {/* Search */}
      <div className="px-4 py-3 border-b border-[#E8DCC8]">
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#B8860B"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            placeholder="Search sections..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-[#E8DCC8] bg-[#FDF8F0] text-[#2C1810] placeholder-[#B8860B]/50 focus:outline-none focus:border-[#B8860B] focus:ring-1 focus:ring-[#B8860B]/30 transition-colors"
          />
          {searchQuery && (
            <button
              onClick={() => onSearchChange("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#5C3D2E] hover:text-[#2C1810]"
              aria-label="Clear search"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Sections list */}
      <nav className="flex-1 overflow-y-auto sidebar-scroll py-2">
        {filteredSections.length === 0 ? (
          <p className="px-5 py-4 text-sm text-[#5C3D2E] italic">
            No sections found
          </p>
        ) : (
          <ul className="space-y-0.5">
            {filteredSections.map((section) => {
              const isSelected = selectedId === section.id;
              return (
                <li key={section.id}>
                  <button
                    onClick={() => {
                      onSelect(section.id);
                      onClose();
                    }}
                    className={`w-full text-left px-5 py-3 flex items-start justify-between gap-2 transition-colors ${
                      isSelected
                        ? "bg-[#FAF3E8] border-l-3 border-[#B8860B]"
                        : "hover:bg-[#FDF8F0] border-l-3 border-transparent"
                    }`}
                  >
                    <span
                      className={`text-sm leading-snug ${
                        isSelected
                          ? "font-semibold text-[#B8860B]"
                          : "text-[#2C1810]"
                      }`}
                    >
                      {section.title}
                    </span>
                    {section.page && (
                      <span className="text-xs text-[#B8860B]/60 shrink-0 mt-0.5">
                        {section.page}
                      </span>
                    )}
                  </button>

                  {/* Subsections - show when selected or search matches */}
                  {isSelected &&
                    section.subsections &&
                    section.subsections.length > 0 && (
                      <ul className="ml-6 border-l border-[#E8DCC8]">
                        {section.subsections.map((sub) => (
                          <li key={sub.id}>
                            <button
                              onClick={() => {
                                const el = document.getElementById(sub.id);
                                if (el) {
                                  el.scrollIntoView({ behavior: "smooth" });
                                }
                                onClose();
                              }}
                              className="w-full text-left px-4 py-2 text-xs text-[#5C3D2E] hover:text-[#B8860B] hover:bg-[#FDF8F0] transition-colors"
                            >
                              {sub.title}
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                </li>
              );
            })}
          </ul>
        )}
      </nav>
    </aside>
  );
}
