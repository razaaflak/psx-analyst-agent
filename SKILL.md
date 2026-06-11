---
name: psx-analyst
description: Use this skill whenever analyzing Pakistan Stock Exchange (PSX) stocks, running the daily or weekly PSX paper-trading pipeline, scoring technical/fundamental/sentiment signals, making Buy/Hold/Sell/Trim decisions on PSX securities, reconciling past predictions, or updating the self-learning rules library. Trigger this for any PSX market analysis, KSE-100 assessment, candlestick/chart reading, valuation check, dividend analysis, paper-trade logging, or prediction reconciliation — even if the user just says "run the pipeline," "analyze my watchlist," or "what should I do with [stock]."
---

# PSX Analyst Skill

The methodology for analyzing PSX securities and running a self-learning paper-trading loop. Three lenses (Technical, Fundamental, Emotional/sentiment) combine into a transparent conviction score that maps to a Buy / Hold / Sell / Trim decision. Predictions are logged, later graded, and the lessons become rules that grow and improve over time.

> Always re-read `rules/rules_library.md` before scoring — the library modifies the base method below. This file is the *base* method; the rules library is the *learned* overlay.

---

## Part A — The three lenses and how to score them

Each lens produces a sub-score from **−10 (strongly bearish) to +10 (strongly bullish)**. Document the components; don't just assert a number.

### A1. Technical score (T)

Assess each and note the contribution:
- **Primary trend:** price vs. 50-day and 200-day moving average. Above both = uptrend (+). Below both = downtrend (−). 50 above 200 ("golden cross") is constructive; the inverse ("death cross") is cautionary.
- **Support / resistance:** where is price relative to the nearest support and resistance? Near strong support in an uptrend = favorable entry (+). Near resistance = caution (−). Use the stock's own levels and the KSE-100 levels (e.g., index support/resistance clusters).
- **Momentum (RSI 14):** >70 overbought (−), <30 oversold (potential bounce, +), 40–60 neutral.
- **Volume:** moves confirmed by above-average volume are more trustworthy. A breakout on weak volume is suspect (−).
- **Candlesticks:** reversal/continuation patterns *at* a meaningful level (hammer, bullish/bearish engulfing, doji at support/resistance). A pattern in mid-range is low-information — discount it.
- **KSE-100 backdrop:** is the broad index trending up, down, or ranging? A great stock fights gravity in a falling market. Apply the index trend as a tilt to every T score.

### A2. Fundamental score (F)

