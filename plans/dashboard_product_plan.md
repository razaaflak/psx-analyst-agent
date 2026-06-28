# PSX AI Hub Product Plan

**Status:** Draft v2 — commercial product direction, not locked.
**Owner:** Ahmad
**Product name:** PSX AI Hub
**Purpose:** Build a polished AI-enabled Pakistan Stock Exchange portal for beginner, intermediate, and advanced PSX users.

This plan replaces the earlier internal dashboard direction. The public product is not a pipeline monitor and should not expose training, paper-trading, file names, scraping details, or internal readiness language. Users should experience PSX AI Hub as a premium market-intelligence portal: useful, visual, personalized, and simple to understand.

---

## 1. Product Positioning

**Public promise:**

> PSX AI Hub is an AI-powered Pakistan Stock Exchange intelligence platform that helps investors understand the market, discover opportunities, track portfolios, receive personalized alerts, and research PSX stocks with confidence.

**Product feeling:**

- First serious AI-enabled PSX one-stop shop.
- Modern financial terminal, but friendly enough for normal investors.
- Visual, fast, polished, chart-heavy, and symbol-driven.
- Clear enough for beginners; powerful enough for serious PSX users.
- Data-backed and confidence-aware without showing the internal machinery.

**Do not position it as:**

- A paper-trading dashboard.
- A training monitor.
- A pipeline viewer.
- A collection of raw CSVs, rules, or logs.
- A broker or order-execution platform.

---

## 2. Product Principles

1. **Sell the outcome, hide the machinery.**
   Users see market intelligence, AI summaries, charts, alerts, and portfolio insights. They do not see how data was collected or how internal files are structured.

2. **One intelligence core, three product experiences.**
   Beginner, Intermediate, and Advanced should share one underlying truth engine. The tiers change feature depth, analytics density, personalization, and alert power.

3. **Polished visuals are part of the product.**
   Use PSX symbols, company logos where available, sector colors, charting, heatmaps, badges, icons, and report-style cards. Avoid plain admin-dashboard energy.

4. **Phase the build.**
   Do not build every tool, side option, agent, scanner, and report in one go. Ship a small, beautiful core first, then expand.

5. **Decision support, not execution.**
   Even when monetized, the platform should not place trades. It should help users review, compare, understand, and decide.

6. **Trust without overexposure.**
   Public wording can say "Verified PSX data" or "Updated after market close." It should not expose collection ladders, source scripts, or internal readiness gates.

---

## 3. User Tiers

The tiers should become product packaging, not just UI modes.

| Tier | User | Promise | Main Value |
|---|---|---|---|
| **Beginner** | New or casual PSX investor | Understand PSX without confusion | Simple market view, watchlist, explanations, dividend/result alerts |
| **Intermediate** | Active investor managing holdings | Make better portfolio decisions | Portfolio Doctor, AI stock scores, sector risk, personalized alerts |
| **Advanced** | Serious investor/trader/researcher | Research deeply and move faster | AI analyst personas, scanners, advanced charts, evidence, exports |

### Beginner

Beginner users should not see overwhelming tables by default.

Core experience:

- Market Pulse with simple mood and sector view.
- AI explanations in plain English.
- Watchlist with simple labels: Strong, Watch, Risk, Expensive, Dividend.
- Dividend and result alerts.
- Glossary-style explanations for common terms.
- "Why this matters" blocks on important cards.

Avoid:

- Dense backtests.
- Rule IDs.
- Raw scoring formulas.
- Complicated technical indicators by default.
- Urgent buy/sell language.

### Intermediate

Intermediate users want help managing decisions.

Core experience:

- Portfolio Doctor.
- Sector exposure and concentration risk.
- AI stock scores with fundamental, technical, and sentiment explainers.
- Personalized WhatsApp alerts.
- Watchlist ranking.
- Result/dividend impact summary.
- Stock comparison.
- Weekly portfolio health report.

Avoid:

