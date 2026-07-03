#!/usr/bin/env python3
"""
universe_signals.py — Layer-1 universe prediction engine.

Runs the SKILL.md Part-H deterministic scorecard for EVERY KSE-100 symbol
from the locally-stored data/ohlc/ + data/fundamentals/ stores (no network).

Outputs:
  data/universe_signals.csv  — append-only, one row per symbol per run
  data/dashboard_feed.json   — rewritten each run, per-symbol dashboard payload

Signal map  (score → signal):
  score >= +3  → BUY
  -2 < score < +3  → HOLD
  score <= -2  → SELL

Conviction (screen-grade 1-3 only — Layer 1, NOT actionable advice):
  |score| >= 5 → 3
  3-4 → 2
  else → 1

Usage:
  python scripts/universe_signals.py
  python scripts/universe_signals.py --date 2026-06-23  (override run date)
  python scripts/universe_signals.py --dry-run          (print table, don't write)
"""

import json, os, sys, csv, datetime as dt, argparse

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OHLC_DIR = os.path.join(ROOT, "data", "ohlc")
FUND_DIR = os.path.join(ROOT, "data", "fundamentals")
UNI_FILE = os.path.join(ROOT, "data", "universe.json")
SIG_CSV  = os.path.join(ROOT, "data", "universe_signals.csv")
DASH_JSON = os.path.join(ROOT, "data", "dashboard_feed.json")

# face-value overrides (PKR). Default 10.
FACE = {"UBL": 5.0, "MTL": 5.0}

# CSV columns (append-only — never remove/reorder existing columns)
CSV_COLS = [
    "date", "symbol", "signal", "conviction", "score",
    "close", "rsi", "ma20", "ma50", "ma200",
    "pos52", "eps_trend", "yield_pct", "mom20",
    "support", "resistance", "diligence",
    "grade_on_date", "status", "result", "why",
    # per-factor breakdown (transparency)
    "f_trend", "f_rsi", "f_52w", "f_mom20", "f_eps", "f_yield", "f_rules",
]

# ─── helpers ────────────────────────────────────────────────────────────────

def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)

def adj_closes(bars):
    return [b.get("adj_close") or b["close"] for b in bars]

def sma(vals, n):
    if len(vals) < n:
        return None
    return sum(vals[-n:]) / n

def rsi14(vals):
    """Wilder RSI-14 from a list of closes."""
    if len(vals) < 16:
        return None
    gains = losses = 0.0
    for i in range(-14, 0):
        d = vals[i] - vals[i - 1]
        if d >= 0:
            gains += d
        else:
            losses -= d
    avg_g = gains / 14
    avg_l = losses / 14
    # one more smoothing step with the last bar
    d = vals[-1] - vals[-2]
    g = max(d, 0)
    l = max(-d, 0)
    avg_g = (avg_g * 13 + g) / 14
    avg_l = (avg_l * 13 + l) / 14
    if avg_l == 0:
        return 100.0
    return 100 - 100 / (1 + avg_g / avg_l)

def swing_lo_hi(bars, n=60):
    """Nearest support (swing low) and resistance (swing high) over last n bars."""
    recent = bars[-n:] if len(bars) >= n else bars
    lows   = [b.get("adj_low",  b.get("low",  b["close"])) for b in recent]
    highs  = [b.get("adj_high", b.get("high", b["close"])) for b in recent]
    return min(lows), max(highs)

def ttm_dps(fund, sym):
    """TTM DPS (PKR) from payout history. Face-value correct per R-EXP-002."""
    face = FACE.get(sym, 10.0)
    pays = [p for p in fund.get("payouts", [])
            if p.get("type") == "dividend" and p.get("pct")]
    if not pays:
        return 0.0, face
    pays.sort(key=lambda p: p["announced"], reverse=True)
    latest = dt.date.fromisoformat(pays[0]["announced"])
    window = [p for p in pays
              if (latest - dt.date.fromisoformat(p["announced"])).days <= 370]
    total_pct = sum(p["pct"] for p in window)
    return total_pct / 100 * face, face

