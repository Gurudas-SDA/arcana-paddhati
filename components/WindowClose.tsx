import React from "react";

/**
 * V61 step 4 (Vraja Lila 30.10.2026, question 2 variant «А»): the ONE close button of every popup window.
 * Round, 44×44 tap area, centre 30 / 30 from the card's top-right corner, a 18 px cross with a 1.5 px line (--window-close-stroke), strictly 1:1 (never squeezed),
 * one colour from the token (--window-close-fg). The size / place live in the .window-close rule (app/globals.css) and the tokens
 * --window-close-* (design-system/tokens.css); the card is `position: relative` (.window-card or the window's own rule).
 */
export default function WindowClose({
  onClick,
  label,
  className = "",
  buttonRef,
  ...rest
}: {
  onClick: () => void;
  label: string;
  className?: string;
  buttonRef?: React.Ref<HTMLButtonElement>;
} & Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "onClick" | "className" | "aria-label">) {
  return (
    <button
      ref={buttonRef}
      type="button"
      onClick={onClick}
      aria-label={label}
      className={`window-close ${className}`.trim()}
      {...rest}
    >
      <svg aria-hidden="true" width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeLinecap="round">
        <line x1="1" y1="1" x2="17" y2="17" />
        <line x1="17" y1="1" x2="1" y2="17" />
      </svg>
    </button>
  );
}
