"""
Deterministic prediction grader — hardens the one number the whole readiness gate
depends on (the live hit-rate) against lenient self-grading.

WHY THIS EXISTS
  Grades in predictions_log.csv are currently written in free text by the same agent
  that issued the call. With no mechanical check, hit-rate can silently drift via
  generous self-grading. This script reads the RAW price record (data/ohlc/*.json,
  the source of truth) and computes a mechanical HIT / MISS / PARTIAL for the
  machine-checkable prediction types, with NO look-ahead (only bars strictly AFTER
  issue_date, up to grade_on_date).

WHAT IT DOES NOT DO
  - It NEVER writes to predictions_log.csv. The CSV is append-only and grading is the
    agent's call; this tool only *proposes* a grade + the evidence string so the agent
    can confirm or override (and record a reasoned disagreement). Determinism is a
    check on the human grade, not a replacement for judgment.
  - It does not invent prices. If a needed bar is missing it returns NEEDS-DATA, not a guess.

SUPPORTED PREDICTION TYPES (parsed from prediction_text where structured)
  direction          : "closes higher than X" / "closes above L" / "outperforms KSE-100"
  magnitude          : "does not break below L" / "holds above L" / "stays within A-B"
  conditional        : "if <index cond> then <stock move>"  (best-effort; falls back to NEEDS-REVIEW)
  decision_quality   : "will be in profit (above entry E)" / "outperform cash/benchmark"
  outperformance     : stock vs KSE-100 cumulative over window

  Anything it can't parse confidently -> NEEDS-REVIEW (the agent grades by hand).

Usage:
  python scripts/grade_predictions.py                     # grade all matured open rows as of today
  python scripts/grade_predictions.py --asof 2026-06-16   # grade as of a specific date
  python scripts/grade_predictions.py --id P-001          # one prediction
  python scripts/grade_predictions.py --all               # include not-yet-matured (preview only)

Output: a proposal table the agent reviews before writing grades to the CSV.
"""

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"
OHLC_DIR = DATA / "ohlc"
PRED_CSV = DATA / "predictions_log.csv"

# Index symbols the parser recognises for "outperforms the index" phrasing.
INDEX_TOKENS = ("KSE-100", "KSE100", "INDEX")


# --------------------------------------------------------------------------- #
# Price access (raw OHLC store = source of truth)
# --------------------------------------------------------------------------- #

_ohlc_cache: dict[str, list[dict]] = {}


def load_ohlc(symbol: str) -> list[dict]:
    sym = symbol.upper()
    if sym in _ohlc_cache:
        return _ohlc_cache[sym]
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
    _ohlc_cache[sym] = bars
    return bars


def has_split_after(symbol: str, after: str) -> bool:
    """True if a confirmed corporate action falls on/after `after` for this symbol.
    When true, return-based grades over that window must use adj_close; level-based
    grades (literal price targets stated in raw terms at issue) keep raw close."""
    try:
        blob = json.loads((DATA / "corporate_actions.json").read_text(encoding="utf-8"))
        return any(e["symbol"] == symbol.upper() and e["date"] > after and e.get("confirmed")
                   for e in blob.get("events", []))
    except Exception:
        return False


def bars_in_window(symbol: str, after: str, through: str) -> list[dict]:
    """Bars strictly AFTER issue_date, up to and including grade_on_date. No look-ahead."""
    return [b for b in load_ohlc(symbol) if after < b["date"] <= through]


def ret_close(bar: dict, use_adj: bool) -> float:
    """Close to use for RETURN math: adj_close when a split is in the prediction window,
    else raw close. Level comparisons always use raw close (targets are stated in raw terms)."""
    if use_adj and bar.get("adj_close") is not None:
        return bar["adj_close"]
    return bar["close"]


def close_on_or_before(symbol: str, d: str, use_adj: bool = False) -> float | None:
    """Last close on or before date d (for the issue-day reference close).
    use_adj=True returns adj_close (for return math across a split window)."""
    prior = [b for b in load_ohlc(symbol) if b["date"] <= d]
    if not prior:
        return None
    return ret_close(prior[-1], use_adj)


# --------------------------------------------------------------------------- #
# Number / level extraction
# --------------------------------------------------------------------------- #

