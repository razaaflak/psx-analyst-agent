"""
Counterfactual baselines — answers "is the agent adding anything, or would a dumb
default have done as well?" The advisor is only useful if it beats simple alternatives
over time.

WHY THIS EXISTS
  A prediction can hit while the book underperforms (this already happened: 2/2 graded
  HITs but the book LAGGED KSE-100 that week). Hit-rate ≠ advisory value. The honest
  scoreboard is: book return vs a few trivial baselines, since portfolio inception.
  All of these are closed-form from data already stored — computable even at n=2,
  because it's portfolio arithmetic, not a hit-rate needing a sample.

BASELINES (all start from the same starting_cash, same inception date)
  1. ALL-CASH        : never invested. Return = 0%. (The "did trading even help?" floor.)
  2. KSE-100         : starting_cash fully into the index at inception close. (Beat-the-market bar.)
  3. EQUAL-WEIGHT    : starting_cash split equally across the inception holdings. (Did sizing help?)
  4. HOLD-DAY-1      : the actual day-1 holdings, held untouched to today. (Did later activity help?)
  5. BOOK (actual)   : the real paper portfolio's current marked-to-market equity.

  Comparing BOOK vs HOLD-DAY-1 isolates the value of everything done AFTER day 1.
  Comparing BOOK vs EQUAL-WEIGHT isolates sizing skill.
  Comparing BOOK vs KSE-100 is the alpha bar. BOOK vs CASH is the survival bar.

Prices come from the raw OHLC store (data/ohlc/*.json). Inception = the portfolio's
earliest first_bought date. "Now" = the latest common close available (no look-ahead,
no fabrication; if a symbol lacks a current bar it's marked and excluded with a warning).

Usage:
  python scripts/counterfactuals.py                 # as of latest available close
  python scripts/counterfactuals.py --asof 2026-06-12
  python scripts/counterfactuals.py --json          # machine-readable (for the weekly report)

This is paper research only. Not financial advice.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"
OHLC_DIR = DATA / "ohlc"
PORTFOLIO = DATA / "portfolio.json"

_cache: dict[str, list[dict]] = {}


def load_ohlc(symbol: str) -> list[dict]:
    sym = symbol.upper()
    if sym in _cache:
        return _cache[sym]
    path = OHLC_DIR / f"{sym}.json"
    bars: list[dict] = []
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        if isinstance(data, str):
            data = json.loads(data)
        if isinstance(data, list):
            bars = sorted(
                [b for b in data if b.get("date") and b.get("close") is not None],
                key=lambda b: b["date"],
            )
            # This script is entirely return-based (ratios since inception), so prefer the
            # split/bonus-adjusted close — a holding that split mid-window would otherwise
            # show a spurious crash. Raw close untouched in the file. NOTE: 'now' MTM uses
            # the current real price, which equals adj_close at the right edge (factor 1.0).
            for b in bars:
                if b.get("adj_close") is not None:
                    b["close"] = b["adj_close"]
    _cache[sym] = bars
    return bars


def close_on_or_before(symbol: str, d: str) -> tuple[str | None, float | None]:
    prior = [b for b in load_ohlc(symbol) if b["date"] <= d]
    if not prior:
        return None, None
    return prior[-1]["date"], prior[-1]["close"]


def main() -> None:
    ap = argparse.ArgumentParser(description="Counterfactual baselines vs the paper book.")
    ap.add_argument("--asof", type=str, default=None, help="Valuation date (default: latest common close)")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = ap.parse_args()

    with open(PORTFOLIO, "r", encoding="utf-8") as f:
        pf = json.load(f)

    starting_cash = float(pf["starting_cash"])
    holdings = pf["holdings"]
    cash_now = float(pf.get("cash", 0))
    inception = min(h["first_bought"] for h in holdings)

    # Determine valuation date: latest close common to KSE100 (always present) unless --asof.
    kse_bars = load_ohlc("KSE100")
    if not kse_bars:
        print("ERROR: KSE100 OHLC missing — cannot compute baselines.")
        sys.exit(1)
    asof = args.asof or kse_bars[-1]["date"]

    warnings: list[str] = []

    # --- BOOK (actual): current MTM = cash_now + sum(qty * close_asof) ---
    book_mtm = cash_now
    for h in holdings:
        d, c = close_on_or_before(h["ticker"], asof)
        if c is None:
            warnings.append(f"no price for {h['ticker']} at/<= {asof}; excluded from BOOK MTM")
            continue
        book_mtm += h["qty"] * c
    book_ret = book_mtm / starting_cash - 1

    # --- HOLD-DAY-1: same shares, held; value = cash leftover at inception + qty*close_asof ---
    # Reconstruct inception cost to get the day-1 leftover cash.
    invested_cost = sum(h["qty"] * h["avg_cost"] for h in holdings)
    day1_leftover_cash = starting_cash - invested_cost
    hold_mtm = day1_leftover_cash
    for h in holdings:
        d, c = close_on_or_before(h["ticker"], asof)
        if c is not None:
            hold_mtm += h["qty"] * c
    hold_ret = hold_mtm / starting_cash - 1

    # --- KSE-100: starting_cash into the index at inception, valued at asof ---
    _, kse0 = close_on_or_before("KSE100", inception)
    _, kse1 = close_on_or_before("KSE100", asof)
    kse_ret = (kse1 / kse0 - 1) if (kse0 and kse1) else None

    # --- EQUAL-WEIGHT: starting_cash / N across inception tickers at their inception close ---
    n = len(holdings)
    per_name = starting_cash / n
    ew_mtm = 0.0
    ew_ok = True
    for h in holdings:
        _, c0 = close_on_or_before(h["ticker"], inception)
        _, c1 = close_on_or_before(h["ticker"], asof)
        if not c0 or not c1:
            warnings.append(f"equal-weight: missing inception/asof price for {h['ticker']}")
            ew_ok = False
            continue
        ew_mtm += per_name * (c1 / c0)
    ew_ret = (ew_mtm / starting_cash - 1) if ew_ok else None

    rows = [
        ("ALL-CASH (no investing)", 0.0),
        ("KSE-100 (index)", kse_ret),
        ("EQUAL-WEIGHT day-1 names", ew_ret),
        ("HOLD-DAY-1 (untouched)", hold_ret),
        ("BOOK (actual paper)", book_ret),
    ]

    result = {
        "asof": asof,
        "inception": inception,
        "starting_cash": starting_cash,
        "book_mtm": round(book_mtm, 2),
        "baselines": {name: (round(r * 100, 2) if r is not None else None) for name, r in rows},
        "book_vs_kse_pp": round((book_ret - kse_ret) * 100, 2) if kse_ret is not None else None,
        "book_vs_hold_pp": round((book_ret - hold_ret) * 100, 2),
        "book_vs_equalweight_pp": round((book_ret - ew_ret) * 100, 2) if ew_ret is not None else None,
        "warnings": warnings,
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"\nCounterfactual baselines  (inception {inception} → asof {asof})")
    print("=" * 60)
    print(f"{'BASELINE':<30} {'RETURN':>10}")
    print("-" * 60)
    for name, r in rows:
        val = f"{r*100:+.2f}%" if r is not None else "n/a"
        print(f"{name:<30} {val:>10}")
    print("=" * 60)
    if kse_ret is not None:
        verdict = "BEATS" if book_ret > kse_ret else "LAGS"
        print(f"  BOOK vs KSE-100      : {(book_ret-kse_ret)*100:+.2f}pp  ({verdict} the index)")
    print(f"  BOOK vs HOLD-DAY-1   : {(book_ret-hold_ret)*100:+.2f}pp  (value of post-day-1 activity)")
    if ew_ret is not None:
        print(f"  BOOK vs EQUAL-WEIGHT : {(book_ret-ew_ret)*100:+.2f}pp  (value of sizing skill)")
    if warnings:
        print("\n  ⚠ warnings:")
        for w in warnings:
            print(f"     {w}")
    print("\nPaper research only. Not financial advice.")


if __name__ == "__main__":
    main()
