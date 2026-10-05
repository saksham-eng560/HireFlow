import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { MotionProvider } from "@/components/motion-provider";
import { ThemeProvider } from "@/components/theme-provider";
import { ToastProvider } from "@/components/ui/toast";
import { TooltipProvider } from "@/components/ui/tooltip";
import { OPEN_GRAPH, SITE_DESCRIPTION, SITE_TITLE, SITE_URL } from "@/lib/site";
import { cn } from "@/lib/utils";
import "./globals.css";

const sans = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: "HireFlow", template: "%s · HireFlow" },
  description: SITE_DESCRIPTION,
  applicationName: "HireFlow",
  keywords: ["internships", "job applications", "resume tailoring", "AI agent", "applicant tracking", "open source"],
  openGraph: OPEN_GRAPH,
  twitter: { card: "summary_large_image", title: SITE_TITLE, description: SITE_DESCRIPTION },
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }, { url: "/favicon.ico", sizes: "any" }],
    apple: "/apple-touch-icon.png",
  },
};

export const viewport: Viewport = {
  themeColor: [
    // Literal colours are required here (the <meta name="theme-color"> tag); they match --background.
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#090e1a" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={cn(sans.variable, mono.variable)}>
      <body className="font-sans">
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false} storageKey="theme" disableTransitionOnChange>
          <TooltipProvider delayDuration={200}>
            <ToastProvider><MotionProvider>{children}</MotionProvider></ToastProvider>
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
