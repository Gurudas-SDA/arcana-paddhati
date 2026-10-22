import type { TocPart } from "@/lib/book";
import { getUi } from "@/lib/content";
import { t } from "@/lib/i18n";

const HEADING_FONT = { fontFamily: "var(--font-book, Georgia, serif)" };

/** Heading of a part of the book (Part I, II, …) in «Лента», with a "in
 *  preparation" line while the part has no chapters yet. V45 (Vraja Lila msg
 *  6178 / 1412, 22.10.2026): a part has no page of its own any more — no
 *  «В этом разделе» box (V39 removed), not in «Назад» / «Вперёд», its row in
 *  «Содержание» only expands its chapters. Its old address still opens this
 *  heading (old links / bookmarks), with «Назад» / «Вперёд» to its neighbours. */
export default function PartPage({ part, lang }: { part: TocPart; lang: string; inBook?: boolean }) {
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
      {part.sections.length === 0 && (
        <p className="text-[15px] leading-7 italic text-[#5C3D2E]">{t(ui, "part.empty")}</p>
      )}
    </article>
  );
}
