#!/usr/bin/env python
"""Fetch raw Uniswap V3 pool event logs + gas history from the BigQuery
public `crypto_ethereum` dataset.

Requires `gcloud auth application-default login` once (Application Default
Credentials) -- the `bq` CLI's own auth is separate and does not cover the
Python client used here.

Usage:
    uv run --active scripts/fetch_data.py --start 2023-06-01 --end 2024-07-31 --dry-run
    uv run --active scripts/fetch_data.py --start 2023-06-01 --end 2024-07-31
"""
import argparse
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

from t1000 import constants

LOGS_QUERY = """
SELECT block_number, block_timestamp, transaction_hash, log_index, topics, data
FROM `bigquery-public-data.crypto_ethereum.logs`
WHERE LOWER(address) = @pool_address
  AND block_timestamp BETWEEN @start_ts AND @end_ts
  AND topics[SAFE_OFFSET(0)] IN UNNEST(@topic0_list)
ORDER BY block_number, log_index
"""

BLOCKS_QUERY = """
SELECT number AS block_number, timestamp AS block_timestamp, base_fee_per_gas
FROM `bigquery-public-data.crypto_ethereum.blocks`
WHERE timestamp BETWEEN @start_ts AND @end_ts
ORDER BY number
"""

NFPM_TX_QUERY = """
SELECT `hash` AS tx_hash, block_number, block_timestamp, receipt_gas_used, gas_price
FROM `bigquery-public-data.crypto_ethereum.transactions`
WHERE LOWER(to_address) = @nfpm_address
  AND block_timestamp BETWEEN @start_ts AND @end_ts
ORDER BY block_number
"""


def _run_query(client: bigquery.Client, query: str, params: list, dry_run: bool = False) -> pd.DataFrame:
    job_config = bigquery.QueryJobConfig(query_parameters=params, dry_run=dry_run)
    job = client.query(query, job_config=job_config)
    if dry_run:
        print(f"  [dry-run] estimated bytes processed: {job.total_bytes_processed:,}")
        return pd.DataFrame()
    return job.result().to_dataframe(create_bqstorage_client=False)


def fetch_logs(client, start_date, end_date, dry_run=False) -> pd.DataFrame:
    params = [
        bigquery.ScalarQueryParameter("pool_address", "STRING", constants.POOL_ADDRESS.lower()),
        bigquery.ScalarQueryParameter("start_ts", "TIMESTAMP", start_date),
        bigquery.ScalarQueryParameter("end_ts", "TIMESTAMP", end_date),
        bigquery.ArrayQueryParameter("topic0_list", "STRING", list(constants.TOPIC0.values())),
    ]
    return _run_query(client, LOGS_QUERY, params, dry_run=dry_run)


def fetch_blocks(client, start_date, end_date, dry_run=False) -> pd.DataFrame:
    params = [
        bigquery.ScalarQueryParameter("start_ts", "TIMESTAMP", start_date),
        bigquery.ScalarQueryParameter("end_ts", "TIMESTAMP", end_date),
    ]
    return _run_query(client, BLOCKS_QUERY, params, dry_run=dry_run)


def fetch_nfpm_transactions(client, start_date, end_date, dry_run=False) -> pd.DataFrame:
    params = [
        bigquery.ScalarQueryParameter("nfpm_address", "STRING", constants.NFPM_ADDRESS.lower()),
        bigquery.ScalarQueryParameter("start_ts", "TIMESTAMP", start_date),
        bigquery.ScalarQueryParameter("end_ts", "TIMESTAMP", end_date),
    ]
    return _run_query(client, NFPM_TX_QUERY, params, dry_run=dry_run)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--out-dir", default="data/raw")
    parser.add_argument("--project", default="uniswap-rl")
    parser.add_argument("--dry-run", action="store_true", help="print estimated bytes scanned, fetch nothing")
    args = parser.parse_args()

    client = bigquery.Client(project=args.project)
    out_dir = Path(args.out_dir)

    print(f"Pool: {constants.POOL_ADDRESS}  window: {args.start} -> {args.end}")

    print("Logs query:")
    logs_df = fetch_logs(client, args.start, args.end, dry_run=args.dry_run)
    print("Blocks query:")
    blocks_df = fetch_blocks(client, args.start, args.end, dry_run=args.dry_run)
    print("NFPM transactions query:")
    nfpm_df = fetch_nfpm_transactions(client, args.start, args.end, dry_run=args.dry_run)

    if args.dry_run:
        print("Dry run only -- nothing written. Re-run without --dry-run to fetch.")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    logs_df.to_parquet(out_dir / "logs.parquet", index=False)
    print(f"Saved {len(logs_df):,} log rows -> {out_dir / 'logs.parquet'}")

    blocks_df.to_parquet(out_dir / "blocks.parquet", index=False)
    print(f"Saved {len(blocks_df):,} block rows -> {out_dir / 'blocks.parquet'}")

    nfpm_df.to_parquet(out_dir / "nfpm_transactions.parquet", index=False)
    print(f"Saved {len(nfpm_df):,} NFPM tx rows -> {out_dir / 'nfpm_transactions.parquet'}")


if __name__ == "__main__":
    main()
