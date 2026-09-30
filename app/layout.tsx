import type { Metadata } from "next";
import { Noto_Serif } from "next/font/google";
import AppShell from "@/components/AppShell";
import { availableLanguages, getLocales, getUi } from "@/lib/content";
import { t } from "@/lib/i18n";
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
    icon: "/arcana-paddhati/favicon.ico",
    apple: "/arcana-paddhati/apple-touch-icon.png",
  },
  manifest: "/arcana-paddhati/manifest.json",
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
      className={`${notoSerif.variable} h-full`}
      suppressHydrationWarning
    >
      <body className="h-full antialiased">
        <AppShell locales={getLocales()} available={availableLanguages()}>
          {children}
        </AppShell>
      </body>
    </html>
  );
}
