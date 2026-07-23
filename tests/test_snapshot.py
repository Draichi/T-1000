from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from t1000.fee_engine import FeeEngine
from t1000.snapshot import (
    deserialize_engine,
    load_snapshot,
    load_snapshot_index_from_dir,
    precompute_snapshots,
    replay_events,
    save_snapshot,
    serialize_engine,
)
from t1000.tick_math import sqrt_price_x96_from_tick


def _make_event(event_type, fields, ts):
    return SimpleNamespace(event_type=event_type, fields=fields, timestamp=ts)


def _synthetic_events(n=40):
    events = []
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    tick = 0
    for i in range(n):
        ts = base + timedelta(hours=i)
        if i == 0:
            events.append(_make_event("Mint", {"tick_lower": -1000, "tick_upper": 1000, "amount": 10_000}, ts))
        else:
            new_tick = tick + (5 if i % 2 == 0 else -3)
            events.append(
                _make_event(
                    "Swap",
                    {
                        "amount0": 100 if i % 2 == 0 else -80,
                        "amount1": -90 if i % 2 == 0 else 70,
                        "sqrt_price_x96": sqrt_price_x96_from_tick(new_tick),
                        "tick": new_tick,
                        "liquidity": 10_000,
                    },
                    ts,
                )
            )
            tick = new_tick
    return events


def test_serialize_deserialize_round_trip():
    engine = FeeEngine()
    engine.initialize_pool(sqrt_price_x96_from_tick(0), 0)
    engine.apply_mint(-100, 100, 5000)
    engine.apply_swap(100, -90, sqrt_price_x96_from_tick(10), 10, 5000)

    restored = deserialize_engine(serialize_engine(engine))

    assert restored.pool == engine.pool
    assert restored.tick_map == engine.tick_map


def test_save_and_load_snapshot_file_round_trip(tmp_path):
    engine = FeeEngine()
    engine.initialize_pool(sqrt_price_x96_from_tick(0), 0)
    engine.apply_mint(-100, 100, 5000)

    path = tmp_path / "snap.pkl.gz"
    save_snapshot(engine, path)
    restored = load_snapshot(path)

    assert restored.pool == engine.pool
    assert restored.tick_map == engine.tick_map


def test_snapshot_plus_replay_matches_full_replay(tmp_path):
    """The core correctness property that justifies the whole snapshot
    mechanism: loading the nearest snapshot and replaying only the remainder
    must produce byte-identical engine state to replaying everything from
    genesis."""
    events = _synthetic_events(40)
    index = precompute_snapshots(events, tmp_path, cadence_seconds=3600 * 10)

    target_index = 33
    target_ts = events[target_index].timestamp

    snap_ts, snap_path = index.nearest_at_or_before(target_ts)
    restored = load_snapshot(snap_path)
    baked_in = sum(1 for e in events if e.timestamp <= snap_ts)
    replay_events(restored, events, start_index=baked_in, end_index=target_index + 1)

    reference = FeeEngine()
    replay_events(reference, events, start_index=0, end_index=target_index + 1)

    assert restored.pool == reference.pool
    assert restored.tick_map == reference.tick_map


def test_snapshot_boundary_never_splits_same_timestamp_events(tmp_path):
    """Regression: several events can share one timestamp (same block). A
    snapshot cut in the middle of such a group would strand the leftover
    events -- outside the snapshot AND outside a `timestamp > snap_ts`
    replay. Every snapshot at T must therefore contain exactly the events
    with timestamp <= T."""
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    events = []
    tick = 0
    for i in range(30):
        ts = base + timedelta(hours=i)
        # three events per block: a swap flanked by two mints
        events.append(_make_event("Mint", {"tick_lower": -1000, "tick_upper": 1000, "amount": 1_000}, ts))
        new_tick = tick + (5 if i % 2 == 0 else -3)
        events.append(
            _make_event(
                "Swap",
                {
                    "amount0": 100 if i % 2 == 0 else -80,
                    "amount1": -90 if i % 2 == 0 else 70,
                    "sqrt_price_x96": sqrt_price_x96_from_tick(new_tick),
                    "tick": new_tick,
                    "liquidity": 10_000,
                },
                ts,
            )
        )
        events.append(_make_event("Mint", {"tick_lower": -2000, "tick_upper": 2000, "amount": 500}, ts))
        tick = new_tick

    index = precompute_snapshots(events, tmp_path, cadence_seconds=3600 * 7)
    assert len(index.entries) >= 2

    for snap_ts, snap_path in index.entries:
        restored = load_snapshot(snap_path)
        reference = FeeEngine()
        baked_in = sum(1 for e in events if e.timestamp <= snap_ts)
        replay_events(reference, events, start_index=0, end_index=baked_in)
        assert restored.pool == reference.pool
        assert restored.tick_map == reference.tick_map


def test_load_snapshot_index_from_dir_reconstructs_equivalent_index(tmp_path):
    events = _synthetic_events(40)
    original_index = precompute_snapshots(events, tmp_path, cadence_seconds=3600 * 10)

    reloaded_index = load_snapshot_index_from_dir(tmp_path)
    assert len(reloaded_index.entries) == len(original_index.entries)

    target_ts = events[33].timestamp
    orig_ts, orig_path = original_index.nearest_at_or_before(target_ts)
    reloaded_ts, reloaded_path = reloaded_index.nearest_at_or_before(target_ts)
    assert orig_path == reloaded_path
    # millisecond-precision round trip: same instant to the second
    assert abs((orig_ts - reloaded_ts).total_seconds()) < 1
