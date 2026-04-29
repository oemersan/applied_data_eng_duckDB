"""
Pandas baseline benchmark.

Loads 3 months of NYC Yellow Taxi data into a Pandas DataFrame and runs three
analytical queries on it. Measures wall-clock time for each step.

Run:    python scripts/01_pandas_baseline.py
"""

from __future__ import annotations

import glob
import time
from pathlib import Path

import pandas as pd

DATA_GLOB = "data/yellow_2024-*.parquet"


def time_it(label: str):
    """Context-manager-style timer."""
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

    print(f"=== Pandas baseline ===")
    print(f"Files: {len(files)}")
    for f in files:
        size_mb = Path(f).stat().st_size / 1024 / 1024
        print(f"  - {f}  ({size_mb:.1f} MB)")
    print()

    # Step 1: load all files
    with time_it("1. Load 3 parquet files into DataFrame") as t:
        df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    load_time = t.elapsed
    print(f"     -> {len(df):,} rows, {df.memory_usage(deep=True).sum()/1024/1024:.1f} MB in RAM")

    # Step 2: aggregate by pickup location
    with time_it("2. GROUP BY PULocationID (top-10 fares)") as t:
        q1 = (
            df.groupby("PULocationID")
              .agg(trips=("fare_amount", "count"),
                   avg_fare=("fare_amount", "mean"),
                   total_revenue=("total_amount", "sum"))
              .sort_values("total_revenue", ascending=False)
              .head(10)
        )
    q1_time = t.elapsed

    # Step 3: hourly trip pattern
    with time_it("3. Trips by pickup hour") as t:
        df["pickup_hour"] = df["tpep_pickup_datetime"].dt.hour
        q2 = df.groupby("pickup_hour").size().reset_index(name="trips")
    q2_time = t.elapsed

    # Step 4: payment-type breakdown with filter
    with time_it("4. Tip rate by payment type (fare > $10)") as t:
        q3 = (
            df[df["fare_amount"] > 10]
              .assign(tip_rate=lambda d: d["tip_amount"] / d["fare_amount"])
              .groupby("payment_type")["tip_rate"]
              .mean()
              .reset_index()
        )
    q3_time = t.elapsed

    total = load_time + q1_time + q2_time + q3_time
    print()
    print(f"  {'TOTAL':<40s} {total:7.3f} s")
    print()
    print("Sample result (top-3 pickup zones by revenue):")
    print(q1.head(3).to_string())


if __name__ == "__main__":
    main()
