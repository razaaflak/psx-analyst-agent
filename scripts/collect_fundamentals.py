"""
PSX Fundamentals Collector — quarterly results + payout history per symbol.

Sources
-------
1. Quarterly results (EPS / PAT / PBT):
   GET https://psx.com.pk/psx/announcement/financial-announcements
   Static HTML table; 1 464+ rows covering all listed companies.
   Rows are matched to tickers via a full-name → ticker map (auto-generated
   from universe.json + watchlist, supplemented by a manual override table).
   Announcement date is in <th colspan="9"><h4>DATE</h4></th> rows that
   precede the data rows for that date.

2. Payouts (dividend / bonus / right):
   POST https://dps.psx.com.pk/company/payouts  body: symbol=SYM
   Returns an HTML table with columns: Date | Financial Results | Details |
   Book Closure.  Only recent payouts appear (typically 6–10 rows, going
   back ~12–18 months).

Output: data/fundamentals/{SYM}.json  — one file per symbol.
Schema:
  {
    "symbol": "OGDC",
    "fetched": "2026-06-13",
    "sources": ["https://psx.com.pk/psx/...", "https://dps.psx.com.pk/..."],
    "quarterly_results": [
      {"announced": "2026-04-29", "period": "31/03/2026", "period_type": "IIIQ",
       "eps": 26.80, "pat": 115262.705, "pbt": 175798.519,
       "consolidated": true}
    ],
    "payouts": [
      {"announced": "2026-04-29", "period": "31/03/2026", "period_type": "IIIQ",
       "type": "dividend", "pct": 32.50, "interim_label": "iii",
       "ex_or_bc": "12/05/2026 - 13/05/2026"}
    ]
  }

IMPORTANT — face value warning:
  PSX payouts are declared as % of face value.  Face values differ per company
  and can change after stock splits (e.g. UBL Rs 5 post-2025 split,
  MTL Rs 5 post-June-2026 split).  This script stores the RAW % as declared.
  Do NOT convert % → PKR here; let the analyst do that with the current FV.

Idempotent:
  Re-runs merge on (period + period_type + consolidated) for results,
  and on (announced + period + period_type + pct) for payouts.
  Existing records are kept; new or updated records from the source win.

Usage:
  python scripts/collect_fundamentals.py                      # all watchlist symbols
  python scripts/collect_fundamentals.py --watchlist          # same
  python scripts/collect_fundamentals.py --universe           # all KSE-100 symbols
  python scripts/collect_fundamentals.py --symbols OGDC,MCB   # specific symbols
"""

import argparse
import json
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# UTF-8 stdout fix (Windows cp1252 chokes on Unicode)
# ---------------------------------------------------------------------------
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FUND_DIR = REPO_ROOT / "data" / "fundamentals"
WATCHLIST_PATH = REPO_ROOT / "data" / "watchlist.json"
UNIVERSE_PATH  = REPO_ROOT / "data" / "universe.json"

FIN_ANN_URL = "https://psx.com.pk/psx/announcement/financial-announcements"
PAYOUTS_URL = "https://dps.psx.com.pk/company/payouts"

SLEEP_BETWEEN = 1.1   # seconds between per-symbol payout requests

# ---------------------------------------------------------------------------
# Manual name overrides for the financial-announcements page.
# Only needed when the PSX announcement name differs from universe.json name.
# Keys are lowercase substrings; values are ticker symbols.
# Auto-generated entries from universe.json take lower priority than these.
# ---------------------------------------------------------------------------
NAME_OVERRIDES: dict[str, str] = {
    "mari energies limited":            "MARI",   # renamed from Mari Petroleum
    "mari petroleum":                   "MARI",   # legacy name still appears
    "oil & gas development company":    "OGDC",   # PSX drops "Limited" sometimes
    "engro holdings limited":           "ENGROH",
    "d.g. khan cement company":         "DGKC",   # abbreviated on PSX page
    "the bank of punjab":               "BOP",
    "pakistan state oil company":       "PSO",
    "hub power company":                "HUBC",
    "kot addu power company":           "KAPCO",
    "k-electric limited":               "KEL",
    "karachi electric":                 "KEL",   # PSX may use this name
    "cnergyico":                        "CNERGY",
    "byco petroleum":                   "CNERGY", # legacy name before rebranding
    "pakistan single window":           "PSEL",
    "power sector employees":           "PSEL",
    "pakistan telecommunication":       "PTC",
    "sui northern gas pipelines":       "SNGP",
    "sui southern gas company":         "SSGC",
    "pakistan stock exchange":          "PSX",
    "national bank of pakistan":        "NBP",
    "pakistan national shipping":       "PNSC",   # if listed
    "glaxosmithkline pakistan":         "GLAXO",
    "sanofi-aventis pakistan":          "SAPL",
    "abbott laboratories (pakistan)":   "ABOT",
    "nestle pakistan limited":          "NESTLE",
    "colgate-palmolive (pakistan)":     "COLG",
    "haleon pakistan limited":          "HALEON",
}


