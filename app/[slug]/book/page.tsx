// /<lang>/book/ — «Прокручивать» (A89): the whole book of a language in one scroll.
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import BookPage from "@/components/BookPage";
import { getSectionIds, getPartIds, getUi } from "@/lib/content";
import { PREFIXED_LANGUAGES, isPrefixedLang, t } from "@/lib/i18n";
import { BOOK_SEGMENT } from "@/lib/bookRoute";

export const dynamicParams = false;

export function generateStaticParams() {
  if ([...getSectionIds(), ...getPartIds()].includes(BOOK_SEGMENT)) {
    throw new Error(`Section id equal to the book route: ${BOOK_SEGMENT}`);
  }
  return PREFIXED_LANGUAGES.map((l) => ({ slug: l.code }));
}

export async function generateMetadata({ params }: PageProps<"/[slug]/book">): Promise<Metadata> {
  const { slug } = await params;
  const ui = getUi(slug);
  return { title: t(ui, "meta.title"), robots: { index: false } };
}

export default async function LangBook({ params }: PageProps<"/[slug]/book">) {
  const { slug } = await params;
  if (!isPrefixedLang(slug)) notFound();
  return <BookPage lang={slug} />;
}
