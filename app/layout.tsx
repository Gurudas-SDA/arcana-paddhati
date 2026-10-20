import type { Metadata, Viewport } from "next";
import { Noto_Serif } from "next/font/google";
import localFont from "next/font/local";
import AppShell from "@/components/AppShell";
import { BASE_PATH } from "@/lib/basePath";
import { availableLanguages, getLocales, getUi } from "@/lib/content";
import { LANG_REDIRECT_SCRIPT, t } from "@/lib/i18n";
import { READER_PREFS_SCRIPT } from "@/lib/readerPrefsKeys";
import { EARLY_TAP_SCRIPT } from "@/lib/earlyTap";
import { HOME_CARDS_SCRIPT } from "@/lib/homeCards";
import { CA_LOADER_CSS, CA_LOADER_SVG, SPLASH_CSS, SPLASH_SCRIPT } from "@/lib/caSplash";
import { SPLASH_LINKS_SCRIPT } from "@/lib/splashImages";
import "./globals.css";

// 20.10.2026 (Vraja Lila msg 5316 p. 4, «Шрифты — разбор»): the upright Noto
// Serif in our own cut — only the characters the book and the interface use
// (scripts/font_subset.py), the same variable font (weights 100–900), so the
// text looks the same. 3 files, 67 KB preloaded instead of 248 KB (Google's
// latin-ext alone was 187 KB for ~70 IAST letters). No italic (as before:
// italic stays the browser's slant). Noto Serif from next/font stays behind
// them, not preloaded: a character outside our cut is still drawn by it.
// All text uses var(--font-book) (app/globals.css).
const arcanaSerifLatin = localFont({
  src: "./fonts/arcana-serif-latin.woff2",
  weight: "100 900",
  style: "normal",
  display: "swap",
  variable: "--font-arcana-latin",
  adjustFontFallback: false,
  declarations: [{ prop: "unicode-range", value: "U+20-7E,U+A0-FF,U+153,U+301,U+303-304,U+323,U+2002,U+2009,U+200B,U+2013-2014,U+2018-201A,U+201C-201E,U+2022,U+2026,U+2032-2033,U+2039-203A,U+2044,U+20AC,U+2122,U+2212" }],
});
const arcanaSerifExt = localFont({
  src: "./fonts/arcana-serif-latinext.woff2",
  weight: "100 900",
  style: "normal",
  display: "swap",
  variable: "--font-arcana-ext",
  adjustFontFallback: false,
  declarations: [{ prop: "unicode-range", value: "U+20,U+A0,U+100-101,U+104-105,U+10C-10D,U+112-113,U+117,U+119,U+123,U+129-12B,U+12E-12F,U+134-137,U+13B-13C,U+146,U+14D,U+150-151,U+15A-15B,U+15F-161,U+169-16B,U+171,U+173,U+175,U+17D-17E,U+219,U+21B,U+301,U+303-304,U+323,U+1D43,U+1E0C-1E0D,U+1E13,U+1E25,U+1E37,U+1E39,U+1E3B,U+1E41,U+1E43,U+1E45-1E47,U+1E5A-1E5B,U+1E5D,U+1E62-1E63,U+1E6C-1E6D,U+1E8F,U+2020" }],
});
const arcanaSerifCyr = localFont({
  src: "./fonts/arcana-serif-cyrillic.woff2",
  weight: "100 900",
  style: "normal",
  display: "swap",
  variable: "--font-arcana-cyr",
  adjustFontFallback: false,
  declarations: [{ prop: "unicode-range", value: "U+20,U+A0,U+301,U+400,U+404,U+406-407,U+410-429,U+42B,U+42D-44F,U+451,U+454,U+456-457,U+490-491,U+2116" }],
});

const notoSerif = Noto_Serif({
  variable: "--font-noto-serif",
  subsets: ["latin", "latin-ext", "cyrillic"],
  display: "swap",
  preload: false,
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
    // iOS uses the startup pictures only for a web app it treats as standalone
    // (the manifest already says "display": "standalone").
    "apple-mobile-web-app-capable": "yes",
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
      className={`${arcanaSerifLatin.variable} ${arcanaSerifExt.variable} ${arcanaSerifCyr.variable} ${notoSerif.variable} h-full`}
      suppressHydrationWarning
    >
      <head>
        {/* Retired language (Cyrillic-Sanskrit Russian) -> its replacement. */}
        <script dangerouslySetInnerHTML={{ __html: LANG_REDIRECT_SCRIPT }} />
        {/* Reader text size / background (lib/readerPrefs.ts) before first
            paint: a reload at night never flashes white. */}
        <script dangerouslySetInnerHTML={{ __html: READER_PREFS_SCRIPT }} />
        <script dangerouslySetInnerHTML={{ __html: EARLY_TAP_SCRIPT }} />
        {/* Cover cards (offline saving): their place reserved before first paint. */}
        <script dangerouslySetInnerHTML={{ __html: HOME_CARDS_SCRIPT }} />
        {/* Start screen (lib/caSplash.ts): Vraja Lila's CA loader + our white layer. */}
        <style dangerouslySetInnerHTML={{ __html: (CA_LOADER_CSS + SPLASH_CSS).replace(/\/\*[\s\S]*?\*\//g, "").replace(/\s+/g, " ") }} />
        {/* iOS home-screen app: the system's first picture = the start screen's first
            frame (lib/splashImages.ts, public/splash/). */}
        <script dangerouslySetInnerHTML={{ __html: SPLASH_LINKS_SCRIPT }} />
      </head>
      <body className="h-full antialiased" translate="no">
        {/* Start screen, before anything else is painted; leaves when the page is
            hydrated and drawn (AppShell), at the latest after 4 s. Never takes a tap. */}
        <div
          id="ap-splash"
          aria-hidden="true"
          suppressHydrationWarning
          dangerouslySetInnerHTML={{ __html: `<div class="ap-splash-sign">${CA_LOADER_SVG.replace(/\s+/g, " ")}</div>` }}
        />
        <script dangerouslySetInnerHTML={{ __html: SPLASH_SCRIPT }} />
        <AppShell locales={getLocales()} available={availableLanguages()}>
          {children}
        </AppShell>
      </body>
    </html>
  );
}