def eps_trend(fund):
    """
    Returns ('rising'|'flat'|'falling'|None, latest_eps_float|None).
    Uses unconsolidated quarterly results only.
    Compares latest IQ-annualised vs latest full-year (YR) EPS.
    """
    qs = [q for q in fund.get("quarterly_results", [])
          if not q.get("consolidated") and q.get("eps") is not None]
    if not qs:
        return None, None

    yr = [q for q in qs if q.get("period_type") == "YR" and q["eps"]]
    iq = [q for q in qs if q.get("period_type") in ("IQ", "IIIQ", "HYR") and q["eps"]]

    # latest available single-period EPS (for P/E)
    all_sorted = sorted(qs, key=lambda q: q["announced"], reverse=True)
    latest_eps = all_sorted[0]["eps"] if all_sorted else None

    if iq and yr:
        yr.sort(key=lambda q: q["announced"], reverse=True)
        iq.sort(key=lambda q: q["announced"], reverse=True)
        annual_runrate = iq[0]["eps"] * 4
        prior_annual   = yr[0]["eps"]
        if prior_annual and prior_annual > 0:
            growth = (annual_runrate / prior_annual - 1) * 100
            if growth > 10:
                return "rising", latest_eps
            elif growth < -10:
                return "falling", latest_eps
            else:
                return "flat", latest_eps

    # fallback: compare two annual rows if available
    if len(yr) >= 2:
        yr.sort(key=lambda q: q["announced"], reverse=True)
        if yr[0]["eps"] > yr[1]["eps"] * 1.05:
            return "rising", latest_eps
        elif yr[0]["eps"] < yr[1]["eps"] * 0.95:
            return "falling", latest_eps
        else:
            return "flat", latest_eps

    return None, latest_eps  # not enough data to determine trend

# ─── scorecard (SKILL.md Part H) ────────────────────────────────────────────

