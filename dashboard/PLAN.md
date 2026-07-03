# PSX Dashboard — v1 Engineering Plan

**Status:** 🔒 **LOCKED 2026-07-03 — approved for implementation.** Scope/contract changes hereafter only via Lead + changelog bump; no side-channel edits.
**Owner:** Ahmad (product) · Lead/Architect (execution, §12)
**Doc version:** 1.3-locked (2026-07-03) — see changelog §13
**Target:** First shippable dashboard — single-symbol deep view
**Confirmed environment:** PHP 8.5.1 (CLI) + Python 3.12 venv both present on dev machine. Windows 11.

---

## 1. Goal (one sentence)

A lightweight, locally-served web dashboard where a user types a KSE-100 symbol into a search bar and sees, on one page, that stock's **candlestick chart, fundamentals, relevant news, current engine signal, and graded signal history** — read live from the training pipeline's existing data files, with **zero changes to the pipeline**.

**Product north star** (from project mandate): the eventual dashboard is *chart + indicators + support/resistance + current signal + **history of past signals per symbol***. v1 builds the single-symbol slice of exactly that.

## 2. Scope

### In scope (v1)
- Single-symbol deep view driven by a search bar (typeahead).
- Five panels: **candlestick (hero)**, current signal, fundamentals, news, signal history.
- Past-signal markers plotted on the candlestick (stretch ticket U8 — cut first if schedule slips).
- Lightweight PHP dev server in its own isolated subfolder (`dashboard/`).
- Read-only consumption of pipeline flat files. No writes to `data/`.

### Out of scope (v2+ — backlog, §9)
- Universe overview grid (all 100 signals on one page).
- Cross-symbol filtering / scans.
- ML-model & ensemble signal columns (engine layer not built yet in pipeline).
- SQLite-backed queries (see §4.3 — deliberately deferred).
- Auth, multi-user, deployment/hosting, real-time push.

## 3. Key architectural decisions (already made)

| # | Decision | Rationale |
|---|---|---|
| D1 | **Server = PHP built-in server** (`php -S`) | Confirmed installed (8.5.1). Zero-dep, one-command launch. |
| D2 | **Read flat files, NOT `psx.db`** | `psx.db` only holds *legacy portfolio* tables (`predictions`, `trades`, thin `prices_eod`). It does **not** ingest the universe engine. Real data is in flat files (§4.1). |
| D3 | **`dashboard_feed.json` is the primary signal source** | Pipeline already pre-computes per-symbol signal + MA/RSI/S-R/why for all 100. It's effectively a ready-made API payload (~70 KB total). |
| D4 | **Charting = Apache ECharts, vendored locally** | One lib covers candles + MA overlays + support/resistance markLines + signal markPoints + volume subchart, good dark mode. Apache-2.0 license. No CDN → offline, matches pipeline "no external fabrication" ethos. Pin the version (5.x latest at vendor time) and record it in README. |
| D5 | **Isolated `dashboard/` subfolder** | Dashboard is a pure read-only *consumer*; never touches training loop. Deletable without side effects. |
| D6 | **Read-only contract** | `DATA_DIR` opened read-only. No file in `data/` is ever written by the dashboard. |
| D7 | **No browser caching of API responses** | Data changes daily (pipeline run). API sends `Cache-Control: no-store`; a cached yesterday-payload silently lies to the user. Static assets may cache normally. |

## 4. Data layer (the important part)

### 4.1 Source files (all already produced by the pipeline)

| Panel | File | Shape / notes | Verified |
|---|---|---|---|
| Candlestick | `data/ohlc/{SYM}.json` | Array of bars `{date,open,high,low,close,volume,adj_factor,adj_open,adj_high,adj_low,adj_close}`. ~1243 bars (5yr) e.g. OGDC. **Use `adj_*` fields for split continuity.** 101 files (100 symbols + `KSE100` index). | ✅ 1243 bars OGDC |
| Current signal + indicators | `data/dashboard_feed.json` | `symbols[SYM]` → `{name,date,close,signal,conviction,score,ma20,ma50,ma200,rsi,pos52,eps_trend,yield_pct,mom20,support,resistance,diligence,why,factors{}}`. 100 symbols. `_meta` has counts, as-of date (`_generated`), disclaimer note. ~70 KB. | ✅ 100 symbols |
| Signal history (graded + pending) | `data/universe_signals.csv` | Append-only, 1 row/symbol/run. Cols incl `date,symbol,signal,conviction,score,close,...,grade_on_date,status,result,why,f_*`. 6 batches present (06-23 → 07-03). **`status` ∈ `{graded, open}`** — 06-23/06-24 graded, 06-29→07-03 open (not matured). `result` empty when open; when graded holds `"HIT: …"` / `"MISS: …"` free text **containing commas inside quotes** (128/600 rows). | ✅ 600 rows, 100 syms, 6 dates, statuses confirmed |
| Fundamentals | `data/fundamentals/{SYM}.json` | `{symbol,fetched,quarterly_results[{announced,period,period_type,consolidated,eps,pat,pbt,payout_note}],payouts[{announced,period_type,type,pct,interim_label,ex_or_bc}]}`. ~97/100 present. | ✅ OGDC full |
| News | `data/news_archive.jsonl` | One JSON/line `{headline,source,lens,impact,_snapshot}` (some lines also carry `date`). Symbols mentioned **inside headline/impact text** (e.g. "OGDC", "E&P", "cement") — no structured symbol field. | ✅ grep confirms |
| Filings / STALE | `data/diligence_ledger.json` | `filings[{symbol,date,doc_id,title,pdf_url,in_universe,materiality,classify_reason,reviewed,review_notes}]`. Drives STALE badge. | ✅ present |
| Engine stats (footer/badge) | `data/rolling_stats.json` | Hit-rate by predictor/batch under `engine.rule_scorecard`. Optional in v1 (nice-to-have header stat). | ✅ present (69%, 200 graded) |
| Symbol list (typeahead) | `data/universe.json` | `symbols[{ticker,name}]`, 100 entries. | ✅ present |

