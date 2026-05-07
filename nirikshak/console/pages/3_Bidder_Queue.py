"""Bidder Queue — Upload bidder submissions and view evaluation status."""

import streamlit as st
from sqlmodel import select

from nirikshak.console.helpers import (
    api_post, get_sync_session, render_sidebar, verdict_emoji, verdict_label,
)
from nirikshak.core.schemas import Bidder, BidderVerdict, Document, Tender


render_sidebar()
st.header("📦 Bidder Queue")

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

    st.subheader(f"Tender: {tender.title}")

    # ── Upload section ────────────────────────────────────────────────

    with st.expander("➕ Upload New Bidder", expanded=True):
        bidder_name = st.text_input("Bidder Name", placeholder="e.g., Rajesh Construction Pvt Ltd")
        uploaded_files = st.file_uploader(
            "Upload Bidder Documents",
            type=["pdf", "jpg", "jpeg", "png", "docx"],
            accept_multiple_files=True,
        )

        if uploaded_files:
            st.caption(f"{len(uploaded_files)} file(s) selected: {', '.join(f.name for f in uploaded_files)}")

        if st.button("Upload & Evaluate", type="primary", disabled=not (bidder_name and uploaded_files)):
            with st.spinner(f"Processing {bidder_name}'s submission — this takes 5-8 minutes (extracting evidence from {len(uploaded_files)} documents, running verdict rules)..."):
                try:
                    files = [("files", (f.name, f.getvalue(), "application/octet-stream")) for f in uploaded_files]
                    import httpx
                    r = httpx.post(
                        f"http://localhost:8000/api/tenders/{tender_id}/bidders/upload",
                        data={"bidder_name": bidder_name},
                        files=files,
                        timeout=900,  # 15 minutes — bidder eval is slow due to sequential LLM calls
                    )
                    r.raise_for_status()
                    result = r.json()
                    verdict = result["aggregate_verdict"]
                    emoji = verdict_emoji(verdict)
                    label = verdict_label(verdict)
                    st.success(f"Evaluation complete! **{bidder_name}**: {emoji} {label}")

                    # Show per-criterion summary
                    for pc in result["per_criterion"]:
                        e = verdict_emoji(pc["state"])
                        st.markdown(f"  - {pc['criterion_id']}: {e} {verdict_label(pc['state'])} — {pc['reason'][:80]}")

                    st.rerun()
                except Exception as e:
                    st.error(f"Evaluation failed: {e}")

    st.markdown("---")

    # ── Bidder list ───────────────────────────────────────────────────

    with get_sync_session() as session:
        bidders = session.exec(
            select(Bidder).where(Bidder.tender_id == tender_id).order_by(Bidder.submission_date.desc())
        ).all()

        if not bidders:
            st.info("No bidders uploaded yet. Use the form above to upload a bidder's submission.")
            st.stop()

        # Get verdicts
        bidder_verdicts = {}
        bidder_doc_counts = {}
        for b in bidders:
            bv = session.exec(select(BidderVerdict).where(BidderVerdict.bidder_id == b.id)).first()
            bidder_verdicts[b.id] = bv
            doc_count = len(session.exec(select(Document).where(Document.bidder_id == b.id)).all())
            bidder_doc_counts[b.id] = doc_count

    # Summary stats
    st.subheader("Summary")
    total = len(bidders)
    eligible = sum(1 for v in bidder_verdicts.values() if v and v.aggregate_state.value == "eligible")
    not_eligible = sum(1 for v in bidder_verdicts.values() if v and v.aggregate_state.value == "not_eligible")
    needs_review = sum(1 for v in bidder_verdicts.values() if v and v.aggregate_state.value == "needs_review")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Bidders", total)
    col2.metric("✅ Eligible", eligible)
    col3.metric("❌ Not Eligible", not_eligible)
    col4.metric("⚠️ Needs Review", needs_review)

    # Progress bar
    if total > 0:
        st.progress(eligible / total, text=f"{eligible}/{total} eligible")

    st.markdown("---")

    # Bidder cards
    st.subheader("Bidders")

    # Sort: Needs Review first, then Not Eligible, then Eligible
    sort_order = {"needs_review": 0, "not_eligible": 1, "eligible": 2}
    sorted_bidders = sorted(
        bidders,
        key=lambda b: sort_order.get(
            bidder_verdicts[b.id].aggregate_state.value if bidder_verdicts.get(b.id) else "eligible", 3
        ),
    )

    for bidder in sorted_bidders:
        bv = bidder_verdicts.get(bidder.id)
        verdict_state = bv.aggregate_state.value if bv else "unknown"
        emoji = verdict_emoji(verdict_state)
        label = verdict_label(verdict_state)
        doc_count = bidder_doc_counts.get(bidder.id, 0)

        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            col1.markdown(f"**{bidder.name}**")
            col1.caption(f"Submitted: {bidder.submission_date.strftime('%Y-%m-%d %H:%M')}")
            col2.markdown(f"{emoji} **{label}**")
            col3.markdown(f"📄 {doc_count} docs")

            if col4.button("Review", key=f"review_{bidder.id}"):
                st.session_state["selected_bidder_id"] = str(bidder.id)
                st.switch_page("pages/4_Verdict_Review.py")

except Exception as e:
    st.error(f"Error: {e}")
