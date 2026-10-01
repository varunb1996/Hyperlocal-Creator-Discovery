import type { Metadata, Viewport } from "next";
import { IBM_Plex_Sans } from "next/font/google";
import { Brand } from "@/components/brand";
import { NavLinks } from "@/components/nav-links";
import "./globals.css";

const plex = IBM_Plex_Sans({
  variable: "--font-plex",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Creator Discovery",
  description: "Ranked Pune creator shortlists for cafés and restaurants.",
};

export const viewport: Viewport = {
  themeColor: "#f6f7f9",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${plex.variable} h-full`}>
      <body className="min-h-full">
        <div className="border-b bg-card">
          <nav aria-label="Main" className="mx-auto flex h-16 w-full max-w-2xl items-center justify-between gap-3 px-4 xl:max-w-7xl xl:px-8">
            <Brand />
            <NavLinks />
          </nav>
        </div>
        {children}
      </body>
    </html>
  );
}
