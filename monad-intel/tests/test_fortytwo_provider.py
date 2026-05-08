"""FortytwoPrimeProvider tests.

Cover:
- Manager falls back to MockProvider in dev with no wallet/key.
- With a wallet configured, the provider uses the MCP path: it sends
  `initialize`, then `tools/call`, signs on 402, and parses `content.text`.
- The non-streaming JSON response shape is decoded into NormalizedPrimeResult.

We use httpx.MockTransport so we never hit the real network.
"""

from __future__ import annotations

import base64
import json

import httpx
import pytest

from app.services.deep_analysis.base import PrimePayload


def _payload() -> PrimePayload:
    return PrimePayload(
        chain="monad",
        address="0x" + "11" * 20,
        contract_name="Token",
        verified=True,
        verified_source="contract Token { ... }",
        implementation_address=None,
        implementation_source=None,
        static_features={"owner_can_mint": True, "is_proxy": False},
        dynamic_features={"has_liquidity": False},
        findings=[{"code": "OWNER_CAN_MINT", "severity": "high", "weight": 18}],
        risk_score=42.0,
        confidence_score=0.7,
        task_instruction="audit",
    )


def test_manager_dev_no_wallet_returns_mock(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("PLATFORM_WALLET_PRIVATE_KEY", "")
    monkeypatch.setenv("FORTYTWO_API_KEY", "")
    from app.config import get_settings
    get_settings.cache_clear()  # type: ignore[attr-defined]
    from app.services.deep_analysis.manager import get_provider

    p = get_provider()
    assert p.name == "mock"
    get_settings.cache_clear()  # type: ignore[attr-defined]


def test_manager_prefers_wallet_when_available(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv(
        "PLATFORM_WALLET_PRIVATE_KEY",
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    )
    monkeypatch.setenv("PLATFORM_WALLET_CHAIN", "monad")
    monkeypatch.setenv("FORTYTWO_API_KEY", "")
    from app.config import get_settings
    get_settings.cache_clear()  # type: ignore[attr-defined]
    from app.services.deep_analysis.manager import get_provider

    p = get_provider()
    assert p.name == "fortytwo-prime"
    get_settings.cache_clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_mcp_path_signs_on_402_and_parses_result(monkeypatch) -> None:
    """End-to-end MCP flow over an httpx mock transport."""
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv(
        "PLATFORM_WALLET_PRIVATE_KEY",
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    )
    monkeypatch.setenv("PLATFORM_WALLET_CHAIN", "monad")
    monkeypatch.setenv("FORTYTWO_API_KEY", "")
    monkeypatch.setenv("FORTYTWO_PRIME_ENABLED", "true")
    from app.config import get_settings
    get_settings.cache_clear()  # type: ignore[attr-defined]

    state = {"step": 0, "saw_signature": False}

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        state["step"] += 1
        # 1st request: initialize → 200 with empty result.
        if body.get("method") == "initialize":
            return httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": body["id"], "result": {"protocolVersion": "2025-11-25"}},
            )
        # 2nd request: tools/call without payment-signature → 402.
        if body.get("method") == "tools/call" and "payment-signature" not in req.headers:
            return httpx.Response(402, text="payment required")
        # 3rd request: tools/call with payment-signature → 200 result.
        if body.get("method") == "tools/call" and "payment-signature" in req.headers:
            state["saw_signature"] = True
            sig = req.headers["payment-signature"]
            decoded = json.loads(base64.b64decode(sig).decode("utf-8"))
            assert decoded["client"].startswith("0x")
            assert int(decoded["maxAmount"]) == 2_000_000
            mock_result = {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "attack_paths": [{"name": "x", "steps": ["a"], "preconditions": [], "severity": "high"}],
                            "exploit_preconditions": ["owner_can_mint"],
                            "likely_abuse_scenarios": ["dilution"],
                            "blast_radius": {"affected_users": "holders", "asset_loss": "partial"},
                            "mitigations": ["renounce"],
                            "narrative_summary": "ok",
                        }),
                    }
                ],
                "_meta": {"usage": {"prompt_tokens": 100, "completion_tokens": 50}},
            }
            return httpx.Response(
                200,
                headers={"x-session-id": "sess-123"},
                json={"jsonrpc": "2.0", "id": body["id"], "result": mock_result},
            )
        return httpx.Response(500, text="unexpected")

    transport = httpx.MockTransport(handler)

    # Patch httpx.AsyncClient inside the provider module to use our transport.
    from app.services.deep_analysis import fortytwo_prime_provider as ftp

    real_async_client = httpx.AsyncClient

    def make_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(ftp.httpx, "AsyncClient", make_client)

    provider = ftp.FortytwoPrimeProvider()
    result = await provider.analyze_contract(_payload())

    assert state["saw_signature"] is True
    assert state["step"] == 3  # initialize + unpaid 402 + paid 200
    assert result.exploit_preconditions == ["owner_can_mint"]
    assert result.narrative_summary == "ok"
    assert result.provider_metadata["transport"] == "mcp"
    assert result.provider_metadata["wallet_chain"] == "monad"

    get_settings.cache_clear()  # type: ignore[attr-defined]
