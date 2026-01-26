#!/usr/bin/env python3
"""
Find URLs from the original CSV that weren't successfully imported.

Compares the original CSV against the database to find missing recipes.

Usage:
    python scripts/find_missing.py savedrecipelist.csv > failed_urls.csv
"""

import sys
import csv
import sqlite3
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/find_missing.py <original_csv>", file=sys.stderr)
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    db_path = Path("recipes.db")

    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    if not db_path.exists():
        print(f"Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    # Get all imported URLs from database
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT source_url FROM recipes")
    imported_urls = set()
    for row in cursor:
        url = row[0]
        # Normalize URL for comparison
        url = url.replace("https://", "").replace("http://", "")
        url = url.rstrip("/")
        imported_urls.add(url)
    conn.close()

    # Read original CSV and find missing
    missing = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("url", "").strip()
            if not url:
                continue

            # Normalize for comparison
            normalized = url.replace("https://", "").replace("http://", "")
            normalized = normalized.rstrip("/")
            # Also check without query params
            normalized_base = normalized.split("?")[0]

            found = False
            for imported in imported_urls:
                if normalized in imported or normalized_base in imported:
                    found = True
                    break

            if not found:
                missing.append(row)

    # Output missing as CSV
    if missing:
        print(f"# Found {len(missing)} missing URLs", file=sys.stderr)
        writer = csv.DictWriter(sys.stdout, fieldnames=["url", "caption"])
        writer.writeheader()
        for row in missing:
            writer.writerow({
                "url": row.get("url", ""),
                "caption": row.get("caption", ""),
            })
    else:
        print("All URLs imported successfully!", file=sys.stderr)


if __name__ == "__main__":
    main()
