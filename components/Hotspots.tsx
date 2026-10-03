"use client";

// Numbered picture <-> numbered list sync. Tapping a list row highlights its
// object on the picture (the object drawn in strong black, the rest faded);
// tapping a number or object on the picture highlights the matching row and
// scrolls to it. Whenever
// the highlighted spot is off-screen, a small floating copy shows the
// highlight. The darkened object comes from its own pixel mask (exactly that
// object and its number); "inert" areas (the Deities) take no taps at all. A
// tap on any empty part of the page clears the highlight.
// Data: lib/hotspots.ts (data/hotspots.json). Print shows the plain image.

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import type { HotspotImage } from "@/lib/hotspots";

interface Active {
  img: string;
  nums: string[];
  source: "list" | "image";
  /** Increments on every selection (restarts the fade-in, re-scrolls). */
  seq: number;
}

interface Ctx {
  active: Active | null;
  select: (img: string, nums: string[], source: Active["source"]) => void;
  clear: () => void;
  /** True once per selection: the first matching row scrolls to itself. */
  claimScroll: (seq: number) => boolean;
  /** The figure registers its element (visibility check on selection). */
  registerFigure: (img: string, el: HTMLElement | null) => void;
}

const HotspotContext = createContext<Ctx | null>(null);

/** Taps on these never clear the highlight from the page-level listener. */
const IGNORE_TAP = [
  "a", "button", "input", "textarea", "select", "label", "summary",
  "[role=button]", "[role=dialog]", "[contenteditable]",
  "[data-hs-row]", ".hs-hit", ".hs-figure", ".hs-peek",
].join(",");

export function HotspotProvider({ children }: { children: React.ReactNode }) {
  const [active, setActive] = useState<Active | null>(null);
  const seq = useRef(0);
  const scrolledSeq = useRef(0);
  const figures = useRef(new Map<string, HTMLElement>());
  const select = useCallback((img: string, nums: string[], source: Active["source"]) => {
    setActive((prev) => {
      // Tapping the active row again switches the highlight off.
      if (prev && source === "list" && prev.img === img && prev.nums.join() === nums.join()) return null;
      seq.current += 1;
      return { img, nums, source, seq: seq.current };
    });
  }, []);
  const clear = useCallback(() => setActive(null), []);

  // While a highlight is on, a tap/click on any empty part of the page clears
  // it (on pointerup: browsers may swallow the click of the first tap after a
  // fling). Ignored: scroll gestures (>10 px between press and release, a
  // cancelled pointer, or a press that stops a still-moving page), text
  // selection, and taps on interactive elements, list rows, the picture and
  // the floating copy (they handle taps themselves).
  const isOn = active !== null;
  useEffect(() => {
    if (!isOn) return;
    let start: { x: number; y: number; sel: string; t: Element | null } | null = null;
    let lastScroll = 0;
    const selText = () => window.getSelection()?.toString().trim() ?? "";
    const ignored = (t: EventTarget | null) =>
      !(t instanceof Element) || !!t.closest(IGNORE_TAP);
    const onScroll = () => {
      lastScroll = performance.now();
      start = null;
    };
    const onDown = (e: PointerEvent) => {
      const ok = e.isPrimary && e.button === 0 && performance.now() - lastScroll > 150;
      start = ok ? { x: e.clientX, y: e.clientY, sel: selText(), t: e.target as Element } : null;
    };
    const onCancel = () => {
      start = null;
    };
    const onUp = (e: PointerEvent) => {
      const s = start;
      start = null;
      if (!s || !e.isPrimary || Math.hypot(e.clientX - s.x, e.clientY - s.y) > 10) return;
      // This gesture selected text (drag, long press): keep the highlight.
      const sel = selText();
      if (sel && sel !== s.sel) return;
      if (ignored(s.t) || ignored(e.target)) return;
      setActive(null);
    };
    document.addEventListener("pointerdown", onDown, true);
    document.addEventListener("pointercancel", onCancel, true);
    document.addEventListener("pointerup", onUp);
    window.addEventListener("scroll", onScroll, true);
    return () => {
      document.removeEventListener("pointerdown", onDown, true);
      document.removeEventListener("pointercancel", onCancel, true);
      document.removeEventListener("pointerup", onUp);
      window.removeEventListener("scroll", onScroll, true);
    };
  }, [isOn]);
  const claimScroll = useCallback((n: number) => {
    if (scrolledSeq.current === n) return false;
    scrolledSeq.current = n;
    return true;
  }, []);
  const registerFigure = useCallback((img: string, el: HTMLElement | null) => {
    if (el) figures.current.set(img, el);
    else figures.current.delete(img);
  }, []);
  const value = useMemo(
    () => ({ active, select, clear, claimScroll, registerFigure }),
    [active, select, clear, claimScroll, registerFigure],
  );
  return <HotspotContext.Provider value={value}>{children}</HotspotContext.Provider>;
}

