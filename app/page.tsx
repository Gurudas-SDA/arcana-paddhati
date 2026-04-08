"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import bookData from "@/data/book.json";
import Sidebar from "@/components/Sidebar";
import SectionContent from "@/components/SectionContent";
import InstallButton from "@/components/InstallButton";

export default function Home() {
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(
    null
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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

  const selectedSection = bookData.sections.find(
    (s) => s.id === selectedSectionId
  );

  return (
    <div className="flex h-full">
      {/* Desktop sidebar */}
      <div className="hidden lg:flex lg:w-80 lg:shrink-0 lg:flex-col h-full">
        <Sidebar
          sections={bookData.sections}
          selectedId={selectedSectionId}
          onSelect={setSelectedSectionId}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onClose={() => {}}
        />
      </div>

      {/* Mobile sidebar overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/30 sidebar-backdrop"
            onClick={() => setMobileMenuOpen(false)}
            aria-hidden="true"
          />
          {/* Sidebar panel */}
          <div className="fixed inset-y-0 left-0 z-50 w-80 max-w-[85vw] sidebar-transition">
            <Sidebar
              sections={bookData.sections}
              selectedId={selectedSectionId}
              onSelect={setSelectedSectionId}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              onClose={() => setMobileMenuOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Main content area */}
      <main className="flex-1 overflow-y-auto">
        {/* Mobile header */}
        <div className="sticky top-0 z-30 lg:hidden flex items-center gap-3 px-4 py-3 bg-white/95 backdrop-blur-sm border-b border-[#ddd]">
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
        {selectedSection ? (
          <SectionContent section={selectedSection} />
        ) : (
          <LandingView />
        )}
      </main>
    </div>
  );
}

function LandingView() {
  return (
    <div className="flex flex-col items-center justify-center min-h-full px-6 py-12">
      <div className="max-w-md w-full text-center">
        {/* Cover image */}
        <div className="mb-8 mx-auto w-56 sm:w-64 rounded-lg overflow-hidden shadow-lg shadow-[#2C1810]/10">
          <Image
            src="/arcana-paddhati/cover.jpg"
            alt="Arcana Paddhati book cover"
            width={256}
            height={360}
            className="w-full h-auto"
            priority
          />
        </div>

        {/* Title */}
        <h1
          className="text-2xl sm:text-3xl font-bold mb-2"
          style={{
            fontFamily: "var(--font-noto-serif, Georgia, serif)",
            color: "#2C1810",
          }}
        >
          {bookData.title}
        </h1>

        {/* Subtitle */}
        <p
          className="text-base mb-6"
          style={{ color: "#B8860B" }}
        >
          {bookData.subtitle}
        </p>

        {/* Decorative divider */}
        <div className="flex items-center justify-center gap-3 mb-6">
          <div className="h-px w-12 bg-gradient-to-r from-transparent to-[#D4A843]" />
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="#B8860B"
            className="opacity-60"
          >
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
          </svg>
          <div className="h-px w-12 bg-gradient-to-l from-transparent to-[#D4A843]" />
        </div>

        {/* Description */}
        <p className="text-sm leading-relaxed text-[#5C3D2E] max-w-sm mx-auto">
          A comprehensive manual for the sacred process of deity worship
          (arcana) in the Vaishnava tradition. Select a section from the
          table of contents to begin reading.
        </p>

        {/* Install PWA button */}
        <div className="mt-6 flex justify-center">
          <InstallButton />
        </div>

        {/* Arrow hint for desktop */}
        <div className="hidden lg:flex items-center justify-center gap-2 mt-8 text-[#B8860B]/50">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
          <span className="text-xs">Select a section from the sidebar</span>
        </div>

        {/* Tap hint for mobile */}
        <div className="flex lg:hidden items-center justify-center gap-2 mt-8 text-[#B8860B]/50">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
          <span className="text-xs">Tap the menu to browse sections</span>
        </div>
      </div>
    </div>
  );
}
