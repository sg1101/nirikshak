"""Eval Dashboard — Three-layer accuracy and system metrics."""

import streamlit as st
from nirikshak.console.helpers import api_get, render_sidebar, verdict_emoji, verdict_label
from nirikshak.console.theme import (
    inject_global_css, status_card, info_banner, section_header, confidence_bar,
    NAVY, DARK, SUCCESS, DANGER, WARNING, MUTED, INFO,
)

inject_global_css()
render_sidebar()

st.markdown(f"""
<div style="display:flex; align-items:center; gap:12px; margin-bottom:20px;">
    <span style="font-size:2rem;">📈</span>
    <div>
        <h1 style="margin:0; color:{DARK};">Evaluation Dashboard</h1>
        <span style="color:{MUTED};">Three-layer accuracy metrics and system health</span>
    </div>
</div>
""", unsafe_allow_html=True)

try:
    metrics = api_get("/api/eval/metrics")
except Exception as e:
    st.error(f"Could not load metrics: {e}")
    st.stop()

# Test set info
ts = metrics["test_set_size"]
st.markdown(info_banner(
    f"Computed on <b>{ts['tenders']} tender(s)</b> x <b>{ts['bidders']} bidders</b> = "
    f"<b>{ts['criterion_pairs']} bidder-criterion pairs</b>. "
    f"Production calibration requires ~200 evaluations.",
    INFO,
), unsafe_allow_html=True)

st.markdown("---")

# Layer 1: OCR
st.markdown(section_header("Layer 1: OCR Character-Level Accuracy", "Character error rate on extracted text"), unsafe_allow_html=True)
st.markdown(f"""
<div style="background:white; border-radius:12px; padding:20px; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    <div style="color:{MUTED}; font-size:0.9rem; margin-bottom:8px;">Not measured in prototype (demo uses native-text PDFs). Requires scanned documents with ground-truth transcriptions.</div>
    <div style="color:{DARK}; font-size:2rem; font-weight:700;">N/A</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Layer 2: Field extraction
st.markdown(section_header("Layer 2: Field-Level Extraction", "Evidence quality metrics"), unsafe_allow_html=True)

eq = metrics["evidence_quality"]
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(status_card("Evidence Claims", str(eq["total_claims"]), INFO, "📋"), unsafe_allow_html=True)
with col2:
    vpr = f"{eq['verifier_pass_rate']:.0%}" if eq["verifier_pass_rate"] is not None else "N/A"
    st.markdown(status_card("Verifier Pass Rate", vpr, SUCCESS if (eq["verifier_pass_rate"] or 0) > 0.7 else WARNING, "✓"), unsafe_allow_html=True)
with col3:
    ac = f"{eq['avg_confidence']:.0%}" if eq["avg_confidence"] else "N/A"
    st.markdown(status_card("Avg Confidence", ac, SUCCESS if (eq["avg_confidence"] or 0) > 0.8 else WARNING, "🎯"), unsafe_allow_html=True)

st.markdown("---")

# Layer 3: Verdict agreement
st.markdown(section_header("Layer 3: Verdict-Level Agreement", "System vs ground truth"), unsafe_allow_html=True)

va = metrics["verdict_agreement"]
bl = va["bidder_level"]
cl = va["criterion_level"]

col1, col2 = st.columns(2)
with col1:
    val = f"{bl['accuracy']:.0%}" if bl["accuracy"] is not None else "N/A"
    st.markdown(status_card("Bidder-Level Accuracy", val, SUCCESS if (bl["accuracy"] or 0) > 0.8 else WARNING, "👥"), unsafe_allow_html=True)
    if bl["total"] > 0:
        st.caption(f"{bl['matches']}/{bl['total']} bidders match ground truth")
with col2:
    val = f"{cl['accuracy']:.0%}" if cl["accuracy"] is not None else "N/A"
    st.markdown(status_card("Criterion-Level Accuracy", val, SUCCESS if (cl["accuracy"] or 0) > 0.8 else WARNING, "📋"), unsafe_allow_html=True)
    if cl["total"] > 0:
        st.caption(f"{cl['matches']}/{cl['total']} criterion verdicts match")

# Per-bidder breakdown
if va["per_bidder"]:
    with st.expander("Per-Bidder Breakdown"):
        for pb in va["per_bidder"]:
            match_icon = "✅" if pb["match"] else "❌"
            st.markdown(
                f"- {match_icon} **{pb['bidder_name']}**: "
                f"Expected {verdict_emoji(pb['expected_verdict'])} {verdict_label(pb['expected_verdict'])}, "
                f"Got {verdict_emoji(pb['actual_verdict'])} {verdict_label(pb['actual_verdict'])}"
            )

st.markdown("---")

# Needs-Review fraction
st.markdown(section_header("Needs-Review Fraction", "System calibration metric"), unsafe_allow_html=True)

nr = metrics["needs_review_fraction"]
nr_pct = nr["fraction"] * 100

# Gauge visualization
gauge_color = SUCCESS if 5 <= nr_pct <= 40 else WARNING
st.markdown(f"""
<div style="background:white; border-radius:12px; padding:20px; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <div style="color:{MUTED}; font-size:0.8rem; text-transform:uppercase;">Needs-Review Rate</div>
            <div style="color:{DARK}; font-size:2.5rem; font-weight:700;">{nr_pct:.0f}%</div>
            <div style="color:{MUTED}; font-size:0.85rem;">{nr['count']}/{nr['total']} verdicts routed to review</div>
        </div>
        <div style="width:200px;">
            <div style="display:flex; justify-content:space-between; font-size:0.7rem; color:{MUTED};">
                <span>Over-confident</span><span>Optimal</span><span>Over-cautious</span>
            </div>
            <div style="display:flex; height:8px; border-radius:4px; overflow:hidden;">
                <div style="background:{DANGER}40; width:15%;"></div>
                <div style="background:{SUCCESS}40; width:70%;"></div>
                <div style="background:{WARNING}40; width:15%;"></div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Honest scope
st.markdown(f"""
<div style="background:{NAVY}05; border:1px solid {NAVY}15; border-radius:12px; padding:20px;">
    <h3 style="color:{NAVY}; margin-top:0;">Scope & Caveats</h3>
    <ul style="color:{DARK}; line-height:1.8;">
        <li>Numbers from <strong>prototype test set</strong> — limited tenders and bidders</li>
        <li>OCR accuracy not measured (native-text PDFs only)</li>
        <li>Field extraction uses verifier pass rate as proxy</li>
        <li>Production calibration requires ~200 real evaluations</li>
    </ul>
    <p style="color:{NAVY}; font-style:italic; margin-bottom:0;">
        "We build around the trustworthiness constraint, not the accuracy headline number.
        The audit log, not the model accuracy, is the regulated artefact."
    </p>
</div>
""", unsafe_allow_html=True)
