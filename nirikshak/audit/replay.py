"""Audit drill — replay a verdict from frozen inputs (PRD §8.3)."""

import json
import logging
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nirikshak.core.schemas import (
    AuditLogEntry, Criterion, CriteriaSpec, EvidenceClaim,
    Verdict, VerdictState,
)
from nirikshak.verdict.engine import evaluate_criterion
import nirikshak.verdict.rules  # noqa: trigger registration

logger = logging.getLogger(__name__)


class ReplayResult(BaseModel):
    entry_hash: str
    bidder_id: str | None = None
    criterion_id: str | None = None
    historical_state: str | None = None
    recomputed_state: str | None = None
    match: bool
    chain_of_events: list[dict]
    divergence_reason: str | None = None
    recomputed_reason: str | None = None


async def replay_verdict(entry_hash: str, session: AsyncSession) -> ReplayResult:
    """Replay a verdict from frozen inputs.

    Given an audit entry hash (typically a rule_fired entry), reconstruct
    the full reasoning chain and re-run the verdict engine to verify consistency.
    """
    # 1. Fetch the target entry
    result = await session.execute(
        select(AuditLogEntry).where(AuditLogEntry.entry_hash == entry_hash)
    )
    target = result.scalar_one_or_none()
    if not target:
        return ReplayResult(
            entry_hash=entry_hash,
            match=False,
            chain_of_events=[],
            divergence_reason=f"Audit entry not found: {entry_hash[:16]}...",
        )

    payload = target.payload
    bidder_id = payload.get("bidder_id")
    criterion_id = payload.get("criterion_id") or payload.get("criterion")
    historical_state = payload.get("state")

    if not bidder_id or not criterion_id:
        return ReplayResult(
            entry_hash=entry_hash,
            match=False,
            chain_of_events=[_entry_to_dict(target)],
            divergence_reason="Entry does not contain bidder_id and criterion_id.",
        )

    # 2. Reconstruct the chain of events for this bidder+criterion
    all_entries_result = await session.execute(
        select(AuditLogEntry).order_by(AuditLogEntry.sequence.asc())
    )
    all_entries = all_entries_result.scalars().all()

    chain = []
    tender_id = None
    for e in all_entries:
        p = e.payload
        p_str = json.dumps(p, default=str)
        if bidder_id in p_str or (criterion_id and criterion_id in p_str):
            chain.append(_entry_to_dict(e))
            if not tender_id and "tender_id" in p:
                tender_id = p["tender_id"]
        elif e.action_type.value in ("tender_ingested", "criteria_extracted", "criteria_locked"):
            # Include tender-level events
            chain.append(_entry_to_dict(e))
            if not tender_id and "tender_id" in p:
                tender_id = p["tender_id"]

    # 3. Load the criterion from DB
    criterion = None
    if tender_id:
        try:
            tender_uuid = UUID(str(tender_id))
        except (ValueError, AttributeError):
            tender_uuid = None

        spec = None
        if tender_uuid:
            spec_result = await session.execute(
                select(CriteriaSpec)
                .where(CriteriaSpec.tender_id == tender_uuid)
                .order_by(CriteriaSpec.version.desc())
            )
            spec = spec_result.scalar_one_or_none()
        if spec:
            crit_result = await session.execute(
                select(Criterion).where(
                    Criterion.criteria_spec_id == spec.id,
                    Criterion.id == criterion_id,
                )
            )
            criterion = crit_result.scalar_one_or_none()

    if not criterion:
        return ReplayResult(
            entry_hash=entry_hash,
            bidder_id=bidder_id,
            criterion_id=criterion_id,
            historical_state=historical_state,
            match=False,
            chain_of_events=chain,
            divergence_reason=f"Criterion {criterion_id} not found in DB.",
        )

    # 4. Re-load the evidence from DB
    evidence_result = await session.execute(
        select(EvidenceClaim).where(
            EvidenceClaim.bidder_id == UUID(bidder_id),
            EvidenceClaim.criterion_id == criterion_id,
        )
    )
    evidence = list(evidence_result.scalars().all())

    # 5. Re-run the verdict engine
    recomputed = evaluate_criterion(criterion, evidence)
    recomputed_state = recomputed.state.value

    # 6. Compare
    match = (historical_state == recomputed_state)

    divergence_reason = None
    if not match:
        divergence_reason = (
            f"Historical verdict: {historical_state}, "
            f"Recomputed verdict: {recomputed_state}. "
            f"Evidence count: {len(evidence)}. "
            f"This may indicate non-determinism or data changes."
        )

    logger.info(
        "Replay %s: bidder=%s criterion=%s historical=%s recomputed=%s match=%s",
        entry_hash[:12], bidder_id[:8], criterion_id, historical_state, recomputed_state, match,
    )

    return ReplayResult(
        entry_hash=entry_hash,
        bidder_id=bidder_id,
        criterion_id=criterion_id,
        historical_state=historical_state,
        recomputed_state=recomputed_state,
        match=match,
        chain_of_events=chain,
        divergence_reason=divergence_reason,
        recomputed_reason=recomputed.reason_template,
    )


def _entry_to_dict(entry: AuditLogEntry) -> dict:
    return {
        "sequence": entry.sequence,
        "timestamp": entry.timestamp.isoformat(),
        "actor": entry.actor,
        "action_type": entry.action_type.value,
        "entry_hash": entry.entry_hash[:16] + "...",
        "payload_summary": _summarize_payload(entry.payload),
    }


def _summarize_payload(payload: dict) -> str:
    parts = []
    for k in ("tender_id", "bidder_id", "criterion_id", "state", "rule", "criteria_count"):
        if k in payload:
            val = str(payload[k])
            if len(val) > 12 and k.endswith("_id"):
                val = val[:8] + "..."
            parts.append(f"{k}={val}")
    return ", ".join(parts) if parts else json.dumps(payload, default=str)[:80]
