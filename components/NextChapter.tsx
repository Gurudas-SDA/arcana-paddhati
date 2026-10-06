import NextChapterLink from "@/components/NextChapterLink";
import { getNextChapter } from "@/lib/content";
import { localeHref, t, type UiDict } from "@/lib/i18n";

/**
 * «След. глава ›» at the end of a chapter (Satkirti, 06.10.2026): a link to
 * the next page in the contents' order, with that chapter's number and title
 * under it (smaller). Nothing after the last chapter. A link (a new history
 * entry): the next chapter opens at its top and Back / «‹ Назад» returns here.
 */
export default function NextChapter({ lang, id, ui }: { lang: string; id: string; ui: UiDict }) {
  const next = getNextChapter(lang, id);
  if (!next) return null;
  const label = next.part
    ? `${t(ui, "part.label", { n: next.part })}. ${next.title}`
    : `${next.num ? `${next.num}. ` : ""}${next.title}`;
  return (
    <nav className="chapter-next" aria-label={t(ui, "reader.next")}>
      <NextChapterLink href={localeHref(lang, next.id)} id={next.id} className="chapter-next-link">
        <span className="chapter-next-label">
          {t(ui, "reader.next")}
          <span aria-hidden="true" className="chapter-next-arrow">
            {" ›"}
          </span>
        </span>
        <span className="chapter-next-title">{label}</span>
      </NextChapterLink>
    </nav>
  );
}
