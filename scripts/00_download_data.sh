#!/usr/bin/env bash
# Downloads 3 months of NYC TLC Yellow Taxi trip data in Parquet format.
# Source: NYC Taxi & Limousine Commission public data
# https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
#
# Total size: ~150 MB compressed Parquet, ~10 million rows.
# This is enough to make Pandas slow but DuckDB still snappy.

set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p data

BASE_URL="https://d37ci6vzurychx.cloudfront.net/trip-data"
MONTHS=("2024-01" "2024-02" "2024-03")

echo "Downloading NYC Yellow Taxi trip data (3 months)..."
for m in "${MONTHS[@]}"; do
  out="data/yellow_${m}.parquet"
  if [[ -f "$out" ]]; then
    echo "  [skip] $out already exists"
    continue
  fi
  url="${BASE_URL}/yellow_tripdata_${m}.parquet"
  echo "  [get ] $url"
  curl -fSL --retry 3 -o "$out" "$url"
done

echo
echo "Done. Files in data/:"
ls -lh data/*.parquet
