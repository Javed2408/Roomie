import type { Metadata, Viewport } from "next";
import { Outfit, Work_Sans } from "next/font/google";
import "./globals.css";

// Headings use Outfit (geometric, friendly); body text uses Work Sans
// (highly readable at small sizes). next/font downloads them at build time
// and serves them from our own site, so there is no layout shift.
const headingFont = Outfit({
  variable: "--font-heading",
  subsets: ["latin"],
  display: "swap",
});

const bodyFont = Work_Sans({
  variable: "--font-body",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Roomie — find compatible roommates near campus",
    template: "%s · Roomie",
  },
  description:
    "Find compatible roommates and shared accommodation near your campus.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // The colour of the browser's own bar on phones, for each appearance.
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#faf9f6" },
    { media: "(prefers-color-scheme: dark)", color: "#141312" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      // Tells Next.js that smooth scrolling (set in globals.css) is on
      // purpose, so it can switch it off briefly while changing pages.
      data-scroll-behavior="smooth"
      className={`${headingFont.variable} ${bodyFont.variable} h-full antialiased`}
    >
      <body className="bg-background text-foreground flex min-h-full flex-col font-sans">
        {children}
      </body>
    </html>
  );
}
