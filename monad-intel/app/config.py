"""Centralized configuration. All env vars live here, nowhere else."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # core
    app_env: Literal["dev", "staging", "prod"] = "dev"
    log_level: str = "INFO"

    # db
    database_url: str = "sqlite+aiosqlite:///./monad_intel.db"
    database_echo: bool = False

    # redis
    redis_url: str = "redis://localhost:6379/0"

    # chain
    monad_chain: str = "monad"
    monad_chain_id: int = 143
    monad_rpc_http: str = "https://rpc.monad.xyz"
    monad_rpc_ws: str = "wss://rpc.monad.xyz"
    monad_ws_subscription: Literal["newHeads", "monadNewHeads"] = "newHeads"
    rpc_timeout_seconds: float = 15.0
    rpc_max_retries: int = 4
    receipt_retry_attempts: int = 8
    receipt_retry_base_ms: int = 120

    # ingestion
    bootstrap_chunk_size: int = 50
    block_queue_maxsize: int = 512
    enrichment_concurrency: int = 8

    # verification
    sourcify_base_url: str = "https://sourcify-api-monad.blockvision.org"
    etherscan_v2_base_url: str = "https://api.etherscan.io/v2/api"
    etherscan_api_key: str = ""

    # Fortytwo Prime (enabled by default; manager.py still requires either a
    # platform wallet OR an API key to actually route to the real provider —
    # otherwise it falls back to LocalProvider, which never charges).
    fortytwo_prime_enabled: bool = True

    # MCP / x402 path — preferred. No API key, pays via the platform wallet.
    fortytwo_mcp_url: str = "https://mcp.fortytwo.network/mcp"
    fortytwo_mcp_protocol_version: str = "2025-11-25"
    fortytwo_mcp_client_name: str = "monad-scope"
    fortytwo_mcp_client_version: str = "0.1.0"
    fortytwo_tool_name: str = "ask_fortytwo_prime"

    # Platform wallet — signs EIP-3009 authorizations against USDC.
    # Hex (with or without 0x). Empty = wallet path disabled.
    platform_wallet_private_key: str = ""
    # "monad" or "base". USDC is paid in this chain's native USDC contract.
    platform_wallet_chain: str = "monad"
    # x402 payment cap per request, in USDC base units (USDC has 6 decimals).
    fortytwo_max_payment_usdc_units: int = 2_000_000  # 2 USDC

    # USDC contract addresses (Fortytwo-supported).
    usdc_monad_address: str = "0x754704Bc059F8C67012fEd69BC8A327a5aafb603"
    usdc_base_address: str = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    # Fortytwo escrow recipient (deployed on both Monad and Base).
    fortytwo_escrow_recipient: str = "0x9562f50f73d8ee22276f13a18d051456d8d137a0"

    # Legacy API-key path — kept as a fallback only. Empty by default.
    fortytwo_api_base_url: str = "https://api.fortytwo.network/v1"
    fortytwo_api_key: str = ""
    fortytwo_model: str = "fortytwo-prime"
    fortytwo_timeout_seconds: float = 120.0
    fortytwo_max_tokens: int = 4096

    # billing
    prime_price_usd: int = 6
    prime_lock_ttl_seconds: int = 60

    # Privy (user wallet auth — frontend uses @privy-io/react-auth, backend verifies JWTs).
    privy_app_id: str = ""
    privy_app_secret: str = ""  # server-side only, never sent to clients
    privy_jwks_url_template: str = "https://auth.privy.io/api/v1/apps/{app_id}/jwks.json"
    privy_issuer: str = "privy.io"
    privy_jwt_audience: str = ""  # defaults to app_id when empty
    # If true, endpoints requiring auth will reject unauthenticated requests.
    # If false (single-user / local dev), routes still accept unauthenticated calls.
    privy_required: bool = False

    # scoring
    default_ruleset_version: int = 1

    # ---------------- helpers ----------------

    @property
    def rpc_http_urls(self) -> list[str]:
        return [u.strip() for u in self.monad_rpc_http.split(",") if u.strip()]

    @field_validator("log_level")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
