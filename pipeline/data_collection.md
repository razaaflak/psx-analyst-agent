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

### Source roles — do NOT cross-check the wrong source (verified 2026-06-18)
Each source carries a **different data type**. Routing a lookup to the wrong one wastes a fetch and proves nothing.

| Source | Carries | Does NOT carry | Use for |
|---|---|---|---|
| **dps.psx.com.pk/announcements/companies** | LIVE disclosures: insider trades (5.6.x), corporate-briefing notices, board-meeting/regulatory filings + their PDF/GIF attachments | — | **Only** source for live disclosures. No fallback exists — if it's down, the disclosure is simply unavailable that day (log it). |
| **scstrade.com** `SS_CompanySnapShotAnn.aspx?symbol=` | Results/dividend **CALENDAR**: board-meeting date, EPS, EPS-cum, **DIVIDEND %**, BONUS, RIGHT, **XDATE (ex-div)** | insider trades, briefing notices, any live disclosure | Cross-verify **earnings & payout** (EPS/dividend) and **capture XDATE** for the F-lens. NEVER expect it to confirm a disclosure — structurally can't. (Confirmed 2026-06-18: PSO insider/briefing absent; UBL insider sell absent.) Data-only — never take its trading calls ([[reference_scstrade_fundamentals]]). |
| **scstrade.com** `SS_CompanySnapShot.aspx?symbol=` | Ratios snapshot: P/E, P/B, ROE, ROA, BVPS, yield, 52wk | live disclosures | F-lens ratios fallback. |

**XDATE / ex-dividend discipline (F-lens):** the scstrade calendar lists each holding's **ex-div date**. On the ex-div day a stock drops mechanically by ~the dividend amount — this is NOT a thesis break and must NOT be graded as a loss. Each run, check whether any holding has an XDATE on/near today; if so, expect the drop and annotate the prediction/grade accordingly (no look-ahead — only use a *published* XDATE).

**scstrade Company Snapshot — fundamentals fallback (verified 2026-06-17, DATA-ONLY).** When a ratio/metric isn't in our existing sources (PSX portal, `data/fundamentals/{SYM}.json`, sarmaaya), pull it from:
`https://scstrade.com/stockscreening/SS_CompanySnapShot.aspx?symbol={SYMBOL}`
Reads clean via plain `WebFetch` (no browser). Carries: P/E (+expected), P/B (+expected), latest & annual EPS, expected earnings growth, BVPS, ROE, ROA, last annual dividend, dividend yield, payout ratio, 52-week range, day range, volume, plus bank-specific ratios (equity/advances, ADR, cash/deposits). Tag `source: "scstrade.com snapshot"` on every value taken.
**Hard rule: extract DATA ONLY. Never ingest, repeat, or act on any buy/sell/hold call, target price, or analyst opinion from scstrade. All trading judgment is the agent's own (F/T/E method).** Treat its "expected" figures as the site's estimates — label them estimates, don't treat as reported actuals.

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

**Exact DOM (verified 2026-06-18 — do NOT guess the layout):** one table `#announcementsTable` (`table.tbl`), `tbody tr` rows (~50/page). Columns in order: **`td[0]`=DATE, `td[1]`=TIME, `td[2]`=SYMBOL, `td[3]`=NAME, `td[4]`=TITLE, `td[5]`=View link**. The TITLE in `td[4]` IS the announcement content — there is no separate detail fetch needed for the headline. Canonical extractor:
```js
() => Array.from(document.querySelectorAll('#announcementsTable tbody tr')).map(r => {
  const td = r.querySelectorAll('td');
  return { date: td[0]?.innerText.trim(), time: td[1]?.innerText.trim(),
           symbol: td[2]?.innerText.trim(), name: td[3]?.innerText.trim(),
           title: td[4]?.innerText.trim(), url: r.querySelector('a')?.href || null };
});
```
Then filter `symbol ∈ watchlist`. Record the **full `title` text**.

