# pipeline/daily_run.md — The Daily Pipeline (exact steps)

**Trigger phrase:** "Run the PSX daily pipeline for today."
**When:** after 5:00 PM PKT on a PSX trading day (after EOD data settles). Skip weekends/holidays.
**Read first:** `INSTRUCTIONS.md`, `SKILL.md`, and `rules/rules_library.md`.

Follow these 8 steps in order. Persist all file changes at the end.

---

## Step 0 — Setup & guardrails
- Confirm today is a PSX trading day. If not, say so and offer the weekly review instead.
- Load `data/portfolio.json`, `data/watchlist.json`, `rules/rules_library.md`, and `data/rolling_stats.json`, and have `pipeline/data_collection.md` ready (Step 1 uses it).
  - **`data/rolling_stats.json`** is the small DERIVED summary of all history (overall + per-rule hit-rate, open-prediction grade dates, portfolio P&L). Read it for the rolling track record instead of loading the whole `predictions_log.csv` / `trade_ledger.csv` into context — those grow unbounded. Use `open_predictions_by_grade_date` to know which prediction IDs mature today; then read **only those specific rows** from `predictions_log.csv` in Step 2 (e.g. via a targeted grep, not a full-file read).
  - If `rolling_stats.json` is missing or its `as_of_date` is stale, regenerate it from the CSVs (this is the same thing Step 8 does) before proceeding. The CSVs remain the source of truth; this file is rebuildable from them.
  - **Ensure the query DB exists.** `data/psx.db` is git-ignored (derived). If it is missing — e.g. a fresh clone — build it first: `python scripts/build_db.py --verify` (must print `GATE: PASS`). It is rebuilt from the canonical CSVs/JSON, so this never loses data.
- Confirm the **Playwright MCP** server is connected. If not, report it and stop (data collection depends on it).
- State today's date and the active rules (count by tier).

## Step 1 — INGEST today's data (automated — no manual paste)
- **Run `pipeline/data_collection.md` via Playwright MCP** to scrape today's official EOD figures from the PSX Data Portal (`dps.psx.com.pk`):
  - KSE-100 close, points change, % change, total volume/value, advancers/decliners.
  - For each watchlist + holding: open, high, low, close, volume, and recent history for MAs/RSI.
  - Fundamentals (P/E, P/B, yield) from the configured fundamentals source.
  - Company announcements (results, dividends, board meetings, regulatory) and material macro news.
- Validate (sanity checks), then write the raw snapshot to `data/market_data/YYYY-MM-DD.json` and save the close screenshot.
- **State the data source rung used and a confidence note.** Follow the fallback ladder. **If every automated path fails, skip the run gracefully and tell Ahmad — never fabricate a number.**

