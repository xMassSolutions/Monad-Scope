"""Prime cache + lock + state machine — the billing critical path.

Public surface (used by the API + the worker):
- `find_existing(session, contract)` — checks cache (impl-hash → contract-key)
   and active jobs; returns a PrimeStatusBlock describing the current state.
- `purchase(session, redis, contract, payment)` — full purchase flow:
   acquire lock → re-check cache + active job → confirm payment → create job →
   release lock → return updated status. Idempotent under concurrency.
- `build_payload(...)` — assembles the structured request for the provider.
- `commit_result(...)` — stores a successful Prime result and flips
   `prime_available=True` on the contract row.
- `record_failure(...)` — marks the job failed (no result row).
"""

from __future__ import annotations

from typing import Any

from redis.asyncio import Redis
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.logging import get_logger
from app.models.contract import Contract
from app.models.prime import PrimeAnalysis
from app.repositories import contracts as contracts_repo
from app.repositories import findings as findings_repo
from app.repositories import jobs as jobs_repo
from app.repositories import prime as prime_repo
from app.schemas.prime import PrimeResultRead, PrimeStatusBlock
from app.schemas.common import PrimeState
from app.services.deep_analysis.base import NormalizedPrimeResult, PrimePayload
from app.utils.hashes import contract_key, implementation_cache_key
from app.utils.locks import redis_lock
from app.utils.time import utc_now

log = get_logger(__name__)


JOB_KIND = "prime"
DEFAULT_TASK_INSTRUCTION = (
    "Identify all plausible attack paths and exploit preconditions for this contract. "
    "Prioritize high-impact, low-precondition scenarios. Be concrete."
)


def _dedup_key_for(contract: Contract) -> str:
    if contract.implementation_hash:
        return implementation_cache_key(contract.implementation_hash, contract.bytecode_hash, contract.chain)
    if contract.bytecode_hash:
        return implementation_cache_key(None, contract.bytecode_hash, contract.chain)
    return contract_key(contract.address, contract.chain)


def _lock_key_for(contract: Contract) -> str:
    return f"prime:lock:{_dedup_key_for(contract)}"


def _result_to_read(row: PrimeAnalysis) -> PrimeResultRead:
    r = row.result_json or {}
    return PrimeResultRead(
        provider_name=row.provider_name,
        prime_version=row.prime_version,
        attack_paths=r.get("attack_paths", []),
        exploit_preconditions=r.get("exploit_preconditions", []),
        likely_abuse_scenarios=r.get("likely_abuse_scenarios", []),
        blast_radius=r.get("blast_radius", {}),
        mitigations=r.get("mitigations", []),
        narrative_summary=r.get("narrative_summary", ""),
        provider_metadata=r.get("provider_metadata", {}),
        created_at=row.created_at,
    )


async def find_existing(session: AsyncSession, contract: Contract) -> PrimeStatusBlock:
    """Look up cached Prime result + active job — order matters:
    1. impl-hash cache  2. contract-id cache  3. active job
    """
    settings = get_settings()
    cached: PrimeAnalysis | None = None
    if contract.implementation_hash:
        cached = await prime_repo.get_by_implementation_hash(session, contract.implementation_hash)
    if cached is None:
        cached = await prime_repo.get_by_contract_id(session, contract.id)
    if cached is not None:
        return PrimeStatusBlock(
            state=PrimeState.AVAILABLE,
            price_usd=0,
            result=_result_to_read(cached),
        )

    active = await jobs_repo.find_active(session, kind=JOB_KIND, dedup_key=_dedup_key_for(contract))
    if active is not None:
        return PrimeStatusBlock(
            state=PrimeState.IN_PROGRESS,
            price_usd=0,
            job_id=active.id,
        )

    return PrimeStatusBlock(
        state=PrimeState.NOT_PURCHASED,
        price_usd=settings.prime_price_usd,
    )