def _nums(text: str) -> list[float]:
    return [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*\.?\d*", text)]


def _first_level_after(text: str, *keywords: str) -> float | None:
    """First number that appears after any of the keyword phrases."""
    low = text.lower()
    for kw in keywords:
        i = low.find(kw)
        if i >= 0:
            m = re.search(r"(\d[\d,]*\.?\d*)", text[i:])
            if m:
                return float(m.group(1).replace(",", ""))
    return None


# --------------------------------------------------------------------------- #
# Graders by type — each returns (grade, evidence) or (None, reason)
# --------------------------------------------------------------------------- #

def grade_outperformance(sym: str, idx: str, issue: str, grade_on: str) -> tuple[str | None, str]:
    sbars = bars_in_window(sym, issue, grade_on)
    ibars = bars_in_window(idx, issue, grade_on)
    if not sbars or not ibars:
        return None, "NEEDS-DATA (missing stock or index bars in window)"
    # return math must be split-adjusted if a corporate action falls in the window
    s_adj, i_adj = has_split_after(sym, issue), has_split_after(idx, issue)
    s0 = close_on_or_before(sym, issue, use_adj=s_adj)
    i0 = close_on_or_before(idx, issue, use_adj=i_adj)
    if not s0 or not i0:
        return None, "NEEDS-DATA (missing issue-day reference close)"
    s_ret = ret_close(sbars[-1], s_adj) / s0 - 1
    i_ret = ret_close(ibars[-1], i_adj) / i0 - 1
    gap = (s_ret - i_ret) * 100
    g = "HIT" if s_ret > i_ret else "MISS"
    return g, (f"{sym} cum {s_ret*100:+.2f}% vs index {i_ret*100:+.2f}% "
               f"over {sbars[0]['date']}..{sbars[-1]['date']} (gap {gap:+.2f}pp)")


def grade_above_level(sym: str, level: float, issue: str, grade_on: str,
                      mode: str) -> tuple[str | None, str]:
    """mode='close_above_once': HIT if any close > level in window.
       mode='hold_above':       HIT if no close < level (support holds).
       mode='no_break_below':   same as hold_above (does not break below)."""
    bars = bars_in_window(sym, issue, grade_on)
    if not bars:
        return None, "NEEDS-DATA (no bars in window)"
    closes = [(b["date"], b["close"]) for b in bars]
    if mode == "close_above_once":
        hits = [c for c in closes if c[1] > level]
        if hits:
            return "HIT", f"{sym} closed > {level} on {hits[0][0]} ({hits[0][1]})"
        hi = max(closes, key=lambda c: c[1])
        return "MISS", f"{sym} never closed > {level}; high close {hi[1]} on {hi[0]}"
    else:  # hold_above / no_break_below
        breaks = [c for c in closes if c[1] < level]
        if breaks:
            return "MISS", f"{sym} broke < {level} on {breaks[0][0]} ({breaks[0][1]})"
        lo = min(closes, key=lambda c: c[1])
        return "HIT", f"{sym} held >= {level} all {len(closes)} sessions; low close {lo[1]} on {lo[0]}"


def grade_below_level(sym: str, level: float, issue: str, grade_on: str) -> tuple[str | None, str]:
    """'does not close below L' style — HIT if every close >= L."""
    return grade_above_level(sym, level, issue, grade_on, mode="no_break_below")


def grade_range(sym: str, lo: float, hi: float, issue: str, grade_on: str) -> tuple[str | None, str]:
    bars = bars_in_window(sym, issue, grade_on)
    if not bars:
        return None, "NEEDS-DATA (no bars in window)"
    out = [(b["date"], b["close"]) for b in bars if b["close"] < lo or b["close"] > hi]
    if out:
        return "MISS", f"{sym} left [{lo},{hi}] on {out[0][0]} ({out[0][1]})"
    return "HIT", f"{sym} stayed within [{lo},{hi}] for all {len(bars)} sessions"


def grade_higher_than_ref(sym: str, ref: float, issue: str, grade_on: str) -> tuple[str | None, str]:
    """'closes higher than today's close (ref) over next N sessions' — HIT if final close > ref."""
    bars = bars_in_window(sym, issue, grade_on)
    if not bars:
        return None, "NEEDS-DATA (no bars in window)"
    final = bars[-1]
    g = "HIT" if final["close"] > ref else "MISS"
    return g, f"{sym} final close {final['close']} on {final['date']} vs ref {ref}"


def grade_decision_quality(sym: str, entry: float, issue: str, grade_on: str) -> tuple[str | None, str]:
    """'will be in profit (above entry E) when graded' — HIT if final close > entry."""
    bars = bars_in_window(sym, issue, grade_on)
    if not bars:
        return None, "NEEDS-DATA (no bars in window)"
    final = bars[-1]
    g = "HIT" if final["close"] > entry else "MISS"
    return g, f"{sym} final close {final['close']} on {final['date']} vs paper entry {entry}"


# --------------------------------------------------------------------------- #
# Dispatch — parse the text to choose a grader
# --------------------------------------------------------------------------- #

def propose_grade(row: dict) -> tuple[str | None, str]:
    text = row["prediction_text"]
    low = text.lower()
    sym = row["ticker_or_index"].upper()
    issue = row["issue_date"]
    grade_on = row["grade_on_date"]
    ptype = row["type"].strip()

    # If a split/bonus falls inside this prediction's window, any literal price LEVEL in
    # the text (target/stop/entry) was stated in pre-split terms but the closes after the
    # event are post-split — a level-vs-close comparison would be wrong. Return-based
    # grades (outperformance below) are split-adjusted and safe; everything else bails to
    # NEEDS-REVIEW so the agent rescales the level by hand.
    split_in_window = has_split_after(sym, issue) and not (
        "outperform" in low or "underperform" in low)
    if split_in_window:
        return None, ("NEEDS-REVIEW (corporate action inside window — literal price level is "
                      "pre-split; rescale by the event ratio in data/corporate_actions.json)")

    # Outperformance / vs-index (covers many 'direction' rows too)
    if "outperform" in low or "underperform" in low or any(t.lower() in low for t in INDEX_TOKENS) and ("vs" in low or "than kse" in low or "higher % change" in low):
        # which side is the index? if the stock IS the index, skip
        if sym in ("KSE100", "KSE-100"):
            return None, "NEEDS-REVIEW (index-conditional — grade by hand, see Q2b)"
        underperf = "underperform" in low
        g, ev = grade_outperformance(sym, "KSE100", issue, grade_on)
        if g and underperf:
            g = "MISS" if g == "HIT" else "HIT"  # invert: predicted underperformance
            ev = "predicted UNDERPERFORM — " + ev
        if g:
            return g, ev

    # decision_quality: "in profit (above entry E)"
    if ptype == "decision_quality" or "in profit" in low:
        entry = _first_level_after(text, "entry", "above paper entry", "above entry")
        if entry is None:
            n = _nums(text)
            entry = n[0] if n else None
        if entry is not None:
            return grade_decision_quality(sym, entry, issue, grade_on)

    # range: "within A-B" / "between A and B"
    m = re.search(r"(\d[\d,]*\.?\d*)\s*[–\-to]+\s*(\d[\d,]*\.?\d*)\s*range", low)
    if "within" in low and m:
        lo, hi = float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))
        return grade_range(sym, lo, hi, issue, grade_on)

    # "does not break below L" / "does not close below L"
    if "below" in low and ("not break" in low or "not close below" in low or "does not" in low):
        lvl = _first_level_after(text, "below")
        if lvl is not None:
            return grade_below_level(sym, lvl, issue, grade_on)

    # "holds above L" / "closes above L at least once"
    if "above" in low:
        lvl = _first_level_after(text, "above")
        if lvl is not None:
            if "at least once" in low or "closes above" in low:
                return grade_above_level(sym, lvl, issue, grade_on, mode="close_above_once")
            if "holds above" in low or "hold above" in low:
                return grade_above_level(sym, lvl, issue, grade_on, mode="hold_above")
            # default for 'above' with no qualifier: did final close exceed it
            return grade_above_level(sym, lvl, issue, grade_on, mode="close_above_once")

    # "closes higher than today's close (ref)"
    if "higher than" in low:
        nums = _nums(text)
        if nums:
            return grade_higher_than_ref(sym, nums[0], issue, grade_on)

    return None, "NEEDS-REVIEW (unrecognised structure — grade by hand)"


