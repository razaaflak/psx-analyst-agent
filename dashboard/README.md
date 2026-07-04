# PSX Dashboard (v1)

Local, read-only dashboard over the training pipeline's `data/` files. See `PLAN.md` (locked v1.3) for the full spec.

## Run

```powershell
.\serve.ps1        # Windows
./serve.sh         # POSIX
```

Then open http://localhost:8000 (port fixed per PLAN §11).

Requires PHP 8.x on PATH (dev machine has 8.5.1). No other dependencies.

## Routing decision (PLAN §5, option b)

Docroot = `public/`. API endpoints live at `public/api/*.php` (URL-reachable). Shared code stays **outside** the docroot and is `require`d by relative path:

- `config.php` — `DATA_DIR` resolver, headers, constants
- `api/lib/data.php` — read-only JSON/CSV/JSONL readers (TICKET-D1)
- `api/lib/sector_keywords.php` — news relevance map (TICKET-D3)

`lib/` and `config.php` are therefore not URL-reachable by construction (I1 AC).

## Hard rules

- **Read-only**: nothing under `data/` is ever written by the dashboard (PLAN D6). `data.php` contains no write helpers.
- **API contract**: payload shapes in PLAN §6 change only via Lead + changelog bump. UI builds against `fixtures/symbol_OGDC.json` until D4 lands.
- **No caching of API responses**: `Cache-Control: no-store` (PLAN D7).

## Vendored libraries

| Lib | Version | License | Location |
|---|---|---|---|
| Apache ECharts | 5.5.1 | Apache-2.0 | `public/assets/vendor/echarts.min.js` |

No CDN usage — everything works offline.
