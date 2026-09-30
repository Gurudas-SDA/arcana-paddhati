// /<lang>/<section>/ — a section in a non-default language. Section ids are the
// same in every language; a missing translation falls back to English.
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import SectionContent from "@/components/SectionContent";
import { getSection, getSectionIds, getUi } from "@/lib/content";
import { PREFIXED_LANGUAGES, isPrefixedLang, t } from "@/lib/i18n";

export const dynamicParams = false;

export function generateStaticParams() {
  const ids = getSectionIds();
  return PREFIXED_LANGUAGES.flatMap((l) =>
    ids.map((id) => ({ slug: l.code, section: id }))
  );
}

export async function generateMetadata({
  params,
}: PageProps<"/[slug]/[section]">): Promise<Metadata> {
  const { slug: lang, section: id } = await params;
  const ui = getUi(lang);
  const section = getSection(lang, id);
  return {
    title: section
      ? t(ui, "meta.sectionTitle", { section: section.title })
      : t(ui, "header.title"),
  };
}

export default async function LangSectionPage({
  params,
}: PageProps<"/[slug]/[section]">) {
  const { slug: lang, section: id } = await params;
  if (!isPrefixedLang(lang)) notFound();
  const section = getSection(lang, id);
  if (!section) notFound();
  return <SectionContent section={section} />;
}
