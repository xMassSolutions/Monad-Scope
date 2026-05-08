"""Prime worker — runs an in-flight Prime job and persists the result.

Picks up jobs created by `services.prime_state.purchase`. Runs the configured
provider, normalizes the output, commits a `PrimeAnalysis` row, and flips
`contract.prime_available`. On failure, marks the job failed (no result row).
"""

from __future__ import annotations

import asyncio

from app.db import session_scope
from app.logging import get_logger
from app.repositories import contracts as contracts_repo
from app.repositories import findings as findings_repo
from app.repositories import jobs as jobs_repo
from app.services import prime_state
from app.services.deep_analysis.manager import get_provider
from app.services.findings import HARD_FAIL_CODES

log = get_logger(__name__)


async def run_job(job_id: str) -> None:
    """Idempotent: if the job is already done/failed, returns silently."""
    async with session_scope() as session:
        job = await jobs_repo.get(session, job_id)
        if job is None:
            log.warning("prime.run.missing", job_id=job_id)
            return
        if job.status in ("done", "failed"):
            return
        await jobs_repo.mark_running(session, job_id)
        contract_id = job.payload.get("contract_id")
        contract = await contracts_repo.get_by_id(session, contract_id) if contract_id else None
        if contract is None:
            await jobs_repo.mark_failed(session, job_id, "contract not found")
            return
        sf = await contracts_repo.get_static_features(session, contract.id)
        df = await contracts_repo.get_dynamic_features(session, contract.id)
        finding_rows = await findings_repo.list_for_contract(session, contract.id)
        findings_payload = [
            {
                "code": f.code,
                "severity": f.severity,
                "weight": f.weight,
                "evidence": f.evidence,
                "source_type": f.source_type,
                "is_hard_fail": f.code in HARD_FAIL_CODES,
            }
            for f in finding_rows
        ]
        payload = prime_state.build_payload(
            contract=contract,
            static_features=sf,
            dynamic_features=df,
            findings=findings_payload,
        )

    provider = get_provider()
    try:
        result = await provider.analyze_contract(payload)
    except Exception as e:  # noqa: BLE001
        log.exception("prime.run.provider_error", job_id=job_id, err=str(e))
        async with session_scope() as session:
            await jobs_repo.mark_failed(session, job_id, str(e)[:1900])
        return

    async with session_scope() as session:
        contract = await contracts_repo.get_by_id(session, contract.id)
        await prime_state.commit_result(
            session,
            contract=contract,
            provider_name=provider.name,
            prime_version=provider.version,
            request_payload={
                "address": payload.address,
                "chain": payload.chain,
                "task": payload.task_instruction,
            },
            result=result,
        )
        await jobs_repo.mark_done(session, job_id, result={"provider": provider.name})

    log.info("prime.run.done", job_id=job_id, address=payload.address, provider=provider.name)
