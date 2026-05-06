"""Nirikshak Console — Streamlit multipage app shell."""

import streamlit as st
from sqlmodel import select

st.set_page_config(
    page_title="Nirikshak",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────

st.sidebar.title("⚖️ Nirikshak")
st.sidebar.caption("AI-Based Tender Evaluation")
st.sidebar.markdown("---")

# Officer identity
officer = st.sidebar.text_input("Officer Email", value="officer1@crpf.gov.in", key="officer_email")
st.sidebar.markdown("---")

# Tender selector
try:
    from nirikshak.console.helpers import get_sync_session
    from nirikshak.core.schemas import Tender

    with get_sync_session() as session:
        tenders = session.exec(select(Tender).order_by(Tender.created_at.desc())).all()

    if tenders:
        tender_options = {str(t.id): f"{t.title}" for t in tenders}
        selected = st.sidebar.selectbox(
            "Active Tender",
            options=list(tender_options.keys()),
            format_func=lambda x: tender_options[x],
            key="selected_tender_id",
        )
    else:
        st.sidebar.info("No tenders yet. Upload one from the Tender Library.")
except Exception:
    st.sidebar.warning("Database not available. Start the API first.")

# ── Main page ─────────────────────────────────────────────────────────

st.title("Nirikshak")
st.markdown("**AI extracts evidence. Rules decide verdicts. Officers approve.**")

st.markdown("---")

col1, col2, col3 = st.columns(3)

try:
    from nirikshak.console.helpers import get_sync_session
    from nirikshak.core.schemas import Tender, Bidder, BidderVerdict

    with get_sync_session() as session:
        tender_count = len(session.exec(select(Tender)).all())
        bidder_count = len(session.exec(select(Bidder)).all())
        verdicts = session.exec(select(BidderVerdict)).all()

    col1.metric("Tenders", tender_count)
    col2.metric("Bidders Evaluated", bidder_count)
    eligible_count = sum(1 for v in verdicts if v.aggregate_state.value == "eligible")
    col3.metric("Eligible Bidders", f"{eligible_count}/{len(verdicts)}")
except Exception:
    col1.metric("Tenders", "—")
    col2.metric("Bidders Evaluated", "—")
    col3.metric("Eligible Bidders", "—")

st.markdown("---")
st.markdown(
    "**Navigate using the sidebar pages:**\n\n"
    "1. **Tender Library** — Upload and manage tenders\n"
    "2. **Criteria Review** — Review and lock eligibility criteria (Gate 1)\n"
    "3. **Bidder Queue** — Ingest bidder submissions\n"
    "4. **Verdict Review** — Review per-bidder verdicts (Gate 2)\n"
    "5. **Report Export** — Consolidated evaluation report\n"
    "6. **Audit Log** — View and verify the audit trail\n"
    "7. **Eval Dashboard** — Accuracy metrics\n"
)
