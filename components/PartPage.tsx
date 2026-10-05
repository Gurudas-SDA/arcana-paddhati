import Link from "next/link";
import type { TocPart } from "@/lib/book";
import { getSection, getSectionNumber, getUi } from "@/lib/content";
import { localeHref, t } from "@/lib/i18n";

const HEADING_FONT = { fontFamily: "var(--font-noto-serif, Georgia, serif)" };

/** Page of a part of the book (Part I, II, …): its chapters, or a
 *  "in preparation" line while the part has none yet. */
export default function PartPage({ part, lang }: { part: TocPart; lang: string }) {
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
        <ol role="list" className="space-y-2 text-[15px] leading-7">
          {part.sections.map((id) => {
            const s = getSection(lang, id);
            if (!s) return null;
            const num = getSectionNumber(id);
            return (
              <li key={id}>
                <Link
                  href={localeHref(lang, id)}
                  className="text-[#1a1a1a] hover:text-[#B8860B] transition-colors"
                >
                  {num && <span className="heading-num">{`${num}.`}</span>}
                  {s.title}
                </Link>
              </li>
            );
          })}
        </ol>
      )}
    </article>
  );
}
