"""Verdict Review — Gate 2: per-bidder verdicts with evidence detail."""

import json
import streamlit as st

st.set_page_config(page_title="Nirikshak — Verdict Review", page_icon="⚖️", layout="wide")
from sqlmodel import select

from nirikshak.console.helpers import (
    criterion_type_label, format_inr, get_sync_session, render_sidebar,
    verdict_emoji, verdict_label, verdict_color,
)
from nirikshak.console.theme import (
    inject_global_css, verdict_pill, criterion_badge, confidence_bar,
    info_banner, section_header, NAVY, DARK, SUCCESS, DANGER, WARNING, MUTED, VERDICT_COLORS,
)
from nirikshak.core.schemas import (
    Bidder, BidderVerdict, Criterion, CriteriaSpec,
    EvidenceClaim, Tender, Verdict, VerdictState,
)

inject_global_css()
render_sidebar()

st.markdown(f"""
<div style="display:flex; align-items:center; gap:12px; margin-bottom:20px;">
    <span style="font-size:2rem;">⚖️</span>
    <div>
        <h1 style="margin:0; color:{DARK};">Verdict Review</h1>
        <span style="color:{MUTED};">Gate 2 — Officer reviews and approves bidder evaluations</span>
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

        bidders = session.exec(select(Bidder).where(Bidder.tender_id == tender_id)).all()

        if not bidders:
            st.markdown(info_banner("No bidders uploaded yet. Go to <b>Bidder Queue</b> to upload submissions.", "#2980B9"), unsafe_allow_html=True)
            st.stop()

        bidder_verdicts = {}
        for b in bidders:
            bv = session.exec(select(BidderVerdict).where(BidderVerdict.bidder_id == b.id)).first()
            bidder_verdicts[b.id] = bv

        spec = session.exec(
            select(CriteriaSpec).where(CriteriaSpec.tender_id == tender_id).order_by(CriteriaSpec.version.desc())
        ).first()
        criteria = []
        if spec:
            criteria = session.exec(select(Criterion).where(Criterion.criteria_spec_id == spec.id)).all()
        criteria_by_id = {c.id: c for c in criteria}

    # ── Two-column layout ─────────────────────────────────────────────

    left_col, right_col = st.columns([1, 3])

    # Left: bidder selector
    with left_col:
        st.markdown(section_header("Bidders"), unsafe_allow_html=True)

        sort_order = {"needs_review": 0, "not_eligible": 1, "eligible": 2}
        sorted_bidders = sorted(
            bidders,
            key=lambda b: sort_order.get(
                bidder_verdicts[b.id].aggregate_state.value if bidder_verdicts.get(b.id) else "eligible", 3
            ),
        )

        pre_selected = st.session_state.get("selected_bidder_id")
        if not pre_selected and sorted_bidders:
            st.session_state["selected_bidder_id"] = str(sorted_bidders[0].id)
            pre_selected = str(sorted_bidders[0].id)

        for bidder in sorted_bidders:
            bv = bidder_verdicts.get(bidder.id)
            state = bv.aggregate_state.value if bv else "unknown"
            is_selected = str(bidder.id) == pre_selected
            color = VERDICT_COLORS.get(state, MUTED)
            border = f"3px solid {color}" if is_selected else f"1px solid #ecf0f1"

            if st.button(
                f"{verdict_emoji(state)} {bidder.name}",
                key=f"bid_{bidder.id}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state["selected_bidder_id"] = str(bidder.id)
                st.rerun()

    # Right: selected bidder evaluation
    with right_col:
        selected_bidder_id = st.session_state.get("selected_bidder_id")
        if not selected_bidder_id:
            st.info("Select a bidder from the left panel.")
            st.stop()

        with get_sync_session() as session:
            bidder = session.get(Bidder, selected_bidder_id)
            if not bidder:
                st.error("Bidder not found.")
                st.stop()

            bv = session.exec(select(BidderVerdict).where(BidderVerdict.bidder_id == bidder.id)).first()
            verdicts = session.exec(select(Verdict).where(Verdict.bidder_id == bidder.id)).all()
            all_evidence = session.exec(select(EvidenceClaim).where(EvidenceClaim.bidder_id == bidder.id)).all()
            evidence_by_criterion = {}
            for e in all_evidence:
                evidence_by_criterion.setdefault(e.criterion_id, []).append(e)

        # Bidder header with verdict banner
        agg_state = bv.aggregate_state.value if bv else "unknown"
        color = VERDICT_COLORS.get(agg_state, MUTED)

        st.markdown(f"""
        <div style="background:linear-gradient(135deg, {color}15 0%, {color}05 100%);
                    border:1px solid {color}30; border-radius:12px; padding:20px; margin-bottom:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <h2 style="margin:0; color:{DARK};">{bidder.name}</h2>
                    <span style="color:{MUTED}; font-size:0.85rem;">
                        Submitted: {bidder.submission_date.strftime('%Y-%m-%d %H:%M')}
                    </span>
                </div>
                <div>{verdict_pill(agg_state, "large")}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Per-criterion verdict cards
        for verdict in verdicts:
            criterion = criteria_by_id.get(verdict.criterion_id)
            if not criterion:
                continue

            state = verdict.state.value
            v_color = VERDICT_COLORS.get(state, MUTED)
            mandatory_text = "Mandatory" if criterion.mandatory else "Optional"
            evidence_list = evidence_by_criterion.get(verdict.criterion_id, [])

            st.markdown(f"""
            <div style="background:white; border-left:4px solid {v_color}; border-radius:0 12px 12px 0;
                        padding:16px 20px; margin:12px 0; box-shadow:0 1px 3px rgba(0,0,0,0.06);">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <strong style="color:{DARK}; font-size:1.1rem;">{criterion.id}</strong>
                        {criterion_badge(criterion.type.value)}
                    </div>
                    <div style="display:flex; align-items:center; gap:12px;">
                        {verdict_pill(state)}
                        <span style="color:{MUTED}; font-size:0.75rem;">{mandatory_text}</span>
                    </div>
                </div>
                <div style="color:{MUTED}; font-size:0.8rem; margin-bottom:6px;">
                    Rule: <code style="background:#ecf0f1; padding:2px 6px; border-radius:4px; font-size:0.75rem;">{verdict.rule_fired}</code>
                </div>
                <div style="color:{DARK}; font-size:0.9rem; line-height:1.5;">{verdict.reason_template}</div>
            </div>
            """, unsafe_allow_html=True)

            # Evidence expander
            if evidence_list:
                with st.expander(f"Evidence ({len(evidence_list)} claim{'s' if len(evidence_list) != 1 else ''})"):
                    for ei, ev in enumerate(evidence_list):
                        st.markdown(f"**Claim {ei + 1}** — Page {ev.source_page}")

                        if isinstance(ev.extracted_value, dict):
                            display_vals = {
                                k: v for k, v in ev.extracted_value.items()
                                if v is not None and k not in ("source_doc_id", "source_bbox")
                            }
                            st.json(display_vals)

                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown(f"**Confidence:** {confidence_bar(ev.confidence)}", unsafe_allow_html=True)
                        with c2:
                            if ev.verifier_passed:
                                st.markdown(f'<span style="color:{SUCCESS}; font-weight:600;">&#10003; Verified</span>', unsafe_allow_html=True)
                            else:
                                st.markdown(f'<span style="color:{WARNING}; font-weight:600;">&#9888; Unverified</span>', unsafe_allow_html=True)

                        if ei < len(evidence_list) - 1:
                            st.markdown("---")

            # Branch evaluations for disjunctive
            if verdict.officer_action and isinstance(verdict.officer_action, dict):
                branches = verdict.officer_action.get("branch_evaluations")
                if branches:
                    with st.expander("Branch Evaluations (Disjunctive Rule)"):
                        for bi, branch in enumerate(branches):
                            passed = branch["passed"]
                            icon = f'<span style="color:{SUCCESS};">&#10003; PASS</span>' if passed else f'<span style="color:{DANGER};">&#10007; FAIL</span>'
                            st.markdown(
                                f"**Branch {chr(65 + bi)}:** "
                                f">={branch['count_required']} works at >={branch['percentage']:.0f}% "
                                f"(threshold {format_inr(branch['threshold'])}) — "
                                f"{branch['qualifying_count']} qualifying — {icon}",
                                unsafe_allow_html=True,
                            )

            # Gate 2 actions
            if state == "needs_review":
                st.markdown(f"""
                <div style="background:{WARNING}10; border:1px solid {WARNING}30; border-radius:8px;
                            padding:12px; margin:8px 0;">
                    <strong style="color:{WARNING};">Gate 2 — Officer Action Required</strong>
                </div>
                """, unsafe_allow_html=True)
                c1, c2, c3 = st.columns(3)
                if c1.button("✅ Accept As-Is", key=f"accept_{verdict.criterion_id}"):
                    st.success(f"Accepted {verdict.criterion_id} as-is.")
                override_reason = c2.text_input("Reason", key=f"or_{verdict.criterion_id}", placeholder="Override reason")
                if c2.button("✏️ Override", key=f"override_{verdict.criterion_id}"):
                    if override_reason:
                        st.success(f"Overridden: {override_reason}")
                    else:
                        st.warning("Provide a reason.")
                if c3.button("⬆️ Escalate", key=f"esc_{verdict.criterion_id}"):
                    st.info(f"Escalated {verdict.criterion_id}.")

except Exception as e:
    st.error(f"Error: {e}")
    import traceback
    st.code(traceback.format_exc())
