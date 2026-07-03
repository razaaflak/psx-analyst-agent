#!/usr/bin/env python
"""
process_filings.py — turn raw PSX announcements into a persistent diligence ledger.

WHY THIS EXISTS
---------------
`universe_signals.py` previously set `diligence = "STALE" if announced_today else "OK"`.
That flag was purely per-run: it self-cleared the very next day whether or not the
filing was ever read. A symbol could file a material restructuring, get flagged STALE
for one day, then silently revert to OK — exactly the JDWS failure mode the flag was
meant to prevent (acting on stale fundamentals because the filing's content was unread).

This script makes STALE *mean something durable*:
  1. For each NEW filing (from data/market_data/<date>.json announcements), download the
     PDF, extract its text (pymupdf; notes when a PDF is image-only / needs OCR).
  2. Auto-classify materiality from the title + extracted text (keyword rules).
  3. Persist every filing in data/diligence_ledger.json with a verdict + reviewed flag.

A symbol is STALE (per the ledger) while it has ANY unresolved filing — i.e. a filing
that is material AND not yet human-reviewed. Non-material reaffirmations (rating
maintained, routine board-meeting notices, AGM minutes, fund distributions) auto-clear.
Material filings (results, mergers/schemes, demergers, capital changes, profit
warnings, payouts that change fundamentals) stay STALE until a human sets reviewed=true.

This is the JDWS protection done properly: the flag persists until the content is
actually accounted for, not just until the next trading day.

USAGE
-----
  python scripts/process_filings.py --date 2026-06-29            # process that day's filings
  python scripts/process_filings.py --date 2026-06-29 --no-download   # classify by title only
  python scripts/process_filings.py --review AGP --notes "Scheme read; await Sindh HC sanction"
  python scripts/process_filings.py --list-stale                 # show currently-stale symbols
"""
import argparse, datetime as dt, json, os, re, sys

ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MKT_DIR   = os.path.join(ROOT, "data", "market_data")
LEDGER    = os.path.join(ROOT, "data", "diligence_ledger.json")
PDF_CACHE = os.path.join(ROOT, "data", "filings_cache")
UNI_FILE  = os.path.join(ROOT, "data", "universe.json")

# ── materiality classification ──────────────────────────────────────────────
# Title/text keywords that make a filing MATERIAL (fundamentals/structure may change
# → keep STALE until a human reviews). Order: most specific first.
MATERIAL_PATTERNS = [
    r"scheme of arrangement", r"amalgamation", r"\bmerger\b", r"demerger",
    r"bifurcation", r"restructur", r"re-?organi[sz]ation",
    r"financial result", r"\bresults?\b", r"\bprofit\b", r"\bloss\b", r"earnings",
    r"\beps\b", r"dividend", r"\bbonus\b", r"right issue", r"rights issue",
    r"capital", r"acquisi", r"divest", r"de-?listing", r"winding up",
    r"profit warning", r"material information",
]
# Patterns that are routine / non-material reaffirmations → auto-clear (OK).
NONMATERIAL_PATTERNS = [
    r"entity rating", r"rating (maintained|reaffirmed|assigned)",
    r"corporate briefing", r"\bcbs\b",
    r"closed period",                 # the closed-period notice itself is procedural
    r"notice of (agm|eogm|egm|book closure)",
    r"minutes of (the )?(annual |extra)?",
    r"interim distribution", r"completion of",
    r"true copy of resolutions adopted",
]


