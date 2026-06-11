# pipeline/data_collection.md — Automated Data Collection via Playwright MCP

This replaces all manual copy-paste. The agent drives a real browser through the **Playwright MCP** server to pull each day's PSX data from the official Data Portal, writes a date-stamped raw snapshot for audit, and hands clean structured data to the daily pipeline.

> **Prerequisite:** the Playwright MCP server must be connected to the agent (see README → Setup). The agent calls Playwright tools directly; it never asks Ahmad to paste data unless every automated path fails.

---

## Sources (official PSX Data Portal — verify before trusting)

| What | URL |
|---|---|
| KSE-100 + market watch (Today's Summary) | `https://dps.psx.com.pk/` and `https://dps.psx.com.pk/?page_id=30` |
| Per-company quote + OHLC + history | `https://dps.psx.com.pk/company/{SYMBOL}` (e.g. `/company/MEBL`) |
| Corporate announcements | `https://dps.psx.com.pk/announcements/companies` |
| Sector summary | `https://dps.psx.com.pk/sector-summary` |
| Historical / daily download | `https://dps.psx.com.pk/historical` |
| Backups (human-readable) | `https://www.ksestocks.com/MarketSummary`, `https://sarmaaya.pk` |

**Note on fundamentals:** the PSX portal is mostly price/volume. For P/E, P/B, ROE, and dividend history (the F lens), use a company page that carries them (e.g. `scstrade.com` company snapshot or `sarmaaya.pk`) — scrape the same way. Always record which source supplied each fundamental.

---

## Playwright MCP tools you will use

- `browser_navigate({url})` — open a page.
- `browser_wait_for({text})` or `({time})` — wait until the table/data has rendered (PSX loads via JS).
- `browser_snapshot()` — get the accessibility tree with element refs; use it to *locate* the data table before extracting.
- `browser_evaluate({function})` — run a JS function in the page and return structured JSON. **This is the primary extraction method.**
- `browser_network_requests()` — list XHR/fetch calls the page made; use to find the underlying JSON feed (often cleaner than scraping the DOM).
- `browser_take_screenshot({filename})` — save visual evidence of the close for the audit trail.
- `browser_console_messages()` — debug if extraction returns empty.
- `browser_close()` — close when done.

---

## Collection procedure (run at Step 1 of the daily pipeline)

### 1. Market index + watchlist prices
1. `browser_navigate` → `https://dps.psx.com.pk/`.
2. `browser_wait_for` the market table (e.g. wait for text like "KSE100" or a known ticker) so JS has populated it.
3. **Prefer the network feed:** call `browser_network_requests()`. If the page fetched a JSON endpoint with the quotes, note that URL and `browser_navigate` to it (or re-evaluate `fetch`) to read clean JSON. Cleaner and more stable than DOM scraping.
4. **Fallback — DOM extraction:** call `browser_snapshot()` to confirm the table structure, then `browser_evaluate` with a function that reads the rows and returns an array. Template (adapt the selectors to the live DOM — do NOT assume; confirm against the snapshot):
   ```js
   () => {
     const rows = [...document.querySelectorAll('table tbody tr')];
     return rows.map(r => {
       const c = [...r.querySelectorAll('td')].map(td => td.innerText.trim());
       return { symbol: c[0], open: c[1], high: c[2], low: c[3],
                current: c[4], volume: c[5], change: c[6] };
     }).filter(x => x.symbol);
   }
   ```
5. Capture the **KSE-100** value, points change, % change, total volume/value, advancers/decliners (from the index header/summary on the same portal).
6. Filter the returned rows down to the watchlist tickers; keep the full set in the raw snapshot for audit.

### 2. Per-stock detail & history (only for watchlist + holdings)
For each symbol, `browser_navigate` → `/company/{SYMBOL}`, `browser_wait_for`, then `browser_evaluate` to pull: last close, day OHLC, 52-week range, and the recent price history needed for moving averages and RSI. Grab fundamentals here or from the fundamentals source. Keep requests gentle (see rate limits).

### 3. Announcements & news
`browser_navigate` → `/announcements/companies`, extract the day's announcements (results, dividends, board meetings, regulatory) and tag any that match a watchlist symbol. These feed the **F** and **E** lenses.

### 3b. Macro & business news (RSS — feeds the E lens) — ADDED Run #3
The PSX portal carries only *company* filings, not macro/govt/geopolitical news. Pull that from **free RSS feeds** of the same Pakistani financial outlets a practitioner reads. **Use `WebFetch` (or plain HTTP), NOT Playwright** — RSS is a stable dated schema; no DOM scraping, no browser needed.

**Feeds (free, confirmed live 2026-06-11):**
| Source | URL | Strength |
|---|---|---|
| Business Recorder | `https://www.brecorder.com/feeds/latest-news` | economy/policy/markets, today-dated |
| Mettis Global | `https://mettisglobal.news/feed` | forex, rates, markets, commodities |
| Dawn (business) | `https://www.dawn.com/feeds/business` | broader, noisier — optional 3rd |

**Procedure each run:**
1. `WebFetch` each feed; read item titles + pub-dates.
2. **Keyword-filter** to what touches the book. Buckets → lens mapping (SKILL.md Part F):
   - **tickers** (OGDC/PPL/MARI/MEBL/FABL/UBL/MCB/FFC/DGKC/CHCC/LUCK/MTL/ENGROH/PSO/APL) → direct E read
   - **oil / Brent / WTI / Arab Light** → E&P (OGDC/PPL/MARI) tilt
   - **SBP / policy rate / MPC / KIBOR / MTB / T-bill** → banks (R-001) + high-debt (R-002)
   - **budget / NEC / FBR / finance bill / tax** → event-risk (R-004), sector re-rate
   - **PKR / rupee / remittances / IMF / reserves / FX liabilities** → broad risk + importers/exporters
   - **geopolitics (Iran / Israel / Middle East / war / strikes)** → oil spike + risk-off; widen stops
   - **sector terms (cement / fertilizer / E&P / bank / OMC / auto)** → sector tilt
3. Tag each kept item: `{ date, source, headline, bucket, ticker_or_sector, read: "+/−/risk", note }`.
4. **Commodities & flows block** — capture daily levels (from Mettis commodity feed, or Ahmad's WhatsApp brief if shared): Brent, WTI, Arab Light, gold, silver, coal, **USD/PKR**, **FIPI net**, leverage (futures/MTS/MFS). These drive the E lens directly.
5. **Date-check:** confirm each item's pub-date == today (or note lag). A KSE-100/commodity value in a brief that matches *yesterday's* close means the brief is a morning recap of the prior session — use it, but tag the date correctly (no look-ahead).

**Discipline:** news is an **E-lens modifier only** (SKILL.md Part G). It can widen a stop / raise cash / shrink conviction — it can **never** trigger a fresh entry by itself, and never overrides F/T. News-derived rules start **Experimental** (0 weight) and must earn ≥8 obs like any rule.

### 4. Validate before trusting
- **Sanity checks:** index move within a believable range; prices not zero/null; volumes plausible; today's date matches. If a number looks wrong, mark it `unverified` and cross-check the backup source.
- **No data / market closed / site down:** record the failure, try the backup source once, and if still failing, **skip the run gracefully** and tell Ahmad — never fabricate.

### 5. Persist the raw snapshot (audit trail)
Write `data/market_data/YYYY-MM-DD.json` with this schema, then hand it to the pipeline:
```json
{
  "date": "2026-06-10",
  "fetched_at": "2026-06-10T17:10:00+05:00",
  "source": "dps.psx.com.pk (network feed)",
  "confidence": "high",
  "index": { "kse100": 0, "change_pts": 0, "change_pct": 0,
             "volume": 0, "advancers": 0, "decliners": 0 },
  "stocks": [
    { "symbol": "MEBL", "open": 0, "high": 0, "low": 0, "close": 0,
      "volume": 0, "change_pct": 0, "source": "dps.psx.com.pk" }
  ],
  "fundamentals": [
    { "symbol": "MEBL", "pe": null, "pb": null, "div_yield": null,
      "source": "sarmaaya.pk", "note": "" }
  ],
  "announcements": [
    { "symbol": "FFC", "type": "dividend", "text": "", "source": "dps.psx.com.pk" }
  ],
  "commodities": {
    "brent": null, "wti": null, "arab_light": null, "gold": null, "silver": null,
    "coal": null, "usd_pkr": null, "fipi_net_usd_mn": null,
    "leverage": { "futures_bn": null, "mts_bn": null, "mfs_bn": null },
    "as_of": "YYYY-MM-DD", "source": ""
  },
  "macro_news": [
    { "date": "2026-06-10", "source": "brecorder", "headline": "", "bucket": "oil|rate|budget|pkr|geopolitics|sector|ticker",
      "ticker_or_sector": "", "read": "+|-|risk", "note": "" }
  ],
  "screenshot": "data/market_data/2026-06-10_close.png",
  "warnings": []
}
```
Also save the `browser_take_screenshot` of the close to the path above.

---

## Reliability, etiquette & compliance

- **Wait, don't race:** always `browser_wait_for` before extracting — PSX renders client-side, so a too-early read returns empty.
- **Be gentle:** sequential requests, a 1–3s pause between company pages, run once daily after close. No hammering.
- **Resilient selectors:** confirm structure via `browser_snapshot` each run rather than hard-coding fragile selectors; the portal's DOM can change. If extraction returns empty, re-snapshot and adapt.
- **Restrict the browser:** run Playwright MCP with `--allowed-hosts` limited to the PSX/data domains so the agent can't wander.
- **Headless + persistent profile** is fine for this read-only task.
- **ToS / IP note:** scrape only for Ahmad's **personal, non-redistributed** analysis, at low frequency. The PSX portal's terms restrict redistribution and commercial use of its data and it enforces its IP; if this ever feeds a public product, get a proper market-data license (`marketdatarequest@psx.com.pk`). Don't republish raw PSX data.

## Fallback ladder (in order)
1. PSX portal network JSON feed → 2. PSX portal DOM extract → 3. Backup source (ksestocks/sarmaaya) → 4. Screenshot + read values → 5. As a last resort only, ask Ahmad to paste. Always record which rung was used in `source`/`confidence`.
