# rules/rules_library.md — The Agent's Self-Authored Rulebook

This file is the **learned overlay** on top of the base method in `SKILL.md`. The agent reads it before every decision and updates it after every reconciliation. Rules graduate by track record (see SKILL.md Part D). Prefer few, well-tested, causally-sensible rules over many coincidences.

**Tiers:** Experimental (no real decision weight yet) → Provisional (≥8 obs, ≥60% hit) → Core (≥20 obs, ≥65% hit, survives out-of-sample) → Retired.
**Active (Provisional + Core) cap:** ~30 rules. Retire the weakest before adding when full.

---

## Tier legend & status board
- Last full review: **2026-06-15 (Daily run — SBP MPC day)**
- Active rules: 4 Core (seed), 0 Provisional, 5 Experimental
- Current lens weights (core): F 0.40 / T 0.35 / E 0.25 — UNCHANGED (no Core-tier out-of-sample evidence yet; only 2 graded predictions P-003/P-006, both HIT — far below promotion sample).
- Graded so far: 3 (P-003 HIT, P-006 HIT, P-012 HIT) → 3/3 = 100% but n far too small to mean anything. No promotions. (Caveat: a perfect record at n=3 is itself a small-sample artifact, not skill — and these were issued in a strong-up tape; the harder grades land 06-16 when MPC/oil-regime calls — P-011 Islamic-vs-conv, P-014 E&P-underperform — mature.)

---

## CORE rules (seed — these are economically-grounded priors, not data-fitted; treat their "evidence" as starting beliefs to be tested, and demote if they fail out-of-sample)

### R-001 [Tier: Core (seed)]
- Created: 2026-06-09 | Last reviewed: 2026-06-09
- Hypothesis: When the SBP policy rate is rising/elevated, banks' net interest margins expand, supporting bank earnings.
- Trigger (if): policy rate rising or > ~10% AND name is a quality bank (MEBL/MCB/UBL)
- Action (then): tilt F +1 to +2 for banks; do not penalize banks for the broad-market rate headwind.
- Causal story: banks reprice assets faster than liabilities → wider margins.
- Evidence: seed prior (test against live results).

### R-002 [Tier: Core (seed)]
- Created: 2026-06-09 | Last reviewed: 2026-06-09
- Hypothesis: High debt-to-equity firms underperform when KIBOR rises (higher financing cost erodes profit).
- Trigger (if): policy rate rising AND stock's debt-to-equity is high / interest coverage thin
- Action (then): tilt F −1 to −2; require a larger margin of safety before BUY.
- Causal story: rising rates raise interest expense on floating-rate debt.
- Evidence: seed prior.

### R-003 [Tier: Core (seed)]
- Created: 2026-06-09 | Last reviewed: 2026-06-09
- Hypothesis: A dividend yield far above a stock's own 5-year average more often signals expected trouble (price fell / cut feared) than a free gift — especially yields > ~15%.
- Trigger (if): trailing yield > 1.5× the stock's 5-yr average OR > ~15% absolute
- Action (then): investigate dividend safety before any BUY; tilt F −1 until coverage confirmed.
- Causal story: the market prices in an expected cut; price drop inflates trailing yield.
- Evidence: 1 observation (2026-06-09 UBL: initially calculated 124.7% payout — CORRECTED by cross-check. UBL face value is PKR 5 post-June 2025 split, not PKR 10. Actual DPS = PKR 32/sh (4×Rs8); payout ratio = 62.3% vs EPS 51.33 — healthy. R-003 did NOT apply; false trigger due to bad face-value assumption). Obs: 1, outcome: rule correctly did not apply once data fixed. Lesson: always verify face value before computing DPS from % payout.

### R-004 [Tier: Core (seed)]
- Created: 2026-06-09 | Last reviewed: 2026-06-09
- Hypothesis: Ahead of a binary macro event (MPC decision, budget, IMF review), short-term volatility rises and single-day predictions are less reliable.
- Trigger (if): a scheduled binary macro event falls within the prediction's horizon
- Action (then): reduce conviction by ~30%, widen swing stops, prefer holding cash over new swing entries.
- Causal story: event uncertainty widens the outcome distribution.
- Evidence: seed prior.

---

## PROVISIONAL rules
*(none yet — the agent will populate this as patterns earn ≥8 observations at ≥60% hit-rate)*

---

## EXPERIMENTAL rules (hypotheses under observation — minimal decision weight)

