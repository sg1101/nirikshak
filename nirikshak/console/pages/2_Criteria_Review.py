"""Criteria Review — Gate 1: review and lock eligibility criteria."""

import streamlit as st
from sqlmodel import select

from nirikshak.console.helpers import (
    api_post, criterion_type_label, get_sync_session,
)
from nirikshak.core.schemas import CriteriaSpec, Criterion, Tender

st.header("🔍 Criteria Review (Gate 1)")

tender_id = st.session_state.get("selected_tender_id")
if not tender_id:
    st.warning("No tender selected. Go to **Tender Library** and select a tender first.")
    st.stop()

try:
    with get_sync_session() as session:
        tender = session.get(Tender, tender_id)
        if not tender:
            st.error("Selected tender not found.")
            st.stop()

        spec = session.exec(
            select(CriteriaSpec)
            .where(CriteriaSpec.tender_id == tender.id)
            .order_by(CriteriaSpec.version.desc())
        ).first()

        if not spec:
            st.info("No criteria extracted yet. Upload and process a tender first.")
            st.stop()

        criteria = session.exec(
            select(Criterion).where(Criterion.criteria_spec_id == spec.id)
        ).all()

        locked = spec.locked_at is not None

    # ── Header ────────────────────────────────────────────────────────

    col1, col2, col3 = st.columns([4, 2, 2])
    col1.subheader(tender.title)
    col2.markdown(f"**Spec Version:** {spec.version}")
    if locked:
        col3.success(f"🔒 Locked by {spec.locked_by}")
    else:
        col3.warning("📝 Draft — Review and lock below")

    st.caption(f"Content Hash: `{spec.content_hash[:24]}...`")
    st.markdown("---")

    # ── Criteria cards ────────────────────────────────────────────────

    st.subheader(f"Eligibility Criteria ({len(criteria)})")

    for i, criterion in enumerate(criteria):
        type_label = criterion_type_label(criterion.type.value)
        mandatory_badge = "🔴 Mandatory" if criterion.mandatory else "🔵 Optional"

        with st.container(border=True):
            header_col, badge_col = st.columns([5, 2])
            header_col.markdown(f"### {criterion.id} | {type_label}")
            badge_col.markdown(f"**{mandatory_badge}**")

            if locked:
                # Read-only view
                st.markdown(f"**Description:** {criterion.description}")
                if criterion.parameters:
                    st.json(criterion.parameters)
            else:
                # Editable view
                new_desc = st.text_area(
                    "Description",
                    value=criterion.description,
                    key=f"desc_{criterion.id}",
                    height=80,
                )
                new_mandatory = st.checkbox(
                    "Mandatory",
                    value=criterion.mandatory,
                    key=f"mand_{criterion.id}",
                )
                if criterion.parameters:
                    st.markdown("**Parameters:**")
                    st.json(criterion.parameters)

            # Source citation
            with st.expander(f"📖 Source (Page {criterion.source_page})"):
                st.markdown(f"> {criterion.source_quote}")

    # ── Lock controls ─────────────────────────────────────────────────

    if not locked:
        st.markdown("---")
        st.subheader("Lock Criteria Spec")
        st.warning(
            "⚠️ Locking the criteria spec makes it **immutable**. "
            "All downstream evaluation will use this exact set of criteria. "
            "This action cannot be undone."
        )

        officer_email = st.session_state.get("officer_email", "officer1@crpf.gov.in")
        st.markdown(f"**Officer:** {officer_email}")

        if st.button("🔒 Lock Criteria Spec", type="primary"):
            with st.spinner("Locking criteria spec..."):
                try:
                    result = api_post(
                        f"/api/criteria-specs/{spec.id}/lock",
                        data={"officer_email": officer_email},
                    )
                    st.success(
                        f"Criteria spec locked!\n\n"
                        f"- **Locked by:** {result['locked_by']}\n"
                        f"- **Content Hash:** `{result['content_hash'][:24]}...`\n"
                        f"- **Timestamp:** {result['locked_at']}"
                    )
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to lock: {e}")
    else:
        st.markdown("---")
        st.info(
            f"✅ This criteria spec was locked on **{spec.locked_at}** by **{spec.locked_by}**. "
            f"Proceed to **Bidder Queue** to upload and evaluate bidders."
        )

except Exception as e:
    st.error(f"Error loading criteria: {e}")
