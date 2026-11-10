"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils/cn";

const NAV = [
  { href: "/", label: "Home" },
  { href: "/analyze", label: "Analyse" },
  { href: "/discover", label: "Discover" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/chat", label: "Research chat" },
  { href: "/settings", label: "Settings" },
];

export function SiteNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  return (
    <header className="nav fixed inset-x-0 top-0 z-40 border-b border-ink/10 bg-paper/95 backdrop-blur">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-accent focus:px-4 focus:py-2 focus:text-white">
        Skip to content
      </a>
      <div className="wrap flex h-[var(--nav)] items-center justify-between gap-6">
        <Link href="/" className="flex items-center gap-2.5" aria-label="AI Investment Intelligence Platform — home">
          <span aria-hidden className="flex h-8 w-8 items-center justify-center bg-accent font-mono text-sm font-medium text-white">
            AI
          </span>
          <span className="font-display text-[17px] font-medium tracking-tight">
            Investment Intelligence
          </span>
        </Link>
        {/* Desktop nav from lg: at 820px the six links plus the brand do not fit one row. */}
        <nav aria-label="Primary" className="hidden items-center gap-1 lg:flex">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              aria-current={pathname === item.href ? "page" : undefined}
              className={cn(
                "link-underline rounded-sm px-3 py-2 text-sm",
                pathname === item.href ? "font-medium text-accent" : "text-muted hover:text-ink",
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <button
          type="button"
          className="inline-flex h-11 min-w-11 items-center justify-center rounded-sm border border-ink/15 px-3 text-sm font-medium lg:hidden"
          aria-expanded={open}
          aria-controls="mobile-nav"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? "Close" : "Menu"}
        </button>
      </div>
      {open && (
        <nav id="mobile-nav" aria-label="Primary mobile" className="absolute inset-x-0 top-full border-b border-ink/10 bg-paper lg:hidden">
          <ul className="wrap py-2">
            {NAV.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={pathname === item.href ? "page" : undefined}
                  onClick={() => setOpen(false)}
                  className={cn(
                    "flex min-h-11 items-center text-[15px]",
                    pathname === item.href ? "font-medium text-accent" : "text-muted",
                  )}
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </header>
  );
}

function FooterColumns() {
  return (
    <div className="grid gap-6 sm:grid-cols-3">
      <div>
        <p className="font-display text-lg font-medium">Investment Intelligence</p>
        <p className="mt-2 hidden max-w-xs text-sm leading-relaxed text-inv-muted sm:block">
          AI research for Indian equities: news sentiment, live prices,
          opportunities and goal-based portfolios.
        </p>
      </div>
      <nav aria-label="Footer">
        <p className="font-mono text-xs uppercase tracking-widest text-inv-muted">Product</p>
        <ul className="mt-3 space-y-2 text-sm">
          {NAV.slice(1, 5).map((item) => (
            <li key={item.href}>
              <Link href={item.href} className="inline-flex min-h-11 items-center link-underline">
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <div className="hidden sm:block">
        <p className="font-mono text-xs uppercase tracking-widest text-inv-muted">Data</p>
        <p className="mt-3 text-sm leading-relaxed text-inv-muted">
          Prices from Yahoo Finance. News from Indian business RSS feeds,
          NewsAPI and Finnhub. Sentiment is rule-based and explainable.
        </p>
      </div>
    </div>
  );
}

/* The close and the footer are one section, footer.closing (one screen):
   row 1 the dealt close, row 2 the links and the legal row. On other pages
   the footer is a plain footer. */
export function SiteFooter() {
  const pathname = usePathname();
  const isHome = pathname === "/";
  if (!isHome) {
    return (
      <footer className="border-t border-ink/10 bg-inv-bg text-inv-ink">
        <div className="wrap py-12">
          <FooterColumns />
        </div>
        <div className="border-t border-inv-surface">
          <p className="wrap py-4 font-mono text-xs text-inv-muted">
            Research aid, not investment advice. Past sentiment does not predict future returns.
          </p>
        </div>
      </footer>
    );
  }
  return (
    <footer className="closing section-box bg-inv-bg text-inv-ink" style={{ "--h": 1 } as React.CSSProperties}>
      <div className="wrap justify-between">
        <div>
          <h2 id="close" className="font-display text-3xl leading-[1.1] sm:text-5xl">
            Start with one stock.
          </h2>
          <p className="mt-5 max-w-lg text-[17px] leading-relaxed text-inv-muted">
            One ticker, one score, one decision.
            <span className="hidden sm:inline"> The research is free to read; the call is yours to make.</span>
          </p>
          <div className="mt-8">
            <Link
              id="close-primary"
              href="/analyze"
              className="btn-step inline-flex h-12 min-h-11 items-center rounded-sm bg-accent px-6 text-[15px] font-medium text-white hover:bg-[#0a5e68]"
            >
              Analyse a stock
            </Link>
          </div>
        </div>
        <div>
          <FooterColumns />
          <div className="mt-10 border-t border-inv-surface pt-4">
            <p className="font-mono text-xs text-inv-muted">
              Research aid, not investment advice. Past sentiment does not predict future returns.
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}

/* Phone action bar: the main action, fixed at the foot, shown once the
   hero's button has scrolled away (and hidden while it is on screen).
   Home page only; display:none above 639px. */
export function ActionBar() {
  const pathname = usePathname();
  const [shown, setShown] = useState(false);
  useEffect(() => {
    if (pathname !== "/") return;
    const btn = document.getElementById("hero-primary");
    if (!btn) {
      setShown(true);
      return;
    }
    const io = new IntersectionObserver(([entry]) => setShown(!entry.isIntersecting), {
      threshold: 0,
    });
    io.observe(btn);
    return () => io.disconnect();
  }, [pathname]);
  if (pathname !== "/") return null;
  return (
    <nav className="actionbar" aria-label="Quick actions" data-bar={shown ? "shown" : "hidden"}>
      <Link
        href="/analyze"
        className="btn-step inline-flex h-12 items-center justify-center rounded-sm bg-accent text-[15px] font-medium text-white hover:bg-[#0a5e68]"
      >
        Analyse a stock
      </Link>
    </nav>
  );
}