/** URL of a per-object mask: next to the picture, in hotspots/. */
function maskUrl(src: string, file: string): string {
  return src.replace(/[^/]*$/, `hotspots/${file}`);
}

/** Fraction (0..1) of the element visible in the viewport (also below the sticky header). */
function visibleFraction(el: Element): number {
  const r = el.getBoundingClientRect();
  const top = Math.max(r.top, 56);
  const bottom = Math.min(r.bottom, window.innerHeight);
  const h = Math.max(0, bottom - top);
  return r.height > 0 ? h / Math.min(r.height, window.innerHeight - 56) : 0;
}

/** True if the picture's highlighted spot(s) lie inside the viewport (below the sticky header). */
function spotOnScreen(fig: HTMLElement, nums: string[]): boolean {
  const r = fig.getBoundingClientRect();
  const ys = nums.map((n) => Number(fig.dataset[`y${n}`] ?? 50));
  return ys.every((y) => {
    const py = r.top + (y / 100) * r.height;
    return py > 56 + 24 && py < window.innerHeight - 24;
  });
}

/** One row of a numbered list linked to a picture. Renders `as` (li/div) with the row's classes. */
export function HotspotRow({
  img,
  nums,
  as = "div",
  className = "",
  children,
}: {
  img: string;
  nums: string[];
  as?: "li" | "div";
  className?: string;
  children: React.ReactNode;
}) {
  const ctx = useContext(HotspotContext);
  const ref = useRef<HTMLElement>(null);
  const isActive =
    !!ctx?.active && ctx.active.img === img && ctx.active.nums.some((n) => nums.includes(n));
  const fromImage = isActive && ctx?.active?.source === "image";
  const seq = ctx?.active?.seq ?? 0;

  useEffect(() => {
    if (!fromImage || !ctx || !ref.current) return;
    if (!ctx.claimScroll(seq)) return;
    if (visibleFraction(ref.current) < 1) {
      ref.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [fromImage, seq, ctx]);

  if (!ctx || nums.length === 0) {
    const Tag = as;
    return <Tag className={className}>{children}</Tag>;
  }
  const Tag = as as "div";
  return (
    <Tag
      ref={ref as React.RefObject<HTMLDivElement>}
      role="button"
      tabIndex={0}
      aria-pressed={isActive}
      data-hs-row=""
      data-active={isActive ? "" : undefined}
      className={`hs-row ${className}`}
      onClick={() => ctx.select(img, nums, "list")}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          ctx.select(img, nums, "list");
        }
      }}
    >
      {children}
    </Tag>
  );
}

