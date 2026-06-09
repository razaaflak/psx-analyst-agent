# CLAUDE.md — PSX Analyst Agent (Claude Code project context)

Claude Code loads this file automatically when this folder is opened. It is the operating contract for this project. **Before doing anything, read `INSTRUCTIONS.md` and `SKILL.md` in full, plus the relevant `pipeline/*.md` for the command you were given.**

## What this project is
A **self-learning, paper-trading** research agent for the Pakistan Stock Exchange (PSX). It collects PSX data automatically (Playwright MCP), runs Technical + Fundamental + Emotional/sentiment analysis, issues Buy/Hold/Sell/Trim **paper** suggestions, then grades its own past predictions and grows a rules library over time. It does **not** place real trades and it is **not** financial advice.

## Trigger commands → what to do
- **"Run the PSX daily pipeline for today"** → follow `pipeline/daily_run.md` end-to-end (8 steps). Collect data first via Playwright MCP per `pipeline/data_collection.md`.
- **"Run the PSX weekly review"** → follow `pipeline/weekly_run.md`.
- **"Morning brief"** → the lightweight pre-open summary at the end of `pipeline/daily_run.md` (no new paper trades).
- **"Analyze [TICKER]"** → apply `SKILL.md` to that one name and output a per-stock card (still paper, still cite data source).

## Non-negotiable rules (full list in INSTRUCTIONS.md)
1. **Paper trading only.** Never place or imply real orders.
2. **Not financial advice.** End substantive outputs with the one-line reminder.
3. **Collect data via Playwright MCP** from `dps.psx.com.pk` (see `pipeline/data_collection.md`). Never ask the user to paste unless every automated fallback fails.
4. **Never fabricate** a price, volume, dividend, or ratio. If verified data can't be obtained, skip the run and say so.
5. **No look-ahead** when grading past predictions; predictions and the trade ledger are append-only.
6. **Respect risk caps** (position/sector/cash/swing) and the rule-graduation thresholds in `SKILL.md`. No leverage. No averaging down on a broken thesis.

## Environment notes
- **Playwright MCP is already configured at system level.** At the start of a run, confirm the `browser_*` tools are available; if they are not, report it and stop (don't fall back to fabricating data).
- Read/write happens inside this folder: `data/`, `rules/`, `journal/`, `reports/`. Read current state at the start of each run; persist all updates at the end.
- Raw scraped snapshots go to `data/market_data/YYYY-MM-DD.json` (+ a close screenshot) as an audit trail.

## File map
```
CLAUDE.md            ← this bootstrap (auto-loaded)
INSTRUCTIONS.md      ← full operating prompt / identity / rules
SKILL.md             ← the analysis + decision + self-learning methodology
pipeline/daily_run.md       ← daily 8-step procedure
pipeline/data_collection.md ← Playwright MCP scraping spec
pipeline/weekly_run.md      ← weekend deep-dive
data/                ← portfolio.json, watchlist.json, ledgers, market_data/
rules/rules_library.md      ← the growing self-authored rulebook
journal/             ← dated daily entries
reports/             ← weekly reports
```

Start every run by reading the current state files, end every run by persisting updates and writing the journal entry.
