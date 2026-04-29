# DuckDB — YZV 322E Tool Presentation

An in-process analytical (OLAP) SQL database for the "long tail" of data
science: datasets that are too big for Pandas to handle comfortably but too
small to justify spinning up Spark or a data warehouse.

This repository is the working demo for the YZV 322E Applied Data
Engineering individual tool presentation (Spring 2026).

> **Course context.** YZV 322E covers PostgreSQL/pgAdmin as the relational
> store and Python ETL libraries (Pandas) for in-memory transformations.
> DuckDB sits exactly between them: SQL-native like Postgres, in-process
> like Pandas, but column-oriented and vectorized so it stays fast on
> multi-GB datasets that make Pandas struggle.

---

## 1. What is this tool?

DuckDB is an in-process columnar SQL database released in 2019 by Mark
Raasveldt and Hannes Mühleisen at CWI (Amsterdam). Often called "SQLite
for analytics", it runs inside your Python process with zero server setup
and queries Parquet, CSV, and JSON files directly. License: MIT.

## 2. Prerequisites

| Requirement | Tested version |
|---|---|
| OS | Linux (Ubuntu 22.04+) — also works on macOS and WSL2 |
| Python | 3.10 or newer |
| Docker | 24.0+ with the Compose v2 plugin (`docker compose`, not `docker-compose`) |
| `curl` | for downloading the dataset |
| Free disk | ~500 MB for the Parquet files |

DuckDB itself is **not** a service — it is installed as a Python package
(`pip install duckdb`). No daemon, no port, no config file. Postgres
*does* run as a container, but only because we use it as the comparison
baseline.

## 3. Installation

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/<your-username>/duckdb-yzv322e.git
cd duckdb-yzv322e

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy the environment file (Postgres credentials):

```bash
cp .env.example .env
```

Start the Postgres + pgAdmin stack (only needed for scripts 03 and 04):

```bash
docker compose up -d
```

Download three months of NYC Yellow Taxi data (~150 MB, ~10 M rows):

```bash
bash scripts/00_download_data.sh
```

## 4. Running the example

There are four scripts. Run them in order. Each script prints its own
timing breakdown.

```bash
# (1) Pandas baseline — loads everything into memory, then runs queries
python scripts/01_pandas_baseline.py

# (2) Same queries in DuckDB — Parquet is queried in place
python scripts/02_duckdb_demo.py

# (3) Postgres vs DuckDB on the same query
python scripts/03_postgres_compare.py

# (4) Bonus: full ETL pipeline (Parquet -> DuckDB transform -> Postgres load)
python scripts/04_etl_pipeline.py
```

To shut everything down:

```bash
docker compose down -v
```

## 5. Expected output

### `01_pandas_baseline.py`

```
=== Pandas baseline ===
Files: 3
  - data/yellow_2024-01.parquet  (47.7 MB)
  - data/yellow_2024-02.parquet  (47.4 MB)
  - data/yellow_2024-03.parquet  (56.1 MB)

  1. Load 3 parquet files into DataFrame    ~6.0 s
     -> 9,439,xxx rows, ~1500 MB in RAM
  2. GROUP BY PULocationID (top-10 fares)   ~0.7 s
  3. Trips by pickup hour                   ~0.3 s
  4. Tip rate by payment type (fare > $10)  ~0.4 s

  TOTAL                                     ~7.4 s
```

### `02_duckdb_demo.py`

```
=== DuckDB demo ===
DuckDB version: 1.5.2
Files: 3 (queried in place — no load step)

  1. Count rows across all 3 files          ~0.05 s
  2. GROUP BY PULocationID (top-10 fares)   ~0.20 s
  3. Trips by pickup hour                   ~0.15 s
  4. Tip rate by payment type (fare > $10)  ~0.20 s
```

> Numbers depend on the machine. The shape — DuckDB is roughly
> **10-30× faster end-to-end** because it skips the load step and runs
> aggregations multi-threaded over the Parquet file directly — should
> be the same on any modern laptop.

### `03_postgres_compare.py`

```
=== PostgreSQL ===
  1. CREATE TABLE schema                          ~0.02 s
  2. Load Parquet into Postgres (via DuckDB)      ~25.0 s
  3. Run aggregate query                          ~1.5  s
  POSTGRES TOTAL (load + query)                   ~26.5 s

=== DuckDB ===
  1. Query Parquet file directly                  ~0.20 s

=======================================================
  Postgres (load + query):  26.5 s
  DuckDB (direct query):     0.2 s
  Speedup:                  ~130x
=======================================================
```

A screenshot of an actual run is in `results/screenshot.png`.

## 6. Repository layout

```
duckdb-yzv322e/
├── README.md                # this file
├── docker-compose.yml       # Postgres + pgAdmin
├── .env.example             # Postgres credentials template
├── requirements.txt         # Python dependencies
├── data/                    # Parquet files (gitignored)
├── scripts/
│   ├── 00_download_data.sh
│   ├── 01_pandas_baseline.py
│   ├── 02_duckdb_demo.py
│   ├── 03_postgres_compare.py
│   └── 04_etl_pipeline.py
├── notebooks/
│   └── duckdb_walkthrough.ipynb
├── results/
│   └── screenshot.png       # captured during the demo
└── AI_USAGE.md              # AI usage disclosure
```

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `curl` returns 403 / "AccessDenied" | NYC TLC occasionally rate-limits. Wait a minute and re-run `scripts/00_download_data.sh`. |
| `psycopg2.OperationalError: connection refused` | Postgres container is not up yet. Run `docker compose ps`; wait until `postgres` shows `healthy`. |
| `MemoryError` in `01_pandas_baseline.py` | That is partly the point of the demo. Reduce `MONTHS` in `scripts/00_download_data.sh` to a single month, or run the script on a machine with ≥8 GB RAM. |
| `duckdb.IOException: HTTP error` | The `postgres` extension downloads on first use. Make sure outbound HTTPS to `extensions.duckdb.org` is allowed. |

## 8. References

- Official site: https://duckdb.org
- Source: https://github.com/duckdb/duckdb
- Wikipedia: https://en.wikipedia.org/wiki/DuckDB
- v1.5.2 release notes (April 2026): https://duckdb.org/2026/04/13/announcing-duckdb-152
- "DuckDB in Action" book (Manning, free chapter 1): https://motherduck.com/duckdb-book-summary-chapter1/
- Postgres extension: https://duckdb.org/docs/extensions/postgres

## 9. AI usage disclosure

See [`AI_USAGE.md`](AI_USAGE.md).
