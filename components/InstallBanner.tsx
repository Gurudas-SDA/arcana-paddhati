"use client";
import { noteRegistration, startOfflineSync } from "@/lib/offlineProgress";
import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  useSyncExternalStore,
} from "react";
import { t, tNodes, type UiDict } from "@/lib/i18n";
import { BASE_PATH } from "@/lib/basePath";

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
  // Measured, not fixed: the text may wrap to two lines on narrow phones
  // (UI rule: no truncated labels).
  const bannerRef = useRef<HTMLDivElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);
  /** The current press started outside the instructions window (only such a press closes it). */
  const modalDownOutside = useRef(false);
  // Esc closes the instructions window (desktop), like its ✕.
  useEffect(() => {
    if (!showModal) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      e.preventDefault();
      setShowModal(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [showModal]);
  useEffect(() => {
    const root = document.documentElement;
    const el = bannerRef.current;
    if (!visible || !el) {
      root.style.removeProperty("--install-banner-h");
      return;
    }
    const update = () =>
      root.style.setProperty("--install-banner-h", `${el.offsetHeight}px`);
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => {
      ro.disconnect();
      root.style.removeProperty("--install-banner-h");
    };
  }, [visible]);

  useEffect(() => {
    // Register service worker
    if ("serviceWorker" in navigator) {
      // 20.10.2026 (Vraja Lila msg 5316 p. 2; Satkirti's iPad kept the old book):
      // updates arrive by themselves — sw.js is never taken from the HTTP cache
      // (updateViaCache "none"), the browser is asked to check for a new version
      // on every open and every return to the app, and when a new worker takes
      // over a page the old worker served, the page reloads ONCE to show the new book.
      const hadController = !!navigator.serviceWorker.controller;
      const reg = navigator.serviceWorker.register(`${BASE_PATH}/sw.js`, { updateViaCache: "none" });
      reg.catch(() => {});
      noteRegistration(reg);
      const check = () => {
        reg.then((r) => r?.update?.()).catch(() => {});
      };
      check();
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") check();
      });
      let reloaded = false;
      // КСВ 22.10.2026 (Satkirti msg 6133, iPad: «не вижу Заключение»): a page of
      // the old version (opened from the device, or the app brought back from the
      // background) learns of a new version as soon as the browser starts to
      // install it — and reloads ONCE at once: the old worker then takes the page
      // from the network (sw.js waits for it while a newer version installs).
      // Before, the reload came only when the new version had downloaded its
      // core: ~3 min at 200 KB/s, ~14 min at 40 KB/s (qa s92), longer while the
      // app sleeps in the background. Not more often than every 10 minutes.
      const UPD_KEY = "ap.swUpdateReloadAt";
      const readAt = () => {
        try { return Number(sessionStorage.getItem(UPD_KEY)) || 0; } catch { return 0; }
      };
      // this page came from such a reload: it is the new book already, so the
      // later controllerchange needs no second reload
      const freshAfterUpdate = (() => {
        const at = readAt();
        return at > 0 && Date.now() - at < 30 * 60 * 1000 && performance.timeOrigin >= at && navigator.onLine;
      })();
      reg.then((r) => {
        r?.addEventListener?.("updatefound", () => {
          if (!hadController || reloaded || !navigator.onLine) return;
          if (Date.now() - readAt() < 10 * 60 * 1000) return;
          try { sessionStorage.setItem(UPD_KEY, String(Date.now())); } catch { return; }
          reloaded = true;
          window.location.reload();
        });
      }).catch(() => {});
      navigator.serviceWorker.addEventListener("controllerchange", () => {
        if (!hadController || reloaded || freshAfterUpdate) return;
        reloaded = true;
        window.location.reload();
      });
      startOfflineSync();
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
        ref={bannerRef}
        data-no-reader-tap=""
        style={{
          background: "linear-gradient(90deg, var(--ap-band-1), var(--ap-band-2))",
        }}
        className="install-banner no-print flex items-center justify-between gap-2 px-3 py-2.5 sm:px-4 sm:py-2.5 text-white text-sm"
      >
        <span
          className="min-w-0 break-words text-xs sm:text-sm leading-tight"
          style={{ fontFamily: "var(--font-book, Georgia, serif)" }}
        >
          {t(ui, "install.bannerText")}
        </span>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleInstall}
            className="install-banner-btn px-3 py-1 rounded-full bg-white/20 hover:bg-white/30 active:bg-white/40 text-white text-xs sm:text-sm font-semibold transition-colors border border-white/40"
          >
            {t(ui, "install.button")}
          </button>
          <button
            onClick={handleDismiss}
            className="banner-close p-1 rounded-full hover:bg-white/20 transition-colors"
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
        <div
          data-no-reader-tap=""
          className="install-modal fixed inset-0 z-[100] flex items-center justify-center p-4"
          // A tap / click outside the window closes it like its ✕ (Vraja Lila msg 5391, 20.10.2026);
          // only a press that starts AND ends outside (a drag from inside never closes it).
          onPointerDown={(e) => {
            modalDownOutside.current = !modalRef.current?.contains(e.target as Node);
          }}
          onClick={(e) => {
            const outside = modalDownOutside.current && !modalRef.current?.contains(e.target as Node);
            modalDownOutside.current = false;
            if (outside) setShowModal(false);
          }}
        >
          <div className="install-backdrop absolute inset-0" aria-hidden="true" />

          {/* Modal */}
          <div
            ref={modalRef}
            role="dialog"
            aria-modal="true"
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
              style={{ fontFamily: "var(--font-book, Georgia, serif)" }}
            >
              {t(ui, "install.modalTitle")}
            </h2>

            {platform === "ios" ? (
              <ol className="space-y-3 text-sm text-[#2C1810]">
                <li className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[var(--ap-band-1)] to-[var(--ap-band-2)] text-white flex items-center justify-center text-xs font-bold">
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
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[var(--ap-band-1)] to-[var(--ap-band-2)] text-white flex items-center justify-center text-xs font-bold">
                    2
                  </span>
                  <span>
                    {tNodes(ui, "install.ios.step2", {
                      addToHome: <strong>{t(ui, "install.ios.addToHome")}</strong>,
                    })}
                  </span>
                </li>
                <li className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[var(--ap-band-1)] to-[var(--ap-band-2)] text-white flex items-center justify-center text-xs font-bold">
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
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[var(--ap-band-1)] to-[var(--ap-band-2)] text-white flex items-center justify-center text-xs font-bold">
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
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[var(--ap-band-1)] to-[var(--ap-band-2)] text-white flex items-center justify-center text-xs font-bold">
                    2
                  </span>
                  <span>
                    {tNodes(ui, "install.android.step2", {
                      menu: <strong>&#x22EE;</strong>,
                    })}
                  </span>
                </li>
                <li className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[var(--ap-band-1)] to-[var(--ap-band-2)] text-white flex items-center justify-center text-xs font-bold">
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
                  <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[var(--ap-band-1)] to-[var(--ap-band-2)] text-white flex items-center justify-center text-xs font-bold">
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