def build_name_to_ticker() -> dict[str, str]:
    """
    Build a full name→ticker map by combining:
    1. universe.json names (lowercased, exact match)
    2. watchlist.json names
    3. NAME_OVERRIDES (highest priority, substring match)
    Returns a dict: lowercase name fragment → ticker.
    """
    mapping: dict[str, str] = {}

    # From universe.json
    if UNIVERSE_PATH.exists():
        with open(UNIVERSE_PATH, "r", encoding="utf-8") as f:
            universe = json.load(f)
        for entry in universe.get("symbols", []):
            ticker = entry.get("ticker", "").strip().upper()
            name   = entry.get("name", "").strip().lower()
            if ticker and name:
                mapping[name] = ticker

    # From watchlist.json (may have names not in universe)
    if WATCHLIST_PATH.exists():
        with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
            wl = json.load(f)
        for item in wl.get("watchlist", []):
            ticker = item.get("ticker", "").strip().upper()
            name   = item.get("name", item.get("company", "")).strip().lower()
            if ticker and name and ticker not in {v for v in mapping.values()}:
                mapping[name] = ticker

    # Overrides win (applied last — higher priority)
    mapping.update(NAME_OVERRIDES)

    return mapping


# Built once at module level; used by build_results_for_symbol
NAME_TO_TICKER: dict[str, str] = {}  # populated in main() after path resolution

# ---------------------------------------------------------------------------
# Symbol discovery
# ---------------------------------------------------------------------------

def load_watchlist_symbols() -> list[str]:
    if WATCHLIST_PATH.exists():
        with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
            wl = json.load(f)
        symbols = [item.get("ticker", "").strip().upper()
                   for item in wl.get("watchlist", []) if item.get("ticker")]
        print(f"[symbols] loaded {len(symbols)} tickers from watchlist.json")
        return symbols
    symbols = ["MEBL","MCB","UBL","OGDC","PPL","MARI","FFC","ENGROH",
               "LUCK","MTL","FABL","DGKC","CHCC","PSO","APL"]
    print(f"[symbols] watchlist.json not found — using hardcoded list ({len(symbols)})")
    return symbols


def load_universe_symbols() -> list[str]:
    """Load all KSE-100 tickers from data/universe.json."""
    if not UNIVERSE_PATH.exists():
        print("[symbols] universe.json not found — falling back to watchlist")
        return load_watchlist_symbols()
    with open(UNIVERSE_PATH, "r", encoding="utf-8") as f:
        universe = json.load(f)
    tickers = [e["ticker"].strip().upper() for e in universe.get("symbols", []) if e.get("ticker")]
    # merge watchlist symbols not already in universe
    wl_syms = load_watchlist_symbols()
    universe_set = set(tickers)
    extra = [s for s in wl_syms if s not in universe_set]
    if extra:
        tickers.extend(extra)
        print(f"[symbols] +{len(extra)} watchlist symbols not in universe: {extra}")
    print(f"[symbols] universe total: {len(tickers)} tickers")
    return tickers


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_num(raw: str):
    """Parse a numeric string like '115,262.705 (CS)' → float or None."""
    s = raw.strip()
    if not s or s == "-":
        return None
    # Remove trailing labels like ' (CS)', ' (UCS)', ' (i)', etc.
    s = re.sub(r"\s*\([A-Za-z]+\)\s*$", "", s)
    s = s.strip()
    # Handle loss notation: '(12.50)' → -12.50
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1]
    s = s.replace(",", "")
    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return None


def _parse_period(raw: str):
    """
    Parse period strings like '31/03/2026(IIIQ)' or '31/12/2025(YR)'.
    Returns (period_date_str, period_type) e.g. ('31/03/2026', 'IIIQ').
    """
    raw = raw.strip()
    m = re.match(r"(\d{2}/\d{2}/\d{4})\(([^)]+)\)", raw)
    if m:
        return m.group(1), m.group(2)
    return raw, ""


