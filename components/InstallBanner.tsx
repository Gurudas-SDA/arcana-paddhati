"use client";
import React, {
  useState,
  useEffect,
  useCallback,
  useSyncExternalStore,
} from "react";
import { t, tNodes, type UiDict } from "@/lib/i18n";

type Platform = "ios" | "android" | "unknown";

/** Chrome/Edge `beforeinstallprompt` event (not in the TS DOM lib). */
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

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

/** Whether the banner may be shown at all (client only; false on the server). */
function isEligible(): boolean {
  // Already installed — never show
  if (window.matchMedia("(display-mode: standalone)").matches) return false;
  // Previously dismissed — don't show
  try {
    if (localStorage.getItem("installDismissed") === "true") return false;
  } catch {
    // storage unavailable — treat as not dismissed
  }
  return true;
}

const noopSubscribe = () => () => {};

export default function InstallBanner({ ui }: { ui: UiDict }) {
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [hidden, setHidden] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const eligible = useSyncExternalStore(noopSubscribe, isEligible, () => false);
  const platform = useSyncExternalStore<Platform>(
    noopSubscribe,
    detectPlatform,
    () => "unknown"
  );
  const visible = eligible && !hidden;

  // Let full-height layouts (the home-page cover) reserve the banner's height.
  useEffect(() => {
    const root = document.documentElement;
    if (visible) root.style.setProperty("--install-banner-h", "2.75rem");
    else root.style.removeProperty("--install-banner-h");
    return () => {
      root.style.removeProperty("--install-banner-h");
    };
  }, [visible]);

  useEffect(() => {
    // Register service worker
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/arcana-paddhati/sw.js");
    }

    // Listen for native install prompt (Chrome / Edge / Android Chrome)
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", handler);

    // Hide banner after successful install
    const installedHandler = () => {
      setHidden(true);
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
        setHidden(true);
      }
      setDeferredPrompt(null);
    } else {
      // No native prompt — show manual instructions modal
      setShowModal(true);
    }
  }, [deferredPrompt]);

  const handleDismiss = useCallback(() => {
    try {
      localStorage.setItem("installDismissed", "true");
    } catch {
      // ignore
    }
    setHidden(true);
  }, []);

  if (!visible) return null;

  return (
    <>
      {/* Banner */}
      <div
        style={{
          background: "linear-gradient(90deg, #D4A843, #B8860B)",
        }}
        className="no-print flex items-center justify-between gap-2 px-3 py-2.5 sm:px-4 sm:py-2.5 text-white text-sm"
      >
        <span
          className="truncate text-xs sm:text-sm leading-tight"
          style={{ fontFamily: "var(--font-noto-serif, Georgia, serif)" }}
        >
          {t(ui, "install.bannerText")}
        </span>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleInstall}
            className="px-3 py-1 rounded-full bg-white/20 hover:bg-white/30 active:bg-white/40 text-white text-xs sm:text-sm font-semibold transition-colors border border-white/40"
          >
            {t(ui, "install.button")}
          </button>
          <button
            onClick={handleDismiss}
            className="p-1 rounded-full hover:bg-white/20 transition-colors"
            aria-label={t(ui, "install.dismiss")}
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
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          {/* Backdrop: does nothing; the modal closes only with its ✕ */}
          <div className="absolute inset-0 bg-black/30" />

          {/* Modal */}
          <div
            className="relative bg-white rounded-xl shadow-2xl w-full max-w-[360px] p-5"
          >
            {/* Close button */}
            <button
              onClick={() => setShowModal(false)}
              className="absolute top-3 right-3 p-1 rounded-full hover:bg-[#F5E6C8] transition-colors text-[#5C3D2E]"
              aria-label={t(ui, "install.close")}
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
              {t(ui, "install.modalTitle")}
            </h2>

            {platform === "ios" ? (
              <ol className="space-y-3 text-sm text-[#2C1810]">
                <li className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[#D4A843] to-[#B8860B] text-white flex items-center justify-center text-xs font-bold">
                    1
                  </span>
                  <span>
                    {tNodes(ui, "install.ios.step1", {
                      share: <strong>{t(ui, "install.ios.share")}</strong>,
                      icon: (
                        <span className="inline-block align-middle text-base">
                          &#x2934;&#xFE0E;
                        </span>
                      ),
                    })}
                  </span>
                </li>
                <li className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[#D4A843] to-[#B8860B] text-white flex items-center justify-center text-xs font-bold">
                    2
                  </span>
                  <span>
                    {tNodes(ui, "install.ios.step2", {
                      addToHome: <strong>{t(ui, "install.ios.addToHome")}</strong>,
                    })}
                  </span>
                </li>
                <li className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[#D4A843] to-[#B8860B] text-white flex items-center justify-center text-xs font-bold">
                    3
                  </span>
                  <span>
                    {tNodes(ui, "install.ios.step3", {
                      add: <strong>{t(ui, "install.add")}</strong>,
                    })}
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
                    {tNodes(ui, "install.android.step1", {
                      chrome: <strong>{t(ui, "install.android.chrome")}</strong>,
                      menu: <strong>&#x22EE;</strong>,
                      openInBrowser: (
                        <strong>{t(ui, "install.android.openInBrowser")}</strong>
                      ),
                    })}
                  </span>
                </li>
                <li className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[#D4A843] to-[#B8860B] text-white flex items-center justify-center text-xs font-bold">
                    2
                  </span>
                  <span>
                    {tNodes(ui, "install.android.step2", {
                      menu: <strong>&#x22EE;</strong>,
                    })}
                  </span>
                </li>
                <li className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[#D4A843] to-[#B8860B] text-white flex items-center justify-center text-xs font-bold">
                    3
                  </span>
                  <span>
                    {tNodes(ui, "install.android.step3", {
                      addToHome: (
                        <strong>{t(ui, "install.android.addToHome")}</strong>
                      ),
                    })}
                  </span>
                </li>
                <li className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[#D4A843] to-[#B8860B] text-white flex items-center justify-center text-xs font-bold">
                    4
                  </span>
                  <span>
                    {tNodes(ui, "install.android.step4", {
                      add: <strong>{t(ui, "install.add")}</strong>,
                    })}
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