- Too much internal methodology.
- Advanced-only scanners on the main dashboard.
- Overly technical agent debates unless expanded.

### Advanced

Advanced users want power tools.

Core experience:

- AI analyst panel.
- Advanced charting.
- Technical setup scanner.
- Dividend/yield quality scanner.
- Valuation and peer comparison.
- Strategy evidence and historical outcome views.
- Custom alert builder.
- Exportable reports.

Avoid:

- Hiding too much detail.
- Generic summaries without evidence.
- Simplifying away disagreement between analyst personas.

---

## 4. Navigation And Pages

Recommended commercial navigation:

1. **Market Pulse**
2. **AI Picks & Watchlist**
3. **Portfolio Doctor**
4. **Stock Lab**
5. **Alerts**
6. **AI Analysts**
7. **Charts & Analytics**
8. **Reports**
9. **Account & Billing**

The first release should not implement every page at full depth. Each page below has a target product shape plus suggested phase.

---

## 5. Page Detail

### 5.1 Market Pulse

**Job:** Make PSX AI Hub feel like the user's daily PSX starting point.

Primary widgets:

- KSE-100 headline card with index level, change, and market mood.
- Sector heatmap: banks, E&P, cement, fertilizer, power, textile, autos, technology.
- Top gainers / losers.
- Most active symbols.
- News highlights.
- AI daily market summary.
- "What changed today" card.
- "What to watch tomorrow" card.

Beginner:

- Simple market mood.
- 3 bullet AI summary.
- Sector heatmap with plain labels.
- Top news explained.

Intermediate:

- Sector rotation.
- Watchlist impact.
- Portfolio impact.
- Result/dividend highlights.

Advanced:

- Breadth, volume, technical index levels, market regime, macro overlay.
- Sector relative strength.

Phase:

- **Phase 1:** KSE-100, sector heatmap, AI summary, top movers, news highlights.
- **Phase 3+:** Regime model, breadth, sector rotation analytics.

---

### 5.2 AI Picks & Watchlist

**Job:** Help users find stocks worth reviewing.

Primary widgets:

- Personalized watchlist.
- AI-ranked opportunity cards.
- Dividend candidates.
- Swing setup candidates.
- Risk warnings.
- Recently changed view: "New today", "Improved", "Weakened".
- Confidence badges.
- Add/remove watchlist.

Beginner:

- Simple labels: Watch, Good Dividend, High Risk, Overheated.
- Plain-language explanation.

Intermediate:

- AI stock scores.
- Portfolio fit.
- Entry-quality note.
- Result/dividend event status.

Advanced:

- Filter by sector, valuation, RSI, dividend yield, trend, volume, and agent opinion.
- Compare AI personas on the same symbol.

Phase:

- **Phase 1:** Watchlist, symbol cards, simple AI summaries.
- **Phase 2:** Personalized rankings and watchlist alerts.
- **Phase 4:** Advanced scanner filters and persona comparison.

---

### 5.3 Portfolio Doctor

**Job:** Turn a user's holdings into useful insights.

Primary widgets:

- Holdings upload/manual entry.
- Portfolio value summary.
- Sector allocation chart.
- Concentration risk.
- Dividend income estimate.
- Holding-level AI health score.
- Rebalancing review candidates.
- Cash allocation.
- Portfolio vs KSE-100 comparison.

Beginner:

- "Healthy / Watch / Risk" labels.
- Simple explanation of overexposure.
- Dividend income estimate.

Intermediate:

- Sector caps, stock weights, risk contribution.
- Review suggestions.
- Portfolio health report.

Advanced:

- Scenario analysis.
- Drawdown simulation.
- Factor exposure.
- Correlation-style concentration warnings.

Phase:

- **Phase 2:** Manual portfolio entry, sector allocation, health labels.
- **Phase 3:** Personalized alerts and weekly health report.
- **Phase 4:** Scenario analysis and advanced risk analytics.

---

### 5.4 Stock Lab

**Job:** Make PSX AI Hub the place users search any PSX stock.

