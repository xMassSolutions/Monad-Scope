"""Auth-related routes — /auth/me + /auth/config (public)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_optional_user
from app.config import get_settings
from app.services.privy import PrivyUser

router = APIRouter()


@router.get("/auth/config")
async def auth_config() -> dict:
    """Public config the frontend needs to initialize Privy. App secret is NEVER returned."""
    s = get_settings()
    return {
        "privy_app_id": s.privy_app_id or None,
        "privy_required": s.privy_required,
        "supported_chains": ["monad", "base"],
        "monad_chain_id": s.monad_chain_id,
    }


@router.get("/auth/me")
async def me(user: PrivyUser | None = Depends(get_optional_user)) -> dict:
    if user is None:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "user_id": user.user_id,
        "wallets": user.wallets,
        "email": user.email,
    }
