#!/usr/bin/env python3
"""Ad-hoc screener: rank dividends / swing / growth from local fundamentals + OHLC.
No network. Reads data/fundamentals/*.json and data/ohlc/*.json. No look-ahead beyond latest bar."""
import json, glob, os, datetime as dt, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUND = os.path.join(ROOT, "data", "fundamentals")
OHLC = os.path.join(ROOT, "data", "ohlc")

# face value overrides (PKR). Default 10. Splits change these.
FACE = {"UBL": 5.0, "MTL": 5.0}

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def parse_date(s):
    return dt.date.fromisoformat(s)

def ohlc(sym):
    p = os.path.join(OHLC, sym + ".json")
    if not os.path.exists(p):
        return None
    bars = load(p)
    if not bars:
        return None
    return bars

def adj_closes(bars):
    return [b.get("adj_close", b["close"]) for b in bars]

def rsi(vals, n=14):
    if len(vals) < n + 1:
        return None
    gains = losses = 0.0
    for i in range(-n, 0):
        d = vals[i] - vals[i-1]
        if d >= 0: gains += d
        else: losses -= d
    if losses == 0: return 100.0
    rs = (gains/n) / (losses/n)
    return 100 - 100/(1+rs)

def sma(vals, n):
    if len(vals) < n: return None
    return sum(vals[-n:]) / n

def ttm_eps(fund):
    """Sum last 4 unconsolidated quarterly EPS if available; else use latest YR unconsolidated."""
    qs = [q for q in fund.get("quarterly_results", []) if not q.get("consolidated")]
    # prefer most recent annual (YR) unconsolidated for stable ttm
    yr = [q for q in qs if q.get("period_type") == "YR" and q.get("eps")]
    if yr:
        yr.sort(key=lambda q: q["announced"], reverse=True)
        return yr[0]["eps"], yr[0]["period"]
    # fallback: latest eps
    if qs:
        qs.sort(key=lambda q: q["announced"], reverse=True)
        return qs[0].get("eps"), qs[0].get("period")
    return None, None

def eps_growth(fund):
    """YoY: latest YR unconsolidated EPS vs prior-year YR. Need 2 annuals; fundamentals only have latest.
    Fallback: latest quarter EPS vs same quarter PAT growth not available -> use IQ vs prior IQ if present."""
    qs = [q for q in fund.get("quarterly_results", []) if not q.get("consolidated") and q.get("eps")]
    # compare latest interim quarter to the annual-implied run-rate is unreliable; we only have ~2 periods.
    # Use: latest IQ eps annualized vs latest YR eps  -> growth proxy
    iq = [q for q in qs if q.get("period_type") == "IQ"]
    yr = [q for q in qs if q.get("period_type") == "YR"]
    if iq and yr:
        iq.sort(key=lambda q: q["announced"], reverse=True)
        yr.sort(key=lambda q: q["announced"], reverse=True)
        latest_q = iq[0]["eps"]
        annual = yr[0]["eps"]
        # quarterly run-rate annualized vs prior full-year
        ann_runrate = latest_q * 4
        if annual:
            return (ann_runrate/annual - 1) * 100, f"{iq[0]['period']} x4 vs FY {yr[0]['period']}"
    return None, None

def ttm_dps(fund, sym):
    face = FACE.get(sym, 10.0)
    pays = [p for p in fund.get("payouts", []) if p.get("type") == "dividend" and p.get("pct")]
    if not pays:
        return 0.0, face, 0
    pays.sort(key=lambda p: p["announced"], reverse=True)
    # sum payouts announced within last ~370 days of latest announce date
    latest = parse_date(pays[0]["announced"])
    window = [p for p in pays if (latest - parse_date(p["announced"])).days <= 370]
    total_pct = sum(p["pct"] for p in window)
    dps = total_pct/100 * face
    return dps, face, len(window)

