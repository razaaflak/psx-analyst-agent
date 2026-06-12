# AGENTS.md - Codex Project Context

This repository is the PSX Analyst Agent: a self-learning, paper-trading research pipeline for Pakistan Stock Exchange analysis.

## Read First

Before any substantive run or analysis, read these files:

- `CLAUDE.md` - bootstrap contract and command routing
- `INSTRUCTIONS.md` - master operating rules and non-negotiables
- `SKILL.md` - PSX analysis, scoring, risk, and self-learning methodology
- The relevant `pipeline/*.md` file for the user command

## Hard Rules

- Paper trading only. Never place, imply, or recommend real orders.
- This is not financial advice. End substantive outputs with the required reminder.
- Never fabricate market data. If verified data cannot be collected, skip the run.
- Use Playwright MCP / browser tools for PSX data collection from `dps.psx.com.pk` following `pipeline/data_collection.md`.
- Keep predictions and ledgers append-only unless the user explicitly asks for repair.
- Respect portfolio risk caps, no leverage, and no averaging down on a broken thesis.
- Read current state at the start of each run and persist updates at the end.

## Key State Files

- `data/portfolio.json`
- `data/watchlist.json`
- `data/trade_ledger.csv`
- `data/predictions_log.csv`
- `data/market_data/YYYY-MM-DD.json`
- `data/ohlc/{SYMBOL}.json` - daily OHLC candle store (16 symbols, ~12 months of real open/high/low/close/volume). Powers MA20/50/200, RSI, ATR, and candlestick reads. Kept current by `scripts/collect_ohlc.py --update` in Step 1.
- `data/rolling_stats.json` - derived rolling track-record summary (read at Step 0)
- `data/psx.db` - derived, git-ignored query DB (rebuilt at Step 8 via `scripts/build_db.py --verify`)
- `rules/rules_library.md`
- `journal/YYYY-MM-DD.md`
- `reports/`

## Environment

- Python for this project runs from the project-local venv: `.venv\Scripts\python.exe`. Never install into the global interpreter; `.venv/` is git-ignored. Required packages: `requests`, `beautifulsoup4`, `pandas` (already installed).
- Playwright MCP `browser_*` tools collect live price/announcement data. Confirm they are connected at Step 0; if absent, stop (never fabricate).
- OHLC history does NOT need a browser: `scripts/collect_ohlc.py` uses `POST dps.psx.com.pk/historical` via plain `requests`. `--backfill --months N` rebuilds; `--update` appends today's bar idempotently (safe to re-run same day). It drops weekend/non-trading rows automatically.

## Command Routing

- `Run the PSX daily pipeline for today` -> follow `pipeline/daily_run.md`
- `Run the PSX weekly review` -> follow `pipeline/weekly_run.md`
- `Morning brief` -> use the lightweight brief in `pipeline/daily_run.md`
- `Analyze [TICKER]` -> apply `SKILL.md` to that stock and cite the data source

## Working Notes

The repository may contain uncommitted run outputs in `data/`, `journal/`, and `rules/`. Treat them as user or prior-agent work and do not revert them unless explicitly asked.

Data-quality note on the OHLC store: DGKC legitimately has ~240 bars vs ~244 for the other symbols — PSX has no DGKC bars on 2025-12-25, 2026-02-05, 2026-03-23, 2026-05-28 (the rest of the market traded those days). This is a real PSX data gap, not a scrape bug. Do not synthesize the missing bars.

Delegate mechanical grunt work (multi-symbol scraping, chart/HTML generation, bulk file edits) to cheaper sub-agents (Sonnet/Haiku), keeping the lead model for analysis and decisions. Note: sub-agents may be shell-permission-blocked in some sessions (they can write files but not execute) — in that case the lead runs the command.
