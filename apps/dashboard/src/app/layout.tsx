import type { Metadata } from "next";
import { Manrope, Space_Grotesk } from "next/font/google";

import { Providers } from "@/components/providers";
import "@/app/globals.css";

const fontBody = Manrope({
  subsets: ["latin"],
  variable: "--font-body"
});

const fontDisplay = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display"
});

export const metadata: Metadata = {
  title: "EcoLoop AI",
  description:
    "AI-powered building energy optimization platform built on EnergyPlus, LangGraph, MCP, and Qwen3."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${fontBody.variable} ${fontDisplay.variable}`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
