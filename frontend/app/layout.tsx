import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Klondike Trainer",
  description: "Offline Klondike Solitaire trainer: set up a deal, solve it, and watch the solution play out.",
  manifest: "/manifest.json",
  icons: [{ rel: "icon", url: "/icon.svg", type: "image/svg+xml" }],
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#0a3a24",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
