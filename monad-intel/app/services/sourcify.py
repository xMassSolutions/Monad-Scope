"""Sourcify-Monad adapter (Blockvision-hosted).

Endpoint shape follows the standard Sourcify server API:
    GET {base}/files/any/{chainId}/{address}

Returns a small dict: {verified: bool, source: str|None, name: str|None, metadata: dict|None}.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.logging import get_logger

log = get_logger(__name__)


class SourcifyAdapter:
    name = "sourcify"

    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        s = get_settings()
        self._base = (base_url or s.sourcify_base_url).rstrip("/")
        self._chain_id = s.monad_chain_id
        self._timeout = timeout

    async def lookup(self, address: str) -> dict[str, Any]:
        url = f"{self._base}/files/any/{self._chain_id}/{address}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
        except httpx.HTTPError as e:
            log.warning("sourcify.error", err=str(e))
            return {"verified": False, "source": None, "name": None, "metadata": None}
        if resp.status_code == 404:
            return {"verified": False, "source": None, "name": None, "metadata": None}
        if resp.status_code >= 400:
            log.warning("sourcify.http_error", status=resp.status_code)
            return {"verified": False, "source": None, "name": None, "metadata": None}
        try:
            data = resp.json()
        except ValueError:
            return {"verified": False, "source": None, "name": None, "metadata": None}

        # Sourcify response: {"status": "full"|"partial", "files": [{name, content, ...}]}.
        status = data.get("status")
        files = data.get("files") or []
        meta_file = next((f for f in files if f.get("name") == "metadata.json"), None)
        sources = [f for f in files if f.get("name", "").endswith(".sol")]
        metadata = None
        if meta_file:
            try:
                import json as _j

                metadata = _j.loads(meta_file["content"])
            except Exception:  # noqa: BLE001
                metadata = None
        contract_name = None
        if metadata:
            settings = (metadata.get("settings") or {}).get("compilationTarget") or {}
            if settings:
                contract_name = next(iter(settings.values()), None)
        source_text = "\n\n".join((f.get("content") or "") for f in sources) or None
        return {
            "verified": status in ("full", "partial"),
            "source": source_text,
            "name": contract_name,
            "metadata": metadata,
        }
