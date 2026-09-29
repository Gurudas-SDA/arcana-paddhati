import type { Metadata } from "next";
import { notFound } from "next/navigation";
import SectionContent from "@/components/SectionContent";
import { book, getSection } from "@/lib/book";

// Static export: only the section ids known at build time exist.
export const dynamicParams = false;

export function generateStaticParams() {
  return book.sections.map((s) => ({ section: s.id }));
}

export async function generateMetadata({
  params,
}: PageProps<"/[section]">): Promise<Metadata> {
  const { section: id } = await params;
  const section = getSection(id);
  return {
    title: section ? `${section.title} \u2014 Arcana Paddhati` : "Arcana Paddhati",
  };
}

export default async function SectionPage({
  params,
}: PageProps<"/[section]">) {
  const { section: id } = await params;
  const section = getSection(id);
  if (!section) notFound();
  return <SectionContent section={section} />;
}
