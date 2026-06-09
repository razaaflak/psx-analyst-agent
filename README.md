# PSX Analyst Agent — A Self-Learning Paper-Trading Pipeline

A daily, self-improving research agent for the Pakistan Stock Exchange (PSX). It does **not** place real trades. It runs technical, fundamental, and sentiment ("emotional") analysis, issues Buy / Hold / Sell / Trim suggestions, logs them as **paper trades**, then reconciles its own past predictions against what actually happened — learning from its hits and misses and writing new rules for itself over time.

> **This is a decision-support and learning tool, not financial advice and not a profit guarantee.** Pattern-based rules can overfit and break. Every suggestion is a paper suggestion for you to review with your own judgment. You alone decide what (if anything) to do in your real brokerage account.

---

## What's in this package

```
psx-analyst-agent/
├── CLAUDE.md                  ← auto-loaded by Claude Code (the operating contract)
├── README.md                  ← you are here (overview + the schedule)
├── INSTRUCTIONS.md            ← the master operating prompt you give your agent
├── SKILL.md                   ← the skill file (the analysis + decision methodology)
├── pipeline/
│   ├── daily_run.md           ← exact step-by-step daily procedure
│   ├── data_collection.md     ← automated Playwright MCP scraping spec (no copy-paste)
│   └── weekly_run.md          ← weekend deep-dive procedure
├── data/
│   ├── portfolio.json         ← paper holdings + paper cash
│   ├── watchlist.json         ← stocks the agent watches
│   ├── trade_ledger.csv       ← every paper buy/sell, with reasons
│   ├── predictions_log.csv    ← daily predictions + next-day reconciliation
│   └── market_data/           ← raw date-stamped EOD snapshots scraped each run (audit trail)
├── rules/
│   └── rules_library.md       ← the agent's growing, self-authored rulebook
├── journal/                   ← one dated markdown journal entry per run
└── reports/                   ← weekly performance reports
```

