#!/usr/bin/env python
r"""
parse_announcements.py — turn raw PSX announcement rows into snapshot-ready filings.

WHY THIS EXISTS
---------------
The daily snapshot (data/market_data/<date>.json) used to be hand-assembled by the
agent after scraping dps.psx.com.pk. That manual step kept losing the PDF link, so
process_filings.py could not fetch the document and material filings slipped through
un-read (FABL 2026-06-30: link was /download/ATTACHMENT/... while the scrape only
looked for /download/document/...; the href came back null and the filing was never
opened). This script removes the human from the URL-building loop.

THE FIX
-------
PSX serves a filing's file under one of:
    /download/document/<id>.pdf       (most company disclosures)
    /download/attachment/<id>.pdf     (some disclosures, incl. capital actions)  <-- was missed
    data-images="<id>.gif"            (image-only filings, rendered client side)
All three are normalized here to an ABSOLUTE https URL. The agent only has to dump
raw rows; the link logic lives in one tested place.

HOW THE AGENT USES IT (daily_run Step 1)
----------------------------------------
1. Navigate Playwright MCP to https://dps.psx.com.pk/announcements/companies
2. Run this browser_evaluate snippet (capture EVERY link/img, not a single selector):

     () => Array.from(
       (document.querySelector('#announcementsTable')||document.querySelector('table'))
         .querySelectorAll('tbody tr'))
       .map(tr => { const td=tr.querySelectorAll('td'); if(td.length<5) return null;
         const a=tr.querySelector('a[href*="download"]');
         const img=tr.querySelector('[data-images]');
         return { date: td[0].innerText.trim(), symbol: td[2].innerText.trim(),
                  title: td[4].innerText.trim(),
                  href: a ? a.getAttribute('href') : null,
                  data_images: img ? img.getAttribute('data-images') : null }; })
       .filter(Boolean)

3. Save that array to a temp json and run:
     python scripts/parse_announcements.py --raw <rows.json> --date <YYYY-MM-DD> \
            --merge data/market_data/<YYYY-MM-DD>.json
   It writes the `announcements` list (absolute URLs, universe-flagged) into the snapshot.

This guarantees the link is captured for every filing type, so process_filings.py
(which now also has its own normalize_pdf_url defense-in-depth) can always fetch.
"""
import argparse, json, os, sys

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNI_FILE = os.path.join(ROOT, "data", "universe.json")
PSX_BASE = "https://dps.psx.com.pk"


def universe_syms() -> set:
    with open(UNI_FILE, encoding="utf-8") as fh:
        return {s["ticker"].upper() for s in json.load(fh)["symbols"]}


def build_url(href: str | None, data_images: str | None) -> tuple[str, str]:
    """Return (absolute_url, doc_id) from a row's href or data-images.

    Handles /download/document/, /download/attachment/, and data-images=*.gif.
    """
    href = (href or "").strip()
    if href:
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = PSX_BASE + href
        elif href.startswith("http://"):
            href = "https://" + href[len("http://"):]
        elif not href.startswith("https://"):
            href = f"{PSX_BASE}/{href.lstrip('/')}"
        # doc id = filename stem (e.g. 279282-1 from /download/attachment/279282-1.pdf)
        doc_id = os.path.splitext(os.path.basename(href))[0]
        return href, doc_id
    if data_images:                                   # image-only filing
        img = data_images.strip()
        doc_id = os.path.splitext(os.path.basename(img))[0]
        return f"{PSX_BASE}/download/attachment/{img}", doc_id
    return "", ""


def parse_rows(rows: list, date: str, universe_only: bool) -> list:
    uni = universe_syms()
    out = []
    for r in rows:
        sym = (r.get("symbol") or "").upper()
        if not sym:
            continue
        in_uni = sym in uni
        if universe_only and not in_uni:
            continue
        url, doc_id = build_url(r.get("href"), r.get("data_images"))
        out.append({
            "symbol": sym,
            "title": r.get("title", "").strip(),
            "doc_id": doc_id or None,
            "pdf_url": url or None,
            "in_universe": in_uni,
        })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", required=True, help="JSON file of raw rows from browser_evaluate")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--merge", help="Snapshot json to write the announcements[] into "
                                    "(created if missing; index fields preserved if present)")
    ap.add_argument("--all", action="store_true",
                    help="Keep non-universe filings too (default: universe only)")
    args = ap.parse_args()

    with open(args.raw, encoding="utf-8") as fh:
        rows = json.load(fh)
    anns = parse_rows(rows, args.date, universe_only=not args.all)

    # report (and loudly flag any row that produced no fetchable url)
    missing = [a for a in anns if not a["pdf_url"]]
    print(f"parsed {len(rows)} raw rows -> {len(anns)} filings "
          f"({'universe-only' if not args.all else 'all'}); {len(missing)} with NO url")
    for a in anns:
        flag = "  ⚠ NO URL" if not a["pdf_url"] else ""
        print(f"  {a['symbol']:10} doc={str(a['doc_id']):12} {a['title'][:55]}{flag}")

    if args.merge:
        snap = {}
        if os.path.exists(args.merge):
            with open(args.merge, encoding="utf-8") as fh:
                snap = json.load(fh)
        snap.setdefault("date", args.date)
        snap["announcements"] = anns
        with open(args.merge, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print(f"wrote announcements[] into {args.merge}")

    if missing:
        sys.exit(2)   # block the pipeline: a filing with no url cannot be diligence-checked


if __name__ == "__main__":
    main()