**ALWAYS OPEN THE ATTACHMENT for every watchlist match — the title is a label, not the content (learned 2026-06-18).** Two real examples that title-only mis-graded: a UBL "5.6.1.d disclosure" was actually an *executive SELL of 3,406 sh @455*; a PSO "corporate briefing notice" was actually a *full 9MFY26 results deck (GP +82%, OP +97%)*. Never set `material`/`read` from the title alone.

**Attachment URLs (verified 2026-06-18):** each row's View-cell has a `data-images="{postid}-1.gif"` link and may also have a direct PDF link `/download/document/{postid}.pdf`.
- **PDF:** `https://dps.psx.com.pk/download/document/{postid}.pdf` → save locally + extract text. WebFetch often fails on scanned/image PDFs; use the venv: `pip install pymupdf` once, then `fitz.open(path)` → `page.get_text()` per page. (psx decks are text-layer PDFs and extract cleanly.)
- **GIF (scanned form, no PDF):** the URL is `https://dps.psx.com.pk/download/image/{postid}-1.gif` — note `/download/image/` NOT `/download/document/`. `browser_navigate` to it, `browser_take_screenshot` (fullPage), then `Read` the PNG to OCR the form (insider trades, share counts, rates live here).

Only AFTER reading the attachment, set `material` (true if dividend/EPS/bonus/rights/result/board-meeting/merger/ex-div/insider-trade-of-size) and `read` (positive/negative/neutral/risk). Record `attachment` URL + `attachment_type` in the snapshot. A routine 5.6.x insider disclosure is `material:false` only after confirming the share count is immaterial — a large insider sell IS material.

**Failure ladder — never write "category pending / not retrieved" and move on:**
1. If `#announcementsTable` selector returns 0 rows → re-check with `browser_snapshot`; the id may have changed. Fall back to `document.querySelector('table.tbl')` then generic `document.querySelectorAll('table')` (pick the one whose header row contains "SYMBOL").
2. If the dps page is down/blocked → **fallback source** `https://www.psx.com.pk/psx/announcement/financial-announcements` (Tier-2 HTML table, §3b) for the financial subset (dividends/EPS/ex-div), and `WebFetch` the company's own announcement listing if needed.
3. If a watchlist symbol's TITLE is genuinely truncated → open its `url` (`/company/{SYMBOL}`) and read the announcements panel there.
4. Only if **all** of the above fail for a symbol, log a warning AND state the F/E impact is `unknown` (never silently assume neutral).

**Discipline:** a filing whose text could not be read is NOT the same as "no news" — it is an open risk flag and must surface in the run's warnings + watch items, not be dropped.

### 3b. Macro, policy & corporate-action news — ADDED Run #3, expanded Run #3b (2026-06-11)
The PSX portal market-watch carries only price/volume. The signal that moves the **F** and **E** lenses lives elsewhere: macro/govt news, SBP policy, and the **financial-announcements** (dividends / EPS / ex-div / book-closure) table. Pull these in **two tiers** — RSS where it exists (cheap, dated, via `WebFetch`), HTML where it doesn't (via Playwright, same as price scraping).

**ALL sources below were tested live 2026-06-11. Status is real, not assumed — verify a feed returns XML before trusting it (the original Mettis entry was a search-guess with no public feed; removed).**

#### Tier 1 — RSS via `WebFetch` (no browser)
| Source | URL | Status | Strength |
|---|---|---|---|
| Business Recorder (latest) | `https://www.brecorder.com/feeds/latest-news` | ✅ RSS 2.0 | economy/policy/markets/commodities, today-dated |
| Dawn (business) | `https://www.dawn.com/feeds/business` | ✅ RSS 2.0 | **PSX-specific** — names regulatory rows, budget, NEC, results; today-dated |

