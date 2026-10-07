"use client";

/**
 * A parampara portrait: WebP via <picture>, the PNG when the WebP fails to load
 * (Reader v7.8.1, Codex review). <picture> picks its source by type support only —
 * a WebP that fails (broken / blocked / missing from the cache) would leave the
 * portrait empty. On that error the <source> is pointed at the PNG, so the
 * picture selects again and shows it. Also checked once on mount: the error may
 * have happened before hydration (static page), when no handler was listening.
 */
import { useCallback } from "react";

function toPng(img: HTMLImageElement) {
  if (img.dataset.pngFallback) return;
  const src = img.currentSrc || img.src;
  if (!/\.webp(\?|$)/.test(src)) return;
  img.dataset.pngFallback = "1";
  const png = img.getAttribute("src") ?? "";
  img.parentElement?.querySelectorAll("source").forEach((s) => s.setAttribute("srcset", png));
  // re-run the selection (the source change alone does it in most engines)
  img.setAttribute("src", png);
}

export default function PortraitImg({ webp, png, alt }: { webp?: string; png: string; alt: string }) {
  const ref = useCallback((img: HTMLImageElement | null) => {
    if (img && img.complete && img.naturalWidth === 0) toPng(img);
  }, []);
  return (
    <picture className="portrait-picture">
      {webp && <source srcSet={webp} type="image/webp" />}
      <img
        ref={ref}
        src={png}
        alt={alt}
        className="portrait-img"
        draggable={false}
        onError={(e) => toPng(e.currentTarget)}
      />
    </picture>
  );
}
