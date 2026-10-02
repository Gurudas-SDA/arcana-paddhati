import Image from "next/image";
import { getUi } from "@/lib/content";
import { t } from "@/lib/i18n";

/** Home page for one language (used by / and /<lang>/): only the book cover.
 *  Navigation (contents, language, install) is in the app shell. */
export default function HomePage({ lang }: { lang: string }) {
  const ui = getUi(lang);
  return (
    <div className="flex items-center justify-center min-h-full px-6 py-10">
      <div className="mx-auto w-64 sm:w-80 rounded-lg overflow-hidden shadow-lg shadow-[#2C1810]/10">
        <Image
          src="/arcana-paddhati/cover.jpg"
          alt={t(ui, "home.coverAlt")}
          width={874}
          height={1240}
          className="w-full h-auto"
          priority
        />
      </div>
    </div>
  );
}
