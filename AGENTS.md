# AGENTS.md - Codex / Sub-Agent Project Context

> **⚠ PIVOT 2026-06-24 (Ahmad's direction).** This repository is now a **universe-wide PSX prediction engine** being trained over all ~100 KSE-100 symbols. The old "PSX analyst / portfolio advisor (Urul)" framing is RETIRED — the portfolio loop is removed; Ahmad trades his own EClear book separately. Engine output is a graded prediction, NOT advice.

This repository trains a **self-learning, universe-wide prediction engine** for the Pakistan Stock Exchange: each run it emits a BUY/HOLD/SELL signal for every ~100 KSE-100 symbol, grades matured past signals with no look-ahead, and improves itself. The engine is an **ensemble** — a transparent rule scorecard + a trained ML model, blended by measured hit-rate. Months-long training project feeding a future candlestick dashboard.

## Read First

Before any substantive run, read:
- `CLAUDE.md` — bootstrap contract, command routing, file map, build TODOs
- `INSTRUCTIONS.md` — identity, engine spec, prime directives
- `SKILL.md` — analysis lenses (Parts A–G) + the engine scorecard/ML/ensemble/training (Part H)
- `data/run_state.md` — current engine state + active BUILD TODOs (do these in order)
- The relevant `pipeline/*.md` for the command given

## Goal

A daily BUY/HOLD/SELL signal for **every** ~100 KSE-100 symbol, graded over months, so the engine's rules + ML model are trained and measured across the whole universe and across regimes. Feeds a candlestick dashboard (chart + indicators + support/resistance + current signal + history of past signals). **Training, not production advice** — never auto-executed, never a trade recommendation. The portfolio is gone (Ahmad trades separately).

## Hard Rules

- Train across the WHOLE universe every run — a signal for all ~100, not a subset.
- No look-ahead, ever. Signal at date D reads bars ≤ D, graded on bars > D; ML split is chronological. Signals/grades append-only / fill-in-place.
- Graded, not trusted. Every signal scored by `grade_predictions.py`; report real hit-rate by predictor/rule/regime; never inflate.
- Never fabricate market data. If verified data can't be collected, skip the run.
- Data collection ladder: (1) plain Python requests, (2) Node.js Playwright script (`scripts/*.mjs`), (3) interactive Playwright MCP. Confirm `browser_*` connected at Step 0; if absent, stop.
- Anti-overfitting is cardinal: graduation thresholds on universe-wide+multi-regime samples, multiple-comparisons discount, causal story required, judge the ML model out-of-sample only.
- Transparency: per-factor `why` on every rule signal; feature explanation on the model.
- Diligence gate (#9) survives for any name ever escalated to actionable (open filings, verify earnings/dividend trend + face value, Shariah, catalysts; STALE names blocked). The engine's auto-yield is screen-grade and has been WRONG — never trust it for an actionable call.
- Read current state at start of each run; persist all updates at end.
- **Legacy portfolio files are FROZEN** — do NOT write to `portfolio.json`, `trade_ledger.csv`, `predictions_log.csv`, `broker_intake.jsonl`. Keep as audit history. No broker-intake step, no trade step.

## Key State Files

```
data/run_state.md             — carry-forward hand-off + BUILD TODOs (read Step 0, rewrite Step 6)
data/universe.json            — 100 KSE-100 constituents (the training universe)
data/universe_signals.csv     — append-only RULE-scorecard signals, all ~100, 1 row/symbol/run; grader-scored
data/universe_model_signals.csv — append-only ML-MODEL signals (TO BUILD)
data/universe_ensemble.csv    — append-only ENSEMBLE blend (TO BUILD)
data/dashboard_feed.json      — DERIVED per-symbol dashboard feed; rewritten each run
data/rolling_stats.json       — DERIVED summary: hit-rate by predictor/rule/regime; rebuilt Step 6
data/psx.db                   — DERIVED query DB; git-ignored; rebuilt Step 6 via build_db.py --verify
data/market_data/YYYY-MM-DD.json — daily raw scrape snapshot + close screenshot
data/ohlc/{SYMBOL}.json       — 101 symbols × 5yr OHLC (adj for splits); updated daily --update --universe
data/fundamentals/{SYMBOL}.json — 97/100 KSE-100; EPS/PAT/PBT + payout history
data/news_archive.jsonl       — forward-only E-lens news archive
rules/rules_library.md        — self-authored rulebook (evidence TO REBUILD from universe outcomes)
[FROZEN legacy] data/portfolio.json, data/trade_ledger.csv, data/predictions_log.csv, data/broker_intake.jsonl, data/watchlist.json
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

scripts/universe_signals.py    # ✅ LIVE — RULE scorecard engine (predictor #1)
  # Deterministic BUY/HOLD/SELL + conviction 1-3 for ALL ~100 KSE-100 from stored ohlc/+fundamentals/
  # via SKILL.md Part-H scorecard (per-factor math). Appends 1 row/symbol/run to universe_signals.csv;
  # writes dashboard_feed.json; flags diligence=STALE on new filings. No network. Training, NOT advice.
  # ⚠ KNOWN BUG: yield_pct mis-computed for high-%-payout names (%-of-face-value, R-EXP-002) — FIX.

scripts/universe_model.py      # 🔨 TO BUILD — ML model engine (predictor #2, SKILL.md H6)
  # Trained classifier; features from ohlc+fundamentals; target = forward-return sign over H5 horizon;
  # chronological 70/30 split on 5yr×101; logistic/GBT first; feature importances exposed.
  # -> data/universe_model_signals.csv, graded by grade_predictions.py. Then ensemble blend (H7).

scripts/grade_predictions.py   # no-look-ahead grader
  # ⚠ TO EXTEND: currently grades ONLY predictions_log.csv. Must grade universe_signals.csv (+ model/
  #   ensemble): BUY->close>ref, SELL->close<ref, HOLD->within ±band (SKILL.md H5). Reuse
  #   grade_higher_than_ref / bars_in_window. THE #1 build TODO — universe is UNGRADED until done.
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

- `Run the PSX daily pipeline for today` → `pipeline/daily_run.md` (6 steps: ingest universe → grade → learn → signal all 100 → report → hand-off)
- `Run the PSX weekly review` → `pipeline/weekly_run.md` (out-of-sample rule/model review + calibration)
- `Analyze [TICKER]` → show the engine signal + per-factor math + signal history; run #9 diligence first only if escalating to actionable
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
