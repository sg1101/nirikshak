"""Audit Log — View, verify, and replay the audit trail."""

import streamlit as st
import pandas as pd
from sqlmodel import select

from nirikshak.console.helpers import api_get, api_post, get_sync_session, verdict_emoji, verdict_label, render_sidebar
from nirikshak.core.schemas import AuditLogEntry


render_sidebar()
st.header("🔗 Audit Log")

# ── Chain verification ────────────────────────────────────────────────

col1, col2 = st.columns([1, 3])
if col1.button("🔍 Verify Chain Integrity", type="primary"):
    with st.spinner("Verifying hash chain..."):
        try:
            result = api_get("/api/audit/verify")
            if result["valid"]:
                col2.success("✅ Audit chain is **valid** — no tampering detected.")
            else:
                col2.error(f"❌ Chain broken at sequence **{result['broken_at_sequence']}**!")
        except Exception as e:
            col2.error(f"Verification failed: {e}")

st.markdown("---")

# ── Audit log table ───────────────────────────────────────────────────

try:
    with get_sync_session() as session:
        entries = session.exec(
            select(AuditLogEntry).order_by(AuditLogEntry.sequence.desc())
        ).all()

    if not entries:
        st.info("No audit entries yet.")
        st.stop()

    # Filter
    action_types = sorted(set(e.action_type.value for e in entries))
    selected_types = st.multiselect(
        "Filter by action type",
        options=action_types,
        default=action_types,
    )

    filtered = [e for e in entries if e.action_type.value in selected_types]

    st.subheader(f"Audit Entries ({len(filtered)} of {len(entries)})")

    # Display as table
    rows = []
    for e in filtered:
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
    st.subheader("Entry Detail")
    seq_options = [e.sequence for e in filtered]
    if seq_options:
        selected_seq = st.selectbox("Select entry by sequence", options=seq_options)
        entry = next(e for e in filtered if e.sequence == selected_seq)

        col1, col2 = st.columns(2)
        col1.markdown(f"**Sequence:** {entry.sequence}")
        col1.markdown(f"**Timestamp:** {entry.timestamp}")
        col1.markdown(f"**Actor:** {entry.actor}")
        col1.markdown(f"**Action:** {entry.action_type.value}")
        col2.markdown(f"**Entry Hash:** `{entry.entry_hash}`")
        col2.markdown(f"**Previous Hash:** `{entry.previous_hash}`")
        col2.markdown(f"**Payload Hash:** `{entry.payload_hash}`")

        st.markdown("**Payload:**")
        st.json(entry.payload)

        # ── Replay button for rule_fired entries ──────────────────────
        if entry.action_type.value == "rule_fired":
            st.markdown("---")
            st.subheader("🔄 Audit Drill — Replay Verdict")
            st.markdown(
                "Re-run the verdict engine from frozen inputs to verify consistency. "
                "This is the audit drill: can we reproduce the exact same verdict?"
            )

            if st.button("🔄 Replay This Verdict", type="primary", key=f"replay_{entry.sequence}"):
                with st.spinner("Replaying verdict from frozen inputs..."):
                    try:
                        result = api_post(
                            "/api/audit/replay",
                            data={"entry_hash": entry.entry_hash},
                        )

                        if result["match"]:
                            st.success(
                                f"✅ **Verdict reproduced successfully!**\n\n"
                                f"The system re-evaluated **{result['criterion_id']}** for bidder "
                                f"`{result['bidder_id'][:8]}...` and produced the same verdict.\n\n"
                                f"- **Historical:** {verdict_emoji(result['historical_state'])} {verdict_label(result['historical_state'])}\n"
                                f"- **Recomputed:** {verdict_emoji(result['recomputed_state'])} {verdict_label(result['recomputed_state'])}"
                            )
                        else:
                            st.error(
                                f"❌ **Divergence detected!**\n\n"
                                f"- **Historical:** {result['historical_state']}\n"
                                f"- **Recomputed:** {result['recomputed_state']}\n\n"
                                f"**Reason:** {result.get('divergence_reason', 'Unknown')}"
                            )

                        # Show recomputed reason
                        if result.get("recomputed_reason"):
                            with st.expander("Recomputed reasoning"):
                                st.markdown(result["recomputed_reason"])

                        # Show chain of events
                        with st.expander(f"Chain of events ({len(result['chain_of_events'])} entries)"):
                            for event in result["chain_of_events"]:
                                st.markdown(
                                    f"**[{event['sequence']}]** `{event['action_type']}` "
                                    f"— {event['payload_summary']}"
                                )
                                st.caption(f"{event['timestamp']} | {event['entry_hash']}")

                    except Exception as e:
                        st.error(f"Replay failed: {e}")

except Exception as e:
    st.error(f"Error loading audit log: {e}")
