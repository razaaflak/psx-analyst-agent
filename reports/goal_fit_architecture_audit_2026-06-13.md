# PSX Analyst Agent Goal-Fit And Architecture Audit

Date: 2026-06-13  
Scope: Analysis-only session. No pipeline state, rules, ledgers, data, scripts, or portfolio files were changed.  
Question: How fit is the current project, architecture, and technique stack for the actual goal: a PSX advisor that can tell Ahmad buy / hold / increase / decrease with evidence-backed judgment.

## Verdict

The project is well-designed as a disciplined learning and paper-advisory system. It is not yet an advisor. Its architecture is unusually honest for a trading-agent repo: it has real data ingestion, append-only prediction logs, paper trades, no-look-ahead grading, rule promotion gates, risk caps, source citations, weekly reviews, and a derived query DB. These are the right bones.

Current goal-fit: about 6.5 / 10 for becoming a reliable PSX advisory research assistant, and about 3 / 10 for being trusted today as an actual capital-allocation advisor.

The gap is not mostly tooling. The gap is evidence maturity, portfolio-level evaluation, and decision calibration. The system has built the measuring machine, but it has not yet produced enough measured judgment.

## What The Project Gets Right

1. It defines the real job clearly.

The repo does not say "predict every stock tomorrow." It defines a personal advisor for Ahmad, with buy / hold / increase / decrease guidance, paper phase first, Ahmad executes, and advisory mode only after readiness gates. That is the correct framing. A personal advisor needs consistency, risk awareness, and track record, not just clever signals.

2. The daily loop is structurally sound.

The 8-step loop is close to what a real discretionary analyst should do:

- ingest official data
- reconcile prior predictions
- learn from hits and misses
- update rules cautiously
- analyze through technical, fundamental, and sentiment lenses
- decide with sizing and stops
- log falsifiable predictions
- journal the reasoning

This creates a feedback loop. Most trading agents skip the feedback loop and become narrative machines. This repo does not.

3. No-look-ahead discipline is explicitly built in.

The project repeatedly says not to rewrite old calls, not to grade using future data, and to fill only grading columns later. The backtest script also states that each signal at bar t reads only bars through t and outcomes are measured afterward. This is essential. Without it, the project would be useless as a learning agent.

4. The rule library has good anti-overfitting rules.

Experimental -> Provisional -> Core is the right shape. Thresholds of 8 observations at 60% for Provisional and 20 observations at 65% plus out-of-sample survival for Core are sane starting gates. The current rules file also shows restraint: it refused to promote on 2/2 live hits and kept the promising RSI bear-regime finding Experimental.

5. Data coverage has improved meaningfully.

The architecture now has:

- 101 OHLC files
- 5-year historical candles for most symbols
- true OHLC, not close-only pseudo-technicals
- fundamentals files across the universe
- market snapshots
- a forward news archive
- a rebuildable SQLite DB

That is the minimum foundation for a serious PSX learning system.

6. Risk constraints exist.

Single-name cap, sector cap, cash buffer, swing bucket, per-trade risk, no leverage, no averaging down on broken thesis, and friction modeling are all in the method. This matters more than signal discovery. The actual goal is to help Ahmad survive and compound, not just make exciting calls.

7. The weekly review is the right governance layer.

The weekly review asks the most important questions: are we improving, are rules overfit, are holdings theses intact, what changed in the macro calendar, and what should be improved next week. This is where the "30-year practitioner" behavior can develop.

## Current Weaknesses

1. Evidence maturity is extremely low.

As of the read state, the system has 14 predictions, only 2 graded, both hits. The files correctly mark this as sample-too-small. This means the current live track record is not evidence yet. It is only a bootstrap.

The architecture is ready to learn. It has not learned enough.

2. The current Core rules are seed priors, not earned rules.

R-001 through R-004 are economically sensible, but they are marked Core seed. That is acceptable as a bootstrap, but dangerous if treated like learned edge. A real advisory system should separate:

