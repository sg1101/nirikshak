"""Bidder Queue — Upload bidder submissions and view evaluation status."""

import streamlit as st

st.set_page_config(page_title="Nirikshak — Bidder Queue", page_icon="⚖️", layout="wide")
from sqlmodel import select

from nirikshak.console.helpers import (
    api_post, get_sync_session, render_sidebar, verdict_emoji, verdict_label,
)
from nirikshak.console.theme import (
    inject_global_css, verdict_pill, status_card, info_banner, section_header,
    NAVY, DARK, SUCCESS, DANGER, WARNING, MUTED, VERDICT_COLORS,
)
from nirikshak.core.schemas import Bidder, BidderVerdict, Document, Tender, VerdictState

inject_global_css()
render_sidebar()

st.markdown(f"""
<div style="display:flex; align-items:center; gap:12px; margin-bottom:20px;">
    <span style="font-size:2rem;">📦</span>
    <div>
        <h1 style="margin:0; color:{DARK};">Bidder Queue</h1>
        <span style="color:{MUTED};">Upload and evaluate bidder submissions</span>
    </div>
</div>
""", unsafe_allow_html=True)

tender_id = st.session_state.get("selected_tender_id")
if not tender_id:
    st.markdown(info_banner("No tender selected. Go to <b>Tender Library</b> and select a tender first.", WARNING), unsafe_allow_html=True)
    st.stop()

try:
    with get_sync_session() as session:
        tender = session.get(Tender, tender_id)
        if not tender:
            st.error("Tender not found.")
            st.stop()

    st.markdown(f"""
    <div style="background:{NAVY}10; border:1px solid {NAVY}20; border-radius:8px; padding:12px 16px; margin-bottom:16px;">
        <strong style="color:{NAVY};">Tender:</strong> {tender.title}
        <span style="color:{MUTED}; margin-left:16px;">Est. Value: ₹{float(tender.estimated_value)/1e7:.2f} Cr</span>
    </div>
    """, unsafe_allow_html=True)

    # Upload section
    with st.expander("➕ Upload New Bidder", expanded=True):
        bidder_name = st.text_input("Bidder Name", placeholder="e.g., ABC Constructions Pvt Ltd")
        uploaded_files = st.file_uploader(
            "Upload Bidder Documents",
            type=["pdf", "jpg", "jpeg", "png", "docx"],
            accept_multiple_files=True,
        )

        if uploaded_files:
            st.caption(f"{len(uploaded_files)} file(s): {', '.join(f.name for f in uploaded_files)}")

        if st.button("Upload & Evaluate", type="primary", disabled=not (bidder_name and uploaded_files)):
            with st.spinner(f"Processing {bidder_name} — this takes 5-8 minutes (extracting evidence from {len(uploaded_files)} documents, running verdict rules)..."):
                try:
                    files = [("files", (f.name, f.getvalue(), "application/octet-stream")) for f in uploaded_files]
                    import httpx
                    r = httpx.post(
                        f"http://localhost:8000/api/tenders/{tender_id}/bidders/upload",
                        data={"bidder_name": bidder_name},
                        files=files,
                        timeout=900,
                    )
                    r.raise_for_status()
                    result = r.json()
                    v = result["aggregate_verdict"]
                    st.success(f"**{bidder_name}**: {verdict_emoji(v)} {verdict_label(v)}")
                    for pc in result["per_criterion"]:
                        e = verdict_emoji(pc["state"])
                        st.markdown(f"  - {pc['criterion_id']}: {e} {verdict_label(pc['state'])} — {pc['reason'][:80]}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Evaluation failed: {e}")

    st.markdown("---")

    # Load bidder data
    with get_sync_session() as session:
        bidders = session.exec(
            select(Bidder).where(Bidder.tender_id == tender_id).order_by(Bidder.submission_date.desc())
        ).all()

        if not bidders:
            st.markdown(info_banner("No bidders uploaded yet. Use the form above.", "#2980B9"), unsafe_allow_html=True)
            st.stop()

        bidder_verdicts = {}
        bidder_doc_counts = {}
        for b in bidders:
            bv = session.exec(select(BidderVerdict).where(BidderVerdict.bidder_id == b.id)).first()
            bidder_verdicts[b.id] = bv
            doc_count = len(session.exec(select(Document).where(Document.bidder_id == b.id)).all())
            bidder_doc_counts[b.id] = doc_count

    # Summary metrics
    total = len(bidders)
    eligible = sum(1 for v in bidder_verdicts.values() if v and v.aggregate_state == VerdictState.eligible)
    not_eligible = sum(1 for v in bidder_verdicts.values() if v and v.aggregate_state == VerdictState.not_eligible)
    needs_review = sum(1 for v in bidder_verdicts.values() if v and v.aggregate_state == VerdictState.needs_review)

    st.markdown(section_header("Summary", f"{total} bidders evaluated"), unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(status_card("Total", str(total), DARK, "📦"), unsafe_allow_html=True)
    with col2:
        st.markdown(status_card("Eligible", str(eligible), SUCCESS, "✓"), unsafe_allow_html=True)
    with col3:
        st.markdown(status_card("Not Eligible", str(not_eligible), DANGER, "✗"), unsafe_allow_html=True)
    with col4:
        st.markdown(status_card("Needs Review", str(needs_review), WARNING, "⚠"), unsafe_allow_html=True)

    # Verdict distribution bar
    if total > 0:
        e_pct = eligible / total * 100
        n_pct = not_eligible / total * 100
        r_pct = needs_review / total * 100
        st.markdown(f"""
        <div style="display:flex; height:12px; border-radius:6px; overflow:hidden; margin:12px 0 24px 0;">
            <div style="background:{SUCCESS}; width:{e_pct}%;" title="{eligible} Eligible"></div>
            <div style="background:{DANGER}; width:{n_pct}%;" title="{not_eligible} Not Eligible"></div>
            <div style="background:{WARNING}; width:{r_pct}%;" title="{needs_review} Needs Review"></div>
        </div>
        """, unsafe_allow_html=True)

    # Bidder cards
    st.markdown(section_header("Bidders"), unsafe_allow_html=True)

    sort_order = {"needs_review": 0, "not_eligible": 1, "eligible": 2}
    sorted_bidders = sorted(
        bidders,
        key=lambda b: sort_order.get(
            bidder_verdicts[b.id].aggregate_state.value if bidder_verdicts.get(b.id) else "eligible", 3
        ),
    )

    for bidder in sorted_bidders:
        bv = bidder_verdicts.get(bidder.id)
        state = bv.aggregate_state.value if bv else "unknown"
        color = VERDICT_COLORS.get(state, MUTED)
        doc_count = bidder_doc_counts.get(bidder.id, 0)

        st.markdown(f"""
        <div style="background:white; border-left:4px solid {color}; border-radius:0 12px 12px 0;
                    padding:16px 20px; margin:8px 0; box-shadow:0 1px 3px rgba(0,0,0,0.06);
                    display:flex; justify-content:space-between; align-items:center;">
            <div>
                <strong style="color:{DARK}; font-size:1.05rem;">{bidder.name}</strong>
                <br><span style="color:{MUTED}; font-size:0.8rem;">{doc_count} documents | {bidder.submission_date.strftime('%Y-%m-%d %H:%M')}</span>
            </div>
            <div>{verdict_pill(state)}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Review Verdicts →", key=f"review_{bidder.id}", type="secondary"):
            st.session_state["selected_bidder_id"] = str(bidder.id)
            st.switch_page("pages/4_Verdict_Review.py")

except Exception as e:
    st.error(f"Error: {e}")