Primary widgets:

- Symbol search.
- Company profile with logo/symbol.
- Price chart.
- AI stock summary.
- Fundamentals: EPS, payout, dividend history, valuation, earnings trend.
- Technicals: moving averages, RSI, volume, support/resistance.
- News/results/dividend timeline.
- Peer comparison.
- Watchlist and alert actions.

Beginner:

- "Is this stock strong, weak, expensive, risky, dividend-friendly?"
- Explanation-first cards.

Intermediate:

- AI stock score breakdown.
- Portfolio fit.
- Event risk.

Advanced:

- Historical valuation bands.
- Technical overlays.
- Peer table.
- Persona debate and evidence.

Phase:

- **Phase 1:** Search, profile, chart, AI summary, basic fundamentals.
- **Phase 2:** Watchlist actions, event timeline.
- **Phase 4:** Advanced overlays, peer comparison, persona debate.

---

### 5.5 Alerts

**Job:** Make WhatsApp/SMS personalization a premium reason to subscribe.

Primary widgets:

- Channel preferences: WhatsApp, SMS, email later.
- Alert categories:
  - market brief
  - result announcement
  - dividend announcement
  - price level
  - portfolio risk
  - watchlist change
  - AI analyst update
  - weekly report
- Quiet hours.
- Daily alert cap.
- Alert history.
- Test alert preview.

Beginner:

- Simple toggles.
- Daily market brief.
- Watchlist/dividend/result alerts.

Intermediate:

- Portfolio risk alerts.
- Personalized watchlist alerts.
- Price level alerts.

Advanced:

- Custom trigger builder.
- Agent disagreement alerts.
- Technical setup alerts.

Phase:

- **Phase 2:** WhatsApp daily brief and watchlist/result/dividend alerts.
- **Phase 3:** Portfolio risk alerts.
- **Phase 4:** Custom alert builder.

Public wording:

- Use "research alert", "watch item", "portfolio review", "market brief".
- Avoid "buy now", "guaranteed", "must sell", or "trade placed".

---

### 5.6 AI Analysts

**Job:** Make the AI part tangible and monetizable.

Personas:

- **Dividend Investor:** Long-term dividend and quality lens.
- **Swing Trader:** Technical setups and short-horizon opportunities.
- **Risk Officer:** Concentration, event risk, overexposure, thesis weakness.
- **Macro Analyst:** Rates, oil, PKR, budget, IMF, sector impact.
- **Beginner Explainer:** Converts market jargon into simple language.

Primary widgets:

- Persona cards.
- Today's analyst notes.
- Symbol-specific persona opinions.
- Agreement/disagreement summary.
- "Ask an analyst" chat-style interaction later.

Beginner:

- Beginner Explainer and Dividend Investor only.

Intermediate:

- Dividend Investor, Swing Trader, Risk Officer.

Advanced:

- Full analyst panel, comparisons, custom questions, historical evidence.

Phase:

- **Phase 3:** Static daily persona summaries through OpenRouter.
- **Phase 4:** Symbol-level persona debate.
- **Phase 5:** Interactive analyst chat with guardrails.

Internal guardrail:

- Persona agents should read derived snapshots and user-safe product data. They should not write source records or independently create unverified claims.

---

### 5.7 Charts & Analytics

**Job:** Give advanced users the tools they expect from a serious market portal.

Primary widgets:

- Interactive price charts.
- Moving averages.
- Volume.
- RSI.
- Support/resistance.
- Valuation bands.
- Dividend history chart.
- Peer comparison chart.
- Sector comparison.
- Screening tools.

Beginner:

- Basic line chart and simple trend label.

Intermediate:

- Moving averages, volume, valuation history.

Advanced:

- Full technical overlays, screeners, historical setup outcomes, export.

Phase:

- **Phase 1:** Basic chart in Stock Lab.
- **Phase 3:** Dedicated charts page.
- **Phase 4:** Advanced overlays and screeners.

---

### 5.8 Reports

