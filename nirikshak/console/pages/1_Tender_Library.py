"""Tender Library — Upload and manage tenders."""

import streamlit as st
from sqlmodel import select

from nirikshak.console.helpers import (
    api_post, format_inr, get_sync_session, render_sidebar,
)
from nirikshak.console.theme import (
    inject_global_css, info_banner, section_header,
    NAVY, DARK, SUCCESS, WARNING, MUTED,
)
from nirikshak.core.schemas import Tender, CriteriaSpec, Criterion

inject_global_css()
render_sidebar()

st.markdown(f"""
<div style="display:flex; align-items:center; gap:12px; margin-bottom:20px;">
    <span style="font-size:2rem;">📚</span>
    <div>
        <h1 style="margin:0; color:{DARK};">Tender Library</h1>
        <span style="color:{MUTED};">Upload and manage government tender documents</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Upload section
with st.expander("➕ Upload New Tender", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("Tender Title", placeholder="e.g., Construction of Vehicle Parking")
        procuring_authority = st.text_input("Procuring Authority", placeholder="e.g., CRPF Zone Bangalore")
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
                    count = len(result["criteria_spec"]["criteria"])
                    st.success(f"Tender uploaded! **{count} eligibility criteria** extracted.")
                    st.session_state["selected_tender_id"] = result["tender_id"]
                else:
                    st.warning("Uploaded but no criteria found.")
                st.rerun()
            except Exception as e:
                st.error(f"Upload failed: {e}")

st.markdown("---")

# Tender list
st.markdown(section_header("All Tenders"), unsafe_allow_html=True)

try:
    with get_sync_session() as session:
        tenders = session.exec(select(Tender).order_by(Tender.created_at.desc())).all()

        if not tenders:
            st.markdown(info_banner("No tenders uploaded yet. Use the form above to upload your first tender.", "#2980B9"), unsafe_allow_html=True)
        else:
            for tender in tenders:
                spec = session.exec(
                    select(CriteriaSpec).where(CriteriaSpec.tender_id == tender.id).order_by(CriteriaSpec.version.desc())
                ).first()

                criteria_count = 0
                locked = False
                if spec:
                    criteria_count = len(session.exec(select(Criterion).where(Criterion.criteria_spec_id == spec.id)).all())
                    locked = spec.locked_at is not None

                color = SUCCESS if locked else WARNING
                status_text = "🔒 Locked" if locked else "📝 Draft"

                is_selected = st.session_state.get("selected_tender_id") == str(tender.id)
                border = f"2px solid {NAVY}" if is_selected else f"1px solid #ecf0f1"

                st.markdown(f"""
                <div style="background:white; border-left:4px solid {color}; border-radius:0 12px 12px 0;
                            padding:16px 20px; margin:8px 0; box-shadow:0 1px 3px rgba(0,0,0,0.06);
                            {'outline:2px solid ' + NAVY + '; outline-offset:2px;' if is_selected else ''}">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <strong style="color:{DARK}; font-size:1.05rem;">{tender.title}</strong>
                            <br><span style="color:{MUTED}; font-size:0.8rem;">{tender.procuring_authority} | Bid date: {tender.bid_submission_date}</span>
                        </div>
                        <div style="text-align:right;">
                            <div style="color:{DARK}; font-weight:700; font-size:1.1rem;">{format_inr(tender.estimated_value)}</div>
                            <span style="color:{MUTED}; font-size:0.8rem;">{criteria_count} criteria | {status_text}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("Select →" if not is_selected else "✓ Selected", key=f"sel_{tender.id}",
                             type="primary" if not is_selected else "secondary"):
                    st.session_state["selected_tender_id"] = str(tender.id)
                    st.rerun()

except Exception as e:
    st.error(f"Could not load tenders: {e}")
