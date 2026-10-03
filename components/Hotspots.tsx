"use client";

// Numbered picture <-> numbered list sync. Tapping a list row highlights its
// object on the picture (glowing gold ring, rest dimmed); tapping a number or
// object on the picture highlights the matching row and scrolls to it. When
// the picture is off-screen, a small floating copy shows the highlight.
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
  /** Increments on every selection (restarts the pulse, re-scrolls). */
  seq: number;
  /** Row tapped while the picture was off-screen: show the floating copy. */
  peek: boolean;
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

export function HotspotProvider({ children }: { children: React.ReactNode }) {
  const [active, setActive] = useState<Active | null>(null);
  const seq = useRef(0);
  const scrolledSeq = useRef(0);
  const figures = useRef(new Map<string, HTMLElement>());
  const select = useCallback((img: string, nums: string[], source: Active["source"]) => {
    const fig = figures.current.get(img);
    const peek = source === "list" && !!fig && !spotOnScreen(fig, nums);
    setActive((prev) => {
      // Tapping the active row again switches the highlight off.
      if (prev && source === "list" && prev.img === img && prev.nums.join() === nums.join()) return null;
      seq.current += 1;
      return { img, nums, source, seq: seq.current, peek };
    });
  }, []);
  const clear = useCallback(() => setActive(null), []);
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
  const glowId = `${maskId}-g`;
  const active = ctx.active && ctx.active.img === imgName ? ctx.active : null;
  const px = (v: number, of: number) => (v / 100) * of;
  // Tap targets: big objects first so smaller ones lie on top.
  const order = Object.entries(spots).sort(([, a], [, b]) => b.rx * b.ry - a.rx * a.ry);
  const labelR = Math.max(w, h) * 0.03;
  const shown = active ? active.nums.filter((n) => spots[n]) : [];
  const grow = 1.2;

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
        <defs>
          <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation={Math.max(w, h) * 0.008} />
          </filter>
          {shown.length > 0 && (
            <clipPath id={maskId}>
              {shown.map((n) => {
                const sp = spots[n];
                return (
                  <React.Fragment key={n}>
                    <ellipse cx={px(sp.x, w)} cy={px(sp.y, h)} rx={px(sp.rx, w) * grow} ry={px(sp.ry, h) * grow} />
                    {sp.lx !== undefined && sp.ly !== undefined && (
                      <circle cx={px(sp.lx, w)} cy={px(sp.ly, h)} r={labelR * 1.1} />
                    )}
                  </React.Fragment>
                );
              })}
            </clipPath>
          )}
        </defs>

        {shown.length > 0 && (
          <g key={active!.seq} pointerEvents="none">
            {/* The highlighted object(s) at full strength over the faded picture. */}
            <image href={src} width={w} height={h} clipPath={`url(#${maskId})`} className="hs-lit" />
            {shown.map((n) => {
              const sp = spots[n];
              const cx = px(sp.x, w), cy = px(sp.y, h), rx = px(sp.rx, w) * grow, ry = px(sp.ry, h) * grow;
              return (
                <g key={n}>
                  <ellipse cx={cx} cy={cy} rx={rx} ry={ry} className="hs-halo" strokeWidth={Math.max(w, h) * 0.016} filter={`url(#${glowId})`} />
                  <ellipse cx={cx} cy={cy} rx={rx} ry={ry} className="hs-ring" vectorEffect="non-scaling-stroke" />
                  <ellipse cx={cx} cy={cy} rx={rx} ry={ry} className="hs-pulse" vectorEffect="non-scaling-stroke" />
                </g>
              );
            })}
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
  // seq of the selection whose floating copy was closed (✕ or picture in view).
  const [dismissed, setDismissed] = useState(0);
  const active = ctx?.active && ctx.active.img === imgName ? ctx.active : null;
  const peek = !!active && active.peek && dismissed !== active.seq;
  const activeSeq = active?.seq ?? 0;
  const registerFigure = ctx?.registerFigure;
  const setRef = useCallback(
    (el: HTMLDivElement | null) => {
      ref.current = el;
      registerFigure?.(imgName, el);
    },
    [registerFigure, imgName],
  );

  // Hide the floating copy once the picture itself scrolls into view.
  useEffect(() => {
    if (!peek) return;
    const onScroll = () => {
      if (ref.current && visibleFraction(ref.current) >= 0.6) setDismissed(activeSeq);
    };
    window.addEventListener("scroll", onScroll, true);
    return () => window.removeEventListener("scroll", onScroll, true);
  }, [peek, activeSeq]);

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
            <div
              className="relative"
              onClick={(e) => {
                // Tap on the picture background: go to the picture itself.
                if ((e.target as Element).tagName === "svg") {
                  setDismissed(activeSeq);
                  ref.current?.scrollIntoView({ behavior: "smooth", block: "center" });
                }
              }}
            >
              <HotspotCanvas src={src} alt="" data={data} imgName={imgName} ctx={ctx} compact />
            </div>
          </div>,
          document.body,
        )}
    </>
  );
}
