"""Eval Dashboard — Three-layer accuracy and system metrics."""

import streamlit as st
from nirikshak.console.helpers import api_get, verdict_emoji, verdict_label, render_sidebar


render_sidebar()
st.header("📈 Evaluation Dashboard")

try:
    metrics = api_get("/api/eval/metrics")
except Exception as e:
    st.error(f"Could not load metrics: {e}")
    st.stop()

# ── Test set info ─────────────────────────────────────────────────────

ts = metrics["test_set_size"]
st.info(
    f"Numbers below are computed on a test set of **{ts['tenders']} tender(s)** "
    f"x **{ts['bidders']} bidders** = **{ts['criterion_pairs']} bidder-criterion pairs**. "
    f"Production calibration would require ~200 real evaluations to lock thresholds."
)

st.markdown("---")

# ── Layer 1: OCR (placeholder) ────────────────────────────────────────

st.subheader("Layer 1: OCR Character-Level Accuracy")
st.markdown(
    "**Status:** Not measured in prototype (demo uses native-text PDFs). "
    "Production measurement requires scanned/photo documents with ground-truth transcriptions."
)
st.metric("OCR CER", "N/A (native PDFs only)")

st.markdown("---")

# ── Layer 2: Field Extraction (evidence quality as proxy) ─────────────

st.subheader("Layer 2: Field-Level Extraction")

eq = metrics["evidence_quality"]
col1, col2, col3 = st.columns(3)
col1.metric("Total Evidence Claims", eq["total_claims"])
col2.metric("Verifier Pass Rate", f"{eq['verifier_pass_rate']:.0%}" if eq["verifier_pass_rate"] is not None else "N/A")
col3.metric("Avg Confidence", f"{eq['avg_confidence']:.0%}" if eq["avg_confidence"] else "N/A")

st.caption(
    "Verifier pass rate measures how often extracted values can be traced back to the cited page. "
    "Field-level accuracy against hand-labeled ground truth requires expanded Golden Set."
)

st.markdown("---")

# ── Layer 3: Verdict Agreement ────────────────────────────────────────

st.subheader("Layer 3: Verdict-Level Agreement")

va = metrics["verdict_agreement"]

col1, col2 = st.columns(2)
bl = va["bidder_level"]
cl = va["criterion_level"]

col1.metric(
    "Bidder-Level Accuracy",
    f"{bl['accuracy']:.0%}" if bl["accuracy"] is not None else "N/A",
    help=f"{bl['matches']}/{bl['total']} bidders match ground truth",
)
col2.metric(
    "Criterion-Level Accuracy",
    f"{cl['accuracy']:.0%}" if cl["accuracy"] is not None else "N/A",
    help=f"{cl['matches']}/{cl['total']} criterion verdicts match ground truth",
)

# Per-bidder breakdown
if va["per_bidder"]:
    st.markdown("**Per-Bidder Breakdown:**")
    for pb in va["per_bidder"]:
        match_icon = "✅" if pb["match"] else "❌"
        expected = verdict_emoji(pb["expected_verdict"])
        actual = verdict_emoji(pb["actual_verdict"])
        st.markdown(
            f"- {match_icon} **{pb['bidder_name']}**: "
            f"Expected {expected} {verdict_label(pb['expected_verdict'])}, "
            f"Got {actual} {verdict_label(pb['actual_verdict'])}"
        )

        # Show criterion-level mismatches
        mismatches = [
            (cid, d) for cid, d in pb.get("criteria", {}).items() if not d["match"]
        ]
        if mismatches:
            for cid, d in mismatches:
                st.caption(
                    f"    {cid}: expected {d['expected']}, got {d['actual']}"
                )

st.markdown("---")

# ── Needs-Review Fraction ─────────────────────────────────────────────

st.subheader("Needs-Review Fraction")

nr = metrics["needs_review_fraction"]
st.metric(
    "Needs-Review Rate",
    f"{nr['fraction']:.0%}",
    help=f"{nr['count']}/{nr['total']} verdicts routed to manual review",
)

# Interpretation
if nr["fraction"] < 0.05:
    st.warning("⚠️ Very low — system may be over-confident. Consider lowering confidence threshold.")
elif nr["fraction"] > 0.40:
    st.warning("⚠️ Very high — system may be dodging hard cases. Consider raising confidence threshold.")
else:
    st.success("✅ Within expected range — genuine ambiguity is being surfaced.")

st.caption(
    "The Needs-Review fraction tells the system's honest story. "
    "We aim for the rate where genuine disagreements concentrate — "
    "neither too low (over-confident) nor too high (over-cautious)."
)

st.markdown("---")

# ── Honest scope ──────────────────────────────────────────────────────

st.subheader("Scope & Caveats")
st.markdown(
    "- Numbers are from a **prototype test set** — 1 tender, 5 bidders, all native-text PDFs\n"
    "- OCR accuracy not measured (no scanned documents in test set)\n"
    "- Field extraction accuracy uses verifier pass rate as proxy (no hand-labeled field ground truth)\n"
    "- Verdict agreement is against hand-curated expected outcomes\n"
    "- Production calibration requires ~200 real evaluations across diverse tenders\n\n"
    "*We have built around the trustworthiness constraint, not the accuracy headline number. "
    "The audit log, not the model accuracy, is the regulated artefact this system stakes its credibility on.*"
)
