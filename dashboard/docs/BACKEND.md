# Backend (PHP)

Four files. All defensive (assume every file can be half-written / mis-quoted / missing). **No write helpers exist anywhere** (D6).

## `config.php` (outside docroot)
- `define('DATA_DIR', realpath(__DIR__.'/../data'))` — the one read-root. If missing → 500 JSON `{error:"data_dir_not_found"}`.
- `define('SYM_PATTERN', '/^[A-Z0-9]{1,12}$/')`.
- `define('DASHBOARD_VERSION', '1.0.0')`.
- `api_headers()` — sets `Content-Type: application/json; charset=utf-8` + `Cache-Control: no-store` (D7). Call at the top of every endpoint.

## `api/lib/data.php` (outside docroot) — the read-only data lib
| Function | Contract |
|---|---|
| `data_path(string $rel): ?string` | Resolves `$rel` under `DATA_DIR`. Rejects `..` segments, null bytes, empties. Uses `realpath` + prefix-check when target exists; lexical bound-check when it doesn't. Returns `null` on any escape → callers treat as `invalid_path`. **The path-traversal guard.** |
| `is_valid_symbol(string $sym): bool` | `^[A-Z0-9]{1,12}$`. |
| `read_json($absPath): array` | `{ok:true,data}` or `{ok:false,error}`. `error ∈ {not_found, read_failed, parse_error}`. **G4:** on read/parse failure (not `not_found`) retries once after 200 ms. Warnings suppressed (`@`); never throws. |
| `read_jsonl($absPath): array` | `{ok:true,data:[…]}` — array of parsed lines; malformed/blank lines skipped silently (one torn line ≠ dead archive). Same G4 retry. |
| `read_csv($absPath): array` | `{ok:true,rows:[{header=>val}]}`. **`fgetcsv()` only (G1)**, maps by header **name (G6)**. Ragged rows padded/truncated to header width rather than erroring. Strips BOM/whitespace on header cells. Same G4 retry. |

**Never** add a write function to this file — it is read-only by construction (D6).

## `api/lib/sector_keywords.php` (outside docroot) — news relevance
- `sector_keyword_map(): array` — builds `ticker => [keywords]` from a 12-sector table (E&P, cement, banks, OMC, fertilizer, textile, auto, power, pharma, food/FMCG, tech/telecom, macro). Edit this table to tune news matching.
- `news_item_text($item)` — concatenates `headline + impact + note + ticker_or_sector` (handles both JSONL shapes).
- `news_item_impact($item)` — `impact ?? note`.
- `news_item_is_macro_eligible($item)` — `lens === "E"`, else `array_key_exists('bucket', …)` (older shape).
- `news_item_match($item, $ticker, $map)` — returns `'symbol'` (word-boundary ticker hit), `'sector'` (keyword substring), or `null`.
- `build_symbol_news($allItems, $ticker, $limit=10, $macroFallbackCount=5)` — direct matches (symbol/sector) newest-first, then macro fallback to fill up to `$limit`. Each item tagged `match`.

## `public/api/search.php` (docroot) — typeahead
`ini_set('display_errors','0')`, `api_headers()`, then: `q` < 2 chars → `[]`; load `universe.json`; prefix (ticker, case-insensitive) matches first, then name-substring; skip `KSE100` (G8); cap 10. Data-layer failure → `[]` (non-critical, safe). Always valid JSON.

## `public/api/symbol.php` (docroot) — core merge
`display_errors` off (a warning must never corrupt JSON). Steps:
1. Validate `sym` (regex) → invalid → `found:false, error:invalid_symbol`.
2. Read `dashboard_feed.json` → if symbol absent → `found:false`. Capture `as_of` + signal block.
3. Read `ohlc/{SYM}.json` → map to `{date,o,h,l,c,v(,raw_close)}` from `adj_*` (G5). Track last-bar date.
4. **G3 freshness:** `as_of != ohlcLastDate` → warning.
5. Read `universe_signals.csv`, filter by symbol → normalize `result` to `HIT|MISS|PENDING` + `result_detail`, newest-first (G2).
6. Read `fundamentals/{SYM}.json` → derive `latest_eps`/`latest_period`, pass through `quarterly_results`+`payouts`. `not_found` → `null` (G7, not an error).
7. Read `news_archive.jsonl` → `build_symbol_news()` (D3).
8. Read `diligence_ledger.json` → filter filings by symbol; set `hasUnreviewedMaterial` if any `MATERIAL` + `!reviewed`.
9. Assemble `signal` block; **override `diligence → "STALE"`** if `hasUnreviewedMaterial` (precedence rule).
10. `meta.warnings` always an array; any section that failed to load is `null` + a warning (G4).

## Adding a field to the payload (the safe way)
1. Add it in `symbol.php` (or `search.php`).
2. Bump `PLAN.md` §13 changelog (contract change).
3. Regenerate `fixtures/symbol_OGDC.json` if you want the fixture to match (fixtures are dev reference only — not in the runtime path).
4. Consume it in `app.js` / `chart.js`.
