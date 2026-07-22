"""Decode raw Uniswap V3 pool event logs (topics + data) with no RPC connection.

BigQuery's `crypto_ethereum.logs` table already contains the exact topics/data
an `eth_getLogs` call would return, so decoding is fully offline: topic0
identifies the event, remaining topics carry indexed args, `data` carries the
non-indexed args in declaration order (see constants.EVENT_SIGNATURES).
"""
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from eth_abi import decode as abi_decode
from hexbytes import HexBytes

from . import constants


def _topic_to_address(topic: str) -> str:
    return "0x" + HexBytes(topic).hex()[-40:]


def _topic_to_signed_int(topic: str) -> int:
    """Indexed signed integers (e.g. int24 tick bounds) are ABI-encoded as a
    sign-extended 256-bit word before becoming a topic, so a plain two's
    complement interpretation of the full 32-byte word recovers the original
    value directly."""
    value = int(HexBytes(topic).hex(), 16)
    if value >= 2**255:
        value -= 2**256
    return value


@dataclass(frozen=True)
class DecodedEvent:
    event_type: str
    block_number: int
    log_index: int
    tx_hash: str
    timestamp: Any
    fields: dict = field(default_factory=dict)


def decode_log_row(row: Mapping[str, Any]) -> DecodedEvent:
    """`row` needs: block_number, block_timestamp, transaction_hash, log_index,
    topics (list[str], each a 0x-prefixed 32-byte hex word), data (0x-prefixed hex)."""
    topics: Sequence[str] = row["topics"]
    topic0 = topics[0]
    event_type = constants.TOPIC0_TO_EVENT.get(topic0)
    if event_type is None:
        raise ValueError(f"Unknown topic0: {topic0}")

    data_bytes = bytes(HexBytes(row["data"]))

    if event_type == "Swap":
        sender = _topic_to_address(topics[1])
        recipient = _topic_to_address(topics[2])
        amount0, amount1, sqrt_price_x96, liquidity, tick = abi_decode(
            ["int256", "int256", "uint160", "uint128", "int24"], data_bytes
        )
        fields = dict(
            sender=sender, recipient=recipient, amount0=amount0, amount1=amount1,
            sqrt_price_x96=sqrt_price_x96, liquidity=liquidity, tick=tick,
        )
    elif event_type == "Mint":
        owner = _topic_to_address(topics[1])
        tick_lower = _topic_to_signed_int(topics[2])
        tick_upper = _topic_to_signed_int(topics[3])
        sender, amount, amount0, amount1 = abi_decode(
            ["address", "uint128", "uint256", "uint256"], data_bytes
        )
        fields = dict(
            owner=owner, tick_lower=tick_lower, tick_upper=tick_upper,
            sender=sender, amount=amount, amount0=amount0, amount1=amount1,
        )
    elif event_type == "Burn":
        owner = _topic_to_address(topics[1])
        tick_lower = _topic_to_signed_int(topics[2])
        tick_upper = _topic_to_signed_int(topics[3])
        amount, amount0, amount1 = abi_decode(["uint128", "uint256", "uint256"], data_bytes)
        fields = dict(
            owner=owner, tick_lower=tick_lower, tick_upper=tick_upper,
            amount=amount, amount0=amount0, amount1=amount1,
        )
    elif event_type == "Collect":
        owner = _topic_to_address(topics[1])
        tick_lower = _topic_to_signed_int(topics[2])
        tick_upper = _topic_to_signed_int(topics[3])
        recipient, amount0, amount1 = abi_decode(["address", "uint128", "uint128"], data_bytes)
        fields = dict(
            owner=owner, tick_lower=tick_lower, tick_upper=tick_upper,
            recipient=recipient, amount0=amount0, amount1=amount1,
        )
    elif event_type == "CollectProtocol":
        sender = _topic_to_address(topics[1])
        recipient = _topic_to_address(topics[2])
        amount0, amount1 = abi_decode(["uint128", "uint128"], data_bytes)
        fields = dict(sender=sender, recipient=recipient, amount0=amount0, amount1=amount1)
    else:  # pragma: no cover - constants.TOPIC0_TO_EVENT keeps this unreachable
        raise ValueError(f"Unhandled event type: {event_type}")

    return DecodedEvent(
        event_type=event_type,
        block_number=row["block_number"],
        log_index=row["log_index"],
        tx_hash=row["transaction_hash"],
        timestamp=row.get("block_timestamp"),
        fields=fields,
    )
