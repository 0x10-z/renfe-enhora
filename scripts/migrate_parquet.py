"""
One-time migration: split monthly parquet files into per-snapshot part files.

Old layout:  data/arrivals/YYYY-MM.parquet  (all snapshots in one file)
New layout:  data/arrivals/YYYY-MM-DD/{snapshot_id}.parquet

Usage:
    python -m scripts.migrate_parquet              # dry run (prints what would happen)
    python -m scripts.migrate_parquet --execute    # actually writes + renames old files
"""
import argparse
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

_DATA_ROOT = Path(__file__).parent.parent / "data"
_TABLES = ["arrivals", "stations"]


def _date_from_snapshot(snapshot_id: str) -> str:
    """Extract YYYY-MM-DD from 'service_2026-04-10T08:19'."""
    # snapshot_id format: {service}_{YYYY-MM-DDTHH:MM}
    # The date portion is always the last segment after the last underscore
    ts_part = snapshot_id.rsplit("_", 1)[-1]  # e.g. "2026-04-10T08:19"
    return ts_part[:10]  # YYYY-MM-DD


def migrate_table(folder: str, src_file: Path, execute: bool) -> dict:
    """Split src_file into per-snapshot part files inside daily directories."""
    print(f"\n{'[DRY RUN] ' if not execute else ''}Migrating {src_file.name} ({src_file.stat().st_size / 1024 / 1024:.1f} MB)")

    table = pq.read_table(src_file)
    snapshot_col = table.column("snapshot_id").to_pylist()
    snapshots = sorted(set(snapshot_col))
    print(f"  {table.num_rows:,} rows -> {len(snapshots)} snapshots")

    written = 0
    skipped = 0
    for snap_id in snapshots:
        date_str = _date_from_snapshot(snap_id)
        safe_id = snap_id.replace(":", "-")
        dest_dir = _DATA_ROOT / folder / date_str
        dest_file = dest_dir / f"{safe_id}.parquet"

        if dest_file.exists():
            skipped += 1
            continue

        if execute:
            dest_dir.mkdir(parents=True, exist_ok=True)
            mask = pa.array([s == snap_id for s in snapshot_col])
            chunk = table.filter(mask)
            pq.write_table(chunk, dest_file, compression="zstd")

        written += 1

    print(f"  Written: {written} | Skipped (already exist): {skipped}")

    if execute and written > 0:
        backup = src_file.with_suffix(".parquet.bak")
        src_file.rename(backup)
        print(f"  Old file renamed to: {backup.name}")

    return {"written": written, "skipped": skipped}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--execute", action="store_true", help="Write files and rename old parquets (default: dry run)")
    args = parser.parse_args()

    execute = args.execute
    if not execute:
        print("DRY RUN — pass --execute to actually write files\n")

    total_written = 0
    for folder in _TABLES:
        src_dir = _DATA_ROOT / folder
        # Find monthly parquets (YYYY-MM.parquet pattern, not daily dirs)
        src_files = [f for f in src_dir.glob("????-??.parquet") if f.is_file()]
        if not src_files:
            print(f"\n{folder}/: no monthly parquets found, skipping")
            continue
        for src_file in sorted(src_files):
            result = migrate_table(folder, src_file, execute)
            total_written += result["written"]

    print(f"\nDone. Total part files {'written' if execute else 'would be written'}: {total_written}")
    if not execute:
        print("Run with --execute to apply changes.")


if __name__ == "__main__":
    main()
