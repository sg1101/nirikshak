"""Criteria spec construction, versioning, and locking (PRD §5.2 + §7)."""

import logging
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nirikshak.audit.chain import append_entry
from nirikshak.core.hashing import content_hash_json
from nirikshak.core.schemas import (
    AuditActionType,
    Criterion,
    CriteriaSpec,
    MinedCriteriaList,
    MinedCriterion,
)

logger = logging.getLogger(__name__)


async def build_spec(
    session: AsyncSession,
    tender_id: UUID,
    criteria: list[Criterion],
) -> CriteriaSpec:
    """Create a new CriteriaSpec from mined criteria. Saves to DB + audit log."""
    spec = CriteriaSpec(
        id=uuid4(),
        tender_id=tender_id,
        version=1,
    )

    # Compute content hash from criteria list
    criteria_data = MinedCriteriaList(criteria=[
        MinedCriterion(
            suggested_id=c.id,
            type=c.type,
            description=c.description,
            mandatory=c.mandatory,
            parameters=c.parameters,
            source_page=c.source_page,
            source_quote=c.source_quote,
        )
        for c in criteria
    ])
    spec.content_hash = content_hash_json(criteria_data)

    session.add(spec)
    await session.flush()

    # Assign spec ID to criteria and save
    for c in criteria:
        c.criteria_spec_id = spec.id
        session.add(c)

    await session.flush()

    # Audit entry
    await append_entry(
        session,
        actor="system",
        action_type=AuditActionType.criteria_extracted,
        payload={
            "tender_id": str(tender_id),
            "criteria_spec_id": str(spec.id),
            "content_hash": spec.content_hash,
            "criteria_count": len(criteria),
        },
    )

    logger.info("Built CriteriaSpec %s with %d criteria (hash=%s)", spec.id, len(criteria), spec.content_hash[:12])
    return spec


async def lock_spec(
    session: AsyncSession,
    spec_id: UUID,
    officer_email: str,
) -> CriteriaSpec:
    """Lock a CriteriaSpec — makes it immutable for downstream evaluation."""
    result = await session.execute(select(CriteriaSpec).where(CriteriaSpec.id == spec_id))
    spec = result.scalar_one_or_none()
    if spec is None:
        raise ValueError(f"CriteriaSpec not found: {spec_id}")
    if spec.locked_at is not None:
        raise ValueError(f"CriteriaSpec already locked at {spec.locked_at}")

    spec.locked_at = datetime.utcnow()
    spec.locked_by = officer_email
    session.add(spec)
    await session.flush()

    await append_entry(
        session,
        actor=officer_email,
        action_type=AuditActionType.criteria_locked,
        payload={
            "tender_id": str(spec.tender_id),
            "criteria_spec_id": str(spec.id),
            "content_hash": spec.content_hash,
            "locked_by": officer_email,
        },
    )

    logger.info("Locked CriteriaSpec %s by %s", spec.id, officer_email)
    return spec


async def get_locked_spec(session: AsyncSession, tender_id: UUID) -> CriteriaSpec | None:
    """Return the latest locked spec for a tender, or None."""
    result = await session.execute(
        select(CriteriaSpec)
        .where(CriteriaSpec.tender_id == tender_id, CriteriaSpec.locked_at.isnot(None))
        .order_by(CriteriaSpec.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_criteria_for_spec(session: AsyncSession, spec_id: UUID) -> list[Criterion]:
    """Return all criteria belonging to a spec."""
    result = await session.execute(
        select(Criterion).where(Criterion.criteria_spec_id == spec_id)
    )
    return list(result.scalars().all())
