#!/usr/bin/env python
"""Fetch historical ETHUSDT perpetual funding rates from Binance's public
(no-auth) Futures API, for the delta-hedge feature (see TODO.md P1).

Usage:
    uv run --active scripts/fetch_funding.py --start 2024-05-01 --end 2025-06-01
"""
import argparse
import time
from pathlib import Path

import pandas as pd
import requests

FUNDING_RATE_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
SYMBOL = "ETHUSDT"
PAGE_LIMIT = 1000


def fetch_funding_rates(start_ms: int, end_ms: int) -> pd.DataFrame:
    rows = []
    cursor = start_ms
    while cursor < end_ms:
        resp = requests.get(
            FUNDING_RATE_URL,
            params={"symbol": SYMBOL, "startTime": cursor, "endTime": end_ms, "limit": PAGE_LIMIT},
            timeout=30,
        )
        resp.raise_for_status()
        page = resp.json()
        if not page:
            break
        rows.extend(page)
        cursor = page[-1]["fundingTime"] + 1
        if len(page) < PAGE_LIMIT:
            break
        time.sleep(0.2)  # stay well under Binance's public rate limit

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["timestamp", "funding_rate"])
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(df["fundingTime"], unit="ms", utc=True),
            "funding_rate": df["fundingRate"].astype(float),
        }
    ).drop_duplicates(subset="timestamp").sort_values("timestamp").reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--out-dir", default="data/raw")
    args = parser.parse_args()

    start_ms = int(pd.Timestamp(args.start, tz="UTC").timestamp() * 1000)
    end_ms = int(pd.Timestamp(args.end, tz="UTC").timestamp() * 1000)

    print(f"Symbol: {SYMBOL}  window: {args.start} -> {args.end}")
    funding_df = fetch_funding_rates(start_ms, end_ms)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "funding_rate.parquet"
    funding_df.to_parquet(out_path, index=False)
    print(f"Saved {len(funding_df):,} funding-rate rows -> {out_path}")
    if not funding_df.empty:
        print(f"  coverage: {funding_df['timestamp'].min()} -> {funding_df['timestamp'].max()}")


if __name__ == "__main__":
    main()
