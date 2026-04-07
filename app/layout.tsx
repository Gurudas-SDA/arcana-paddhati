import type { Metadata } from "next";
import { Noto_Serif } from "next/font/google";
import { Geist } from "next/font/google";
import "./globals.css";

const notoSerif = Noto_Serif({
  variable: "--font-noto-serif",
  subsets: ["latin", "latin-ext"],
  display: "swap",
});

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Arcana Paddhati \u2014 Temple Manual",
  description:
    "The Process of Deity Worship \u2014 a comprehensive temple manual for arcana paddhati, the sacred process of deity worship in the Vaishnava tradition.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${notoSerif.variable} ${geistSans.variable} h-full`}
    >
      <body className="h-full antialiased">{children}</body>
    </html>
  );
}
