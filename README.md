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

📺 **Video presentation:** [link will be added after upload — see `video_link.txt`](./video_link.txt)

---

## 1. What is this tool?

DuckDB is an in-process columnar SQL database released in 2019 by Mark
Raasveldt and Hannes Mühleisen at CWI (Amsterdam). Often called "SQLite
for analytics", it runs inside your Python process — or its own browser
notebook UI — with zero server setup and queries Parquet, CSV, and JSON
files directly. License: MIT. Current version: 1.5.2 (April 2026).

## 2. Prerequisites

| Requirement | Tested version |
|---|---|
| OS | Linux (Ubuntu 22.04+) — also works on macOS and WSL2 |
| Python | 3.10 or newer |
| Docker | 24.0+ with the Compose v2 plugin (`docker compose`, not `docker-compose`) |
| `curl` | for downloading the dataset and the DuckDB CLI |
| Free disk | ~500 MB for the Parquet files |

DuckDB itself is **not** a service. It comes in two forms, both used here:

- **Python package** (`pip install duckdb`) — used by the benchmark scripts
- **CLI binary** (`curl https://install.duckdb.org | sh`) — used to launch
  the official browser UI with `duckdb -ui`

PostgreSQL runs as a container, used as the comparison baseline and as
the destination of the ETL demo.

## 3. Installation

Clone the repository and create a Python virtual environment:

```bash
git clone https://github.com/<your-username>/duckdb-yzv322e.git
cd duckdb-yzv322e

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install the DuckDB CLI (separate from the Python package — needed for the UI):

```bash
curl https://install.duckdb.org | sh
# Restart the shell or `source ~/.bashrc`, then verify:
duckdb --version    # expect: v1.5.2
```

Copy the environment file (Postgres credentials):

```bash
cp .env.example .env
```

> **Port conflict?** If your machine already runs PostgreSQL on 5432
> (`sudo ss -ltnp | grep 5432` shows a process), edit `.env` and change
> `POSTGRES_PORT=5432` to `POSTGRES_PORT=5433`. Both the scripts and
> the SQL cells in `DEMO_SQL_CELLS.md` pick up the value automatically.

Start the Postgres + pgAdmin stack:

```bash
docker compose up -d
docker compose ps      # wait until postgres shows (healthy)
```

Download three months of NYC Yellow Taxi data (~150 MB, ~9.5 M rows):

```bash
bash scripts/00_download_data.sh
```

## 4. Running the example

There are two ways to run the demo: through the **DuckDB UI** (interactive,
visual — the version shown in the recorded presentation) or through the
**Python benchmark scripts** (reproducible, headline numbers).

### 4a. The interactive UI demo

```bash
duckdb demo.duckdb -ui     # opens http://localhost:4213 in your browser
```

Then open [`DEMO_SQL_CELLS.md`](./DEMO_SQL_CELLS.md) and paste each cell
into the DuckDB UI notebook in order. The cells cover:

1. Setup: a view over the 3 Parquet files
2. Row count of 9.5 M rows in milliseconds
3. Top pickup zones by revenue
4. Trips by hour of day (with the Column Explorer panel)
5. Tip-rate insight by payment type
6. Pandas comparison handoff
7. **Live ETL into Postgres** (the headline moment — refresh pgAdmin to see the new table)
8. Read back from Postgres

For the Postgres side, open pgAdmin in a second browser tab at
[`http://localhost:5050`](http://localhost:5050) (login: `admin@example.com` / `admin`).

### 4b. The reproducible benchmark scripts

These produce the speedup numbers shown on the presentation slides
(6× vs Pandas, 363× vs Postgres). Run them in order; each prints its own
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

The numbers below are from a real run on Ubuntu 22.04, Python 3.10,
DuckDB 1.5.2, with the 3-month NYC Yellow Taxi 2024 Q1 dataset
(9,554,778 rows). Your numbers will differ depending on your machine,
but the **shape** of the comparison should hold. Captured outputs of
the runs that produced these numbers live in [`results/`](./results/).

### `01_pandas_baseline.py`

```
=== Pandas baseline ===
Files: 3
  - data/yellow_2024-01.parquet  (47.6 MB)
  - data/yellow_2024-02.parquet  (48.0 MB)
  - data/yellow_2024-03.parquet  (57.3 MB)

  1. Load 3 parquet files into DataFrame     0.875 s
     -> 9,554,778 rows, 1639.8 MB in RAM
  2. GROUP BY PULocationID (top-10 fares)    0.161 s
  3. Trips by pickup hour                    0.193 s
  4. Tip rate by payment type (fare > $10)   1.007 s

  TOTAL                                      2.236 s
```

Note the **1.6 GB of RAM** consumed: 150 MB of compressed Parquet
expands to roughly 10× that size once Pandas decodes everything into
NumPy arrays. On a laptop with 8 GB RAM this is already painful;
double the dataset and Pandas swaps or crashes.

### `02_duckdb_demo.py`

```
=== DuckDB demo ===
DuckDB version: 1.5.2
Files: 3 (queried in place — no load step)

  1. Count rows across all 3 files           0.002 s
     -> 9,554,778 rows
  2. GROUP BY PULocationID (top-10 fares)    0.282 s
  3. Trips by pickup hour                    0.038 s
  4. Tip rate by payment type (fare > $10)   0.030 s
```

