import type { Metadata } from "next";

import "./globals.css";
import { ActionBar, SiteFooter, SiteNav } from "@/components/layout/SiteNav";

export const metadata: Metadata = {
  title: "Investment Intelligence: AI research for Indian stocks",
  description:
    "News-driven sentiment, live prices, opportunity scans and goal-based portfolios for NSE and BSE stocks.",
  openGraph: {
    title: "Investment Intelligence: AI research for Indian stocks",
    description:
      "News-driven sentiment, live prices, opportunity scans and goal-based portfolios for NSE and BSE stocks.",
    type: "website",
    images: [{ url: "/social-preview.png", width: 1200, height: 630 }],
  },
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-type="software" data-radius="sharp">
      <head>
        <meta name="page-type" content="software" />
        <meta name="site-kind" content="software" />
        {/* No scripts in <head>: the moments loader touches the DOM (it moves
            figures and marks <html>), which must happen after React hydration,
            or hydration fails and the marks are lost. The home page imports it
            in a useEffect instead. */}
      </head>
      <body>
        <SiteNav />
        <main id="main" className="pt-[var(--nav)]">{children}</main>
        <SiteFooter />
        <ActionBar />
      </body>
    </html>
  );
}
