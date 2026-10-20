import { getParts, getSection, getSectionIds, getSectionNumber, getUi, sectionNote } from "@/lib/content";
import { tocLayout } from "@/lib/book";
import ContinuousBook from "@/components/ContinuousBook";
import SectionContent from "@/components/SectionContent";
import PartPage from "@/components/PartPage";
import GroupContents from "@/components/GroupContents";

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
                note={sectionNote(lang, item.id)}
                after={<GroupContents lang={lang} id={item.id} ui={ui} />}
              />
            )}
          </div>
        );
      })}
    </ContinuousBook>
  );
}
