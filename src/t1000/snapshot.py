"""Serialize/restore FeeEngine state for fast env.reset(): replaying the full
historical event log from genesis on every episode reset would be far too
slow, so precompute_snapshots() walks the log once and periodically dumps
engine state to disk; env.reset() then loads the nearest snapshot at or
before its sampled start time and only replays the short remainder.
"""
import gzip
import pickle
from dataclasses import asdict
from datetime import timedelta, timezone
from datetime import datetime as _datetime
from pathlib import Path
from typing import Any, Iterable, Optional

from .fee_engine import FeeEngine, PoolState, TickInfo


def serialize_engine(engine: FeeEngine) -> dict:
    return {
        "fee_pips": engine.fee_pips,
        "pool": asdict(engine.pool),
        "tick_map": {tick: asdict(info) for tick, info in engine.tick_map.items()},
    }


def deserialize_engine(state: dict) -> FeeEngine:
    engine = FeeEngine(fee_pips=state["fee_pips"])
    engine.pool = PoolState(**state["pool"])
    engine.tick_map = {tick: TickInfo(**info) for tick, info in state["tick_map"].items()}
    return engine


def save_snapshot(engine: FeeEngine, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as f:
        pickle.dump(serialize_engine(engine), f)


def load_snapshot(path: Path) -> FeeEngine:
    with gzip.open(Path(path), "rb") as f:
        state = pickle.load(f)
    return deserialize_engine(state)


def apply_event(engine: FeeEngine, event: Any) -> None:
    """event: an abi_decode.DecodedEvent (or anything with .event_type/.fields).
    Collect/CollectProtocol don't affect pool/tick-map state (only owed-token
    bookkeeping, handled by the position/env layer), so they're a no-op here.
    """
    f = event.fields
    if event.event_type == "Mint":
        engine.apply_mint(f["tick_lower"], f["tick_upper"], f["amount"])
    elif event.event_type == "Burn":
        engine.apply_burn(f["tick_lower"], f["tick_upper"], f["amount"])
    elif event.event_type == "Swap":
        engine.apply_swap(f["amount0"], f["amount1"], f["sqrt_price_x96"], f["tick"], f["liquidity"])


def replay_events(engine: FeeEngine, events: list, start_index: int = 0, end_index: Optional[int] = None) -> int:
    """Applies events[start_index:end_index] (pre-sorted by
    (block_number, log_index)) to `engine` in place. Returns count applied."""
    end_index = len(events) if end_index is None else end_index
    for event in events[start_index:end_index]:
        apply_event(engine, event)
    return end_index - start_index


def snapshot_filename(ts: Any) -> str:
    """Epoch-milliseconds filename: unambiguous and lexicographically
    sortable, unlike a str(timestamp)-derived name (dashes appear in both the
    date part and a ':'->'-' substitution, making that scheme irreversible)."""
    epoch_ms = int(ts.timestamp() * 1000)
    return f"{epoch_ms}.pkl.gz"


class SnapshotIndex:
    """Maps snapshot timestamps -> file path; finds the nearest snapshot at
    or before a requested timestamp."""

    def __init__(self, entries: Iterable[tuple[Any, Path]]):
        self.entries = sorted(entries, key=lambda e: e[0])

    def nearest_at_or_before(self, timestamp: Any) -> tuple[Any, Path]:
        best = None
        for ts, path in self.entries:
            if ts <= timestamp:
                best = (ts, path)
            else:
                break
        if best is None:
            raise ValueError(f"No snapshot at or before {timestamp}")
        return best


def precompute_snapshots(
    events: list, out_dir: Path, cadence_seconds: float = 86400, engine: Optional[FeeEngine] = None
) -> SnapshotIndex:
    """Walks `events` (sorted, with a `.timestamp` attribute) once, saving a
    full engine snapshot at least every `cadence_seconds`. Pass an existing
    `engine` (e.g. freshly constructed) to inspect it afterwards, such as its
    `liquidity_mismatches` data-quality counter.

    A snapshot taken at timestamp T always contains ALL events with
    timestamp <= T: events sharing one timestamp (same block) must land
    entirely inside or entirely after a snapshot, or the `timestamp > snap_ts`
    replay mask in env.reset() would silently skip the leftover events of the
    snapshot's own block."""
    out_dir = Path(out_dir)
    if engine is None:
        engine = FeeEngine()
    entries: list[tuple[Any, Path]] = []
    next_snapshot_ts = None
    prev_ts = None

    def _save(ts) -> None:
        path = out_dir / snapshot_filename(ts)
        save_snapshot(engine, path)
        entries.append((ts, path))

    for event in events:
        ts = event.timestamp
        if next_snapshot_ts is None:
            next_snapshot_ts = ts
        if prev_ts is not None and ts > prev_ts and prev_ts >= next_snapshot_ts:
            _save(prev_ts)
            next_snapshot_ts = prev_ts + timedelta(seconds=cadence_seconds)
        apply_event(engine, event)
        prev_ts = ts

    if prev_ts is not None and prev_ts >= next_snapshot_ts:
        _save(prev_ts)

    return SnapshotIndex(entries)


def load_snapshot_index_from_dir(snapshot_dir: Path) -> SnapshotIndex:
    """Reconstructs a SnapshotIndex from a directory of `snapshot_filename()`-
    named files, without needing the original event list in memory (e.g. in
    a fresh train.py/backtest.py process)."""
    snapshot_dir = Path(snapshot_dir)
    entries = []
    for path in snapshot_dir.glob("*.pkl.gz"):
        epoch_ms = int(path.name.removesuffix(".pkl.gz"))
        ts = _datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
        entries.append((ts, path))
    return SnapshotIndex(entries)
