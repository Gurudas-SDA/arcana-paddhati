/** The route of the whole-book export of «Прокручивать» (A89, lib/readingMode.ts).
 *  A module without browser code: the static route pages import it too. */
import { localeHref } from "./i18n";

/** The route segment of the whole-book export (never a section id). */
export const BOOK_SEGMENT = "book";

export function bookHref(lang: string): string {
  return localeHref(lang, BOOK_SEGMENT);
}