### R-EXP-002 [Tier: Experimental]
- Created: 2026-06-09 | Last reviewed: 2026-06-09
- Hypothesis: Before computing DPS from a "% payout" announcement, always verify the current face value of the share — PSX payouts are expressed as % of face value, which can change via stock splits.
- Trigger (if): any payout expressed as a percentage (e.g. "160% dividend")
- Action (then): verify face value (PKR 5 or PKR 10 or other) from annual report before converting to PKR/share; do not assume PKR 10
- Causal story: UBL split each Rs10 share into two Rs5 shares in June 2025. "160% of Rs5 = Rs8" not "160% of Rs10 = Rs16". Assuming PKR 10 doubles the apparent DPS and yield, triggering false R-003 alerts.
- Evidence: 2 observations. (1) 2026-06-09 UBL false alarm caught by cross-check. (2) 2026-06-13: MTL 2:1 split (Rs10→Rs5 face value) PASSED at EOGM 2026-06-05 — confirmed via filings. MTL face value is now Rs5; any future MTL % -payout→DPS conversion MUST use Rs5, not Rs10. Apply immediately as data hygiene rule.

### R-EXP-003 [Tier: Experimental]
- Created: 2026-06-11 | Last reviewed: 2026-06-11
- Hypothesis: Sustained Brent > $90/bbl supports PSX E&P names (OGDC, PPL, MARI) via higher revenue realization.
- Trigger (if): Brent (or Arab Light) > $90 sustained in the macro_news/commodities feed
- Action (then): tilt E +1 for E&P holdings; do not chase if already extended in 52w range (OGDC at 85% on 06-11).
- Causal story: E&P revenue ≈ realized oil/gas price × volume; higher oil → higher topline & cash flow, partly offset by circular-debt drag on actual receipts.
- Evidence: 2 observations. (1) 2026-06-11: Brent $94.17, Arab Light $94.18 per Ahmad's brief; OGDC −0.15%/PPL −0.62% — oil supportive but E&P did NOT rally. (2) 2026-06-12: **regime flipped** — oil *slumping* (Mideast peace), and E&P **lagged** the tape (OGDC +0.57%, PPL +1.42%, MARI +0.67%; basket avg +0.89% vs KSE-100 +1.59%). Both obs point the same way: the oil→E&P link is **necessary-not-sufficient**, and under falling oil E&P underperforms. P-014 now tests the inverse directly (grade 06-16). No decision weight until ≥8 obs.

### R-EXP-004 [Tier: Experimental — meta/measurement]
- Created: 2026-06-11 | Last reviewed: 2026-06-11
- Hypothesis: Predictions that incorporate the macro_news/commodities layer have a higher hit-rate than those that do not.
- Trigger (if): a prediction's drivers include a news/commodity read (tag driver_lenses with 'E-news')
- Action (then): none yet — this is a MEASUREMENT rule. Tag the prediction; do not change weights.
- Causal story: if true, macro context improves timing/risk calls; if false, news adds noise and should be dropped.
- Evidence: 0 graded. Per SKILL.md Part G §5 (measure-or-retire): after ~20–30 graded, compare with-news vs without-news hit-rate. If news-tagged ≤ baseline, RETIRE the news layer. This rule enforces that honesty.

### R-EXP-005 [Tier: Experimental]
- Created: 2026-06-13 | Last reviewed: 2026-06-13
- Hypothesis: RSI14 < 30 in a **bear-regime market** (KSE100 close < KSE100 MA50) → positive return over the next 10 bars. The regime filter is essential — the same signal in a bull regime collapses.
- Trigger (if): individual stock RSI14 < 30 AND KSE100 is below its own MA50 at signal time
- Action (then): tilt T +1 for an oversold name; increase position sizing conviction slightly vs unconditional RSI signals. Still require F+E alignment before acting.
- Causal story: oversold in a bear market = capitulation selling exhaustion. Market already in downtrend → sellers have been active longer → bounce when they run out is more reliable. Oversold in a bull market = a minor dip that can keep dipping.
- Evidence: 0 live observations. **Backtest-validated pre-tier**: 74.1% holdout hit-rate (n=54 holdout signals, n=178 total), 5yr/101-symbol backfill, 70/30 chronological split. Bear-regime filter (KSE100<MA50) vs unconditional: +26pp holdout improvement (47.8%→74.1%). See `reports/backtests/condition_search_2026-06-13.json`. Live forward observations required before Provisional.
- ⚠ **Multiple-comparisons caveat (discount the 74.1% accordingly):** this number is the BEST of **5 variants** searched in one condition-search sweep, not a pre-registered hypothesis. With 5 filters tried on the same base signal, the best holdout is upward-biased by selection — a 74% on n=54 is roughly what noise-mining can produce even with no true edge. Treat the *effective* holdout strength as materially lower than face value. This is the same overfitting trap the audit warns about under "Regime Awareness"; do NOT escalate regime tagging into a standing framework on the back of it. The honest path: the bear-regime causal story is plausible, but the edge is **unproven until live forward obs accumulate**. Promote on live evidence, not on the searched backtest number.