- practitioner priors
- backtest-supported rules
- live-validated rules
- portfolio-proven rules

Right now "Core seed" may sound stronger than it is. The system should keep applying them cautiously, but reporting should make clear that they are priors under trial.

3. Prediction hit-rate is not the same as advisory quality.

A prediction can hit while the portfolio underperforms. This already happened in miniature: the book had 2/2 graded prediction hits but lagged the KSE-100 that week. That is not a failure; it is a warning that the measurement stack must include portfolio alpha, drawdown, risk-adjusted return, and decision quality.

The actual goal is not "be right on prediction rows." The goal is "improve Ahmad's capital allocation." The project needs stronger portfolio-level scoring.

4. The first paper portfolio was created too broadly at once.

Eight core buys on day one is useful as a sandbox, but not ideal as an advisor training pattern. It makes attribution harder:

- Did the method pick the right sectors?
- Did it size well?
- Did it enter well?
- Did it avoid bad setups?
- Did it only buy because the system needed holdings?

Future runs should prefer staged entries and explicit "why now" triggers.

5. Fundamental analysis is not deep enough yet.

The F lens is weighted highest, correctly. But current files emphasize P/E, yield, payout history, EPS/PAT/PBT, and broad sector/macro fit. For real advisor judgment, the F lens needs more depth:

- normalized earnings across cycles
- cash conversion and operating cash flow
- debt maturity and floating-rate exposure
- working capital stress
- related-party / sponsor quality
- regulatory receivables for E&P/power
- sector-specific KPIs
- valuation against history and peers
- dividend sustainability under stress

The fundamentals collector is a good start, but the advisory method needs a stronger company model layer.

6. Backtests currently test signals, not implementable strategies.

The backtest is honest and useful, but the first run mostly tests binary signal outcomes:

- did a signal lead to positive return?
- did it beat KSE-100?

That is not enough for advisory readiness. A real advisory backtest should simulate:

- position sizing
- entry delay
- stop loss
- targets
- transaction costs
- liquidity filters
- max position and sector caps
- portfolio rebalance rules
- cash drag
- benchmark comparison
- drawdown

Right now the backtest validates fragments of judgment, not the full advisory behavior.

7. Condition search is promising but fragile.

The RSI oversold bear-regime finding is interesting: weak unconditional result, strong holdout result for RSI < 30 when KSE100 < MA50. But the shape is odd: poor in-sample and strong holdout can happen when the market regime distribution changed. That does not invalidate it, but it demands caution.

Before this becomes more than Experimental, it needs:

- walk-forward splits, not one 70/30 split
- per-year breakdown
- sector breakdown
- liquidity breakdown
- average return, median return, worst decile, max adverse excursion
- execution after next close/open, not same close
- portfolio simulation with stops

8. The E/news layer is useful but high-risk.

The repo correctly says news is a modifier only and must be measured or retired. That is excellent. But this layer can still create narrative overconfidence. Macro news often explains what already happened. It can pollute predictions unless the system distinguishes:

- known before close
- known after close
- recap of prior session
- scheduled event
- unscheduled shock
- company-specific hard fact
- analyst interpretation

The current pipeline has date hygiene notes, but the news archive should eventually store timestamp, source type, and "available_before_decision" flags.

9. There is no explicit advisor readiness scorecard file.

Readiness gates exist in INSTRUCTIONS.md, but they are not yet operationalized as a persistent dashboard. The system should track readiness every week in a machine-readable way:

- graded prediction count
- rolling hit-rate
- hit-rate by conviction bucket
- decision P&L by action type
- portfolio return vs KSE100
- max drawdown
- rule counts by tier
- Core rules earned from live evidence
- calibration score
- news layer value-add
- data failure rate

This would stop vague confidence creep.

10. "Hold" decisions need scoring too.

