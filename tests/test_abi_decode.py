from eth_abi import encode as abi_encode

from t1000 import constants
from t1000.abi_decode import decode_log_row

OWNER = "0x1111111111111111111111111111111111111111"
SENDER = "0x2222222222222222222222222222222222222222"
RECIPIENT = "0x3333333333333333333333333333333333333333"


def _addr_topic(addr: str) -> str:
    return "0x" + "00" * 12 + addr[2:].lower()


def _int_topic(value: int) -> str:
    return "0x" + (value % 2**256).to_bytes(32, "big", signed=False).hex()


def _make_row(event_type, topics, data, block_number=100, log_index=0, tx_hash="0xabc"):
    return {
        "block_number": block_number,
        "block_timestamp": "2024-01-01T00:00:00Z",
        "transaction_hash": tx_hash,
        "log_index": log_index,
        "topics": [constants.TOPIC0[event_type]] + topics,
        "data": "0x" + data.hex(),
    }


def test_decode_swap_round_trip():
    data = abi_encode(
        ["int256", "int256", "uint160", "uint128", "int24"],
        [1000, -2000, 12345678901234567890, 999999, -12345],
    )
    row = _make_row("Swap", [_addr_topic(SENDER), _addr_topic(RECIPIENT)], data)
    event = decode_log_row(row)

    assert event.event_type == "Swap"
    assert event.fields["sender"] == SENDER.lower()
    assert event.fields["recipient"] == RECIPIENT.lower()
    assert event.fields["amount0"] == 1000
    assert event.fields["amount1"] == -2000
    assert event.fields["sqrt_price_x96"] == 12345678901234567890
    assert event.fields["liquidity"] == 999999
    assert event.fields["tick"] == -12345


def test_decode_mint_round_trip():
    data = abi_encode(["address", "uint128", "uint256", "uint256"], [SENDER, 500, 111, 222])
    row = _make_row(
        "Mint",
        [_addr_topic(OWNER), _int_topic(-100), _int_topic(200)],
        data,
    )
    event = decode_log_row(row)

    assert event.event_type == "Mint"
    assert event.fields["owner"] == OWNER.lower()
    assert event.fields["tick_lower"] == -100
    assert event.fields["tick_upper"] == 200
    assert event.fields["sender"] == SENDER.lower()
    assert event.fields["amount"] == 500
    assert event.fields["amount0"] == 111
    assert event.fields["amount1"] == 222


def test_decode_burn_round_trip():
    data = abi_encode(["uint128", "uint256", "uint256"], [500, 111, 222])
    row = _make_row("Burn", [_addr_topic(OWNER), _int_topic(-100), _int_topic(200)], data)
    event = decode_log_row(row)

    assert event.event_type == "Burn"
    assert event.fields["tick_lower"] == -100
    assert event.fields["tick_upper"] == 200
    assert event.fields["amount"] == 500


def test_decode_collect_round_trip():
    data = abi_encode(["address", "uint128", "uint128"], [RECIPIENT, 111, 222])
    row = _make_row("Collect", [_addr_topic(OWNER), _int_topic(-100), _int_topic(200)], data)
    event = decode_log_row(row)

    assert event.event_type == "Collect"
    assert event.fields["recipient"] == RECIPIENT.lower()
    assert event.fields["amount0"] == 111
    assert event.fields["amount1"] == 222


def test_decode_negative_ticks_near_min_max():
    data = abi_encode(["uint128", "uint256", "uint256"], [1, 0, 0])
    row = _make_row(
        "Burn",
        [_addr_topic(OWNER), _int_topic(constants.MIN_TICK), _int_topic(constants.MAX_TICK)],
        data,
    )
    event = decode_log_row(row)
    assert event.fields["tick_lower"] == constants.MIN_TICK
    assert event.fields["tick_upper"] == constants.MAX_TICK


def test_unknown_topic0_raises():
    import pytest

    row = _make_row("Swap", [_addr_topic(SENDER), _addr_topic(RECIPIENT)], b"\x00" * 32)
    row["topics"][0] = "0x" + "ff" * 32
    with pytest.raises(ValueError):
        decode_log_row(row)
