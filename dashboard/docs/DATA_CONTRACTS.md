# Data Contracts

## Source files (all produced by the pipeline; dashboard only reads them)

All paths relative to `data/` (= `DATA_DIR`, resolved as `realpath(__DIR__/../data)` in `config.php`).

| Consumed for | File | Shape / notes |
|---|---|---|
| Current signal + indicators | `dashboard_feed.json` | `{_meta:{_generated,_symbols,_buy,_hold,_sell,_note}, symbols:{SYM:{name,date,close,signal,conviction,score,ma20,ma50,ma200,rsi,pos52,eps_trend,yield_pct,mom20,support,resistance,diligence,why,factors{trend,rsi,pos52w,mom20,eps,yield,rules}}}}`. 100 symbols. `_generated` = as-of date. **Primary signal source.** |
| Candlestick | `ohlc/{SYM}.json` | Array of bars `{date,open,high,low,close,volume,adj_factor,adj_open,adj_high,adj_low,adj_close}`. ~1200–1243 bars (5yr). **Use `adj_*` for split continuity (G5).** 101 files (100 symbols + `KSE100` index). |
| Signal history (graded + pending) | `universe_signals.csv` | Append-only, 1 row/symbol/run. Cols: `date,symbol,signal,conviction,score,close,…,grade_on_date,status,result,why,f_*`. 100 rows/run. `status ∈ {graded, open}`. `result` empty when open; when graded holds `"HIT: …"` / `"MISS: …"` free text **containing commas inside quotes** (G1). |
| Fundamentals | `fundamentals/{SYM}.json` | `{symbol,fetched,quarterly_results[{announced,period,period_type,consolidated,eps,pat,pbt,payout_note}],payouts[{announced,period,period_type,type,pct,interim_label,ex_or_bc}]}`. 100/100 present (audited 2026-07-04 — full coverage). |
| News | `news_archive.jsonl` | One JSON/line. **TWO shapes** (see below). No structured symbol field — relevance is text-matched. |
| Filings / STALE | `diligence_ledger.json` | `{filings:[{symbol,date,doc_id,title,pdf_url,in_universe,materiality,classify_reason,reviewed,review_notes}]}`. Drives STALE badge. |
| Symbol list (typeahead) | `universe.json` | `{symbols:[{ticker,name}]}`, 100 entries. |
| Engine stats (footer, optional) | `rolling_stats.json` | Hit-rate by predictor/batch under `engine.rule_scorecard`. Optional; footer renders gracefully if absent. |

### `news_archive.jsonl` — the two line shapes (bit us during the build)
- **Older lines:** `{headline, note, ticker_or_sector, bucket, read, source, date/_snapshot}`
- **Newer lines:** `{headline, impact, source, date}`

The matcher scans `headline + impact + note + ticker_or_sector`. Output `impact` field = `impact ?? note`. Macro-eligibility = `lens:"E"` OR (older-shape) `bucket` key present. All handled in `sector_keywords.php`.

---

## API: `GET /api/search.php?q=<str>`
Typeahead. `q` < 2 chars → `[]`. Prefix (ticker) matches first, then name-substring. `KSE100` excluded (G8). Cap 10.
```json
[{ "ticker":"OGDC", "name":"Oil & Gas Development Company Limited" }]
```
Headers: `Content-Type: application/json; charset=utf-8`, `Cache-Control: no-store`.

