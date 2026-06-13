# AGENTS.md - Codex / Sub-Agent Project Context

This repository is the PSX Analyst Agent ("Urul"): a self-learning pipeline training toward becoming Ahmad's personal Pakistan Stock Exchange advisor with 30-year-practitioner-level judgment.

## Read First

Before any substantive run or analysis, read:

- `CLAUDE.md` — bootstrap contract, command routing, file map
- `INSTRUCTIONS.md` — identity, prime directives, readiness gates for advisory go-live
- `SKILL.md` — F/T/E analysis, scoring, risk caps, rule-graduation thresholds
- The relevant `pipeline/*.md` for the command given

## Ultimate Goal

Paper phase = training. Target: advise Ahmad which stock to buy/hold/increase%/decrease% based on real data, rules, and a compounding track record — contributing to actual profits. Ahmad executes; agent never places orders. Advisory switch flips only when readiness gates in `INSTRUCTIONS.md §1` honestly pass (n≥40-50 graded, hit≥60%, full cycle seen, ≥2-3 Core rules via live obs, drawdown survived, calibration verified).

## Hard Rules

- Paper trading only. Never place, imply, or recommend real orders.
- Not financial advice. End substantive outputs with the required reminder.
- Never fabricate market data. If verified data cannot be collected, skip the run.
- Data collection ladder: (1) plain Python requests, (2) Node.js Playwright script (`scripts/*.mjs`), (3) interactive Playwright MCP. Both Node.js and Playwright are installed system-wide.
- Playwright MCP `browser_*` tools collect live price/announcement data. Confirm connected at Step 0; if absent, stop.
- Keep predictions and ledgers append-only unless user explicitly asks for repair.
- No look-ahead when grading. Respect portfolio risk caps. No leverage. No averaging down on broken thesis.
- Read current state at start of each run; persist all updates at end.

## Key State Files

```
data/portfolio.json           — holdings + cash (read Step 0, write Step 6+8)
data/watchlist.json           — analysis universe with Shariah flags, face values
data/universe.json            — 100 KSE-100 constituents (--universe flag source)
data/trade_ledger.csv         — append-only paper trades
data/predictions_log.csv      — append-only predictions; graded columns filled in-place
data/rolling_stats.json       — DERIVED summary; rebuilt Step 8; read Step 0
data/psx.db                   — DERIVED query DB; git-ignored; rebuilt Step 8 via build_db.py --verify
data/market_data/YYYY-MM-DD.json — daily raw scrape snapshot + audit trail
data/ohlc/{SYMBOL}.json       — 101 symbols × 5yr OHLC (2021-07→); updated daily --update --universe
data/fundamentals/{SYMBOL}.json — 97/100 KSE-100; EPS/PAT/PBT + payout history
data/news_archive.jsonl       — forward-only E-lens news archive (grows from 2026-06-11)
rules/rules_library.md        — self-authored rulebook (4 Core-seed, 5 Experimental as of 2026-06-13)
```

## Key Scripts

```
scripts/collect_ohlc.py
  --update --universe          # daily: append today's bar for all 101 symbols
  --backfill --years 5 --universe  # fresh clone: backfill all (skip-if-exists by default)
  --backfill --years 5 --symbols A,B,C  # targeted backfill
  --force                      # re-fetch even if file exists

scripts/collect_fundamentals.py
  --universe                   # all KSE-100 (97/100 coverage; KEL/PSEL no filings)
  --watchlist                  # holdings + watchlist only
  --symbols OGDC,MCB           # specific

scripts/archive_news.py        # idempotent; appends macro_news from snapshots to news_archive.jsonl
scripts/build_db.py --verify   # rebuild psx.db; must print GATE:PASS before commit
scripts/backtest.py            # no-look-ahead rule validation; 70/30 chronological split
  --condition-search           # test conditional variants of rsi_oversold_bounce
  --rules golden_cross,rsi_oversold_bounce
  --symbols OGDC,PPL
```

## Backtest Engine — Honesty Contract

- **No look-ahead.** Signal at bar `t` reads only bars[0..t]. Outcomes measured bars[t+1..t+horizon].
- **Backtest-validated = pre-tier only.** Never substitutes for live Provisional/Core obs.
- **Chronological 70/30 split.** In-sample edge that collapses in holdout = coincidence.
- **Signal cooldown = horizon bars** per symbol (no overlapping windows).
- **E-lens rules excluded** — no historical news archive exists (news_archive.jsonl is forward-only from 2026-06-11).

First full backtest (2026-06-13, 101 symbols, 5yr):
- All 5 unconditional T-rules: coin-flip in holdout. No backtest-validated tier awarded.
- Condition-search finding: `rsi_oversold_bear_regime` (RSI<30 + KSE100<MA50) = **74.1% holdout** (n=54) — now R-EXP-005.

## Environment

- Python venv: `.venv\Scripts\python.exe`. Never use global interpreter.
- Node.js + Playwright installed system-wide. Write `scripts/*.mjs` for JS-rendered pages.
- OHLC source: `POST dps.psx.com.pk/historical {month,year,symbol}` — plain requests, no browser.
- Fundamentals source 1: `GET psx.com.pk/psx/announcement/financial-announcements` (raw HTML, no `<tbody>`).
- Fundamentals source 2: `POST dps.psx.com.pk/company/payouts {symbol=SYM}`.
- Face-value warning: PSX payouts are % of face value. UBL = Rs5 (post-2025 split), MTL = Rs5 (post-2026 split). Never assume Rs10.

## Command Routing

- `Run the PSX daily pipeline for today` → `pipeline/daily_run.md` (8 steps)
- `Run the PSX weekly review` → `pipeline/weekly_run.md`
- `Morning brief` → lightweight brief in `pipeline/daily_run.md`
- `Analyze [TICKER]` → `SKILL.md` per-stock card, cite data source
- `Run backtest` → `python scripts/backtest.py`
- `Condition search` → `python scripts/backtest.py --condition-search`

## Delegation Notes

Delegate mechanical grunt work to cheaper sub-agents (Sonnet/Haiku): multi-symbol scraping, bulk file edits, HTML parsing. Keep lead model (Opus) for analysis, rule judgments, and decisions. Sub-agents may be shell-permission-blocked in some sessions (can write files but not execute) — in that case the lead runs the command directly.

## Working Notes

- Repository may contain uncommitted run outputs in `data/`, `journal/`, `rules/`. Treat as user/prior-agent work; do not revert unless explicitly asked.
- DGKC legitimately has ~240 bars (PSX data gap on specific dates — real, not a scrape bug). Do not synthesize missing bars.
- `data/psx.db` is git-ignored (derived). Missing on fresh clone → run `python scripts/build_db.py --verify` first.
- `data/ohlc/` is git-tracked (101 files, ~5yr each). Missing → run `collect_ohlc.py --backfill --years 5 --universe`.
- CSVs are source of truth. If psx.db disagrees with CSV, CSVs win. Rebuild DB.
