# CLAUDE.md — PSX Universe Prediction Engine (Claude Code project context)

Claude Code loads this file automatically when this folder is opened. It is the operating contract. **Before doing anything, read `INSTRUCTIONS.md` and `SKILL.md` in full, plus `pipeline/daily_run.md`.**

## What this project is (PIVOTED 2026-06-24)
A **self-learning, universe-wide prediction engine for the Pakistan Stock Exchange.** Each run it collects real data for the whole KSE-100, emits a **BUY / HOLD / SELL signal for every one of the ~100 symbols**, grades its matured past signals with no look-ahead, and improves itself. The engine is an **ensemble**: a transparent **rule scorecard** + a trained **ML model**, both graded, blended by measured hit-rate. The eventual product is a **candlestick dashboard** (chart + indicators + support/resistance + current signal + history of past signals per symbol).

**This is a months-long TRAINING project, NOT a production advisory.** Engine output is a graded prediction, never a trade recommendation.

> **The portfolio loop is REMOVED.** Earlier versions advised on Ahmad's real EClear book (holdings, trades, allocation calls). As of 2026-06-24 (Ahmad's direction) that is gone — Ahmad manages his own trading separately. Legacy portfolio files (`portfolio.json`, `trade_ledger.csv`, `predictions_log.csv`, `broker_intake.jsonl`) are FROZEN historical artifacts — do not write to them. See memory [[project_universe_engine_pivot]].

## Trigger commands → what to do
- **"Run the PSX daily pipeline for today"** → follow `pipeline/daily_run.md` end-to-end (6 steps): ingest universe → grade matured signals → learn (rules + model + ensemble) → signal all ~100 → report → hand-off.
- **"Run the PSX weekly review"** → `pipeline/weekly_run.md` (out-of-sample rule/model review, regime-coverage + calibration audit).
- **"Analyze [TICKER]"** → show that symbol's engine signal + the per-factor math + its signal history; if Ahmad wants it actionable, run the Prime-Directive-#9 diligence gate first.

## Non-negotiable rules (full list in INSTRUCTIONS.md)
1. **Train across the WHOLE universe every run** — a signal for all ~100, not a subset.
2. **No look-ahead, ever.** Signal at date D reads bars ≤ D, graded on bars > D. ML split is chronological. Signals/grades append-only / fill-in-place.
3. **Graded, not trusted.** Every signal scored by `grade_predictions.py`; report the real hit-rate by predictor/rule/regime. Never inflate.
4. **Collect data automatically (Playwright MCP + scripts); never fabricate.** If verified data can't be had, skip and say so.
5. **Anti-overfitting is the cardinal discipline.** Graduation thresholds, multiple-comparisons discount, causal story required, judge the model out-of-sample.
6. **Transparency** — per-factor `why` on every rule signal; feature explanation on the model.
7. **Diligence gate (#9) survives** for any name ever escalated to actionable (open filings, verify earnings/dividend trend + face value, Shariah, catalysts; STALE names blocked).

## Environment notes
- **Playwright MCP configured at system level.** Confirm `browser_*` tools at run start; if absent, report and stop.
- **Node.js + Playwright installed system-wide** for JS-rendered/403 pages. Tool ladder: (1) plain Python requests, (2) Node Playwright script, (3) interactive Playwright MCP.
- Python venv: `.venv\Scripts\python.exe`. Never the global interpreter. Run scripts with `PYTHONIOENCODING=utf-8` (Windows console).
- Read/write inside this folder: `data/`, `rules/`, `journal/`, `reports/`. Read current state at start; persist all updates at end.

## File map
```
CLAUDE.md            ← this bootstrap (auto-loaded)
INSTRUCTIONS.md      ← full operating prompt / identity / engine spec / rules
SKILL.md             ← analysis method (Parts A–G) + the engine scorecard/ML/training (Part H)
pipeline/daily_run.md       ← daily 6-step engine-training procedure (canonical)
pipeline/data_collection.md ← Playwright MCP scraping spec
pipeline/weekly_run.md      ← weekend deep-dive (out-of-sample + calibration)

data/
  run_state.md              ← carry-forward hand-off (read Step 0, rewrite Step 6); engine state + build TODOs
  universe.json             ← 100 KSE-100 constituents (the training universe)
  universe_signals.csv      ← append-only RULE-scorecard signals, all ~100, 1 row/symbol/run; grader-scored
  universe_model_signals.csv← append-only ML-MODEL signals (TO BUILD)
  universe_ensemble.csv     ← append-only ENSEMBLE blend (TO BUILD)
  dashboard_feed.json       ← DERIVED per-symbol feed for the candlestick dashboard (rewritten each run)
  rolling_stats.json        ← DERIVED summary: hit-rate by predictor/rule/regime (rebuilt Step 6)
  psx.db                    ← DERIVED query DB (git-ignored; rebuilt Step 6)
  market_data/YYYY-MM-DD.json ← daily raw scrape snapshot (+ close screenshot)
  ohlc/{SYMBOL}.json        ← 101 symbols × 5yr real OHLC (adj for splits); updated daily
  fundamentals/{SYMBOL}.json← 97/100 KSE-100; EPS/PAT/PBT + payouts
  news_archive.jsonl        ← forward-only E-lens news archive
  [FROZEN legacy] portfolio.json, trade_ledger.csv, predictions_log.csv, broker_intake.jsonl

scripts/
  collect_ohlc.py           ← OHLC store: --update --universe (daily) | --backfill --years 5
  collect_fundamentals.py   ← fundamentals: --universe
  detect_corporate_actions.py / adjust_ohlc.py ← split/bonus continuity (GATE: PASS)
  archive_news.py           ← append macro_news to news_archive.jsonl
  universe_signals.py       ← RULE scorecard engine (LIVE; has a yield bug to fix)
  universe_model.py         ← ML model engine (TO BUILD)
  grade_predictions.py      ← no-look-ahead grader (TO EXTEND: must grade universe_signals.csv)
  backtest.py               ← no-look-ahead validator / condition-search (rule-weight derivation, model pre-train)
  build_db.py               ← rebuild psx.db; --verify gate must print GATE:PASS (TO EXTEND: ingest signal logs)
  queries.md                ← named SQL queries for psx.db

rules/rules_library.md      ← self-authored rulebook (evidence TO REBUILD from universe outcomes)
journal/                    ← dated run entries
reports/                    ← weekly reports + reports/backtests/
```

## Active build TODOs (the pivot is docs-complete; code work is next — see run_state.md)
1. **Extend `grade_predictions.py` to grade `universe_signals.csv`** (the key gap — universe is currently ungraded).
2. **Fix the `universe_signals.py` yield bug** (%-of-face-value conversion; INDU showed 2.93% vs real ~9.5%).
3. **Rebuild rule evidence from universe outcomes** (rules currently cite ~30 legacy portfolio grades).
4. **Build `scripts/universe_model.py`** (ML classifier) + ensemble blend + grading for both.
5. **Extend `build_db.py`** to ingest the signal logs.

Start every run by reading the state files. End by persisting updates and writing the journal entry.