/** Image + SVG overlay (highlight and tap targets). */
function HotspotCanvas({
  src,
  alt,
  data,
  imgName,
  ctx,
  compact = false,
}: {
  src: string;
  alt: string;
  data: HotspotImage;
  imgName: string;
  ctx: Ctx;
  compact?: boolean;
}) {
  const { w, h, spots } = data;
  const rawId = useId();
  const maskId = `hsm-${rawId.replace(/[^a-zA-Z0-9]/g, "")}`;
  const gradId = `${maskId}-g`;
  const inkId = `${maskId}-i`;
  const active = ctx.active && ctx.active.img === imgName ? ctx.active : null;
  const px = (v: number, of: number) => (v / 100) * of;
  // Tap targets: big objects first so smaller ones lie on top.
  const order = Object.entries(spots).sort(([, a], [, b]) => b.rx * b.ry - a.rx * a.ry);
  const labelR = Math.max(w, h) * 0.03;
  const shown = active ? active.nums.filter((n) => spots[n]) : [];
  // Soft-edged window: fully opaque up to FEATHER_SOLID of its radius (= the
  // hotspot's own radius), fading out to nothing at the edge.
  const FEATHER = 1.3;
  const FEATHER_SOLID = 1 / FEATHER;

  return (
    <>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt}
        className={`hs-img block w-full h-auto${shown.length ? " hs-img-faded" : ""}`}
        draggable={false}
      />
      <svg
        className="hs-overlay no-print absolute inset-0 h-full w-full"
        viewBox={`0 0 ${w} ${h}`}
        preserveAspectRatio="none"
        onClick={(e) => {
          if (e.target === e.currentTarget && !compact) ctx.clear();
        }}
      >
        {shown.length > 0 && (
          <defs>
            <radialGradient id={gradId}>
              <stop offset={0} stopColor="#fff" stopOpacity={1} />
              <stop offset={FEATHER_SOLID} stopColor="#fff" stopOpacity={1} />
              <stop offset={1} stopColor="#fff" stopOpacity={0} />
            </radialGradient>
            <mask id={maskId} maskUnits="userSpaceOnUse" x={0} y={0} width={w} height={h}>
              {shown.map((n) => {
                const sp = spots[n];
                // Pixel mask: exactly this object and its number.
                if (sp.mask) {
                  return <image key={n} href={maskUrl(src, sp.mask)} width={w} height={h} />;
                }
                return (
                  <React.Fragment key={n}>
                    <ellipse
                      cx={px(sp.x, w)}
                      cy={px(sp.y, h)}
                      rx={px(sp.rx, w) * FEATHER}
                      ry={px(sp.ry, h) * FEATHER}
                      fill={`url(#${gradId})`}
                    />
                    {sp.lx !== undefined && sp.ly !== undefined && (
                      <circle cx={px(sp.lx, w)} cy={px(sp.ly, h)} r={labelR * 0.62} fill={`url(#${gradId})`} />
                    )}
                  </React.Fragment>
                );
              })}
            </mask>
            {/* "Ink": greys and colours pushed towards black, white stays white. */}
            <filter id={inkId} x={0} y={0} width="100%" height="100%" colorInterpolationFilters="sRGB">
              <feComponentTransfer>
                <feFuncR type="gamma" amplitude={1} exponent={3.2} offset={0} />
                <feFuncG type="gamma" amplitude={1} exponent={3.2} offset={0} />
                <feFuncB type="gamma" amplitude={1} exponent={3.2} offset={0} />
              </feComponentTransfer>
            </filter>
          </defs>
        )}

        {shown.length > 0 && (
          // The selected object(s): the same picture in strong black ink, seen
          // through a soft-edged window over the faded picture.
          <g key={active!.seq} pointerEvents="none" className="hs-lit">
            <image href={src} width={w} height={h} filter={`url(#${inkId})`} mask={`url(#${maskId})`} />
          </g>
        )}

        {/* Tap targets: the object and its printed number. */}
        {order.map(([n, s]) => (
          <g
            key={n}
            role="button"
            tabIndex={compact ? -1 : 0}
            aria-label={n}
            className="hs-hit"
            onClick={(e) => {
              e.stopPropagation();
              ctx.select(imgName, [n], "image");
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                ctx.select(imgName, [n], "image");
              }
            }}
          >
            <ellipse cx={px(s.x, w)} cy={px(s.y, h)} rx={px(s.rx, w)} ry={px(s.ry, h)} vectorEffect="non-scaling-stroke" />
            {s.lx !== undefined && s.ly !== undefined && (
              <circle cx={px(s.lx, w)} cy={px(s.ly, h)} r={labelR} vectorEffect="non-scaling-stroke" />
            )}
          </g>
        ))}

        {/* Not a tap target at all (the Deities): taps here do nothing. */}
        {data.inert?.map((poly, i) => (
          <polygon
            key={`inert-${i}`}
            className="hs-inert"
            points={poly.map(([x, y]) => `${px(x, w)},${px(y, h)}`).join(" ")}
            onClick={(e) => e.stopPropagation()}
          />
        ))}
      </svg>
    </>
  );
}