The system logs paper trades and predictions, but an advisor's most common action will be HOLD. Bad holds are costly. Good holds are valuable. The current method should explicitly evaluate:

- hold that avoided churn
- hold that missed an obvious sell
- hold that missed an add opportunity
- trim not taken
- buy not taken

Without scoring non-actions, the agent can look accurate while silently failing at allocation.

## Architecture Assessment

### Data Layer

Strong direction. Official PSX data, OHLC store, fundamentals store, market snapshots, news archive, and derived DB form a good architecture.

Needed next:

- data quality tests for missing bars, split adjustments, bad volumes, and stale fundamentals
- explicit corporate-action adjustment handling for splits, bonuses, rights, and ex-dividend drops
- timestamped news availability
- source reliability scoring
- clear distinction between raw, cleaned, derived, and interpreted data

### Analysis Layer

The three-lens F/T/E model is appropriate for Ahmad's profile. Fundamentals leading the weights makes sense for dividend-oriented buy-and-hold. Technicals as entry/exit timing and sentiment as risk modifier is a good architecture.

Needed next:

- sector-specific fundamental scorecards
- technical signals tied to testable rules only
- confidence calibration by lens
- explicit uncertainty bands
- no forced score precision when data is weak

### Learning Layer

This is the project's best part. Predictions, grading, rules, weekly validation, and rule retirement are exactly the right mechanisms.

Needed next:

- decision-level attribution, not only prediction-level attribution
- rule impact measurement: what changed because rule R fired?
- counterfactual tracking: what would baseline have done?
- calibration curves: conviction 5, 6, 7 should produce different realized hit rates and returns

### Portfolio Layer

This is the weakest major layer relative to the goal. The current book tracks holdings, cash, stops, targets, and performance, but the advisory goal needs richer portfolio intelligence.

Needed next:

- benchmarked daily equity curve
- risk-adjusted return
- sector exposure history
- concentration and correlation risk
- cash decision attribution
- cost drag
- realized vs unrealized P&L
- thesis status per holding
- add/trim ladder plans

### Governance Layer

Strong. The project has hard rules, paper-only constraints, not-advice reminder, weekly review, and readiness gates. This is exactly how to keep the agent from becoming reckless.

Needed next:

- formal readiness dashboard
- explicit "not ready because..." section every weekly review
- red-team review of the best-looking rules
- monthly audit of whether the method beats a passive KSE100 benchmark after costs

## Technique Assessment

### Technical Analysis

Fit: medium.

The system now has the data needed for real TA: OHLC, MA50/200, RSI, volume, candlesticks, ATR. The technique is fine as a timing layer. The first backtest, however, showed most unconditional TA rules are weak or coin-flips. That is normal. TA should remain secondary and rule-gated.

Best use:

- entry timing
- stop placement
- avoid chasing
- detect regime
- confirm breakouts

Bad use:

- making standalone buy decisions
- promoting visual patterns without live evidence
- treating RSI/MA as universal rules

### Fundamental Analysis

Fit: promising but incomplete.

This should be the project's main edge because Ahmad's stated style is long-term, dividend-oriented, and risk-aware. But the current fundamentals stack is still early. EPS and payout history are useful; they are not a full investment thesis.

The system should build per-sector F templates. For example:

- Banks: NIM, deposit mix, infection ratio, capital adequacy, payout sustainability
- E&P: realized prices, reserves, circular debt receivables, exploration success, dividend cover
- Cement: capacity utilization, coal cost, debt, pricing discipline, dispatches
- Fertilizer: gas pricing, subsidy/tax risk, urea offtake, payout, working capital
- OMC/refinery: inventory gains/losses, regulated margins, circular debt, FX exposure

### Sentiment / News Analysis

Fit: useful but must remain constrained.

The current design's best feature is that news cannot independently trigger buys. Keep that. The news layer should be treated like risk radar, not alpha engine, until it proves value.

### Backtesting

