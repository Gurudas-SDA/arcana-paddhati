"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import InstallBanner from "@/components/InstallBanner";
import type { SearchEntry, TocSection } from "@/lib/book";

const SEARCH_INDEX_URL = "/arcana-paddhati/search-index.json";

type IndexState = SearchEntry[] | "loading" | "error" | null;

export default function AppShell({
  sections,
  children,
}: {
  sections: TocSection[];
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [searchQuery, setSearchQuery] = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchIndex, setSearchIndex] = useState<IndexState>(null);
  const indexRequested = useRef(false);

  // Close the mobile menu whenever the route changes (incl. back/forward).
  const [lastPathname, setLastPathname] = useState(pathname);
  if (pathname !== lastPathname) {
    setLastPathname(pathname);
    setMobileMenuOpen(false);
  }

  // Close mobile menu on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMobileMenuOpen(false);
      }
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, []);

  // Prevent body scroll when mobile menu is open
  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileMenuOpen]);

  // Full-text search index: fetched lazily on first focus of the search box.
  const loadSearchIndex = useCallback(() => {
    if (indexRequested.current) return;
    indexRequested.current = true;
    setSearchIndex("loading");
    fetch(SEARCH_INDEX_URL)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<SearchEntry[]>;
      })
      .then((entries) => setSearchIndex(entries))
      .catch(() => {
        // Fall back to title-only search; allow a retry on next focus.
        indexRequested.current = false;
        setSearchIndex("error");
      });
  }, []);

  const entries = Array.isArray(searchIndex) ? searchIndex : null;

  const sidebarProps = {
    sections,
    searchQuery,
    onSearchChange: setSearchQuery,
    onSearchFocus: loadSearchIndex,
    searchEntries: entries,
  };

  return (
    <div className="app-shell flex h-full">
      {/* Desktop sidebar */}
      <div className="no-print hidden lg:flex lg:w-80 lg:shrink-0 lg:flex-col h-full">
        <Sidebar {...sidebarProps} onClose={() => {}} />
      </div>

      {/* Mobile sidebar overlay */}
      {mobileMenuOpen && (
        <div className="no-print fixed inset-0 z-40 lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/30 sidebar-backdrop"
            onClick={() => setMobileMenuOpen(false)}
            aria-hidden="true"
          />
          {/* Sidebar panel */}
          <div className="fixed inset-y-0 left-0 z-50 w-80 max-w-[85vw] sidebar-transition">
            <Sidebar
              {...sidebarProps}
              onClose={() => setMobileMenuOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Main content area */}
      <main className="app-main flex-1 overflow-y-auto">
        <InstallBanner />
        {/* Mobile header */}
        <div className="no-print sticky top-0 z-30 lg:hidden flex items-center gap-3 px-4 py-3 bg-white/95 backdrop-blur-sm border-b border-[#ddd]">
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="p-2 rounded-lg hover:bg-[#F5E6C8] transition-colors"
            aria-label="Open menu"
          >
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#2C1810"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <h1
            className="text-sm font-semibold truncate text-[#1a1a1a]"
            style={{ fontFamily: "var(--font-noto-serif, Georgia, serif)" }}
          >
            Arcana Paddhati
          </h1>
        </div>

        {/* Content */}
        {children}
      </main>
    </div>
  );
}