Two things stand out. First, the row count finishes in **2 ms** — DuckDB
reads only the Parquet metadata, no data scan. Second, total query work
is ~0.35 s vs Pandas' 2.24 s, but with **zero RAM blow-up** because
DuckDB streams data through its vectorized engine instead of
materialising the whole DataFrame.

> **Note on UI vs script timings.** The DuckDB UI runs queries through
> a local HTTP server, which adds ~50–100 ms of overhead per query
> (browser → server → result serialization → render). The scripts call
> DuckDB in-process and so report the raw engine time. Both numbers are
> correct measurements of different things.

### `03_postgres_compare.py`

```
=== PostgreSQL ===
  1. CREATE TABLE schema                          0.008 s
  2. Load Parquet into Postgres (via DuckDB)      6.147 s
  3. Run aggregate query                          0.237 s
  POSTGRES TOTAL (load + query)                   6.383 s

=== DuckDB ===
  1. Query Parquet file directly                  0.018 s

=======================================================
  Postgres (load + query):  6.383 s
  DuckDB (direct query):    0.018 s
  Speedup:                  363.7x
=======================================================
```

This is the headline number. **DuckDB is ~360× faster end-to-end** for
ad-hoc analysis on a Parquet file because it skips the load step
entirely. Postgres is excellent at what it does — persistent OLTP — but
that strength becomes a tax when all you want is to scan a file once.

### `04_etl_pipeline.py`

```
=== ETL pipeline: Parquet -> DuckDB -> Postgres ===

  TRANSFORM: 20,351 aggregated rows  (0.13 s)
  LOAD:      wrote into Postgres     (0.03 s)

Top 5 (date, zone) by revenue, read back from Postgres:
  date          zone   trips   avg_fare      revenue
  2024-01-02     132    6336      63.89    523119.50
  2024-03-24     132    6139      65.34    515437.42
  ...

Total ETL time: 0.16 s
```

A real pipeline shape: 9.5 M raw rows reduced to 20 K daily-zone
aggregates, then loaded into Postgres for downstream consumption.
DuckDB does the heavy lifting (the SQL `GROUP BY`), Postgres stores the
final, much smaller result set. This is exactly the place DuckDB fits
in the YZV 322E course: a fast transform engine sitting between
ingestion and the relational store.

## 6. Repository layout

```
duckdb-yzv322e/
├── README.md                # this file
├── DEMO_SQL_CELLS.md        # SQL cells for the recorded UI demo
├── docker-compose.yml       # Postgres + pgAdmin
├── .env.example             # Postgres credentials template
├── requirements.txt         # Python dependencies
├── video_link.txt           # YouTube link (unlisted) of the recorded presentation
├── data/                    # Parquet files — populated by the download script (gitignored)
├── scripts/
│   ├── 00_download_data.sh
│   ├── 01_pandas_baseline.py
│   ├── 02_duckdb_demo.py
│   ├── 03_postgres_compare.py
│   └── 04_etl_pipeline.py
├── notebooks/
│   └── duckdb_walkthrough.ipynb   # Jupyter version, alternative to the UI
├── results/
│   ├── 01_pandas.txt        # captured output from a real run
│   ├── 02_duckdb.txt
│   ├── 03_compare.txt
│   ├── 04_etl.txt
│   └── screenshot.png
└── AI_USAGE.md              # AI usage disclosure
```

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `address already in use` on `docker compose up` | Local Postgres is using 5432. Edit `.env`, set `POSTGRES_PORT=5433`, then `docker compose up -d` again. |
| `duckdb: command not found` | The DuckDB CLI is not on your `PATH`. Run `source ~/.bashrc` after the install script, or restart the terminal. |
| `curl` returns 403 / "AccessDenied" | NYC TLC occasionally rate-limits. Wait a minute and re-run `scripts/00_download_data.sh`. |
| `psycopg2.OperationalError: connection refused` | Postgres container is not up yet. Run `docker compose ps`; wait until `postgres` shows `healthy`. |
| `MemoryError` in `01_pandas_baseline.py` | Reduce `MONTHS` in `scripts/00_download_data.sh` to a single month, or run on a machine with ≥8 GB RAM. |
| `duckdb.IOException: HTTP error` on `INSTALL postgres` | The `postgres` extension downloads on first use. Make sure outbound HTTPS to `extensions.duckdb.org` is allowed. |
| `pip install psycopg2-binary` fails to build | `sudo apt install -y libpq-dev` then retry. |
| pgAdmin doesn't show the new table after Cell 7 | Right-click on `taxi` database in the left panel → **Refresh**, then expand `Schemas → public → Tables`. |

## 8. References

- Official site: https://duckdb.org
- Source: https://github.com/duckdb/duckdb
- DuckDB UI announcement (March 2025): https://duckdb.org/2025/03/12/duckdb-ui
- Wikipedia: https://en.wikipedia.org/wiki/DuckDB
- v1.5.2 release notes (April 2026): https://duckdb.org/2026/04/13/announcing-duckdb-152
- "DuckDB in Action" book (Manning, free chapter 1): https://motherduck.com/duckdb-book-summary-chapter1/
- Postgres extension: https://duckdb.org/docs/extensions/postgres

## 9. AI usage disclosure

See [`AI_USAGE.md`](AI_USAGE.md) for the full disclosure with
task-by-task breakdown.
