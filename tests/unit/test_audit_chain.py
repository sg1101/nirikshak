"""Unit tests for the audit hash chain.

These tests require a running Postgres instance. They are skipped if the DB is unavailable.
For CI, run with: docker compose up db -d && pytest tests/unit/test_audit_chain.py
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from nirikshak.audit.chain import append_entry, get_entries_for_bidder, verify_chain
from nirikshak.core.schemas import AuditActionType

TEST_DB_URL = "postgresql+asyncpg://nirikshak:nirikshak@localhost:5432/nirikshak"


@pytest.fixture
async def session():
    """Create a test session with clean audit table."""
    try:
        engine = create_async_engine(TEST_DB_URL)
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
            # TRUNCATE bypasses rules, DELETE does not (rules block it)
            await conn.execute(text("TRUNCATE auditlogentry"))
    except Exception:
        pytest.skip("Postgres not available")

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.mark.asyncio
async def test_append_and_verify(session):
    """Append entries and verify the chain is valid."""
    for i in range(5):
        await append_entry(
            session,
            actor="system",
            action_type=AuditActionType.tender_ingested,
            payload={"tender_id": f"tender-{i}", "index": i},
        )
    await session.commit()

    valid, broken = await verify_chain(session)
    assert valid is True
    assert broken is None


@pytest.mark.asyncio
async def test_empty_chain_is_valid(session):
    valid, broken = await verify_chain(session)
    assert valid is True


@pytest.mark.asyncio
async def test_chain_links(session):
    """Verify entries are properly linked."""
    e1 = await append_entry(session, "system", AuditActionType.tender_ingested, {"id": "1"})
    e2 = await append_entry(session, "system", AuditActionType.criteria_extracted, {"id": "2"})
    await session.commit()

    assert e1.sequence == 0
    assert e2.sequence == 1
    assert e2.previous_hash == e1.entry_hash


@pytest.mark.asyncio
async def test_entries_for_bidder(session):
    """Filter entries by bidder ID."""
    bidder_id = "bidder-abc-123"
    await append_entry(session, "system", AuditActionType.bidder_ingested, {"bidder_id": bidder_id})
    await append_entry(session, "system", AuditActionType.tender_ingested, {"tender_id": "other"})
    await append_entry(session, "system", AuditActionType.evidence_extracted, {"bidder_id": bidder_id, "criterion_id": "FIN-001"})
    await session.commit()

    entries = await get_entries_for_bidder(session, bidder_id)
    assert len(entries) == 2
    assert all(bidder_id in str(e.payload) for e in entries)
