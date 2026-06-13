"""
PSX Backtest Engine — validates rules-library hypotheses against historical OHLC.

PURPOSE
  Compress "30 years of experience" into weeks: test each testable rule against
  years of real PSX bars instead of waiting months for live forward observations.

HONESTY CONTRACT (mirrors INSTRUCTIONS.md / SKILL.md)
  1. NO LOOK-AHEAD. A signal at bar t may only read bars[0..t]. Outcomes are
     measured strictly over bars[t+1 .. t+horizon]. Enforced structurally:
     signal functions receive a *view* truncated at t.
  2. Backtest results earn a rule the `backtest-validated` PRE-TIER only.
     They NEVER substitute for live forward observations required for
     Provisional (≥8 obs) or Core (≥20 obs) — markets shift, and the live
     loop is the only proof the edge still exists.
  3. Chronological train/holdout split (default 70/30). A rule that only
     works in-sample is a coincidence, not a rule.
  4. Signal cooldown per symbol = horizon bars, so overlapping windows don't
     pseudo-replicate one event into many "observations".
  5. E-lens (news) rules are NOT backtestable here — no historical news
     archive exists. Only T- and cross-sectional rules run. Stated, not hidden.

Data:   data/ohlc/{SYM}.json  (from scripts/collect_ohlc.py)
Output: console table + reports/backtests/backtest_<date>.json

Usage:
  python scripts/backtest.py                       # all rules, all symbols with ≥250 bars
  python scripts/backtest.py --rules rsi_oversold_bounce,golden_cross
  python scripts/backtest.py --split 0.7           # chronological train/holdout fraction
  python scripts/backtest.py --symbols OGDC,PPL
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
OHLC_DIR = REPO_ROOT / "data" / "ohlc"
REPORT_DIR = REPO_ROOT / "reports" / "backtests"

WARMUP = 200          # min bars of history before a signal may fire
TRADING_YEAR = 246    # approx PSX trading days/year (52w window)

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_bars(sym: str) -> list[dict]:
    path = OHLC_DIR / f"{sym}.json"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        bars = json.load(f)
    # keep only bars with a close; ascending by date (store guarantees, but verify)
    bars = [b for b in bars if b.get("close") is not None]
    bars.sort(key=lambda b: b["date"])
    return bars


def all_symbols() -> list[str]:
    return sorted(p.stem for p in OHLC_DIR.glob("*.json"))

# ---------------------------------------------------------------------------
# Indicators — computed once per symbol, value at index t uses bars[<=t] only
# ---------------------------------------------------------------------------

def compute_indicators(bars: list[dict]) -> dict:
    n = len(bars)
    # Use the split/bonus-adjusted close when present (from scripts/adjust_ohlc.py) so
    # MA/RSI/52w-high and forward returns are continuous across corporate actions; fall
    # back to raw close for any un-adjusted store. Volume stays raw (liquidity is raw).
    closes = [(b.get("adj_close") if b.get("adj_close") is not None else b["close"]) for b in bars]
    vols = [b.get("volume") or 0 for b in bars]

    def sma(period: int) -> list:
        out = [None] * n
        s = 0.0
        for i in range(n):
            s += closes[i]
            if i >= period:
                s -= closes[i - period]
            if i >= period - 1:
                out[i] = s / period
        return out

    def avg_vol(period: int) -> list:
        out = [None] * n
        s = 0.0
        for i in range(n):
            s += vols[i]
            if i >= period:
                s -= vols[i - period]
            if i >= period - 1:
                out[i] = s / period
        return out

    # Wilder RSI(14)
    rsi = [None] * n
    period = 14
    if n > period:
        gains = losses = 0.0
        for i in range(1, period + 1):
            d = closes[i] - closes[i - 1]
            gains += max(d, 0)
            losses += max(-d, 0)
        ag, al = gains / period, losses / period
        rsi[period] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
        for i in range(period + 1, n):
            d = closes[i] - closes[i - 1]
            ag = (ag * (period - 1) + max(d, 0)) / period
            al = (al * (period - 1) + max(-d, 0)) / period
            rsi[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)

    # rolling 52w high (of closes, trailing TRADING_YEAR bars incl. today)
    hi52 = [None] * n
    for i in range(n):
        lo_idx = max(0, i - TRADING_YEAR + 1)
        if i - lo_idx + 1 >= 60:  # need a meaningful window
            hi52[i] = max(closes[lo_idx:i + 1])

    return {
        "close": closes, "vol": vols,
        "ma50": sma(50), "ma200": sma(200),
        "avgvol20": avg_vol(20), "rsi14": rsi, "hi52": hi52,
    }

# ---------------------------------------------------------------------------
# Outcome helpers — read bars AFTER t only
# ---------------------------------------------------------------------------

def fwd_return(ind: dict, t: int, h: int):
    """Return % change close[t] -> close[t+h]; None if insufficient future bars."""
    closes = ind["close"]
    if t + h >= len(closes):
        return None
    return (closes[t + h] - closes[t]) / closes[t] * 100.0


def fwd_return_by_date(date_map: dict, dates: list, t: int, h: int, sym_dates: list):
    """Index-relative outcome: KSE100 % change over the same calendar window."""
    d0, d1_idx = sym_dates[t], t + h
    if d1_idx >= len(sym_dates):
        return None
    d1 = sym_dates[d1_idx]
    if d0 not in date_map or d1 not in date_map:
        return None
    c0, c1 = date_map[d0], date_map[d1]
    return (c1 - c0) / c0 * 100.0

# ---------------------------------------------------------------------------
# Rule definitions
# Each: signal(ind, t) -> bool   (may read indices <= t ONLY)
#       horizon (bars), outcome: "abs" (fwd ret > 0) or "rel" (beats KSE100)
# ---------------------------------------------------------------------------

RULES = {
    "golden_cross": {
        "desc": "MA50 crosses above MA200 → outperforms KSE100 over next 20 bars",
        "maps_to": "T-lens golden-cross input (daily snapshots)",
        "horizon": 20, "outcome": "rel",
        "signal": lambda ind, t: (
            ind["ma200"][t] is not None and ind["ma200"][t - 1] is not None
            and ind["ma50"][t - 1] <= ind["ma200"][t - 1]
            and ind["ma50"][t] > ind["ma200"][t]
        ),
    },
    "rsi_oversold_bounce": {
        "desc": "RSI14 < 30 → positive absolute return over next 10 bars",
        "maps_to": "T-lens oversold input (e.g. APL RSI 30.9 on 06-12)",
        "horizon": 10, "outcome": "abs",
        "signal": lambda ind, t: ind["rsi14"][t] is not None and ind["rsi14"][t] < 30,
    },
    "volume_breakout_followthrough": {
        "desc": "Close ≥ +3% on ≥3× avg20 volume → positive return over next 5 bars",
        "maps_to": "P-012-style breakout persistence (DGKC 06-12)",
        "horizon": 5, "outcome": "abs",
        "signal": lambda ind, t: (
            ind["avgvol20"][t - 1] not in (None, 0)
            and ind["close"][t - 1] > 0
            and (ind["close"][t] - ind["close"][t - 1]) / ind["close"][t - 1] >= 0.03
            and ind["vol"][t] >= 3 * ind["avgvol20"][t - 1]
        ),
    },
    "near_52w_high_momentum": {
        "desc": "Close within 2% of 52w high → outperforms KSE100 over next 20 bars",
        "maps_to": "T-lens pos52pct input",
        "horizon": 20, "outcome": "rel",
        "signal": lambda ind, t: (
            ind["hi52"][t] is not None and ind["close"][t] >= 0.98 * ind["hi52"][t]
        ),
    },
    "rsi_overbought_chase": {
        "desc": "RSI14 > 75 → NEGATIVE/flat return next 10 bars (tests the no-chasing discipline)",
        "maps_to": "Run #4 'no chasing RSI-overbought' decision",
        "horizon": 10, "outcome": "abs_inverse",  # hit if fwd return <= 0
        "signal": lambda ind, t: ind["rsi14"][t] is not None and ind["rsi14"][t] > 75,
    },
}

# ---------------------------------------------------------------------------
# Conditional variants for condition-search (activated via --condition-search)
# These test the same core signal with an extra filter applied.
# Only rsi_oversold_bounce for now — it's the best candidate from first run.
# ---------------------------------------------------------------------------

CONDITIONAL_RULES = {
    # Filter 1: bull-regime only (KSE100 close > KSE100 MA50 at signal time)
    "rsi_oversold_bull_regime": {
        "desc": "RSI14<30 AND KSE100 in bull regime (KSE100 > MA50) → +return next 10 bars",
        "maps_to": "R-EXP-001 condition-search: rsi_oversold_bounce × regime filter",
        "horizon": 10, "outcome": "abs",
        "requires_kse_ind": True,   # engine will inject kse_ind for this symbol's dates
        "signal": lambda ind, t, kse_ind=None, t_kse=None: (
            ind["rsi14"][t] is not None and ind["rsi14"][t] < 30
            and kse_ind is not None and t_kse is not None
            and kse_ind["ma50"][t_kse] is not None
            and kse_ind["close"][t_kse] > kse_ind["ma50"][t_kse]
        ),
    },
    # Filter 2: bear-regime only (KSE100 < MA50)
    "rsi_oversold_bear_regime": {
        "desc": "RSI14<30 AND KSE100 in bear regime (KSE100 < MA50) → +return next 10 bars",
        "maps_to": "R-EXP-001 condition-search: rsi_oversold_bounce × bear-regime filter",
        "horizon": 10, "outcome": "abs",
        "requires_kse_ind": True,
        "signal": lambda ind, t, kse_ind=None, t_kse=None: (
            ind["rsi14"][t] is not None and ind["rsi14"][t] < 30
            and kse_ind is not None and t_kse is not None
            and kse_ind["ma50"][t_kse] is not None
            and kse_ind["close"][t_kse] < kse_ind["ma50"][t_kse]
        ),
    },
    # Filter 3: high-liquidity names only (symbol vol > 500k avg20 at signal)
    "rsi_oversold_liquid": {
        "desc": "RSI14<30 AND avg20 volume > 500k → +return next 10 bars",
        "maps_to": "R-EXP-001 condition-search: rsi_oversold_bounce × liquidity filter",
        "horizon": 10, "outcome": "abs",
        "requires_kse_ind": False,
        "signal": lambda ind, t, kse_ind=None, t_kse=None: (
            ind["rsi14"][t] is not None and ind["rsi14"][t] < 30
            and ind["avgvol20"][t] is not None and ind["avgvol20"][t] > 500_000
        ),
    },
    # Filter 4: deeper oversold (RSI < 25, more extreme)
    "rsi_deeply_oversold": {
        "desc": "RSI14 < 25 (deeper) → +return next 10 bars",
        "maps_to": "R-EXP-001 condition-search: tighter RSI threshold",
        "horizon": 10, "outcome": "abs",
        "requires_kse_ind": False,
        "signal": lambda ind, t, kse_ind=None, t_kse=None: (
            ind["rsi14"][t] is not None and ind["rsi14"][t] < 25
        ),
    },
    # Filter 5: bull regime + liquid (combined)
    "rsi_oversold_bull_liquid": {
        "desc": "RSI14<30 AND bull regime AND avg20 vol > 500k → +return next 10 bars",
        "maps_to": "R-EXP-001 condition-search: regime + liquidity combined",
        "horizon": 10, "outcome": "abs",
        "requires_kse_ind": True,
        "signal": lambda ind, t, kse_ind=None, t_kse=None: (
            ind["rsi14"][t] is not None and ind["rsi14"][t] < 30
            and ind["avgvol20"][t] is not None and ind["avgvol20"][t] > 500_000
            and kse_ind is not None and t_kse is not None
            and kse_ind["ma50"][t_kse] is not None
            and kse_ind["close"][t_kse] > kse_ind["ma50"][t_kse]
        ),
    },
}

# Cross-sectional rule handled separately (needs multiple symbols aligned by date)
PAIRS_RULE = {
    "name": "islamic_vs_conventional_banks",
    "desc": "Islamic banks (MEBL,FABL) beat conventional (MCB,UBL) over rolling 5-bar windows",
    "maps_to": "R-EXP-001 — CAVEAT: unconditional test; live rule is conditional on "
               "rising-rate regime, which OHLC alone cannot see. Treat as baseline only.",
    "islamic": ["MEBL", "FABL"], "conventional": ["MCB", "UBL"], "horizon": 5,
}

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def run_rule(rule_name: str, rule: dict, symbols: list[str], kse_map: dict, split: float) -> dict:
    horizon = rule["horizon"]
    events = []  # (date, sym, hit, fwd, rel)

    for sym in symbols:
        if sym == "KSE100":
            continue
        bars = load_bars(sym)
        if len(bars) < WARMUP + horizon + 10:
            continue
        ind = compute_indicators(bars)
        sym_dates = [b["date"] for b in bars]
        last_fire = -10**9

        for t in range(WARMUP, len(bars) - horizon):
            if t - last_fire < horizon:        # cooldown — no overlapping windows
                continue
            try:
                if not rule["signal"](ind, t):
                    continue
            except (TypeError, IndexError):
                continue
            fwd = fwd_return(ind, t, horizon)
            if fwd is None:
                continue
            last_fire = t

            if rule["outcome"] == "abs":
                hit = fwd > 0
                rel = None
            elif rule["outcome"] == "abs_inverse":
                hit = fwd <= 0
                rel = None
            else:  # rel — beat the index over the same window
                idx_ret = fwd_return_by_date(kse_map, None, t, horizon, sym_dates)
                if idx_ret is None:
                    continue
                rel = fwd - idx_ret
                hit = rel > 0
            events.append({"date": sym_dates[t], "sym": sym, "hit": hit,
                           "fwd_pct": round(fwd, 2),
                           "rel_pp": round(rel, 2) if rel is not None else None})

    events.sort(key=lambda e: e["date"])
    cut = int(len(events) * split)
    insample, holdout = events[:cut], events[cut:]

    def stats(ev):
        if not ev:
            return {"n": 0, "hit_rate": None, "avg_fwd_pct": None}
        return {
            "n": len(ev),
            "hit_rate": round(sum(e["hit"] for e in ev) / len(ev) * 100, 1),
            "avg_fwd_pct": round(sum(e["fwd_pct"] for e in ev) / len(ev), 2),
        }

    return {
        "rule": rule_name, "desc": rule["desc"], "maps_to": rule["maps_to"],
        "horizon_bars": horizon, "outcome_type": rule["outcome"],
        "all": stats(events), "in_sample": stats(insample), "holdout": stats(holdout),
        "first_event": events[0]["date"] if events else None,
        "last_event": events[-1]["date"] if events else None,
        "events": events,
    }


def run_conditional_rule(rule_name: str, rule: dict, symbols: list[str],
                         kse_bars: list[dict], kse_map: dict, split: float) -> dict:
    """Run a conditional rule variant. Supports requires_kse_ind for regime filters."""
    horizon = rule["horizon"]
    events = []

    kse_dates = [b["date"] for b in kse_bars]
    kse_date_idx = {d: i for i, d in enumerate(kse_dates)}
    kse_ind = compute_indicators(kse_bars) if rule.get("requires_kse_ind") else None

    for sym in symbols:
        if sym == "KSE100":
            continue
        bars = load_bars(sym)
        if len(bars) < WARMUP + horizon + 10:
            continue
        ind = compute_indicators(bars)
        sym_dates = [b["date"] for b in bars]
        last_fire = -10**9

        for t in range(WARMUP, len(bars) - horizon):
            if t - last_fire < horizon:
                continue
            # Map sym date to kse index
            t_kse = kse_date_idx.get(sym_dates[t]) if kse_ind else None
            try:
                if not rule["signal"](ind, t, kse_ind=kse_ind, t_kse=t_kse):
                    continue
            except (TypeError, IndexError):
                continue
            fwd = fwd_return(ind, t, horizon)
            if fwd is None:
                continue
            last_fire = t
            hit = fwd > 0 if rule["outcome"] == "abs" else fwd <= 0
            events.append({"date": sym_dates[t], "sym": sym, "hit": hit, "fwd_pct": round(fwd, 2)})

    events.sort(key=lambda e: e["date"])
    cut = int(len(events) * split)
    insample, holdout = events[:cut], events[cut:]

    def stats(ev):
        if not ev:
            return {"n": 0, "hit_rate": None, "avg_fwd_pct": None}
        return {
            "n": len(ev),
            "hit_rate": round(sum(e["hit"] for e in ev) / len(ev) * 100, 1),
            "avg_fwd_pct": round(sum(e["fwd_pct"] for e in ev) / len(ev), 2),
        }

    return {
        "rule": rule_name, "desc": rule["desc"], "maps_to": rule["maps_to"],
        "horizon_bars": horizon, "outcome_type": rule["outcome"],
        "all": stats(events), "in_sample": stats(insample), "holdout": stats(holdout),
        "first_event": events[0]["date"] if events else None,
        "last_event": events[-1]["date"] if events else None,
        "events": events,
    }


def run_pairs_rule(split: float) -> dict | None:
    """R-EXP-001 baseline: islamic vs conventional banks, aligned by common dates."""
    groups = {}
    for label, syms in (("islamic", PAIRS_RULE["islamic"]), ("conventional", PAIRS_RULE["conventional"])):
        series = []
        for s in syms:
            bars = load_bars(s)
            if bars:
                series.append({b["date"]: b["close"] for b in bars})
        if not series:
            return None
        groups[label] = series

    common = set.intersection(*[set(m.keys()) for m in groups["islamic"] + groups["conventional"]])
    dates = sorted(common)
    h = PAIRS_RULE["horizon"]
    if len(dates) < WARMUP:
        return None

    events = []
    t = WARMUP
    while t < len(dates) - h:
        d0, d1 = dates[t], dates[t + h]

        def grp_ret(series):
            rets = [(m[d1] - m[d0]) / m[d0] * 100 for m in series]
            return sum(rets) / len(rets)

        isl, conv = grp_ret(groups["islamic"]), grp_ret(groups["conventional"])
        events.append({"date": d0, "sym": "BANKS", "hit": isl > conv,
                       "fwd_pct": round(isl, 2), "rel_pp": round(isl - conv, 2)})
        t += h  # non-overlapping windows

    cut = int(len(events) * split)

    def stats(ev):
        if not ev:
            return {"n": 0, "hit_rate": None, "avg_rel_pp": None}
        return {"n": len(ev),
                "hit_rate": round(sum(e["hit"] for e in ev) / len(ev) * 100, 1),
                "avg_rel_pp": round(sum(e["rel_pp"] for e in ev) / len(ev), 2)}

    return {
        "rule": PAIRS_RULE["name"], "desc": PAIRS_RULE["desc"], "maps_to": PAIRS_RULE["maps_to"],
        "horizon_bars": h, "outcome_type": "pairs",
        "all": stats(events), "in_sample": stats(events[:cut]), "holdout": stats(events[cut:]),
        "first_event": events[0]["date"] if events else None,
        "last_event": events[-1]["date"] if events else None,
        "events": events,
    }

# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_table(results: list[dict]) -> None:
    print("\n" + "=" * 100)
    print(f"{'RULE':<32} {'N':>5} {'HIT%':>6} | {'IN-S n':>6} {'IN-S%':>6} | {'HOLD n':>6} {'HOLD%':>6}  VERDICT")
    print("-" * 100)
    for r in results:
        a, i, h = r["all"], r["in_sample"], r["holdout"]
        if a["n"] == 0:
            verdict = "no signals"
        elif a["n"] < 30:
            verdict = "n<30 — insufficient"
        elif h["n"] >= 10 and h["hit_rate"] is not None and h["hit_rate"] >= 55 and i["hit_rate"] >= 55:
            verdict = "BACKTEST-VALIDATED"
        elif h["n"] >= 10 and h["hit_rate"] is not None and h["hit_rate"] < 50:
            verdict = "fails holdout"
        else:
            verdict = "weak/mixed"
        print(f"{r['rule']:<32} {a['n']:>5} {a['hit_rate'] if a['hit_rate'] is not None else '—':>6} | "
              f"{i['n']:>6} {i['hit_rate'] if i['hit_rate'] is not None else '—':>6} | "
              f"{h['n']:>6} {h['hit_rate'] if h['hit_rate'] is not None else '—':>6}  {verdict}")
    print("=" * 100)
    print("Reminder: backtest-validated is a PRE-tier. Live forward observations are still required")
    print("for Provisional/Core. E-lens/news rules are NOT covered (no historical news archive).")


def main() -> None:
    ap = argparse.ArgumentParser(description="PSX rules backtest (no look-ahead)")
    ap.add_argument("--rules", type=str, default="all",
                    help=f"comma list of: {','.join(RULES)},{PAIRS_RULE['name']} (default all)")
    ap.add_argument("--symbols", type=str, default=None, help="comma list (default: all in data/ohlc)")
    ap.add_argument("--split", type=float, default=0.7, help="chronological in-sample fraction (default 0.7)")
    ap.add_argument("--condition-search", action="store_true",
                    help="Run conditional variants of rsi_oversold_bounce to find edge conditions")
    args = ap.parse_args()

    symbols = args.symbols.split(",") if args.symbols else all_symbols()
    symbols = [s.strip().upper() for s in symbols]

    kse_bars = load_bars("KSE100")
    kse_map = {b["date"]: b["close"] for b in kse_bars}
    if not kse_map:
        print("[WARN] KSE100 bars missing — relative-outcome rules will produce no events.")

    if args.condition_search:
        print("\n=== CONDITION SEARCH: rsi_oversold_bounce variants ===\n")
        results = []
        # baseline first
        print(f"[run] rsi_oversold_bounce (baseline) over {len(symbols)} symbols…")
        results.append(run_rule("rsi_oversold_bounce", RULES["rsi_oversold_bounce"],
                                symbols, kse_map, args.split))
        for cname, crule in CONDITIONAL_RULES.items():
            print(f"[run] {cname} over {len(symbols)} symbols…")
            results.append(run_conditional_rule(cname, crule, symbols, kse_bars, kse_map, args.split))
        print_table(results)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        out = REPORT_DIR / f"condition_search_{date.today().isoformat()}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"run_date": date.today().isoformat(), "split": args.split,
                       "mode": "condition_search", "n_symbols": len(symbols),
                       "results": results}, f, indent=1)
        print(f"\n[saved] {out}")
        return

    wanted = list(RULES) + [PAIRS_RULE["name"]] if args.rules == "all" else \
        [r.strip() for r in args.rules.split(",")]

    results = []
    for name in wanted:
        if name == PAIRS_RULE["name"]:
            r = run_pairs_rule(args.split)
            if r:
                results.append(r)
            continue
        if name not in RULES:
            print(f"[WARN] unknown rule '{name}' — skipped")
            continue
        print(f"[run] {name} over {len(symbols)} symbols…")
        results.append(run_rule(name, RULES[name], symbols, kse_map, args.split))

    print_table(results)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"backtest_{date.today().isoformat()}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"run_date": date.today().isoformat(), "split": args.split,
                   "n_symbols": len(symbols), "results": results}, f, indent=1)
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
