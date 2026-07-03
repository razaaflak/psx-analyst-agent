# run_state.md — carry-forward between runs (LOCAL source of truth)

**Purpose.** Single forward-pointer: where the last run left off + what the next run must do.
Replaces agent-private memory so ANY agent (Claude, Codex, …) resumes from the repo alone.
**Overwritten in full each run.** Latest-state only; history lives in `journal/` + the signal logs.

> Rule: if a fact matters to the NEXT run, it goes here or in another `data/` file — never only in agent memory.

---

## ⚠⚠ PROJECT PIVOTED 2026-06-24 — read this FIRST

**This is now a UNIVERSE-WIDE PREDICTION ENGINE, not a portfolio advisor.** The portfolio loop is REMOVED.

- **Goal:** an ensemble engine emitting a daily BUY/HOLD/SELL for ALL ~100 KSE-100 symbols, graded over months, feeding a future candlestick dashboard. Training project, NOT advice.
- **Engine = ENSEMBLE:** rule scorecard (`universe_signals.py`, LIVE) + ML model (`universe_model.py`, TO BUILD), blended by measured out-of-sample hit-rate.
- **Portfolio DROPPED.** Ahmad trades his EClear book himself. Legacy files FROZEN (do NOT write): `portfolio.json`, `trade_ledger.csv`, `predictions_log.csv` (we DO still grade out its open rows), `broker_intake.jsonl`.
- Memory: [[project_universe_engine_pivot]].

## 🟢 DAILY 2026-07-03 (Fri) — what changed this run
Full 6-step loop, plus a data-integrity fix carried over from the prior run's midnight-rollover mislabel. **No matured predictions this run — pure ingest + signal + filings run, no grading/learning event.**

