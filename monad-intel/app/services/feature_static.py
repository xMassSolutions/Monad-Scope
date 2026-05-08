"""Static feature extraction.

All keys are guaranteed present (None or bool). The contract of this module
is the *exact* set of keys used by the findings engine.

Extraction signals (each best-effort):
- selector presence in bytecode
- text matching in source (when verified)
- proxy detection result fed in by the caller

This is deliberately conservative: when in doubt, set False (not present).
The findings engine combines features into hard-fail / weighted findings.
"""

from __future__ import annotations

import re

from app.utils.hashes import contains_selector, function_selector

# --- ERC-20 admin / mint / control selectors ---
SEL_MINT = function_selector("mint(address,uint256)")
SEL_MINT_TO = function_selector("mintTo(address,uint256)")
SEL_BLACKLIST = function_selector("blacklist(address,bool)")
SEL_BLOCK_USER = function_selector("blockUser(address)")
SEL_PAUSE = function_selector("pause()")
SEL_UNPAUSE = function_selector("unpause()")
SEL_SET_FEE = function_selector("setFee(uint256)")
SEL_SET_BUY_FEE = function_selector("setBuyFee(uint256)")
SEL_SET_SELL_FEE = function_selector("setSellFee(uint256)")
SEL_SET_MAX_WALLET = function_selector("setMaxWallet(uint256)")
SEL_SET_MAX_TX = function_selector("setMaxTx(uint256)")
SEL_RENOUNCE_OWNERSHIP = function_selector("renounceOwnership()")
SEL_WITHDRAW = function_selector("withdraw(uint256)")
SEL_WITHDRAW_TO = function_selector("withdrawTo(address,uint256)")
SEL_RESCUE_TOKEN = function_selector("rescueERC20(address,uint256)")
SEL_REMOVE_LIQUIDITY = function_selector(
    "removeLiquidity(address,address,uint256,uint256,uint256,address,uint256)"
)
SEL_UPGRADE_TO = function_selector("upgradeTo(address)")
SEL_UPGRADE_TO_AND_CALL = function_selector("upgradeToAndCall(address,bytes)")


# Source-level patterns for things selectors miss.
_RE_OWNER_ONLY = re.compile(r"\bonlyOwner\b", re.IGNORECASE)
_RE_MINT_CAP = re.compile(r"\b(maxSupply|MAX_SUPPLY|cap|MAX_CAP|MAX_MINT)\b")
_RE_HIDDEN_TRANSFER = re.compile(
    r"(require\s*\(\s*[\w.]*(canTrade|tradingEnabled|isAllowed|whitelist|blacklist)|_beforeTokenTransfer)",
    re.IGNORECASE,
)
_RE_LIQ_REMOVAL = re.compile(r"\b(removeLiquidity|withdrawLiquidity|emergencyWithdraw)\b")
_RE_RENOUNCE = re.compile(r"\brenounceOwnership\s*\(", re.IGNORECASE)


# Canonical key set — extend deliberately, don't add fields ad-hoc.
STATIC_FEATURE_KEYS = (
    "source_verified",
    "implementation_verified",
    "is_proxy",
    "owner_can_mint",
    "mint_capped",
    "blacklist_function",
    "trading_can_pause",
    "owner_can_change_fees",
    "max_wallet_controls",
    "max_tx_controls",
    "admin_can_withdraw_user_funds",
    "liquidity_removal_controls",
    "hidden_transfer_restrictions",
    "upgradeable_proxy",
    "renounce_pattern_detected",
    "unverified_contract",
)


def _empty() -> dict[str, bool | None]:
    return {k: False for k in STATIC_FEATURE_KEYS}


def extract_static_features(
    *,
    code_hex: str,
    source: str | None,
    is_proxy: bool,
    implementation_verified: bool | None,
    source_verified: bool,
) -> dict[str, bool | None]:
    f = _empty()
    f["source_verified"] = bool(source_verified)
    f["implementation_verified"] = bool(implementation_verified) if is_proxy else None
    f["is_proxy"] = bool(is_proxy)
    f["unverified_contract"] = not bool(source_verified)

    # Bytecode signals.
    f["owner_can_mint"] = contains_selector(code_hex, SEL_MINT) or contains_selector(code_hex, SEL_MINT_TO)
    f["blacklist_function"] = contains_selector(code_hex, SEL_BLACKLIST) or contains_selector(code_hex, SEL_BLOCK_USER)
    f["trading_can_pause"] = contains_selector(code_hex, SEL_PAUSE) and contains_selector(code_hex, SEL_UNPAUSE)
    f["owner_can_change_fees"] = (
        contains_selector(code_hex, SEL_SET_FEE)
        or contains_selector(code_hex, SEL_SET_BUY_FEE)
        or contains_selector(code_hex, SEL_SET_SELL_FEE)
    )
    f["max_wallet_controls"] = contains_selector(code_hex, SEL_SET_MAX_WALLET)
    f["max_tx_controls"] = contains_selector(code_hex, SEL_SET_MAX_TX)
    f["admin_can_withdraw_user_funds"] = (
        contains_selector(code_hex, SEL_WITHDRAW_TO)
        or contains_selector(code_hex, SEL_RESCUE_TOKEN)
    )
    f["liquidity_removal_controls"] = contains_selector(code_hex, SEL_REMOVE_LIQUIDITY)
    f["upgradeable_proxy"] = is_proxy and (
        contains_selector(code_hex, SEL_UPGRADE_TO) or contains_selector(code_hex, SEL_UPGRADE_TO_AND_CALL)
    )

    # Source-level signals (only meaningful when verified).
    if source:
        f["owner_can_mint"] = f["owner_can_mint"] or bool(_RE_OWNER_ONLY.search(source) and re.search(r"\bmint\s*\(", source, re.IGNORECASE))
        f["mint_capped"] = bool(_RE_MINT_CAP.search(source))
        f["hidden_transfer_restrictions"] = bool(_RE_HIDDEN_TRANSFER.search(source))
        f["liquidity_removal_controls"] = f["liquidity_removal_controls"] or bool(_RE_LIQ_REMOVAL.search(source))
        f["renounce_pattern_detected"] = bool(_RE_RENOUNCE.search(source))
    else:
        # Without source, leave subtle features unset (None) instead of asserting False.
        f["mint_capped"] = None
        f["hidden_transfer_restrictions"] = None
        f["renounce_pattern_detected"] = None

    return f
