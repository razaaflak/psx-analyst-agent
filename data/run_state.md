# run_state.md — carry-forward between runs (LOCAL source of truth)

**Purpose.** Single forward-pointer: where the last run left off + what the next run must do.
Replaces agent-private memory so ANY agent (Claude, Codex, …) resumes from the repo alone.
**Overwritten in full each run.** Latest-state only; history lives in `journal/` + the signal logs.

> Rule: if a fact matters to the NEXT run, it goes here or in another `data/` file — never only in agent memory.

---

## ⚠⚠ PROJECT PIVOTED 2026-06-24 — read this FIRST

**This is now a UNIVERSE-WIDE PREDICTION ENGINE, not a portfolio advisor.** Ahmad's direction: "forget about portfolio… train this pipeline on the full list of symbols… a defined prediction engine, intelligent rule-based, tested trained." The portfolio loop is REMOVED.

- **Goal:** an ensemble engine that emits a daily BUY/HOLD/SELL for ALL ~100 KSE-100 symbols, graded over months, feeding a future candlestick dashboard. Training project, NOT advice.
- **Engine = ENSEMBLE:** rule scorecard (`universe_signals.py`, LIVE) + ML model (`universe_model.py`, TO BUILD), blended by measured out-of-sample hit-rate.
- **Portfolio DROPPED.** Ahmad trades his EClear book himself, outside this pipeline. Legacy files FROZEN (do NOT write): `portfolio.json`, `trade_ledger.csv`, `predictions_log.csv`, `broker_intake.jsonl`. Keep them as audit history.
- Memory: [[project_universe_engine_pivot]] (supersedes [[project_universe_engine_direction]]).

## 🟢 WEEKEND 2026-06-28 (W26) — what changed this run
Ran the weekend review in ENGINE mode (the portfolio-era `weekly_run.md` steps are N/A). Two of the
six build TODOs are now closed:

- **TODO #1 — universe grader: BUILT + VERIFIED ✅.** Extended `scripts/grade_predictions.py` with
  `grade_universe()` / `grade_universe_row()` / `atr14_at()` + CLI flags `--universe` and `--write`.
  Per SKILL.md H5, no look-ahead, adjusted-close basis: BUY = any in-window close > signal-date close;
  SELL = any close < it; HOLD = every close within ±1×ATR14 (±3% fallback). Writes `status`→`graded`
  and the grade into the **`result`** column only — issued `why` and all issued fields immutable;
  defaults to dry run, `--write` persists. Verified: `--asof 2026-06-28` → 0 matured (correct);
  `--asof 2026-07-01` preview → grades only the 06-23 batch (has post-signal bars), returns NEEDS-DATA
  for 06-24 (no bars after yet). CSV confirmed untouched by the dry runs. Wired into `daily_run.md` Step 2.
- **TODO #2 — "yield bug": CLOSED, was a MISDIAGNOSIS ✅.** The `2.93` that triggered it was the
  **`mom20`** column being read as `yield_pct`. Yields are already face-value-correct
  (INDU 11.98%, FFC 8.14%, OGDC 5.59%, FATIMA 6.28%, UBL 8.47%). No code change; the daily_run yield
  warning was corrected. Memory [[project_universe_engine_pivot]] should be updated to reflect both.

## 🔨 BUILD TODOs — remaining (priority order)
3. **Rebuild rule evidence from the UNIVERSE** — `rules/rules_library.md` still cites ~30 legacy
   PORTFOLIO predictions. NOW UNBLOCKED (grader exists). Once a real graded universe sample accrues
   (≥06-30), recompute each rule's hit-rate across ALL symbols where it fired (psx.db query).
4. **Build `scripts/universe_model.py`** (ML classifier, SKILL.md H6) — features from stored
   ohlc+fundamentals, target = forward-return sign over the H5 horizon, chronological 70/30 split,
   logistic/GBT first, feature importances → `data/universe_model_signals.csv`, graded by the same grader.
5. **Build the ensemble blend** (SKILL.md H7) → `data/universe_ensemble.csv`; rule-weighted until the
   model has a forward sample; ensemble itself graded.
6. **Extend `scripts/build_db.py`** to ingest the signal logs (universe/model/ensemble + grade columns);
   keep the GATE:PASS row-count check.

## ⏭ NEXT-RUN MUST-DO (the grader is ready; feed it)
1. **`collect_ohlc.py --update --universe`** — OHLC store ends **2026-06-24**; the 06-30/07-01 grades
   need the post-signal bars. Without fresh bars the grader correctly returns NEEDS-DATA and grades nothing.
2. On/after **2026-06-30**: `grade_predictions.py --universe --asof <today>` (preview), then `--write`
   → the FIRST real graded universe sample (06-23 batch). Repeat 2026-07-01 for the 06-24 batch.
3. ⚠ Do NOT read the W26 preview's "80%" as a result — it was a 1-session window, never written.

## Engine state (as of 2026-06-28, weekend W26)
- **Rule scorecard LIVE.** 200 signal rows (06-23, 06-24 × 100), **all `status=open`**.
- **Universe hit-rate: 0 graded (UNGRADED — honest).** Grader now WIRED but no rows matured with bars
  yet. First real grades land once OHLC is updated past the grade dates.
- **ML model / ensemble:** not built (TODO #4/#5).
- **Data stores:** OHLC ends **2026-06-24** (101 symbols, adj, GATE:PASS); fundamentals 97/100;
  news_archive ~52 items. OHLC must be `--update`d next run.
- **KSE-100 backdrop (regime):** still the single **melt-up** regime since ~06-09 — above MA20/50/200,
  RSI elevated. ⚠ The engine has NOT seen a sustained correction; regime-stratified grading (H5) is
  essential before trusting anything. Watch the flip line: KSE100 close < MA20 = first out-of-regime test.

## Live watch (engine-relevant)
- **Oil:** Brent ~$76, sinking toward $75 (US-Iran peace + Iran sell license). Falling-oil = relative
  E&P drag hypothesis (R-EXP-003) — a regime feature worth encoding for the model.
- **STALE discipline:** Step-1 must set `diligence=STALE` on any symbol with a new filing so the engine
  never treats stale fundamentals as current (JDWS protection).

## Legacy (FROZEN — context only, do NOT update in engine mode)
- Last portfolio book (2026-06-24, before freeze): 6 holdings FABL/FFC/LUCK/MEBL/OGDC/INDU + cash 155,804;
  equity 802,848; legacy track record 30 graded/26 HIT/4 MISS = 86.7% (PORTFOLIO predictions — NOT a
  universe metric). Ahmad runs this book himself.

## Notes for the next agent
- Start by reading: `CLAUDE.md`, `INSTRUCTIONS.md`, `SKILL.md` (Part H), `pipeline/daily_run.md`, this file, `rules/rules_library.md`.
- The grader is the unblocker and it's DONE — next run's job is to FEED it (update OHLC, then grade with `--write` once matured).
- Windows console: `PYTHONIOENCODING=utf-8` on every script.
- Rewrite this file at Step 6 of every run (latest-state only).

*Not financial advice. Training engine — output is a graded prediction, never a trade recommendation.*