def classify(title: str, text: str = "") -> tuple[str, str]:
    """Return (materiality, reason). materiality in {MATERIAL, NON_MATERIAL, UNKNOWN}."""
    blob = f"{title}\n{text}".lower()
    # Board-meeting notices: "OTHER THAN financial results" / "other than to consider
    # the accounts" is procedural (non-material). Only a meeting called TO consider
    # results/accounts is material (results pending). Check the negation FIRST so the
    # mere presence of the word "financial" inside "other than financial results"
    # does not flip it to MATERIAL (KEL 2026-06-30 was misclassified this way).
    if re.search(r"board meeting", blob):
        if re.search(r"other than .{0,30}(financial )?result|other than .{0,30}account", blob):
            return "NON_MATERIAL", "board meeting OTHER THAN financial results (procedural)"
        if re.search(r"(consider|approv|adopt).{0,40}(result|account|financial statement)"
                     r"|financial result|quarterly result|annual result|half[- ]year", blob):
            return "MATERIAL", "board meeting to consider financial results (results pending)"
    for pat in NONMATERIAL_PATTERNS:
        if re.search(pat, blob):
            return "NON_MATERIAL", f"matched non-material pattern /{pat}/"
    for pat in MATERIAL_PATTERNS:
        if re.search(pat, blob):
            return "MATERIAL", f"matched material pattern /{pat}/"
    # A bare "board meeting in progress" with no result reference = procedural.
    if re.search(r"board meeting", blob):
        return "NON_MATERIAL", "routine board-meeting notice (no result reference)"
    return "UNKNOWN", "no keyword match — treat as material until reviewed"


# ── url handling ─────────────────────────────────────────────────────────────
PSX_BASE = "https://dps.psx.com.pk"


def normalize_pdf_url(url: str, doc_id: str = "") -> str:
    """Return a fetchable absolute PSX document URL.

    Handles the recurring failure mode where the snapshot stores a *relative*
    href ('/download/document/279317.pdf') or omits the url but has a doc_id.
    Never returns a scheme-less path.
    """
    url = (url or "").strip()
    if url.startswith("//"):                       # protocol-relative
        return "https:" + url
    if url.startswith("/"):                        # site-relative
        return PSX_BASE + url
    if url.startswith("http://"):                  # force https (PSX redirects)
        return "https://" + url[len("http://"):]
    if url.startswith("https://"):
        return url
    if url:                                        # bare path like 'download/document/x.pdf'
        return f"{PSX_BASE}/{url.lstrip('/')}"
    if doc_id:                                     # no url at all → reconstruct from doc_id
        return f"{PSX_BASE}/download/document/{doc_id}.pdf"
    return ""


# ── pdf text extraction ─────────────────────────────────────────────────────
def extract_pdf_text(url: str, sym: str, doc_id: str) -> tuple[str, str]:
    """Download + extract text. Returns (text, note). note flags image-only PDFs.

    `url` is normalized to an absolute PSX URL first, and reconstructed from
    doc_id if missing, so a scheme-less/blank snapshot value no longer silently
    skips the fetch.
    """
    try:
        import requests, fitz  # pymupdf
    except ImportError as e:
        return "", f"pdf libs missing ({e}); title-only classification"

    fetch_url = normalize_pdf_url(url, doc_id)
    if not fetch_url:
        return "", "no pdf_url and no doc_id — cannot fetch"

    os.makedirs(PDF_CACHE, exist_ok=True)
    path = os.path.join(PDF_CACHE, f"{sym}_{doc_id or 'noid'}.pdf")
    last_err = ""
    for attempt in range(3):                       # transient PSX 5xx / timeouts
        try:
            if not os.path.exists(path) or os.path.getsize(path) < 100:
                r = requests.get(fetch_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=45)
                r.raise_for_status()
                magic = r.content[:5]
                is_pdf = magic.startswith(b"%PDF-")
                is_img = magic[:3] == b"GIF" or magic[:2] == b"\xff\xd8" or magic[:4] == b"\x89PNG"
                if not (is_pdf or is_img):
                    last_err = f"not a PDF/image (got {r.headers.get('content-type','?')})"
                    break
                with open(path, "wb") as fh:
                    fh.write(r.content)
                if is_img:                          # image-only filing (e.g. .gif notice)
                    return "", "image-only filing (GIF/PNG/JPEG) — needs visual review"
            d = fitz.open(path)
            text = "\n".join(p.get_text() for p in d)
            if len(text.strip()) < 20:
                return "", "image-only PDF (no text layer) — needs OCR / visual review"
            return text, f"extracted {len(text)} chars from {d.page_count}p"
        except Exception as e:
            last_err = str(e)
    return "", f"download/extract failed after retries: {last_err}"


