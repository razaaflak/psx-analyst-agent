"""
OHLC back-adjuster — makes every series CONTINUOUS across splits/bonuses so that
MA/RSI/ATR/backtest read correct values across a corporate-action date.

THE PROBLEM IT FIXES
  data/ohlc/{SYM}.json is RAW from PSX (unadjusted). A 2:1 split halves the close
  overnight. Any MA200 / RSI14 / ATR / backtest window that spans the split date is
  computed across a 50% price cliff and is WRONG. detect_corporate_actions.py finds
  the cliffs; THIS script removes their effect.

HOW (standard back-adjustment)
  Back-adjust = scale every bar BEFORE an event by the cumulative event ratio, so the
  series is continuous and its right edge equals today's REAL traded price. For an
  event on date D with ratio r = close_before / close_after (e.g. ~2.0 for a 2:1 split,
  ~8.5 for a large bonus), every bar with date < D is divided by r. With multiple events
  the factors compound (a bar before two splits is divided by r1*r2).

  Ratio is derived EMPIRICALLY (close_before / close_after) — this handles clean splits
  AND messy bonus ratios uniformly, and matches what actually happened in the tape rather
  than guessing a "clean" fraction.

NON-DESTRUCTIVE
  Raw open/high/low/close/volume are PRESERVED untouched. Adjusted values are written to
  NEW fields: adj_open / adj_high / adj_low / adj_close (and adj_factor on each bar, the
  cumulative multiplier applied). Volume is NOT adjusted (we keep raw traded volume; a
  'split_adjusted_volume' could be added later if needed, but raw volume is what liquidity
  filters want). Consumers read `adj_close or close` — so an un-adjusted store still works.

SOURCE OF EVENTS
  data/corporate_actions.json (from detect_corporate_actions.py). Only events with
  confirmed=true are applied by default (use --include-unconfirmed to apply all). The
  empirical ratio is recomputed from the bars at apply time and stored back on the event
  as 'applied_ratio' for the audit trail.

Usage:
  python scripts/adjust_ohlc.py --confirm-all      # mark every detected event confirmed (with empirical ratio), then adjust
  python scripts/adjust_ohlc.py                    # adjust using confirmed events only
  python scripts/adjust_ohlc.py --include-unconfirmed
  python scripts/adjust_ohlc.py --symbols UBL,LUCK # adjust just these
  python scripts/adjust_ohlc.py --verify           # after adjusting, check no residual >30% adj_close cliff remains

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
EVENTS_PATH = DATA / "corporate_actions.json"

RESIDUAL_CLIFF = 0.30  # for --verify: an adj_close gap beyond this (unexplained) is a failure


# --------------------------------------------------------------------------- #
# IO
# --------------------------------------------------------------------------- #

def load_bars(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, list):
        return []
    return sorted([b for b in data if b.get("date")], key=lambda b: b["date"])


def save_bars(path: Path, bars: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(bars, key=lambda b: b["date"]), f, indent=1)


def load_events() -> dict:
    if not EVENTS_PATH.exists():
        print(f"ERROR: {EVENTS_PATH} not found — run detect_corporate_actions.py first.")
        sys.exit(1)
    with open(EVENTS_PATH, "r", encoding="utf-8") as f:
        blob = json.load(f)
    return blob


def save_events(blob: dict) -> None:
    with open(EVENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(blob, f, indent=2)


# --------------------------------------------------------------------------- #
# Empirical ratio + adjustment
# --------------------------------------------------------------------------- #

def empirical_ratio(bars: list[dict], event_date: str) -> float | None:
    """ratio = close on the last bar BEFORE event_date / close ON event_date.
    >1 for a split/bonus (price drops), <1 for a reverse split (price rises)."""
    before = [b for b in bars if b["date"] < event_date and b.get("close")]
    on = [b for b in bars if b["date"] == event_date and b.get("close")]
    if not before or not on:
        return None
    c_before = before[-1]["close"]
    c_on = on[0]["close"]
    if not c_on or c_on <= 0:
        return None
    return c_before / c_on


def adjust_symbol(sym: str, events: list[dict], include_unconfirmed: bool) -> tuple[bool, str]:
    """Apply back-adjustment to one symbol's file. Returns (changed, message)."""
    path = OHLC_DIR / f"{sym}.json"
    if not path.exists():
        return False, f"{sym}: no file"
    bars = load_bars(path)
    if not bars:
        return False, f"{sym}: empty"

    sym_events = [e for e in events if e["symbol"] == sym
                  and (include_unconfirmed or e.get("confirmed"))]
    sym_events.sort(key=lambda e: e["date"])

    # Build per-event ratio (recompute empirically from current bars for accuracy).
    applied = []
    for ev in sym_events:
        r = empirical_ratio(bars, ev["date"])
        if r is None or abs(r - 1.0) < 0.05:
            continue  # nothing meaningful to adjust
        ev["applied_ratio"] = round(r, 6)
        applied.append((ev["date"], r))

    # Compute cumulative adjustment factor for each bar:
    # a bar on date d is divided by the product of ratios of all events with date > d
    # (events strictly AFTER the bar — those are the splits the bar hasn't experienced yet).
    for b in bars:
        factor = 1.0
        for (edate, r) in applied:
            if b["date"] < edate:
                factor *= r
        b["adj_factor"] = round(factor, 8)
        for src, dst in (("open", "adj_open"), ("high", "adj_high"),
                         ("low", "adj_low"), ("close", "adj_close")):
            v = b.get(src)
            b[dst] = round(v / factor, 4) if (v is not None) else None

    save_bars(path, bars)
    if applied:
        ev_str = ", ".join(f"{d}(÷{r:.3f})" for d, r in applied)
        return True, f"{sym}: adjusted across {len(applied)} event(s) — {ev_str}"
    return True, f"{sym}: no events — adj_* = raw (factor 1.0)"


