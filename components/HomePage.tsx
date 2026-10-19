import { preload } from "react-dom";
import { getUi, uiWithFallback } from "@/lib/content";
import OfflineSaveCard, { type OfflineSaveLabels } from "@/components/OfflineSaveCard";
import { t } from "@/lib/i18n";
import { BASE_PATH } from "@/lib/basePath";
import { webpFor } from "@/lib/webpImages";

/* 19.10.2026 (load speed, Vraja Lila msg 5076; «Скорость загрузки книги — разбор» p. 1): the cover is the
   page's LCP. It is fetched first (preload + fetchpriority high), as WebP in the size the screen needs
   (440 / 874 px wide, never upscaled beyond the original 874×1240), the JPG for a browser without WebP.
   Files: public/media/cover/ (media layout, Vraja Lila msg 5075). */
const COVER = `${BASE_PATH}/media/cover`;
// 19.10.2026 (Vraja Lila msg 5338 / 5334): WebP q58 with content-hashed names (scripts/images_webp.py).
const COVER_WEBP = `${BASE_PATH}/media/${webpFor("cover/cover.webp")}`;
const SRCSET = `${BASE_PATH}/media/${webpFor("cover/cover-440.webp")} 440w, ${COVER_WEBP} 874w`;
// Shown width: the panel width, at most the screen height minus margins × the cover's aspect (874/1240).
const SIZES = "min(100vw, calc((100vh - 2rem) * 0.705))";

const SAVE_KEYS = [
  "offline.save.loading", "offline.save.loadingNote", "offline.save.paused", "offline.save.pausedNote",
  "offline.save.done", "offline.save.doneNote", "offline.save.hide", "offline.save.count",
  "offline.save.partial", "offline.save.partialWhat", "offline.save.textOk", "offline.save.textMissing",
  "offline.save.retry", "offline.kind.text", "offline.kind.images", "offline.kind.transcripts", "offline.kind.other",
];

function saveLabels(lang: string): OfflineSaveLabels {
  const { strings: s, fallback } = uiWithFallback(lang, SAVE_KEYS);
  const sfx = fallback ? ` ${getUi(lang)["language.fallbackSuffix"] ?? "(EN)"}` : "";
  return {
    loading: s["offline.save.loading"] + sfx,
    loadingNote: s["offline.save.loadingNote"],
    paused: s["offline.save.paused"] + sfx,
    pausedNote: s["offline.save.pausedNote"],
    done: s["offline.save.done"] + sfx,
    doneNote: s["offline.save.doneNote"],
    hide: s["offline.save.hide"],
    count: s["offline.save.count"],
    partial: s["offline.save.partial"] + sfx,
    partialWhat: s["offline.save.partialWhat"],
    textOk: s["offline.save.textOk"],
    textMissing: s["offline.save.textMissing"],
    retry: s["offline.save.retry"],
    kinds: {
      text: s["offline.kind.text"],
      images: s["offline.kind.images"],
      transcripts: s["offline.kind.transcripts"],
      other: s["offline.kind.other"],
    },
  };
}

/** Home page for one language (used by / and /<lang>/): only the book cover.
 *  Navigation (contents, language, install) is in the app shell. */
export default function HomePage({ lang }: { lang: string }) {
  const ui = getUi(lang);
  preload(COVER_WEBP, { as: "image", type: "image/webp", imageSrcSet: SRCSET, imageSizes: SIZES, fetchPriority: "high" });
  return (
    <div className="home-page flex flex-col items-center justify-center min-h-full px-4 py-4 sm:px-6 lg:py-6">
      {/* The cover fills the content panel: as tall as the viewport allows
          (minus the mobile header, the install banner and small margins),
          width follows the aspect ratio and never exceeds the panel width.
          Never upscaled beyond the image's own 874x1240. */}
      <picture>
        <source type="image/webp" srcSet={SRCSET} sizes={SIZES} />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`${COVER}/cover.jpg`}
          alt={t(ui, "home.coverAlt")}
          width={874}
          height={1240}
          fetchPriority="high"
          loading="eager"
          decoding="async"
          className="home-cover block w-auto h-auto max-w-full rounded-lg shadow-lg shadow-[#2C1810]/10"
          style={{ color: "transparent", maxWidth: "min(100%, 874px)" /* srcset w-descriptors set the natural size from `sizes`; never above the original 874 px */ }}
        />
      </picture>
      {/* Saving for offline (Vraja Lila msg 5318): place reserved before first paint (lib/homeCards.ts). */}
      <OfflineSaveCard labels={saveLabels(lang)} />
    </div>
  );
}
