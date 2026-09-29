import type { Metadata } from "next";
import { Noto_Serif } from "next/font/google";
import AppShell from "@/components/AppShell";
import { getToc } from "@/lib/book";
import "./globals.css";

const notoSerif = Noto_Serif({
  variable: "--font-noto-serif",
  subsets: ["latin", "latin-ext"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Arcana Paddhati \u2014 Temple Manual",
  description:
    "The Process of Deity Worship \u2014 a comprehensive temple manual for arcana paddhati, the sacred process of deity worship in the Vaishnava tradition.",
  icons: {
    icon: "/arcana-paddhati/favicon.ico",
    apple: "/arcana-paddhati/apple-touch-icon.png",
  },
  manifest: "/arcana-paddhati/manifest.json",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${notoSerif.variable} h-full`}>
      <body className="h-full antialiased">
        <AppShell sections={getToc()}>{children}</AppShell>
      </body>
    </html>
  );
}