### 4.2 News→symbol relevance (design note for TICKET-D3)
News has **no structured symbol tag**. v1 relevance rule (simple, good enough):
1. Headline or `impact` text contains the ticker (word-boundary, case-insensitive), **OR**
2. Text contains a **sector keyword** mapped from the symbol's sector (e.g. E&P → OGDC/PPL/MARI; cement → LUCK/DGKC/MLCF/CHCC; banks → ABL/MEBL/UBL/MCB/HBL/FABL; OMC → PSO/APL; fertilizer → FFC/EFERT/ENGROH).
Maintain a small `sector_keywords.php` map. Fallback: show latest N market-wide macro items flagged `lens:"E"`, visually labeled "market-wide". **Do not over-engineer NLP in v1.**

### 4.3 Why not SQLite in v1
`psx.db` doesn't contain engine data (D2), and single-symbol lookups from flat files are trivially fast (one JSON read + one CSV filter over 600 rows). SQLite only pays off for *cross-universe* queries (v2 overview/scan). **Deferred, not rejected** — §9 backlog includes a `build_db.py` extension to ingest signal logs first.

### 4.4 Data gotchas (MUST-read for DATA epic — each one has bitten this repo before)

| # | Gotcha | Rule for engineers |
|---|---|---|
| G1 | **CSV fields contain commas inside quotes** (`result`, `why` — 128/600 rows verified). | Parse with `fgetcsv()` only. Never `explode(',')`. AC on D1 covers this. |
| G2 | **Recent signal batches are ungraded** (`status=open`, empty `result`) — currently 400/600 rows. | History rows carry three states: `HIT` / `MISS` / `PENDING (grades <grade_on_date>)`. UI must render PENDING as first-class, not error/blank. |
| G3 | **Feed date vs OHLC last-bar date can diverge** (real incident 2026-07-03: midnight-spanning run mislabeled a batch; fixed in pipeline, but the failure mode exists). | `symbol.php` compares `dashboard_feed._meta._generated` to the symbol's last OHLC bar date; on mismatch emit `meta.warnings[]` → UI shows amber "data freshness" banner. Cheap, catches real bugs. |
| G4 | **Pipeline rewrites feed files during its daily run** — a page load mid-run can read a half-written JSON. | Readers: read whole file → `json_decode` → on parse failure retry once after 200 ms → then return `data_unavailable` error payload. Never crash to PHP warning HTML. |
| G5 | **Raw `close` has cliffs at splits/bonuses.** | Chart from `adj_*` fields always. Tooltip may show raw close as secondary. |
| G6 | **CSV may gain columns over time** (pipeline evolves; e.g. model/ensemble cols planned). | Map by header name, never by column index. |
| G7 | **~3/100 symbols lack fundamentals**; some lack news matches. | Every panel needs a designed empty-state (§7.2). Missing file ≠ error. |
| G8 | **`KSE100.json` exists in ohlc/ but is an index, not a stock** — no signal/fundamentals. | Exclude from search results in v1 (open question §11 for a header index sparkline). |

## 5. Folder layout (new, isolated)

```
psx-analyst-agent/
  dashboard/                      ← NEW, self-contained, git-tracked
    PLAN.md                       ← this doc
    README.md                     ← run instructions + pinned ECharts version
    serve.ps1  /  serve.sh        ← `php -S localhost:8000 -t public`
    config.php                    ← defines DATA_DIR (../data), constants
    public/
      index.php                   ← single-page shell
      api/ → (router or copy)     ← see routing note below
      assets/
        app.js                    ← fetch + render orchestration
        chart.js                  ← ECharts candlestick builder
        styles.css                ← dark theme, responsive grid
        vendor/echarts.min.js     ← vendored, no CDN
    api/
      symbol.php                  ← GET ?sym=OGDC → merged symbol payload
      search.php                  ← GET ?q=og → typeahead list
      lib/
        data.php                  ← read-only JSON/CSV/JSONL readers + DATA_DIR resolver
        sector_keywords.php       ← symbol→sector keyword map (news relevance)
```