Fit: useful for hypothesis filtering, not yet for advisor validation.

The current backtest is honest and valuable. It should evolve from signal backtesting into strategy and portfolio simulation. Until then, it can say "this signal deserves live observation," not "this advisor works."

### Paper Trading

Fit: necessary but immature.

Paper trading is the only way to test the whole loop. But it must become more realistic:

- next-session executable price assumptions
- liquidity and market impact
- partial fills for thin names
- stop execution assumptions
- ex-dividend and tax handling
- explicit slippage

## Highest-Impact Suggestions

### 1. Create a weekly Advisor Readiness Dashboard

Add a derived file such as `data/advisor_readiness.json` or a weekly report section with:

- graded predictions
- hit-rate and partial-adjusted hit-rate
- prediction return impact
- portfolio return vs KSE100
- max drawdown
- rolling 20-prediction hit-rate
- conviction calibration
- rule maturity count
- earned Core rules
- benchmark alpha after costs
- not-ready reasons

This directly operationalizes the actual goal.

### 2. Score decisions, not only predictions

Every recommendation should later be graded as a decision:

- BUY/ADD: did it outperform cash and benchmark over horizon?
- HOLD: was holding better than trim/sell?
- TRIM/SELL: did it reduce drawdown or avoid underperformance?
- NO TRADE: did patience help or miss opportunity?

This is the difference between a prediction game and an advisor.

### 3. Add a portfolio backtest engine

Build a second backtest mode that simulates the full advisor policy:

- candidate ranking
- position sizing
- cash rules
- sector caps
- stops and targets
- frictions
- next-session execution
- benchmark comparison
- drawdown

Signal backtests answer "does this rule have promise?" Portfolio backtests answer "would this advisor have helped Ahmad?"

### 4. Add sector-specific fundamental scorecards

Keep the F/T/E model, but make F deeper by sector. Each sector should have required metrics, red flags, and thesis-break conditions. This is the most direct path toward practitioner-level judgment.

### 5. Separate seed priors from earned Core rules

Rename or report the current seed Core rules as "Core priors" until they earn live evidence. This avoids accidental overconfidence.

### 6. Track counterfactual baselines

For every run, compute what would have happened under simple alternatives:

- 100% KSE100 proxy
- equal-weight watchlist
- hold existing portfolio
- cash
- buy top F-score only

The advisor is useful only if it beats realistic simple baselines over time.

### 7. Formalize non-action logging

Most advisory value is in not doing dumb things. Log important non-actions:

- did not add before MPC
- did not chase RSI overbought
- did not average down
- held cash through event
- refused unverified data

Then grade whether the non-action helped.

### 8. Improve corporate-action handling

Splits, bonuses, rights, and ex-dividend effects can corrupt both fundamentals and charts. Build explicit adjustment and warning logic. The UBL and MTL face-value notes show this is not theoretical.

### 9. Add calibration rules

A conviction 7 call should not be just nicer wording than conviction 5. Track realized outcomes by conviction bucket. If conviction does not predict better outcomes, shrink conviction language until calibrated.

### 10. Keep the current humility

The strongest thing in the repo is its refusal to pretend. Preserve that. The system should remain willing to say:

- sample too small
- rule failed holdout
- portfolio lagged
- data unverified
- no action
- not ready for advisory switch

That humility is not a weakness. It is the foundation of becoming useful.

## Bottom Line

The architecture is directionally right for the actual goal. It has the right safety rails, learning loop, data stores, and governance. The biggest missing piece is not "more AI." It is stronger measurement of advisory decisions and portfolio outcomes.

If the project adds decision grading, portfolio backtesting, sector-specific fundamentals, readiness dashboards, and counterfactual baselines, it can become a serious personal PSX research assistant. Until then, it is a promising paper-training system with good discipline and insufficient evidence.

## Future-Proof / 200IQ Upgrades

The next level is not adding more indicators. It is making the system harder to fool, harder to overfit, and better at judging its own ignorance.

