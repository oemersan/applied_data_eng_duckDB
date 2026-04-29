"""
PostgreSQL vs DuckDB comparison.

This script highlights the BIGGEST practical difference between Postgres and
DuckDB for analytical work on files:

  - Postgres needs the data inside the database first. We measure the cost
    of loading one Parquet file into a Postgres table, then running the query.
  - DuckDB queries the Parquet file directly. No load step.

The point is NOT that Postgres is "bad" — it is brilliant at OLTP. The point
is that for ad-hoc analysis on files, DuckDB skips an entire stage.

Prerequisites:
  - `docker compose up -d` (Postgres running on localhost:5432)
  - `data/yellow_2024-01.parquet` exists (run scripts/00_download_data.sh)
  - `cp .env.example .env` (or export the vars yourself)

Run:    python scripts/03_postgres_compare.py
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import duckdb
import psycopg2
from dotenv import load_dotenv

PARQUET_FILE = "data/yellow_2024-01.parquet"


def time_it(label: str):
    class _T:
        def __enter__(self_):
            self_.t0 = time.perf_counter()
            return self_
        def __exit__(self_, *_):
            self_.elapsed = time.perf_counter() - self_.t0
            print(f"  {label:<45s} {self_.elapsed:7.3f} s")
    return _T()


def get_pg_conn():
    load_dotenv()
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        user=os.environ.get("POSTGRES_USER", "demo"),
        password=os.environ.get("POSTGRES_PASSWORD", "demo"),
        dbname=os.environ.get("POSTGRES_DB", "taxi"),
    )


def main() -> None:
    if not Path(PARQUET_FILE).exists():
        raise SystemExit(f"{PARQUET_FILE} not found. Run scripts/00_download_data.sh first.")

    QUERY_SQL = """
        SELECT PULocationID,
               COUNT(*)          AS trips,
               AVG(fare_amount)  AS avg_fare,
               SUM(total_amount) AS total_revenue
        FROM yellow_taxi
        GROUP BY PULocationID
        ORDER BY total_revenue DESC
        LIMIT 10
    """

    # ---------------- Postgres ----------------
    print("=== PostgreSQL ===")
    pg = get_pg_conn()
    cur = pg.cursor()

    with time_it("1. CREATE TABLE schema") as _:
        cur.execute("DROP TABLE IF EXISTS yellow_taxi")
        cur.execute("""
            CREATE TABLE yellow_taxi (
                VendorID              INTEGER,
                tpep_pickup_datetime  TIMESTAMP,
                tpep_dropoff_datetime TIMESTAMP,
                passenger_count       DOUBLE PRECISION,
                trip_distance         DOUBLE PRECISION,
                RatecodeID            DOUBLE PRECISION,
                store_and_fwd_flag    TEXT,
                PULocationID          INTEGER,
                DOLocationID          INTEGER,
                payment_type          BIGINT,
                fare_amount           DOUBLE PRECISION,
                extra                 DOUBLE PRECISION,
                mta_tax               DOUBLE PRECISION,
                tip_amount            DOUBLE PRECISION,
                tolls_amount          DOUBLE PRECISION,
                improvement_surcharge DOUBLE PRECISION,
                total_amount          DOUBLE PRECISION,
                congestion_surcharge  DOUBLE PRECISION,
                Airport_fee           DOUBLE PRECISION
            )
        """)
        pg.commit()

    # Use DuckDB's postgres extension to load efficiently — this is the fastest
    # honest way to bulk-load a Parquet file into Postgres from Python.
    with time_it("2. Load Parquet into Postgres (via DuckDB)") as t_load:
        d = duckdb.connect()
        d.execute("INSTALL postgres; LOAD postgres;")
        pg_conn_str = (
            f"host={os.environ.get('POSTGRES_HOST','localhost')} "
            f"port={os.environ.get('POSTGRES_PORT','5432')} "
            f"user={os.environ.get('POSTGRES_USER','demo')} "
            f"password={os.environ.get('POSTGRES_PASSWORD','demo')} "
            f"dbname={os.environ.get('POSTGRES_DB','taxi')}"
        )
        d.execute(f"ATTACH '{pg_conn_str}' AS pg (TYPE POSTGRES)")
        d.execute(f"""
            INSERT INTO pg.yellow_taxi
            SELECT * FROM '{PARQUET_FILE}'
        """)
    load_time = t_load.elapsed

    with time_it("3. Run aggregate query") as t_q:
        cur.execute(QUERY_SQL)
        pg_result = cur.fetchall()
    pg_query_time = t_q.elapsed

    pg_total = load_time + pg_query_time
    print(f"  {'POSTGRES TOTAL (load + query)':<45s} {pg_total:7.3f} s")
    cur.close()
    pg.close()

    # ---------------- DuckDB ----------------
    print()
    print("=== DuckDB ===")
    con = duckdb.connect()
    with time_it("1. Query Parquet file directly") as t_d:
        duck_result = con.execute(QUERY_SQL.replace("yellow_taxi", f"'{PARQUET_FILE}'")).fetchall()
    duck_total = t_d.elapsed

    # ---------------- Summary ----------------
    print()
    print("=" * 55)
    print(f"  Postgres (load + query): {pg_total:7.3f} s")
    print(f"  DuckDB (direct query):   {duck_total:7.3f} s")
    if duck_total > 0:
        print(f"  Speedup:                  {pg_total/duck_total:6.1f}x")
    print("=" * 55)
    print()
    print("Note: this is NOT a fair fight. Postgres is paying the cost")
    print("of being a persistent transactional store. DuckDB skips that")
    print("entire stage because it just reads the Parquet file in place.")
    print("That's exactly the point — pick the right tool for the job.")


if __name__ == "__main__":
    main()
