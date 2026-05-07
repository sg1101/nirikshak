"""Report Export — Consolidated evaluation report preview."""

import streamlit as st
from sqlmodel import select

from nirikshak.console.helpers import (
    format_inr, get_sync_session, render_sidebar, verdict_emoji, verdict_label,
)
from nirikshak.console.theme import (
    inject_global_css, verdict_pill, info_banner, section_header,
    NAVY, DARK, SUCCESS, DANGER, WARNING, MUTED, VERDICT_COLORS,
)
from nirikshak.core.schemas import (
    Bidder, BidderVerdict, CriteriaSpec, Criterion, Tender, Verdict,
)

inject_global_css()
render_sidebar()

st.markdown(f"""
<div style="display:flex; align-items:center; gap:12px; margin-bottom:20px;">
    <span style="font-size:2rem;">📊</span>
    <div>
        <h1 style="margin:0; color:{DARK};">Report Export</h1>
        <span style="color:{MUTED};">Consolidated evaluation report with digital signature</span>
    </div>
</div>
""", unsafe_allow_html=True)

tender_id = st.session_state.get("selected_tender_id")
if not tender_id:
    st.markdown(info_banner("No tender selected. Go to <b>Tender Library</b> first.", WARNING), unsafe_allow_html=True)
    st.stop()

try:
    with get_sync_session() as session:
        tender = session.get(Tender, tender_id)
        if not tender:
            st.error("Tender not found.")
            st.stop()

        spec = session.exec(
            select(CriteriaSpec).where(CriteriaSpec.tender_id == tender_id).order_by(CriteriaSpec.version.desc())
        ).first()

        bidders = session.exec(select(Bidder).where(Bidder.tender_id == tender_id)).all()
        bidder_verdicts = {}
        bidder_criterion_verdicts = {}
        for b in bidders:
            bv = session.exec(select(BidderVerdict).where(BidderVerdict.bidder_id == b.id)).first()
            bidder_verdicts[b.id] = bv
            vs = session.exec(select(Verdict).where(Verdict.bidder_id == b.id)).all()
            bidder_criterion_verdicts[b.id] = vs

    # Tender summary card
    st.markdown(f"""
    <div style="background:white; border-radius:12px; padding:24px; box-shadow:0 1px 3px rgba(0,0,0,0.08); margin-bottom:20px;">
        <h3 style="color:{DARK}; margin-top:0;">Tender Summary</h3>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div><span style="color:{MUTED};">Title:</span> <strong>{tender.title}</strong></div>
            <div><span style="color:{MUTED};">Est. Value:</span> <strong>{format_inr(tender.estimated_value)}</strong></div>
            <div><span style="color:{MUTED};">Authority:</span> <strong>{tender.procuring_authority}</strong></div>
            <div><span style="color:{MUTED};">Bid Date:</span> <strong>{tender.bid_submission_date}</strong></div>
        </div>
        {"<div style='margin-top:8px;'><span style=&quot;color:" + MUTED + "; font-size:0.8rem;&quot;>Spec Hash: <code>" + spec.content_hash[:32] + "...</code></span></div>" if spec else ""}
    </div>
    """, unsafe_allow_html=True)

    # Bidder results
    st.markdown(section_header("Bidder Evaluation Results", f"{len(bidders)} bidders evaluated"), unsafe_allow_html=True)

    if not bidders:
        st.markdown(info_banner("No bidders evaluated yet.", "#2980B9"), unsafe_allow_html=True)
        st.stop()

    for bidder in bidders:
        bv = bidder_verdicts.get(bidder.id)
        state = bv.aggregate_state.value if bv else "unknown"
        color = VERDICT_COLORS.get(state, MUTED)

        with st.expander(f"{verdict_emoji(state)} **{bidder.name}** — {verdict_label(state)}"):
            for v in bidder_criterion_verdicts.get(bidder.id, []):
                v_color = VERDICT_COLORS.get(v.state.value, MUTED)
                st.markdown(
                    f'<div style="padding:6px 0; border-bottom:1px solid #f0f0f0;">'
                    f'<strong>{v.criterion_id}</strong> '
                    f'{verdict_pill(v.state.value)} '
                    f'<span style="color:{MUTED}; font-size:0.85rem;">— {v.reason_template[:100]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("---")

    # Download
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
                st.success("Report generated and digitally signed.")
    except Exception as e:
        st.error(f"Report generation failed: {e}")

except Exception as e:
    st.error(f"Error: {e}")
