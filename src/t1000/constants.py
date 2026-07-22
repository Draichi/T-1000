"""On-chain constants for the Uniswap V3 ETH/USDC 0.05% pool.

Event topic0 hashes are computed at import time via keccak256 of the
canonical event signature strings (never hardcoded from memory), so a
transcription mistake fails loudly instead of silently corrupting decoding.
"""
from eth_utils import keccak

POOL_ADDRESS = "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"  # USDC/WETH 0.05%
NFPM_ADDRESS = "0xc36442b4a4522e871399cd717abdd847ab11fe88"  # NonfungiblePositionManager

TOKEN0_SYMBOL, TOKEN0_DECIMALS = "USDC", 6
TOKEN1_SYMBOL, TOKEN1_DECIMALS = "WETH", 18

FEE_PIPS = 500          # 0.05% = 500 / 1_000_000
TICK_SPACING = 10       # tick spacing for the 500-pip fee tier

MIN_TICK = -887272
MAX_TICK = 887272
MIN_SQRT_RATIO = 4295128739
MAX_SQRT_RATIO = 1461446703485210103287273052203988822378723970342

Q128 = 2**128
Q256 = 2**256

EVENT_SIGNATURES = {
    "Swap": "Swap(address,address,int256,int256,uint160,uint128,int24)",
    "Mint": "Mint(address,address,int24,int24,uint128,uint256,uint256)",
    "Burn": "Burn(address,int24,int24,uint128,uint256,uint256)",
    "Collect": "Collect(address,address,int24,int24,uint128,uint128)",
    "CollectProtocol": "CollectProtocol(address,address,uint128,uint128)",
}

TOPIC0 = {name: "0x" + keccak(text=sig).hex() for name, sig in EVENT_SIGNATURES.items()}
TOPIC0_TO_EVENT = {v: k for k, v in TOPIC0.items()}
