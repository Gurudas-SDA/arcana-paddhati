import { getParts, getSection, getSectionIds, getSectionNumber, getUi, isFallbackSection } from "@/lib/content";
import { tocLayout } from "@/lib/book";
import ContinuousBook from "@/components/ContinuousBook";
import SectionContent from "@/components/SectionContent";
import PartPage from "@/components/PartPage";
import GroupContents from "@/components/GroupContents";
import NextChapter from "@/components/NextChapter";
import { t } from "@/lib/i18n";

/** «Прокручивать» (A89, lib/readingMode.ts): the whole book of one language in
 *  one scroll (Vraja Lila PR 2), on its own route — the cover stays light.
 *  Navigation (contents, language, install) is in the app shell. */
export default function BookPage({ lang }: { lang: string }) {
  const ui = getUi(lang);
  const parts = getParts(lang);
  return (
    <ContinuousBook lang={lang}>
      {tocLayout(getSectionIds(), parts).map((item) => {
        const part = item.kind === "part" ? parts.find((p) => p.id === item.id) : undefined;
        const section = item.kind === "section" ? getSection(lang, item.id) : undefined;
        return (
          <div key={item.id} data-book-section={item.id} className="book-section">
            {part ? <PartPage part={part} lang={lang} /> : section && (
              <SectionContent
                section={section}
                ui={ui}
                num={getSectionNumber(item.id)}
                note={isFallbackSection(lang, item.id) ? t(ui, "section.fallback") : undefined}
                after={<><GroupContents lang={lang} id={item.id} ui={ui} /><NextChapter lang={lang} id={item.id} ui={ui} /></>}
              />
            )}
          </div>
        );
      })}
    </ContinuousBook>
  );
}