# ── ledger I/O ──────────────────────────────────────────────────────────────
def load_ledger() -> dict:
    if os.path.exists(LEDGER):
        with open(LEDGER, encoding="utf-8") as fh:
            return json.load(fh)
    return {"_meta": {"schema": 1, "note": "Persistent filing diligence ledger. "
            "A symbol is STALE while it has an unresolved (material + not reviewed) filing."},
            "filings": []}


def save_ledger(led: dict) -> None:
    led["_meta"]["updated_at"] = dt.datetime.now().isoformat(timespec="seconds")
    with open(LEDGER, "w", encoding="utf-8") as fh:
        json.dump(led, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def universe_syms() -> set:
    with open(UNI_FILE, encoding="utf-8") as fh:
        return {s["ticker"].upper() for s in json.load(fh)["symbols"]}


def stale_symbols(led: dict) -> set:
    """A symbol is STALE if it has any filing that is (MATERIAL or UNKNOWN) and not reviewed."""
    out = set()
    for f in led["filings"]:
        if f.get("reviewed"):
            continue
        if f.get("materiality") in ("MATERIAL", "UNKNOWN"):
            out.add(f["symbol"].upper())
    return out


def filing_key(f: dict) -> tuple:
    return (f["symbol"].upper(), f.get("doc_id") or f.get("title", ""))


# ── commands ────────────────────────────────────────────────────────────────
def cmd_process(date: str, download: bool) -> None:
    mkt_path = os.path.join(MKT_DIR, f"{date}.json")
    if not os.path.exists(mkt_path):
        print(f"no market_data for {date}: {mkt_path}", file=sys.stderr)
        sys.exit(1)
    with open(mkt_path, encoding="utf-8") as fh:
        anns = json.load(fh).get("announcements", [])
    if not isinstance(anns, list):
        print(f"announcements for {date} is not a list (no per-company filings) — nothing to do.")
        return

    led = load_ledger()
    existing = {filing_key(f) for f in led["filings"]}
    uni = universe_syms()
    added = 0
    for a in anns:
        if not isinstance(a, dict):
            continue
        sym = (a.get("symbol") or a.get("ticker") or "").upper()
        if not sym:
            continue
        title = a.get("title", "")
        doc_id = a.get("doc_id") or ""
        url = normalize_pdf_url(a.get("pdf_url") or "", doc_id)
        key = (sym, doc_id or title)
        if key in existing:
            continue
        text, note = ("", "download disabled (--no-download)")
        if download:
            if url:
                text, note = extract_pdf_text(url, sym, doc_id or "noid")
            else:
                note = "no pdf_url and no doc_id in snapshot — cannot fetch"
        materiality, reason = classify(title, text)
        rec = {
            "symbol": sym, "date": date, "doc_id": doc_id, "title": title,
            "pdf_url": url, "text_extracted": bool(text), "in_universe": sym in uni,
            "materiality": materiality, "classify_reason": reason,
            "extract_note": note,
            "reviewed": materiality == "NON_MATERIAL",   # non-material auto-clears
            "review_notes": "auto-cleared (non-material)" if materiality == "NON_MATERIAL" else "",
        }
        led["filings"].append(rec)
        existing.add(key)
        added += 1
        tag = "OK" if rec["reviewed"] else "STALE"
        u = "·univ" if rec["in_universe"] else ""
        print(f"  [{tag}] {sym}{u}: {materiality:12} — {title[:60]}  ({note})")

    save_ledger(led)
    stale = sorted(stale_symbols(led) & uni)
    print(f"\nProcessed {date}: {added} new filing(s). "
          f"Universe symbols currently STALE ({len(stale)}): {', '.join(stale) or 'none'}")

    # ── HARD GATE: never silently move on with unread material PDFs ───────────
    # Any in-universe filing that is MATERIAL/UNKNOWN, unreviewed, and whose PDF
    # text could NOT be extracted (download failed OR image-only) MUST be opened
    # and reviewed visually by the agent. We surface these loudly and exit 2 so
    # the daily pipeline blocks on them instead of skipping (the recurring miss).
    needs_read = [
        f for f in led["filings"]
        if f["date"] == date and f["in_universe"] and not f.get("reviewed")
        and f.get("materiality") in ("MATERIAL", "UNKNOWN")
        and not f.get("text_extracted")
    ]
    if needs_read:
        print("\n" + "=" * 78)
        print(f"⚠  ACTION REQUIRED — {len(needs_read)} material/unknown universe filing(s) "
              f"have NO extracted text.")
        print("   You MUST open each PDF (Read renders image-only PDFs) and then run")
        print("   process_filings.py --review SYM --notes \"...\" to clear or correct it.")
        print("=" * 78)
        for f in needs_read:
            local = os.path.join("data", "filings_cache",
                                 f"{f['symbol']}_{f['doc_id'] or 'noid'}.pdf")
            have = "cached" if os.path.exists(os.path.join(ROOT, local)) else "NOT downloaded"
            print(f"  • {f['symbol']:8} {f['materiality']:9} {have:14} {local}")
            print(f"      title: {f['title'][:70]}")
            print(f"      note : {f.get('extract_note','')}")
            if not f.get("pdf_url"):
                print("      ⚠ no fetchable URL — capture an absolute pdf_url/doc_id in the snapshot.")
        # Exit non-zero so daily_run cannot proceed past this step unnoticed.
        sys.exit(2)


def cmd_review(sym: str, notes: str) -> None:
    led = load_ledger()
    sym = sym.upper()
    hit = [f for f in led["filings"] if f["symbol"].upper() == sym and not f.get("reviewed")]
    if not hit:
        print(f"{sym}: no unresolved filings to review.")
        return
    for f in hit:
        f["reviewed"] = True
        f["review_notes"] = notes or "reviewed (manual)"
        f["reviewed_at"] = dt.date.today().isoformat()
        print(f"  reviewed {sym}: {f['title'][:60]}")
    save_ledger(led)
    print(f"{sym} cleared ({len(hit)} filing(s)).")


def cmd_list_stale() -> None:
    led = load_ledger()
    uni = universe_syms()
    rows = [f for f in led["filings"] if not f.get("reviewed")
            and f.get("materiality") in ("MATERIAL", "UNKNOWN")]
    if not rows:
        print("No unresolved (stale) filings.")
        return
    print(f"Unresolved filings ({len(rows)}):")
    for f in sorted(rows, key=lambda r: (not r["in_universe"], r["symbol"])):
        u = "univ" if f["symbol"].upper() in uni else "  - "
        print(f"  [{u}] {f['symbol']:10} {f['date']}  {f['materiality']:9}  {f['title'][:55]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", help="Process this date's announcements (YYYY-MM-DD)")
    ap.add_argument("--no-download", action="store_true",
                    help="Classify by title only; don't fetch PDFs")
    ap.add_argument("--review", metavar="SYM", help="Mark a symbol's filings reviewed (clears STALE)")
    ap.add_argument("--notes", default="", help="Review notes to record with --review")
    ap.add_argument("--list-stale", action="store_true", help="List currently-stale symbols")
    args = ap.parse_args()

    if args.list_stale:
        cmd_list_stale()
    elif args.review:
        cmd_review(args.review, args.notes)
    elif args.date:
        cmd_process(args.date, download=not args.no_download)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
