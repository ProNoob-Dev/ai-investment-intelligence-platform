# Page plan — AI Investment Intelligence Platform

Line 1: kind **software** (fintech: AI investment research for Indian stocks).
Line 2: deal — palette **cool-white-slate** (bg #f7f9fa, surface #ecf0f2, ink
#1f3038, accent teal #0d7480); type **Geist + Geist Mono** (display 500,
tracking -4.5% hero); hero **collage**; moments **liquid-type** (hero) +
**pinned-chapters** (how it works); nav-centre, footer-columns, close-type,
dark-band, pill buttons, stack mark; radius **sharp**. The palette fits a
fintech product because its off-white ground reads like a trading desk's
paper and its teal accent is the colour of money and markets — calm, exact,
never loud. No violet anywhere.

## Home (`/`) — the landing page

1. **Hero (collage, 1 screen):** h1 "Investment research, ahead of the
   market." (6 words; names the product, per the gate's copy-headline
   check — it replaced the dealt line in the gate round 2 fixes, after the
   round 1 line "Investment research before the market moves." overflowed
   its column at 64px and overlapped the collage; the banner was updated to
   match). One hard fact on the first screen: live RELIANCE price +
   sentiment from the API. Collage visual = the live analyse app-frame
   (price, sentiment gauge, drivers) beside a news card. One primary action:
   "Analyse a stock". Liquid-type moment on the headline.
2. **How it works (pinned-chapters, 2 screens):** three steps — news in,
   sentiment scored, decision out — each with its own frame (ingest,
   sentiment gauge, BUY/HOLD/SELL call).
3. **Live now (1 screen):** today's top opportunities from the scanner,
   real data, each a card to its analysis.
4. **Close (close-type, dark-band):** one line + "Analyse a stock" again.
   Footer-columns.

## App screens (same system, one section per screen, equal edges)

- **Analyse (`/analyze`):** search field + live result: price card, sentiment
  gauge + trend chart, drivers, peers, AI summary, news references, stale
  states. The app-frame is the product itself.
- **Discover (`/discover`):** scanner status + opportunity cards + manual scan.
- **Portfolio (`/portfolio`):** goal cards with P&L and progress, add goal /
  holding, AI suggestion per goal.
- **Research chat (`/chat`):** bubbles, typing indicator, history, portfolio
  context.
- **Settings (`/settings`):** API URL, provider status, data freshness.

Copy voice: plain, exact, investor-grade. No slop words ("unlock",
"supercharge", "delve"), no invented figures. Every number on screen comes
from the API or is labelled as an example.

Phone trims (final, after the gate): h1 34px below sm; compact gauge
max-w 180px on phones; hero fact line and lead suffix hidden below sm; hero
--padt 72px on phones; live-now lead hidden below sm and its 3rd card hidden
below md; scanner-status strip hidden below sm (it would overflow the
one-screen live-now section at 320); footer --bar 64px unconditional on
phones; footer height auto below 360px; how-it-works min-height 200svh on
phones (the pinned-chapters moment leaves it content-height at rest, and
that height is not a whole number of screens); footer Data column hidden
below sm, close lead second sentence hidden below sm.
