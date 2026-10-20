"use client";

// The «Продолжить» card's behaviour (components/ResumeCard.tsx draws it before
// first paint): a tap opens the place with the app's router; in the language
// the place was taken in, also the exact block (lib/readingMode.ts keepPlace).
// After a move to the cover inside the app (no new page load, so the inline
// script did not run) the card is drawn here, before paint.
import { useLayoutEffect } from "react";
import { useRouter } from "next/navigation";
import { stripBasePath } from "@/lib/basePath";
import { keepPlace } from "@/lib/readingMode";
import { readReadingPlace } from "@/lib/readingPlace";

export default function ResumeCardLink({ script }: { script: string }) {
  const router = useRouter();
  useLayoutEffect(() => {
    const slot = document.getElementById("home-resume");
    if (!slot) return;
    if (!slot.firstChild && readReadingPlace()) {
      document.documentElement.setAttribute("data-home-resume", "");
      try {
        new Function(script)();
      } catch {
        // not drawn
      }
    }
    const onClick = (e: MouseEvent) => {
      const a = (e.target as Element | null)?.closest?.("a.home-resume") as HTMLAnchorElement | null;
      if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      e.stopPropagation();
      const place = readReadingPlace();
      if (a.hasAttribute("data-same-lang") && place && place.section === a.dataset.section) {
        keepPlace({ sectionId: place.section, index: place.block, delta: place.offset });
      }
      router.push(stripBasePath(new URL(a.href).pathname) + new URL(a.href).hash);
    };
    slot.addEventListener("click", onClick);
    // The line wraps, so the card's height follows the width (rotation, window
    // resize): keep the cover's reserved place equal to the drawn card.
    const ro =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(() => {
            const d = document.documentElement;
            if (!slot.firstChild || !d.hasAttribute("data-home-resume")) return;
            const h = `${Math.ceil(slot.getBoundingClientRect().height)}px`;
            if (d.style.getPropertyValue("--home-resume-h") !== h) d.style.setProperty("--home-resume-h", h);
          });
    ro?.observe(slot);
    return () => {
      slot.removeEventListener("click", onClick);
      ro?.disconnect();
    };
  }, [router, script]);
  return null;
}
