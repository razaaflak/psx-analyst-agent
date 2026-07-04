# Frontend

Vanilla JS + CSS Grid + ECharts 5.5.1 (vendored). One page, no framework, no build step.

## `public/index.php` — the shell (63 lines)
Static HTML skeleton, filled by JS. Key IDs (JS hooks): `#search-input`, `#search-results`, `#as-of`, `#freshness-banner` / `#freshness-banner-text`, `#app-main`, `#landing`, `#app-footer` / `#footer-disclaimer` / `#footer-engine-stat`. Scripts loaded in order: `vendor/echarts.min.js` → `chart.js` → `app.js`. Asset tags cache-bust via a `filemtime` helper (`asset_v()`) so JS edits reflect without hard reload.

## `public/assets/app.js` (~496 lines) — orchestration
- **Data source switch:** `getSymbolPayload(sym)` / `getSearchResults(q)` are the single fetch functions. `DEV_FIXTURES = false` (live API). Fixture branch is dead code kept for reference — leave it.
- **Routing:** URL hash = deep link. `hashchange` → `loadFromHash()` → `loadSymbol(sym)`. Empty hash → `showLanding()`. Refresh/share on `#OGDC` deep-loads.
- **Search:** debounced (~150 ms) typeahead on 2+ chars. `state = {activeIndex, results, debounceTimer}`. Keydown on the input: ArrowDown/Up → `moveActive()` (adds `.active` class), Enter → `state.results[activeIndex] || results[0]`, Escape → `closeResults()`. `aria-expanded` toggled. Selecting sets `location.hash`.
- **Render pipeline** (`renderPayload`): `meta.found === false` → `renderNotFound`. Else set as-of, freshness banner (`meta.warnings`), then build the panel grid and call: `renderSignalBanner`, `renderFundamentals`, `renderNews`, `renderHistory`, `renderFooterStat`, and `window.PSXChart.render(chartPanel, payload)`.
- **States built first:** skeleton loaders (`renderSkeleton`), not-found empty-state, data-error, per-panel empty states. Happy path last.
- **Signal banner:** signal chip (color+text), conviction pips `●●○ n/3`, stat row (close/RSI/yield/pos52), verbatim `why`, ⓘ factor-glossary popover (hardcoded factor definitions, keyboard-openable), STALE chip when `diligence != "OK"` OR unreviewed material filing.
- **History table:** ✓ HIT (green) / ✗ MISS (red) / ⏳ PENDING (neutral + `grade_on_date`). Hover a graded row → `result_detail` grader text.
- **News:** `[market-wide]` tag when `match === "macro"`.

## `public/assets/chart.js` (~648 lines) — `window.PSXChart.render(container, payload)`
ECharts candlestick from **adjusted** OHLC. Two modes, persisted in localStorage:
- `LS_KEY = "psx_dashboard_chart_mode"` → `"simple"` (default) / `"analyst"`.
- `LS_KEY_MARKERS = "psx_dashboard_signal_markers"` → markers ON unless `"off"`.
- `RANGE_DAYS = { 6M:126, 1Y:252, 2Y:504, Max:Infinity }`. Range toggle re-slices client-side; `paint()` does a full `setOption(true)` rebuild.

**Simple mode (default):** candles; MA20/50/200 labeled *"1-month / 3-month / long-term trend"*; derived trend-summary sentence; volume subchart + 20-day avg + heavy-day annotations; floor/ceiling markLines (`support`/`resistance`); 52-week shaded band + caption; RSI heat chip (overheated/normal/beaten-down); ATR "typical daily move" caption; 💰 dividend markers parsed from `fundamentals.payouts[].ex_or_bc` (range start date); past-signal markers ▲BUY/▼SELL/◆HOLD colored by outcome (U8).

**Analyst mode (toggle):** adds RSI(14) subchart (30/70 bands) + Bollinger(20,2). **No MACD** (engine doesn't use it — only-what-the-engine-reasons-with rule).

**Zoom (added 2026-07-04):** `dataZoom` = `inside` (wheel/pinch/drag-pan) + `slider` (visible control below subcharts). Both span all x-axes: Simple `[0,1]`, Analyst `[0,1,2]` (RSI zooms in sync). Range-button click rebuilds → resets zoom window to the new slice (no dispatch needed). Grid heights trimmed + canvas heights (460 simple / 600 analyst, in `styles.css`) sized to seat the slider.

**Tooltip:** axis-triggered; OHLC + volume, `raw_close` when it differs, and appended past-signal info (glyph + signal + result + result_detail + why) when a marker sits on the hovered bar.

## `public/assets/styles.css` (~526 lines) — design tokens
Dark default (`color-scheme: dark`) with a `:root[data-theme="light"]` override. Token groups in `:root`:
- **Backgrounds:** `--bg-0..3`, `--border`, `--border-soft`.
- **Text tiers:** `--text-1` (primary) / `--text-2` / `--text-3` (muted).
- **Signal:** `--buy #2fbf71` / `--hold #d8a441` / `--sell #e0555e` (+ `-bg` variants). **Candles:** `--up`=buy green, `--down`=sell red (PSX convention).
- **States:** `--warn` (freshness), `--stale`, `--accent #4c8dff`, `--focus-ring`.
- **Scale:** `--radius-s/m/l`, `--space-1..6`, `--font-ui`, shimmer colors.

**Accessibility:** never color alone — signal chip carries text, history carries ✓/✗/⏳ glyphs; `focus-visible` on search + toggles; tabular numerals on price/stat columns.

**Responsive** (`.layout-grid` carries the column grid, NOT `#app-main`):
- ≥1200px: two columns — chart left ~65% / side panels right (verified `895px / 466px` at 1440). Side panels split via `.side-two-col` (`1fr 1fr`).
- 768–1199px: chart full-width; fundamentals + news side-by-side below.
- <768px: single column; `#chart-canvas` height drops to 320px. Verified no horizontal scroll at 375px.

## Where to make common changes
| Want to… | Edit |
|---|---|
| Tune news relevance | `api/lib/sector_keywords.php` (BE) |
| Add/adjust a chart indicator | `chart.js` (must be something the engine reasons with) |
| Change colors/spacing | `styles.css` `:root` tokens |
| Add a payload field | `symbol.php` → then `app.js`/`chart.js` + PLAN §13 bump |
| Change signal/history rendering | `app.js` render functions |
