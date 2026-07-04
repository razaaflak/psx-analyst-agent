# PSX Dashboard — Docs Index

Complete reference for the PSX dashboard so a new session can work without re-exploring the code. Written 2026-07-04 against commit `b9db2eb` (Dashboard v1, merged to `main`).

## What this is
A **local, read-only web dashboard** over the PSX universe prediction-engine's `data/` flat files. Type a KSE-100 symbol → see its candlestick chart, current engine signal, fundamentals, relevant news, and graded signal history on one page. **Zero writes to `data/`; zero changes to the training pipeline.** Serves all 100 KSE-100 symbols live.

Status: **v1 complete + QA-passed + committed**. Not yet pushed (remote credential reconciliation pending — see [OPERATIONS.md](OPERATIONS.md)).

## Read these in order
1. **[ARCHITECTURE.md](ARCHITECTURE.md)** — the 8 architectural decisions (D1–D7), folder layout, routing, request flow, hard rules.
2. **[DATA_CONTRACTS.md](DATA_CONTRACTS.md)** — every source file the dashboard reads, the exact API payload shapes (`/api/symbol.php`, `/api/search.php`), and the 8 data gotchas (G1–G8) with how each is handled.
3. **[BACKEND.md](BACKEND.md)** — PHP layer: `data.php` readers, `sector_keywords.php` news matcher, `search.php`, `symbol.php`. Function-by-function.
4. **[FRONTEND.md](FRONTEND.md)** — `app.js` (routing/search/render), `chart.js` (ECharts candlestick + indicators + zoom + markers), `styles.css` tokens, `index.php` shell.
5. **[OPERATIONS.md](OPERATIONS.md)** — how to run, verify, QA results, push/merge status, and known open items / backlog.

## The canonical spec still lives one level up
`dashboard/PLAN.md` (locked v1.3) is the **original engineering contract** — tickets, personas, changelog. These docs describe *what was actually built*; PLAN.md describes *what was planned*. They agree, but if you change the API contract, bump PLAN.md's changelog (§13) too.

## 30-second orientation
- **Server:** `php -S localhost:8000 -t dashboard/public` (or `dashboard/serve.ps1`). PHP 8.5.1, no other deps.
- **Docroot:** `public/`. API at `public/api/*.php`. Shared PHP (`config.php`, `api/lib/*`) lives **outside** docroot, `require`d by relative path → not URL-reachable.
- **Data source:** flat files in `../data/` (NOT `psx.db` — that only has legacy portfolio tables, see D2). `dashboard_feed.json` is the primary signal source.
- **Frontend:** vanilla JS + ECharts 5.5.1 (vendored, no CDN). Single page, URL-hash routing (`#OGDC`).
- **Read-only:** `data.php` has no write helpers by construction. This is a hard rule (D6).
