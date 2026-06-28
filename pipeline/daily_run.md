# pipeline/daily_run.md — The Daily Engine-Training Run (exact steps)

**Trigger phrase:** "Run the PSX daily pipeline for today."
**When:** after 5:00 PM PKT on a PSX trading day (after EOD data settles). Skip weekends/holidays.
**Read first:** `INSTRUCTIONS.md`, `SKILL.md` (esp. Parts D & H), and `rules/rules_library.md`.

> **⚠ PIVOT 2026-06-24.** This is the **universe prediction engine** loop. The old portfolio loop (broker intake, analyze holdings, decide, trade, predict-for-the-book) is REMOVED. The pipeline now: ingest the whole universe → grade matured signals → learn (rules + model) → emit signals for all ~100 → report → hand off. No portfolio, no trades.

Follow these 6 steps in order. Persist all file changes at the end.

---

## Step 0 — Setup & guardrails
- Confirm today is a PSX trading day. If not, say so and offer the weekly review.
- Load `rules/rules_library.md`, `data/rolling_stats.json`, and **`data/run_state.md`** (the carry-forward hand-off — engine state, open signals due to grade today, build TODOs). The authoritative numbers live in the signal logs / `psx.db`; run_state is the quick map.
- **Ensure infra exists** (fresh-clone safe):
  - `data/psx.db` (git-ignored, derived) — if missing: `python scripts/build_db.py --verify` (must print `GATE: PASS`).
  - OHLC store `data/ohlc/{SYMBOL}.json` (101 symbols, 5yr) — if missing/short: `.venv\Scripts\python.exe scripts/collect_ohlc.py --backfill --years 5 --universe`.
  - Fundamentals `data/fundamentals/{SYM}.json` — if missing: `.venv\Scripts\python.exe scripts/collect_fundamentals.py --universe`.
- Confirm the **Playwright MCP** server is connected. If not, report and stop (ingest depends on it).
- State today's date, the active rules (count by tier), and the engine's current rolling hit-rate by predictor.

## Step 1 — INGEST the whole universe (automated — no manual paste)
- **Scrape today's official EOD via Playwright MCP** from `dps.psx.com.pk`:
  - KSE-100 close, points/%, total volume/value, breadth (the regime backdrop).
  - Company announcements (results / material info / board meetings). **For every NEW filing, set the symbol's `diligence=STALE` for this run** so the engine knows its stored fundamentals may be stale and its content unread (the JDWS protection). dps is the ONLY live-disclosure source.
- **Update the OHLC candle store:** `.venv\Scripts\python.exe scripts/collect_ohlc.py --update --universe` — appends today's true OHLC bar for all 101 symbols (idempotent). Source = `POST dps.psx.com.pk/historical` (plain requests). If `--update` fails, note it and fall back to the close-only feed; don't block.
- **Scan + apply corporate actions:** `--update` auto-runs `scripts/detect_corporate_actions.py`; if a NEW split/bonus is flagged, verify vs PSX filings, then `.venv\Scripts\python.exe scripts/adjust_ohlc.py --confirm-all --verify` (must print **GATE: PASS** — no residual >30% cliff). All consumers read `adj_close or close`, so MA/RSI/ATR stay continuous across splits.
- **Refresh fundamentals:** `.venv\Scripts\python.exe scripts/collect_fundamentals.py --universe` — merges quarterly EPS/PAT/PBT + payout history for all KSE-100 names (idempotent). **Face-value warning:** payout `pct` is % of face value — convert with CURRENT face value (R-EXP-002). The engine's auto-yield is face-value-correct (verified 2026-06-28: INDU 11.98%, FFC 8.14%, OGDC 5.59% — the old "yield bug" was a momentum-vs-yield column misread, not a bug).
- **Archive news + capture oil/macro:** `.venv\Scripts\python.exe scripts/archive_news.py` (forward-only E-lens history); fetch Brent/oil + key macro for the regime read.
- Write the raw snapshot to `data/market_data/YYYY-MM-DD.json` (+ close screenshot). **Note:** `announcements` should be a **list of `{symbol,...}` rows** so the engine can read STALE flags; on a no-filing day a descriptive object is tolerated (the engine handles both). State the data rung + a confidence note. If every automated path fails, skip the run — never fabricate.

## Step 2 — GRADE matured signals (the learning input)
- Find matured rows via `psx.db` / the signal logs: `status='open' AND grade_on_date <= today` — for BOTH `data/predictions_log.csv` (legacy hand predictions, still grade out the open ones) AND `data/universe_signals.csv` (the engine corpus) AND (once built) the model/ensemble logs.
- **Run the deterministic grader (legacy preds):** `.venv\Scripts\python.exe scripts/grade_predictions.py --asof <today>` — proposes mechanical HIT/MISS for the open `predictions_log.csv` rows (frozen legacy; still grade them out).
- **Grade the universe (WIRED 2026-06-28):** `.venv\Scripts\python.exe scripts/grade_predictions.py --universe --asof <today> --write`. Reads the raw OHLC store, bars strictly after the signal date through `grade_on_date` (no look-ahead), on the adjusted-close basis. BUY = any in-window close > signal-date close; SELL = any in-window close < it; HOLD = every close within ±1×ATR14 (±3% fallback). Writes `status`→`graded` and the grade into the `result` column only (issued `why`/all issued fields immutable). **Preview without `--write` first; only `--write` when the OHLC store actually has bars after the signal date** — otherwise it correctly returns NEEDS-DATA and grades nothing. First real grades: 06-23 batch matures 2026-06-30, 06-24 batch 2026-07-01.
- Write grades back into the signal logs (fill only the grading columns: `status,result,why`; never edit the issued signal). Do not edit `psx.db` directly — it rebuilds from the CSVs at Step 6.
- Produce a grading summary: how many graded, **rolling hit-rate by predictor (rule / model / ensemble) and by rule and by regime**, biggest miss + likely cause (data / model / noise).