## API: `GET /api/symbol.php?sym=<TICKER>` — the core payload
```json
{
  "meta":   { "ticker":"OGDC", "name":"…", "as_of":"2026-07-03", "found":true,
              "warnings":[] },
  "signal": { "signal":"HOLD","conviction":1,"score":0,"close":345.43,
              "ma20":…,"ma50":…,"ma200":…,"rsi":81.0,"pos52":100.0,
              "yield_pct":5.5,"mom20":7.96,"support":…,"resistance":…,
              "eps_trend":"unknown","diligence":"OK","why":"trend+2; rsi-2(81); …",
              "factors":{ "trend":2,"rsi":-2,"pos52w":-1,"mom20":1,"eps":0,"yield":0,"rules":0 } },
  "ohlc":   [ { "date":"2025-01-02","o":…,"h":…,"l":…,"c":…,"v":…,"raw_close":… }, … ],
  "history":[ { "date":"2026-07-03","signal":"HOLD","conviction":1,"score":0,
                "status":"open","result":"PENDING","result_detail":null,
                "grade_on_date":"2026-07-10","why":"…" },
              { "date":"2026-06-23","signal":"HOLD","conviction":1,"score":1,
                "status":"graded","result":"HIT",
                "result_detail":"HIT: HOLD: stayed within [332.17,344.17] …","why":"…" } ],
  "fundamentals": { "latest_eps":26.8,"latest_period":"IIIQ 31/03/2026","eps_trend":"unknown",
                    "quarterly_results":[…],"payouts":[…] },
  "news":   [ { "date":"2026-06-22","headline":"…","impact":"…","source":"…","match":"symbol|sector|macro" }, … ],
  "filings":[ { "date":"2026-06-29","title":"…","materiality":"NON_MATERIAL","reviewed":true,"pdf_url":"…" }, … ]
}
```

### Contract rules (enforced in `symbol.php`)
- `ohlc.o/h/l/c` = the **adjusted** series (falls back to raw fields if `adj_*` absent). `raw_close` included **only when it differs** from adjusted close (tooltip use, G5).
- `history[].result` normalized to enum **`HIT | MISS | PENDING`**. Graded rows keep the full grader text in `result_detail`. `open` status and graded-but-unparsed both → `PENDING`. Newest-first.
- `signal.diligence` = feed value, **overridden to `"STALE"`** if the ledger has an unreviewed `MATERIAL` filing for the symbol (STALE precedence rule).
- `news[].match` = `symbol` | `sector` | `macro` (drives the `[market-wide]` UI tag).
- `meta.warnings` is **always an array** (empty when clean). Freshness warning `"ohlc_last_bar X != feed as_of Y"` added when feed date ≠ OHLC last-bar date (G3). Section load failures also append a warning and null the section (G4).
- **Unknown symbol** (not in feed) → `200` with `{"meta":{"found":false,"ticker":"…"}}`. **Invalid symbol** (fails regex) → `200` with `{"meta":{"found":false,"ticker":"…","error":"invalid_symbol"}}`.

### OHLC sizing
Full series shipped (~1243 bars ≈ 150–200 KB). Range toggle slices client-side, no refetch.

---

## Data gotchas (G1–G8) and how each is handled

| # | Gotcha | Handling |
|---|---|---|
| G1 | CSV `result`/`why` fields have **commas inside quotes** (128/600 rows). | `read_csv()` uses `fgetcsv()` exclusively. Never `explode(',')`. |
| G2 | Recent batches are **ungraded** (`status=open`, empty `result`). | History normalized to three first-class states HIT/MISS/**PENDING**; UI renders PENDING with `grade_on_date`, never as error/blank. |
| G3 | **Feed date vs OHLC last-bar date can diverge** (real 2026-07-03 midnight-rollover incident). | `symbol.php` compares them → `meta.warnings[]` → UI amber freshness banner. |
| G4 | Pipeline **rewrites feed files mid-run** → a page load can read half-written JSON. | Readers: read whole file → decode → on parse failure retry once after 200 ms → then structured `{ok:false,error}` (never a PHP warning). Section nulled + warning added. |
| G5 | Raw `close` has **cliffs at splits/bonuses**. | Chart from `adj_*` always. `raw_close` in tooltip only when it differs. |
| G6 | CSV **may gain columns** over time (model/ensemble cols planned). | `read_csv()` maps by header **name**, never index. |
| G7 | ~3/100 symbols *could* lack fundamentals; some lack news. | Every panel has a designed empty-state. Missing file ≠ error. (Note: as of 2026-07-04 all 100 have fundamentals, so this path is coded but not live-exercisable.) |
| G8 | `KSE100.json` exists in `ohlc/` but is an **index, not a stock**. | Excluded from search results. |
