# Architecture

## Decisions (D1–D7)

| # | Decision | Why |
|---|---|---|
| D1 | **Server = PHP built-in** (`php -S`) | Confirmed installed (8.5.1). Zero-dep, one-command. |
| D2 | **Read flat files, NOT `psx.db`** | `psx.db` only holds *legacy portfolio* tables (predictions/trades/thin prices_eod). It does **not** ingest the universe engine. Real data is in `data/*.json` + `data/*.csv`. |
| D3 | **`dashboard_feed.json` = primary signal source** | Pipeline pre-computes per-symbol signal + MA/RSI/S-R/why for all 100. Effectively a ready-made API payload (~70 KB). |
| D4 | **Charting = Apache ECharts, vendored** | One lib covers candles + MA + S/R markLines + signal markPoints + volume subchart + dark mode. Apache-2.0. No CDN → offline. Pinned **5.5.1**. |
| D5 | **Isolated `dashboard/` subfolder** | Pure read-only consumer; deletable without side effects on the training loop. |
| D6 | **Read-only contract** | `DATA_DIR` opened read-only. No file in `data/` is ever written. `data.php` contains **no write helpers by construction**. |
| D7 | **No browser caching of API responses** | Data changes daily. API sends `Cache-Control: no-store`. Static assets cache normally (cache-busted via `filemtime`). |

## Folder layout (as built)

```
dashboard/
  PLAN.md                     ← locked engineering spec (v1.3)
  README.md                   ← run instructions + pinned ECharts version
  serve.ps1 / serve.sh        ← php -S localhost:8000 -t public
  config.php                  ← DATA_DIR resolver, api_headers(), SYM_PATTERN  [OUTSIDE docroot]
  docs/                       ← THIS folder
  fixtures/                   ← symbol_OGDC.json, symbol_EFERT.json (dev reference payloads; NOT in runtime path)
  api/
    lib/
      data.php                ← read-only JSON/CSV/JSONL readers + data_path()  [OUTSIDE docroot]
      sector_keywords.php     ← symbol→sector map + news matcher               [OUTSIDE docroot]
  public/                     ← DOCROOT (php -S -t public)
    index.php                 ← single-page shell (header/search/banner/main/footer)
    api/
      symbol.php              ← GET ?sym=OGDC → merged payload (core deliverable)
      search.php              ← GET ?q=og → typeahead list
    assets/
      app.js                  ← fetch + render orchestration, routing, search
      chart.js                ← ECharts candlestick builder (window.PSXChart)
      styles.css              ← dark-default theme tokens, responsive grid
      vendor/echarts.min.js   ← vendored ECharts 5.5.1 (Apache-2.0)
```

## Routing (the important structural choice)
`php -S` serves ONE docroot. Chosen **option (b)**: docroot = `public/`. API endpoints live at `public/api/*.php` (URL-reachable). Shared code — `config.php`, `api/lib/data.php`, `api/lib/sector_keywords.php` — lives **outside** the docroot and is pulled in via relative `require`:

```php
// public/api/symbol.php
require __DIR__ . '/../../config.php';
require __DIR__ . '/../../api/lib/data.php';
require __DIR__ . '/../../api/lib/sector_keywords.php';
```

Result: `lib/` and `config.php` are **not URL-reachable** (requesting `/config.php` returns the SPA `index.php`, never the PHP source). Verified in QA.

## Request flow

```
Browser (index.php SPA)
  │  URL hash change (#OGDC)  ────────────► loadSymbol("OGDC")
  │
  ├─ GET /api/search.php?q=og    ──► universe.json         ──► [{ticker,name}, …]
  └─ GET /api/symbol.php?sym=OGDC ──► dashboard_feed.json  (signal + indicators + as_of)
                                    ├► ohlc/OGDC.json        (adjusted candles)
                                    ├► universe_signals.csv  (graded history, filtered)
                                    ├► fundamentals/OGDC.json (EPS/payouts)
                                    ├► news_archive.jsonl     (sector/symbol relevance)
                                    └► diligence_ledger.json  (filings, STALE trigger)
                                    ──► merged §6.2 JSON payload
  │
  ├─ app.js renders: signal banner, fundamentals, news, history panels
  └─ chart.js (window.PSXChart.render) builds the ECharts candlestick from payload.ohlc
```

Every request re-reads the live files (no caching). One symbol = 1 feed read + 5 small file reads + 1 CSV scan (600 rows). Trivially fast on localhost.

## Hard rules (do not violate)
1. **Read-only `data/`** — the dashboard never writes there. `data.php` has no write helpers (D6).
2. **API contract changes go through PLAN.md** — bump the §13 changelog if you touch `/api/symbol.php` or `/api/search.php` payload shapes.
3. **No CDN** — ECharts is vendored. A strict-offline test must still render charts.
4. **`Cache-Control: no-store` on all API responses** (D7) — a cached yesterday-payload silently lies.
5. **Symbol input sanitized** — `^[A-Z0-9]{1,12}$`, resolved within `DATA_DIR` only (traversal guard in `data_path()`).
6. **Dev-server only** — `php -S` is not hardened for public hosting. Local single-user is the v1 assumption.
