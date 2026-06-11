# rules/rules_library.md — The Agent's Self-Authored Rulebook

This file is the **learned overlay** on top of the base method in `SKILL.md`. The agent reads it before every decision and updates it after every reconciliation. Rules graduate by track record (see SKILL.md Part D). Prefer few, well-tested, causally-sensible rules over many coincidences.

**Tiers:** Experimental (no real decision weight yet) → Provisional (≥8 obs, ≥60% hit) → Core (≥20 obs, ≥65% hit, survives out-of-sample) → Retired.
**Active (Provisional + Core) cap:** ~30 rules. Retire the weakest before adding when full.

---

## Tier legend & status board
- Last full review: **2026-06-11 (Run #3)**
- Active rules: 4 Core (seed), 0 Provisional, 4 Experimental
- Current lens weights (core): F 0.40 / T 0.35 / E 0.25 — only change via Core-tier evidence, ±0.05 steps.

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
- Evidence: 1 observation (2026-06-09 UBL false alarm caught by cross-check). Apply immediately as data hygiene rule.

### R-EXP-003 [Tier: Experimental]
- Created: 2026-06-11 | Last reviewed: 2026-06-11
- Hypothesis: Sustained Brent > $90/bbl supports PSX E&P names (OGDC, PPL, MARI) via higher revenue realization.
- Trigger (if): Brent (or Arab Light) > $90 sustained in the macro_news/commodities feed
- Action (then): tilt E +1 for E&P holdings; do not chase if already extended in 52w range (OGDC at 85% on 06-11).
- Causal story: E&P revenue ≈ realized oil/gas price × volume; higher oil → higher topline & cash flow, partly offset by circular-debt drag on actual receipts.
- Evidence: 1 observation (2026-06-11: Brent $94.17, Arab Light $94.18 per Ahmad's brief; OGDC −0.15%/PPL −0.62% on the day — note: oil supportive but E&P did NOT rally, possibly circular-debt overhang or profit-taking near range highs). Watch: oil tailwind may be necessary-not-sufficient. No decision weight until ≥8 obs.

### R-EXP-004 [Tier: Experimental — meta/measurement]
- Created: 2026-06-11 | Last reviewed: 2026-06-11
- Hypothesis: Predictions that incorporate the macro_news/commodities layer have a higher hit-rate than those that do not.
- Trigger (if): a prediction's drivers include a news/commodity read (tag driver_lenses with 'E-news')
- Action (then): none yet — this is a MEASUREMENT rule. Tag the prediction; do not change weights.
- Causal story: if true, macro context improves timing/risk calls; if false, news adds noise and should be dropped.
- Evidence: 0 graded. Per SKILL.md Part G §5 (measure-or-retire): after ~20–30 graded, compare with-news vs without-news hit-rate. If news-tagged ≤ baseline, RETIRE the news layer. This rule enforces that honesty.

### R-EXP-001 [Tier: Experimental]
- Created: 2026-06-09 | Last reviewed: 2026-06-09
- Hypothesis: In SBP rate-hike cycles, Islamic banks (MEBL, FABL) outperform conventional peers due to faster profit-rate repricing and structural market-share growth.
- Trigger (if): SBP rate rising AND comparing Islamic vs conventional bank performance
- Action (then): tilt F +0.5 additional for Islamic banks vs conventional in same rate environment
- Causal story: Islamic financing reprices with benchmark rate quickly; growing market-share adds volume on top of margin expansion. Conventional banks face NIM expansion too but no market-share tailwind.
- Evidence: 2 observations. (1) 2026-06-10: MEBL +1.13% vs MCB −1.61%, UBL −0.77%, FABL −0.10% on a day KSE-100 fell −0.53% — Islamic banks held up materially better. (2) 2026-06-11: Islamic avg (MEBL +1.01%, FABL +1.32% → +1.17%) vs conventional avg (MCB +0.40%, UBL +0.48% → +0.44%) on a +0.16% index day — Islamic outperformed by ~0.73pp. Both obs support hypothesis. P-011 now tests it directly. Do not apply materially until ≥8 obs.

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
