"""Verifier facade — pluggable adapters in priority order.

Adapters return a uniform dict:
    {verified: bool, source: str|None, name: str|None, metadata: dict|None}
The first adapter that returns verified=True wins; otherwise we fall back
to unverified state.
"""

from __future__ import annotations

from typing import Any, Protocol

from app.logging import get_logger
from app.services.sourcify import SourcifyAdapter

log = get_logger(__name__)


class VerifierAdapter(Protocol):
    name: str

    async def lookup(self, address: str) -> dict[str, Any]: ...


class Verifier:
    def __init__(self, adapters: list[VerifierAdapter] | None = None) -> None:
        self._adapters: list[VerifierAdapter] = adapters or [SourcifyAdapter()]

    def add(self, adapter: VerifierAdapter) -> None:
        self._adapters.append(adapter)

    async def lookup(self, address: str) -> dict[str, Any]:
        for adapter in self._adapters:
            try:
                result = await adapter.lookup(address)
            except Exception as e:  # noqa: BLE001
                log.warning("verifier.adapter_error", adapter=adapter.name, err=str(e))
                continue
            if result.get("verified"):
                return {**result, "verifier_source": adapter.name}
        return {
            "verified": False,
            "source": None,
            "name": None,
            "metadata": None,
            "verifier_source": None,
        }