## Step 3 — LEARN (improve the engine)
- For each miss/partial across the universe: **data** problem (bad input), **model** problem (a rule/feature/the ML model misfired), or **noise** (genuinely unpredictable)? Only model problems change the engine.
- **Rules:** propose changes per SKILL.md Part D, now on **universe-wide** samples (the honest multi-symbol/multi-regime bar):
  - new pattern → **Experimental** (causal story required, 0 weight);
  - rule that hit again across symbols → increment evidence; promote if thresholds met (≥8/≥60% Provisional; ≥20/≥65%/out-of-sample Core);
  - failing rule → demote/Retire. Base promote/demote on per-rule hit-rate queried from `psx.db` across ALL symbols where the rule fired.
  - **Rebuild rule evidence from the universe, not the old portfolio grades** (build TODO: R-001..R-EXP-006 currently cite ~30 portfolio predictions; recompute each from universe outcomes).
- **ML model:** re-evaluate forward-graded performance; re-fit on the expanded history if scheduled (chronological split, no look-ahead). Judge on out-of-sample forward hit-rate + calibration, never training accuracy.
- **Ensemble blend:** adjust the rule-vs-model weight toward whichever has the better measured out-of-sample, multi-regime hit-rate. Log the blend weight + why.
- Keep the active (Provisional+Core) rule library ≤ ~30. Respect anti-overfitting (Prime Directive #5).

## Step 4 — SIGNAL the whole universe (the engine output)
- **Run the rule scorecard:** `python scripts/universe_signals.py` (no network — reads stored OHLC + fundamentals). For every KSE-100 symbol it emits BUY/HOLD/SELL + screen-grade conviction (1–3) + support/resistance + the `diligence` flag (STALE from Step 1), showing per-factor math. Appends one row/symbol to `data/universe_signals.csv`; sets each row's `grade_on_date`.
- **Run the ML model** (once built): `python scripts/universe_model.py` → per-symbol BUY/HOLD/SELL + probability, appended to `data/universe_model_signals.csv` with feature explanation.
- **Compute the ensemble** (once built): blend rule + model per the current weight → `data/universe_ensemble.csv`.
- **Write `data/dashboard_feed.json`** (DERIVED, rewritten each run): per symbol — latest OHLC ref, each predictor's signal + conviction/prob, the ensemble, MA20/50/200, RSI, support/resistance, the diligence flag, and a pointer to that symbol's signal HISTORY (so the candlestick dashboard overlays past signals on the candles and shows how right they were).
- **No actionable calls here.** A signal is a graded prediction, not advice. If Ahmad asks to escalate a specific name to actionable, that triggers the Prime-Directive-#9 diligence gate separately — never while `diligence=STALE`.

## Step 5 — REPORT (the run journal)
- Write `journal/YYYY-MM-DD.md`: run header (date, data source/confidence, KSE-100 backdrop + regime read); the **grading scoreboard** (counts graded today; rolling hit-rate by predictor / top rules / regime; biggest miss + cause); rule/model/ensemble changes made; the **universe signal summary** (BUY/HOLD/SELL counts, notable extremes, any STALE names); the footer (engine-health one-liner + the single most important watch item + the not-advice reminder).
- Lead with a 5-line TL;DR: regime in one line, engine signal summary, rolling hit-rate by predictor, what changed, the key engine-health risk.

## Step 6 — HAND-OFF (persist + rewrite carry-forward)
- **Regenerate `data/rolling_stats.json`**: counts + rolling hit-rate **by predictor / rule / regime**, open-signals-by-grade-date, active-rule counts by tier, ensemble blend weight, `as_of_date`. Keep `sample_too_small: true` until the universe sample is large AND multi-regime AND calibrated. DERIVED — CSVs win on conflict.
- **Rebuild `data/psx.db`**: `python scripts/build_db.py --verify` (must print `GATE: PASS`; the verify gate confirms DB rows == CSV data rows). Build TODO: extend `build_db.py` to ingest the universe/model/ensemble signal logs so they are queryable.
- **Rewrite `data/run_state.md`** (latest-state only, overwrite): engine state, rolling hit-rate by predictor, open signals due next run + grade dates, active build TODOs, live watch items. This is what lets any agent resume the engine from the repo alone.
- Note: legacy portfolio files (`portfolio.json`, `trade_ledger.csv`, `broker_intake.jsonl`) are FROZEN — not updated by this loop. Keep them as historical artifacts; do not delete (audit trail), do not write to them.

---

### Optional: weekly deep-dive
See `pipeline/weekly_run.md` — the out-of-sample rule/model review, regime-coverage audit, and calibration check. (To be re-aligned to engine mode.)