# --------------------------------------------------------------------------- #
# Verify
# --------------------------------------------------------------------------- #

def verify_symbol(sym: str, events: list[dict]) -> list[str]:
    """Check no residual unexplained cliff > RESIDUAL_CLIFF remains in adj_close."""
    path = OHLC_DIR / f"{sym}.json"
    bars = load_bars(path)
    bad = []
    ev_dates = {e["date"] for e in events if e["symbol"] == sym}
    prev = None
    for b in bars:
        c = b.get("adj_close", b.get("close"))
        if prev is not None and prev > 0 and c:
            gap = c / prev - 1
            if abs(gap) > RESIDUAL_CLIFF and b["date"] not in ev_dates:
                bad.append(f"{sym} {b['date']}: residual adj_close gap {gap*100:+.1f}% (unexplained)")
        prev = c
    return bad


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> None:
    ap = argparse.ArgumentParser(description="Back-adjust the OHLC store for splits/bonuses.")
    ap.add_argument("--symbols", type=str, default=None, help="Comma-separated tickers (default: all with events)")
    ap.add_argument("--confirm-all", action="store_true",
                    help="Mark every detected event confirmed (with empirical ratio) before adjusting")
    ap.add_argument("--include-unconfirmed", action="store_true",
                    help="Apply unconfirmed events too (default: confirmed only)")
    ap.add_argument("--verify", action="store_true", help="After adjusting, assert no residual cliffs remain")
    args = ap.parse_args()

    blob = load_events()
    events = blob.get("events", [])

    # --confirm-all: stamp empirical ratio + confirmed=true on each event
    if args.confirm_all:
        for ev in events:
            path = OHLC_DIR / f"{ev['symbol']}.json"
            if path.exists():
                r = empirical_ratio(load_bars(path), ev["date"])
                if r is not None:
                    ev["applied_ratio"] = round(r, 6)
            ev["confirmed"] = True
            ev["note"] = "confirmed via empirical ratio (close_before/close_after); back-adjustment applied"
        save_events(blob)
        print(f"[confirm-all] marked {len(events)} event(s) confirmed with empirical ratios.")

    include_unconf = args.include_unconfirmed or args.confirm_all

    # Which symbols to process: explicit list, else every symbol that has an event,
    # plus we still write adj_* for all store files so consumers can rely on the field.
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        symbols = sorted({p.stem for p in OHLC_DIR.glob("*.json")})

    print(f"\n[adjust] processing {len(symbols)} symbol(s) "
          f"({'incl. unconfirmed' if include_unconf else 'confirmed events only'})\n")
    changed = 0
    for sym in symbols:
        ok, msg = adjust_symbol(sym, events, include_unconf)
        if ok:
            changed += 1
            # only print symbols that actually had events, to keep output readable
            if "across" in msg:
                print(f"  {msg}")
    print(f"\n[adjust] wrote adj_* fields to {changed} file(s).")

    if args.verify:
        print("\n[verify] checking for residual unexplained cliffs in adj_close…")
        all_bad: list[str] = []
        for sym in symbols:
            all_bad.extend(verify_symbol(sym, events))
        if all_bad:
            print("  ⚠ RESIDUAL CLIFFS FOUND (a corporate action may be undetected):")
            for line in all_bad:
                print(f"     {line}")
            print("\n  GATE: FAIL")
            sys.exit(1)
        print("  No residual cliffs > 30%. Series are continuous.")
        print("  GATE: PASS")


if __name__ == "__main__":
    main()
