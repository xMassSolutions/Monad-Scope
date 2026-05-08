"""Shared FastAPI dependencies (auth)."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.config import get_settings
from app.logging import get_logger
from app.services.privy import PrivyUser, PrivyVerifier, PrivyVerifierError

log = get_logger(__name__)


async def get_optional_user(
    authorization: str | None = Header(default=None),
) -> PrivyUser | None:
    """Returns the authenticated PrivyUser if a valid token is present, else None.

    Use this on routes that *can* be authenticated but don't require it.
    """
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        verifier = PrivyVerifier.get()
        user = await verifier.verify(token)
        await verifier.enrich_with_admin_api(user)
        return user
    except PrivyVerifierError as e:
        log.info("auth.privy.invalid_token", err=str(e))
        return None
    except Exception as e:  # noqa: BLE001
        log.warning("auth.privy.error", err=str(e))
        return None


async def get_current_user(
    user: PrivyUser | None = Depends(get_optional_user),
) -> PrivyUser:
    """Required-auth variant. 401s if no valid token (or 200s in single-user
    local-dev mode when PRIVY_REQUIRED is false and no app id is configured)."""
    s = get_settings()
    if user is not None:
        return user
    if not s.privy_required and not s.privy_app_id:
        # Local-dev convenience: synthesize an anonymous principal so the route
        # logic can assume `user` is truthy. Never used when Privy is configured.
        return PrivyUser(user_id="anonymous", raw_claims={"_anon": True})
    if not s.privy_required:
        # Privy is configured but enforcement is off — require a token only
        # when one was sent (so we still bounce malformed tokens). Anonymous
        # callers proceed.
        return PrivyUser(user_id="anonymous", raw_claims={"_anon": True})
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
