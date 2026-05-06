"""Shared helpers for Streamlit console pages."""

from decimal import Decimal
from functools import lru_cache

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session

from nirikshak.core.config import get_settings
import nirikshak.core.schemas  # noqa: ensure models registered

_sync_engine = None
_sync_session_factory = None

API_BASE = "http://localhost:8000"


def get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        settings = get_settings()
        _sync_engine = create_engine(settings.database_url_sync, echo=False)
    return _sync_engine


def get_sync_session() -> Session:
    global _sync_session_factory
    if _sync_session_factory is None:
        _sync_session_factory = sessionmaker(get_sync_engine(), class_=Session)
    return _sync_session_factory()


def api_post(path: str, **kwargs) -> dict:
    r = httpx.post(f"{API_BASE}{path}", timeout=300, **kwargs)
    r.raise_for_status()
    return r.json()


def api_get(path: str) -> dict:
    r = httpx.get(f"{API_BASE}{path}", timeout=30)
    r.raise_for_status()
    return r.json()


def format_inr(amount) -> str:
    """Format a number as INR with crore/lakh suffix."""
    try:
        val = float(amount)
    except (TypeError, ValueError):
        return str(amount)
    if val >= 1e7:
        return f"₹{val / 1e7:.2f} Cr"
    elif val >= 1e5:
        return f"₹{val / 1e5:.2f} L"
    else:
        return f"₹{val:,.0f}"


def verdict_color(state: str) -> str:
    return {
        "eligible": "green",
        "not_eligible": "red",
        "needs_review": "orange",
    }.get(state, "gray")


def verdict_emoji(state: str) -> str:
    return {
        "eligible": "✅",
        "not_eligible": "❌",
        "needs_review": "⚠️",
    }.get(state, "❓")


def verdict_label(state: str) -> str:
    return {
        "eligible": "Eligible",
        "not_eligible": "Not Eligible",
        "needs_review": "Needs Review",
    }.get(state, state)


def criterion_type_label(ctype: str) -> str:
    return {
        "financial_threshold": "💰 Financial",
        "experience_count": "🏗️ Experience",
        "statutory_registration": "📋 Registration",
        "quality_certification": "🏆 Certification",
        "document_checklist": "📄 Document",
        "policy_compliance": "📜 Compliance",
    }.get(ctype, ctype)