### R-EXP-001 [Tier: Experimental]
- Created: 2026-06-09 | Last reviewed: 2026-06-09
- Hypothesis: In SBP rate-hike cycles, Islamic banks (MEBL, FABL) outperform conventional peers due to faster profit-rate repricing and structural market-share growth.
- Trigger (if): SBP rate rising AND comparing Islamic vs conventional bank performance
- Action (then): tilt F +0.5 additional for Islamic banks vs conventional in same rate environment
- Causal story: Islamic financing reprices with benchmark rate quickly; growing market-share adds volume on top of margin expansion. Conventional banks face NIM expansion too but no market-share tailwind.
- Evidence: 3 observations. (1) 2026-06-10: MEBL +1.13% vs MCB −1.61%, UBL −0.77%, FABL −0.10% on a day KSE-100 fell −0.53% — Islamic banks held up materially better. (2) 2026-06-11: Islamic avg (MEBL +1.01%, FABL +1.32% → +1.17%) vs conventional avg (MCB +0.40%, UBL +0.48% → +0.44%) on +0.16% index day — +0.73pp. (3) 2026-06-12: Islamic avg (MEBL +1.86%, FABL +1.31% → +1.59%) vs conventional avg (MCB +0.29%, UBL +1.50% → +0.90%) on a +1.59% index day — Islamic +0.69pp. All 3 obs support hypothesis. P-011 grades it directly 06-16. Do not apply materially until ≥8 obs.

---

## RETIRED rules (kept for memory — do not apply)
*(none yet)*

---

