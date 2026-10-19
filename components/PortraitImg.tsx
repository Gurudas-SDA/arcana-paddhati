"use client";

/**
 * A parampara portrait: WebP via <picture>, the PNG when the WebP fails to load
 * (Reader v7.8.1, Codex review). <picture> picks its source by type support only —
 * a WebP that fails (broken / blocked / missing from the cache) would leave the
 * portrait empty. On that error the <source> is pointed at the PNG, so the
 * picture selects again and shows it. Also checked once on mount: the error may
 * have happened before hydration (static page), when no handler was listening.
 * v8.0: also the photo inside a code-masked portrait (components/MaskedPortrait.tsx).
 * 19.10.2026 (load speed, Vraja Lila msg 5076; «Скорость загрузки книги — разбор» p. 1): only the first
 * portrait is fetched at once (eager, fetchpriority high — it is the page's LCP); the others load lazily
 * as the reader nears them (loading="lazy", decoding="async"). width/height reserve the box before the
 * picture arrives (no layout shift; CSS keeps width/height auto, so the attributes only give the ratio).
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

type ImgProps = {
  webp?: string; png: string; alt: string; width?: number; height?: number; className?: string;
  /** the first portrait on the page: fetched at once with high priority; the others lazily */
  eager?: boolean;
};

export default function PortraitImg({ webp, png, alt, width, height, className = "portrait-img", eager = false }: ImgProps) {
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
        width={width}
        height={height}
        loading={eager ? "eager" : "lazy"}
        fetchPriority={eager ? "high" : undefined}
        decoding={eager ? undefined : "async"}
        className={className}
        draggable={false}
        onError={(e) => toPng(e.currentTarget)}
      />
    </picture>
  );
}
