# rules/rules_library.md — The Agent's Self-Authored Rulebook

This file is the **learned overlay** on top of the base method in `SKILL.md`. The agent reads it before every decision and updates it after every reconciliation. Rules graduate by track record (see SKILL.md Part D). Prefer few, well-tested, causally-sensible rules over many coincidences.

**Tiers:** Experimental (no real decision weight yet) → Provisional (≥8 obs, ≥60% hit) → Core (≥20 obs, ≥65% hit, survives out-of-sample) → Retired.
**Active (Provisional + Core) cap:** ~30 rules. Retire the weakest before adding when full.

---

## Tier legend & status board
- Last full review: **2026-06-09 (seed)**
- Active rules: 4 Core (seed), 0 Provisional, 0 Experimental
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
- Evidence: seed prior.

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
*(none yet — the agent adds new ideas here from daily reconciliation, each with a causal story)*

---

## RETIRED rules (kept for memory — do not apply)
*(none yet)*

---

### Maintenance log
| Date | Change | Reason |
|---|---|---|
| 2026-06-09 | Seeded R-001..R-004 as Core priors | Bootstrap the library with economically-sensible rules; to be validated against live results |
