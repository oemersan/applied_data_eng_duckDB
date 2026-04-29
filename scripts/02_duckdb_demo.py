"""
DuckDB benchmark — same three queries as the Pandas baseline.

The crucial difference: DuckDB queries the Parquet files in-place. There is
no separate "load into memory" step. The glob pattern `data/yellow_2024-*.parquet`
is read on the fly, in parallel, using DuckDB's vectorized engine.

Run:    python scripts/02_duckdb_demo.py
"""

from __future__ import annotations

import glob
import time
from pathlib import Path

import duckdb

DATA_GLOB = "data/yellow_2024-*.parquet"


def time_it(label: str):
    class _T:
        def __enter__(self_):
            self_.t0 = time.perf_counter()
            return self_
        def __exit__(self_, *_):
            self_.elapsed = time.perf_counter() - self_.t0
            print(f"  {label:<40s} {self_.elapsed:7.3f} s")
    return _T()


def main() -> None:
    files = sorted(glob.glob(DATA_GLOB))
    if not files:
        raise SystemExit(
            f"No parquet files found matching {DATA_GLOB!r}. "
            "Run scripts/00_download_data.sh first."
        )

    print(f"=== DuckDB demo ===")
    print(f"DuckDB version: {duckdb.__version__}")
    print(f"Files: {len(files)} (queried in place — no load step)")
    for f in files:
        size_mb = Path(f).stat().st_size / 1024 / 1024
        print(f"  - {f}  ({size_mb:.1f} MB)")
    print()

    con = duckdb.connect()  # in-memory database

    # Step 1: row count (forces a full scan, comparable to Pandas "load")
    with time_it("1. Count rows across all 3 files") as t:
        n_rows = con.execute(
            f"SELECT COUNT(*) FROM '{DATA_GLOB}'"
        ).fetchone()[0]
    print(f"     -> {n_rows:,} rows")

    # Step 2: aggregate by pickup location
    with time_it("2. GROUP BY PULocationID (top-10 fares)") as t:
        q1 = con.execute(f"""
            SELECT
                PULocationID,
                COUNT(*)            AS trips,
                AVG(fare_amount)    AS avg_fare,
                SUM(total_amount)   AS total_revenue
            FROM '{DATA_GLOB}'
            GROUP BY PULocationID
            ORDER BY total_revenue DESC
            LIMIT 10
        """).df()

    # Step 3: hourly pattern
    with time_it("3. Trips by pickup hour") as t:
        q2 = con.execute(f"""
            SELECT
                EXTRACT(hour FROM tpep_pickup_datetime) AS pickup_hour,
                COUNT(*) AS trips
            FROM '{DATA_GLOB}'
            GROUP BY pickup_hour
            ORDER BY pickup_hour
        """).df()

    # Step 4: payment-type breakdown
    with time_it("4. Tip rate by payment type (fare > $10)") as t:
        q3 = con.execute(f"""
            SELECT
                payment_type,
                AVG(tip_amount / fare_amount) AS avg_tip_rate
            FROM '{DATA_GLOB}'
            WHERE fare_amount > 10
            GROUP BY payment_type
            ORDER BY payment_type
        """).df()

    print()
    print("Sample result (top-3 pickup zones by revenue):")
    print(q1.head(3).to_string(index=False))


if __name__ == "__main__":
    main()