def scorecard(sym, bars, fund, run_date, announced_today=False):
    """
    Returns a dict with all scorecard fields.
    No network. Reads stored OHLC + fundamentals only.
    """
    closes  = adj_closes(bars)
    last    = closes[-1]
    raw_last = bars[-1]["close"]

    ma20  = sma(closes, 20)
    ma50  = sma(closes, 50)
    ma200 = sma(closes, 200)
    rsi_v = rsi14(closes)

    # 52-week position
    win_52 = closes[-252:] if len(closes) >= 252 else closes
    lo52, hi52 = min(win_52), max(win_52)
    pos52 = (last - lo52) / (hi52 - lo52) * 100 if hi52 > lo52 else None

    # 20-day momentum
    mom20 = (closes[-1] / closes[-21] - 1) * 100 if len(closes) >= 21 else None

    # support / resistance
    s_lo, s_hi = swing_lo_hi(bars, 60)
    support    = round(max(s_lo, ma50 or 0, ma200 or 0), 2)
    resistance = round(min(s_hi, hi52), 2)

    # fundamentals
    trend, latest_eps = eps_trend(fund)
    dps, face = ttm_dps(fund, sym)
    yld = (dps / raw_last * 100) if raw_last and dps else 0.0
    pe  = (raw_last / latest_eps) if latest_eps and latest_eps > 0 else None

    # ── factor scores ────────────────────────────────────────────────────────
    # Trend: price vs MA50 & MA200 + golden/death cross
    f_trend = 0
    if ma50 and ma200:
        above_50  = last > ma50
        above_200 = last > ma200
        golden    = ma50 > ma200
        if above_50 and above_200 and golden:
            f_trend = +2
        elif above_200:
            f_trend = +1
        elif not above_50 and not above_200 and not golden:
            f_trend = -2
        else:
            f_trend = -1
    elif ma200:
        f_trend = +1 if last > ma200 else -1

    # RSI zone
    f_rsi = 0
    if rsi_v is not None:
        if 40 <= rsi_v <= 60:
            f_rsi = +1
        elif rsi_v < 30:
            f_rsi = +1   # oversold mean-revert up
        elif rsi_v > 80:
            f_rsi = -2
        elif rsi_v > 70:
            f_rsi = -1

    # 52-week position
    f_52w = 0
    if pos52 is not None:
        if 25 <= pos52 <= 60:
            f_52w = +1
        elif pos52 > 90:
            f_52w = -1

    # 20-day momentum
    f_mom20 = 0
    if mom20 is not None:
        if mom20 > 0:
            f_mom20 = +1
        elif mom20 < -5:
            f_mom20 = -1

    # EPS trend (the JDWS lesson: falling → -2)
    f_eps = 0
    if trend == "rising":
        f_eps = +2
    elif trend == "falling":
        f_eps = -2
    elif trend == "flat":
        f_eps = 0
    # None → 0 (not enough data)

    # Yield (covered)
    f_yield = 0
    if yld >= 6 and latest_eps and latest_eps > 0:
        f_yield = +1
    if yld > 15:
        f_yield = 0   # R-003: suspicious yield — don't reward; flag instead

    # Rule tilts (Core/Provisional only; Experimental = 0 weight)
    # R-001: if SBP rate elevated (11.5%) and symbol is a quality bank → +1 F-tilt
    ISLAMIC_BANKS = {"MEBL", "FABL"}
    CONV_BANKS    = {"MCB", "UBL", "HBL", "ABL", "AKBL", "BAHL", "HMB", "NBP",
                     "BAFL", "BOP", "SCBPL", "PABC"}
    f_rules = 0
    if sym in ISLAMIC_BANKS or sym in CONV_BANKS:
        f_rules += 1   # R-001: elevated SBP rate → NIM expansion tailwind for banks

    # Total score
    score = f_trend + f_rsi + f_52w + f_mom20 + f_eps + f_yield + f_rules

    # Signal + screen-grade conviction (1-3 only; Layer 1)
    if score >= 3:
        signal = "BUY"
    elif score <= -2:
        signal = "SELL"
    else:
        signal = "HOLD"

    abs_score = abs(score)
    if abs_score >= 5:
        conviction = 3
    elif abs_score >= 3:
        conviction = 2
    else:
        conviction = 1

    # Diligence flag: STALE if new announcement today, else OK
    diligence = "STALE" if announced_today else "OK"

    # Grade window: 5 sessions for daily signals
    grade_on = run_date + dt.timedelta(days=7)   # ~5 trading sessions
    # skip weekends
    while grade_on.weekday() >= 5:
        grade_on += dt.timedelta(days=1)

    why_parts = []
    if f_trend:    why_parts.append(f"trend{'+' if f_trend>0 else ''}{f_trend}")
    if f_rsi:      why_parts.append(f"rsi{'+' if f_rsi>0 else ''}{f_rsi}({rsi_v:.0f})" if rsi_v else f"rsi{f_rsi}")
    if f_52w:      why_parts.append(f"52w{'+' if f_52w>0 else ''}{f_52w}({pos52:.0f}%)" if pos52 else f"52w{f_52w}")
    if f_mom20:    why_parts.append(f"mom20{'+' if f_mom20>0 else ''}{f_mom20}")
    if f_eps:      why_parts.append(f"eps_{trend}{'+' if f_eps>0 else ''}{f_eps}")
    if f_yield:    why_parts.append(f"yld{yld:.1f}%{'+' if f_yield>0 else ''}{f_yield}")
    if f_rules:    why_parts.append(f"rules+{f_rules}")
    why = "; ".join(why_parts) if why_parts else "all_zero"

    return {
        "date":        run_date.isoformat(),
        "symbol":      sym,
        "signal":      signal,
        "conviction":  conviction,
        "score":       score,
        "close":       round(raw_last, 2),
        "rsi":         round(rsi_v, 1) if rsi_v is not None else None,
        "ma20":        round(ma20, 2) if ma20 else None,
        "ma50":        round(ma50, 2) if ma50 else None,
        "ma200":       round(ma200, 2) if ma200 else None,
        "pos52":       round(pos52, 1) if pos52 is not None else None,
        "eps_trend":   trend or "unknown",
        "yield_pct":   round(yld, 2),
        "mom20":       round(mom20, 2) if mom20 is not None else None,
        "support":     support,
        "resistance":  resistance,
        "diligence":   diligence,
        "grade_on_date": grade_on.isoformat(),
        "status":      "open",
        "result":      "",
        "why":         why,
        # per-factor breakdown
        "f_trend":  f_trend,
        "f_rsi":    f_rsi,
        "f_52w":    f_52w,
        "f_mom20":  f_mom20,
        "f_eps":    f_eps,
        "f_yield":  f_yield,
        "f_rules":  f_rules,
        # extras for dashboard_feed (not in CSV)
        "_pe":         round(pe, 2) if pe else None,
        "_name":       None,   # filled by caller
    }

