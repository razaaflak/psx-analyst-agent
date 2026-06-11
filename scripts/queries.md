# scripts/queries.md — Canned queries for the daily pipeline

`data/psx.db` is a **derived, queryable copy** of the canonical flat files
(`predictions_log.csv`, `trade_ledger.csv`, `market_data/*.json`). The CSVs/JSON
remain the source of truth. Rebuild the DB anytime with:

```
python scripts/build_db.py --verify
```

Run a query via Python's built-in sqlite3 (no install needed). Pattern:

```
python -c "import sqlite3,sys; c=sqlite3.connect('data/psx.db'); [print(r) for r in c.execute(sys.argv[1]).fetchall()]" "SELECT ..."
```

Or for multi-line, write the SQL to a temp `.sql` and read it — but the canned
queries below are single-statement and fit the one-liner.

> **Discipline unchanged.** The DB is only a read accelerator + the maturity/aggregate
> helper. All WRITES still go to the CSVs first (append-only, never edit issued
> prediction rows, never edit past trade rows). After writing the CSVs at run end,
> rebuild the DB so it stays in sync. If DB and CSV ever disagree, the CSVs win.

---

## Q1 — Matured predictions to grade today (Step 2)
Returns only the open rows whose grade_on_date has arrived. Replace the date.

```sql
SELECT prediction_id, ticker_or_index, prediction_text, type, conviction, driver_lenses, driver_rules
FROM predictions
WHERE status='open' AND grade_on_date <= '2026-06-10'
ORDER BY grade_on_date;
```

## Q2 — Actual price outcome to grade against (Step 2, no look-ahead)
Pull the EOD closes for the predicted symbol across the prediction's window.
Only use dates AFTER the prediction's issue_date.

```sql
SELECT date, symbol, close, change_pct, volume
FROM prices_eod
WHERE symbol='OGDC' AND date BETWEEN '2026-06-10' AND '2026-06-16'
ORDER BY date;
```

## Q2b — Index-relative grade path (stock %chg vs KSE-100 %chg per day)
For predictions like "X outperforms KSE-100 over next N sessions". Both series
come from the DB (`index_eod` holds the KSE-100), so no JSON re-read needed.
Use dates strictly AFTER the prediction's issue_date.

```sql
SELECT p.date, p.change_pct AS stock_pct, i.change_pct AS kse_pct,
       (p.change_pct > i.change_pct) AS stock_outperformed
FROM prices_eod p JOIN index_eod i ON p.date = i.date
WHERE p.symbol='MEBL' AND p.date > '2026-06-10'
ORDER BY p.date;
```

## Q3 — Rolling hit-rate, overall (Step 2 summary / Step 3 learning)
```sql
SELECT
  COUNT(*) AS graded,
  SUM(grade='HIT')     AS hit,
  SUM(grade='PARTIAL') AS partial,
  SUM(grade='MISS')    AS miss,
  ROUND(100.0*SUM(grade='HIT')/NULLIF(COUNT(*),0),1) AS hit_rate_pct
FROM predictions
WHERE status='graded';
```

## Q4 — Hit-rate by rule (Step 3 promote/demote/retire decisions)
A rule "fires" when its id appears in driver_rules. LIKE matches the id substring.

```sql
SELECT 'R-001' AS rule,
  SUM(driver_rules LIKE '%R-001%' AND status='graded')           AS graded,
  SUM(driver_rules LIKE '%R-001%' AND grade='HIT')               AS hit,
  ROUND(100.0*SUM(driver_rules LIKE '%R-001%' AND grade='HIT')
        /NULLIF(SUM(driver_rules LIKE '%R-001%' AND status='graded'),0),1) AS hit_rate_pct
FROM predictions;
```
(Repeat per rule id, or loop the rule ids in a tiny script.)

## Q5 — Hit-rate by conviction bucket (calibration check)
```sql
SELECT conviction,
  COUNT(*) AS graded,
  SUM(grade='HIT') AS hit,
  ROUND(100.0*SUM(grade='HIT')/NULLIF(COUNT(*),0),1) AS hit_rate_pct
FROM predictions
WHERE status='graded'
GROUP BY conviction
ORDER BY conviction;
```

## Q6 — Open prediction count + next grade dates (Step 0 / Step 8 stats)
```sql
SELECT prediction_id, grade_on_date, ticker_or_index
FROM predictions
WHERE status='open'
ORDER BY grade_on_date;
```

## Q7 — Trade history for a ticker (P&L context)
```sql
SELECT date, action, qty, paper_price, net_value, reason
FROM trades
WHERE ticker='FFC'
ORDER BY date;
```