def _parse_payout_details(details: str):
    """
    Parse payout details like '32.50%(iii) (D)' or '85%(F) (D)' or '= 50% (R)'.
    Returns dict with keys: type ('dividend'|'bonus'|'right'|'unknown'),
    pct (float or None), interim_label (str or None).
    """
    s = details.strip()
    result = {"type": "unknown", "pct": None, "interim_label": None}

    # Determine type from trailing code
    type_map = {"D": "dividend", "B": "bonus", "R": "right"}
    tm = re.search(r"\(([DBR])\)\s*$", s)
    if tm:
        result["type"] = type_map.get(tm.group(1), "unknown")

    # Extract percentage
    pm = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
    if pm:
        result["pct"] = float(pm.group(1))

    # Extract interim label like (i), (ii), (iii), (F)
    im = re.search(r"%\s*\(([^)]+)\)", s)
    if im:
        result["interim_label"] = im.group(1)

    return result


def _parse_date_str(raw: str) -> str:
    """
    Try to normalise a date string to YYYY-MM-DD.
    Handles: 'April 29, 2026 3:56 PM', '29/04/2026', 'Jun 10, 2026', etc.
    Returns original string if parsing fails.
    """
    raw = raw.strip()
    for fmt in ("%B %d, %Y %I:%M %p", "%B %d, %Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    # Try stripping time part then retry
    short = re.sub(r"\s+\d+:\d+.*$", "", raw)
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(short, fmt).date().isoformat()
        except ValueError:
            pass
    return raw


def _is_consolidated(pbt_raw: str):
    """Return True if (CS), False if (UCS), None if unspecified."""
    s = pbt_raw.strip()
    if "(CS)" in s:
        return True
    if "(UCS)" in s:
        return False
    return None


# ---------------------------------------------------------------------------
# Source 1: Financial Announcements page
# ---------------------------------------------------------------------------

def fetch_financial_announcements(session: requests.Session) -> list[dict]:
    """
    Fetch and parse the PSX financial announcements page.
    Returns a list of raw row dicts keyed by lowercase company name fragment.
    """
    print(f"[fin-ann] fetching {FIN_ANN_URL} …", flush=True)
    for attempt in (1, 2):
        try:
            r = session.get(FIN_ANN_URL, timeout=30)
            r.raise_for_status()
            break
        except requests.RequestException as e:
            if attempt == 2:
                print(f"  [WARN] financial-announcements fetch failed after retry: {e}")
                return []
            print(f"  [WARN] attempt {attempt} failed, retrying …")
            time.sleep(2.0)

    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table")
    if not table:
        print("  [WARN] no <table> found on financial-announcements page")
        return []

    # NOTE: the raw HTML served to plain requests has NO <tbody> — browsers
    # inject it. Fall back to the table itself.
    tbody = table.find("tbody") or table

    rows_raw = []
    current_date = ""

    for tr in tbody.find_all("tr"):
        # Header/date rows come in two shapes depending on render:
        #   <th colspan="9"><h4>Jun 10, 2026</h4></th>   (browser DOM)
        #   <td colspan="9">Jun 10, 2026</td>            (raw HTML, single cell)
        th = tr.find("th")
        if th:
            h4 = th.find("h4")
            if h4:
                current_date = _parse_date_str(h4.get_text(strip=True))
            continue  # also skips the column-header row

        cells = tr.find_all("td")
        if len(cells) == 1:
            # single-cell row = date separator in raw HTML
            txt = cells[0].get_text(strip=True)
            parsed = _parse_date_str(txt)
            if parsed != txt or re.match(r"^[A-Z][a-z]{2} \d{1,2}, \d{4}$", txt):
                current_date = parsed
            continue
        if len(cells) < 7:
            continue

        company_name = cells[0].get_text(strip=True)
        time_str     = cells[1].get_text(strip=True)
        period_raw   = cells[2].get_text(strip=True)
        payout_raw   = cells[3].get_text(strip=True)
        pbt_raw      = cells[4].get_text(strip=True)
        pat_raw      = cells[5].get_text(strip=True)
        eps_raw      = cells[6].get_text(strip=True)
        book_closure = cells[8].get_text(strip=True) if len(cells) > 8 else ""

        rows_raw.append({
            "announced_date": current_date,
            "company_name":   company_name,
            "period_raw":     period_raw,
            "payout_raw":     payout_raw,
            "pbt_raw":        pbt_raw,
            "pat_raw":        pat_raw,
            "eps_raw":        eps_raw,
            "book_closure":   book_closure,
        })

    print(f"  [fin-ann] parsed {len(rows_raw)} data rows")
    return rows_raw


def build_results_for_symbol(symbol: str, all_rows: list[dict]) -> list[dict]:
    """
    Filter all_rows to those matching symbol, parse numeric fields,
    return list of quarterly_result dicts.
    Matching strategy: exact lowercase match first, then substring.
    """
    matching_patterns = [k for k, v in NAME_TO_TICKER.items() if v == symbol]
    if not matching_patterns:
        return []

    results = []
    for row in all_rows:
        cn = row["company_name"].lower()
        # Exact match first, then substring — avoids e.g. "engro" matching both ENGROH and EFERT
        matched = (cn in matching_patterns) or any(pat in cn for pat in matching_patterns)
        if not matched:
            continue

        period_raw = row["period_raw"]
        if not period_raw or period_raw == "-":
            continue

        period_str, period_type = _parse_period(period_raw)

        eps = _parse_num(row["eps_raw"])
        pat = _parse_num(row["pat_raw"])
        pbt = _parse_num(row["pbt_raw"])

        # Skip rows that have no financial data at all
        if eps is None and pat is None and pbt is None:
            continue

        consolidated = _is_consolidated(row["pbt_raw"])

        rec = {
            "announced":   row["announced_date"],
            "period":      period_str,
            "period_type": period_type,
            "consolidated": consolidated,
        }
        if eps is not None:
            rec["eps"] = eps
        if pat is not None:
            rec["pat"] = pat
        if pbt is not None:
            rec["pbt"] = pbt

        # Payout info embedded in this row (e.g. OGDC announces div with results)
        # Stored separately in payouts, but note it here too
        if row["payout_raw"] and row["payout_raw"] != "-":
            rec["payout_note"] = row["payout_raw"].strip()

        results.append(rec)

    return results


# ---------------------------------------------------------------------------
# Source 2: /company/payouts endpoint
# ---------------------------------------------------------------------------

def fetch_payouts(session: requests.Session, symbol: str) -> list[dict]:
    """
    POST /company/payouts with symbol=SYM.
    Returns parsed list of payout dicts.
    """
    for attempt in (1, 2):
        try:
            r = session.post(PAYOUTS_URL, data={"symbol": symbol}, timeout=20)
            r.raise_for_status()
            break
        except requests.RequestException as e:
            if attempt == 2:
                print(f"    [WARN] payouts fetch failed for {symbol} after retry: {e}")
                return []
            print(f"    [WARN] payouts attempt {attempt} failed, retrying …")
            time.sleep(2.0)

    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table")
    if not table:
        return []

    payouts = []
    tbody = table.find("tbody")
    tr_list = tbody.find_all("tr") if tbody else []
    for tr in tr_list:
        cells = tr.find_all("td")
        if len(cells) < 3:
            continue

        announced_raw = cells[0].get_text(strip=True)   # "April 29, 2026 3:56 PM"
        period_raw    = cells[1].get_text(strip=True)   # "31/03/2026(IIIQ)"
        details_raw   = cells[2].get_text(strip=True)   # " 32.50%(iii) (D) "
        bc_raw        = cells[3].get_text(strip=True) if len(cells) > 3 else ""

        if not details_raw or details_raw == "-":
            continue

        period_str, period_type = _parse_period(period_raw)
        details = _parse_payout_details(details_raw)

        rec: dict = {
            "announced":   _parse_date_str(announced_raw),
            "period":      period_str,
            "period_type": period_type,
            "type":        details["type"],
        }
        if details["pct"] is not None:
            rec["pct"] = details["pct"]
        if details["interim_label"]:
            rec["interim_label"] = details["interim_label"]
        if bc_raw and bc_raw not in ("-", ""):
            rec["ex_or_bc"] = bc_raw.strip()

        payouts.append(rec)

    return payouts


# ---------------------------------------------------------------------------
# Merge helpers (idempotent)
# ---------------------------------------------------------------------------

def _result_key(r: dict) -> tuple:
    """Dedup key for a quarterly result record."""
    return (r.get("period", ""), r.get("period_type", ""), r.get("consolidated"))


def _payout_key(p: dict) -> tuple:
    """Dedup key for a payout record."""
    return (p.get("announced", ""), p.get("period", ""), p.get("period_type", ""),
            p.get("type", ""), p.get("pct"))


def merge_records(existing: list[dict], new_records: list[dict],
                  keyfn) -> list[dict]:
    """Merge new_records into existing; new wins on key collision."""
    by_key = {keyfn(r): r for r in existing}
    for r in new_records:
        by_key[keyfn(r)] = r
    # Sort by announced date descending (most recent first), then period
    return sorted(by_key.values(),
                  key=lambda r: (r.get("announced", ""), r.get("period", "")),
                  reverse=True)


# ---------------------------------------------------------------------------
# Load / save JSON
# ---------------------------------------------------------------------------

def load_existing(sym: str) -> dict:
    path = DATA_FUND_DIR / f"{sym}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"symbol": sym, "quarterly_results": [], "payouts": []}


def save_fund(sym: str, data: dict) -> None:
    DATA_FUND_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_FUND_DIR / f"{sym}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(symbols: list[str]) -> None:
    today = date.today().isoformat()

    session = requests.Session()
    session.headers.update({
        "User-Agent": "PSX-FundamentalsCollector/1.0",
        "Accept": "text/html,application/xhtml+xml,*/*",
    })

    # --- Step 1: fetch the full announcements page once (shared across all symbols)
    all_rows = fetch_financial_announcements(session)

    print()
    summary = []

    for sym in symbols:
        print(f"  [{sym}]", end=" ", flush=True)

        existing = load_existing(sym)

        # --- Quarterly results from announcements page
        new_results = build_results_for_symbol(sym, all_rows)

        merged_results = merge_records(
            existing.get("quarterly_results", []),
            new_results,
            _result_key,
        )
        print(f"results:{len(merged_results)}", end="  ", flush=True)

        # --- Payouts from DPS endpoint (polite sleep between calls)
        time.sleep(SLEEP_BETWEEN)
        new_payouts = fetch_payouts(session, sym)
        merged_payouts = merge_records(
            existing.get("payouts", []),
            new_payouts,
            _payout_key,
        )
        print(f"payouts:{len(merged_payouts)}", flush=True)

        data = {
            "symbol":  sym,
            "fetched": today,
            "sources": [FIN_ANN_URL, PAYOUTS_URL],
            "quarterly_results": merged_results,
            "payouts": merged_payouts,
        }
        save_fund(sym, data)

        summary.append({
            "symbol":  sym,
            "results": len(merged_results),
            "payouts": len(merged_payouts),
            "status":  "ok" if (merged_results or merged_payouts) else "no-data",
        })

    # --- Summary table
    print()
    print("=" * 60)
    print(f"{'SYMBOL':<10} {'RESULTS':>8} {'PAYOUTS':>8}  STATUS")
    print("-" * 60)
    no_data = []
    for row in summary:
        print(f"{row['symbol']:<10} {row['results']:>8} {row['payouts']:>8}  {row['status']}")
        if row["status"] == "no-data":
            no_data.append(row["symbol"])
    print("=" * 60)
    if no_data:
        print(f"\nWARN: no data found for: {', '.join(no_data)}")
        print("  Check NAME_TO_TICKER map — company may use a different name on the announcements page.")
    else:
        print("\nAll symbols completed with at least some data.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    global NAME_TO_TICKER

    parser = argparse.ArgumentParser(
        description="PSX Fundamentals Collector — quarterly EPS/PAT + payouts per symbol"
    )
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--watchlist", action="store_true",
                     help="Use tickers from data/watchlist.json (default)")
    grp.add_argument("--universe", action="store_true",
                     help="Use all KSE-100 tickers from data/universe.json")
    grp.add_argument("--symbols", type=str,
                     help="Comma-separated ticker list, e.g. OGDC,MCB,UBL")
    args = parser.parse_args()

    # Build name→ticker map once paths are resolved
    NAME_TO_TICKER = build_name_to_ticker()
    print(f"[name-map] {len(NAME_TO_TICKER)} name patterns loaded")

    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        print(f"[symbols] from --symbols arg: {symbols}")
    elif args.universe:
        symbols = load_universe_symbols()
    else:
        symbols = load_watchlist_symbols()

    # Never attempt fundamentals for KSE100 (it's an index, not a company)
    symbols = [s for s in symbols if s != "KSE100"]

    run(symbols)


if __name__ == "__main__":
    main()
