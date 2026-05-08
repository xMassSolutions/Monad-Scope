"""Dynamic feature scaffolding.

Real on-chain liquidity / holder data requires either an indexer or per-pool
RPC scrapes that are out of scope for this scaffold. We expose the canonical
key set with all values nullable, and provide hooks the caller can fill in.

Callers should pass any data they have (creator launch counts, owner deltas
they observed elsewhere). Missing fields stay None — the scoring engine
penalizes confidence rather than risk for unknowns.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.utils.time import utc_now

DYNAMIC_FEATURE_KEYS = (
    "has_liquidity",
    "liquidity_usd",
    "liquidity_lock_days",
    "holder_count",
    "top_10_holder_pct",
    "tx_count_1d",
    "tx_count_7d",
    "pool_age_days",
    "deployer_launch_count",
    "deployer_suspicious_count",
    "owner_changed_recently",
    "implementation_changed_recently",
)


def empty_dynamic_features() -> dict[str, Any]:
    return {k: None for k in DYNAMIC_FEATURE_KEYS}


def merge_dynamic_features(base: dict[str, Any], partial: dict[str, Any]) -> dict[str, Any]:
    """Merge a partial update — only non-None values overwrite."""
    out = dict(base)
    for k, v in partial.items():
        if k in DYNAMIC_FEATURE_KEYS and v is not None:
            out[k] = v
    return out


def is_recent(ts: datetime | None, within: timedelta) -> bool | None:
    if ts is None:
        return None
    return (utc_now() - ts) <= within


async def collect_dynamic_features(
    *,
    contract_address: str,
    creator_address: str | None,
    deployer_launch_count: int | None = None,
    deployer_suspicious_count: int | None = None,
    owner_change_at: datetime | None = None,
    implementation_change_at: datetime | None = None,
) -> dict[str, Any]:
    """Best-effort collector. Real adapters (indexer, DEX) plug in via the
    optional kwargs above. Returns the canonical dict shape."""
    feats = empty_dynamic_features()
    feats["deployer_launch_count"] = deployer_launch_count
    feats["deployer_suspicious_count"] = deployer_suspicious_count
    feats["owner_changed_recently"] = is_recent(owner_change_at, timedelta(days=2))
    feats["implementation_changed_recently"] = is_recent(implementation_change_at, timedelta(days=2))
    return feats
