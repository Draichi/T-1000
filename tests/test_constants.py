from eth_utils import keccak

from t1000 import constants


def test_topic0_well_known_erc20_transfer_cross_check():
    """Independent sanity check of the keccak pipeline itself: the ERC20
    Transfer event topic0 is one of the most widely published hashes on
    Ethereum, so if our keccak(text=...) call reproduces it exactly, we can
    trust the same call for the (less universally memorized) Uniswap V3
    event signatures in constants.py.
    """
    known_transfer_topic0 = (
        "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    )
    computed = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
    assert computed == known_transfer_topic0


def test_topic0_shape():
    for name, topic in constants.TOPIC0.items():
        assert topic.startswith("0x"), name
        assert len(topic) == 66, (name, topic)  # 0x + 32 bytes hex
        int(topic, 16)  # valid hex


def test_topic0_round_trips_through_lookup_table():
    for name, topic in constants.TOPIC0.items():
        assert constants.TOPIC0_TO_EVENT[topic] == name


def test_topic0_are_all_distinct():
    assert len(set(constants.TOPIC0.values())) == len(constants.TOPIC0)