rows = []
for fp in glob.glob(os.path.join(FUND, "*.json")):
    sym = os.path.splitext(os.path.basename(fp))[0]
    fund = load(fp)
    bars = ohlc(sym)
    if not bars: continue
    closes = adj_closes(bars)
    raw_last = bars[-1]["close"]
    last = closes[-1]
    last_date = bars[-1]["date"]
    eps, eps_period = ttm_eps(fund)
    dps, face, ndiv = ttm_dps(fund, sym)
    g, gnote = eps_growth(fund)
    pe = (raw_last/eps) if eps and eps > 0 else None
    yld = (dps/raw_last*100) if raw_last else 0.0
    r = rsi(closes)
    s50 = sma(closes, 50); s200 = sma(closes, 200)
    # 52w range position
    win = closes[-250:] if len(closes) >= 250 else closes
    lo, hi = min(win), max(win)
    pos52 = (last-lo)/(hi-lo)*100 if hi > lo else None
    # momentum 20d
    mom20 = (closes[-1]/closes[-21]-1)*100 if len(closes) >= 21 else None
    rows.append(dict(sym=sym, last=raw_last, date=last_date, eps=eps, pe=pe, dps=dps, face=face,
                     ndiv=ndiv, yld=yld, growth=g, gnote=gnote, rsi=r, s50=s50, s200=s200,
                     pos52=pos52, mom20=mom20))

def f(x, d=1):
    return "—" if x is None else f"{x:.{d}f}"

# DIVIDENDS: yield, require coverage (P/E reasonable, payout sustainable proxy: eps>0, ndiv>=3)
div = [r for r in rows if r["yld"] > 0 and r["eps"] and r["eps"] > 0 and r["ndiv"] >= 3]
# guard R-003: flag extreme yields
div.sort(key=lambda r: r["yld"], reverse=True)

# SWING: liquid-ish, near support but turning. score: oversold RSI 35-55 + above s200 (uptrend intact) + lower-half 52w
def swing_score(r):
    sc = 0
    if r["rsi"] is not None:
        if 35 <= r["rsi"] <= 50: sc += 2   # pulled back, not crashing
        elif 50 < r["rsi"] <= 60: sc += 1
    if r["s50"] and r["s200"] and r["last"] > r["s200"]: sc += 1  # primary uptrend
    if r["pos52"] is not None and 25 <= r["pos52"] <= 60: sc += 2  # mid-range, room to run
    if r["mom20"] is not None and r["mom20"] > 0: sc += 1          # turning up
    return sc
sw = [r for r in rows if r["rsi"] is not None and r["s200"]]
for r in sw: r["sw"] = swing_score(r)
sw.sort(key=lambda r: (r["sw"], r["mom20"] or -99), reverse=True)

# GROWTH: positive EPS growth proxy + reasonable PE + above trend
gr = [r for r in rows if r["growth"] is not None and r["growth"] > 0 and r["pe"] and 0 < r["pe"] < 25]
def growth_score(r):
    sc = r["growth"]/10
    if r["pe"] and r["pe"] < 12: sc += 2   # growth at reasonable price
    if r["s50"] and r["s200"] and r["s50"] > r["s200"]: sc += 2  # uptrend
    return sc
for r in gr: r["grsc"] = growth_score(r)
gr.sort(key=lambda r: r["grsc"], reverse=True)

print(f"# universe: {len(rows)} symbols | latest bar dates vary\n")
print("## TOP DIVIDENDS (ttm yield, coverage-screened)")
print(f"{'SYM':6}{'price':>8}{'DPS':>7}{'yld%':>7}{'P/E':>7}{'EPS':>8}{'#div':>5}  note")
for r in div[:12]:
    flag = " ⚠>15% R-003" if r["yld"] > 15 else ""
    print(f"{r['sym']:6}{r['last']:>8.1f}{r['dps']:>7.1f}{r['yld']:>7.1f}{f(r['pe']):>7}{f(r['eps']):>8}{r['ndiv']:>5}  face{int(r['face'])}{flag}")

print("\n## TOP SWING (pullback-in-uptrend setups)")
print(f"{'SYM':6}{'price':>8}{'RSI':>6}{'pos52%':>8}{'mom20%':>8}{'>s200':>7}{'score':>6}")
for r in sw[:12]:
    print(f"{r['sym']:6}{r['last']:>8.1f}{f(r['rsi']):>6}{f(r['pos52']):>8}{f(r['mom20']):>8}{('Y' if r['last']>r['s200'] else 'n'):>7}{r['sw']:>6}")

print("\n## TOP GROWTH (EPS-growth proxy at reasonable price)")
print(f"{'SYM':6}{'price':>8}{'growth%':>9}{'P/E':>7}{'s50>s200':>9}  gnote")
for r in gr[:12]:
    print(f"{r['sym']:6}{r['last']:>8.1f}{f(r['growth']):>9}{f(r['pe']):>7}{('Y' if (r['s50'] and r['s200'] and r['s50']>r['s200']) else 'n'):>9}  {r['gnote']}")