### 1. Create an Advisor Readiness Score

Every weekly review should output one hard readiness score, for example `0-100`, based on:

- graded prediction count
- hit rate
- partial-adjusted hit rate
- portfolio alpha vs KSE-100
- max drawdown
- conviction calibration
- number of live-earned Core rules
- rule decay
- data reliability

This prevents vague "we are improving" narratives.

### 2. Grade Decisions, Not Just Predictions

The agent should grade every advisory action:

- BUY: did it beat benchmark after costs?
- ADD: was adding better than holding?
- HOLD: did patience help or hurt?
- TRIM: did it reduce downside or lose upside?
- SELL: did it avoid further damage?
- NO TRADE: was restraint correct?

This is the biggest gap. A real advisor is judged by allocation decisions, not forecast trivia.

### 3. Add Counterfactual Baselines

Every run should compare itself against simple alternatives:

- all cash
- equal-weight watchlist
- KSE-100 proxy
- hold current portfolio
- buy top F-score only
- buy top momentum only

The agent is only useful if it beats simple baselines over time.

### 4. Build A Portfolio Simulator, Not Just Signal Backtests

Current backtests test fragments. A future-proof system needs full-policy simulation:

- rank candidates
- apply sizing
- apply cash rules
- enforce sector caps
- simulate stops and targets
- include frictions and slippage
- benchmark against KSE-100
- measure drawdown

This answers the real question: would Urul's actual behavior have helped Ahmad?

### 5. Separate Four Kinds Of Knowledge

Do not mix these:

- Seed Prior: economically sensible belief
- Backtest Candidate: worked historically
- Live Validated: worked in forward paper trading
- Portfolio Proven: improved actual paper portfolio outcomes

Only the last two should meaningfully drive confidence.

### 6. Add Regime Awareness

The same rule behaves differently across regimes. Track:

- bull trend
- bear trend
- sideways market
- rate-hike cycle
- rate-cut cycle
- budget or MPC event window
- high inflation vs low inflation
- PKR stress vs PKR stability
- oil uptrend vs oil downtrend

Future-proof edge comes from knowing when a rule should be active.

### 7. Build Sector-Specific Fundamental Models

Generic P/E plus yield is not enough. Add sector templates:

- Banks: NIM, deposits, infection ratio, capital adequacy, payout
- E&P: oil/gas prices, reserves, circular debt, exploration, receivables
- Cement: coal, dispatches, utilization, pricing power, debt
- Fertilizer: gas pricing, urea offtake, subsidy and tax risk
- OMC/refinery: margins, inventory gains/losses, FX, circular debt

This is where practitioner-level judgment will come from.

### 8. Add Thesis Break Rules

Every holding should have explicit kill conditions:

- dividend cut due to weak earnings
- debt stress rising
- sector thesis reversed
- support broken on volume
- regulatory shock
- better replacement available

Without thesis-break logic, the system may keep holding names after the original reason is gone.

### 9. Track Confidence Calibration

A conviction 7 should outperform conviction 5. If not, conviction is decorative.

Weekly query:

- conviction 5 hit rate and average return
- conviction 6 hit rate and average return
- conviction 7 hit rate and average return

If higher conviction does not produce better outcomes, shrink all conviction language.

### 10. Add Red-Team Mode

Before any BUY or ADD, force a bearish analyst pass:

- What would make this wrong?
- What data may be stale?
- Is this just sector hype?
- Is the upside already priced?
- What does the market know that we do not?

Strong advisory systems argue against themselves before acting.

### Recommended Upgrade Order

Build the next evolution around this hierarchy:

`Data quality -> decision grading -> portfolio simulation -> regime-aware rules -> sector-specific fundamentals -> readiness score`

That makes Urul future-proof: not louder, not more complex, just much harder to deceive.

Paper research only. Ahmad makes his own decisions; this is not financial advice.
