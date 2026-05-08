"""Classifier unit tests — selector-pattern smoke tests."""

from __future__ import annotations

from app.services.classifier import (
    EIP1167_PREFIX,
    EIP1167_SUFFIX,
    SEL_GET_RESERVES,
    SEL_TOKEN0,
    SEL_TOKEN1,
    SEL_TRANSFER,
    SEL_BALANCE_OF,
    SEL_TOTAL_SUPPLY,
    SEL_TOKEN_URI,
    SEL_OWNER_OF,
    SEL_SWAP_EXACT_TOKENS,
    SEL_CREATE_PAIR,
    SEL_PROPOSE,
    SEL_CAST_VOTE,
    classify,
    is_eip1167_proxy,
)


def _bytecode(*selectors: str, prefix: str = "60806040") -> str:
    return "0x" + prefix + "".join(s.replace("0x", "") for s in selectors)


def test_classify_token() -> None:
    code = _bytecode(SEL_TRANSFER, SEL_BALANCE_OF, SEL_TOTAL_SUPPLY)
    assert classify(code_hex=code) == "token"


def test_classify_nft_via_owner_of() -> None:
    code = _bytecode(SEL_TRANSFER, SEL_BALANCE_OF, SEL_TOTAL_SUPPLY, SEL_OWNER_OF, SEL_TOKEN_URI)
    assert classify(code_hex=code) == "nft"


def test_classify_lp_pair() -> None:
    code = _bytecode(SEL_GET_RESERVES, SEL_TOKEN0, SEL_TOKEN1)
    assert classify(code_hex=code) == "lp_pair"


def test_classify_router() -> None:
    code = _bytecode(SEL_SWAP_EXACT_TOKENS)
    assert classify(code_hex=code) == "router"


def test_classify_factory() -> None:
    code = _bytecode(SEL_CREATE_PAIR)
    assert classify(code_hex=code) == "factory"


def test_classify_governance() -> None:
    code = _bytecode(SEL_PROPOSE, SEL_CAST_VOTE)
    assert classify(code_hex=code) == "governance"


def test_classify_proxy_eip1167() -> None:
    code = "0x" + EIP1167_PREFIX + "00" * 20 + EIP1167_SUFFIX
    assert is_eip1167_proxy(code)
    assert classify(code_hex=code) == "proxy"


def test_classify_unknown() -> None:
    assert classify(code_hex="0x") == "unknown"


def test_classify_proxy_flag_overrides() -> None:
    code = _bytecode(SEL_TRANSFER, SEL_BALANCE_OF, SEL_TOTAL_SUPPLY)
    assert classify(code_hex=code, is_proxy=True) == "proxy"