# ─── main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date",    default=None, help="Override run date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Print table, don't write files")
    args = parser.parse_args()

    run_date = dt.date.fromisoformat(args.date) if args.date else dt.date.today()

    uni = load_json(UNI_FILE)
    symbols = [s["ticker"] for s in uni["symbols"]]
    name_map = {s["ticker"]: s["name"] for s in uni["symbols"]}

    # Determine which symbols are STALE (diligence flag).
    #
    # STALE is NOT just "filed something today" (that self-cleared the next day even
    # if the filing was never read — the JDWS failure mode). The persistent diligence
    # ledger (data/diligence_ledger.json, written by scripts/process_filings.py) is
    # AUTHORITATIVE:
    #   - a symbol is STALE while it has an UNRESOLVED filing (materiality MATERIAL or
    #     UNKNOWN and not yet reviewed) — this PERSISTS across runs until accounted for;
    #   - a filing reviewed/auto-cleared as NON_MATERIAL does NOT make the symbol STALE,
    #     even on its filing day.
    # Today's raw snapshot announcements are a FALLBACK: they flag a symbol only if the
    # ledger has no record of that filing yet (i.e. process_filings.py hasn't run) — so
    # a brand-new, unprocessed filing still defaults to STALE (safe).
    announced_syms = set()      # → STALE
    resolved_syms  = set()      # filings the ledger has cleared (non-material/reviewed)

    # (a) authoritative ledger
    ledger_file = os.path.join(ROOT, "data", "diligence_ledger.json")
    if os.path.exists(ledger_file):
        led = load_json(ledger_file)
        for f in led.get("filings", []):
            sym_l = (f.get("symbol") or "").upper()
            if not sym_l:
                continue
            unresolved = (not f.get("reviewed")) and f.get("materiality") in ("MATERIAL", "UNKNOWN")
            if unresolved:
                announced_syms.add(sym_l)
            else:
                resolved_syms.add(sym_l)

    # (b) today's raw announcements — flag only if not already resolved by the ledger
    mkt_file = os.path.join(ROOT, "data", "market_data", f"{run_date.isoformat()}.json")
    if os.path.exists(mkt_file):
        mkt = load_json(mkt_file)
        anns = mkt.get("announcements", [])
        # list form carries per-company rows; a descriptive object = no filings.
        if isinstance(anns, list):
            for ann in anns:
                if not isinstance(ann, dict):
                    continue
                s = (ann.get("symbol") or ann.get("ticker") or "").upper()
                if s and s not in resolved_syms:
                    announced_syms.add(s)

    results = []
    skipped = []

    for sym in symbols:
        ohlc_path = os.path.join(OHLC_DIR, sym + ".json")
        fund_path = os.path.join(FUND_DIR, sym + ".json")

        if not os.path.exists(ohlc_path):
            skipped.append((sym, "no OHLC"))
            continue
        if not os.path.exists(fund_path):
            skipped.append((sym, "no fundamentals"))
            continue

        bars = load_json(ohlc_path)
        fund = load_json(fund_path)

        if len(bars) < 20:
            skipped.append((sym, f"only {len(bars)} bars"))
            continue

        # Only use bars up to run_date (no look-ahead)
        bars = [b for b in bars if b["date"] <= run_date.isoformat()]
        if len(bars) < 20:
            skipped.append((sym, "insufficient bars for run_date"))
            continue

        try:
            row = scorecard(sym, bars, fund, run_date, sym in announced_syms)
            row["_name"] = name_map.get(sym, "")
            results.append(row)
        except Exception as e:
            skipped.append((sym, f"error: {e}"))

    # ── print table ──────────────────────────────────────────────────────────
    buy  = [r for r in results if r["signal"] == "BUY"]
    sell = [r for r in results if r["signal"] == "SELL"]
    hold = [r for r in results if r["signal"] == "HOLD"]

    buy.sort(key=lambda r: (-r["score"], r["symbol"]))
    sell.sort(key=lambda r: (r["score"], r["symbol"]))
    hold.sort(key=lambda r: (-r["score"], r["symbol"]))

    print(f"\n{'='*100}")
    print(f"LAYER-1 UNIVERSE ENGINE — {run_date}  |  {len(results)} symbols scored  "
          f"|  BUY={len(buy)}  HOLD={len(hold)}  SELL={len(sell)}")
    print(f"{'='*100}")
    print(f"  Training signal only — NOT actionable advice (Layer 1). "
          f"Layer-2 conviction call requires full Prime-Directive-#9 diligence.")
    print(f"{'='*100}\n")

    hdr = f"{'SYM':8} {'SIGNAL':6} {'CV':3} {'SC':4} {'CLOSE':8} {'RSI':6} {'MA50':8} {'MA200':8} {'52W%':6} {'EPS':8} {'YLD%':6} {'DILIG':7}  WHY"
    sep = "-" * len(hdr)

    for label, group in [("▲ BUY", buy), ("─ HOLD (top 20)", hold[:20]), ("▼ SELL", sell)]:
        if not group:
            continue
        print(f"\n{label}")
        print(sep)
        print(hdr)
        print(sep)
        for r in group:
            print(
                f"{r['symbol']:8} {r['signal']:6} {r['conviction']:3} {r['score']:+4} "
                f"{r['close']:8.2f} "
                f"{(str(round(r['rsi'],1)) if r['rsi'] else '—'):>6} "
                f"{(str(round(r['ma50'],1)) if r['ma50'] else '—'):>8} "
                f"{(str(round(r['ma200'],1)) if r['ma200'] else '—'):>8} "
                f"{(str(round(r['pos52'],1))+'%' if r['pos52'] is not None else '—'):>6} "
                f"{r['eps_trend']:>8} "
                f"{r['yield_pct']:>6.1f}% "
                f"{'⚠STALE' if r['diligence']=='STALE' else 'OK':>7}  "
                f"{r['why']}"
            )

    if skipped:
        print(f"\n⚠ Skipped {len(skipped)}: {', '.join(s[0] for s in skipped[:20])}"
              + (f" …+{len(skipped)-20}" if len(skipped) > 20 else ""))

    if args.dry_run:
        print("\n[dry-run] — no files written.")
        return

    # ── append to universe_signals.csv ───────────────────────────────────────
    write_header = not os.path.exists(SIG_CSV)
    # Deduplicate: skip symbols already written for this run_date
    existing_keys = set()
    if not write_header:
        with open(SIG_CSV, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                if row.get("date") == run_date.isoformat():
                    existing_keys.add(row["symbol"])

    new_rows = [r for r in results if r["symbol"] not in existing_keys]

    with open(SIG_CSV, "a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        for r in new_rows:
            writer.writerow(r)

    print(f"\n✓ Appended {len(new_rows)} rows to {os.path.relpath(SIG_CSV, ROOT)}"
          f"  ({len(existing_keys)} already present for {run_date})")

    # ── write dashboard_feed.json ─────────────────────────────────────────────
    feed = {}
    for r in results:
        feed[r["symbol"]] = {
            "name":        r["_name"],
            "date":        r["date"],
            "close":       r["close"],
            "signal":      r["signal"],
            "conviction":  r["conviction"],
            "score":       r["score"],
            "ma20":        r["ma20"],
            "ma50":        r["ma50"],
            "ma200":       r["ma200"],
            "rsi":         r["rsi"],
            "pos52":       r["pos52"],
            "eps_trend":   r["eps_trend"],
            "yield_pct":   r["yield_pct"],
            "mom20":       r["mom20"],
            "support":     r["support"],
            "resistance":  r["resistance"],
            "diligence":   r["diligence"],
            "why":         r["why"],
            "factors": {
                "trend":  r["f_trend"],
                "rsi":    r["f_rsi"],
                "pos52w": r["f_52w"],
                "mom20":  r["f_mom20"],
                "eps":    r["f_eps"],
                "yield":  r["f_yield"],
                "rules":  r["f_rules"],
            },
            "signal_history_file": f"data/universe_signals.csv",
        }

    meta = {
        "_generated": run_date.isoformat(),
        "_symbols":   len(results),
        "_buy":       len(buy),
        "_hold":      len(hold),
        "_sell":      len(sell),
        "_note":      "Layer-1 engine signal. Training only, not actionable advice. "
                      "diligence=STALE means a new filing was posted today — open it before any Layer-2 call.",
    }
    out = {"_meta": meta, "symbols": feed}

    with open(DASH_JSON, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    print(f"✓ Wrote dashboard_feed.json  ({len(results)} symbols)")
    print(f"\nSummary: BUY={len(buy)}  HOLD={len(hold)}  SELL={len(sell)}  "
          f"STALE={sum(1 for r in results if r['diligence']=='STALE')}  "
          f"skipped={len(skipped)}")


if __name__ == "__main__":
    main()
