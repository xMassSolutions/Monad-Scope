"""Provider selection + cache-first policy.

Routing rules (in priority order):
1. FORTYTWO_PRIME_ENABLED + PLATFORM_WALLET_PRIVATE_KEY set → FortytwoPrimeProvider (MCP + x402, no API key).
2. FORTYTWO_PRIME_ENABLED + FORTYTWO_API_KEY set         → FortytwoPrimeProvider (legacy API-key path).
3. APP_ENV=dev                                            → MockProvider (deterministic, free).
4. Else                                                   → LocalProvider (deterministic, free).

The cache-first check happens in `prime_state.find_existing` — the manager
only runs when `prime_state` has confirmed there is no existing result and no
active job. This keeps "never charge twice" enforceable from one place.
"""

from __future__ import annotations

from app.config import get_settings
from app.logging import get_logger
from app.services.deep_analysis.base import DeepAnalysisProvider
from app.services.deep_analysis.fortytwo_prime_provider import FortytwoPrimeProvider
from app.services.deep_analysis.local_provider import LocalProvider
from app.services.deep_analysis.mock_provider import MockProvider

log = get_logger(__name__)


def get_provider() -> DeepAnalysisProvider:
    s = get_settings()
    if s.fortytwo_prime_enabled and (s.platform_wallet_private_key or s.fortytwo_api_key):
        try:
            return FortytwoPrimeProvider()
        except Exception as e:  # noqa: BLE001
            # If construction fails (bad key, etc.), degrade gracefully.
            log.warning("manager.fortytwo_init_failed", err=str(e))
    if s.app_env == "dev":
        return MockProvider()
    return LocalProvider()
