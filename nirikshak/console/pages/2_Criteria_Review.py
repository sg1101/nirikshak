"""Criteria Review — Gate 1: review and lock eligibility criteria."""

import streamlit as st

st.set_page_config(page_title="Nirikshak — Criteria Review", page_icon="⚖️", layout="wide")
from sqlmodel import select

from nirikshak.console.helpers import (
    api_post, criterion_type_label, get_sync_session, render_sidebar,
)
from nirikshak.console.theme import (
    inject_global_css, criterion_badge, info_banner, section_header,
    NAVY, DARK, SUCCESS, WARNING, MUTED, CRITERION_COLORS,
)
from nirikshak.core.schemas import CriteriaSpec, Criterion, Tender

inject_global_css()
render_sidebar()

st.markdown(f"""
<div style="display:flex; align-items:center; gap:12px; margin-bottom:20px;">
    <span style="font-size:2rem;">🔍</span>
    <div>
        <h1 style="margin:0; color:{DARK};">Criteria Review</h1>
        <span style="color:{MUTED};">Gate 1 — Review, edit, and lock eligibility criteria</span>
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
            st.error("Selected tender not found.")
            st.stop()

        spec = session.exec(
            select(CriteriaSpec).where(CriteriaSpec.tender_id == tender.id).order_by(CriteriaSpec.version.desc())
        ).first()

        if not spec:
            st.markdown(info_banner("No criteria extracted yet. Upload and process a tender first.", "#2980B9"), unsafe_allow_html=True)
            st.stop()

        criteria = session.exec(select(Criterion).where(Criterion.criteria_spec_id == spec.id)).all()
        locked = spec.locked_at is not None

    # Header
    lock_html = (
        f'<span style="background:{SUCCESS}15; color:{SUCCESS}; padding:6px 14px; border-radius:8px; font-weight:600;">🔒 Locked by {spec.locked_by}</span>'
        if locked else
        f'<span style="background:{WARNING}15; color:{WARNING}; padding:6px 14px; border-radius:8px; font-weight:600;">📝 Draft</span>'
    )

    st.markdown(f"""
    <div style="background:white; border-radius:12px; padding:20px; margin-bottom:20px; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <h2 style="margin:0; color:{DARK};">{tender.title}</h2>
                <span style="color:{MUTED}; font-size:0.85rem;">Spec v{spec.version} | Hash: <code>{spec.content_hash[:20]}...</code></span>
            </div>
            {lock_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Criteria cards
    st.markdown(section_header(f"Eligibility Criteria ({len(criteria)})", "AI-extracted from tender document"), unsafe_allow_html=True)

    for criterion in criteria:
        ctype = criterion.type.value
        color = CRITERION_COLORS.get(ctype, MUTED)
        mandatory_html = (
            f'<span style="background:{DARK}15; color:{DARK}; padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:600;">Mandatory</span>'
            if criterion.mandatory else
            f'<span style="background:{MUTED}20; color:{MUTED}; padding:2px 8px; border-radius:4px; font-size:0.75rem;">Optional</span>'
        )

        st.markdown(f"""
        <div style="background:white; border-left:4px solid {color}; border-radius:0 12px 12px 0;
                    padding:16px 20px; margin:10px 0; box-shadow:0 1px 3px rgba(0,0,0,0.06);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <strong style="color:{DARK}; font-size:1.1rem;">{criterion.id}</strong>
                    {criterion_badge(ctype)}
                </div>
                {mandatory_html}
            </div>
            <div style="color:{DARK}; font-size:0.95rem; line-height:1.5; margin-bottom:8px;">
                {criterion.description}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Parameters
        if criterion.parameters:
            with st.expander(f"Parameters — {criterion.id}"):
                if locked:
                    st.json(criterion.parameters)
                else:
                    st.json(criterion.parameters)

        # Source citation
        with st.expander(f"Source (Page {criterion.source_page}) — {criterion.id}"):
            st.markdown(f"""
            <div style="background:{NAVY}05; border-left:3px solid {NAVY}40; padding:12px 16px;
                        border-radius:0 6px 6px 0; font-style:italic; color:#555; line-height:1.6;">
                "{criterion.source_quote}"
                <br><span style="color:{MUTED}; font-style:normal; font-size:0.8rem;">— Page {criterion.source_page}</span>
            </div>
            """, unsafe_allow_html=True)

    # Lock controls
    if not locked:
        st.markdown("---")
        st.markdown(f"""
        <div style="background:{WARNING}08; border:1px solid {WARNING}30; border-radius:12px; padding:20px; margin:16px 0;">
            <h3 style="color:{WARNING}; margin-top:0;">⚠️ Lock Criteria Spec</h3>
            <p style="color:{DARK};">Locking makes the criteria spec <strong>immutable</strong>.
            All downstream evaluation will use this exact set. This action cannot be undone.</p>
        </div>
        """, unsafe_allow_html=True)

        officer_email = st.session_state.get("officer_email_input", "officer1@crpf.gov.in")
        if st.button("🔒 Lock Criteria Spec", type="primary"):
            with st.spinner("Locking..."):
                try:
                    result = api_post(f"/api/criteria-specs/{spec.id}/lock", data={"officer_email": officer_email})
                    st.success(f"Locked! Hash: `{result['content_hash'][:24]}...`")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")
    else:
        st.markdown(f"""
        <div style="background:{SUCCESS}08; border:1px solid {SUCCESS}30; border-radius:12px; padding:16px; margin:16px 0;">
            <p style="color:{SUCCESS}; margin:0;">
                ✅ Locked on <strong>{spec.locked_at}</strong> by <strong>{spec.locked_by}</strong>.
                Proceed to <strong>Bidder Queue</strong> to upload and evaluate bidders.
            </p>
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error: {e}")
