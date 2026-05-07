"""Nirikshak Console — Streamlit multipage app shell."""

import streamlit as st
from sqlmodel import select

st.set_page_config(
    page_title="Nirikshak",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from nirikshak.console.helpers import render_sidebar, get_sync_session
from nirikshak.console.theme import (
    inject_global_css, status_card, pipeline_step, info_banner,
    NAVY, SUCCESS, DANGER, WARNING, DARK,
)

inject_global_css()
render_sidebar()

# ── Hero banner ───────────────────────────────────────────────────────

st.markdown(f"""
<div style="background:linear-gradient(135deg, {NAVY} 0%, #2980B9 100%);
            padding:40px; border-radius:16px; margin-bottom:24px;">
    <h1 style="color:white; margin:0; font-size:2.5rem;">Nirikshak</h1>
    <p style="color:rgba(255,255,255,0.85); font-size:1.1rem; margin:8px 0 0 0;">
        AI extracts evidence. Rules decide verdicts. Officers approve.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Metrics ───────────────────────────────────────────────────────────

try:
    from nirikshak.core.schemas import Tender, Bidder, BidderVerdict, VerdictState

    with get_sync_session() as session:
        tender_count = len(session.exec(select(Tender)).all())
        bidder_count = len(session.exec(select(Bidder)).all())
        verdicts = session.exec(select(BidderVerdict)).all()

    eligible = sum(1 for v in verdicts if v.aggregate_state == VerdictState.eligible)
    not_eligible = sum(1 for v in verdicts if v.aggregate_state == VerdictState.not_eligible)
    needs_review = sum(1 for v in verdicts if v.aggregate_state == VerdictState.needs_review)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(status_card("Tenders", str(tender_count), "#2980B9", "📋"), unsafe_allow_html=True)
    with col2:
        st.markdown(status_card("Bidders Evaluated", str(bidder_count), DARK, "📦"), unsafe_allow_html=True)
    with col3:
        st.markdown(status_card("Eligible", str(eligible), SUCCESS, "✓"), unsafe_allow_html=True)
    with col4:
        st.markdown(status_card("Needs Review", str(needs_review), WARNING, "⚠"), unsafe_allow_html=True)

    # Pipeline visualization
    has_tenders = tender_count > 0
    has_locked = False
    has_bidders = bidder_count > 0
    has_verdicts = len(verdicts) > 0

    if has_tenders:
        from nirikshak.core.schemas import CriteriaSpec
        with get_sync_session() as session:
            locked = session.exec(select(CriteriaSpec).where(CriteriaSpec.locked_at.isnot(None))).all()
            has_locked = len(locked) > 0

    # Pipeline visualization — native Streamlit columns (avoids HTML code block leak)
    steps = [
        ("1. Upload Tender", has_tenders, not has_tenders),
        ("2. Review Criteria", has_locked, has_tenders and not has_locked),
        ("3. Upload Bidders", has_bidders, has_locked and not has_bidders),
        ("4. Review Verdicts", has_verdicts, has_bidders and not has_verdicts),
        ("5. Export Report", False, has_verdicts),
    ]
    step_cols = st.columns(len(steps))
    for col, (name, done, active) in zip(step_cols, steps):
        if done:
            col.success(name)
        elif active:
            col.info(name)
        else:
            col.markdown(f"<div style='background:#ecf0f1; color:#95A5A6; padding:10px; border-radius:8px; text-align:center; font-weight:600; font-size:0.8rem;'>{name}</div>", unsafe_allow_html=True)

except Exception:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(status_card("Tenders", "—", "#2980B9"), unsafe_allow_html=True)
    with col2:
        st.markdown(status_card("Bidders", "—", DARK), unsafe_allow_html=True)
    with col3:
        st.markdown(status_card("Eligible", "—", SUCCESS), unsafe_allow_html=True)
    with col4:
        st.markdown(status_card("Needs Review", "—", WARNING), unsafe_allow_html=True)

# ── Quick actions ─────────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("📋 Upload Tender", use_container_width=True):
        st.switch_page("pages/1_Tender_Library.py")
with col2:
    if st.button("📦 Upload Bidders", use_container_width=True):
        st.switch_page("pages/3_Bidder_Queue.py")
with col3:
    if st.button("⚖️ Review Verdicts", use_container_width=True):
        st.switch_page("pages/4_Verdict_Review.py")

# ── How it works ──────────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="background:white; border-radius:12px; padding:24px; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    <h3 style="color:{DARK}; margin-top:0;">How Nirikshak Works</h3>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
        <div style="padding:12px;">
            <strong style="color:{NAVY};">1. Upload Tender</strong><br>
            <span style="color:#7f8c8d;">Upload a tender PDF. AI extracts eligibility criteria automatically.</span>
        </div>
        <div style="padding:12px;">
            <strong style="color:{NAVY};">2. Review & Lock (Gate 1)</strong><br>
            <span style="color:#7f8c8d;">Officer reviews extracted criteria, edits if needed, then locks.</span>
        </div>
        <div style="padding:12px;">
            <strong style="color:{NAVY};">3. Upload Bidders</strong><br>
            <span style="color:#7f8c8d;">Upload bidder documents. AI extracts evidence for each criterion.</span>
        </div>
        <div style="padding:12px;">
            <strong style="color:{NAVY};">4. Verdicts & Report</strong><br>
            <span style="color:#7f8c8d;">Deterministic rules decide. Officer approves. Audit trail preserved.</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