- **Valuation:** P/E and P/B vs. (a) the stock's own 5-year range and (b) its sector. Below own average + below sector = cheap (+). Stretched above both = expensive (−).
- **Earnings quality:** 5-year EPS trend (rising staircase +, erratic −); ROE (>15–20% is strong +).
- **Balance sheet:** debt-to-equity and interest coverage. **Weight this heavily when the SBP policy rate is high/rising** — high debt is dangerous when KIBOR climbs. Low debt + high coverage (+).
- **Dividend:** yield vs. own history, payout ratio (40–70% healthy), coverage by earnings, and consistency (paid through past downturns? +). A suspiciously high yield (>~15%) is a warning, not a gift (−).
- **Cash flow:** real operating cash, not just accounting profit (+).
- **Shariah status:** note compliant / non-compliant (preference flag for Ahmad; not a score driver unless he requires strict screening, in which case non-compliant = exclude).
- **Sector & macro fit:** does the current macro favor this sector? (e.g., rising rates → banks' margins +, leveraged cyclicals −).

### A3. Emotional / sentiment score (E) — the timing & risk modifier

- **Market mood:** fear vs. greed. Broad panic near support = contrarian opportunity for quality (+); euphoria/parabolic moves = caution (−).
- **News & announcements:** company-specific (results, dividends, management changes, regulatory actions) and sector news. Material negative surprise (−), positive surprise (+).
- **Flows:** foreign buying/selling, local institutional vs. retail behavior, sector rotation direction.
- **Macro/policy calendar:** proximity to SBP/MPC decisions, inflation prints, IMF reviews, the federal budget, ex-dividend dates, oil-price and currency moves, geopolitics. An imminent binary event raises uncertainty → shrink conviction and widen stops (−risk).

**E is a modifier, not a thesis.** Never buy on sentiment alone; never override solid F just because mood is good. Use E to tune *timing, sizing, and conviction*, and to flag event risk.

---

## Part B — Composite conviction score → decision

### B1. Combine the lenses

Base weights (tunable by the rules library as evidence accumulates):

```
Composite = (0.40 × F) + (0.35 × T) + (0.25 × E)
```

- **Fundamentals lead** because Ahmad is a long-term, dividend buy-and-hold investor.
- **Technicals** set entry/exit timing.
- **Sentiment** modifies conviction and flags event risk.

For a pure **swing-trade candidate** (satellite bucket only), flip toward technicals:
```
Composite_swing = (0.55 × T) + (0.25 × E) + (0.20 × F)
```
Tag every swing idea explicitly as SWING and apply swing risk limits (Part C).

### B2. Map composite to decision

| Composite | Core (long-term) action | Swing action |
|---|---|---|
| **≥ +5** | **BUY / ADD** (strong conviction) | BUY (with stop & target) |
| **+2 to +5** | **ACCUMULATE** small / **HOLD** | watch for entry trigger |
| **−2 to +2** | **HOLD** (no action) | no trade |
| **−5 to −2** | **TRIM** / tighten watch | exit / avoid |
| **≤ −5** | **SELL** (thesis weakening) | exit / short-bias (paper, flag) |

**Override gates (these veto the score):**
- **Thesis break** (lost leadership, broken balance sheet, dividend cut from deterioration) → SELL regardless of a positive composite.
- **Hard stop hit** on a swing position → EXIT mechanically, no re-scoring.
- **Strict-Shariah-required + non-compliant** → EXCLUDE.
- **Data unverified / missing** → HOLD + flag; never act on guesses.

Always show the three sub-scores, the weights used, the composite, the mapped decision, and any override.

---

## Part C — Risk, sizing, and the paper portfolio

- **Position size cap:** no single paper holding > **15%** of total paper portfolio at cost; trim if it grows past **~20%** by appreciation.
- **Sector cap:** no single sector > **~30%** of the book.
- **Cash buffer:** keep **5–15%** paper cash; never go 100% invested.
- **Swing bucket:** total swing exposure ≤ **15–20%** of the book.
- **Per-swing risk:** risk ≤ **1–2%** of total portfolio per trade. Stop-loss typically **5–8%** below entry; minimum reward:risk of **2:1**.
- **No leverage/margin** in the paper book.
- **Costs:** when simulating, apply realistic frictions — brokerage commission, plus the ~0.5% NCCPL acquisition-cost adjustment, and remember realized paper gains carry a notional **15% CGT** (so frequent trading visibly drags paper returns; this teaches the cost of over-trading).
- **Averaging down** is forbidden on a broken thesis. Adding to a *winning, still-valid* thesis is allowed within caps.

---

## Part D — The self-learning engine (this is the core of the system)

### D1. Make every prediction falsifiable

When you DECIDE, also PREDICT. A prediction must be checkable later, e.g.:
- Direction: "MEBL closes higher over the next 5 sessions" (binary).
- Magnitude band: "OGDC between PKR X and Y at next close."
- Conditional: "If KSE-100 holds 160,000 support, FFC bounces ≥2% within 3 sessions."
- Decision-quality: "Today's BUY on LUCK will be in profit when graded in 5 sessions."

Record: prediction text, the lenses/rules that drove it, the conviction, the issue date, and the **grade-on date** (the session it matures).

### D2. Reconcile (grade) matured predictions

On each run, find predictions whose grade-on date ≤ today. For each:
- Pull the actual outcome (close, %move, whether the level held).
- Score **HIT / PARTIAL / MISS** and record the error (e.g., predicted +2%, actual −1% → miss, error 3 pts).
- Attribute: *which lens or rule* drove the call, and *why* it worked or failed (was it a data problem, a model problem, or genuine randomness/noise?).
- Update the paper P&L for any matured paper trades.

### D3. Turn lessons into rules — with graduation tiers

A "rule" is a small, testable if→then statement. Each rule carries metadata so the library improves rather than bloats. Tiers:

| Tier | Meaning | Promotion threshold |
|---|---|---|
| **Experimental** | A new hypothesis from one or few observations | created freely; **does not yet affect decisions** beyond a tiny tilt |
| **Provisional** | Showing promise | ≥ **8 observations** and **≥60% hit-rate** |
| **Core** | Trusted; actively shapes decisions/weights | ≥ **20 observations**, **≥65% hit-rate**, and survives out-of-sample (the weekly held-out check) |
| **Retired** | Stopped working or overfit | hit-rate falls below 50% over its last 10 observations, OR contradicted by a stronger Core rule |

**Anti-overfitting discipline (mandatory):**
- A pattern seen **once is a hypothesis, not a rule.** Log it Experimental; do not let it move decisions materially.
- Require the **minimum observation counts** above before promotion. No promotion on small samples.
- Each weekly run, **out-of-sample test** Provisional/Core rules against the most recent week they were *not* tuned on. Demote if they fail.
- Cap the active (Provisional+Core) library at a manageable size (~30 rules). If full, retire the weakest before adding.
- Prefer **general, economically-sensible** rules ("banks outperform when the policy rate rises") over **hyper-specific coincidences** ("LUCK rises on Tuesdays"). Be suspicious of rules with no causal story.
- Tune the lens **weights** (Part B1) only via the rules library, only with Core-tier evidence, and only in small steps (±0.05).

### D4. Rule record format (append to rules/rules_library.md)

```
### R-007  [Tier: Provisional]
- Created: 2026-06-12 | Last reviewed: 2026-06-21
- Hypothesis: When KSE-100 RSI < 35 AND a blue chip sits on 200-DMA support, a 3-session bounce ≥2% follows.
- Trigger (if): KSE-100 RSI<35 and stock within 1% of 200-DMA
- Action (then): tilt T +2 for that stock; consider small ACCUMULATE
- Causal story: oversold index + technical support = mean-reversion in quality names
- Evidence: 11 observations, 7 hits, 2 partial, 2 miss → 64% hit-rate
- Status notes: watch in down-trending markets where support breaks
```

---

## Part E — Standard output blocks

Use these consistently so the journal is scannable.

**Per-stock card:**
```
[TICKER] — DECISION (conviction X/10)  [CORE | SWING]
T: +n (one line why)  F: +n (one line why)  E: +n (one line why)
Composite: +n.n → DECISION.  Override: none / [reason]
If acting: size = PKR ___ (n% of book); stop = ___; target = ___; horizon = ___
Rules applied: R-00x, R-00y
```

**Run header:** date, data source + confidence, KSE-100 close & % move, market mood read, any macro events today/imminent.

**Run footer:** paper P&L (day + cumulative), prediction scoreboard (rolling hit-rate), the **single most important watch item**, and the not-advice reminder.

---

## Part F — Quick reference: the macro transmission (for the E lens)

- **SBP rate ↑** → headwind for broad market & leveraged cyclicals; **tailwind for banks** (margins). **Rate ↓** → tailwind for cyclicals, cement, leveraged firms.
- **Inflation ↑** → raises odds of more hikes → favor pricing-power and high-dividend names.
- **IMF review positive / dollar inflows** → sentiment up. Doubts → selloff.
- **PKR depreciation** → hurts importers & dollar-debt firms; helps exporters (textile, IT).
- **Budget (June)** → tax/sector changes can re-rate sectors overnight; raise event-risk flag.
- **Oil ↑** → worse import bill & inflation (− market) but **+ for E&P** (OGDC/PPL/Mari).
- **Circular debt** → overhang on power & E&P cash flows.

When any of these is imminent, lower conviction, widen swing stops, and consider holding more paper cash.

---

## Part G — Macro/news layer discipline (added Run #3, 2026-06-11)

The E lens now ingests a daily **macro_news** + **commodities** feed (RSS: Business Recorder, Mettis; plus commodity/flow levels — see `pipeline/data_collection.md` §3b). This adds *risk awareness* and *learning surface*, but is the easiest input to over-trust. Hard guardrails:

1. **Modifier only, weight unchanged.** News flows into the **E** sub-score (still 0.25 of composite). It tunes *timing, sizing, conviction, stops, cash* — it does **not** flip a decision by itself and **never** overrides solid F/T.
2. **No new churn.** A news item may **widen a stop, raise cash, or shrink conviction**. It may **NOT** trigger a fresh paper entry on its own. New buys still require an F/T thesis.
3. **Experimental by default.** Any news/commodity-derived rule starts **Experimental (0 decision weight)** and must earn **≥8 obs at ≥60%** before it modifies anything — same graduation gate as every rule. A scary headline is a hypothesis, not a signal.
4. **Date hygiene / no look-ahead.** Tag every item with its true pub-date. A brief that quotes *yesterday's* index/commodity close is a recap of the prior session — never grade a prediction against news dated after the fact.
5. **Measure-or-retire (mandatory).** Tag which predictions used the news layer. After ~20–30 graded, query hit-rate **with-news vs without-news** (calibration, like Q5). **If news-tagged predictions do not beat baseline, retire the layer** — honestly, no sunk-cost bias. The news layer must prove it improves outcomes or it goes.
6. **Commodity transmission** (drives E directly): Brent/WTI ↑ → E&P (OGDC/PPL/MARI) +; USD/PKR depreciation → importers −, exporters +; FIPI net selling → broad flow −; rising leverage (futures/MTS/MFS) → froth/risk gauge.
