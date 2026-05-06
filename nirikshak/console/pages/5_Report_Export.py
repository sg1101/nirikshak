"""Report Export — Consolidated evaluation report preview."""

import streamlit as st
from sqlmodel import select

from nirikshak.console.helpers import (
    format_inr, get_sync_session, render_sidebar, verdict_emoji, verdict_label,
)
from nirikshak.core.schemas import (
    Bidder, BidderVerdict, CriteriaSpec, Criterion, Tender, Verdict,
)


render_sidebar()
st.header("📊 Report Export")

tender_id = st.session_state.get("selected_tender_id")
if not tender_id:
    st.warning("No tender selected. Go to **Tender Library** first.")
    st.stop()

try:
    with get_sync_session() as session:
        tender = session.get(Tender, tender_id)
        if not tender:
            st.error("Tender not found.")
            st.stop()

        spec = session.exec(
            select(CriteriaSpec)
            .where(CriteriaSpec.tender_id == tender_id)
            .order_by(CriteriaSpec.version.desc())
        ).first()

        bidders = session.exec(
            select(Bidder).where(Bidder.tender_id == tender_id)
        ).all()

        bidder_verdicts = {}
        bidder_criterion_verdicts = {}
        for b in bidders:
            bv = session.exec(select(BidderVerdict).where(BidderVerdict.bidder_id == b.id)).first()
            bidder_verdicts[b.id] = bv
            vs = session.exec(select(Verdict).where(Verdict.bidder_id == b.id)).all()
            bidder_criterion_verdicts[b.id] = vs

    # ── Report preview ────────────────────────────────────────────────

    st.subheader("Consolidated Evaluation Report")

    # Tender summary
    with st.container(border=True):
        st.markdown("### Tender Summary")
        col1, col2 = st.columns(2)
        col1.markdown(f"**Title:** {tender.title}")
        col1.markdown(f"**Authority:** {tender.procuring_authority}")
        col2.markdown(f"**Est. Value:** {format_inr(tender.estimated_value)}")
        col2.markdown(f"**Bid Date:** {tender.bid_submission_date}")
        if spec:
            st.caption(f"Criteria Spec Hash: `{spec.content_hash[:32]}...`")

    st.markdown("---")

    # Bidder verdicts table
    st.markdown("### Bidder Evaluation Results")

    if not bidders:
        st.info("No bidders evaluated yet.")
        st.stop()

    for bidder in bidders:
        bv = bidder_verdicts.get(bidder.id)
        state = bv.aggregate_state.value if bv else "unknown"
        emoji = verdict_emoji(state)
        label = verdict_label(state)

        with st.expander(f"{emoji} **{bidder.name}** — {label}"):
            for v in bidder_criterion_verdicts.get(bidder.id, []):
                v_emoji = verdict_emoji(v.state.value)
                st.markdown(f"- **{v.criterion_id}**: {v_emoji} {verdict_label(v.state.value)} — {v.reason_template[:100]}")

    st.markdown("---")

    # Download button
    import httpx
    try:
        if st.button("⬇️ Generate & Download Signed PDF Report", type="primary"):
            with st.spinner("Generating signed PDF report..."):
                r = httpx.get(f"http://localhost:8000/api/tenders/{tender_id}/report", timeout=60)
                r.raise_for_status()
                st.download_button(
                    label="📥 Click to Save PDF",
                    data=r.content,
                    file_name=f"nirikshak_report_{str(tender_id)[:8]}.pdf",
                    mime="application/pdf",
                )
                st.success("Report generated and digitally signed. Audit log updated.")
    except Exception as e:
        st.error(f"Report generation failed: {e}")

except Exception as e:
    st.error(f"Error: {e}")
