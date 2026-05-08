"""Per-contract enrichment pipeline.

Orchestrates: bytecode -> verification -> proxy detection -> classification ->
static features -> findings -> scoring -> persistence -> grouping -> schedule next.

Pure orchestration: each step delegates to a service. The pipeline is called
from `workers/enrichment.py` for new contracts and from `workers/rescans.py`
for refreshes (with `stage='refined'`).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.models.analysis import ContractAnalysis
from app.models.contract import Contract
from app.repositories import analyses as analyses_repo
from app.repositories import contracts as contracts_repo
from app.repositories import findings as findings_repo
from app.repositories import projects as projects_repo
from app.repositories import rulesets as rulesets_repo
from app.services import exploit_match as exploit_match_svc
from app.services import grouping as grouping_svc
from app.services import scoring as scoring_svc
from app.services.classifier import classify
from app.services.feature_dynamic import collect_dynamic_features, empty_dynamic_features
from app.services.feature_static import extract_static_features
from app.services.findings import compute_findings
from app.services.rpc import JsonRpcClient
from app.services.scheduler import next_refresh
from app.services.verifier import Verifier
from app.utils.hashes import bytecode_hash, implementation_hash
from app.utils.time import utc_now

log = get_logger(__name__)


# EIP-1967 implementation slot:
# bytes32(uint256(keccak256("eip1967.proxy.implementation")) - 1)
EIP1967_IMPL_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"


async def _resolve_implementation_address(rpc: JsonRpcClient, address: str) -> str | None:
    try:
        raw = await rpc.get_storage_at(address, EIP1967_IMPL_SLOT)
    except Exception:  # noqa: BLE001
        return None
    if not raw or raw in ("0x", "0x0"):
        return None
    # Last 20 bytes of the 32-byte slot.
    h = raw[2:] if raw.startswith("0x") else raw
    if len(h) < 40:
        return None
    addr = "0x" + h[-40:].lower()
    if int(addr, 16) == 0:
        return None
    return addr


async def enrich_contract(
    session: AsyncSession,
    rpc: JsonRpcClient,
    verifier: Verifier,
    contract: Contract,
    *,
    stage: str = "initial",
    dynamic_overrides: dict[str, Any] | None = None,
) -> ContractAnalysis:
    """Run the full pipeline for a single contract; return the persisted analysis."""

    # 1. Bytecode + hashes.
    code = await rpc.get_code(contract.address)
    bcode_hash = bytecode_hash(code)
    impl_hash = implementation_hash(code)

    # 2. Verification (best-effort).
    v = await verifier.lookup(contract.address)
    source = v.get("source")
    name = v.get("name")
    verified = bool(v.get("verified"))
    verifier_source = v.get("verifier_source")

    # 3. Proxy detection.
    impl_address = await _resolve_implementation_address(rpc, contract.address)
    is_proxy = impl_address is not None
    impl_verified: bool | None = None
    if is_proxy:
        impl_v = await verifier.lookup(impl_address)
        impl_verified = bool(impl_v.get("verified"))
        # Override impl_hash with the resolved implementation's bytecode if we can fetch it.
        try:
            impl_code = await rpc.get_code(impl_address)
            if impl_code and impl_code not in ("0x", "0x0"):
                impl_hash = implementation_hash(impl_code)
        except Exception:  # noqa: BLE001
            pass

    # 4. Classification.
    kind = classify(
        code_hex=code,
        is_proxy=is_proxy,
        contract_name=name,
        metadata_hint=name,
    )

    # 5. Static features.
    static_features = extract_static_features(
        code_hex=code,
        source=source,
        is_proxy=is_proxy,
        implementation_verified=impl_verified,
        source_verified=verified,
    )

    # 6. Dynamic features (best-effort; empty in `initial` unless overrides given).
    if stage == "refined" or dynamic_overrides:
        df = await collect_dynamic_features(
            contract_address=contract.address,
            creator_address=contract.creator_address,
        )
        if dynamic_overrides:
            from app.services.feature_dynamic import merge_dynamic_features
            df = merge_dynamic_features(df, dynamic_overrides)
    else:
        df = empty_dynamic_features()

    # 7. Findings — using the active ruleset.
    active_ruleset = await rulesets_repo.get_active(session)
    weights = (active_ruleset.weights_json if active_ruleset else None) or None
    findings = compute_findings(
        static_features=static_features, dynamic_features=df, weights=weights
    )

    # 8. Match against the historical-exploit registry, then score.
    finding_codes = [f.code for f in findings]
    exploit_report = await exploit_match_svc.match_for_codes(session, finding_codes)
    verdict = scoring_svc.score(
        static_features=static_features,
        dynamic_features=df,
        findings=findings,
        weights=weights,
        exploit_match=exploit_report,
    )

    # 9. Persist features + findings + analysis.
    await contracts_repo.upsert_static_features(session, contract.id, static_features)
    if stage == "refined" or dynamic_overrides:
        await contracts_repo.upsert_dynamic_features(session, contract.id, df)
    await findings_repo.replace_findings(session, contract.id, findings)

    next_version = await analyses_repo.next_version(session, contract.id)
    analysis = ContractAnalysis(
        contract_id=contract.id,
        analysis_version=next_version,
        risk_score=verdict.risk_score,
        confidence_score=verdict.confidence_score,
        risk_tier=verdict.risk_tier,
        action=verdict.action,
        analysis_stage=stage,
        summary_json=verdict.summary,
        unknowns_json=verdict.unknowns,
        created_at=utc_now(),
    )
    await analyses_repo.insert(session, analysis)

    # 10. Update contract row.
    next_due = next_refresh(
        risk_tier=verdict.risk_tier,
        has_liquidity=bool(df.get("has_liquidity")),
        is_live_project=False,
    )
    await contracts_repo.update_enrichment(
        session,
        contract.id,
        bytecode_hash=bcode_hash,
        implementation_hash=impl_hash,
        is_proxy=is_proxy,
        implementation_address=impl_address,
        verified=verified,
        verifier_source=verifier_source,
        contract_name=name,
        kind=kind,
        risk_score=verdict.risk_score,
        confidence_score=verdict.confidence_score,
        risk_tier=verdict.risk_tier,
        action=verdict.action,
        analysis_stage=stage,
        last_refreshed_at=utc_now(),
        next_refresh_at=next_due,
    )

    # 11. Project grouping (only on initial enrichment; regroup runs separately).
    if stage == "initial":
        # Re-fetch contract (we just updated it).
        fresh = await contracts_repo.get_by_id(session, contract.id)
        if fresh is not None:
            await grouping_svc.assign_first_pass(session, fresh)
            if fresh.project_id:
                await projects_repo.touch_last_seen(session, fresh.project_id)

    log.info(
        "enrichment.done",
        address=contract.address,
        kind=kind,
        risk=verdict.risk_score,
        tier=verdict.risk_tier,
        stage=stage,
    )
    return analysis
