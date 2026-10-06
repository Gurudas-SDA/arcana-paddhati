// /<section>/ (English section) and /<lang>/ (home page of another language)
// share this dynamic segment, so section ids must never equal language codes.
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import HomePage from "@/components/HomePage";
import GroupContents from "@/components/GroupContents";
import NextChapter from "@/components/NextChapter";
import PartPage from "@/components/PartPage";
import SectionContent from "@/components/SectionContent";
import {
  getPart,
  getPartIds,
  getSection,
  getSectionIds,
  getSectionNumber,
  getUi,
} from "@/lib/content";
import { DEFAULT_LANG, PREFIXED_LANGUAGES, isPrefixedLang, t } from "@/lib/i18n";

// Static export: only the ids known at build time exist.
export const dynamicParams = false;

export function generateStaticParams() {
  const ids = [...getSectionIds(), ...getPartIds()];
  const clash = ids.filter((id) => isPrefixedLang(id));
  if (clash.length) {
    throw new Error(`Section id(s) equal to a language code: ${clash.join(", ")}`);
  }
  return [
    ...ids.map((id) => ({ slug: id })),
    ...PREFIXED_LANGUAGES.map((l) => ({ slug: l.code })),
  ];
}

export async function generateMetadata({
  params,
}: PageProps<"/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  if (isPrefixedLang(slug)) {
    const ui = getUi(slug);
    return { title: t(ui, "meta.title"), description: t(ui, "meta.description") };
  }
  const ui = getUi(DEFAULT_LANG);
  const section = getSection(DEFAULT_LANG, slug) ?? getPart(DEFAULT_LANG, slug);
  return {
    title: section
      ? t(ui, "meta.sectionTitle", { section: section.title })
      : t(ui, "header.title"),
  };
}

export default async function SlugPage({ params }: PageProps<"/[slug]">) {
  const { slug } = await params;
  if (isPrefixedLang(slug)) return <HomePage lang={slug} />;
  const part = getPart(DEFAULT_LANG, slug);
  if (part) return <PartPage part={part} lang={DEFAULT_LANG} />;
  const section = getSection(DEFAULT_LANG, slug);
  if (!section) notFound();
  const ui = getUi(DEFAULT_LANG);
  return (
    <SectionContent
      section={section}
      ui={ui}
      num={getSectionNumber(slug)}
      after={
        <>
          <GroupContents lang={DEFAULT_LANG} id={slug} ui={ui} />
          <NextChapter lang={DEFAULT_LANG} id={slug} ui={ui} />
        </>
      }
    />
  );
}