### Maintenance log
| Date | Change | Reason |
|---|---|---|
| 2026-06-09 | Seeded R-001..R-004 as Core priors | Bootstrap the library with economically-sensible rules; to be validated against live results |
| 2026-06-09 | Added R-EXP-001 as Experimental | Hypothesis from Run #1: Islamic banks outperform conventional in rate-hike cycles; 0 obs, no decision weight yet |
| 2026-06-09 | Added R-EXP-002 as Experimental | Data hygiene: verify face value before converting % payout to DPS — UBL split Rs10→Rs5 in Jun 2025; false R-003 alarm caught and corrected |
| 2026-06-09 | UBL decision flipped HOLD→BUY | Post cross-check: payout ratio 62.3% not 124.7%; face value PKR 5; added to portfolio at paper price 402 |
| 2026-06-10 | P-003 graded HIT | KSE-100 held >168k; MEBL +1.13%. R-001 and index-support read both correct. No rule changes. |
| 2026-06-10 | R-EXP-001 obs count → 1 | MEBL +1.13% vs conventional banks −0.77% to −1.61% on down-market day. One supporting data point. |
| 2026-06-11 | R-EXP-001 obs count → 2 | Islamic avg +1.17% vs conventional avg +0.44% on +0.16% index day. 2nd supporting obs. P-011 issued to test directly. Still Experimental, no decision weight. |
| 2026-06-11 | No grading this run | No predictions matured (earliest P-006 grades 06-13). No rule promote/demote. 3 new predictions issued (P-009..P-011). |
| 2026-06-11 | Added macro/news layer | RSS news + commodities feed wired into E lens (SKILL Part G guardrails; data_collection §3b). Modifier-only, no churn, measure-or-retire. |
| 2026-06-11 | Added R-EXP-003 | Brent>$90 → E&P tilt. 1 obs: oil $94 but OGDC/PPL flat-down — oil tailwind may be necessary-not-sufficient. |
| 2026-06-11 | Added R-EXP-004 (meta) | Measurement rule: news-tagged predictions must beat baseline hit-rate after 20–30 graded or the news layer is retired. |
| 2026-06-12 | No grading this run | 0 predictions matured (earliest P-006 grades 06-13). No promote/demote. 3 new predictions issued (P-012..P-014). |
| 2026-06-12 | R-EXP-001 obs → 3 | Islamic avg +1.59% vs conventional +0.90% on +1.59% index day (+0.69pp). 3rd supporting obs. Still Experimental. |
| 2026-06-12 | R-EXP-003 obs → 2 (non-confirming regime) | Oil regime flipped to *slump*; E&P lagged index (avg +0.89% vs +1.59%). Oil→E&P looks necessary-not-sufficient. P-014 tests inverse. |
| 2026-06-12 | R-EXP-002 live trigger noted | MTL filed book-closure for a share sub-division (split) — re-verify face value before any future MTL DPS/yield calc. |
| 2026-06-12 | No trades (R-004 budget event-risk) | Budget FY26-27 imminent + several names RSI-overbought post +1.59% rally → HOLD all, hold cash. Book flipped to cum +0.49%. |
| 2026-06-13 | **P-006 graded HIT** | MEBL cum +4.05% vs KSE-100 +1.22% over 06-10/11/12 (+2.84pp). R-001 + R-EXP-001 both consistent. 2nd graded prediction, 2nd HIT. No promotion (n=2, need ≥20 for Core out-of-sample). |
| 2026-06-13 | R-EXP-001 — no new formal obs | P-006 (MEBL-vs-index) leans on R-EXP-001 but is NOT the direct Islamic-vs-conventional test; P-011 is (grades 06-16). Obs count stays 3 to keep it honest (direct observations only). |
| 2026-06-13 | R-EXP-003 — regime note (no new graded obs) | Brent fell further to ~$88-89 (2mo low, Mideast de-escalation). Falling-oil regime persists → E&P headwind. P-014 (inverse test) grades 06-16. Still 0 decision weight. |
| 2026-06-13 | R-EXP-002 — LIVE | MTL 2:1 split (Rs10→Rs5) PASSED at EOGM 2026-06-05. MTL face value now Rs5 — any future MTL DPS/yield calc must use Rs5. Hygiene rule applied. |
| 2026-06-13 | R-004 — flagged LIVE for week ahead | **SBP MPC Mon 2026-06-15** (final FY26 meeting; 49/49 hold-vs-hike split; May CPI 11.7% 23-mo high → real hike risk) + Finance Bill passage by 06-30. Binary event inside horizon of P-010/011/012/013/014 (grade 06-15/16). Reduce conviction ~30%, hold cash, no new swing entries pre-MPC. |
| 2026-06-13 | BUDGET overlay (no rule change) | FY27 budget verified: super-tax cut EXCLUDES banks/oil-gas/fertiliser → no relief for E&P (OGDC/PPL) or FFC/ENGROH; cement gets construction-WHT cut + infra demand (DGKC/CHCC budget winners); IT/exporters (SYS/NML, not held) winners. Recorded as E-lens modifier (Part G), NOT a new rule — single event, no track record. See [[project_fy27_budget]]. |
| 2026-06-13 | Lens weights unchanged | F 0.40/T 0.35/E 0.25 held. No Core-tier evidence to justify a ±0.05 step. |
| 2026-06-13 | **First 5yr backtest run** — 101 symbols, 70/30 split | Results: `golden_cross` weak/mixed (n=40, holdout 58.3% but only 12 holdout signals — too small); `rsi_oversold_bounce` FAILS holdout (52.8% → 47.8%); `volume_breakout_followthrough` FAILS (48.6% flat); `near_52w_high_momentum` FAILS (45.7% → 44.4%); `rsi_overbought_chase` FAILS (44.0% → 44.6%). `islamic_vs_conventional_banks` n<30, insufficient. **No rule awarded backtest-validated tier.** All T-lens rules remain Experimental. Baseline: all rules coin-flip level unconditionally. Full results: `reports/backtests/backtest_2026-06-13.json`. |
| 2026-06-13 | **Condition-search on rsi_oversold_bounce** | 5 variants tested. Key finding: `rsi_oversold_bear_regime` (RSI<30 AND KSE100<MA50) = **74.1% holdout hit-rate (n=54)**. Causal story: oversold bounces during confirmed market downtrends (bear regime) are capitulation bounces — more reliable because the selling is exhaustion-driven, not part of a grinding uptrend correction. Bull-regime variant collapses to 25% holdout — confirms the edge is regime-specific. Liquidity filter alone doesn't help (45.7% holdout). **Action: add `rsi_oversold_bear_regime` as new Experimental rule R-EXP-005.** Monitor via live predictions before promoting. Full results: `reports/backtests/condition_search_2026-06-13.json`. |
| 2026-06-13 | **Audit-review hardening (2 independent agents, Sonnet+Opus)** | Implemented the 4 both-agree do-now items from the goal-fit audit + 2 honesty caveats. (1) **Corporate-action guard** `scripts/detect_corporate_actions.py` — OHLC store is raw/unadjusted; detector flagged 17 split/bonus discontinuities incl. UBL 2025-06-23 2:1 (the R-EXP-002 event), MARI, LUCK, SYS, BAFL → `data/corporate_actions.json`; auto-runs in `collect_ohlc --update`. (2) **Deterministic grader** `scripts/grade_predictions.py` — mechanical HIT/MISS from raw OHLC, no look-ahead, guards hit-rate vs lenient self-grading; re-derived P-006 HIT independently. (3) **Counterfactual baselines** `scripts/counterfactuals.py` — book +0.49% vs KSE-100 +1.21% (LAGS 0.72pp) and vs EQUAL-WEIGHT +2.05% (**sizing LOST 1.56pp** — new signal). (4) Decision_quality + non-action logging wired into daily_run Steps 6-7. Plus R-EXP-005 multiple-comparisons caveat (best-of-5-variants → discount 74.1%) and the concentration note below. |
| 2026-06-15 | **P-012 graded HIT** | DGKC closed 221.05 (+7.14%) vs 200 floor target — high-volume cement breakout STUCK, no mean-reversion. 3rd graded prediction, 3rd HIT (n=3, no promotion; need ≥20 for Core). Driver: SBP rate-hold + FY27 construction-WHT cut. |
| 2026-06-15 | **R-004 — LIVE observation (worked as intended)** | SBP MPC HELD policy rate at 11.5% (no hike; 49/49 split going in). R-004 discipline (hold cash, no new swing entries, −30% conviction pre-event) was correctly applied 06-12→06-15 — we did not guess the binary. Event resolved bullishly (+2.69% relief rally) so cash drag cost upside, but that is the *price of process*, not a rule miss. P-014 (explicit MPC-horizon E&P test) grades 06-16. No change. Elevated-rate regime (11.5%) persists → R-001 thesis intact. |
| 2026-06-15 | **R-EXP-001 — mildly NON-confirming day (corrected grouping)** | ⚠ CORRECTION to earlier draft: **FABL is ISLAMIC, not conventional** (watchlist: "Banks (Islamic), compliant"). Correct baskets on the rate-hold rally — **Islamic: MEBL +0.24%, FABL +3.87% → avg +2.06%** vs **Conventional: UBL +5.70%, MCB +0.62% → avg +3.16%**. Conventional edged Islamic by ~1.1pp, driven entirely by UBL catch-up (UBL had lagged; today it snapped back). MEBL was extended (RSI ~72, post 52w-high) and digested — FABL (Islamic) held up fine. So the day is only *mildly* non-confirming, not the clear counter-day the first draft claimed. Obs count stays 3 supporting. P-011 (direct Islamic-avg-vs-conventional-avg test, uses MEBL+FABL vs MCB+UBL) grades 06-16. Do NOT suppress. Still Experimental, 0 decision weight. |
| 2026-06-15 | **R-EXP-003 — falling-oil regime deepened, E&P relative laggard again** | Brent crashed ~−5.6% to ~$80 (8-wk low, US-Iran peace). Yet OGDC +2.09%/PPL +3.07% ROSE — carried by broad +2.69% melt-up — but OGTI oil-gas index +1.97% LAGGED the tape, and E&P trailed cement/banks. Consistent with necessary-not-sufficient + falling-oil = *relative* E&P headwind. P-014 grades 06-16. Still 0 decision weight. |
| 2026-06-13 | **Concentration caveat (no rule change)** | Both review agents: the 8 day-1 holdings are really ~3 correlated sector bets — banks (MEBL/FABL/UBL), E&P (OGDC/PPL), cement (DGKC/CHCC) + FFC. The "8-position portfolio" is structurally ~3-4 independent bets, so every portfolio-level metric (alpha, drawdown, the EQUAL-WEIGHT counterfactual) is measured on a far less diversified book than the count implies. No correlation/concentration check existed. Carry into next decision: prefer adding *uncorrelated* names over deepening existing sleeves; treat sector exposure, not position count, as the diversification measure. |