#### Tier 2 — HTML via Playwright (`browser_navigate` + `browser_evaluate`)
| Source | URL | Status | Why it has the most weight |
|---|---|---|---|
| **PSX Financial Announcements** | `https://psx.com.pk/psx/announcement/financial-announcements` | ✅ HTML table | **Highest F-lens value:** dividends, EPS/LPS, bonus/rights, **AGM & ex-div / book-closure dates**. Lets us anticipate ex-div drops and earnings. (e.g. confirmed OGDC 32.5% interim, PPL 20% final.) |
| SBP Press Releases | `https://www.sbp.org.pk/press/index.asp` | ⚠️ intermittent (522 timeout on test) | **Direct R-001/R-002 driver** — policy-rate / MPC / liquidity. Best-effort, retry-tolerant; skip if down, never block the run. |
| BR PSX-tagged / trends | `https://www.brecorder.com/trends/pakistan-stock-exchange` , `…/markets/stocks` , `…/trends/rss` | ⚠️ 403 to plain WebFetch | Works only with a real browser UA → Playwright fallback. Lower priority (Dawn+BR-latest already cover macro). |

**Dropped / skipped (tested, no value):** Mettis `…/feed|/rss|/feed.xml` → 404, no RSS. SCSTrade announcements → JS-loaded, empty on fetch, adds nothing the PSX portal lacks.

**Procedure each run:**
1. **Tier 1:** `WebFetch` each RSS feed; read titles + pub-dates.
2. **Tier 2:** with the Playwright session already open for prices, `browser_navigate` to PSX financial-announcements (always) and SBP press (best-effort); `browser_evaluate` the table/list. Tag any watchlist match. Extract **ex-div / book-closure dates** into the F lens.
3. **Keyword-filter** to what touches the book. Buckets → lens mapping (SKILL.md Part F):
   - **tickers** (OGDC/PPL/MARI/MEBL/FABL/UBL/MCB/FFC/DGKC/CHCC/LUCK/MTL/ENGROH/PSO/APL) → direct read
   - **dividend / EPS / result / bonus / right / book closure / AGM** → **F lens** (ex-div timing, earnings surprise)
   - **oil / Brent / WTI / Arab Light** → E&P (OGDC/PPL/MARI) tilt
   - **SBP / policy rate / MPC / KIBOR / MTB / T-bill** → banks (R-001) + high-debt (R-002)
   - **budget / NEC / FBR / finance bill / tax** → event-risk (R-004), sector re-rate
   - **PKR / rupee / remittances / IMF / reserves / FX liabilities** → broad risk + importers/exporters
   - **geopolitics (Iran / Israel / Middle East / war / strikes)** → oil spike + risk-off; widen stops
   - **sector terms (cement / fertilizer / E&P / bank / OMC / auto)** → sector tilt
4. Tag each kept item: `{ date, source, headline, bucket, ticker_or_sector, read: "+/−/risk", note }` into `macro_news`. Put ex-div/results facts into the F lens, not just E.
5. **Commodities & flows block** — capture daily levels from Ahmad's WhatsApp brief if shared (RSS does not carry the levels block): Brent, WTI, Arab Light, gold, silver, coal, **USD/PKR**, **FIPI net**, leverage (futures/MTS/MFS).
6. **Date-check (no look-ahead):** confirm each item's pub-date. A headline quoting *yesterday's* index/commodity close (e.g. "equities lose 903 pts" = the prior session) is a recap — tag it to the correct prior date, never grade a prediction against post-dated news.

**Discipline:** news is an **E-lens modifier only** (SKILL.md Part G) — it can widen a stop / raise cash / shrink conviction, never trigger a fresh entry alone, never override F/T. **Exception:** hard corporate-action *facts* from PSX financial-announcements (a declared dividend, an ex-div date, a reported EPS) are F-lens inputs, not sentiment — treat them as data, like price. News-derived *interpretive* rules still start **Experimental** (0 weight, ≥8 obs to graduate).

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
