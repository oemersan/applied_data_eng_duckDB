"""
End-to-end ETL pipeline: Parquet -> DuckDB (transform) -> PostgreSQL (load).

This is the script that ties DuckDB into the our materials we use in class.
Pipeline:
  1. EXTRACT: read raw Parquet files from data/
  2. TRANSFORM: clean + aggregate using DuckDB SQL
       - drop bad rows (negative fares, zero-distance trips)
       - compute daily metrics per pickup zone
  3. LOAD: write the aggregated table into PostgreSQL via the postgres extension

Run:    python scripts/04_etl_pipeline.py
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import duckdb
from dotenv import load_dotenv

DATA_GLOB = "data/yellow_2024-*.parquet"


def main() -> None:
    if not list(Path("data").glob("yellow_2024-*.parquet")):
        raise SystemExit("No parquet files. Run scripts/00_download_data.sh first.")

    load_dotenv()
    pg_conn_str = (
        f"host={os.environ.get('POSTGRES_HOST','localhost')} "
        f"port={os.environ.get('POSTGRES_PORT','5432')} "
        f"user={os.environ.get('POSTGRES_USER','demo')} "
        f"password={os.environ.get('POSTGRES_PASSWORD','demo')} "
        f"dbname={os.environ.get('POSTGRES_DB','taxi')}"
    )

    con = duckdb.connect()
    con.execute("INSTALL postgres; LOAD postgres;")
    con.execute(f"ATTACH '{pg_conn_str}' AS pg (TYPE POSTGRES)")

    print("=== ETL pipeline: Parquet -> DuckDB -> Postgres ===")
    print()

    # --- TRANSFORM (in DuckDB) ---
    t0 = time.perf_counter()
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE daily_zone_metrics AS
        SELECT
            DATE_TRUNC('day', tpep_pickup_datetime)::DATE AS pickup_date,
            PULocationID,
            COUNT(*)                                       AS trips,
            ROUND(AVG(fare_amount)::NUMERIC, 2)            AS avg_fare,
            ROUND(SUM(total_amount)::NUMERIC, 2)           AS total_revenue,
            ROUND(AVG(trip_distance)::NUMERIC, 2)          AS avg_distance
        FROM '{DATA_GLOB}'
        WHERE fare_amount > 0
          AND trip_distance > 0
          AND tpep_pickup_datetime >= '2024-01-01'
          AND tpep_pickup_datetime <  '2024-04-01'
        GROUP BY pickup_date, PULocationID
    """)
    n_rows = con.execute("SELECT COUNT(*) FROM daily_zone_metrics").fetchone()[0]
    transform_time = time.perf_counter() - t0
    print(f"  TRANSFORM: {n_rows:,} aggregated rows  ({transform_time:.2f} s)")

    # --- LOAD (into Postgres) ---
    t0 = time.perf_counter()
    con.execute("DROP TABLE IF EXISTS pg.daily_zone_metrics")
    con.execute("""
        CREATE TABLE pg.daily_zone_metrics AS
        SELECT * FROM daily_zone_metrics
    """)
    load_time = time.perf_counter() - t0
    print(f"  LOAD:      wrote into Postgres        ({load_time:.2f} s)")

    # --- VERIFY ---
    sample = con.execute("""
        SELECT * FROM pg.daily_zone_metrics
        ORDER BY total_revenue DESC LIMIT 5
    """).fetchall()
    print()
    print("Top 5 (date, zone) by revenue, read back from Postgres:")
    print(f"  {'date':<12} {'zone':>5} {'trips':>7} {'avg_fare':>10} {'revenue':>12}")
    for r in sample:
        print(f"  {str(r[0]):<12} {r[1]:>5} {r[2]:>7} {r[3]:>10} {r[4]:>12}")

    print()
    print(f"Total ETL time: {transform_time + load_time:.2f} s")


if __name__ == "__main__":
    main()