**Job:** Make PSX AI Hub feel like a premium research service.

Primary reports:

- Daily market brief.
- Weekly PSX outlook.
- Portfolio health report.
- Dividend income report.
- Watchlist opportunity report.
- Stock one-pager.
- Advanced PDF/export later.

Beginner:

- Daily brief and simple weekly outlook.

Intermediate:

- Portfolio health and watchlist report.

Advanced:

- Downloadable research packs, custom reports, deeper analytics.

Phase:

- **Phase 2:** Daily/weekly report pages.
- **Phase 3:** Portfolio health report.
- **Phase 4:** Exportable reports.

---

## 6. Phased Build Roadmap

### Phase 0 — Product Foundation

Goal: Define the commercial product language and visual system before building features.

Deliverables:

- Final brand direction: PSX AI Hub.
- Logo/mark direction.
- Color system and typography.
- Navigation structure.
- Page wireframes.
- Tier packaging: Beginner, Intermediate, Advanced.
- Data display language:
  - "Verified PSX data"
  - "Updated after market close"
  - "AI confidence"
  - "Portfolio review"
  - "Research alert"

Do not build:

- Full agents.
- WhatsApp integration.
- Advanced scanners.
- Broker integrations.

---

### Phase 1 — Beginner Portal MVP

Goal: Ship a polished beginner-first PSX AI Hub experience. Phase 1 should make a new or casual PSX user feel, "I finally understand what is happening in the market," without exposing advanced research tools yet.

Phase 1 audience:

- Beginner users only.
- Users who know a few popular PSX symbols but do not know how to read dense technical/fundamental dashboards.
- Users who want a daily market starting point, simple stock explanations, and watchlist alerts.

Phase 1 pages:

1. Market Pulse.
2. Beginner Watchlist.
3. Stock Lab Basic.
4. Alerts Basic.
5. Learn / Explain.

Do not include in Phase 1:

- Portfolio Doctor.
- AI Analyst panel.
- Advanced chart overlays.
- Scanners.
- Backtests or strategy evidence.
- Custom alert builder.
- Intermediate/Advanced tier toggle inside the main app.
- Internal pipeline, data collection, file names, or readiness language.

#### Phase 1 Navigation

Use a simple left sidebar on desktop and bottom navigation on mobile.

Desktop nav:

- Market Pulse
- Watchlist
- Stock Lab
- Alerts
- Learn

Mobile nav:

- Pulse
- Watchlist
- Search
- Alerts
- Learn

The app should not feel like a settings-heavy admin panel. Keep navigation short, icon-led, and visually calm.

#### Phase 1 Visual Style

The first implementation should look like a premium PSX portal, not a rough prototype.

Visual direction:

- Brand: PSX AI Hub.
- Overall feel: refined financial newspaper + modern AI dashboard.
- Palette: off-white / warm paper base, deep charcoal navigation, PSX green accents, restrained red for negative moves, amber for watch/caution, blue for information.
- Typography: strong editorial headings, clean readable UI text.
- Cards: 8-12px radius, crisp borders, light shadows only where needed.
- Charts: clean SVG/canvas charts, not decorative placeholders.
- Symbols: use stock tickers as compact symbol badges until company logos are available.
- Icons: use clear finance/product icons for market, watchlist, search, alerts, learn.
- Mobile: first-class responsive layout, not a squeezed desktop.

Avoid:

- Generic purple SaaS gradients.
- Cartoonish AI visuals.
- Too many floating cards.
- Dense tables on the first screen.
- Flashing price-board energy.
- Any "training", "paper", or internal-system wording.

#### Page 1: Market Pulse

Purpose: The daily home page for beginner PSX users.

Hero area:

- Large page title: "Market Pulse"
- Subtitle: "Your daily PSX snapshot in plain English."
- KSE-100 headline card:
  - index level
  - daily point change
  - daily percentage change
  - mood label: Positive / Mixed / Cautious / Weak
  - updated time: "Updated after market close"

Widgets:

