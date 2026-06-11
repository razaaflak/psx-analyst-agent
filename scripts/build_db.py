#!/usr/bin/env python3
"""
build_db.py — (re)build data/psx.db from the canonical flat files.

The CSVs and market_data/*.json are the SOURCE OF TRUTH. This database is a
DERIVED, queryable copy. It can be deleted and rebuilt at any time with no data
loss. If the DB ever disagrees with the CSVs, the CSVs win — rerun this script.

Tables built:
  predictions  <- data/predictions_log.csv   (append-only history; grading cols filled later)
  trades       <- data/trade_ledger.csv       (append-only paper trades)
  prices_eod   <- data/market_data/*.json     (one row per (date, symbol); queryable price index)

Usage:
  python scripts/build_db.py            # rebuild data/psx.db
  python scripts/build_db.py --verify   # rebuild, then print reconciliation report
"""
import csv
import glob
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DB_PATH = os.path.join(DATA, "psx.db")
PRED_CSV = os.path.join(DATA, "predictions_log.csv")
TRADE_CSV = os.path.join(DATA, "trade_ledger.csv")
MARKET_GLOB = os.path.join(DATA, "market_data", "*.json")


def read_csv_rows(path):
    """Return (header, data_rows). Skips blank lines and '#' comment lines."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = [r for r in reader if r and not (r[0].lstrip().startswith("#"))]
    header, data = rows[0], rows[1:]
    # drop rows that are entirely empty after the comment/blank filter
    data = [r for r in data if any(cell.strip() for cell in r)]
    return header, data


def build_predictions(con):
    header, data = read_csv_rows(PRED_CSV)
    cols = ", ".join(f'"{c}" TEXT' for c in header)
    con.execute(f"CREATE TABLE predictions ({cols})")
    placeholders = ", ".join("?" * len(header))
    # normalise each row to header length (trailing empty grading cols)
    norm = [r + [""] * (len(header) - len(r)) for r in data]
    con.executemany(f"INSERT INTO predictions VALUES ({placeholders})", norm)
    return len(norm)


def build_trades(con):
    header, data = read_csv_rows(TRADE_CSV)
    cols = ", ".join(f'"{c}" TEXT' for c in header)
    con.execute(f"CREATE TABLE trades ({cols})")
    placeholders = ", ".join("?" * len(header))
    norm = [r + [""] * (len(header) - len(r)) for r in data]
    con.executemany(f"INSERT INTO trades VALUES ({placeholders})", norm)
    return len(norm)


def build_prices(con):
    con.execute(
        """CREATE TABLE prices_eod (
            date TEXT, symbol TEXT, open REAL, high REAL, low REAL,
            close REAL, ldcp REAL, volume INTEGER, change_pct REAL,
            pe_ttm REAL, w52_low REAL, w52_high REAL, source TEXT,
            PRIMARY KEY (date, symbol)
        )"""
    )
    con.execute(
        """CREATE TABLE index_eod (
            date TEXT PRIMARY KEY, kse100 REAL, change_pts REAL,
            change_pct REAL, volume INTEGER, advancers INTEGER, decliners INTEGER
        )"""
    )
    n = 0
    ni = 0
    for path in sorted(glob.glob(MARKET_GLOB)):
        with open(path, "r", encoding="utf-8") as f:
            blob = json.load(f)
        date = blob.get("date")
        for s in blob.get("stocks", []):
            con.execute(
                "INSERT OR REPLACE INTO prices_eod VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    date, s.get("symbol"), s.get("open"), s.get("high"),
                    s.get("low"), s.get("close"), s.get("ldcp"), s.get("volume"),
                    s.get("change_pct"), s.get("pe_ttm"),
                    s.get("52w_low"), s.get("52w_high"), s.get("source"),
                ),
            )
            n += 1
        idx = blob.get("index") or {}
        if idx:
            con.execute(
                "INSERT OR REPLACE INTO index_eod VALUES (?,?,?,?,?,?,?)",
                (
                    date, idx.get("kse100"), idx.get("change_pts"),
                    idx.get("change_pct"), idx.get("volume"),
                    idx.get("advancers"), idx.get("decliners"),
                ),
            )
            ni += 1
    return n, ni


def main():
    verify = "--verify" in sys.argv
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)  # always rebuild clean; CSVs are the truth
    con = sqlite3.connect(DB_PATH)
    try:
        np = build_predictions(con)
        nt = build_trades(con)
        npr, nidx = build_prices(con)
        con.commit()
    finally:
        con.close()

    print(f"Built {DB_PATH}")
    print(f"  predictions rows : {np}")
    print(f"  trades rows      : {nt}")
    print(f"  prices_eod rows  : {npr}")
    print(f"  index_eod rows   : {nidx}")

    if verify:
        # reconciliation: DB row counts must equal CSV data-row counts
        _, pdata = read_csv_rows(PRED_CSV)
        _, tdata = read_csv_rows(TRADE_CSV)
        con = sqlite3.connect(DB_PATH)
        db_pred = con.execute("SELECT count(*) FROM predictions").fetchone()[0]
        db_trade = con.execute("SELECT count(*) FROM trades").fetchone()[0]
        graded = con.execute(
            "SELECT count(*) FROM predictions WHERE status='graded'"
        ).fetchone()[0]
        hits = con.execute(
            "SELECT count(*) FROM predictions WHERE grade='HIT'"
        ).fetchone()[0]
        con.close()
        print("\n=== RECONCILIATION ===")
        print(f"  predictions: CSV={len(pdata)}  DB={db_pred}  "
              f"{'MATCH' if len(pdata) == db_pred else 'MISMATCH!!'}")
        print(f"  trades     : CSV={len(tdata)}  DB={db_trade}  "
              f"{'MATCH' if len(tdata) == db_trade else 'MISMATCH!!'}")
        print(f"  graded={graded}  hits={hits}  "
              f"hit_rate={ (100.0*hits/graded) if graded else 'n/a' }")
        ok = len(pdata) == db_pred and len(tdata) == db_trade
        print("  GATE:", "PASS" if ok else "FAIL")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