/** A numbered picture with hotspots (replaces the plain book image). */
export function HotspotFigure({
  src,
  imgName,
  alt,
  data,
  maxWidth = 420,
  closeLabel = "✕",
}: {
  src: string;
  imgName: string;
  alt: string;
  data: HotspotImage;
  maxWidth?: number;
  closeLabel?: string;
}) {
  const ctx = useContext(HotspotContext);
  const ref = useRef<HTMLDivElement | null>(null);
  // seq of the selection whose floating copy was closed with ✕.
  const [dismissed, setDismissed] = useState(0);
  // The highlighted spot is outside the viewport (checked on scroll/resize).
  const [offscreen, setOffscreen] = useState(false);
  const active = ctx?.active && ctx.active.img === imgName ? ctx.active : null;
  const activeSeq = active?.seq ?? 0;
  const activeNums = active?.nums.join(",") ?? "";
  // Whenever a highlight is on and the picture is off-screen, the floating
  // copy shows it, whether the tap came from the list or from the picture.
  const peek = !!active && offscreen && dismissed !== activeSeq;
  const registerFigure = ctx?.registerFigure;
  const setRef = useCallback(
    (el: HTMLDivElement | null) => {
      ref.current = el;
      registerFigure?.(imgName, el);
    },
    [registerFigure, imgName],
  );

  // Track whether the highlighted spot is on screen while a highlight is on.
  useEffect(() => {
    if (!activeNums) return;
    const nums = activeNums.split(",");
    let raf = 0;
    const check = () => {
      raf = 0;
      if (ref.current) setOffscreen(!spotOnScreen(ref.current, nums));
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(check);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onScroll);
    return () => {
      if (raf) cancelAnimationFrame(raf);
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onScroll);
    };
  }, [activeNums, activeSeq]);

  // Fetch the masks early so the first highlight appears at once.
  useEffect(() => {
    if (!ctx) return;
    for (const sp of Object.values(data.spots)) {
      if (sp.mask) new Image().src = maskUrl(src, sp.mask);
    }
  }, [ctx, data, src]);

  if (!ctx) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt={alt} className="book-image" style={{ maxWidth }} />;
  }
  const width = Math.min(maxWidth, data.w);

  return (
    <>
      <div
        ref={setRef}
        className="hs-figure relative mx-auto my-6"
        style={{ width: "100%", maxWidth: width }}
        {...Object.fromEntries(Object.entries(data.spots).map(([n, sp]) => [`data-y${n}`, sp.y]))}
      >
        <HotspotCanvas src={src} alt={alt} data={data} imgName={imgName} ctx={ctx} />
      </div>
      {peek &&
        createPortal(
          <div className="hs-peek no-print" role="dialog" aria-label={alt}>
            <button
              type="button"
              className="hs-peek-close"
              aria-label="Close"
              onClick={() => setDismissed(activeSeq)}
            >
              {closeLabel}
            </button>
            {/* Only the numbers/objects and the close button act; the
                background does nothing. */}
            <div className="relative">
              <HotspotCanvas src={src} alt="" data={data} imgName={imgName} ctx={ctx} compact />
            </div>
          </div>,
          document.body,
        )}
    </>
  );
}
