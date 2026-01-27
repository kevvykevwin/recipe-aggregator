#!/usr/bin/env python3
"""
Batch ingest CSV with progress tracking.

Splits the CSV into batches to avoid overwhelming the API.

Usage:
    python scripts/batch_ingest.py savedrecipelist.csv
"""

import sys
import csv
import time
import httpx
from pathlib import Path


API_URL = "http://localhost:8000/api/ingest/csv"
BATCH_SIZE = 5  # rows per batch (smaller to avoid rate limits)
BATCH_DELAY = 120  # seconds between batches (2 minutes)


def split_csv(filepath: Path, batch_size: int):
    """Split CSV into batches, yielding (batch_num, csv_content)."""
    with open(filepath, "r", encoding="utf-8-sig") as f:  # handle BOM
        reader = csv.DictReader(f)
        fieldnames = [f for f in reader.fieldnames if f is not None]

        batch = []
        batch_num = 1

        for row in reader:
            batch.append(row)

            if len(batch) >= batch_size:
                yield batch_num, fieldnames, batch
                batch = []
                batch_num += 1

        # Yield remaining rows
        if batch:
            yield batch_num, fieldnames, batch


def batch_to_csv(fieldnames: list, rows: list) -> str:
    """Convert batch of rows to CSV string."""
    import io
    # Filter out None from fieldnames
    fieldnames = [f for f in fieldnames if f is not None]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    # Clean rows - remove None keys
    clean_rows = [{k: v for k, v in row.items() if k is not None} for row in rows]
    writer.writerows(clean_rows)
    return output.getvalue()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/batch_ingest.py <csv_file>")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    # Count total rows
    with open(filepath, "r") as f:
        total_rows = sum(1 for _ in f) - 1  # exclude header

    print(f"CSV: {filepath}")
    print(f"Total rows: {total_rows}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Estimated batches: {(total_rows // BATCH_SIZE) + 1}")
    print()

    total_success = 0
    total_failed = 0

    for batch_num, fieldnames, rows in split_csv(filepath, BATCH_SIZE):
        csv_content = batch_to_csv(fieldnames, rows)

        print(f"Batch {batch_num}: Processing {len(rows)} rows...", end=" ", flush=True)

        try:
            with httpx.Client(timeout=1800.0) as client:  # 30 min timeout
                response = client.post(
                    API_URL,
                    files={"file": ("batch.csv", csv_content, "text/csv")}
                )

                if response.status_code == 200:
                    data = response.json()
                    msg = data.get("message", "")
                    print(f"Done - {msg}")

                    # Parse success/fail counts from message
                    if "extracted" in msg:
                        parts = msg.split(":")[-1].strip()
                        for part in parts.split(","):
                            if "extracted" in part:
                                total_success += int(part.split()[0])
                            elif "failed" in part:
                                total_failed += int(part.split()[0])
                else:
                    print(f"Error: {response.status_code} - {response.text}")
                    total_failed += len(rows)

        except Exception as e:
            print(f"Error: {e}")
            total_failed += len(rows)

        # Delay between batches
        print(f"   Waiting {BATCH_DELAY}s before next batch...")
        time.sleep(BATCH_DELAY)

    print()
    print("=" * 40)
    print(f"Complete!")
    print(f"  Extracted: {total_success}")
    print(f"  Failed: {total_failed}")


if __name__ == "__main__":
    main()
