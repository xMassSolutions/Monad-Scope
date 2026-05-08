"""Privy JWT verification tests.

We generate a fresh ES256 keypair, mint a token signed by it, monkey-patch
PyJWKClient to return our public key, and then verify the round-trip.
"""

from __future__ import annotations

import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ec import (
    SECP256R1,
    EllipticCurvePrivateKey,
    generate_private_key,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


APP_ID = "test_app_id_xyz"


@pytest.fixture
def privy_env(monkeypatch):
    monkeypatch.setenv("PRIVY_APP_ID", APP_ID)
    monkeypatch.setenv("PRIVY_APP_SECRET", "")  # don't enrich in tests
    monkeypatch.setenv("PRIVY_REQUIRED", "false")
    from app.config import get_settings
    get_settings.cache_clear()  # type: ignore[attr-defined]
    from app.services.privy import PrivyVerifier
    PrivyVerifier.reset_for_tests()
    yield
    get_settings.cache_clear()  # type: ignore[attr-defined]
    PrivyVerifier.reset_for_tests()


def _keys() -> tuple[EllipticCurvePrivateKey, str]:
    priv = generate_private_key(SECP256R1())
    pem = priv.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    return priv, pem.decode("utf-8")


def _mint_token(priv: EllipticCurvePrivateKey, *, sub="user-1", aud=APP_ID, iss="privy.io", ttl=3600) -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": sub, "aud": aud, "iss": iss, "iat": now, "exp": now + ttl},
        priv,
        algorithm="ES256",
    )


def _patch_signing_key(monkeypatch, priv: EllipticCurvePrivateKey) -> None:
    """Make PyJWKClient.get_signing_key_from_jwt return our test public key."""
    from app.services import privy as privy_mod

    pub = priv.public_key()

    class _Key:
        def __init__(self, key):
            self.key = key

    monkeypatch.setattr(
        privy_mod.PyJWKClient,
        "get_signing_key_from_jwt",
        lambda self, token: _Key(pub),
    )


@pytest.mark.asyncio
async def test_valid_token_round_trip(privy_env, monkeypatch) -> None:
    priv, _ = _keys()
    _patch_signing_key(monkeypatch, priv)
    token = _mint_token(priv, sub="did:privy:abc")

    from app.services.privy import PrivyVerifier

    user = await PrivyVerifier.get().verify(token)
    assert user.user_id == "did:privy:abc"
    assert user.expires_at and user.expires_at > int(time.time())


@pytest.mark.asyncio
async def test_expired_token_rejected(privy_env, monkeypatch) -> None:
    priv, _ = _keys()
    _patch_signing_key(monkeypatch, priv)
    token = _mint_token(priv, ttl=-30)  # expired
    from app.services.privy import PrivyVerifier, PrivyVerifierError

    with pytest.raises(PrivyVerifierError):
        await PrivyVerifier.get().verify(token)


@pytest.mark.asyncio
async def test_wrong_audience_rejected(privy_env, monkeypatch) -> None:
    priv, _ = _keys()
    _patch_signing_key(monkeypatch, priv)
    token = _mint_token(priv, aud="some-other-app")
    from app.services.privy import PrivyVerifier, PrivyVerifierError

    with pytest.raises(PrivyVerifierError):
        await PrivyVerifier.get().verify(token)


@pytest.mark.asyncio
async def test_wrong_issuer_rejected(privy_env, monkeypatch) -> None:
    priv, _ = _keys()
    _patch_signing_key(monkeypatch, priv)
    token = _mint_token(priv, iss="evil.example.com")
    from app.services.privy import PrivyVerifier, PrivyVerifierError

    with pytest.raises(PrivyVerifierError):
        await PrivyVerifier.get().verify(token)


@pytest.mark.asyncio
async def test_signature_mismatch_rejected(privy_env, monkeypatch) -> None:
    real_priv, _ = _keys()
    other_priv, _ = _keys()
    # Server believes `real_priv`'s public key, but token is signed by `other_priv`.
    _patch_signing_key(monkeypatch, real_priv)
    token = _mint_token(other_priv)
    from app.services.privy import PrivyVerifier, PrivyVerifierError

    with pytest.raises(PrivyVerifierError):
        await PrivyVerifier.get().verify(token)


@pytest.mark.asyncio
async def test_get_optional_user_passes_through(privy_env, monkeypatch) -> None:
    priv, _ = _keys()
    _patch_signing_key(monkeypatch, priv)
    token = _mint_token(priv, sub="user-42")

    from app.api.deps import get_optional_user

    user = await get_optional_user(authorization=f"Bearer {token}")
    assert user is not None
    assert user.user_id == "user-42"


@pytest.mark.asyncio
async def test_get_optional_user_returns_none_for_missing(privy_env) -> None:
    from app.api.deps import get_optional_user

    assert await get_optional_user(authorization=None) is None
    assert await get_optional_user(authorization="") is None
    assert await get_optional_user(authorization="not-a-bearer xxx") is None
    assert await get_optional_user(authorization="Bearer ") is None


@pytest.mark.asyncio
async def test_required_auth_rejects_anonymous_when_enforced(privy_env, monkeypatch) -> None:
    monkeypatch.setenv("PRIVY_REQUIRED", "true")
    from app.config import get_settings
    get_settings.cache_clear()  # type: ignore[attr-defined]

    from fastapi import HTTPException
    from app.api.deps import get_current_user

    with pytest.raises(HTTPException) as ei:
        await get_current_user(user=None)
    assert ei.value.status_code == 401
