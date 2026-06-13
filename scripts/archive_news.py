"""
PSX News Archiver — aggregates macro_news blocks from daily snapshots into a
single append-friendly archive for future E-lens backtesting.

Historical news is unavailable free, so this archive only grows FORWARD from
2026-06-11 (the day the news layer was added). Every day kept compounds.

Input:  data/market_data/YYYY-MM-DD.json  (snapshot "macro_news" arrays)
Output: data/news_archive.jsonl — one JSON object per line, deduped on
        (date, headline), sorted by date then insertion order. Idempotent.

Usage:  python scripts/archive_news.py        # run after each daily pipeline
"""

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAP_DIR = REPO_ROOT / "data" / "market_data"
ARCHIVE = REPO_ROOT / "data" / "news_archive.jsonl"


def main() -> None:
    existing: dict[tuple, dict] = {}
    if ARCHIVE.exists():
        with open(ARCHIVE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                existing[(item.get("date"), item.get("headline"))] = item

    before = len(existing)
    snaps = sorted(SNAP_DIR.glob("????-??-??.json"))
    for snap in snaps:
        with open(snap, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data.get("macro_news", []) or []:
            key = (item.get("date"), item.get("headline"))
            if key not in existing:
                item["_snapshot"] = snap.stem
                existing[key] = item

    items = sorted(existing.values(), key=lambda x: (x.get("date") or "", x.get("headline") or ""))
    with open(ARCHIVE, "w", encoding="utf-8", newline="\n") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"[archive] {len(snaps)} snapshots scanned; {len(items) - before} new items; "
          f"{len(items)} total in {ARCHIVE.name}")


if __name__ == "__main__":
    main()
