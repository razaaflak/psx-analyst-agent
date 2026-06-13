"""
PSX Corporate-Action Detector — guards the raw OHLC store against split/bonus poisoning.

WHY THIS EXISTS
  data/ohlc/*.json holds RAW, UNADJUSTED candles straight from dps.psx.com.pk/historical.
  PSX does NOT back-adjust for splits / bonus issues / rights. So when a stock does a
  2:1 split (e.g. MTL Rs10->Rs5, June 2026; UBL Rs10->Rs5, June 2025) the close halves
  overnight. To every downstream consumer — MA50/MA200, RSI14, ATR, candlestick logic,
  and backtest.py's return calc — that looks like a -50% crash. That silently poisons
  the one quantitative layer the agent actually leans on, AND it produced the real
  R-EXP-002 face-value bug already.

WHAT THIS DOES (detection only — never mutates the OHLC files)
  For each symbol, scan consecutive trading bars for a close-to-close gap whose size is
  too large to be ordinary price action AND is not matched by a similar move in KSE100
  on the same day. PSX has a ~7.5% daily circuit breaker, so any *idiosyncratic*
  overnight move beyond a threshold is almost always a corporate action, not trading.
  Suspected events are written to data/corporate_actions.json as an audit/warning file
  the daily pipeline reads at Step 1.

  Classification heuristic (close_today / close_prev = ratio):
    ratio ~ 0.50  -> likely 2:1 split or 100% bonus
    ratio ~ 0.33  -> likely 3:1 split / 200% bonus
    ratio ~ 0.25  -> likely 4:1
    ratio ~ 0.67  -> likely 3:2
    else (large but not a clean ratio) -> "review" (could be rights, partial, or data error)

  This is a HEURISTIC. It flags candidates for human/agent verification against filings;
  it does not assert a confirmed action. Confirmed actions should be recorded with the
  'confirmed' flag (set by the agent after checking PSX announcements).

Usage:
  python scripts/detect_corporate_actions.py                 # scan all data/ohlc/*.json
  python scripts/detect_corporate_actions.py --symbols UBL,MTL
  python scripts/detect_corporate_actions.py --since 2026-01-01
  python scripts/detect_corporate_actions.py --threshold 0.30   # min |gap| to flag (default 0.30)

Output: data/corporate_actions.json  (list of suspected/confirmed events, date-ascending)
Exit code: 0 always (advisory tool). Prints a table; warns if any NEW unconfirmed event found.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_OHLC_DIR = REPO_ROOT / "data" / "ohlc"
EVENTS_PATH = REPO_ROOT / "data" / "corporate_actions.json"

# A single-name overnight close-to-close move beyond this fraction is treated as a
# candidate corporate action (PSX daily circuit limit is ~7.5%, so 30% is far outside
# any legitimate trading move and gives margin for gappy thin names).
DEFAULT_THRESHOLD = 0.30

# How closely the same-day index move must track the stock move for us to call it
# "market move, not corporate action". If the stock dropped 50% but KSE100 was flat,
# it's a split. If both fell together, it's a market event (don't flag).
INDEX_EXPLAINS_FRACTION = 0.5  # index move must be at least 50% of the stock move to excuse it

# Clean split/bonus ratios to match against (close_today / close_prev).
KNOWN_RATIOS = {
    0.500: "2:1 split or 100% bonus",
    0.333: "3:1 split or 200% bonus",
    0.250: "4:1 split or 300% bonus",
    0.667: "3:2 split or 50% bonus",
    0.800: "5:4 split or 25% bonus",
    0.909: "11:10 or 10% bonus",
    2.000: "1:2 reverse split / consolidation",
}
RATIO_TOLERANCE = 0.03  # +/- around a clean ratio


def load_bars(path: Path) -> list[dict]:
    """Load a symbol's OHLC list, tolerating the legacy wrapper formats."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    if isinstance(data, str):
        data = json.loads(data)
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
    if not isinstance(data, list):
        return []
    return [b for b in data if b.get("date") and b.get("close") is not None]


def load_index_changes() -> dict[str, float]:
    """Return {date: close} for KSE100 so we can compute its daily move."""
    path = DATA_OHLC_DIR / "KSE100.json"
    if not path.exists():
        return {}
    bars = load_bars(path)
    return {b["date"]: b["close"] for b in bars}


def classify(ratio: float) -> str:
    for clean, label in KNOWN_RATIOS.items():
        if abs(ratio - clean) <= RATIO_TOLERANCE:
            return label
    return "review (non-clean ratio — possible rights / partial / data error)"