- **Data-integrity fix (do this first if you see it again):** the previous run (labeled "2026-07-03" but started after PKT midnight while grading 07-02's close) wrote 100 signal rows stamped `2026-07-03` that were actually priced off 2026-07-02's close (HBL close 305.64, matching the 07-02 OHLC bar — NOT 07-03's real close of 305.91). This run relabeled those 100 rows to `2026-07-02` in `universe_signals.csv` (grade_on_date shifted 2026-07-10 → 2026-07-09, preserving the +5-trading-day horizon) and renamed `journal/2026-07-03.md` → `journal/2026-07-02.md` to match, BEFORE emitting the true 07-03 batch. **Lesson: after any run that spans PKT midnight, verify the OHLC store's last-bar date actually equals the intended run date before trusting `universe_signals.py`'s row-date stamp** — "idempotent, not a bug" only covers duplicate-run safety, not a wrong date label colliding with the next real day.
- **Step 1 ingest:** OHLC `--update` → all 101 symbols end **2026-07-03** (+1 NEW bar per symbol, GATE:PASS, 18 confirmed corp-action events, 0 new). Verified live: Playwright fetch of dps.psx.com.pk showed page timestamp "Jul 3, 2026 6:21 PM PKT", KSE100 185,372.20 — matches OHLC store's 185,372.21. Fundamentals refreshed. News 0 new (52 total). **KSE100 185,372.21 +0.46% — fresh ALL-TIME HIGH**, 5th straight up day. Brent ~$72.3 (+0.6%, US-Iran peace efforts cautiously holding, Gulf export supply caps upside ahead of US holiday weekend).
- **Step 1 filings:** 9 universe filings scraped; ALL read and cleared: EFERT (MATERIAL — Base plant unscheduled maintenance, ~4-day forced outage, noted not gated), SHFA+PPL (routine small insider buy/sell, <0.5% holdings), TRG×2 (SDNY declined injunctive relief re Chishti litigation — core 12-May ruling unaffected/on appeal, non-adverse; + JS Bank substantial-shareholder sale of 16.1M shares/16.47% cumulative — notable but routine 5.6.4 disclosure, GIF-only filing fixed via rename workaround), ATLH (corporate briefing notice), HMB (PACRA rating upgrade), THALL (routine FY27 budget approval), AGP (7th EOGM abstract — shareholders APPROVED the Scheme of Arrangement, still subject to Sindh HC sanction; same carryover event, content now accounted for, cleared pending HC sanction). **0 STALE at run end.**
- **Step 2 grade:** **nothing matured today** — universe 06-29 batch matures 2026-07-06 (3 days out), legacy P-039 matures 2026-07-07. Universe cumulative unchanged: 138/200 = 69.0% (2 batches). Legacy unchanged: 46 graded/39 HIT/84.8%, 1 open (P-039).
- **Step 3 learn:** no rule/model changes — zero new grading input this run (PD#5: never adjust on no evidence).
- **Step 4 signal:** true 07-03 batch emitted, 100 rows, **grade_on_date 2026-07-10** (verified against today's real OHLC — HBL close 305.91 matches). `dashboard_feed.json` rewritten: **BUY 33 / HOLD 65 / SELL 2 / STALE 0**. Notable: MEBL RSI 82.4 (52w 100%), FABL RSI 84.7 (52w 92%), DCR/ILP RSI 83-84 (overbought cluster deepens as melt-up extends to 5th session); SELL pair EFERT/PAEL (both EPS-falling+trend-breaking; EFERT now compounded by today's outage filing).
- **Step 6:** psx.db GATE:PASS (47 preds reconcile, 46 graded/39 hits/84.78%); rolling_stats + run_state rewritten.

## ⏭ NEXT-RUN MUST-DO
1. **2026-07-06: grade the 06-29 batch** (100 rows) — `collect_ohlc.py --update --universe` FIRST, then `grade_predictions.py --universe --asof 2026-07-06` (preview) → `--write`. **This is the 3rd universe batch — watch whether HOLD-breaks-UP repeats a 3rd time, and whether the regime has finally cracked (index at ATH, now 5 straight up sessions, very extended).**
2. **2026-07-07:** legacy P-039 (OGDC) matures — the last open legacy row. After this grades, ALL legacy predictions are closed out permanently (frozen file, no new legacy predictions will ever be issued).
3. **2026-07-08:** the 07-01 universe batch (100 rows) matures.
4. **2026-07-09:** the (relabeled) 07-02 universe batch (100 rows) matures.
5. **2026-07-10:** the 07-03 universe batch (100 rows, this run's output) matures.
6. **Fix the grade_predictions.py decision_quality evidence-string bug** found on P-043 (garbage placeholder "vs paper entry 100.0" instead of real close/entry comparison) — low priority since legacy predictions are winding down (only P-039 left), but worth a quick patch so the bug doesn't silently mis-grade P-039.
7. **Consider hardening `universe_signals.py`'s date handling** — e.g. warn/abort if `--date`-or-`today()` doesn't match the OHLC store's actual last-bar date, so a midnight-rollover mislabel gets caught automatically instead of silently writing a wrong-but-plausible date.

## 🔨 BUILD TODOs — remaining (priority order)
3. **Rebuild rule evidence from the UNIVERSE** — `rules/rules_library.md` still cites ~40 legacy PORTFOLIO grades. Still NOT enough universe batches (2, both same regime) — wait for several batches across ≥2 regimes, then recompute each rule's hit-rate across all symbols where it fired (psx.db query).
4. **Build `scripts/universe_model.py`** (ML classifier, SKILL.md H6) — features from stored ohlc+fundamentals, target = forward-return sign over H5, chronological 70/30 split, logistic/GBT, feature importances → `data/universe_model_signals.csv`, graded by same grader.
5. **Build the ensemble blend** (SKILL.md H7) → `data/universe_ensemble.csv`; rule-weighted until model has forward sample; ensemble graded.
6. **Extend `scripts/build_db.py`** to ingest the signal logs (universe/model/ensemble + grade columns); keep GATE:PASS row-count check. (Currently reconciles only legacy preds + trades.)
7. **fix `grade_predictions.py` decision_quality evidence-string bug** (see NEXT-RUN MUST-DO #6).
8. **Harden `process_filings.py` cache-write to detect image magic bytes and write the correct extension** (`.gif`/`.png` instead of trusting the URL's `.pdf` suffix) — hit 3 times now (KEL 06-30, RMPL/BOP 07-02, TRG 07-03), workaround (manual rename) is quick but should be automatic.
9. **NEW: harden `universe_signals.py` date handling** against midnight-rollover mislabels (see NEXT-RUN MUST-DO #7) — this run had to manually detect and fix a wrong date label after the fact.

## Engine state (as of 2026-07-03)
- **Rule scorecard LIVE.** 600 signal rows total (06-23, 06-24, 06-29, 07-01, 07-02, 07-03 ×100 each).
- **Universe hit-rate: 69.0% (200 graded, 2 batches).** BUY 79.4% / HOLD 64.1% / SELL 50% (n=4). Still single melt-up regime — honest but not yet trustworthy. 06-29 batch matures 07-06; 07-01 batch matures 07-08; 07-02 batch matures 07-09; 07-03 batch matures 07-10.
- **Legacy hand-preds (FROZEN):** 46 graded / 39 HIT / 84.8%. 1 open (P-039, grades 07-07 — the last legacy row ever).
- **ML model / ensemble:** not built (TODO #4/#5). Blend = 100% rule.
- **Data stores:** OHLC ends **2026-07-03** (101 symbols, adj, GATE:PASS); fundamentals 97/100; news 52.
- **Regime:** melt-up EXTENDED — KSE100 fresh ATH 185,372.21 (+0.46%), 5th straight up day, above all MAs. ⚠ Engine NEVER graded through a correction. Flip line: KSE100 close < MA20 = first out-of-regime test.

## Live watch (engine-relevant)
- **HOLD-breaks-UP asymmetry** — CONFIRMED twice (BUY ~79-81% vs HOLD ~64-65%, ~16pp gap, both batches). Still observation-only per PD#5; the 3rd batch (06-29, matures 07-06, 3 days out) is the next real test — if it survives a flat/red regime, tighten BUY threshold with evidence.
- **Oil:** Brent ~$72.3, +0.6% (US-Iran peace efforts cautiously holding, Gulf export supply caps upside ahead of US holiday weekend). R-EXP-003 falling-oil/E&P-drag last reconfirmed on P-044 (06-24 batch).
- **STALE (0):** AGP cleared this run (7th EOGM shareholders approved the Scheme of Arrangement, still pending Sindh HC sanction — watch for HC sanction news; will need re-review if/when sanctioned + fundamentals restated).
- **process_filings caveat (still true):** snapshot `pdf_url` MUST be absolute — relative paths break the downloader. Most PSX PDFs are image-only (no text layer) → title-keyword classify defaults STALE; agent must OPEN material/unknown PDFs and `--review` to clear. This run: 9/9 filings opened and cleared cleanly; 1 needed a manual `.gif` rename (see BUILD TODO #8, now 3rd occurrence).
- **Overbought in scorecard:** MEBL RSI 82.4 (52w 100%), FABL RSI 84.7 (52w 92%), DCR RSI 83.5, ILP RSI 83.6 — overbought cluster deepens as the melt-up extends to a 5th session. SELL pair: EFERT/PAEL (both EPS-falling + trend-breaking; EFERT also hit with a same-day Base-plant outage filing).
- **Legacy winding down:** only P-039 (OGDC, grades 07-07) remains open. Once graded, `predictions_log.csv` is permanently closed — no new legacy rows will ever be issued (portfolio loop is dropped).

## Legacy (FROZEN — context only, do NOT update in engine mode)
- Last portfolio book (2026-06-24, before freeze): 6 holdings FABL/FFC/LUCK/MEBL/OGDC/INDU + cash 155,804; equity 802,848. Ahmad runs this book himself.

## Notes for the next agent
- Start by reading: `CLAUDE.md`, `INSTRUCTIONS.md`, `SKILL.md` (Part H), `pipeline/daily_run.md`, this file, `rules/rules_library.md`.
- **Update OHLC FIRST, always**, so the grader has post-signal bars.
- Windows console: `PYTHONIOENCODING=utf-8` on every script.
- Rewrite this file at Step 6 of every run (latest-state only).

*Not financial advice. Training engine — output is a graded prediction, never a trade recommendation.*
