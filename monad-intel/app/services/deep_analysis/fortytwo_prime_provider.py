"""Fortytwo Prime provider — MCP + x402Escrow path (no API key required).

Confirmed via official Fortytwo docs:
- MCP endpoint: POST https://mcp.fortytwo.network/mcp (JSON-RPC 2.0).
- Methods: initialize, tools/list (free), tools/call name=ask_fortytwo_prime (paid).
- Payment: HTTP 402 challenge → sign EIP-3009 ReceiveWithAuthorization for USDC
  (Monad chain 143 or Base chain 8453) against the Fortytwo escrow recipient
  → retry with header `payment-signature: <base64(json)>`.
- Successful responses include `x-session-id` (reuse for subsequent calls within
  the session window) and `payment-response` headers, plus a JSON-RPC `result`
  with `_meta.usage`.

The platform wallet (PLATFORM_WALLET_PRIVATE_KEY) is the only signer — end users
never sign anything for Fortytwo. If neither a wallet nor a legacy
FORTYTWO_API_KEY is configured, manager.py falls back to LocalProvider.

Legacy API-key path is still supported for back-compat but disabled by default.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

import httpx

from app.config import get_settings
from app.logging import get_logger
from app.services.deep_analysis.base import (
    DeepAnalysisProvider,
    NormalizedPrimeResult,
    PrimePayload,
)

log = get_logger(__name__)


SYSTEM_PROMPT = """You are an EVM smart-contract security analyst. Analyze the provided contract
for exploitable conditions. Return STRICT JSON ONLY (no prose, no code fences) with this schema:
{
  "attack_paths": [{"name": str, "steps": [str], "preconditions": [str], "severity": str}],
  "exploit_preconditions": [str],
  "likely_abuse_scenarios": [str],
  "blast_radius": {"affected_users": str, "asset_loss": str},
  "mitigations": [str],
  "narrative_summary": str
}
Be concrete and tied to the supplied features and findings."""


def _query_text(payload: PrimePayload) -> str:
    """The MCP tool takes a single `query` string. We pack the structured
    payload as JSON and prepend the system instruction."""
    body = {
        "chain": payload.chain,
        "address": payload.address,
        "contract_name": payload.contract_name,
        "verified": payload.verified,
        "verified_source_excerpt": (payload.verified_source or "")[:8000],
        "implementation_address": payload.implementation_address,
        "implementation_source_excerpt": (payload.implementation_source or "")[:8000],
        "static_features": payload.static_features,
        "dynamic_features": payload.dynamic_features,
        "findings": payload.findings,
        "risk_score": payload.risk_score,
        "confidence_score": payload.confidence_score,
        "task": payload.task_instruction,
    }
    return SYSTEM_PROMPT + "\n\nINPUT:\n" + json.dumps(body, default=str, separators=(",", ":"))


def _user_message_for_api(payload: PrimePayload) -> str:
    body = {
        "chain": payload.chain,
        "address": payload.address,
        "contract_name": payload.contract_name,
        "verified": payload.verified,
        "verified_source_excerpt": (payload.verified_source or "")[:8000],
        "implementation_address": payload.implementation_address,
        "implementation_source_excerpt": (payload.implementation_source or "")[:8000],
        "static_features": payload.static_features,
        "dynamic_features": payload.dynamic_features,
        "findings": payload.findings,
        "risk_score": payload.risk_score,
        "confidence_score": payload.confidence_score,
        "task": payload.task_instruction,
    }
    return json.dumps(body, default=str, separators=(",", ":"))


def _safe_get(d: dict[str, Any], key: str, default: Any) -> Any:
    v = d.get(key)
    return default if v is None else v


def _parse_json_loose(content: str) -> dict[str, Any]:
    """Tolerate stray prose / code fences around the JSON body."""
    s = content.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:].lstrip()
    # Find the outermost {...} if there's surrounding text.
    if not s.startswith("{"):
        i, j = s.find("{"), s.rfind("}")
        if i >= 0 and j > i:
            s = s[i : j + 1]
    return json.loads(s)


# ---------------------------------------------------------------------------
# MCP path
# ---------------------------------------------------------------------------


class _McpClient:
    """Thin async JSON-RPC over HTTPS client for the Fortytwo MCP endpoint.

    Caches the session id between calls within the process. On HTTP 402 it
    invokes the wallet signer (provided by the caller) and retries once.
    """

    def __init__(self) -> None:
        s = get_settings()
        self._url = s.fortytwo_mcp_url
        self._protocol = s.fortytwo_mcp_protocol_version
        self._client_name = s.fortytwo_mcp_client_name
        self._client_version = s.fortytwo_mcp_client_version
        self._tool = s.fortytwo_tool_name
        self._timeout = s.fortytwo_timeout_seconds
        self._session_id: str | None = None
        self._next_id = 1
        self._initialized = False
        self._session_created_at = 0.0
        # Sessions are tagged short-lived in the demo (~1h); we re-init defensively.
        self._session_max_age = 50 * 60
        self._lock = asyncio.Lock()

    def _id(self) -> int:
        i = self._next_id
        self._next_id += 1
        return i

    async def _initialize(self, http: httpx.AsyncClient) -> None:
        body = {
            "jsonrpc": "2.0",
            "id": self._id(),
            "method": "initialize",
            "params": {
                "protocolVersion": self._protocol,
                "capabilities": {},
                "clientInfo": {"name": self._client_name, "version": self._client_version},
            },
        }
        resp = await http.post(
            self._url,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json=body,
        )
        resp.raise_for_status()
        # initialize itself doesn't return a session id; that comes back from a
        # successful paid `tools/call`. We just confirm the server accepts us.
        self._initialized = True
        log.info("fortytwo.mcp.initialized", url=self._url)

    async def call_ask_prime(
        self,
        query: str,
        *,
        signer,  # WalletSigner | None — local import to avoid cycle
    ) -> dict[str, Any]:
        """Invoke `ask_fortytwo_prime`. Returns the JSON-RPC result body."""
        async with self._lock, httpx.AsyncClient(timeout=self._timeout) as http:
            now = time.time()
            if not self._initialized or now - self._session_created_at > self._session_max_age:
                await self._initialize(http)

            base_headers = {
                "Content-Type": "application/json",
                "Accept": "text/event-stream, application/json",
                "x-idempotency-key": str(uuid.uuid4()),
            }
            if self._session_id:
                base_headers["x-session-id"] = self._session_id

            request_body = {
                "jsonrpc": "2.0",
                "id": self._id(),
                "method": "tools/call",
                "params": {"name": self._tool, "arguments": {"query": query}},
            }

            resp = await http.post(self._url, headers=base_headers, json=request_body)
            if resp.status_code == 402:
                if signer is None:
                    raise RuntimeError(
                        "Fortytwo Prime requires payment but no platform wallet is configured "
                        "(set PLATFORM_WALLET_PRIVATE_KEY)."
                    )
                # Sign and retry with payment-signature header.
                from app.services.x402 import encode_payment_signature_header
                auth = signer.sign_authorization()
                header_value = encode_payment_signature_header(auth, signer.max_amount)
                paid_headers = {
                    **base_headers,
                    "payment-signature": header_value,
                }
                log.info(
                    "fortytwo.mcp.x402_signed",
                    chain=signer.chain,
                    chain_id=signer.chain_id,
                    client=signer.address,
                    max_amount=signer.max_amount,
                )
                resp = await http.post(self._url, headers=paid_headers, json=request_body)

            resp.raise_for_status()

            # Capture session id from response headers if present.
            sid = resp.headers.get("x-session-id")
            if sid:
                self._session_id = sid
                self._session_created_at = time.time()

            # The endpoint may return SSE or JSON. We negotiate JSON via Accept,
            # but tolerate either by parsing the body.
            text = resp.text
            try:
                rpc = json.loads(text)
            except json.JSONDecodeError:
                # Crude SSE parse: collect `data: ...` lines, last one wins.
                last_data = None
                for line in text.splitlines():
                    if line.startswith("data:"):
                        last_data = line[5:].strip()
                if not last_data:
                    raise
                rpc = json.loads(last_data)

            if "error" in rpc and rpc["error"] is not None:
                err = rpc["error"]
                raise RuntimeError(
                    f"Fortytwo MCP error [{err.get('code')}]: {err.get('message')}"
                )
            result = rpc.get("result") or {}
            return result


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class FortytwoPrimeProvider(DeepAnalysisProvider):
    """Routes to MCP+x402 if a platform wallet is configured; falls back to the
    legacy API-key path only when no wallet is configured but a key is."""

    name = "fortytwo-prime"
    version = "1.0"

    def __init__(self) -> None:
        s = get_settings()
        self._has_wallet = bool(s.platform_wallet_private_key)
        self._has_api_key = bool(s.fortytwo_api_key)
        if not self._has_wallet and not self._has_api_key:
            raise RuntimeError(
                "FortytwoPrimeProvider requires either PLATFORM_WALLET_PRIVATE_KEY "
                "(MCP+x402, no API key) or FORTYTWO_API_KEY (legacy)."
            )
        self._mcp = _McpClient() if self._has_wallet else None
        self._signer = None
        if self._has_wallet:
            from app.services.x402 import WalletSigner
            self._signer = WalletSigner()

    async def analyze_contract(self, payload: PrimePayload) -> NormalizedPrimeResult:
        if self._has_wallet:
            return await self._analyze_via_mcp(payload)
        return await self._analyze_via_api_key(payload)

    # ------------------------ MCP path ------------------------

    async def _analyze_via_mcp(self, payload: PrimePayload) -> NormalizedPrimeResult:
        result = await self._mcp.call_ask_prime(_query_text(payload), signer=self._signer)
        # MCP tool result shape: {content: [{type: "text", text: "..."}], _meta: {usage: {...}}}
        content_items = result.get("content") or []
        text = ""
        for item in content_items:
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                text = item["text"]
                break
        if not text:
            text = json.dumps(result, default=str)

        try:
            parsed = _parse_json_loose(text)
        except json.JSONDecodeError:
            log.warning("fortytwo.mcp.json_parse_failed", preview=text[:200])
            parsed = {"narrative_summary": text}

        return NormalizedPrimeResult(
            attack_paths=_safe_get(parsed, "attack_paths", []),
            exploit_preconditions=_safe_get(parsed, "exploit_preconditions", []),
            likely_abuse_scenarios=_safe_get(parsed, "likely_abuse_scenarios", []),
            blast_radius=_safe_get(parsed, "blast_radius", {}),
            mitigations=_safe_get(parsed, "mitigations", []),
            narrative_summary=str(parsed.get("narrative_summary") or ""),
            provider_metadata={
                "transport": "mcp",
                "tool": self._mcp._tool,
                "usage": (result.get("_meta") or {}).get("usage"),
                "wallet_chain": self._signer.chain if self._signer else None,
            },
        )

    # ------------------------ API-key path (legacy) ------------------------

    async def _analyze_via_api_key(self, payload: PrimePayload) -> NormalizedPrimeResult:
        s = get_settings()
        body = {
            "model": s.fortytwo_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _user_message_for_api(payload)},
            ],
            "max_tokens": s.fortytwo_max_tokens,
            "stream": False,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {s.fortytwo_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        url = s.fortytwo_api_base_url.rstrip("/") + "/chat/completions"
        async with httpx.AsyncClient(timeout=s.fortytwo_timeout_seconds) as http:
            resp = await http.post(url, headers=headers, json=body)
        if resp.status_code >= 400:
            log.error("fortytwo.api.http_error", status=resp.status_code, body=resp.text[:512])
            raise RuntimeError(f"Fortytwo API HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("Fortytwo API returned no choices")
        content = (choices[0].get("message") or {}).get("content") or ""
        try:
            parsed = _parse_json_loose(content)
        except json.JSONDecodeError:
            parsed = {"narrative_summary": content}

        return NormalizedPrimeResult(
            attack_paths=_safe_get(parsed, "attack_paths", []),
            exploit_preconditions=_safe_get(parsed, "exploit_preconditions", []),
            likely_abuse_scenarios=_safe_get(parsed, "likely_abuse_scenarios", []),
            blast_radius=_safe_get(parsed, "blast_radius", {}),
            mitigations=_safe_get(parsed, "mitigations", []),
            narrative_summary=str(parsed.get("narrative_summary") or ""),
            provider_metadata={
                "transport": "api-key",
                "model": data.get("model") or s.fortytwo_model,
                "id": data.get("id"),
                "usage": data.get("usage"),
            },
        )

        # TODO(streaming): real SSE parsing for stream=true. The non-streaming
        # path above is fully sufficient for our current usage.
