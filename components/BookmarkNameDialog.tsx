"use client";

/**
 * The bookmark's name (V34, Satkirti msg 5866, Vraja Lila msg 5869, 21.10.2026):
 * «при добавлении закладки по центру экрана появляется модальное окно, на котором
 * по умолчанию как название стоит default название главы, но в том же окне её
 * можно переименовать и нажать подтвердить» — and the same window from the pencil
 * on a row of «Закладки».
 *
 * The look of the other windows: black 60 % dimming without blur (V18), a white
 * card in the middle, ✕ at the top right like the install window. «Подтвердить»
 * (also Enter) / «Отмена» (also ✕, Esc, a tap outside). No history step (the
 * bookmark only writes to the device, rule 10.2).
 *
 * V38 (Vraja Lila msg 1315–1317, 22.10.2026, iPhone 13): «клавиатура + полоса iOS
 * „AutoFill Contact“ перекрывают кнопки Cancel/Confirm» — the card stands in the
 * VISIBLE part of the screen (window.visualViewport: above the keyboard and its
 * bar), so «Отмена» / «Подтвердить» are always seen; the field does not look like
 * a contact's name to iOS (no «name» in its id/name, autocomplete off, a search-type
 * field, which Safari's contact AutoFill skips).
 */
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { t, type UiDict } from "@/lib/i18n";
import { BOOKMARK_NAME_MAX } from "@/lib/bookmarks";

/** V43: a zero-width joiner between the letters — the same text to read, no word for Safari's AutoFill match. */
const ZWJ = "\u200D";
function noAutofillText(s: string): string {
  return Array.from(s).join(ZWJ);
}

export default function BookmarkNameDialog({
  ui,
  mode,
  initial,
  onConfirm,
  onCancel,
}: {
  ui: UiDict;
  /** «add»: a new bookmark (the ribbon); «rename»: the pencil in «Закладки». */
  mode: "add" | "rename";
  /** The name in the field when the window opens. */
  initial: string;
  onConfirm: (name: string) => void;
  onCancel: () => void;
}) {
  const [value, setValue] = useState(initial);
  const cardRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const downOutside = useRef(false);
  const onCancelRef = useRef(onCancel);
  useEffect(() => {
    onCancelRef.current = onCancel;
  }, [onCancel]);

  // The name is ready to be typed over (all of it selected).
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.focus({ preventScroll: true });
    try {
      el.select();
    } catch {
      // some browsers refuse select() on a just-focused field
    }
  }, []);

  // Esc = «Отмена». Caught on window first, so the open «Содержание» / the top bar
  // (which close on Esc themselves) never see it.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      e.preventDefault();
      e.stopPropagation();
      onCancelRef.current();
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, []);

  // V38: the visible part of the screen (iOS: the keyboard and its AutoFill bar do
  // not shrink the layout viewport, only window.visualViewport).
  const [area, setArea] = useState<{ top: number; left: number; width: number; height: number } | null>(null);
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    let raf = 0;
    const update = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const full = vv.height >= window.innerHeight - 1 && vv.offsetTop <= 0 && vv.width >= window.innerWidth - 1;
        setArea(full ? null : { top: vv.offsetTop, left: vv.offsetLeft, width: vv.width, height: vv.height });
      });
    };
    update();
    vv.addEventListener("resize", update);
    vv.addEventListener("scroll", update);
    return () => {
      cancelAnimationFrame(raf);
      vv.removeEventListener("resize", update);
      vv.removeEventListener("scroll", update);
    };
  }, []);

  const confirm = () => onConfirm(value.trim());

  return createPortal(
    <div
      data-no-reader-tap=""
      data-bookmark-dialog={mode}
      className="bookmark-name-modal fixed inset-0 z-[100]"
      // A press that starts AND ends outside the card closes it, like the install window.
      onPointerDown={(e) => {
        downOutside.current = !cardRef.current?.contains(e.target as Node);
      }}
      onClick={(e) => {
        const outside = downOutside.current && !cardRef.current?.contains(e.target as Node);
        downOutside.current = false;
        if (outside) onCancel();
      }}
    >
      <div className="bookmark-name-backdrop absolute inset-0" aria-hidden="true" />
      <div
        data-bookmark-dialog-area=""
        className="absolute flex items-center justify-center p-4 overflow-y-auto overscroll-contain"
        style={area ? { top: area.top, left: area.left, width: area.width, height: area.height } : { inset: 0 }}
      >
      <div
        ref={cardRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="bookmark-name-title"
        className="relative bg-white rounded-xl shadow-2xl w-full max-w-[360px] p-5"
      >
        <button
          type="button"
          onClick={onCancel}
          className="absolute top-3 right-3 p-1 rounded-full hover:bg-[#F5E6C8] transition-colors text-[#5C3D2E]"
          aria-label={t(ui, "reader.close")}
          data-bookmark-dialog-close=""
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
        <h2
          id="bookmark-name-title"
          className="text-lg font-bold mb-4 text-[#2C1810] pr-6"
          style={{ fontFamily: "var(--font-book, Georgia, serif)" }}
        >
          {noAutofillText(t(ui, mode === "add" ? "bookmark.dialog.addTitle" : "bookmark.dialog.renameTitle"))}
        </h2>
        <form
          autoComplete="off"
          onSubmit={(e) => {
            e.preventDefault();
            confirm();
          }}
        >
          <label className="block text-sm text-[#5C3D2E] mb-1.5" htmlFor="bmsearch">
            {noAutofillText(t(ui, "bookmark.dialog.label"))}
          </label>
          <input
            ref={inputRef}
            id="bmsearch"
            name="search"
            type="search"
            inputMode="text"
            data-1p-ignore=""
            data-lpignore="true"
            data-form-type="other"
            value={value}
            maxLength={BOOKMARK_NAME_MAX}
            onChange={(e) => setValue(e.target.value)}
            enterKeyHint="done"
            autoComplete="off"
            data-bookmark-dialog-input=""
            className="bookmark-name-field ds-field w-full rounded-lg bg-white px-3 py-2.5 text-base text-[#2C1810]"
          />
          <div className="mt-5 flex justify-end gap-2">
            <button
              type="button"
              onClick={onCancel}
              data-bookmark-dialog-cancel=""
              className="min-h-[44px] rounded-lg px-4 text-sm font-medium text-[#5C3D2E] hover:bg-[#F5E6C8] transition-colors"
            >
              {t(ui, "bookmark.dialog.cancel")}
            </button>
            <button
              type="submit"
              data-bookmark-dialog-confirm=""
              className="min-h-[44px] rounded-lg px-5 text-sm font-semibold text-white bg-gradient-to-br from-[#D4A843] to-[#B8860B] shadow-sm"
            >
              {t(ui, "bookmark.dialog.confirm")}
            </button>
          </div>
        </form>
      </div>
      </div>
    </div>,
    document.body,
  );
}
