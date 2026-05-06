"""Verdict Review — Gate 2: per-bidder verdicts with evidence detail."""

import json

import streamlit as st
from sqlmodel import select

from nirikshak.console.helpers import (
    criterion_type_label, format_inr, get_sync_session,
    verdict_emoji, verdict_label, verdict_color,
)
from nirikshak.core.schemas import (
    Bidder, BidderVerdict, Criterion, CriteriaSpec,
    EvidenceClaim, Tender, Verdict, VerdictState,
)

st.header("⚖️ Verdict Review (Gate 2)")

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

        bidders = session.exec(
            select(Bidder).where(Bidder.tender_id == tender_id)
        ).all()

        if not bidders:
            st.info("No bidders uploaded yet. Go to **Bidder Queue** to upload submissions.")
            st.stop()

        # Load verdicts for all bidders
        bidder_verdicts = {}
        for b in bidders:
            bv = session.exec(select(BidderVerdict).where(BidderVerdict.bidder_id == b.id)).first()
            bidder_verdicts[b.id] = bv

        # Get criteria
        spec = session.exec(
            select(CriteriaSpec)
            .where(CriteriaSpec.tender_id == tender_id)
            .order_by(CriteriaSpec.version.desc())
        ).first()
        criteria = []
        if spec:
            criteria = session.exec(
                select(Criterion).where(Criterion.criteria_spec_id == spec.id)
            ).all()
        criteria_by_id = {c.id: c for c in criteria}

    # ── Two-column layout ─────────────────────────────────────────────

    left_col, right_col = st.columns([1, 3])

    # Left: bidder selector
    with left_col:
        st.subheader("Bidders")

        # Group by verdict
        sort_order = {"needs_review": 0, "not_eligible": 1, "eligible": 2}
        sorted_bidders = sorted(
            bidders,
            key=lambda b: sort_order.get(
                bidder_verdicts[b.id].aggregate_state.value if bidder_verdicts.get(b.id) else "eligible", 3
            ),
        )

        # Default selection
        pre_selected = st.session_state.get("selected_bidder_id")
        default_idx = 0
        for i, b in enumerate(sorted_bidders):
            if str(b.id) == pre_selected:
                default_idx = i
                break

        selected_bidder = None
        for i, bidder in enumerate(sorted_bidders):
            bv = bidder_verdicts.get(bidder.id)
            state = bv.aggregate_state.value if bv else "unknown"
            emoji = verdict_emoji(state)

            if st.button(
                f"{emoji} {bidder.name}",
                key=f"bid_{bidder.id}",
                use_container_width=True,
                type="primary" if str(bidder.id) == pre_selected else "secondary",
            ):
                st.session_state["selected_bidder_id"] = str(bidder.id)
                st.rerun()

        if not pre_selected and sorted_bidders:
            st.session_state["selected_bidder_id"] = str(sorted_bidders[0].id)
            pre_selected = str(sorted_bidders[0].id)

    # Right: selected bidder's evaluation
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

            bv = session.exec(
                select(BidderVerdict).where(BidderVerdict.bidder_id == bidder.id)
            ).first()

            verdicts = session.exec(
                select(Verdict).where(Verdict.bidder_id == bidder.id)
            ).all()

            all_evidence = session.exec(
                select(EvidenceClaim).where(EvidenceClaim.bidder_id == bidder.id)
            ).all()
            evidence_by_criterion = {}
            for e in all_evidence:
                evidence_by_criterion.setdefault(e.criterion_id, []).append(e)

        # Bidder header
        agg_state = bv.aggregate_state.value if bv else "unknown"
        emoji = verdict_emoji(agg_state)
        label = verdict_label(agg_state)

        st.subheader(f"{bidder.name}")
        st.markdown(f"### {emoji} Overall: **{label}**")
        st.caption(f"Submitted: {bidder.submission_date.strftime('%Y-%m-%d %H:%M')}")
        st.markdown("---")

        # Per-criterion verdicts
        for verdict in verdicts:
            criterion = criteria_by_id.get(verdict.criterion_id)
            if not criterion:
                continue

            state = verdict.state.value
            v_emoji = verdict_emoji(state)
            v_label = verdict_label(state)
            type_label = criterion_type_label(criterion.type.value)
            mandatory = "🔴 Mandatory" if criterion.mandatory else "🔵 Optional"

            with st.container(border=True):
                # Header row
                h_col1, h_col2, h_col3 = st.columns([3, 2, 1])
                h_col1.markdown(f"**{criterion.id}** | {type_label}")
                h_col2.markdown(f"{v_emoji} **{v_label}**")
                h_col3.markdown(f"{mandatory}")

                # Rule and reason
                st.caption(f"Rule: `{verdict.rule_fired}`")
                st.markdown(f"{verdict.reason_template}")

                # Evidence
                evidence_list = evidence_by_criterion.get(verdict.criterion_id, [])
                if evidence_list:
                    with st.expander(f"📋 Evidence ({len(evidence_list)} claim{'s' if len(evidence_list) != 1 else ''})"):
                        for ei, ev in enumerate(evidence_list):
                            st.markdown(f"**Claim {ei + 1}** — Page {ev.source_page}")

                            # Show extracted values
                            if isinstance(ev.extracted_value, dict):
                                display_vals = {
                                    k: v for k, v in ev.extracted_value.items()
                                    if v is not None and k not in ("source_doc_id", "source_bbox")
                                }
                                st.json(display_vals)

                            # Confidence and verifier
                            conf_col, ver_col = st.columns(2)
                            conf_col.progress(
                                min(ev.confidence, 1.0),
                                text=f"Confidence: {ev.confidence:.0%}",
                            )
                            if ev.verifier_passed:
                                ver_col.success("✅ Verified")
                            else:
                                ver_col.warning("⚠️ Not verified")

                            if ei < len(evidence_list) - 1:
                                st.markdown("---")

                # Branch evaluations for disjunctive rule
                if verdict.officer_action and isinstance(verdict.officer_action, dict):
                    branches = verdict.officer_action.get("branch_evaluations")
                    if branches:
                        with st.expander("🌿 Branch Evaluations (Disjunctive Rule)"):
                            for bi, branch in enumerate(branches):
                                passed = "✅ PASS" if branch["passed"] else "❌ FAIL"
                                st.markdown(
                                    f"**Branch {chr(65 + bi)}**: "
                                    f"≥{branch['count_required']} works at ≥{branch['percentage']:.0f}% "
                                    f"(threshold {format_inr(branch['threshold'])}) — "
                                    f"{branch['qualifying_count']} qualifying → {passed}"
                                )

                # Gate 2 actions for Needs Review
                if state == "needs_review":
                    st.markdown("---")
                    st.markdown("**Gate 2 Actions:**")
                    act_col1, act_col2, act_col3 = st.columns(3)

                    if act_col1.button("✅ Accept As-Is", key=f"accept_{verdict.criterion_id}"):
                        st.success(f"Accepted {verdict.criterion_id} as-is.")

                    override_reason = act_col2.text_input(
                        "Override reason", key=f"override_reason_{verdict.criterion_id}",
                        placeholder="Reason for override",
                    )
                    if act_col2.button("✏️ Override", key=f"override_{verdict.criterion_id}"):
                        if override_reason:
                            st.success(f"Overridden {verdict.criterion_id}: {override_reason}")
                        else:
                            st.warning("Please provide a reason for override.")

                    if act_col3.button("⬆️ Escalate", key=f"escalate_{verdict.criterion_id}"):
                        st.info(f"Escalated {verdict.criterion_id} to committee.")

except Exception as e:
    st.error(f"Error: {e}")
    import traceback
    st.code(traceback.format_exc())