- **AI Market Summary**
  - 3 short bullets.
  - Plain English.
  - No jargon unless explained.
  - Example:
    - "Banks supported the index today."
    - "Cement cooled after recent strength."
    - "Dividend names stayed relatively stable."

- **Sector Heatmap**
  - 6-8 beginner-friendly sector tiles.
  - Each tile shows sector name, daily move, and color.
  - Green = up, red = down, amber = mixed/flat.
  - Tile labels should be readable: Banks, Oil & Gas, Cement, Fertilizer, Power, Technology, Textile, Autos.

- **Top Movers**
  - Two-column card: Gainers and Losers.
  - Show ticker, company short name, percent move.
  - Add tiny reason label where available: Result, Dividend, Volume, Sector move, News.

- **Today's Watch Items**
  - 3 items max.
  - Beginner-safe language.
  - Example labels:
    - "Dividend event"
    - "Price moved sharply"
    - "Result announced"
    - "Sector getting active"

- **Market Mood Explainer**
  - One short paragraph explaining what the mood means.
  - Include "This is not a trade instruction" in soft footer/legal text, not as the main product message.

Layout:

- Desktop: hero/headline full width, then KSE card and AI summary side by side, heatmap below, top movers/watch items below.
- Mobile: KSE card first, AI summary second, heatmap scrolls horizontally or becomes two columns.

#### Page 2: Beginner Watchlist

Purpose: Let users track selected PSX stocks without needing advanced analysis.

Widgets:

- **My Watchlist Header**
  - Search/add stock input.
  - Watchlist count.
  - Last updated label.

- **Stock Cards**
  - Ticker badge.
  - Company short name.
  - Current/last close price.
  - Daily change.
  - Beginner label:
    - Strong
    - Stable
    - Watch
    - Risky
    - Expensive
    - Dividend
  - One-line AI explanation.
  - Buttons:
    - View
    - Alert

- **Watchlist Insights**
  - "3 stocks moved up today"
  - "1 dividend event"
  - "2 stocks need attention"

- **Beginner Filters**
  - All
  - Dividend
  - Moving Up
  - Needs Attention
  - News Today

UI rules:

- Cards should be visual and scannable.
- No dense spreadsheet in Phase 1.
- Use color labels carefully; do not make every card bright.
- "View" opens Stock Lab Basic.

#### Page 3: Stock Lab Basic

Purpose: Make any PSX stock understandable in 60 seconds.

Top area:

- Search bar: "Search PSX symbol or company"
- Stock identity card:
  - ticker badge
  - company name
  - sector
  - last close
  - daily change
  - beginner label

Widgets:

- **AI Stock Summary**
  - 4 lines max.
  - Explain what the stock does, what changed recently, and what a beginner should watch.

- **Simple Price Chart**
  - 1M / 3M / 1Y tabs.
  - Clean line chart.
  - No advanced indicators in Phase 1.

- **Stock Health**
  - Three simple meters:
    - Price Trend
    - Valuation
    - Dividend
  - Labels: Good / Neutral / Caution.
  - Each meter has a one-sentence explanation.

- **Key Numbers**
  - Price
  - Day change
  - Market cap if available
  - Dividend yield if available
  - P/E if available
  - 52-week range if available

- **News & Events**
  - Recent result/dividend/news items.
  - Each item has a plain-language "Why it matters" line.

- **Beginner Explainer**
  - Contextual definitions.
  - Example: if P/E is shown, include "P/E is a simple way to compare price with earnings."

Actions:

- Add to Watchlist.
- Set Alert.
- Share / copy stock page link later.

UI rules:

- Keep the first screen focused on summary, chart, and stock health.
- Push numbers and events lower on the page.
- Do not show raw model methodology.

#### Page 4: Alerts Basic

Purpose: Make alerts feel like a core paid feature without building the full advanced alert engine yet.

Widgets:

- **Alert Channels**
  - WhatsApp toggle.
  - SMS toggle.
  - Email can be shown as "coming later" only if needed.