# --------------------------------------------------------------------------- #
# CSV read + run
# --------------------------------------------------------------------------- #

def read_predictions() -> list[dict]:
    with open(PRED_CSV, "r", encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.reader(f) if r and not r[0].lstrip().startswith("#")]
    header, data = rows[0], rows[1:]
    out = []
    for r in data:
        r = r + [""] * (len(header) - len(r))
        out.append(dict(zip(header, r)))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Deterministically propose grades for matured predictions.")
    ap.add_argument("--asof", type=str, default=date.today().isoformat(),
                    help="Grade rows whose grade_on_date <= this (default: today)")
    ap.add_argument("--id", type=str, default=None, help="Grade only this prediction_id")
    ap.add_argument("--all", action="store_true", help="Include not-yet-matured rows (preview)")
    args = ap.parse_args()

    rows = read_predictions()
    targets = []
    for r in rows:
        if args.id and r["prediction_id"] != args.id:
            continue
        if r["status"].strip() == "graded" and not args.id:
            continue
        if not args.all and not args.id and r["grade_on_date"] > args.asof:
            continue
        targets.append(r)

    if not targets:
        print(f"No matured open predictions as of {args.asof}. Nothing to propose.")
        return

    print("\n" + "=" * 100)
    print("DETERMINISTIC GRADE PROPOSALS — review each; the agent writes the final grade to the CSV.")
    print("This tool never writes. Confirm or override with a recorded reason (no look-ahead).")
    print("=" * 100)
    agree_needed = 0
    for r in targets:
        g, ev = propose_grade(r)
        existing = r["grade"].strip()
        tag = g if g else "—"
        line = f"\n[{r['prediction_id']}] {r['ticker_or_index']} ({r['type']}, conv {r['conviction']})"
        print(line)
        print(f"  text : {r['prediction_text'][:110]}{'…' if len(r['prediction_text'])>110 else ''}")
        print(f"  proposed grade : {tag}")
        print(f"  evidence       : {ev}")
        if existing:
            match = "✓ matches existing" if existing == g else f"⚠ DIFFERS from existing CSV grade '{existing}'"
            print(f"  existing grade : {existing}  [{match}]")
        if g is None:
            agree_needed += 1

    print("\n" + "-" * 100)
    print(f"{len(targets)} matured row(s). {agree_needed} need manual grading (NEEDS-DATA/REVIEW).")
    print("To record: append the grade columns in data/predictions_log.csv, then rebuild psx.db.")


if __name__ == "__main__":
    main()
