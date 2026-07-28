#!/usr/bin/env python
"""Hard preconditions for the experiment sweep.

Every launcher must call check_all() (or run this file) BEFORE anything
trains. A previous run was silently wasted on a 2-month dataset slice because
nothing asserted coverage up front; this module exists so that mistake fails
loudly instead of burning hours of compute.

Usage:
    python experiments/preconditions.py --processed-dir data/processed_14mo_fixed
"""
import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

# 14 months at 30 days/month; the reference dataset (2024-05-01 -> 2025-06-30)
# spans 425 days, the bad 2-month slice spans 60 -- any threshold in between
# separates them, 420 keeps the semantic "14 months" honest.
MIN_DATASET_DAYS = 420

# Paths that must never be committable; probed via `git check-ignore` so the
# check validates the actual ignore rules, not a string match on .gitignore.
GITIGNORE_PROBES = [
    "data/raw_probe/x.parquet",
    "data/processed_probe/x.parquet",
    "data/raw_14mo/x.parquet",
    "data/processed_14mo_fixed/x.parquet",
]


class PreconditionError(RuntimeError):
    pass


def check_dataset_coverage(processed_dir, min_days: int = MIN_DATASET_DAYS) -> pd.Timedelta:
    processed_dir = Path(processed_dir)
    events_path = processed_dir / "raw_events.parquet"
    if not events_path.exists():
        raise PreconditionError(f"no processed dataset at {events_path}")
    ts = pq.read_table(events_path, columns=["timestamp"]).column("timestamp").to_pandas()
    span = ts.max() - ts.min()
    if span < pd.Timedelta(days=min_days):
        raise PreconditionError(
            f"dataset {processed_dir} covers only {span.days} days "
            f"({ts.min().date()} -> {ts.max().date()}); need >= {min_days} days "
            "(~14 months). Refusing to train on a truncated slice -- point "
            "--processed-dir at the full dataset (e.g. data/processed_14mo_fixed) "
            "or rebuild it with scripts/build_dataset.py --raw-dir data/raw_14mo."
        )
    return span


def check_gitignore_covers_data(repo_root) -> None:
    for probe in GITIGNORE_PROBES:
        rc = subprocess.run(
            ["git", "-C", str(repo_root), "check-ignore", "-q", probe],
        ).returncode
        if rc != 0:
            raise PreconditionError(
                f".gitignore does not ignore {probe!r} -- dataset files could be "
                "committed. Fix .gitignore before launching the sweep."
            )


def check_all(processed_dir, repo_root) -> None:
    span = check_dataset_coverage(processed_dir)
    check_gitignore_covers_data(repo_root)
    print(f"[preconditions] OK: dataset spans {span.days} days; data/* is git-ignored")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", default="data/processed_14mo_fixed")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    try:
        check_all(args.processed_dir, args.repo_root)
    except PreconditionError as e:
        print("\n" + "=" * 72, file=sys.stderr)
        print(f"PRECONDITION FAILED: {e}", file=sys.stderr)
        print("=" * 72, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