- **Beginner Alert Types**
  - Daily market brief.
  - Watchlist price movement.
  - Dividend announcement.
  - Result announcement.
  - Important news on watched stocks.

- **Quiet Hours**
  - Start time.
  - End time.
  - Simple copy: "We will avoid non-urgent alerts during quiet hours."

- **Alert Preview**
  - Show how a WhatsApp alert will look.
  - Example:
    - "PSX AI Hub: MEBL announced a dividend. Here is what changed and why it matters."

- **Alert History**
  - Recent alerts list.
  - Status: Sent / Queued / Failed.

UI rules:

- Use toggles for alert types.
- Use channel icons for WhatsApp/SMS.
- Avoid advanced trigger conditions in Phase 1.

#### Page 5: Learn / Explain

Purpose: Help beginners build confidence and reduce support burden.

Widgets:

- **PSX Basics**
  - What is KSE-100?
  - What is a dividend?
  - What is market cap?
  - What is P/E?
  - What does volume mean?

- **How To Read This App**
  - Market Pulse.
  - Watchlist labels.
  - Stock Health.
  - Alerts.

- **Beginner Guides**
  - "How to follow a stock result"
  - "How to think about dividends"
  - "How to avoid overreacting to one-day moves"

UI rules:

- Use short cards.
- Use illustrations/icons sparingly.
- Link explanations contextually from Market Pulse and Stock Lab.

#### Phase 1 Data And Content Requirements

The implementation agent should design the UI so it can initially run from static/demo data, then later connect to product snapshots.

Required demo data shape:

- Index summary.
- Sector moves.
- Top gainers/losers.
- Watchlist stock cards.
- Stock detail data.
- News/event items.
- Alert preferences.
- Alert history.

Public data labels:

- "Verified PSX data"
- "Updated after market close"
- "AI summary"
- "Watch item"
- "Research alert"

Do not show:

- file names
- script names
- scrape method
- pipeline step numbers
- paper/training status

#### Phase 1 Implementation Handoff Notes

Recommended first build target:

- A polished frontend prototype with real routing, responsive layouts, and demo data.
- No backend required for the first visual implementation unless explicitly requested.
- Keep components reusable:
  - AppShell
  - SidebarNav
  - MobileNav
  - MarketPulsePage
  - WatchlistPage
  - StockLabPage
  - AlertsPage
  - LearnPage
  - MetricCard
  - SectorHeatmap
  - StockCard
  - SimpleLineChart
  - AlertToggle
  - ExplainerCard

Definition of done for Phase 1 design implementation:

- Desktop and mobile layouts work.
- Navigation between the five beginner pages works.
- Cards and charts use realistic PSX demo content.
- UI feels polished enough to show a potential customer.
- No internal pipeline/training/paper wording appears in the product surface.

---

### Phase 2 — Personalization MVP

Goal: Make the product useful to a paying user personally.

Pages:

- Portfolio Doctor basic.
- Alerts.
- Reports basic.

Core features:

- Manual portfolio entry.
- Sector exposure.
- Holding health labels.
- Dividend/result alerts.
- Watchlist alerts.
- WhatsApp daily market brief.
- Alert preferences and quiet hours.
- Daily/weekly report pages.

Success criteria:

- A user can track their own holdings.
- A user receives useful, non-noisy personalized alerts.
- WhatsApp becomes a clear premium feature.

---

### Phase 3 — AI Analyst Layer

Goal: Make AI personas a signature PSX AI Hub feature.

Pages:

- AI Analysts.
- Enhanced Stock Lab.
- Enhanced Portfolio Doctor.

Core features:

- Dividend Investor persona.
- Swing Trader persona.
- Risk Officer persona.
- Macro Analyst persona.
- Persona notes on Market Pulse and Stock Lab.
- Portfolio risk commentary.
- Weekly AI analyst report.

Success criteria:

- Users understand that different investing styles produce different views.
- Personas feel useful, not gimmicky.
- Disagreement is synthesized clearly.

