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
- `rules/rules_library.md`
- `journal/YYYY-MM-DD.md`
- `reports/`

## Command Routing

- `Run the PSX daily pipeline for today` -> follow `pipeline/daily_run.md`
- `Run the PSX weekly review` -> follow `pipeline/weekly_run.md`
- `Morning brief` -> use the lightweight brief in `pipeline/daily_run.md`
- `Analyze [TICKER]` -> apply `SKILL.md` to that stock and cite the data source

## Working Notes

The repository may contain uncommitted run outputs in `data/`, `journal/`, and `rules/`. Treat them as user or prior-agent work and do not revert them unless explicitly asked.
