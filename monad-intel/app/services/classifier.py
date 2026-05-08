"""First-pass contract kind classifier.

Strategy:
- Detect proxy patterns first (EIP-1967, EIP-1167 minimal).
- Detect tokens via ERC-20/721/1155 selectors.
- Detect routers/factories via AMM-style selectors.
- Fall back to heuristics on metadata names.

Selectors are cheap to check: we just look for the 4-byte hex anywhere in
the bytecode. False positives possible (e.g., immutables); that's why this
is a *first-pass* classifier, refined later by static features and source.
"""

from __future__ import annotations

from app.utils.hashes import contains_selector, function_selector

# --- canonical selectors ---
SEL_TRANSFER = function_selector("transfer(address,uint256)")              # 0xa9059cbb
SEL_BALANCE_OF = function_selector("balanceOf(address)")                   # 0x70a08231
SEL_TOTAL_SUPPLY = function_selector("totalSupply()")                      # 0x18160ddd
SEL_DECIMALS = function_selector("decimals()")                             # 0x313ce567
SEL_SYMBOL = function_selector("symbol()")                                 # 0x95d89b41
SEL_NAME = function_selector("name()")                                     # 0x06fdde03
SEL_OWNER = function_selector("owner()")                                   # 0x8da5cb5b
SEL_TRANSFER_OWNERSHIP = function_selector("transferOwnership(address)")    # 0xf2fde38b
SEL_RENOUNCE_OWNERSHIP = function_selector("renounceOwnership()")          # 0x715018a6

# ERC-721
SEL_OWNER_OF = function_selector("ownerOf(uint256)")                       # 0x6352211e
SEL_SAFE_TRANSFER_FROM = function_selector("safeTransferFrom(address,address,uint256)")  # 0x42842e0e
SEL_TOKEN_URI = function_selector("tokenURI(uint256)")                     # 0xc87b56dd

# ERC-1155
SEL_BALANCE_OF_BATCH = function_selector("balanceOfBatch(address[],uint256[])")  # 0x4e1273f4

# Router / pair (Uniswap-V2-style)
SEL_SWAP_EXACT_TOKENS = function_selector(
    "swapExactTokensForTokens(uint256,uint256,address[],address,uint256)"
)  # 0x38ed1739
SEL_GET_RESERVES = function_selector("getReserves()")                      # 0x0902f1ac
SEL_TOKEN0 = function_selector("token0()")                                 # 0x0dfe1681
SEL_TOKEN1 = function_selector("token1()")                                 # 0xd21220a7
SEL_CREATE_PAIR = function_selector("createPair(address,address)")          # 0xc9c65396

# Governor
SEL_PROPOSE = function_selector(
    "propose(address[],uint256[],bytes[],string)"
)  # 0x7d5e81e2
SEL_CAST_VOTE = function_selector("castVote(uint256,uint8)")               # 0x56781388

# Staking
SEL_STAKE = function_selector("stake(uint256)")                            # 0xa694fc3a
SEL_WITHDRAW = function_selector("withdraw(uint256)")                       # 0x2e1a7d4e

# EIP-1167 minimal proxy: bytecode pattern.
EIP1167_PREFIX = "363d3d373d3d3d363d73"
EIP1167_SUFFIX = "5af43d82803e903d91602b57fd5bf3"


def is_eip1167_proxy(code_hex: str) -> bool:
    if not code_hex:
        return False
    c = code_hex.lower().replace("0x", "")
    return EIP1167_PREFIX in c and EIP1167_SUFFIX in c


def classify(
    *,
    code_hex: str,
    is_proxy: bool = False,
    contract_name: str | None = None,
    metadata_hint: str | None = None,
) -> str:
    """Return one of the canonical kinds (see schemas.common.ContractKind)."""

    if not code_hex or code_hex in ("0x", "0x0"):
        return "unknown"

    # Proxy first.
    if is_proxy or is_eip1167_proxy(code_hex):
        return "proxy"

    # Tokens.
    has_xfer = contains_selector(code_hex, SEL_TRANSFER) and contains_selector(code_hex, SEL_BALANCE_OF)
    has_supply = contains_selector(code_hex, SEL_TOTAL_SUPPLY)
    if has_xfer and has_supply:
        if contains_selector(code_hex, SEL_OWNER_OF) or contains_selector(code_hex, SEL_TOKEN_URI):
            return "nft"
        if contains_selector(code_hex, SEL_BALANCE_OF_BATCH):
            return "nft"  # ERC-1155 multi-token; group with NFT for first pass
        return "token"

    # NFT 721/1155 even if transfer signature differs.
    if contains_selector(code_hex, SEL_OWNER_OF) or contains_selector(code_hex, SEL_TOKEN_URI):
        return "nft"
    if contains_selector(code_hex, SEL_BALANCE_OF_BATCH):
        return "nft"

    # AMM pair.
    if (
        contains_selector(code_hex, SEL_GET_RESERVES)
        and contains_selector(code_hex, SEL_TOKEN0)
        and contains_selector(code_hex, SEL_TOKEN1)
    ):
        return "lp_pair"

    # Router.
    if contains_selector(code_hex, SEL_SWAP_EXACT_TOKENS):
        return "router"

    # Factory.
    if contains_selector(code_hex, SEL_CREATE_PAIR):
        return "factory"

    # Governor.
    if contains_selector(code_hex, SEL_PROPOSE) and contains_selector(code_hex, SEL_CAST_VOTE):
        return "governance"

    # Staking heuristic (low confidence).
    if contains_selector(code_hex, SEL_STAKE) and contains_selector(code_hex, SEL_WITHDRAW):
        return "staking"

    # Metadata-name heuristic.
    name = (contract_name or "").lower()
    if name:
        if "treasury" in name or "vault" in name:
            return "treasury"
        if "router" in name:
            return "router"
        if "factory" in name:
            return "factory"
        if "governor" in name or "governance" in name:
            return "governance"
        if "staking" in name:
            return "staking"
        if "implementation" in name or "logic" in name:
            return "implementation"

    if metadata_hint and "implementation" in metadata_hint.lower():
        return "implementation"

    return "utility"
