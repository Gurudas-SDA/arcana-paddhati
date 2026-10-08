import Image from "next/image";
import { getUi } from "@/lib/content";
import { t } from "@/lib/i18n";
import { BASE_PATH } from "@/lib/basePath";

/** Home page for one language (used by / and /<lang>/): only the book cover.
 *  Navigation (contents, language, install) is in the app shell. */
export default function HomePage({ lang }: { lang: string }) {
  const ui = getUi(lang);
  return (
    <div className="flex items-center justify-center min-h-full px-4 py-4 sm:px-6 lg:py-6">
      {/* The cover fills the content panel: as tall as the viewport allows
          (minus the mobile header, the install banner and small margins),
          width follows the aspect ratio and never exceeds the panel width.
          Never upscaled beyond the image's own 874x1240. */}
      <Image
        src={`${BASE_PATH}/cover.jpg`}
        alt={t(ui, "home.coverAlt")}
        width={874}
        height={1240}
        className="home-cover block w-auto h-auto max-w-full rounded-lg shadow-lg shadow-[#2C1810]/10"
        priority
      />
    </div>
  );
}