async def purchase(
    session: AsyncSession,
    redis: Redis,
    contract: Contract,
    payment_receipt: str,
) -> PrimeStatusBlock:
    """Full purchase flow with concurrency safety.

    Returns:
        - state=AVAILABLE if a result already exists (no charge, payment_receipt ignored).
        - state=IN_PROGRESS if a job is already running (no charge).
        - state=IN_PROGRESS if a new job is created (charge has been recorded).

    Raises:
        - RuntimeError if payment_receipt fails verification.
    """
    settings = get_settings()
    lock_key = _lock_key_for(contract)
    ttl_ms = settings.prime_lock_ttl_seconds * 1000

    async with redis_lock(redis, lock_key, ttl_ms=ttl_ms, blocking=2.0) as acquired:
        if not acquired:
            # Another request is mid-flight; treat as in-progress.
            return PrimeStatusBlock(
                state=PrimeState.IN_PROGRESS,
                price_usd=0,
            )

        # Re-check cache and active jobs INSIDE the lock — this is what makes
        # the "never charge twice" invariant hold.
        existing = await find_existing(session, contract)
        if existing.state in (PrimeState.AVAILABLE, PrimeState.IN_PROGRESS):
            return existing

        # Confirm payment. The platform's PSP integration is out of scope; we
        # accept a pre-validated receipt id from the API layer.
        if not _verify_payment(payment_receipt, settings.prime_price_usd):
            raise RuntimeError("payment verification failed")

        job = await jobs_repo.create_if_absent(
            session,
            kind=JOB_KIND,
            dedup_key=_dedup_key_for(contract),
            payload={
                "contract_id": contract.id,
                "address": contract.address,
                "implementation_hash": contract.implementation_hash,
                "bytecode_hash": contract.bytecode_hash,
                "payment_receipt": payment_receipt,
            },
        )
        if job is None:
            # Lost the race against another writer — treat as in_progress, do not charge.
            log.info("prime.purchase.race_lost", address=contract.address)
            return PrimeStatusBlock(state=PrimeState.IN_PROGRESS, price_usd=0)

        log.info("prime.purchase.created_job", job_id=job.id, address=contract.address)
        return PrimeStatusBlock(state=PrimeState.IN_PROGRESS, price_usd=0, job_id=job.id)


def _verify_payment(receipt: str, expected_usd: int) -> bool:
    """Stub. Replace with real PSP verification.

    The receipt is opaque to this module; the API layer should call the PSP
    and pass the verified receipt id here. We accept any non-empty string as
    "verified" so the system is functional out of the box; production must
    swap this out for a real implementation."""
    return bool(receipt)


def build_payload(
    *,
    contract: Contract,
    static_features: dict[str, Any],
    dynamic_features: dict[str, Any],
    findings: list[dict[str, Any]],
    verified_source: str | None = None,
    implementation_source: str | None = None,
    task_instruction: str = DEFAULT_TASK_INSTRUCTION,
) -> PrimePayload:
    return PrimePayload(
        chain=contract.chain,
        address=contract.address,
        contract_name=contract.contract_name,
        verified=contract.verified,
        verified_source=verified_source,
        implementation_address=contract.implementation_address,
        implementation_source=implementation_source,
        static_features=static_features,
        dynamic_features=dynamic_features,
        findings=findings,
        risk_score=contract.risk_score,
        confidence_score=contract.confidence_score,
        task_instruction=task_instruction,
    )


async def commit_result(
    session: AsyncSession,
    *,
    contract: Contract,
    provider_name: str,
    prime_version: str,
    request_payload: dict[str, Any],
    result: NormalizedPrimeResult,
) -> PrimeAnalysis:
    row = PrimeAnalysis(
        contract_id=contract.id,
        implementation_hash=contract.implementation_hash,
        provider_name=provider_name,
        prime_version=prime_version,
        request_payload=request_payload,
        result_json={
            "attack_paths": result.attack_paths,
            "exploit_preconditions": result.exploit_preconditions,
            "likely_abuse_scenarios": result.likely_abuse_scenarios,
            "blast_radius": result.blast_radius,
            "mitigations": result.mitigations,
            "narrative_summary": result.narrative_summary,
            "provider_metadata": result.provider_metadata,
        },
        created_at=utc_now(),
        public_visible=True,
    )
    await prime_repo.insert(session, row)
    await session.execute(
        update(Contract).where(Contract.id == contract.id).values(prime_available=True)
    )
    return row


async def assemble_status_block(session: AsyncSession, contract: Contract) -> PrimeStatusBlock:
    """Convenience wrapper for the API layer."""
    return await find_existing(session, contract)
