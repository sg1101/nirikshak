"""Hash-chained, append-only audit log — PRD §8."""

import json
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from nirikshak.core.hashing import GENESIS_HASH, chain_hash, content_hash
from nirikshak.core.schemas import AuditActionType, AuditLogEntry


async def append_entry(
    session: AsyncSession,
    actor: str,
    action_type: AuditActionType,
    payload: dict,
) -> AuditLogEntry:
    """Append a new entry to the audit chain. Must be called within a transaction."""
    # Serialize payload deterministically for hashing
    payload_raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    p_hash = content_hash(payload_raw.encode())

    # Advisory lock to serialize appends (lock id = fixed int for audit chain)
    await session.execute(text("SELECT pg_advisory_xact_lock(8675309)"))

    # Get the last entry
    result = await session.execute(
        select(AuditLogEntry).order_by(AuditLogEntry.sequence.desc()).limit(1)
    )
    last = result.scalar_one_or_none()

    seq = (last.sequence + 1) if last else 0
    prev = last.entry_hash if last else GENESIS_HASH
    now = datetime.utcnow()

    e_hash = chain_hash(
        sequence=seq,
        timestamp=now.isoformat(),
        actor=actor,
        action_type=action_type.value,
        payload_hash=p_hash,
        previous_hash=prev,
    )

    entry = AuditLogEntry(
        sequence=seq,
        timestamp=now,
        actor=actor,
        action_type=action_type,
        payload=payload,
        payload_hash=p_hash,
        previous_hash=prev,
        entry_hash=e_hash,
    )
    session.add(entry)
    await session.flush()
    return entry


async def verify_chain(session: AsyncSession) -> tuple[bool, int | None]:
    """Verify the entire audit chain. Returns (valid, first_broken_sequence)."""
    result = await session.execute(
        select(AuditLogEntry).order_by(AuditLogEntry.sequence.asc())
    )
    entries = result.scalars().all()

    if not entries:
        return True, None

    prev_hash = GENESIS_HASH
    for entry in entries:
        expected = chain_hash(
            sequence=entry.sequence,
            timestamp=entry.timestamp.isoformat(),
            actor=entry.actor,
            action_type=entry.action_type.value,
            payload_hash=entry.payload_hash,
            previous_hash=prev_hash,
        )
        if entry.entry_hash != expected:
            return False, entry.sequence
        if entry.previous_hash != prev_hash:
            return False, entry.sequence
        prev_hash = entry.entry_hash

    return True, None


async def get_entries_for_bidder(session: AsyncSession, bidder_id: str) -> list[AuditLogEntry]:
    """Get all audit entries that reference a specific bidder."""
    result = await session.execute(
        select(AuditLogEntry).order_by(AuditLogEntry.sequence.asc())
    )
    entries = result.scalars().all()
    return [e for e in entries if str(bidder_id) in json.dumps(e.payload, default=str)]


async def get_entries_for_criterion(
    session: AsyncSession, bidder_id: str, criterion_id: str
) -> list[AuditLogEntry]:
    """Get audit entries for a specific bidder+criterion pair."""
    result = await session.execute(
        select(AuditLogEntry).order_by(AuditLogEntry.sequence.asc())
    )
    entries = result.scalars().all()
    return [
        e for e in entries
        if str(bidder_id) in json.dumps(e.payload, default=str)
        and criterion_id in json.dumps(e.payload, default=str)
    ]