---

### Phase 4 — Advanced Research Tools

Goal: Serve advanced users and justify a higher subscription tier.

Pages:

- Charts & Analytics.
- Advanced Stock Lab.
- Advanced Reports.

Core features:

- Technical scanner.
- Dividend quality scanner.
- Valuation bands.
- Peer comparison.
- Advanced chart overlays.
- Custom alert builder.
- Exportable reports.
- Strategy evidence views.

Success criteria:

- Advanced users can research deeply without leaving PSX AI Hub.
- The product begins to feel like a serious PSX terminal.

---

### Phase 5 — Monetization And Scale

Goal: Convert the product into a sustainable paid platform.

Core features:

- User accounts.
- Subscription plans.
- Payment integration.
- Plan limits:
  - watchlist size
  - portfolio count
  - alert count
  - report exports
  - analyst personas
  - advanced scanners
- Admin dashboard.
- Usage analytics.
- Support workflow.

Success criteria:

- Clear free/trial-to-paid funnel.
- Tier differences are obvious.
- Paid users feel the upgrade value.

---

## 7. Pricing And Packaging Direction

Exact pricing should be decided later, but the feature logic should be:

### Beginner

- Market Pulse.
- Basic Stock Lab.
- Small watchlist.
- Beginner Explainer.
- Dividend/result alerts.
- Daily AI market summary.

### Intermediate

- Everything in Beginner.
- Larger watchlist.
- Portfolio Doctor.
- AI stock scores.
- Personalized WhatsApp alerts.
- Portfolio health report.
- Sector risk analytics.

### Advanced

- Everything in Intermediate.
- Full AI analyst panel.
- Advanced charts.
- Scanners.
- Custom alerts.
- Exports.
- Deep reports.
- Strategy evidence.

---

## 8. Visual Direction

The product should feel like a premium Pakistan-market portal.

Visual requirements:

- Strong PSX AI Hub logo/mark.
- Company symbols/logos in stock cards.
- Sector heatmaps.
- Index and price charts.
- Portfolio donut/bar charts.
- Alert icons for WhatsApp/SMS.
- AI analyst persona cards.
- Green/red market movement, but not a one-note green/red UI.
- Clean responsive dashboard layout.
- Dense enough for investors, not cluttered like an admin panel.

Do not use discarded brainstorming prototypes as implementation references. The Phase 1 section above is the source of truth for the first implementation agent.

---

## 9. Internal Architecture Boundary

This is internal product architecture, not customer-facing copy.

Public pages should read from a safe derived product layer, not directly expose internal files or pipeline steps.

Recommended conceptual flow:

```text
Verified market data
  -> internal research engine
  -> derived product snapshots
  -> dashboard/API
  -> AI personas and notification engine
  -> user-facing pages, WhatsApp, SMS, reports
```

Public wording:

- "Verified PSX data"
- "Updated after market close"
- "AI confidence"
- "Market intelligence"
- "Research alert"

Avoid public wording:

- "paper ledger"
- "pipeline step"
- "scraper"
- "rules_library.md"
- "predictions_log.csv"
- "readiness gate"

---

## 10. Deferred Features

Do not build these in the early phases:

- Broker execution.
- Live order placement.
- Public social/community feed.
- Agent marketplace.
- Mobile app.
- Intraday day-trading terminal.
- Fully custom strategy builder.
- Broker portfolio auto-sync.
- Public claims like "guaranteed profit" or "best stock to buy now."

These may be revisited only after the core paid web portal is working.

---

## 11. Next Product Decisions

Before implementation, decide:

1. Which frontend stack should the implementation agent use?
2. Should Phase 1 be a static polished prototype first, or should it connect to existing product data immediately?
3. Which 20-30 PSX symbols should get polished ticker/profile treatment first?
4. Should WhatsApp appear in Phase 1 as UI-only settings, or be fully deferred to Phase 2?
5. What brand style should lead: premium financial terminal, friendly beginner education portal, or hybrid?
