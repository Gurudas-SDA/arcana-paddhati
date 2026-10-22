import Link from "next/link";
import { getSection, getSectionNumber } from "@/lib/content";
import { localeHref, t, type UiDict } from "@/lib/i18n";

/**
 * «В этом разделе» (V39, Vraja Lila msg 1324–1326, 22.10.2026, variant Б): under a
 * section's page (its own text, if it has one) the list of its chapters is a
 * navigation block — the heading «В этом разделе», then a row per chapter with
 * the arrow › at the right, like the rows of «Содержание», so it is clear that
 * the rows are links. Vraja Lila msg 6096 (22.10.2026): the block is a BOX in the
 * light gold of the tables' alternating rows (--rd-row-stripe), their shape and
 * width, as tall as the list with inner margins — so no separator line.
 * Every section built this way gets it (msg 1328/6090: «так же в подобных случаях
 * впредь и в разделах, которые структурированы так же»): the Introduction's page
 * (components/GroupContents.tsx) and each part's page (components/PartPage.tsx).
 * Not in «Лента» (the chapters follow right below there): the callers leave it out.
 */
export default function SectionChapters({
  lang,
  ui,
  ids,
  numbered,
  label,
  className = "",
}: {
  lang: string;
  ui: UiDict;
  /** The section's chapters, in the contents' order. */
  ids: string[];
  /** Chapter numbers before the titles (the parts' chapters have them, the Introduction's not). */
  numbered: boolean;
  /** The block's accessible name (defaults to the visible heading). */
  label?: string;
  className?: string;
}) {
  const rows = ids
    .map((id) => ({ id, s: getSection(lang, id), num: numbered ? getSectionNumber(id) : null }))
    .filter((r) => !!r.s);
  if (rows.length === 0) return null;
  const heading = t(ui, "group.inThisSection");
  return (
    <nav className={`section-chapters ${className}`.trim()} aria-label={label ?? heading} data-section-chapters="">
      <p className="section-chapters-title" aria-hidden={label ? undefined : true}>
        {heading}
      </p>
      <ul role="list" className="section-chapters-list">
        {rows.map(({ id, s, num }) => (
          <li key={id}>
            <Link href={localeHref(lang, id)} className="section-chapters-row" data-section-chapter={id}>
              <span className="section-chapters-name">
                {num && <span className="heading-num">{`${num}.`}</span>}
                {s!.title}
              </span>
              <svg
                aria-hidden="true"
                className="section-chapters-arrow"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="9 6 15 12 9 18" />
              </svg>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
