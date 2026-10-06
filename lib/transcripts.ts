/**
 * Lecture transcripts bundled with the app (Satkirti, 06.10.2026: every
 * transcript the book refers to opens OFFLINE inside the app; audio stays
 * external). lib/transcripts.json maps a Google Drive file id to the static
 * page public/transcripts/<name>.html, written by
 * scripts/transcripts/build_transcripts.py and precached by the service worker.
 */
import pages from "./transcripts.json";

const PAGES = pages as Record<string, string>;
const ID_RE = /\/d\/([\w-]+)|[?&]id=([\w-]+)/;

/** The in-app page of a transcript link, or null if it is not bundled. */
export function transcriptPage(url: string | undefined): string | null {
  if (!url) return null;
  const m = ID_RE.exec(url);
  const id = m ? (m[1] ?? m[2]) : null;
  const name = id ? PAGES[id] : undefined;
  return name ? `/arcana-paddhati/transcripts/${name}.html` : null;
}

/** Link props for a «транскрипт» link: the in-app page (same window, works
 *  offline) or, if not bundled, the original in a new tab. */
export function transcriptLinkProps(url: string): { href: string; target?: string; rel?: string } {
  const page = transcriptPage(url);
  return page ? { href: page } : { href: url, target: "_blank", rel: "noopener noreferrer" };
}