**Routing note (I1):** `php -S` serves one docroot. Two acceptable options — (a) docroot = `dashboard/` with `public/index.php` path rewrite via a small `router.php`, or (b) simplest: put `api/` under `public/api/` and keep `lib/` + `config.php` **outside** docroot, required via relative path. Option (b) recommended; decide in I1, document in README.

## 6. API contract

**Common to both endpoints:** `Content-Type: application/json; charset=utf-8` · `Cache-Control: no-store` (D7) · `json_encode(..., JSON_UNESCAPED_UNICODE)` · PHP `display_errors=Off` for the API path so a warning never corrupts JSON (errors returned as structured payload, G4).

### 6.1 `GET /api/search.php?q=<str>`
Typeahead. Returns ≤10 matches from `universe.json`, ticker-prefix matches ranked first, then name-substring. `KSE100` excluded (G8).
```json
[{ "ticker":"OGDC", "name":"Oil & Gas Development Company Limited" }]
```
`?q=` or `q` <2 chars → `[]`.

### 6.2 `GET /api/symbol.php?sym=<TICKER>`
Merged single-symbol payload. **This is the core deliverable.**
```json
{
  "meta":    { "ticker":"OGDC", "name":"...", "as_of":"2026-07-03", "found":true,
               "warnings":[ "ohlc_last_bar 2026-07-02 != feed as_of 2026-07-03" ] },
  "signal":  { "signal":"BUY","conviction":3,"score":5,"close":319.11,
               "ma20":..,"ma50":..,"ma200":..,"rsi":64.7,"pos52":57.3,
               "yield_pct":10.7,"mom20":..,"support":..,"resistance":..,
               "eps_trend":"flat","diligence":"OK","why":"...","factors":{...} },
  "ohlc":    [ { "date":"2025-01-02","o":..,"h":..,"l":..,"c":..,"v":..,
                 "raw_close":.. }, ... ],
  "history": [ { "date":"2026-07-03","signal":"BUY","status":"open",
                 "result":"PENDING","grade_on_date":"2026-07-10","why":"..." },
               { "date":"2026-06-23","signal":"HOLD","status":"graded",
                 "result":"HIT","result_detail":"HIT: stayed within …","why":"..." } ],
  "fundamentals": { "latest_eps":26.8,"latest_period":"IIIQ 31/03/2026","eps_trend":"...",
                    "quarterly_results":[...],"payouts":[...] },
  "news":    [ { "date":"2026-06-18","headline":"...","impact":"...","source":"...",
                 "match":"symbol|sector|macro" }, ... ],
  "filings": [ { "date":"2026-06-29","title":"...","materiality":"NON_MATERIAL",
                 "reviewed":true,"pdf_url":"..." }, ... ]
}
```
Contract details:
- `ohlc.o/h/l/c` = the **adjusted** series (G5); `raw_close` included for tooltip.
- `history[].result` normalized to enum `HIT|MISS|PENDING`; original grader text preserved in `result_detail` (G2). Sorted newest-first.
- `news[].match` tells the UI whether the item matched by ticker, sector keyword, or macro fallback (drives the "market-wide" label).
- Unknown symbol → `200` with `{"meta":{"found":false,"ticker":"XYZ"}}` (frontend shows empty-state, not a 404 crash).
- Data-layer failure (G4) → `200` with `meta.found:true` + `meta.warnings[]` + whichever sections loaded; a section that failed is `null`.

**OHLC payload sizing:** ship the full series (~1243 bars ≈ 150–200 KB JSON — fine for localhost and well under ECharts limits). Range toggle slices client-side, zero refetch. Simpler than trim+lazy-load; revisit only if payload measured >1 MB.

## 7. UI / UX specification