How they fit together: **INSTRUCTIONS.md** tells the agent who it is and how to behave. **SKILL.md** is the methodology it applies. **pipeline/** files are the exact steps to follow on each run. **data/**, **rules/**, **journal/** are the memory — what makes it learn across days instead of starting fresh each time.

---

## The exact schedule — when to look at the market

All times are **Pakistan Standard Time (PKT, GMT+5)** = your Islamabad time.

### PSX official market hours (verify on psx.com.pk, they change for Ramadan)

| Day | Pre-open | Regular session | Post-close |
|---|---|---|---|
| **Mon–Thu** | 9:15–9:30 AM | **9:32 AM – 3:30 PM** | 3:50–4:30 PM |
| **Friday** | 9:00–9:17 AM | **9:17 AM–12:00 PM**, then **2:32–4:30 PM** | 4:35–4:50 PM |
| **Ramadan (Mon–Thu)** | from 9:00 AM | 9:17 AM – **1:30 PM** | adjusted |
| **Ramadan (Friday)** | from 9:00 AM | 9:17 AM – **12:30 PM** | adjusted |

### Your routine (built around a busy day + family)

This pipeline is deliberately designed to run **once per day after the close**, on settled end-of-day (EOD) data. That avoids intraday noise, removes the pressure to watch screens all day, and gives the cleanest data for learning. A short morning glance is optional but useful.

| Time (PKT) | Who | What happens |
|---|---|---|
| **8:45–9:05 AM** (Mon–Thu) | You (10 min) | **Pre-open glance.** Skim overnight global news (US market close, oil price, any geopolitics), check PSX announcements board for your holdings. Note anything unusual. *Optional:* run the agent's "Morning Brief" (lightweight). |
| **9:32–10:00 AM** | — | **Do NOT act.** Opening 15–30 min is the most volatile. The agent never logs paper trades on opening prints. |
| **During the day** | — | Live your life. No screen-watching required. |
| **After 5:00 PM** (after EOD data settles) | **Agent (main run)** + you review (~20–30 min) | **The daily pipeline.** Agent **auto-collects today's official close via Playwright MCP** (no copy-paste), reconciles yesterday's prediction vs. reality, updates paper P&L, learns/updates rules, runs full TA+FA+sentiment, issues tomorrow's Buy/Hold/Sell/Trim suggestions, logs paper trades, writes the journal entry. You read it. |
| **Saturday or Sunday** (market closed) | **Agent (weekly run)** + you review (~45 min) | **Weekly deep-dive.** Aggregate hit-rate, prune/promote rules, re-check each holding's thesis, build the week-ahead calendar (MPC dates, results announcements, budget, ex-dividend dates). |

**Key timing principles baked into the design:**
- **Run on EOD close data, not intraday ticks.** Cleaner, less noise, no FOMO.
- **No look-ahead.** When reconciling, the agent only ever compares a *past* prediction to *later* actual data — never uses future information to "explain" a past call.
- **Decisions are for the *next* session.** Tonight's suggestion is what you'd consider doing at tomorrow's open, so the agent is always forecasting, never hindsight-trading.
- **Skip non-trading days.** Weekends and PSX holidays = no daily run (use them for the weekly review instead).

---

## How to start it (Claude Code in VS Code)

Playwright MCP is already configured on your system, so setup is just:

1. **Open this folder in VS Code** with the Claude Code extension. Claude Code automatically loads `CLAUDE.md` (the operating contract) — you don't need to paste `INSTRUCTIONS.md` each time.
2. **Edit `data/watchlist.json`** to set the stocks you want watched (pre-seeded with your blue chips).
3. **Edit `data/portfolio.json`** to set your starting paper cash (default: PKR 1,000,000) and any existing paper holdings (default: none).
4. (One-time sanity check) In the Claude Code chat, ask: *"List your available browser tools"* — you should see the Playwright `browser_*` tools. If you don't, fix the MCP config before running.

## How to run it each day

In the Claude Code chat, send:

> **Run the PSX daily pipeline for today**

The agent reads `CLAUDE.md` → `INSTRUCTIONS.md` → `SKILL.md`, collects today's data itself via Playwright MCP (`pipeline/data_collection.md`), then works through `pipeline/daily_run.md` and writes its updates into `data/`, `rules/`, and `journal/`. Review the journal entry it produces.

On the weekend, send:

> **Run the PSX weekly review**

Other handy prompts: **"Morning brief"** (quick pre-open summary, no trades) and **"Analyze MEBL"** (single-stock card).

### Recommended: review the diff before trusting

Because the agent writes to `data/`, `rules/`, and `journal/`, the VS Code Source Control panel (or `git`) is the easiest way to see exactly what it changed each run. Initialize git in the folder once (`git init && git add -A && git commit -m "seed"`) and you'll get a clean diff of every paper trade, rule change, and prediction after each run.

### Optional: fully unattended runs

If you later want it to run without you triggering it, schedule the headless CLI on trading-day evenings (~5:15 PM PKT, earlier in Ramadan):
```cron
15 17 * * 1-5  cd /path/to/psx-analyst-agent && claude -p "Run the PSX daily pipeline for today" >> data/market_data/cron.log 2>&1
```
The agent self-checks for trading days and skips PSX holidays. For now, the manual VS Code prompt is the simplest path.

---

## A note on data (fully automated)

The agent collects each day's data **itself** via the already-configured Playwright MCP, from the official PSX Data Portal — no copy-paste. The fallback ladder (in `pipeline/data_collection.md`) is: PSX portal JSON feed → PSX portal DOM scrape → backup source (ksestocks/sarmaaya) → screenshot read → (last resort only) ask you to paste. Every run records which source/rung it used and a confidence flag, saves a raw snapshot to `data/market_data/`, and **skips rather than fabricates** if verified data can't be obtained.

> **Use & compliance:** scraping here is for your **personal, non-redistributed** analysis at low frequency. The PSX portal's terms restrict redistribution/commercial use of its data; if this ever powers a public product, obtain a market-data license (marketdatarequest@psx.com.pk). Don't republish raw PSX data.
