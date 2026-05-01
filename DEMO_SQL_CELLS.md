# DuckDB UI Demo — SQL Cells

- Cell 1: setup (one-time)
- Cell 2: count rows (the "2 ms wow")
- Cell 3: real analytical query (top zones)
- Cell 4: hourly pattern
- Cell 5: tip rate breakdown
- Cell 6: the "compare with Pandas" point (run the same query)
- Cell 7: connect to Postgres + ETL pipeline (the live integration moment)
- Cell 8: read back from Postgres to prove it landed

---

## CELL 1 — Setup

```sql
-- Create a view over the 3 Parquet files. No copy, no load — just a pointer.
CREATE OR REPLACE VIEW yellow_taxi AS
SELECT * FROM 'data/yellow_2024-*.parquet';

-- Quick sanity check
SELECT COUNT(*) AS total_rows FROM yellow_taxi;
```

---

## CELL 2

```sql
-- Row count across 3 Parquet files. This only reads metadata.
SELECT COUNT(*) AS total_rows FROM yellow_taxi;
```

---

## CELL 3 — Real analytical query (top pickup zones by revenue)

```sql
-- The classic "top-N by total" aggregation
SELECT
    PULocationID,
    COUNT(*)                              AS trips,
    ROUND(AVG(fare_amount)::NUMERIC, 2)   AS avg_fare,
    ROUND(SUM(total_amount)::NUMERIC, 2)  AS total_revenue
FROM yellow_taxi
GROUP BY PULocationID
ORDER BY total_revenue DESC
LIMIT 10;
```

---

## CELL 4 — Hourly pattern 

```sql
-- Trip count by hour of day. Try the chart icon after running this!
SELECT
    EXTRACT(hour FROM tpep_pickup_datetime) AS pickup_hour,
    COUNT(*) AS trips
FROM yellow_taxi
GROUP BY pickup_hour
ORDER BY pickup_hour;
```

---

## CELL 5 — Filtered aggregation (tip behavior)

```sql
-- Average tip rate, split by payment type, only on real fares
SELECT
    payment_type,
    COUNT(*)                                          AS trips,
    ROUND(AVG(tip_amount / fare_amount)::NUMERIC, 4)  AS avg_tip_rate
FROM yellow_taxi
WHERE fare_amount > 10
GROUP BY payment_type
ORDER BY payment_type;
```

---

## CELL 6 — Same query, but show Pandas RAM use first


```bash
python scripts/01_pandas_baseline.py
```

---

## CELL 7 — Live ETL: DuckDB → PostgreSQL

It connects DuckDB to Postgres and writes
aggregated results into a real table.

```sql
-- Install + load the postgres extension (one-time per session)
INSTALL postgres;
LOAD postgres;

-- Attach the running Postgres container as a database
ATTACH 'host=localhost port=5433 user=demo password=demo dbname=taxi'
  AS pg (TYPE POSTGRES);

-- Build the aggregated table inside Postgres, sourced from Parquet
CREATE OR REPLACE TABLE pg.daily_zone_metrics AS
SELECT
    DATE_TRUNC('day', tpep_pickup_datetime)::DATE  AS pickup_date,
    PULocationID                                    AS zone_id,
    COUNT(*)                                        AS trips,
    ROUND(AVG(fare_amount)::NUMERIC, 2)             AS avg_fare,
    ROUND(SUM(total_amount)::NUMERIC, 2)            AS total_revenue
FROM yellow_taxi
WHERE fare_amount > 0 AND trip_distance > 0
GROUP BY pickup_date, zone_id;

-- Verify the row count of the new Postgres table
SELECT COUNT(*) AS rows_in_postgres FROM pg.daily_zone_metrics;
```


---

## CELL 8 — 

```sql
-- Read top zones from the Postgres table we just wrote
SELECT
    zone_id,
    SUM(trips)         AS total_trips,
    SUM(total_revenue) AS revenue
FROM pg.daily_zone_metrics
GROUP BY zone_id
ORDER BY revenue DESC
LIMIT 5;
```

---

## Cleanup

```sql
-- Drop the table we created in Postgres
DROP TABLE IF EXISTS pg.daily_zone_metrics;

-- Detach Postgres
DETACH pg;
```

Or in terminal:
```bash
docker compose down -v
```

---
