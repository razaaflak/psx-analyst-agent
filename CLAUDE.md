# CLAUDE.md — PSX Analyst Agent (Claude Code project context)

Claude Code loads this file automatically when this folder is opened. It is the operating contract for this project. **Before doing anything, read `INSTRUCTIONS.md` and `SKILL.md` in full, plus the relevant `pipeline/*.md` for the command you were given.**

## What this project is
A **self-learning PSX analyst agent** being trained toward becoming Ahmad's personal, experience-backed Pakistan Stock Exchange advisor. Daily loop: collect real data → F/T/E analysis → paper decisions → grade predictions → grow rules. The paper phase is training, not the destination. **Ultimate goal:** suggest buy/hold/increase%/decrease% with the judgment of a 30-year PSX practitioner, contributing to Ahmad's real profits. Ahmad executes; the agent never places orders. Advisory switch flips only when readiness gates pass (see `INSTRUCTIONS.md §1`).

Current phase: paper trading. Every output carries the not-advice reminder.

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
- **Playwright MCP is already configured at system level.** Confirm `browser_*` tools are available at run start; if not, report and stop.
- **Node.js + Playwright also installed system-wide.** Write Node.js Playwright scripts (`scripts/*.mjs`) for JS-rendered or 403-blocked pages. Tool ladder: (1) plain Python requests, (2) Node Playwright script, (3) interactive Playwright MCP.
- Python venv: `.venv\Scripts\python.exe`. Never use global interpreter.
- Read/write inside this folder: `data/`, `rules/`, `journal/`, `reports/`. Read current state at start; persist all updates at end.
- Raw scraped snapshots → `data/market_data/YYYY-MM-DD.json` + screenshot (audit trail).

## File map
```
CLAUDE.md            ← this bootstrap (auto-loaded)
INSTRUCTIONS.md      ← full operating prompt / identity / rules / readiness gates
SKILL.md             ← analysis + decision + self-learning methodology
pipeline/daily_run.md       ← daily 8-step procedure (canonical reference)
pipeline/data_collection.md ← Playwright MCP scraping spec
pipeline/weekly_run.md      ← weekend deep-dive

data/
  portfolio.json            ← current holdings + cash
  watchlist.json            ← symbols to analyze (with Shariah flags, face values)
  universe.json             ← 100 KSE-100 constituents (source for --universe flag)
  trade_ledger.csv          ← append-only paper trades
  predictions_log.csv       ← append-only predictions; graded in-place
  rolling_stats.json        ← DERIVED summary (rebuilt Step 8; read at Step 0)
  psx.db                    ← DERIVED query DB (git-ignored; rebuilt Step 8)
  market_data/YYYY-MM-DD.json ← daily raw scrape snapshot
  ohlc/{SYMBOL}.json        ← 101 symbols × 5yr real OHLC (2021→); updated daily
  fundamentals/{SYMBOL}.json ← 97/100 KSE-100 symbols; EPS/PAT/PBT + payouts
  news_archive.jsonl        ← forward-only news archive (grows daily from 2026-06-11)

scripts/
  collect_ohlc.py           ← OHLC store: --update --universe (daily) | --backfill --years 5
  collect_fundamentals.py   ← fundamentals: --universe (all 100) | --watchlist | --symbols
  archive_news.py           ← append macro_news from snapshots to news_archive.jsonl
  backtest.py               ← no-look-ahead rule validator; --condition-search for refinement
  build_db.py               ← rebuild psx.db from CSVs; --verify gate must print GATE:PASS
  queries.md                ← named SQL queries Q1-Q5 for psx.db

rules/rules_library.md      ← self-authored rulebook (5 Exp, 4 Core-seed as of 2026-06-13)
journal/                    ← dated daily entries
reports/                    ← weekly reports + reports/backtests/
```

Start every run by reading current state files. End every run by persisting updates and writing the journal entry.
