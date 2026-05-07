"""Shared helpers for Streamlit console pages."""

from decimal import Decimal
from functools import lru_cache

import httpx
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session, select

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


def render_sidebar():
    """Render the shared sidebar on every page. Call this at the top of each page."""
    from nirikshak.core.schemas import Tender

    # ── Branding at the very top ──
    st.sidebar.markdown("""
    <div style="padding:8px 0 4px 0;">
        <span style="font-size:1.5rem; font-weight:700; color:white;">⚖️ Nirikshak</span>
    </div>
    <div style="margin-bottom:12px;">
        <span style="font-size:0.75rem; color:rgba(255,255,255,0.6); letter-spacing:0.5px;">
            AI-Based Tender Evaluation
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ── Custom page navigation ──
    st.sidebar.markdown("""
    <div style="margin-bottom:4px;">
        <span style="font-size:0.65rem; text-transform:uppercase; letter-spacing:1px;
                   color:rgba(255,255,255,0.4); font-weight:600;">Navigation</span>
    </div>
    """, unsafe_allow_html=True)

    pages = [
        ("🏠", "Dashboard", "streamlit_app.py"),
        ("📚", "Tender Library", "pages/1_Tender_Library.py"),
        ("🔍", "Criteria Review", "pages/2_Criteria_Review.py"),
        ("📦", "Bidder Queue", "pages/3_Bidder_Queue.py"),
        ("⚖️", "Verdict Review", "pages/4_Verdict_Review.py"),
        ("📊", "Report Export", "pages/5_Report_Export.py"),
        ("🔗", "Audit Log", "pages/6_Audit_Log.py"),
        ("📈", "Eval Dashboard", "pages/7_Eval_Dashboard.py"),
    ]

    for icon, label, page_path in pages:
        st.sidebar.page_link(page_path, label=f"{icon}  {label}", use_container_width=True)

    st.sidebar.markdown("---")

    # ── Officer context ──
    st.sidebar.markdown("""
    <div style="margin-bottom:2px;">
        <span style="font-size:0.65rem; text-transform:uppercase; letter-spacing:1px;
                   color:rgba(255,255,255,0.4); font-weight:600;">Session</span>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.text_input("Officer Email", value="officer1@crpf.gov.in", key="officer_email_input")

    # ── Active Tender selector ──
    st.sidebar.markdown("""
    <div style="margin-top:12px; margin-bottom:2px;">
        <span style="font-size:0.65rem; text-transform:uppercase; letter-spacing:1px;
                   color:rgba(255,255,255,0.4); font-weight:600;">Active Tender</span>
    </div>
    """, unsafe_allow_html=True)

    try:
        with get_sync_session() as session:
            tenders = session.exec(select(Tender).order_by(Tender.created_at.desc())).all()

        if tenders:
            tender_options = {str(t.id): t.title for t in tenders}
            option_keys = list(tender_options.keys())

            current = st.session_state.get("selected_tender_id")
            default_idx = 0
            if current and current in option_keys:
                default_idx = option_keys.index(current)

            selected = st.sidebar.selectbox(
                "Active Tender",
                options=option_keys,
                index=default_idx,
                format_func=lambda x: tender_options[x],
                key="_sidebar_tender_select",
                label_visibility="collapsed",
            )
            st.session_state["selected_tender_id"] = selected
        else:
            st.sidebar.info("No tenders yet.")
    except Exception:
        st.sidebar.warning("Database not available.")


def api_post(path: str, timeout: int = 600, **kwargs) -> dict:
    r = httpx.post(f"{API_BASE}{path}", timeout=timeout, **kwargs)
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