### 7.1 Layout (desktop, ≥1200px)
```
┌──────────────────────────────────────────────────────────────┐
│  PSX ENGINE            [ 🔍 search symbol… ▾ ]     as of 07-03 │  ← header (sticky)
├──────────────────────────────────────────────────────────────┤
│  ⚠ data freshness warning banner (only when meta.warnings)    │
├──────────────────────────────────────────────────────────────┤
│  OGDC · Oil & Gas Development        ┃ SIGNAL  BUY   ●●● 3/3  │  ← signal banner
│  close 319.11   ▲trend  RSI 64  yld 10.7%  pos52w 57%         │
│  why: trend+1; 52w+1(57%); mom20+1; yld10.7%+1; rules+1  ⓘ    │
├───────────────────────────────────────┬──────────────────────┤
│                                       │  FUNDAMENTALS         │
│         CANDLESTICK (hero)            │  EPS 26.8 (IIIQ)      │
│    MA20 / MA50 / MA200 overlays       │  trend: flat          │
│    support & resistance markLines     │  Payouts:             │
│    ▲▼ past-signal markers (U8)        │   32.5% (iii) 05/2026 │
│    volume subchart below              │   42.5% (ii)  03/2026 │
│    range: [6M] [1Y] [2Y] [Max]        ├──────────────────────┤
│                                       │  NEWS (relevant)      │
│                                       │  • Brent <$80 …       │
│                                       │  • CA surplus [macro] │
├───────────────────────────────────────┴──────────────────────┤
│  SIGNAL HISTORY                                                │
│  date     signal   result              why                    │
│  07-03    BUY      ⏳ PENDING (07-10)  trend+1; …              │
│  06-24    BUY      ✓ HIT               …                       │
│  06-23    HOLD     ✓ HIT               trend-2; rsi+1; …       │
├──────────────────────────────────────────────────────────────┤
│  footer: engine hit-rate 69% (200 graded) · TRAINING ONLY —   │
│          not trade advice                                      │  ← disclaimer
└──────────────────────────────────────────────────────────────┘
```

