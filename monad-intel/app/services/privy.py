"""Privy auth — server-side JWT verification + user resolution.

Privy issues an access token (JWT, ES256) to the frontend. The frontend sends
that token in `Authorization: Bearer <token>` to our API. Here we:
  - Fetch + cache the app's JWKS public keys.
  - Verify the JWT signature, issuer, audience, and expiry.
  - Optionally enrich the principal with linked accounts via the Privy admin
    API (server-to-server with PRIVY_APP_SECRET).

The frontend wires up wallet connection + login UI via `@privy-io/react-auth`;
this module is the backend half — it never trusts client-supplied wallet
addresses, only what's signed by Privy or returned by the Privy admin API.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient, PyJWKClientError
from jwt.exceptions import InvalidTokenError

from app.config import get_settings
from app.logging import get_logger

log = get_logger(__name__)


@dataclass
class PrivyUser:
    """Authenticated principal from a verified Privy access token.

    `wallets` is populated only if the admin-API enrichment succeeds (or the
    JWT itself carries linked accounts in its custom claims, which Privy's
    standard tokens do not).
    """

    user_id: str
    issued_at: int | None = None
    expires_at: int | None = None
    raw_claims: dict[str, Any] = field(default_factory=dict)
    wallets: list[str] = field(default_factory=list)
    email: str | None = None


class PrivyVerifierError(Exception):
    pass


class PrivyVerifier:
    """JWKS-backed verifier with simple in-process caching.

    Thread-safe via an asyncio Lock around JWKS refresh.
    """

    _instance: "PrivyVerifier | None" = None

    def __init__(self) -> None:
        s = get_settings()
        if not s.privy_app_id:
            raise PrivyVerifierError("PRIVY_APP_ID is not configured")
        self._app_id = s.privy_app_id
        self._app_secret = s.privy_app_secret
        self._jwks_url = s.privy_jwks_url_template.format(app_id=s.privy_app_id)
        self._issuer = s.privy_issuer
        self._audience = s.privy_jwt_audience or s.privy_app_id
        self._jwk_client: PyJWKClient | None = None
        self._jwk_lock = asyncio.Lock()
        # User-cache for admin-API responses, keyed by user id.
        self._user_cache: dict[str, tuple[float, PrivyUser]] = {}
        self._user_cache_ttl = 60.0  # seconds

    @classmethod
    def get(cls) -> "PrivyVerifier":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_for_tests(cls) -> None:
        cls._instance = None

    async def _ensure_jwk_client(self) -> PyJWKClient:
        if self._jwk_client is not None:
            return self._jwk_client
        async with self._jwk_lock:
            if self._jwk_client is None:
                # PyJWKClient internally caches; we just construct it once.
                self._jwk_client = PyJWKClient(self._jwks_url, cache_keys=True, lifespan=600)
        return self._jwk_client

    async def verify(self, token: str) -> PrivyUser:
        """Verify a Privy access token and return the principal.

        Raises PrivyVerifierError on any failure.
        """
        try:
            jwk_client = await self._ensure_jwk_client()
            signing_key = await asyncio.to_thread(jwk_client.get_signing_key_from_jwt, token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except PyJWKClientError as e:
            raise PrivyVerifierError(f"jwks fetch failed: {e}") from e
        except InvalidTokenError as e:
            raise PrivyVerifierError(f"invalid token: {e}") from e

        sub = claims.get("sub")
        if not sub:
            raise PrivyVerifierError("token has no subject")

        user = PrivyUser(
            user_id=str(sub),
            issued_at=claims.get("iat"),
            expires_at=claims.get("exp"),
            raw_claims=claims,
        )
        return user

    async def enrich_with_admin_api(self, user: PrivyUser) -> PrivyUser:
        """Fetch linked accounts from the Privy admin API. No-op if no secret."""
        if not self._app_secret:
            return user

        # Check cache.
        cached = self._user_cache.get(user.user_id)
        now = time.time()
        if cached and now - cached[0] < self._user_cache_ttl:
            return cached[1]

        url = f"https://auth.privy.io/api/v1/users/{user.user_id}"
        headers = {"privy-app-id": self._app_id}
        auth = (self._app_id, self._app_secret)
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, auth=auth, headers=headers)
        except httpx.HTTPError as e:
            log.warning("privy.admin_api.error", err=str(e))
            return user
        if resp.status_code >= 400:
            log.warning("privy.admin_api.http_error", status=resp.status_code, body=resp.text[:200])
            return user
        data = resp.json()
        wallets: list[str] = []
        email: str | None = None
        for acct in data.get("linked_accounts") or []:
            t = acct.get("type")
            if t == "wallet" and acct.get("address"):
                wallets.append(str(acct["address"]).lower())
            elif t == "email" and acct.get("address"):
                email = str(acct["address"]).lower()
        user.wallets = wallets
        user.email = email
        self._user_cache[user.user_id] = (now, user)
        return user
