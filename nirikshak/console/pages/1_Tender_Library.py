"""Tender Library — Upload and manage tenders."""

import streamlit as st
from sqlmodel import select

from nirikshak.console.helpers import (
    api_post, format_inr, get_sync_session, render_sidebar,
)
from nirikshak.core.schemas import Tender, CriteriaSpec, Criterion


render_sidebar()
st.header("📚 Tender Library")

# ── Upload section ────────────────────────────────────────────────────

with st.expander("➕ Upload New Tender", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("Tender Title", value="", placeholder="e.g., Construction of Vehicle Parking")
        procuring_authority = st.text_input("Procuring Authority", value="", placeholder="e.g., CRPF Zone Bangalore")
    with col2:
        bid_date = st.date_input("Bid Submission Date")
        estimated_value = st.number_input("Estimated Value (INR)", min_value=0, value=0, step=1000000)

    uploaded_file = st.file_uploader("Upload Tender PDF", type=["pdf"])

    if st.button("Upload & Extract Criteria", type="primary", disabled=not uploaded_file):
        with st.spinner("Uploading tender and extracting eligibility criteria..."):
            try:
                result = api_post(
                    "/api/tenders/upload",
                    data={
                        "title": title or "Untitled Tender",
                        "procuring_authority": procuring_authority or "Unknown",
                        "bid_submission_date": str(bid_date),
                        "estimated_value": str(estimated_value),
                    },
                    files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")},
                )
                if result.get("criteria_spec"):
                    criteria_count = len(result["criteria_spec"]["criteria"])
                    st.success(f"Tender uploaded successfully! Extracted **{criteria_count} eligibility criteria**.")
                    st.session_state["selected_tender_id"] = result["tender_id"]
                else:
                    st.warning("Tender uploaded but no eligibility criteria were found.")
                st.rerun()
            except Exception as e:
                st.error(f"Upload failed: {e}")

st.markdown("---")

# ── Tender list ───────────────────────────────────────────────────────

st.subheader("All Tenders")

try:
    with get_sync_session() as session:
        tenders = session.exec(select(Tender).order_by(Tender.created_at.desc())).all()

        if not tenders:
            st.info("No tenders uploaded yet. Use the form above to upload your first tender.")
        else:
            for tender in tenders:
                # Get criteria count and lock status
                spec = session.exec(
                    select(CriteriaSpec)
                    .where(CriteriaSpec.tender_id == tender.id)
                    .order_by(CriteriaSpec.version.desc())
                ).first()

                criteria_count = 0
                locked = False
                if spec:
                    criteria_count = len(session.exec(
                        select(Criterion).where(Criterion.criteria_spec_id == spec.id)
                    ).all())
                    locked = spec.locked_at is not None

                status = "🔒 Locked" if locked else "📝 Draft"

                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                    col1.markdown(f"**{tender.title}**")
                    col1.caption(f"{tender.procuring_authority} | {tender.bid_submission_date}")
                    col2.markdown(f"Est. Value: **{format_inr(tender.estimated_value)}**")
                    col3.markdown(f"Criteria: **{criteria_count}**")
                    col4.markdown(f"Status: {status}")

                    if st.button("Select", key=f"select_{tender.id}"):
                        st.session_state["selected_tender_id"] = str(tender.id)
                        st.success(f"Selected: {tender.title}")
                        st.rerun()

except Exception as e:
    st.error(f"Could not load tenders: {e}")
