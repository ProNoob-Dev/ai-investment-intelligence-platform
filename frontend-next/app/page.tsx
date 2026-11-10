"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { analyzeTicker, getOpportunities, getScannerStatus } from "@/lib/api/endpoints";
import { Button, Card, Chip } from "@/components/ui/ui";
import { PriceCard } from "@/components/analyze/PriceCard";
import { SentimentCard } from "@/components/analyze/SentimentCard";
import { OpportunityCard } from "@/components/discover/DiscoverCards";
import { formatINR, timeAgo } from "@/lib/utils/format";
import { sentimentLabel } from "@/lib/utils/sentiment";
import type { AnalysisResult } from "@/lib/types/analysis";
import type { Opportunity, ScannerStatus } from "@/lib/types/opportunity";

const STEPS = [
  {
    title: "News in",
    body: "Every 30 minutes the platform pulls Indian business news (Economic Times, Moneycontrol, Livemint, Business Standard and more) and tags each article with the tickers it mentions.",
    frame: "8 feeds · tagged by ticker",
    visual: (
      <div className="space-y-2 font-mono text-[13px] leading-relaxed">
        <p className="flex justify-between gap-3 border border-ink/10 bg-paper px-3 py-2">
          <span>Reliance Jio</span>
          <span className="text-accent">→ RELIANCE</span>
        </p>
        <p className="flex justify-between gap-3 border border-ink/10 bg-paper px-3 py-2">
          <span>HDFC Bank</span>
          <span className="text-accent">→ HDFCBANK</span>
        </p>
        <p className="flex justify-between gap-3 border border-ink/10 bg-paper px-3 py-2">
          <span>Tata Steel</span>
          <span className="text-accent">→ TATASTEEL</span>
        </p>
      </div>
    ),
  },
  {
    title: "News sentiment, scored",
    body: "A rule-based engine reads every headline: weighted terms, intensifiers, negation, contrast and the size of the move. Every score traces back to the words that made it. No black box.",
    frame: "Score −1 to +1 · explainable",
    visual: (
      <div>
        <div className="relative h-2 w-full bg-surface" aria-hidden>
          <span className="absolute inset-y-0 left-0 w-[40%] bg-[#c2402a]/70" />
          <span className="absolute inset-y-0 left-[40%] w-[20%] bg-hold/60" />
          <span className="absolute inset-y-0 left-[60%] w-[40%] bg-accent/70" />
          <span className="absolute top-1/2 h-5 w-0.5 -translate-x-1/2 -translate-y-1/2 bg-ink" style={{ left: "71%" }} />
        </div>
        <div className="mt-2 flex justify-between font-mono text-xs text-muted">
          <span>−1 SELL</span>
          <span>0</span>
          <span>+1 BUY</span>
        </div>
        <p className="mt-3 font-mono text-[13px]">Example headline scores +0.42</p>
      </div>
    ),
  },
  {
    title: "Research call",
    body: "Recent sentiment counts most, history sets the pattern. Above +0.20 is a BUY, below −0.20 a SELL, anything between a HOLD, with the drivers and the headlines behind the call.",
    frame: "BUY ≥ +0.20 · SELL ≤ −0.20",
    visual: (
      <div className="flex flex-wrap gap-2 font-mono text-[13px]">
        <span className="border border-accent bg-accent px-3 py-2 text-white">BUY ≥ +0.20</span>
        <span className="border border-ink/15 bg-paper px-3 py-2">HOLD −0.20 to +0.20</span>
        <span className="border border-ink/15 bg-paper px-3 py-2">SELL ≤ −0.20</span>
      </div>
    ),
  },
];

function HowItWorks() {
  return (
    <section aria-labelledby="how-it-works" data-moment="pinned-chapters" className="section-box">
      <div className="wrap mo-pc__grid">
        <div className="mo-pc__text">
          <h2 id="how-it-works" className="font-display text-3xl font-medium tracking-tight sm:text-4xl">
            How Investment Intelligence makes a call
          </h2>
          <p className="max-w-2xl text-[17px] leading-relaxed text-muted">
            Three steps, all visible. Nothing about the decision is hidden from you.
          </p>
          <ol className="mo-pc__steps">
            {STEPS.map((step, i) => (
              <li key={step.title} className="mo-pc__step">
                <h3>{step.title}</h3>
                <p>{step.body}</p>
                <figure className="mo-pc__visual mo-pc__visual--lit">
                  <div className="w-full">
                    <p className="font-mono text-xs uppercase tracking-widest text-muted">
                      Step {i + 1} · {step.title}
                    </p>
                    <div className="mt-4">{step.visual}</div>
                    <p className="mt-4 font-display text-2xl font-medium tracking-tight">{step.frame}</p>
                  </div>
                </figure>
              </li>
            ))}
          </ol>
        </div>
        <div className="mo-pc__visuals frame" aria-hidden />
      </div>
    </section>
  );
}

