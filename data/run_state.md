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

## 🟢 DAILY 2026-07-03 (Fri, run started after PKT midnight, grading last close 2026-07-02) — what changed this run
Full 6-step loop. **No matured predictions this run (both next grade dates still ahead) — pure ingest + signal + filings run, no grading/learning event.**

- **Step 1 ingest:** OHLC `--update` → all 101 symbols end **2026-07-02** (+1 bar, GATE:PASS, 18 confirmed corp-action events, 0 new). Fundamentals refreshed (KEL/PSEL name-map gap persists, non-blocking). News 0 new (52 total). **KSE100 184,520.96 +0.26% — fresh ALL-TIME HIGH**, 4th straight up day. Brent ~$71.56 (flat/soft; Iran-US indirect mediation only, no direct talks).
- **Step 1 filings:** 12 universe filings scraped; ALL read and cleared to OK: BOP (PACRA entity-rating upgrade), NPL+DGKC+RMPL (outbound RMPL stake acquisition — same Nishat-group/Ingredion event as prior runs; NPL bought 14.36%, DGKC bought 31.07%, both Rs9800/share 2026-06-23; RMPL's own Reg 5.6.4 filing gave the underlying insider-transaction detail), POWER (routine CFO appointment), MUREB (routine EOGM notice), MEBL/AKBL/BOP-2nd (routine exec share transactions, all <0.02% of holding), PTC×2 (CEO changed twice same day — interim 14-day appointment, procedural not financial), FABL (routine board-meeting template, already known-clean). **Only AGP remains STALE** (Scheme of Arrangement, pending Sindh HC — unchanged carryover).
- **Technique gap found:** RMPL/BOP filings were GIF images served under a `.pdf`-suffixed attachment URL (real GIF magic bytes, no `%PDF-` header) — `Read` fails until the cached file is renamed `.gif`. Same pattern as the 2026-06-30 KEL case. Worth automating into `process_filings.py`'s cache-write step (detect magic bytes → write correct extension) — not urgent, workaround is quick.
- **Step 2 grade:** **nothing matured today** — universe 06-29 batch matures 2026-07-06 (3 days out), legacy P-039 matures 2026-07-07. Universe cumulative unchanged: 138/200 = 69.0% (2 batches). Legacy unchanged: 46 graded/39 HIT/84.8%, 1 open (P-039).
- **Step 3 learn:** no rule/model changes — zero new grading input this run (PD#5: never adjust on no evidence).
- **Step 4 signal:** new batch emitted, 100 rows, **grade_on_date 2026-07-10** (clock rolled past PKT midnight mid-run → rows stamped 2026-07-03, confirmed not a bug). `dashboard_feed.json` rewritten: **BUY 31 / HOLD 66 / SELL 3 / STALE 1 (AGP)**. Notable: MEBL RSI 80.9 (52w 99.5%, still HOLD not BUY), AICL/DCR/ILP/HINOON RSI 79-85 (blow-off-reversal candidates as the melt-up extends to a 4th session); SELL trio unchanged pattern (EFERT/IBFL/PAEL, all EPS-falling+trend-breaking).
- **Step 6:** psx.db GATE:PASS (47 preds reconcile, 46 graded/39 hits/84.78%); rolling_stats + run_state rewritten.

## ⏭ NEXT-RUN MUST-DO
1. **2026-07-06: grade the 06-29 batch** (100 rows) — `collect_ohlc.py --update --universe` FIRST, then `grade_predictions.py --universe --asof 2026-07-06` (preview) → `--write`. **This is the 3rd universe batch — watch whether HOLD-breaks-UP repeats a 3rd time, and whether the regime has finally cracked (index at ATH, now 4 straight up sessions, very extended).**
2. **2026-07-07:** legacy P-039 (OGDC) matures — the last open legacy row. After this grades, ALL legacy predictions are closed out permanently (frozen file, no new legacy predictions will ever be issued).
3. **2026-07-08:** the 07-01 universe batch (100 rows) matures.
4. **2026-07-10:** the 07-03 universe batch (100 rows, this run's output) matures.
5. **Fix the grade_predictions.py decision_quality evidence-string bug** found on P-043 (garbage placeholder "vs paper entry 100.0" instead of real close/entry comparison) — low priority since legacy predictions are winding down (only P-039 left), but worth a quick patch so the bug doesn't silently mis-grade P-039.

## 🔨 BUILD TODOs — remaining (priority order)
3. **Rebuild rule evidence from the UNIVERSE** — `rules/rules_library.md` still cites ~40 legacy PORTFOLIO grades. Still NOT enough universe batches (2, both same regime) — wait for several batches across ≥2 regimes, then recompute each rule's hit-rate across all symbols where it fired (psx.db query).
4. **Build `scripts/universe_model.py`** (ML classifier, SKILL.md H6) — features from stored ohlc+fundamentals, target = forward-return sign over H5, chronological 70/30 split, logistic/GBT, feature importances → `data/universe_model_signals.csv`, graded by same grader.
5. **Build the ensemble blend** (SKILL.md H7) → `data/universe_ensemble.csv`; rule-weighted until model has forward sample; ensemble graded.
6. **Extend `scripts/build_db.py`** to ingest the signal logs (universe/model/ensemble + grade columns); keep GATE:PASS row-count check. (Currently reconciles only legacy preds + trades.)
7. **fix `grade_predictions.py` decision_quality evidence-string bug** (see NEXT-RUN MUST-DO #5).
8. **NEW: harden `process_filings.py` cache-write to detect image magic bytes and write the correct extension** (`.gif`/`.png` instead of trusting the URL's `.pdf` suffix) — hit twice now (KEL 06-30, RMPL/BOP 07-02), workaround (manual rename) is quick but should be automatic.

## Engine state (as of 2026-07-02)
- **Rule scorecard LIVE.** 500 signal rows total (06-23, 06-24, 06-29, 07-01, 07-03 ×100 each).
- **Universe hit-rate: 69.0% (200 graded, 2 batches).** BUY 79.4% / HOLD 64.1% / SELL 50% (n=4). Still single melt-up regime — honest but not yet trustworthy. 06-29 batch matures 07-06; 07-01 batch matures 07-08; 07-03 batch matures 07-10.
- **Legacy hand-preds (FROZEN):** 46 graded / 39 HIT / 84.8%. 1 open (P-039, grades 07-07 — the last legacy row ever).
- **ML model / ensemble:** not built (TODO #4/#5). Blend = 100% rule.
- **Data stores:** OHLC ends **2026-07-02** (101 symbols, adj, GATE:PASS); fundamentals 97/100; news 52.
- **Regime:** melt-up EXTENDED — KSE100 fresh ATH 184,520.96 (+0.26%), 4th straight up day, above all MAs. ⚠ Engine NEVER graded through a correction. Flip line: KSE100 close < MA20 = first out-of-regime test.

## Live watch (engine-relevant)
- **HOLD-breaks-UP asymmetry** — CONFIRMED twice (BUY ~79-81% vs HOLD ~64-65%, ~16pp gap, both batches). Still observation-only per PD#5; the 3rd batch (06-29, matures 07-06, 3 days out) is the next real test — if it survives a flat/red regime, tighten BUY threshold with evidence.
- **Oil:** Brent ~$71.56, flat/soft (Iran-US indirect mediation only, no direct talks). R-EXP-003 falling-oil/E&P-drag last reconfirmed on P-044 (06-24 batch).
- **STALE (1): AGP** (Scheme of Arrangement, pending Sindh HC sanction; clears via `process_filings.py --review AGP` once sanctioned + restated fundamentals).
- **process_filings caveat (still true):** snapshot `pdf_url` MUST be absolute — relative paths break the downloader. Most PSX PDFs are image-only (no text layer) → title-keyword classify defaults STALE; agent must OPEN material/unknown PDFs and `--review` to clear. This run: 12/12 filings opened and cleared cleanly; 2 needed a manual `.gif` rename (see BUILD TODO #8).
- **Overbought in scorecard:** MEBL RSI 80.9 (52w 99.5%, still HOLD not BUY per screen-grade), AICL/DCR/ILP/HINOON RSI 79-85 — blow-off-reversal candidates as the melt-up extends to a 4th session. SELL trio stable: EFERT/IBFL/PAEL (all EPS-falling + trend-breaking).
- **Legacy winding down:** only P-039 (OGDC, grades 07-07) remains open. Once graded, `predictions_log.csv` is permanently closed — no new legacy rows will ever be issued (portfolio loop is dropped).

## Legacy (FROZEN — context only, do NOT update in engine mode)
- Last portfolio book (2026-06-24, before freeze): 6 holdings FABL/FFC/LUCK/MEBL/OGDC/INDU + cash 155,804; equity 802,848. Ahmad runs this book himself.

## Notes for the next agent
- Start by reading: `CLAUDE.md`, `INSTRUCTIONS.md`, `SKILL.md` (Part H), `pipeline/daily_run.md`, this file, `rules/rules_library.md`.
- **Update OHLC FIRST, always**, so the grader has post-signal bars.
- Windows console: `PYTHONIOENCODING=utf-8` on every script.
- Rewrite this file at Step 6 of every run (latest-state only).

*Not financial advice. Training engine — output is a graded prediction, never a trade recommendation.*
