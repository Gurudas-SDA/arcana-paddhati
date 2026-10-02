"use client";

import React from "react";
import { useRouter } from "next/navigation";
import {
  LANGUAGES,
  LANG_STORAGE_KEY,
  localeHref,
  t,
  type UiDict,
} from "@/lib/i18n";

/**
 * Native <select> language menu. Switching keeps the current section (and
 * subsection anchor); the choice is remembered in localStorage, but the URL
 * always decides which language is shown.
 */
export default function LanguageSwitcher({
  lang,
  sectionId,
  available,
  ui,
  block = false,
}: {
  lang: string;
  sectionId: string | null;
  /** Languages whose translated text exists; others are marked. */
  available: string[];
  ui: UiDict;
  /** Full-width variant (own row in the desktop sidebar). */
  block?: boolean;
}) {
  const router = useRouter();

  const onChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const next = e.target.value;
    try {
      localStorage.setItem(LANG_STORAGE_KEY, next);
    } catch {
      // storage unavailable — the URL still carries the language
    }
    router.push(localeHref(next, sectionId) + (sectionId ? window.location.hash : ""));
  };

  return (
    <label className={`relative items-center shrink-0 ${block ? "flex w-full" : "inline-flex"}`}>
      <span className="sr-only">{t(ui, "language.label")}</span>
      <svg
        className="pointer-events-none absolute left-2"
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#B8860B"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
      </svg>
      <select
        value={lang}
        onChange={onChange}
        title={t(ui, "language.label")}
        className={`appearance-none ${block ? "w-full" : "max-w-[10rem]"} pl-7 pr-6 py-1 text-xs rounded-md border border-[#E8DCC8] bg-[#FDF8F0] text-[#2C1810] focus:outline-none focus:border-[#B8860B] focus:ring-1 focus:ring-[#B8860B]/30 transition-colors cursor-pointer`}
      >
        {LANGUAGES.map((l) => (
          <option key={l.code} value={l.code} lang={l.htmlLang}>
            {available.includes(l.code)
              ? l.name
              : `${l.name} ${t(ui, "language.fallbackSuffix")}`}
          </option>
        ))}
      </select>
      <svg
        className="pointer-events-none absolute right-1.5"
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#5C3D2E"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </label>
  );
}