export default function HomePage() {
  const [hero, setHero] = useState<AnalysisResult | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [scanner, setScanner] = useState<ScannerStatus | null>(null);
  const [heroError, setHeroError] = useState(false);

  useEffect(() => {
    analyzeTicker("RELIANCE")
      .then(setHero)
      .catch(() => setHeroError(true));
    getOpportunities()
      .then((res) => setOpportunities(res.opportunities.slice(0, 3)))
      .catch(() => setOpportunities([]));
    getScannerStatus()
      .then(setScanner)
      .catch(() => setScanner(null));
  }, []);

  /* Moments mount after React hydration. The loader moves figures and marks
     <html>; doing that before hydration makes React see a different DOM and
     re-render the root, which drops the mounted marks. */
  useEffect(() => {
    let cancelled = false;
    (window as unknown as { __momentsManual: boolean }).__momentsManual = true;
    const url = "/moments/moments.js";
    import(/* webpackIgnore: true */ url)
      .then(async (m) => {
        const mod = m as unknown as { mountAll: (root: Document) => Promise<unknown> };
        if (!cancelled) await mod.mountAll(document);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const topNews = hero?.newsReferences?.[0];

  return (
    <>
      {/* Hero — exactly the first screen. The -mt pulls it under the fixed
          header (main carries pt-[var(--nav)] for the other pages). */}
      <section
        aria-labelledby="hero-title"
        className="section-box hero-box -mt-[var(--nav)]"
        style={{ "--h": 1 } as React.CSSProperties}
      >
        <div className="wrap">
          <div data-enter className="hero-text grid flex-1 items-start gap-6 lg:grid-cols-12">
            <div className="lg:col-span-6" data-moment="liquid-type" data-moment-opts='{"strength": 1}'>
              <p className="font-mono text-xs uppercase tracking-widest text-accent">
                AI investment research · NSE &amp; BSE · 8 news feeds
              </p>
              <h1
                id="hero-title"
                className="mt-4 font-display text-[34px] font-medium leading-[1.05] tracking-[-0.045em] sm:text-[52px] lg:text-[56px]"
              >
                Investment research,
                <br />
                ahead of the market.
              </h1>
              <p className="mt-5 max-w-lg text-[17px] leading-relaxed text-muted">
                Type any Indian stock. The platform reads the news, scores the
                sentiment and checks the price, then gives you a BUY, HOLD or SELL
                call<span className="hidden sm:inline">, with the headlines behind it</span>.
              </p>
              {hero && (
                <p className="mt-5 hidden font-mono text-sm sm:block">
                  <span className="text-muted">RELIANCE </span>
                  {formatINR(hero.currentPrice)}
                  <span className="text-muted"> · </span>
                  {hero.sentiment.toFixed(2)} {sentimentLabel(hero.sentiment)}
                </p>
              )}
              {heroError && (
                <p className="mt-5 font-mono text-sm text-muted">
                  Live data starts when the API is running. See Settings.
                </p>
              )}
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link href="/analyze" id="hero-primary">
                  <Button>Analyse a stock</Button>
                </Link>
                <Link href="/discover" className="hidden sm:inline-flex">
                  <Button variant="secondary">See today’s opportunities</Button>
                </Link>
              </div>
            </div>
            <div className="space-y-4 lg:col-span-6" data-ui aria-label="Live preview of an analysis">
              {hero ? (
                <>
                  <div className="hidden lg:block">
                    <PriceCard result={hero} />
                  </div>
                  <div className="lg:hidden">
                    <SentimentCard result={hero} compact />
                  </div>
                  <div className="hidden lg:block">
                    <SentimentCard result={hero} />
                  </div>
                  {topNews && (
                    <Card className="hidden lg:block">
                      <p className="font-mono text-xs uppercase tracking-widest text-muted">Latest headline</p>
                      <p className="mt-3 line-clamp-2 text-[15px] leading-relaxed">{topNews.title}</p>
                      <p className="mt-2 font-mono text-xs text-muted">{timeAgo(topNews.date)}</p>
                    </Card>
                  )}
                </>
              ) : (
                <Card>
                  <p className="font-mono text-xs uppercase tracking-widest text-muted">Live preview</p>
                  <p className="mt-3 text-[15px] leading-relaxed text-muted">
                    {heroError
                      ? "Start the API to see a live RELIANCE analysis here."
                      : "Loading a live RELIANCE analysis…"}
                  </p>
                </Card>
              )}
            </div>
          </div>
        </div>
      </section>

      <HowItWorks />

      {/* Live now — today's opportunities, one screen. */}
      <section aria-labelledby="live-now" className="section-box bg-surface/60" style={{ "--h": 1 } as React.CSSProperties}>
        <div className="wrap">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 id="live-now" className="font-display text-3xl font-medium tracking-tight sm:text-4xl">
                Live research now
              </h2>
              <p className="mt-3 hidden max-w-2xl text-[17px] leading-relaxed text-muted sm:block">
                The scanner’s latest picks: stocks whose news turned positive.
              </p>
            </div>
            <Link href="/discover" className="link-underline inline-flex min-h-11 items-center font-medium text-accent">
              All opportunities →
            </Link>
          </div>
          {opportunities.length > 0 ? (
            <div className="mt-8 grid gap-6 sm:mt-10 md:grid-cols-3">
              {opportunities.map((opp, i) => (
                <div key={opp.ticker} className={i === 2 ? "hidden md:block" : undefined}>
                  <OpportunityCard opportunity={opp} />
                </div>
              ))}
            </div>
          ) : (
            <Card className="mt-10">
              <p className="text-[15px] leading-relaxed text-muted">
                No opportunities on file yet. Run a scan from the Discover tab. It takes the last 48 hours of news
                and picks the strongest positive names.
              </p>
            </Card>
          )}
          {scanner && opportunities.length > 0 && (
            <p className="mt-10 hidden pt-5 font-mono text-xs text-muted sm:block">
              Scanner: {scanner.opportunitiesCount} picks from {scanner.maxCandidates} candidates · threshold
              +{scanner.sentimentThreshold.toFixed(2)} · last {scanner.lookbackHours} hours
            </p>
          )}
        </div>
      </section>
    </>
  );
}
