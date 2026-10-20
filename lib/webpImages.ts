import map from "./webp-images.json";

/* 19.10.2026 (Vraja Lila msg 5338 / 5334): the book pictures are served as WebP q58 with a content-hashed name
   (scripts/images_webp.py writes lib/webp-images.json); the original PNG / JPG stays the fallback and is what the
   PDF / EPUB use. Paths are relative to public/media/. */
const WEBP: Record<string, string> = map;

/** "common/tilak.png" -> "common/tilak-09a8f00d.webp" (undefined if the picture has no WebP). */
export function webpFor(rel: string | undefined): string | undefined {
  return rel ? WEBP[rel] : undefined;
}