### 7.2 UX rules
- **Landing state (no symbol):** search box centered + short "type a KSE-100 symbol" hint + 3 example chips (OGDC, LUCK, ABL). No blank page.
- **Search:** typeahead on 2+ chars, debounced ~150 ms; arrow-key + Enter selection; Esc closes. Last symbol kept in URL hash (`#OGDC`) so refresh/share works and deep-links load directly.
- **Loading:** skeleton shimmer on panels while `symbol.php` resolves.
- **Signal color:** BUY = green, HOLD = amber/neutral, SELL = red. Conviction as `●●○`-style pips + `n/3` text. `why` string rendered verbatim (transparency is a pipeline prime directive — never hide it).
- **Factor glossary:** ⓘ affordance next to `why` opens a small static tooltip/popover explaining each factor token (trend, rsi, 52w/pos52, mom20, eps, yield, rules) in one line each. Content hardcoded in frontend; no API.
- **STALE badge:** if `signal.diligence != "OK"` **OR** the ledger has an unreviewed **MATERIAL** filing for the symbol → red "STALE — open filing" chip in the signal banner, linking to the filings list. Precedence rule: either source alone triggers it. Non-negotiable (pipeline rule #7).
- **History states:** ✓ HIT (green) / ✗ MISS (red) / ⏳ PENDING (neutral, shows `grade_on_date`). Hover/tap a graded row → `result_detail` full grader text (G2).
- **Freshness banner:** amber, non-blocking, only when `meta.warnings` non-empty (G3).
- **Disclaimer:** persistent footer "Layer-1 engine signal · TRAINING ONLY, not trade advice" (pulled from `dashboard_feed._meta._note`). Required by project mandate.
- **Empty panels:** missing fundamentals/news/filings → panel shows a quiet "no data for this symbol" state; page still renders (G7).
- **News items** show `[market-wide]` tag when `match:"macro"` so sector/symbol items stand out.

### 7.3 Visual system
- Dark theme default (finance context). Design tokens in `styles.css` `:root` — bg layers, text tiers, `--buy/--hold/--sell`, `--up/--down` candle colors, spacing/radius.
- System font stack; tabular numerals (`font-variant-numeric: tabular-nums`) for price/stat columns.
- CSS Grid for panel layout.
- ECharts themed from same token palette. Candles: green up / red down (PSX convention).
- **Accessibility:** never color alone — signal chip carries text ("BUY"), history carries ✓/✗/⏳ glyphs, candle up/down distinguishable by fill vs hollow if feasible. Focus-visible styles on search + range toggles.

### 7.4 Chart indicators — designed for a non-trader (TICKET-U2/U8 spec)

**Principle:** a common man doesn't read oscillators; he reads plain English + pictures. Chart ships two modes — **Simple (default)** and **Analyst (toggle)**. Second principle (transparency): the chart only visualizes what the engine actually reasons with — no decorative indicators.

**Simple mode (default):**

| Indicator | Rendering / plain-language translation | Data source |
|---|---|---|
| MA20 / MA50 / MA200 | Three trend lines labeled **"1-month trend" / "3-month trend" / "long-term trend"** (legend shows both label + MA name) | computed client-side from OHLC |
| Trend summary strip | One derived sentence above the chart, e.g. *"Uptrend — price above all three trend lines"* / *"Weakening — fell below 1-month trend"* (simple rule table off MA relationships) | MA values |
| Volume bars + 20-day avg volume line | Up/down colored bars; days ≥2× avg auto-annotated *"heavy trading — Nx normal"* | OHLC volume |
| Support / Resistance | markLines labeled **"floor <price>"** / **"ceiling <price>"** | feed `support`/`resistance` |
| 52-week range band | Subtle shaded band between 52w low/high + caption *"trading at N% of its 1-year range"* | computed from OHLC; `pos52` for caption |
| RSI heat chip (no subchart) | Chip near chart title: **"overheated"** (RSI>70) / **"beaten down"** (RSI<30) / **"normal"** — tooltip reveals the number | feed `rsi` |
| Typical daily move | Caption *"normally moves ±X (Y%) per day"* — ATR(14)-based; sets expectations for laymen | computed from OHLC (ATR concept already pipeline-native — grader uses it) |
| **Dividend markers 💰** | markPoint at each ex-dividend date: *"32.5% dividend — price dip here is normal"* | `fundamentals.payouts[].ex_or_bc` (parse date range start) |
| Past-signal markers ▲▼◆ | Per U8 (stretch) | history |

**Analyst mode (toggle, persisted in localStorage):** adds RSI(14) subchart with 30/70 bands, Bollinger Bands(20,2), numeric values everywhere. **MACD deliberately excluded** — engine doesn't use it; showing it would violate the only-what-the-engine-reasons-with rule.

**Dividend-marker note:** ex-date price drops are mechanical, not losses (known pipeline grading gotcha). The marker copy must say so — this single feature answers most "why did it crash today?" confusion on a yield-heavy market like PSX.

### 7.5 Responsive
- ≥1200px: two-column (chart left ~65%, side panels right).
- 768–1199px: chart full-width; fundamentals + news side-by-side below.
- <768px: single column, chart height reduced, range toggle wraps. Test at 375px.

## 8. Tickets

> Epics: **INFRA** → **DATA** → **UI** → **QA**. Sizes: S ≈ ≤half-day, M ≈ 1 day, L ≈ 2 days.

### 8.1 Summary table (import-friendly)

| ID | Title | Epic | Size | Depends on |
|----|-------|------|------|-----------|
| I1 | Scaffold `dashboard/` + server + routing decision | INFRA | S | — |
| I2 | Vendor ECharts (pinned) | INFRA | S | I1 |
| D1 | Read-only data lib | DATA | M | I1 |
| D2 | `search.php` | DATA | S | D1 |
| D3 | News relevance map + filter | DATA | M | D1 |
| D4 | `symbol.php` core merge | DATA | L | D1, D3 |
| U1 | Shell + search + routing | UI | M | I1, D2 |
| U2 | Candlestick hero | UI | L | I2, D4, U1 |
| U3 | Signal banner + STALE + glossary | UI | M | D4, U1 |
| U4 | Fundamentals panel | UI | S | D4, U1 |
| U5 | News panel | UI | S | D4, U1 |
| U6 | Signal-history table (3 states) | UI | M | D4, U1 |
| U7 | Footer disclaimer + engine stat | UI | S | U1 |
| U8 | Past-signal markers on chart (STRETCH) | UI | M | U2, U6 |
| Q1 | Cross-symbol + edge-state verification | QA | M | all UI |

### 8.2 Ticket detail

#### Epic INFRA
- **TICKET-I1 — Scaffold `dashboard/`** (S)
  Folder tree (§5), `config.php` (`DATA_DIR` = realpath `../data`, constants), `serve.ps1`/`serve.sh` launching `php -S localhost:8000`, docroot/routing decision per §5 note, `README.md` with run steps.
  _AC:_ `./serve.ps1` starts server; `http://localhost:8000` serves placeholder `index.php`; `lib/` + `config.php` not directly URL-reachable.
- **TICKET-I2 — Vendor ECharts** (S)
  Download ECharts min build into `assets/vendor/`, pin + record version and license (Apache-2.0) in README. No CDN.
  _AC:_ chart lib loads offline (airplane-mode test); version documented.

#### Epic DATA
- **TICKET-D1 — Read-only data lib (`api/lib/data.php`)** (M)
  Helpers: `read_json(path)` (with G4 retry-once + structured failure), `read_jsonl(path)`, `read_csv(path)` (**`fgetcsv`, header-name mapping** — G1/G6), `data_path(rel)` resolver bounded to `DATA_DIR`; `sym` validated `^[A-Z0-9]{1,12}$` (path-traversal guard). No write helpers exist in this file, by design (D6).
  _AC:_ parses OGDC ohlc/fundamentals; CSV row with commas-in-quotes round-trips intact; rejects `sym=../x`; truncated-JSON simulation returns structured failure, not a PHP warning.
- **TICKET-D2 — `api/search.php`** (S)
  Load `universe.json`, prefix-first + substring match, exclude KSE100 (G8), cap 10, JSON out, headers per §6.
  _AC:_ `?q=og` returns OGDC first; `?q=`/1-char returns `[]`; `Cache-Control: no-store` present.
- **TICKET-D3 — News relevance (`sector_keywords.php` + filter)** (M)
  Symbol→sector keyword table (§4.2); matcher scans `headline`+`impact` (word-boundary, case-insensitive); each item tagged `match: symbol|sector|macro`; macro fallback = latest N `lens:"E"` items.
  _AC:_ OGDC news includes the "Brent <$80 … OGDC/PPL/MARI" item tagged `sector`/`symbol`; unrelated single-stock items excluded; symbol with zero matches still gets macro items tagged `macro`.
- **TICKET-D4 — `api/symbol.php` (core merge)** (L)
  Merge per §6.2: signal (`dashboard_feed`), full adjusted OHLC + `raw_close`, history (filter CSV by symbol; normalize `result` → `HIT|MISS|PENDING` + `result_detail`; include `status`, `grade_on_date`; newest-first — G2), fundamentals (+ derive latest EPS/period/trend), news (D3), filings (ledger). Freshness check → `meta.warnings` (G3). Unknown symbol → `found:false`. Partial data-layer failure → section `null` + warning (G4).
  _AC:_ `?sym=OGDC` full payload with 6 history rows (2 graded, 4 PENDING with correct `grade_on_date`); `?sym=ZZZ` → `found:false`; a STALE symbol and a SELL symbol verified; simulated ohlc-date mismatch produces the warning.

#### Epic UI
- **TICKET-U1 — Shell + search + routing (`index.php`,`app.js`,`styles.css`)** (M)
  Header, sticky search w/ debounced typeahead + keyboard nav (calls D2), URL-hash routing (`#OGDC`), landing empty-state + example chips, skeleton loaders, design tokens (§7.3), responsive grid (§7.5), freshness-banner slot.
  _AC:_ typing + arrow/Enter loads a symbol; refresh on `#OGDC` deep-loads; 375px stacks cleanly.
- **TICKET-U2 — Candlestick hero (`chart.js`)** (L)
  ECharts candlestick from adjusted `ohlc`, implementing the **Simple-mode indicator spec §7.4**: plain-labeled MA20/50/200 ("1-month/3-month/long-term trend"), trend summary strip, volume subchart + 20d avg + heavy-day annotations, floor/ceiling markLines, 52-week range band + caption, RSI heat chip, typical-daily-move caption, 💰 dividend markers from payouts. **Analyst-mode toggle** (localStorage-persisted): RSI subchart + Bollinger(20,2). Range toggle 6M/1Y/2Y/Max slicing client-side (no refetch); dark theme from tokens; tooltip shows OHLC + volume (+ `raw_close` when it differs). No MACD (§7.4).
  _AC:_ OGDC renders candles + 3 labeled MAs + floor/ceiling + volume + dividend markers at correct ex-dates; trend strip sentence matches MA state; RSI chip states correct at <30/30–70/>70; Analyst toggle adds RSI panel + Bollinger and survives reload; toggles re-slice instantly; no perf jank at Max (1243 bars).
- **TICKET-U3 — Signal banner + STALE + factor glossary** (M)
  Ticker+name, signal chip, conviction pips, stats row (close/RSI/yield/pos52), verbatim `why`, ⓘ factor glossary popover, STALE badge per §7.2 precedence rule (links to filings).
  _AC:_ BUY green / SELL red / HOLD amber with text labels; STALE chip on diligence≠OK **or** unreviewed material filing; glossary opens/closes via mouse + keyboard.
- **TICKET-U4 — Fundamentals panel** (S)
  Latest EPS + period + trend; quarterly results list; payout history (pct, interim label, ex-date); empty-state (G7).
  _AC:_ OGDC shows EPS 26.8 + payouts; fundamentals-less symbol shows graceful empty-state.
- **TICKET-U5 — News panel** (S)
  Items newest-first: headline + impact + source + date + `[market-wide]` tag for macro matches.
  _AC:_ OGDC shows E&P/oil items untagged, macro items tagged; panel never empty while macro news exists.
- **TICKET-U6 — Signal-history table** (M)
  Rows newest-first: date / signal / result (✓HIT green, ✗MISS red, ⏳PENDING neutral + grade date) / why. Hover reveals `result_detail`. The credibility panel — grades shown honestly, including pending.
  _AC:_ OGDC shows 6 rows — 2 graded correctly colored, 4 PENDING with grade dates; hover shows grader text.
- **TICKET-U7 — Footer disclaimer + engine stat** (S)
  Persistent disclaimer (from `_meta._note`); optional hit-rate from `rolling_stats.json` ("69% · 200 graded" style).
  _AC:_ disclaimer always visible; stat renders when file present, absent gracefully otherwise.
- **TICKET-U8 — Past-signal markers on candlestick (STRETCH)** (M)
  Plot history rows as `markPoint`s on the candle chart at their signal dates (▲ BUY / ▼ SELL / ◆ HOLD-small), colored by outcome (green/red/neutral-pending); tooltip = signal + result + why. Directly serves the product north star (§1). Cut first if v1 slips.
  _AC:_ OGDC shows 6 markers at correct dates; marker tooltip matches history table; toggleable on/off.

#### Epic QA
- **TICKET-Q1 — Cross-symbol + edge-state verification** (M)
  Verify 5 representative symbols: a BUY (OGDC), a SELL (from `_meta`), a STALE/filing symbol, a fundamentals-missing symbol, a low-history symbol. Plus: mid-pipeline-write simulation (G4), freshness-warning simulation (G3), 375/768/1440px widths, Chrome + Edge, keyboard-only pass on search.
  _AC:_ all panels render for all five; zero console errors; PENDING rows everywhere current batches appear; screenshots attached to ticket.

## 9. Backlog (v2+)
- Universe overview tab: 100-signal grid, buy/hold/sell counts, sortable, sector heatmap.
- Cross-symbol scans/filters (RSI<30, yield>10%, BUY+conv3, STALE-only …).
- **Extend `build_db.py`** to ingest `universe_signals.csv` (+ model/ensemble when built) → then move API to SQLite for fast cross-universe queries.
- ML-model & ensemble signal columns once `universe_model.py` exists (pipeline TODO #4).
- KSE100 index sparkline in header (data already in `ohlc/KSE100.json`; see §11).
- EPS quarterly mini-bar-chart in fundamentals panel.
- Compare view (2 symbols side by side); watchlist persistence.
- Packaging / always-on local service; optional auth if shared.

## 10. Risks & notes
- **News tagging is heuristic** (no structured symbol field). Accept imperfect recall in v1; `match` tag makes quality visible; revisit if noisy. (§4.2)
- **`prices_eod` in `psx.db` is a trap** — thin/stale, not the OHLC store. Use `data/ohlc/*.json`. (D2)
- **Split adjustments** — chart `adj_*` always; raw close has cliffs. (G5)
- **Concurrent pipeline writes** can yield torn reads once a day. Mitigated by G4 retry + structured failure; residual risk accepted for v1 (single local user).
- **Browser caching of stale daily data** — mitigated by D7 `no-store`.
- **Read-only is a hard rule** — dashboard never writes `data/`; `data.php` contains no write helpers by construction. (D6)
- **Symbol input sanitization** — `^[A-Z0-9]{1,12}$`, resolved within `DATA_DIR` only. (D1)
- **Dev-server only** (`php -S`) — not hardened for public hosting; local single-user is the v1 assumption. Revisit before any sharing/deployment.
- **CSV growth** — 100 rows/day appended; ~36k rows/yr. Linear scan stays fine for months; SQLite ingest (§9) is the escape hatch, no v1 action.

## 11. Open questions — **RESOLVED AT LOCK: defaults apply**
1. Header KSE100 index sparkline in v1? → **No — backlog.**
2. U8 (chart signal markers) in or out of v1? → **Attempt after U6; cut first on slip.**
3. Port? → **8000.**

## 12. Team structure & agent personas

> Works for a human team or an AI-agent team (Claude Code subagents). Roles are identical; for agents, the **model tier** column applies the project's standing rule: *cheap models for grunt work, top model for architecture/review* — don't burn Opus-class tokens on boilerplate.

### 12.1 Team split — two parallel workstreams + spine

```
                 ┌──────────────────────────┐
                 │  LEAD / ARCHITECT (spine) │  owns plan, contracts, reviews, cut-line
                 └───────┬──────────┬───────┘
             ┌───────────┘          └───────────┐
   ┌─────────▼─────────┐              ┌─────────▼─────────┐
   │  TEAM DATA        │              │  TEAM UI          │
   │  Backend Agent    │              │  Frontend Agent   │
   │  I1 D1 D2 D3 D4   │              │  U1 U3 U4 U5 U6 U7│
   └─────────┬─────────┘              │  Chart Specialist │
             │                        │  I2 U2 U8         │
             │      API contract §6   └─────────┬─────────┘
             └────────= boundary =──────────────┘
                          │
                 ┌────────▼────────┐
                 │  QA / VERIFIER  │  Q1 + gate on every merge
                 └─────────────────┘
```

**Parallelization key:** the API contract (§6) is the *only* interface between teams. Team UI does **not** wait for D4 — Lead produces `fixtures/symbol_OGDC.json` (a hand-built §6.2-conformant payload, incl. PENDING rows and a `warnings` example) on day 1; UI builds against the fixture, swaps to live API when D4 lands. Contract changes go through Lead only — no side-channel field additions.

### 12.2 Roles, personas, ownership

| Role | Persona / mindset | Speciality | Owns tickets | Reviews | Agent model tier |
|---|---|---|---|---|---|
| **Lead / Architect** | Skeptical integrator. Trusts nothing until run. Guards the two hard rules: read-only `data/`, contract-only cross-team changes. Decides cut-line (U8, §11). | System design, API contract, data-layer semantics (§4), merge review | Contract fixtures; §11 decisions | Everything (final) | Top tier (Opus-class) |
| **Backend Agent** (Team DATA) | Defensive parser. Assumes every file can be half-written, mis-quoted, or missing (§4.4 is their bible). Never adds a write path. Prefers boring PHP over clever PHP. | PHP, CSV/JSON/JSONL parsing, input validation, HTTP semantics | I1, D1, D2, D3, D4 | UI's API-consumption code | Mid tier (Sonnet-class) |
| **Frontend Agent** (Team UI) | Design-token purist + a11y advocate. Builds every state first (empty, loading, PENDING, STALE, warning) — happy path last. No inline styles, no color-only meaning. | Vanilla JS, CSS Grid, responsive, keyboard a11y, skeleton/empty states | U1, U3, U4, U5, U6, U7 | Chart Specialist's DOM/CSS integration | Mid tier (Sonnet-class) |
| **Chart Specialist** (Team UI) | ECharts deep-diver. Thinks in series/axes/markLine/markPoint. Obsesses over perf at 1243 bars and tooltip correctness (adjusted vs raw close). | ECharts candlestick, overlays, markers, client-side slicing, canvas perf | I2, U2, U8 | Frontend's chart-adjacent code | Mid tier (Sonnet-class) |
| **QA / Verifier** | Adversarial user. Tries the STALE symbol, the fundamentals-less symbol, the torn read, 375px, keyboard-only — before ever trying OGDC-happy-path. Screenshots or it didn't happen. | Playwright-driven browser verification (Playwright MCP already configured in this repo), edge-state simulation | Q1 + per-merge smoke pass | — (verifies all) | Low/mid tier (Haiku/Sonnet-class) |

### 12.3 Working agreements
1. **Contract freeze:** §6 payload shapes change only via Lead + doc edit here (bump changelog). Fixture regenerates same commit.
2. **Definition of done per ticket:** AC met + QA smoke pass + Lead review. No self-merges.
3. **Gotcha ownership:** every §4.4 gotcha has a test or simulation owned by Backend (G1–G6) or QA (G3/G4/G7 end-to-end).
4. **Sequencing:** Day 1 = I1 (Backend) + fixture (Lead) + U1-start (Frontend) + I2 (Chart). D-track and U-track proceed in parallel per §8.1 deps; integration point = D4×U1 swap-to-live; U8 last, cuttable.
5. **Agent-execution note:** if run as Claude Code subagents, spawn one agent per role with this doc + only their epic's tickets in the prompt; Lead runs in the main session. QA uses Playwright MCP against `localhost:8000`.

## 13. Changelog
- **LOCK (2026-07-03)** — Plan approved by Ahmad and locked for implementation (next session). §11 open questions resolved to their defaults. Any further change requires Lead sign-off + a changelog entry here.
- **1.3 (2026-07-03)** — Added §7.4 chart-indicator spec for non-traders: Simple mode (default) with plain-language indicators — labeled trend lines, derived trend-summary sentence, volume-vs-normal annotations, floor/ceiling wording, 52-week range band, RSI as heat chip (no oscillator), ATR "typical daily move" caption, 💰 ex-dividend markers (from payouts; also demystifies mechanical ex-date drops) — plus Analyst-mode toggle (RSI subchart, Bollinger; MACD excluded — engine doesn't use it). U2 ticket + AC rewritten to this spec (if U2 overruns, split Analyst mode into a follow-up ticket). Responsive renumbered §7.4→§7.5.
- **1.2 (2026-07-03)** — Added §12 team structure: two parallel workstreams (DATA / UI) + Lead spine + QA gate; five role personas with specialities, ticket ownership, review matrix, and agent model tiers (cheap models for grunt work, top tier for architecture/review); fixture-first contract so UI never blocks on D4; working agreements incl. contract freeze + Playwright-MCP-driven QA. Renumbered changelog to §13.
- **1.1 (2026-07-03)** — Review pass: added PENDING signal state (G2 — 400/600 rows are ungraded; original spec only handled HIT/MISS); mandated `fgetcsv` (G1 — 128 rows have commas in quotes); added §4.4 gotchas incl. freshness guard (G3, from the real 07-03 midnight-rollover incident) and torn-read handling (G4); HTTP/caching contract (D7, §6 preamble); ticket sizes + dependency table; new stretch ticket U8 (past-signal markers on chart — product north star); factor glossary + news `match` tag + keyboard a11y in UX; expanded Q1; open questions; removed stray trailing code fence.
- **1.0 (2026-07-03)** — Initial plan.
