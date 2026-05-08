"""x402 wallet signer + payment-signature header tests.

Verifies that with a platform wallet configured:
- WalletSigner instantiates and exposes the right chain id + USDC contract.
- sign_authorization() returns a non-empty signature with valid v/r/s.
- The base64 header decodes to the documented JSON schema.
"""

from __future__ import annotations

import base64
import json
import os

import pytest


@pytest.fixture
def wallet_env(monkeypatch):
    # Anvil's well-known dev key 0 — public, never used for real funds.
    monkeypatch.setenv(
        "PLATFORM_WALLET_PRIVATE_KEY",
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    )
    monkeypatch.setenv("PLATFORM_WALLET_CHAIN", "monad")
    # Reset the cached settings.
    from app.config import get_settings
    get_settings.cache_clear()  # type: ignore[attr-defined]
    yield
    get_settings.cache_clear()  # type: ignore[attr-defined]


def test_wallet_signer_initializes(wallet_env) -> None:
    from app.services.x402 import WalletSigner

    signer = WalletSigner()
    assert signer.address.startswith("0x") and len(signer.address) == 42
    assert signer.chain == "monad"
    assert signer.chain_id == 143
    # USDC on Monad as published by Fortytwo:
    assert signer.usdc_address.lower() == "0x754704bc059f8c67012fed69bc8a327a5aafb603"
    assert signer.escrow_recipient.lower() == "0x9562f50f73d8ee22276f13a18d051456d8d137a0"
    assert signer.max_amount == 2_000_000  # 2 USDC default cap


def test_sign_authorization_produces_valid_signature(wallet_env) -> None:
    from app.services.x402 import WalletSigner

    signer = WalletSigner()
    auth = signer.sign_authorization(amount=1_500_000)
    assert auth.value == 1_500_000
    assert auth.client.lower() == signer.address.lower()
    assert auth.to.lower() == signer.escrow_recipient.lower()
    assert auth.chain_id == 143
    assert auth.v in (27, 28)
    # 32-byte hex (with 0x); allow odd-length hex(int) form too.
    assert auth.r_hex.startswith("0x") and auth.s_hex.startswith("0x")
    assert auth.nonce_hex.startswith("0x") and len(auth.nonce_hex) == 66
    assert auth.valid_after < auth.valid_before


def test_payment_signature_header_decodes_to_documented_schema(wallet_env) -> None:
    from app.services.x402 import WalletSigner, encode_payment_signature_header

    signer = WalletSigner()
    auth = signer.sign_authorization()
    header = encode_payment_signature_header(auth, signer.max_amount)
    body = json.loads(base64.b64decode(header).decode("utf-8"))
    # Documented field names:
    for key in ("client", "maxAmount", "validAfter", "validBefore", "nonce", "v", "r", "s"):
        assert key in body, f"missing {key}"
    assert body["client"].lower() == signer.address.lower()
    assert int(body["maxAmount"]) == signer.max_amount


def test_two_signatures_use_different_nonces(wallet_env) -> None:
    from app.services.x402 import WalletSigner

    signer = WalletSigner()
    a = signer.sign_authorization()
    b = signer.sign_authorization()
    assert a.nonce_hex != b.nonce_hex


def test_unsupported_chain_rejected(monkeypatch) -> None:
    monkeypatch.setenv("PLATFORM_WALLET_PRIVATE_KEY", "0x" + "11" * 32)
    monkeypatch.setenv("PLATFORM_WALLET_CHAIN", "ethereum")
    from app.config import get_settings
    get_settings.cache_clear()  # type: ignore[attr-defined]
    from app.services.x402 import WalletSigner

    with pytest.raises((RuntimeError, ValueError)):
        WalletSigner()
    get_settings.cache_clear()  # type: ignore[attr-defined]
