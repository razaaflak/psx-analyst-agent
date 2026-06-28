# Internal Monitor Dashboard — Build Plan (bite-sized)

**Status:** Plan v1 — 2026-06-23.
**Owner:** Ahmad.
**Audience:** Ahmad (the operator) — NOT customers. This is the *internal* progress monitor.
**Purpose:** Visualize the pipeline's daily output so Ahmad can see, at a glance: candlesticks + indicators per symbol, the engine's BUY/HOLD/SELL signals (current + history), the rules library and how each rule is performing, the predictions and their grades, and the book's progress over time.

> **Not the same as `plans/dashboard_product_plan.md`.** That file = the public commercial "PSX AI Hub" product (hides the machinery, tiered, monetized). THIS file = the internal training monitor that deliberately *shows* the machinery (signals, rules, predictions, hit-rates, diligence flags). Keep them separate; do not merge.

---

## 0. What it reads (no new data work — all of this already exists or is planned)

The dashboard is **read-only over the repo's existing artifacts.** It builds nothing the pipeline doesn't already produce:

| Source file | Feeds |
|---|---|
| `data/ohlc/{SYM}.json` | candlesticks + MA20/50/200 + RSI + volume |
| `data/dashboard_feed.json` (⏳ from `universe_signals.py`) | per-symbol current signal, conviction, indicators, support/resistance, diligence flag, history pointer |
| `data/universe_signals.csv` (⏳) | historical signal labels per symbol (overlay on candles) + per-signal grade |
| `data/predictions_log.csv` | predictions + their HIT/MISS/PARTIAL grades |
| `data/rolling_stats.json` | overall + per-rule hit-rate, open predictions, book P&L |
| `rules/rules_library.md` | the rules + tier + evidence counts |
| `data/portfolio.json` | holdings, cash, weights |
| `data/trade_ledger.csv` | executed trades |
| `journal/YYYY-MM-DD.md` | daily narrative |

**Boundary:** the dashboard never writes to these files. The pipeline owns them; the dashboard only displays. (A tiny read-only API or a static-file read is fine.)

---

## 1. Phasing (ship smallest useful thing first)

### Phase 0 — Decide the stack (½ day, decision only)
- [ ] Pick the lightest thing that renders candlesticks well. Recommendation: **single-page app (Vite + React) + a charting lib (lightweight-charts / ECharts)**, reading the JSON/CSV files directly — OR a Python option (Streamlit/Dash) since the data tooling is already Python. Decide one. Bias to whichever Ahmad will actually iterate on.
- [ ] Decide data access: read the repo files directly (simplest) vs a thin FastAPI/Flask read-only endpoint. Start with direct file read.
- **DoD:** stack chosen, empty app boots and reads one `data/ohlc/{SYM}.json`.

### Phase 1 — Single-symbol candlestick view (the core)
The one screen that proves the whole idea.
- [ ] Candlestick chart from `data/ohlc/{SYM}.json` (use `adj_*` fields).
- [ ] Overlays: MA20 / MA50 / MA200 lines, volume sub-panel, RSI-14 sub-panel.
- [ ] **Support/resistance lines** from `dashboard_feed.json`.
- [ ] **Signal markers on the candles:** plot every past BUY/SELL from `universe_signals.csv` at its date, colored by signal, with a tick/cross once graded (so Ahmad *sees how right past signals were* — your explicit ask).
- [ ] Symbol picker (dropdown over the ~100 universe).
- **DoD:** pick any KSE-100 symbol → see its candles + indicators + S/R + the engine's past signals and their outcomes.

### Phase 2 — Universe grid (all 100 at a glance)
- [ ] A sortable/filterable table or heatmap of all ~100 symbols from `dashboard_feed.json`: symbol, last close, day %, signal, conviction, RSI, trend (vs MAs), 52w position, `diligence` flag.
- [ ] Color the signal cell (BUY green / HOLD grey / SELL red); badge STALE-diligence names.
- [ ] Click a row → opens the Phase-1 single-symbol view.
- [ ] Filters: signal type, sector, diligence=STALE, "changed today".
- **DoD:** one screen shows the whole universe's current signals; click-through to any chart.

### Phase 3 — Rules & predictions monitor (the learning loop, visible)
- [ ] **Rules panel:** list from `rules_library.md` + `rolling_stats.json` per-rule counts — rule id, tier (Exp/Prov/Core), obs, hit-rate, last fired. This is how Ahmad watches rules graduate/decay.
- [ ] **Predictions panel:** open predictions (due dates) + recently graded ones from `predictions_log.csv` — text, conviction, HIT/MISS, the one-line why. Filter open vs graded.
- [ ] **Engine scoreboard:** overall hit-rate, n graded, per-signal-type hit-rate from `rolling_stats.json`; flag `sample_too_small` honestly.
- **DoD:** Ahmad can see which rules are working and whether the engine's calls are hitting.

### Phase 4 — Daily progress & book
- [ ] **Progress over time:** book cumulative return vs KSE-100 (the counterfactual bar) as a line chart from the run history.
- [ ] **Portfolio view:** holdings, weights (donut), cash %, sector exposure from `portfolio.json`.
- [ ] **Today's run summary:** pull the TL;DR + watch item from the latest `journal/YYYY-MM-DD.md`.
- **DoD:** one screen answers "are we making progress and where does the book stand."

---

## 2. Design notes
- **Internal tool aesthetics are fine** — dense, information-rich, dark/terminal is acceptable. This is a cockpit, not a customer product. (Opposite of the product plan's "calm beginner" brief.)
- **Show the machinery on purpose:** rule ids, conviction scores, diligence flags, NEEDS-REVIEW grades — all visible. That's the point.
- **Truth-in-display:** when `rolling_stats.sample_too_small` is true, say so on the scoreboard. Never render the engine's signals as advice — label them "training signal."
- **Read-only, always.** No buttons that mutate repo state. The pipeline is the only writer.

---

## 3. Dependencies & sequencing
- Phase 1's signal overlay and Phase 2 both depend on **`universe_signals.py` + `dashboard_feed.json` existing** (the ⏳ script scheduled in `data/run_state.md`). Until then, Phase 1 can run on OHLC + indicators only (no signal markers), and Phase 3/4 work today off existing files.
- So a sensible order if building before the engine script lands: **Phase 1 (charts/indicators only) → Phase 3 (rules/predictions, all data exists) → then add signal overlays + Phase 2 once `dashboard_feed.json` is produced → Phase 4.**

---

## 4. Open decisions for Ahmad
1. Stack: React+lightweight-charts (best charts, JS) vs Streamlit/Dash (reuses Python tooling, faster to stand up, weaker candles)?
2. Run it as a static local app reading files, or a small local server with a read-only API?
3. Build now on existing files (rules/predictions/portfolio), or wait until `universe_signals.py` + `dashboard_feed.json` exist so the signal layer is there from day one?
