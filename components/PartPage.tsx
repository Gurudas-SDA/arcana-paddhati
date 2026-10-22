import type { TocPart } from "@/lib/book";
import { getUi } from "@/lib/content";
import { t } from "@/lib/i18n";
import SectionChapters from "@/components/SectionChapters";

const HEADING_FONT = { fontFamily: "var(--font-book, Georgia, serif)" };

/** Page of a part of the book (Part I, II, …): its chapters, or a
 *  "in preparation" line while the part has none yet. V39 (Vraja Lila msg 1326 /
 *  6090): the chapters are the «В этом разделе» block (components/SectionChapters.tsx);
 *  in «Лента» (`inBook`) it is left out — the chapters follow right below there. */
export default function PartPage({ part, lang, inBook = false }: { part: TocPart; lang: string; inBook?: boolean }) {
  const ui = getUi(lang);
  return (
    <article className="reader-article">
      <header className="mb-8">
        <p className="text-sm uppercase tracking-[0.12em] text-[#9C7A4E]" style={HEADING_FONT}>
          {t(ui, "part.label", { n: part.numeral })}
        </p>
        <h1
          className="mt-1 text-2xl sm:text-3xl font-semibold leading-tight text-[#1a1a1a]"
          style={HEADING_FONT}
        >
          {part.title}
        </h1>
        <div className="mt-3 h-px bg-[#ccc]" />
      </header>
      {part.sections.length === 0 ? (
        <p className="text-[15px] leading-7 italic text-[#5C3D2E]">{t(ui, "part.empty")}</p>
      ) : (
        !inBook && <SectionChapters lang={lang} ui={ui} ids={part.sections} numbered />
      )}
    </article>
  );
}
