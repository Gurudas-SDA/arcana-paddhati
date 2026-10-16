// /book/ — «Прокручивать» (A89): the whole English book in one scroll.
import type { Metadata } from "next";
import BookPage from "@/components/BookPage";
import { getUi } from "@/lib/content";
import { DEFAULT_LANG, t } from "@/lib/i18n";

export function generateMetadata(): Metadata {
  const ui = getUi(DEFAULT_LANG);
  return { title: t(ui, "meta.title"), robots: { index: false } };
}

export default function Book() {
  return <BookPage lang={DEFAULT_LANG} />;
}