## Step 2 — RECONCILE matured predictions (the learning input)
- Find matured rows by **querying `data/psx.db`** (query **Q1** in `scripts/queries.md`): `status='open' AND grade_on_date <= today`. This returns only the few rows due today — do **not** read the whole `predictions_log.csv` into context. (The DB is a derived copy; `predictions_log.csv` stays the source of truth.)
- For each matured row: fetch the actual outcome — query the EOD close from `psx.db` (**Q2**, dates strictly *after* the prediction's issue_date — no look-ahead). Grade **HIT / PARTIAL / MISS**, compute the error, and write the result + a one-line *why*.
  - **Write the grade back to `data/predictions_log.csv`** (fill only the grading columns of that prediction's existing row; never edit the issued text/conviction/date). The CSV remains append-only/immutable for issued fields. Do **not** edit `psx.db` directly — it is rebuilt from the CSV at run end (Step 8).
- Update paper P&L for any matured paper trades (mark-to-market or realized).
- Produce a short reconciliation summary: how many graded, rolling hit-rate (**Q3**), biggest miss and its likely cause (data / model / noise).

## Step 3 — LEARN & update the rules library
- For each miss/partial: was it a **data** problem (bad input), a **model** problem (a lens or rule misfired), or **noise** (genuinely unpredictable)? Only model problems should change rules.
- Propose rule changes per SKILL.md Part D:
  - New pattern → add as **Experimental** (with a causal story; no material decision weight yet).
  - Provisional/Core rule that hit again → increment evidence; promote if thresholds met.
  - Rule that's failing → demote or **Retire**.
- Base promote/demote/retire decisions on **per-rule and per-conviction hit-rates queried from `psx.db`** (queries **Q4** and **Q5** in `scripts/queries.md`) — the DB gives the full-history aggregate cheaply, without loading every past prediction into context.
- Apply changes to `rules/rules_library.md` using the standard record format. Keep the active library ≤ ~30 rules; retire the weakest if full.
- **Do not promote anything on a small sample.** Respect the graduation thresholds.

## Step 4 — ANALYZE (apply the current method + learned rules)
- For every holding and watchlist name, compute **T, F, E** sub-scores (SKILL.md Part A), applying any Core/Provisional rule tilts.
- Note the KSE-100 backdrop tilt and any imminent macro event (SKILL.md Part F).

## Step 5 — DECIDE
- Compute the **composite** (Part B1) and map to **Buy / Add / Accumulate / Hold / Trim / Sell** (Part B2).
- Apply override gates (thesis break, stop hit, Shariah exclusion, unverified data).
- For any actionable call, compute size (within caps), stop-loss, target, and horizon.
- Output one **per-stock card** per name (SKILL.md Part E).

## Step 6 — PAPER-TRADE (simulate, never real)
- For each actionable decision, append a row to `data/trade_ledger.csv` (BUY/SELL/TRIM, qty, paper price = *next session's* expected execution context, reason, rules applied). Apply simulated frictions (commission, NCCPL adj., notional 15% CGT on realized gains).
- Update `data/portfolio.json`: new cash, holdings, average cost, weights. Re-check caps; if a cap is breached, note the required trim.

## Step 7 — PREDICT (set up tomorrow's learning)
- Write **at least 2–3 falsifiable predictions** to `data/predictions_log.csv` (SKILL.md Part D1): prediction text, driver lenses/rules, conviction, issue date, grade_on_date, status=open.

## Step 8 — JOURNAL & hand-off
- **Regenerate `data/rolling_stats.json`** from the now-updated `predictions_log.csv`, `trade_ledger.csv`, and `portfolio.json`. Recompute: total/graded/open/hit/partial/miss counts and overall hit-rate; `open_predictions_by_grade_date` (each open row's id + grade_on_date + ticker); per-rule graded/hit counts; portfolio cash/invested/deployed%/cumulative return/drawdown; active-rule counts by tier; set `as_of_date` to today. Keep `sample_too_small: true` while graded count is small. This file is DERIVED — if it ever disagrees with the CSVs, the CSVs win.
- **Rebuild `data/psx.db`** from the now-updated flat files: run `python scripts/build_db.py --verify`. The `--verify` gate confirms DB row counts equal the CSV data-row counts (predictions, trades) — if it prints `GATE: FAIL`, stop and reconcile before committing; the CSVs are the truth. This keeps the queryable copy in sync for tomorrow's run.
- Write `journal/YYYY-MM-DD.md` containing: run header, reconciliation summary, rule changes made, the per-stock cards, paper trades logged, new predictions, and the run footer (paper P&L day+cumulative, rolling hit-rate, **the single most important watch item**, and the not-advice reminder).
- Present Ahmad a 5-line TL;DR at the top: today's market in one line, your top 1–2 actions (paper), the key risk, and what you got right/wrong yesterday.

---

### Optional: "Morning Brief" (lightweight, ~2 min, pre-open)
If Ahmad asks for a morning brief before 9:15 AM: summarize overnight global cues (US close, oil, currency, geopolitics), list today's scheduled events (results, ex-div, MPC), restate any open swing stops/targets, and flag anything on the watchlist that gapped on news. **No new paper trades** in the morning — the full pipeline runs after close.
