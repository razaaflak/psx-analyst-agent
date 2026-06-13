"""
PSX OHLC Collector — canonical OHLC store for the daily pipeline.

Source endpoint:
  POST https://dps.psx.com.pk/historical
  Form body: {"month": <int 1-12>, "year": <int>, "symbol": "<SYM>"}
  Returns an HTML table with headers: DATE, OPEN, HIGH, LOW, CLOSE, VOLUME
  One symbol-month per request (~10-22 rows). DATE format "Jun 12, 2026".

KSE100 special note:
  /historical also accepts "KSE100" and returns full OHLC candles.
  No fallback to /timeseries/eod is needed.

Output: data/ohlc/{SYMBOL}.json  — list of bars, date-ascending.
Schema:  [{"date":"2026-06-12","open":198.9,"high":208.9,"low":197.8,"close":206.32,"volume":14121963}, ...]

Usage:
  python scripts/collect_ohlc.py --backfill --months 12   # last N calendar months
  python scripts/collect_ohlc.py --backfill --years 5     # last N years (= years*12 months)
  python scripts/collect_ohlc.py --update                 # current month only (idempotent)
  python scripts/collect_ohlc.py --backfill --years 5 --universe   # KSE-100 universe from data/universe.json
"""

import argparse
import json
import os
import time
import sys
from datetime import date, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Windows consoles default to cp1252 and choke on Unicode (→) in print().
# Force UTF-8 on stdout/stderr so the script runs identically on Windows.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_OHLC_DIR = REPO_ROOT / "data" / "ohlc"
WATCHLIST_PATH = REPO_ROOT / "data" / "watchlist.json"
UNIVERSE_PATH = REPO_ROOT / "data" / "universe.json"

HISTORICAL_URL = "https://dps.psx.com.pk/historical"

HARDCODED_SYMBOLS = [
    "OGDC", "PPL", "MARI", "MEBL", "FABL", "UBL", "MCB",
    "FFC", "ENGROH", "LUCK", "DGKC", "CHCC", "MTL", "PSO", "APL",
    "KSE100",
]

SLEEP_MIN = 1.0   # seconds between requests
SLEEP_MAX = 1.5

# ---------------------------------------------------------------------------
# Symbol discovery
# ---------------------------------------------------------------------------

def load_symbols() -> list[str]:
    """Load symbols from watchlist.json (tickers) + always include KSE100."""
    symbols: list[str] = []
    if WATCHLIST_PATH.exists():
        with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
            wl = json.load(f)
        for item in wl.get("watchlist", []):
            t = item.get("ticker", "").strip().upper()
            if t:
                symbols.append(t)
        print(f"[symbols] loaded {len(symbols)} tickers from watchlist.json")
    else:
        symbols = [s for s in HARDCODED_SYMBOLS if s != "KSE100"]
        print(f"[symbols] watchlist.json not found — using hardcoded list ({len(symbols)} stocks)")

    if "KSE100" not in symbols:
        symbols.append("KSE100")
    return symbols


def load_universe_symbols() -> list[str]:
    """Load symbols from data/universe.json (KSE-100 constituents) + KSE100 index.

    Watchlist tickers are merged in too, so the watchlist never silently
    loses coverage if a name drops out of the index.
    """
    if not UNIVERSE_PATH.exists():
        print(f"[symbols] ERROR: {UNIVERSE_PATH} not found — run the universe fetch first "
              f"or omit --universe to use the watchlist.")
        sys.exit(1)
    with open(UNIVERSE_PATH, "r", encoding="utf-8") as f:
        uni = json.load(f)
    symbols = []
    for item in uni.get("symbols", []):
        t = item.get("ticker", "").strip().upper()
        if t and t not in symbols:
            symbols.append(t)
    print(f"[symbols] loaded {len(symbols)} tickers from universe.json")
    # merge watchlist (in case a watched name isn't an index member)
    for t in load_symbols():
        if t not in symbols:
            symbols.append(t)
    return symbols

# ---------------------------------------------------------------------------
# Fetching + parsing
# ---------------------------------------------------------------------------

