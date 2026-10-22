import type React from "react";

/**
 * Pill — the master toggle chip of the book (V40, Vraja Lila msg 6091–6094, 22.10.2026):
 * «при нажатии кнопка меняет свою ширину и размер… надо фиксированный размер и меняется только
 * интенсивность цвета и заливка… иконка стрелочки внутри дёргается неправильно при открытии»;
 * «относится ко всем подобным элементам — нужно сделать master element и использовать его».
 *
 * Fixed size in every state (same weight, frame and padding); open = stronger colour + fill;
 * the arrow turns smoothly around its centre (down → up) or stays (right: opens a window).
 * Styles: design-system/components.css (.ds-pill); tokens: design-system/tokens.css.
 * Used by: the verse chips «пословно» / «перевод» and the mantra «пословно» chip
 * (components/CollapsibleVerse.tsx), «Настроение Гурудева» (components/MoodBlock.tsx).
 */
export default function Pill({
  open,
  tone = "outline",
  size = "sm",
  chevron = "down",
  className = "",
  children,
  ref,
  ...rest
}: {
  /** Pressed / expanded: the only thing that changes is colour and fill. */
  open: boolean;
  /** outline: white with a thin frame (verse chips); soft: cream with a gold frame (mood). */
  tone?: "outline" | "soft";
  size?: "sm" | "md";
  /** down: expands below (turns up when open); right: opens a window (does not turn). */
  chevron?: "down" | "right";
  className?: string;
  children: React.ReactNode;
  ref?: React.Ref<HTMLButtonElement>;
} & Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "className" | "children">) {
  const px = size === "sm" ? 9 : 10;
  return (
    <button
      type="button"
      ref={ref}
      {...rest}
      data-ds-pill=""
      data-tone={tone}
      data-size={size}
      data-open={open ? "" : undefined}
      className={`ds-pill ${className}`.trim()}
    >
      <svg
        aria-hidden="true"
        width={px}
        height={px}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="ds-pill-chevron"
        data-dir={chevron}
      >
        <polyline points={chevron === "down" ? "6 9 12 15 18 9" : "9 6 15 12 9 18"} />
      </svg>
      {children}
    </button>
  );
}
