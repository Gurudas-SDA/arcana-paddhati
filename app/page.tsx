import Image from "next/image";
import { book as bookData } from "@/lib/book";

export default function Home() {
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
