"use client";
import React, { useState, useEffect, useCallback } from "react";

type Platform = "ios" | "android" | "unknown";

function detectPlatform(): Platform {
  if (typeof navigator === "undefined") return "unknown";
  const ua = navigator.userAgent;
  if (
    /iPad|iPhone|iPod/.test(ua) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
  ) {
    return "ios";
  }
  if (/Android/.test(ua)) {
    return "android";
  }
  return "unknown";
}

export default function InstallBanner() {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [visible, setVisible] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [platform, setPlatform] = useState<Platform>("unknown");

  useEffect(() => {
    // Register service worker
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/arcana-paddhati/sw.js");
    }

    // Already installed — never show
    if (window.matchMedia("(display-mode: standalone)").matches) {
      return;
    }

    // Previously dismissed — don't show
    if (localStorage.getItem("installDismissed") === "true") {
      return;
    }

    setPlatform(detectPlatform());
    setVisible(true);

    // Listen for native install prompt (Chrome / Edge / Android Chrome)
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
    };
    window.addEventListener("beforeinstallprompt", handler);

    // Hide banner after successful install
    const installedHandler = () => {
      setVisible(false);
    };
    window.addEventListener("appinstalled", installedHandler);

    return () => {
      window.removeEventListener("beforeinstallprompt", handler);
      window.removeEventListener("appinstalled", installedHandler);
    };
  }, []);

  const handleInstall = useCallback(async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === "accepted") {
        setVisible(false);
      }
      setDeferredPrompt(null);
    } else {
      // No native prompt — show manual instructions modal
      setShowModal(true);
    }
  }, [deferredPrompt]);

  const handleDismiss = useCallback(() => {
    localStorage.setItem("installDismissed", "true");
    setVisible(false);
  }, []);

  if (!visible) return null;

  return (
    <>
      {/* Banner */}
      <div
        style={{
          background: "linear-gradient(90deg, #D4A843, #B8860B)",
        }}
        className="flex items-center justify-between gap-2 px-3 py-2.5 sm:px-4 sm:py-2.5 text-white text-sm"
      >
        <span
          className="truncate text-xs sm:text-sm leading-tight"
          style={{ fontFamily: "var(--font-noto-serif, Georgia, serif)" }}
        >
          Install Arcana Paddhati for quick access
        </span>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleInstall}
            className="px-3 py-1 rounded-full bg-white/20 hover:bg-white/30 active:bg-white/40 text-white text-xs sm:text-sm font-semibold transition-colors border border-white/40"
          >
            Install
          </button>
          <button
            onClick={handleDismiss}
            className="p-1 rounded-full hover:bg-white/20 transition-colors"
            aria-label="Dismiss install banner"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      </div>

      {/* Instructions modal (for iOS / non-Chrome browsers) */}
      {showModal && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          onClick={() => setShowModal(false)}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/30" />

          {/* Modal */}
          <div
            className="relative bg-white rounded-xl shadow-2xl w-full max-w-[360px] p-5"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close button */}
            <button
              onClick={() => setShowModal(false)}
              className="absolute top-3 right-3 p-1 rounded-full hover:bg-[#F5E6C8] transition-colors text-[#5C3D2E]"
              aria-label="Close"
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>

            <h2
              className="text-lg font-bold mb-4 text-[#2C1810] pr-6"
              style={{ fontFamily: "var(--font-noto-serif, Georgia, serif)" }}
            >
              Install Arcana Paddhati
            </h2>

            {platform === "ios" ? (
              <ol className="space-y-3 text-sm text-[#2C1810]">
                <li className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[#D4A843] to-[#B8860B] text-white flex items-center justify-center text-xs font-bold">
                    1
                  </span>
                  <span>
                    Tap the <strong>Share</strong> button{" "}
                    <span className="inline-block align-middle text-base">
                      &#x2934;&#xFE0E;
                    </span>
                  </span>
                </li>
                <li className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[#D4A843] to-[#B8860B] text-white flex items-center justify-center text-xs font-bold">
                    2
                  </span>
                  <span>
                    Scroll down and tap{" "}
                    <strong>&quot;Add to Home Screen&quot;</strong>
                  </span>
                </li>
                <li className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[#D4A843] to-[#B8860B] text-white flex items-center justify-center text-xs font-bold">
                    3
                  </span>
                  <span>
                    Tap <strong>&quot;Add&quot;</strong> in the top right
                  </span>
                </li>
              </ol>
            ) : (
              <ol className="space-y-3 text-sm text-[#2C1810]">
                <li className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[#D4A843] to-[#B8860B] text-white flex items-center justify-center text-xs font-bold">
                    1
                  </span>
                  <span>
                    Open in <strong>Chrome</strong> browser (tap{" "}
                    <strong>&#x22EE;</strong> &rarr;{" "}
                    <strong>&quot;Open in Browser&quot;</strong> if needed)
                  </span>
                </li>
                <li className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[#D4A843] to-[#B8860B] text-white flex items-center justify-center text-xs font-bold">
                    2
                  </span>
                  <span>
                    In Chrome, tap the <strong>&#x22EE;</strong> menu in the
                    top right
                  </span>
                </li>
                <li className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[#D4A843] to-[#B8860B] text-white flex items-center justify-center text-xs font-bold">
                    3
                  </span>
                  <span>
                    Tap <strong>&quot;Add to Home screen&quot;</strong>
                  </span>
                </li>
                <li className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[#D4A843] to-[#B8860B] text-white flex items-center justify-center text-xs font-bold">
                    4
                  </span>
                  <span>
                    Tap <strong>&quot;Add&quot;</strong>
                  </span>
                </li>
              </ol>
            )}
          </div>
        </div>
      )}
    </>
  );
}