def scan_symbol(symbol: str, bars: list[dict], index_close: dict[str, float],
                threshold: float, since: str | None) -> list[dict]:
    """Return suspected corporate-action events for one symbol."""
    bars = sorted(bars, key=lambda b: b["date"])
    events: list[dict] = []
    for prev, cur in zip(bars, bars[1:]):
        if since and cur["date"] < since:
            continue
        c_prev, c_cur = prev["close"], cur["close"]
        if not c_prev or c_prev <= 0:
            continue
        ratio = c_cur / c_prev
        gap = ratio - 1.0  # signed fractional move
        if abs(gap) < threshold:
            continue

        # Was this explained by the broad market? Compute same-day index move.
        idx_excused = False
        idx_move = None
        if cur["date"] in index_close and prev["date"] in index_close:
            ip, ic = index_close[prev["date"]], index_close[cur["date"]]
            if ip and ip > 0:
                idx_move = ic / ip - 1.0
                # same direction and index move is a big fraction of the stock move
                if (idx_move * gap > 0) and abs(idx_move) >= INDEX_EXPLAINS_FRACTION * abs(gap):
                    idx_excused = True

        if idx_excused:
            continue  # market-wide move, not a corporate action

        events.append({
            "symbol": symbol,
            "date": cur["date"],
            "prev_date": prev["date"],
            "prev_close": round(c_prev, 4),
            "close": round(c_cur, 4),
            "ratio": round(ratio, 4),
            "gap_pct": round(gap * 100, 2),
            "index_move_pct": round(idx_move * 100, 2) if idx_move is not None else None,
            "likely": classify(ratio),
            "confirmed": False,
            "note": "auto-detected; verify against PSX announcements before adjusting any analysis",
        })
    return events


def load_existing_events() -> list[dict]:
    if not EVENTS_PATH.exists():
        return []
    with open(EVENTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("events", []) if isinstance(data, dict) else data


def merge_events(existing: list[dict], found: list[dict]) -> tuple[list[dict], list[dict]]:
    """Merge by (symbol,date) key. Preserve 'confirmed'/note from existing. Return (all, new)."""
    by_key = {(e["symbol"], e["date"]): e for e in existing}
    new_events = []
    for ev in found:
        key = (ev["symbol"], ev["date"])
        if key in by_key:
            # keep the human-curated fields, refresh the computed ones
            prior = by_key[key]
            ev["confirmed"] = prior.get("confirmed", False)
            if prior.get("confirmed"):
                ev["note"] = prior.get("note", ev["note"])
        else:
            new_events.append(ev)
        by_key[key] = ev
    merged = sorted(by_key.values(), key=lambda e: (e["date"], e["symbol"]))
    return merged, new_events


def main() -> None:
    ap = argparse.ArgumentParser(description="Detect suspected splits/bonuses in the raw OHLC store.")
    ap.add_argument("--symbols", type=str, default=None,
                    help="Comma-separated tickers (default: all data/ohlc/*.json)")
    ap.add_argument("--since", type=str, default=None,
                    help="Only flag events on/after this date (YYYY-MM-DD)")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help=f"Min |close-to-close gap| to flag (default {DEFAULT_THRESHOLD})")
    ap.add_argument("--quiet", action="store_true", help="Suppress the per-event table")
    args = ap.parse_args()

    if args.since:
        try:
            datetime.strptime(args.since, "%Y-%m-%d")
        except ValueError:
            print(f"ERROR: --since must be YYYY-MM-DD, got {args.since!r}")
            sys.exit(2)

    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        paths = [DATA_OHLC_DIR / f"{s}.json" for s in symbols]
    else:
        paths = sorted(DATA_OHLC_DIR.glob("*.json"))

    index_close = load_index_changes()

    found: list[dict] = []
    for path in paths:
        if not path.exists():
            print(f"  [skip] {path.name} not found")
            continue
        sym = path.stem
        if sym == "KSE100":
            continue  # index itself is the reference, don't self-flag
        bars = load_bars(path)
        found.extend(scan_symbol(sym, bars, index_close, args.threshold, args.since))

    existing = load_existing_events()
    merged, new_events = merge_events(existing, found)

    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EVENTS_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "_comment": ("Suspected corporate actions (splits/bonuses/rights) auto-detected in "
                         "the RAW unadjusted OHLC store. Detection-only: this file is a WARNING / "
                         "audit trail, not an adjustment. Verify each against PSX announcements and "
                         "set confirmed=true once checked. Downstream TA/backtest treats raw bars; "
                         "use this list to know which series have an unadjusted discontinuity."),
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "threshold": args.threshold,
            "events": merged,
        }, f, indent=2)

    if not args.quiet:
        print("\n" + "=" * 84)
        print(f"{'SYMBOL':<8} {'DATE':<12} {'PREV->NOW':<20} {'GAP%':>8} {'IDX%':>7}  LIKELY")
        print("-" * 84)
        for ev in merged:
            pc = f"{ev['prev_close']}->{ev['close']}"
            idx = f"{ev['index_move_pct']}" if ev["index_move_pct"] is not None else "-"
            star = " " if ev["confirmed"] else "*"
            print(f"{ev['symbol']:<8} {ev['date']:<12} {pc:<20} {ev['gap_pct']:>8} {idx:>7}  {star}{ev['likely']}")
        print("=" * 84)
        print("  * = unconfirmed (verify vs PSX filings)")

    print(f"\n[corporate-actions] {len(merged)} total suspected event(s); "
          f"{len(new_events)} NEW this scan. Written to {EVENTS_PATH.relative_to(REPO_ROOT)}")
    if new_events:
        print("  ⚠ NEW unconfirmed corporate-action candidate(s) — verify before trusting "
              "MA/RSI/ATR/backtest on these series:")
        for ev in new_events:
            print(f"     {ev['symbol']} {ev['date']}  {ev['likely']}  (gap {ev['gap_pct']}%)")


if __name__ == "__main__":
    main()
