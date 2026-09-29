import bookJson from "@/data/book.json";

export interface PairedItem {
  label: string;
  value: string;
}

export interface ContentItem {
  type: string;
  content?: string;
  sanskrit?: string;
  translation?: string;
  src?: string;
  alt?: string;
  items?: PairedItem[];
  layout?: string;
}

export interface Subsection {
  id: string;
  title: string;
  content: ContentItem[];
}

export interface Section {
  id: string;
  title: string;
  subtitle?: string | null;
  page: string;
  content: ContentItem[];
  subsections: Subsection[];
}

export interface Book {
  title: string;
  subtitle: string;
  sections: Section[];
}

/** Slim table-of-contents shape passed to client components (no body text). */
export interface TocSection {
  id: string;
  title: string;
  page: string;
  subsections: { id: string; title: string }[];
}

/** One entry of public/search-index.json (see scripts/build-search-index.mjs). */
export interface SearchEntry {
  section: string;
  anchor?: string;
  title: string;
  sectionTitle: string;
  text: string;
}

export const book = bookJson as Book;

export function getSection(id: string): Section | undefined {
  return book.sections.find((s) => s.id === id);
}

export function getToc(): TocSection[] {
  return book.sections.map((s) => ({
    id: s.id,
    title: s.title,
    page: s.page,
    subsections: (s.subsections ?? []).map((sub) => ({
      id: sub.id,
      title: sub.title,
    })),
  }));
}

/** Lowercase and strip combining diacritics (NFD). */
export function normalizeText(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}
