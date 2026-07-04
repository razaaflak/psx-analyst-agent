# Operations

## Run
```powershell
cd psx-analyst-agent\dashboard
.\serve.ps1                 # Windows  → php -S localhost:8000 -t public
# or  ./serve.sh            # POSIX
```
Open http://localhost:8000 (port fixed at 8000). Requires **PHP 8.5.1** on PATH (dev machine confirmed). No other dependencies. Type a symbol or use `#OGDC` deep-link.

## Verify quickly (no browser)
```powershell
Start-Process php -ArgumentList '-S','localhost:8000','-t','dashboard/public' -WindowStyle Hidden
# then:
Invoke-WebRequest 'http://localhost:8000/api/symbol.php?sym=OGDC' -UseBasicParsing   # found=true, ~1243 bars
Invoke-WebRequest 'http://localhost:8000/api/search.php?q=og'    -UseBasicParsing   # OGDC first
Invoke-WebRequest 'http://localhost:8000/api/symbol.php?sym=ZZZ' -UseBasicParsing   # {"meta":{"found":false,…}}
# kill when done:
Get-Process php | Stop-Process -Force
```
> **Gotcha:** in PowerShell, don't name a helper function `H` — it collides with the `Get-History` alias. Use `Chk` or similar.

## QA results (Q1, 2026-07-04) — ALL PASS
Verified live via Playwright MCP, **zero console errors/warnings** across the whole session:
- **ABL** (BUY conv3): green chip, `●●● 3/3`, dividend + signal markers, bank news, full payouts.
- **EFERT / PAEL** (SELL): red chips, correct payloads (1239 bars, 6 history each).
- **OGDC** (HOLD): dividend markers, zoom, tooltips, freshness path.
- **#ZZZ**: clean empty-state ("No engine data found…"), no PHP crash.
- **API:** `no-store` on both endpoints; `sym=../x` blocked (`invalid_symbol`); `q=1-char` → `[]`; `config.php` not served as source.
- **Keyboard:** typeahead opens, ArrowDown highlights, Enter routes, Escape closes + resets `aria-expanded`.
- **Responsive:** 375 / 768 / 1440px — no horizontal scroll; 1440 shows two-column `.layout-grid` (895/466).
- **Zoom:** slider + wheel/pinch/pan; synced candle/volume/RSI; markers survive zoom; range buttons reset window.

**Not live-exercisable** (coded + structurally correct, but current data doesn't trigger them): STALE badge (zero STALE symbols in live data), fundamentals-empty-state (all 100 have fundamentals). Use a synthetic payload to exercise if needed.

## Symbol coverage — COMPLETE
Audited 2026-07-04: feed=100, ohlc=101 (incl. KSE100 index, excluded from search), fundamentals=100, universe fully in feed. **Every KSE-100 symbol is served live.** No pipeline change is needed for consumability — `dashboard_feed.json` is the pipeline's per-symbol payload and the API maps it 1:1 to the OHLC/fundamentals/signals/news/ledger files. The OGDC/EFERT fixtures were only day-1 UI scaffolding and are no longer in the runtime path.

## Git status
- **Committed:** `b9db2eb` "Dashboard v1: single-symbol deep view …" — 15 files.
- **Merged:** fast-forwarded into local `main` (`main` was 0 ahead / 5 behind the feature branch `engine-grader-2026-06-28`). Local `main` now at the dashboard commit.
- **NOT pushed.** Remote `origin/main` still at the old commit. Push deferred by user.

### Pushing later — credential snag to resolve first
The remote URL carries username `razaaflak@` but `gh` is authed as account **`arazapsych`**, and the `manager` credential helper can't prompt in this non-interactive shell. Options when ready:
1. `gh auth setup-git` then push (may still hit the username mismatch), OR
2. Push with the token: `git push "https://x-access-token:$(gh auth token)@github.com/razaaflak/psx-analyst-agent.git" main`, OR
3. Fix the remote URL to drop the baked-in username: `git remote set-url origin https://github.com/razaaflak/psx-analyst-agent.git` then `git push origin main`.

## Backlog (v2+, from PLAN §9)
- Universe overview tab: 100-signal grid, buy/hold/sell counts, sortable, sector heatmap.
- Cross-symbol scans/filters (RSI<30, yield>10%, BUY+conv3, STALE-only).
- Extend `build_db.py` to ingest `universe_signals.csv` → move API to SQLite for fast cross-universe queries.
- ML-model & ensemble signal columns once `universe_model.py` exists (pipeline TODO).
- KSE100 index sparkline in header (data in `ohlc/KSE100.json`).
- EPS quarterly mini-bar-chart in fundamentals panel.
- Compare view (2 symbols side by side); watchlist persistence.
- Light-theme polish (tokens exist; not QA'd), Edge/Firefox pass (only Chrome verified).

## Known residual risks (accepted for v1)
- **News tagging is heuristic** (no structured symbol field) — `match` tag makes quality visible; tune `sector_keywords.php` if noisy.
- **Concurrent pipeline writes** can cause a torn read once/day — mitigated by G4 retry + structured failure; residual risk accepted (single local user).
- **Dev-server only** — not hardened for public hosting.