def _parse_val(raw: str):
    """Parse a numeric cell; returns float or None for blank/dash."""
    s = raw.strip().replace(",", "")
    if not s or s == "-":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def fetch_month(session: requests.Session, symbol: str, month: int, year: int) -> list[dict]:
    """
    Fetch one symbol-month from /historical.
    Returns a list of bar dicts, or [] on empty/failure.
    Retries once on network error.
    """
    payload = {"month": month, "year": year, "symbol": symbol}

    for attempt in (1, 2):
        try:
            r = session.post(HISTORICAL_URL, data=payload, timeout=30)
            r.raise_for_status()
            break
        except requests.RequestException as e:
            if attempt == 2:
                print(f"    [WARN] {symbol} {year}-{month:02d}: request failed after retry — {e}")
                return []
            print(f"    [WARN] {symbol} {year}-{month:02d}: attempt {attempt} failed, retrying…")
            time.sleep(2.0)

    soup = BeautifulSoup(r.text, "html.parser")
    raw_rows = [
        [td.get_text(strip=True) for td in tr.select("td")]
        for tr in soup.select("tr")
        if tr.select("td")
    ]

    bars: list[dict] = []
    for cells in raw_rows:
        if len(cells) < 6:
            continue
        date_str, open_s, high_s, low_s, close_s, vol_s = (
            cells[0], cells[1], cells[2], cells[3], cells[4], cells[5]
        )
        # Parse date — format "Jun 12, 2026"
        try:
            d = datetime.strptime(date_str, "%b %d, %Y").date()
        except ValueError:
            continue  # skip header or garbage rows

        # PSX is closed weekends. The /historical endpoint sometimes emits
        # carried-forward Sat/Sun rows — drop them so MA/RSI aren't polluted.
        if d.weekday() >= 5:  # 5=Sat, 6=Sun
            continue

        bar: dict = {
            "date": d.isoformat(),
            "open": _parse_val(open_s),
            "high": _parse_val(high_s),
            "low": _parse_val(low_s),
            "close": _parse_val(close_s),
            "volume": None,
        }

        vol_raw = _parse_val(vol_s)
        if vol_raw is not None:
            bar["volume"] = int(vol_raw)

        # Mark close-only bars if open/high/low all null (index fallback, unlikely now)
        if bar["open"] is None and bar["high"] is None and bar["low"] is None:
            bar["ohlc_available"] = False

        bars.append(bar)

    return bars


# ---------------------------------------------------------------------------
# Month helpers
# ---------------------------------------------------------------------------

def months_to_fetch(n_months: int) -> list[tuple[int, int]]:
    """
    Return a list of (month, year) tuples for the last n_months calendar months,
    ordered oldest-first (so we can page forward naturally).
    Includes the current partial month.
    """
    today = date.today()
    result = []
    y, m = today.year, today.month
    for _ in range(n_months):
        result.append((m, y))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    result.reverse()  # oldest first
    return result


# ---------------------------------------------------------------------------
# Merge / persist
# ---------------------------------------------------------------------------

