import type { Metadata, Viewport } from "next";
import { Noto_Serif } from "next/font/google";
import AppShell from "@/components/AppShell";
import { BASE_PATH } from "@/lib/basePath";
import { availableLanguages, getLocales, getUi } from "@/lib/content";
import { LANG_REDIRECT_SCRIPT, t } from "@/lib/i18n";
import { READER_PREFS_SCRIPT } from "@/lib/readerPrefsKeys";
import "./globals.css";

const notoSerif = Noto_Serif({
  variable: "--font-noto-serif",
  subsets: ["latin", "latin-ext", "cyrillic"],
  display: "swap",
});

const ui = getUi("en");

export const metadata: Metadata = {
  title: t(ui, "meta.title"),
  description: t(ui, "meta.description"),
  icons: {
    icon: `${BASE_PATH}/favicon.ico`,
    apple: `${BASE_PATH}/apple-touch-icon.png`,
  },
  manifest: `${BASE_PATH}/manifest.json`,
  other: {
    google: "notranslate",
  },
};

// viewport-fit=cover: the reading area runs under the notch / home indicator;
// the safe areas are padded in CSS (env(safe-area-inset-*), app/globals.css).
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

// The root layout has no route params, so it always renders lang="en".
// Pages of other languages get the right value in the static HTML from
// scripts/patch-html-lang.mjs (postbuild) and on client-side navigation
// from AppShell; suppressHydrationWarning covers that difference.
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      translate="no"
      className={`${notoSerif.variable} h-full`}
      suppressHydrationWarning
    >
      <head>
        {/* Retired language (Cyrillic-Sanskrit Russian) -> its replacement. */}
        <script dangerouslySetInnerHTML={{ __html: LANG_REDIRECT_SCRIPT }} />
        {/* Reader text size / background (lib/readerPrefs.ts) before first
            paint: a reload at night never flashes white. */}
        <script dangerouslySetInnerHTML={{ __html: READER_PREFS_SCRIPT }} />
      </head>
      <body className="h-full antialiased" translate="no">
        <AppShell locales={getLocales()} available={availableLanguages()}>
          {children}
        </AppShell>
      </body>
    </html>
  );
}
