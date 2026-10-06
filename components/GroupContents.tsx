import Link from "next/link";
import { getFrontGroup, getSection } from "@/lib/content";
import { localeHref, t, type UiDict } from "@/lib/i18n";

/**
 * The Introduction's page: after its own text, the list of its chapters
 * (Emblem, Vigraha-tattva, Maṅgalācaraṇa — no chapter numbers), like a part's
 * page lists its chapters (Satkirti, 06.10.2026: the Introduction is an
 * expandable group of the contents). Nothing on any other page.
 */
export default function GroupContents({ lang, id, ui }: { lang: string; id: string; ui: UiDict }) {
  const group = getFrontGroup();
  if (!group || group.head !== id) return null;
  return (
    <nav className="group-contents mt-8" aria-label={t(ui, "group.contents")}>
      <ul role="list" className="space-y-2 text-[15px] leading-7">
        {group.members.map((m) => {
          const s = getSection(lang, m);
          if (!s) return null;
          return (
            <li key={m}>
              <Link href={localeHref(lang, m)} className="text-[#1a1a1a] hover:text-[#B8860B] transition-colors">
                {s.title}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
