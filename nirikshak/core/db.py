"""Database engine, session factory, and initialization."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from nirikshak.core.config import get_settings
import nirikshak.core.schemas  # noqa: F401 — ensure all table models are registered with SQLModel

_engine = None
_async_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=False)
    return _engine


def get_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _async_session_factory


async def get_session() -> AsyncSession:
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_db():
    """Create all tables and apply audit log protection rules."""
    engine = get_engine()
    # First: create all tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    # Second: apply audit log protection rules (needs tables to exist)
    async with engine.begin() as conn:
        for op in ("update", "delete"):
            rule_name = f"audit_no_{op}"
            await conn.execute(text(
                f"DO $$ BEGIN "
                f"  IF NOT EXISTS (SELECT 1 FROM pg_rules WHERE rulename = '{rule_name}') THEN "
                f"    CREATE RULE {rule_name} AS ON {op.upper()} TO auditlogentry DO INSTEAD NOTHING; "
                f"  END IF; "
                f"END $$;"
            ))
