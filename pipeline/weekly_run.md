# pipeline/weekly_run.md — The Weekly Deep-Dive (exact steps)

**Trigger phrase:** "Run the PSX weekly review."
**When:** Saturday or Sunday (market closed), ~45 min of your review time.
**Purpose:** zoom out, validate that the learning is real (not overfit), and prepare for the week ahead.

---

## Step 1 — Performance review
- Aggregate the week's `predictions_log.csv`: total graded, weekly hit-rate, and the trend vs. prior weeks (is the agent actually improving?).
- Paper portfolio: weekly and cumulative return, vs. the KSE-100 over the same window (are you beating the index, paper?). Note max drawdown and current cash %.
- **Run counterfactual baselines** (`.venv\Scripts\python.exe scripts/counterfactuals.py`) and put the full table in the report. Hit-rate ≠ advisory value. The book must justify itself against the dumb defaults: ALL-CASH (did investing help?), KSE-100 (alpha?), EQUAL-WEIGHT (did sizing help or hurt?), HOLD-DAY-1 (did post-day-1 activity add anything?). If the book is losing to a baseline, that is the headline of the review, not a footnote.
- **Cross-check the week's grades with the deterministic grader** (`scripts/grade_predictions.py --asof <sun>`); flag any hand grade that disagrees with the mechanical one. Guards the hit-rate against drift.
- List the best and worst paper calls of the week with the *reason* each worked/failed — **including the best/worst non-actions** (held cash, passed on a chase) now that they're logged as `decision_quality` rows.

## Step 2 — Rule validation (anti-overfitting — the most important step)
- **Out-of-sample test:** take each Provisional and Core rule and check its hit-rate over the most recent week of data it was *not* tuned on.
  - Holds up → keep / consider promotion if thresholds met.
  - Fails (hit-rate < 50% over last 10 obs) → **demote or Retire**.
- Look for **redundant or contradictory** rules; merge or retire the weaker.
- Sanity-check that every active rule still has a plausible **causal story**. Retire "lucky coincidence" rules with no mechanism.
- Confirm the active library is ≤ ~30 rules and the lens weights haven't drifted unjustifiably.

## Step 3 — Thesis re-check on holdings
- For each paper holding, re-confirm the original buy thesis still holds (leadership, earnings, balance sheet, dividend safety). Flag any where the thesis is weakening → candidate Trim/Sell next week.
- Re-verify Shariah status of holdings if Ahmad requires screening (status can change).

## Step 4 — Week-ahead calendar & positioning
- Build the calendar: upcoming **MPC/SBP rate decisions**, scheduled **results announcements**, **ex-dividend dates**, **budget** events, IMF reviews, and any known macro data (CPI). Note oil/currency setup.
- For each event, note the likely affected sectors and whether to raise cash / widen stops / hold steady.
- Refresh the watchlist: add any names that became interesting, remove any that no longer fit.

## Step 5 — Weekly report
- Write `reports/YYYY-Www.md` with: performance summary, rule changes (promoted/demoted/retired with reasons), holdings thesis status, the week-ahead calendar, and one paragraph of "what I'm trying to get better at next week."
- TL;DR at top: are we improving? biggest lesson? main risk next week?
- End with the not-advice reminder.

---

### Monthly add-on (first weekly run of each month)
- Full portfolio rebalance review against target sleeves (core/dividend/cash/swing).
- Tax-awareness pass on the paper book: notional CGT paid this month, any harvestable paper losses (carry-forward up to 3 years), filer-status reminder.
- A longer reflection: is the strategy itself working, or does the method (not just the rules) need adjustment?
