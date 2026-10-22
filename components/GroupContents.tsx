import { getFrontGroup } from "@/lib/content";
import { t, type UiDict } from "@/lib/i18n";
import SectionChapters from "@/components/SectionChapters";

/**
 * The Introduction's page: after its own text, the list of its chapters
 * (Emblem, Vigraha-tattva — no chapter numbers), like a part's page lists its
 * chapters (Satkirti, 06.10.2026: the Introduction is an expandable group of the
 * contents). V39 (Vraja Lila msg 1326): the list is the «В этом разделе» block
 * (components/SectionChapters.tsx). Nothing on any other page; not in «Лента».
 */
export default function GroupContents({ lang, id, ui }: { lang: string; id: string; ui: UiDict }) {
  const group = getFrontGroup();
  if (!group || group.head !== id) return null;
  return (
    <SectionChapters
      lang={lang}
      ui={ui}
      ids={group.members}
      numbered={false}
      label={t(ui, "group.contents")}
      className="group-contents mt-8"
    />
  );
}
