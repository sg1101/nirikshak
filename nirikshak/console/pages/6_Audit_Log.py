"""Audit Log — View, verify, and replay the audit trail."""

import streamlit as st
import pandas as pd
from sqlmodel import select

from nirikshak.console.helpers import api_get, api_post, get_sync_session, render_sidebar, verdict_emoji, verdict_label
from nirikshak.console.theme import (
    inject_global_css, info_banner, section_header, verdict_pill,
    NAVY, DARK, SUCCESS, DANGER, WARNING, MUTED,
)
from nirikshak.core.schemas import AuditLogEntry

inject_global_css()
render_sidebar()

st.markdown(f"""
<div style="display:flex; align-items:center; gap:12px; margin-bottom:20px;">
    <span style="font-size:2rem;">🔗</span>
    <div>
        <h1 style="margin:0; color:{DARK};">Audit Log</h1>
        <span style="color:{MUTED};">Tamper-evident, hash-chained audit trail</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Chain verification banner
col1, col2 = st.columns([1, 4])
if col1.button("🔍 Verify Chain", type="primary"):
    with st.spinner("Verifying hash chain..."):
        try:
            result = api_get("/api/audit/verify")
            if result["valid"]:
                col2.markdown(f"""
                <div style="background:{SUCCESS}10; border:1px solid {SUCCESS}30; border-radius:8px; padding:10px 16px;">
                    <strong style="color:{SUCCESS};">✅ Chain Valid</strong>
                    <span style="color:{MUTED}; margin-left:8px;">No tampering detected. All entries verified.</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                col2.markdown(f"""
                <div style="background:{DANGER}10; border:1px solid {DANGER}30; border-radius:8px; padding:10px 16px;">
                    <strong style="color:{DANGER};">❌ Chain Broken at sequence {result['broken_at_sequence']}</strong>
                </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            col2.error(f"Verification failed: {e}")

st.markdown("---")

try:
    with get_sync_session() as session:
        entries = session.exec(select(AuditLogEntry).order_by(AuditLogEntry.sequence.desc())).all()

    if not entries:
        st.markdown(info_banner("No audit entries yet.", "#2980B9"), unsafe_allow_html=True)
        st.stop()

    # Filter
    action_types = sorted(set(e.action_type.value for e in entries))
    selected_types = st.multiselect("Filter by action type", options=action_types, default=action_types)
    filtered = [e for e in entries if e.action_type.value in selected_types]

    st.markdown(section_header(f"Audit Entries ({len(filtered)} of {len(entries)})"), unsafe_allow_html=True)

    # Color-coded action types
    ACTION_COLORS = {
        "tender_ingested": "#2980B9", "criteria_extracted": "#8E44AD", "criteria_locked": "#27AE60",
        "bidder_ingested": "#E67E22", "evidence_extracted": "#16A085",
        "rule_fired": "#C0392B", "bidder_verdict": "#2C3E50",
        "officer_review": "#F39C12", "report_finalized": "#1B4F72",
    }

    rows = []
    for e in filtered:
        color = ACTION_COLORS.get(e.action_type.value, MUTED)
        rows.append({
            "Seq": e.sequence,
            "Timestamp": e.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "Actor": e.actor,
            "Action": e.action_type.value,
            "Hash": e.entry_hash[:16] + "...",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Detail view
    st.markdown("---")
    st.markdown(section_header("Entry Detail"), unsafe_allow_html=True)

    seq_options = [e.sequence for e in filtered]
    if seq_options:
        selected_seq = st.selectbox("Select entry by sequence", options=seq_options)
        entry = next(e for e in filtered if e.sequence == selected_seq)

        col1, col2 = st.columns(2)
        col1.markdown(f"**Sequence:** {entry.sequence}")
        col1.markdown(f"**Timestamp:** {entry.timestamp}")
        col1.markdown(f"**Actor:** {entry.actor}")
        col1.markdown(f"**Action:** `{entry.action_type.value}`")
        col2.markdown(f"**Entry Hash:** `{entry.entry_hash}`")
        col2.markdown(f"**Previous Hash:** `{entry.previous_hash}`")
        col2.markdown(f"**Payload Hash:** `{entry.payload_hash}`")

        st.markdown("**Payload:**")
        st.json(entry.payload)

        # Replay for rule_fired
        if entry.action_type.value == "rule_fired":
            st.markdown(f"""
            <div style="background:{NAVY}08; border:1px solid {NAVY}20; border-radius:8px; padding:16px; margin:12px 0;">
                <strong style="color:{NAVY};">🔄 Audit Drill — Replay Verdict</strong>
                <p style="color:{MUTED}; margin:4px 0 0 0;">Re-run the verdict engine from frozen inputs to verify consistency.</p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🔄 Replay This Verdict", type="primary"):
                with st.spinner("Replaying..."):
                    try:
                        result = api_post("/api/audit/replay", data={"entry_hash": entry.entry_hash})
                        if result["match"]:
                            st.markdown(f"""
                            <div style="background:{SUCCESS}10; border:1px solid {SUCCESS}30; border-radius:8px; padding:16px;">
                                <strong style="color:{SUCCESS};">✅ Verdict Reproduced Successfully</strong>
                                <p style="color:{DARK}; margin:8px 0 0 0;">
                                    Historical: {verdict_pill(result['historical_state'])}
                                    Recomputed: {verdict_pill(result['recomputed_state'])}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.error(f"Divergence: historical={result['historical_state']}, recomputed={result['recomputed_state']}")
                            if result.get("divergence_reason"):
                                st.warning(result["divergence_reason"])

                        with st.expander(f"Chain of events ({len(result['chain_of_events'])} entries)"):
                            for event in result["chain_of_events"]:
                                st.markdown(f"**[{event['sequence']}]** `{event['action_type']}` — {event['payload_summary']}")
                    except Exception as e:
                        st.error(f"Replay failed: {e}")

except Exception as e:
    st.error(f"Error: {e}")