def load_existing(path: Path) -> dict[str, dict]:
    """Load existing JSON, return dict keyed by date string."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Handle legacy format where outer wrapper object exists
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    if isinstance(data, str):
        # Double-encoded JSON (old KSE100 format)
        data = json.loads(data)
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
    if not isinstance(data, list):
        return {}
    return {bar["date"]: bar for bar in data if "date" in bar}


def save_bars(path: Path, bars_by_date: dict[str, dict]) -> None:
    """Write bars to JSON, sorted ascending by date."""
    sorted_bars = sorted(bars_by_date.values(), key=lambda b: b["date"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted_bars, f, indent=1)


def merge_bars(existing: dict[str, dict], new_bars: list[dict]) -> dict[str, dict]:
    """Merge new bars into existing dict; newer fetch wins on conflict."""
    merged = dict(existing)
    for bar in new_bars:
        merged[bar["date"]] = bar  # new data overwrites old
    return merged


# ---------------------------------------------------------------------------
# Main runners
# ---------------------------------------------------------------------------

def run_backfill(symbols: list[str], n_months: int, skip_existing: bool = True) -> None:
    month_list = months_to_fetch(n_months)
    print(f"\n[backfill] {len(symbols)} symbols × {len(month_list)} months "
          f"({month_list[0][1]}-{month_list[0][0]:02d} → {month_list[-1][1]}-{month_list[-1][0]:02d})\n")

    session = requests.Session()
    session.headers.update({"User-Agent": "PSX-OHLCCollector/1.0"})

    errors: list[str] = []
    summary: list[dict] = []

    for sym in symbols:
        path = DATA_OHLC_DIR / f"{sym}.json"

        # Skip symbols that already have a full backfill (≥ n_months * 15 bars as heuristic)
        if skip_existing and path.exists():
            existing_check = load_existing(path)
            min_expected = n_months * 15  # conservative: 15 trading days/month avg
            if len(existing_check) >= min_expected:
                print(f"  {sym}: skip (already {len(existing_check)} bars)")
                bars_sorted = sorted(existing_check.values(), key=lambda b: b["date"])
                summary.append({
                    "symbol": sym, "bar_count": len(bars_sorted),
                    "first_date": bars_sorted[0]["date"] if bars_sorted else "N/A",
                    "last_date": bars_sorted[-1]["date"] if bars_sorted else "N/A",
                    "status": "skipped",
                })
                continue

        existing = load_existing(path)
        total_new = 0

        print(f"  {sym}:", end="", flush=True)
        for (month, year) in month_list:
            bars = fetch_month(session, sym, month, year)
            if bars:
                before = len(existing)
                existing = merge_bars(existing, bars)
                added = len(existing) - before
                total_new += added
                print(f" {year}-{month:02d}({len(bars)})", end="", flush=True)
            else:
                print(f" {year}-{month:02d}(0)", end="", flush=True)

            sleep_time = SLEEP_MIN + (SLEEP_MAX - SLEEP_MIN) * (hash(f"{sym}{year}{month}") % 100 / 100)
            time.sleep(sleep_time)

        save_bars(path, existing)
        bars_sorted = sorted(existing.values(), key=lambda b: b["date"])
        bar_count = len(bars_sorted)
        first_date = bars_sorted[0]["date"] if bars_sorted else "N/A"
        last_date = bars_sorted[-1]["date"] if bars_sorted else "N/A"
        print(f" → {bar_count} bars total")

        summary.append({
            "symbol": sym,
            "bar_count": bar_count,
            "first_date": first_date,
            "last_date": last_date,
            "status": "ok",
        })

    _print_summary(summary, errors)


def run_update(symbols: list[str]) -> None:
    today = date.today()
    month, year = today.month, today.year
    print(f"\n[update] fetching current month ({year}-{month:02d}) for {len(symbols)} symbols\n")

    session = requests.Session()
    session.headers.update({"User-Agent": "PSX-OHLCCollector/1.0"})

    errors: list[str] = []
    summary: list[dict] = []

    for sym in symbols:
        path = DATA_OHLC_DIR / f"{sym}.json"
        existing = load_existing(path)
        before = len(existing)

        bars = fetch_month(session, sym, month, year)
        if bars:
            existing = merge_bars(existing, bars)
        added = len(existing) - before

        save_bars(path, existing)
        bars_sorted = sorted(existing.values(), key=lambda b: b["date"])
        bar_count = len(bars_sorted)
        first_date = bars_sorted[0]["date"] if bars_sorted else "N/A"
        last_date = bars_sorted[-1]["date"] if bars_sorted else "N/A"

        status = f"+{added} new" if added > 0 else "no new rows"
        print(f"  {sym}: {bar_count} bars  ({first_date} → {last_date})  [{status}]")

        summary.append({
            "symbol": sym,
            "bar_count": bar_count,
            "first_date": first_date,
            "last_date": last_date,
            "status": status,
        })

        sleep_time = SLEEP_MIN + (SLEEP_MAX - SLEEP_MIN) * (hash(f"{sym}{year}{month}") % 100 / 100)
        time.sleep(sleep_time)

    _print_summary(summary, errors, compact=True)


def _print_summary(summary: list[dict], errors: list[str], compact: bool = False) -> None:
    if compact:
        return  # update mode already prints inline
    print("\n" + "=" * 72)
    print(f"{'SYMBOL':<10} {'BARS':>6}  {'FIRST':>12}  {'LAST':>12}  STATUS")
    print("-" * 72)
    for row in summary:
        print(f"{row['symbol']:<10} {row['bar_count']:>6}  {row['first_date']:>12}  {row['last_date']:>12}  {row['status']}")
    print("=" * 72)

    if errors:
        print("\nERRORS:")
        for e in errors:
            print(f"  {e}")
    else:
        print("\nAll symbols completed without fatal errors.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="PSX OHLC Collector — backfill or daily-update data/ohlc/*.json"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--backfill", action="store_true", help="Fetch historical months")
    mode.add_argument("--update", action="store_true", help="Fetch current month only (idempotent)")
    parser.add_argument(
        "--months", type=int, default=12,
        help="Number of calendar months to backfill (default: 12)"
    )
    parser.add_argument(
        "--years", type=int, default=None,
        help="Backfill N years (overrides --months; = N*12 months)"
    )
    parser.add_argument(
        "--universe", action="store_true",
        help="Use data/universe.json (KSE-100 constituents) instead of watchlist.json"
    )
    parser.add_argument(
        "--symbols", type=str, default=None,
        help="Comma-separated ticker list, e.g. HBL,NBP,UBL (overrides --universe/watchlist)"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-fetch all symbols even if they already have data (disables skip-if-exists)"
    )
    args = parser.parse_args()

    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        print(f"[symbols] from --symbols arg: {len(symbols)} tickers")
    elif args.universe:
        symbols = load_universe_symbols()
    else:
        symbols = load_symbols()
    n_months = args.years * 12 if args.years else args.months

    if args.backfill:
        run_backfill(symbols, n_months, skip_existing=not args.force)
    elif args.update:
        run_update(symbols)


if __name__ == "__main__":
    main()
