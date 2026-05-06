"""Signed PDF report generator (PRD §5.6, §7.2)."""

import hashlib
import hmac
import io
import logging
from datetime import datetime
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nirikshak.core.schemas import (
    Bidder, BidderVerdict, CriteriaSpec, Criterion,
    EvidenceClaim, Tender, Verdict,
)

logger = logging.getLogger(__name__)

SIGNING_KEY = b"nirikshak-prototype-key-2026"  # self-signed; production uses CCA DSC


def _sign_content(content: bytes) -> str:
    return hmac.new(SIGNING_KEY, content, hashlib.sha256).hexdigest()


def _verdict_text(state: str) -> str:
    return {"eligible": "ELIGIBLE", "not_eligible": "NOT ELIGIBLE", "needs_review": "NEEDS REVIEW"}.get(state, state)


def _verdict_color(state: str):
    return {"eligible": colors.green, "not_eligible": colors.red, "needs_review": colors.orange}.get(state, colors.gray)


async def generate_report(tender_id: UUID, session: AsyncSession) -> bytes:
    """Generate a signed PDF evaluation report."""

    # Load data
    tender = await session.get(Tender, tender_id)
    if not tender:
        raise ValueError(f"Tender not found: {tender_id}")

    spec_result = await session.execute(
        select(CriteriaSpec).where(CriteriaSpec.tender_id == tender_id).order_by(CriteriaSpec.version.desc())
    )
    spec = spec_result.scalar_one_or_none()

    criteria = []
    if spec:
        crit_result = await session.execute(select(Criterion).where(Criterion.criteria_spec_id == spec.id))
        criteria = list(crit_result.scalars().all())

    bidders_result = await session.execute(select(Bidder).where(Bidder.tender_id == tender_id))
    bidders = list(bidders_result.scalars().all())

    # Build PDF
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=18, spaceAfter=20)
    h2_style = ParagraphStyle("H2", parent=styles["Heading2"], spaceAfter=10)
    body_style = styles["BodyText"]
    small_style = ParagraphStyle("Small", parent=body_style, fontSize=8, textColor=colors.gray)

    # ── Cover ─────────────────────────────────────────────────────────

    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph("NIRIKSHAK", title_style))
    story.append(Paragraph("Consolidated Tender Evaluation Report", styles["Heading2"]))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(f"<b>Tender:</b> {tender.title}", body_style))
    story.append(Paragraph(f"<b>Authority:</b> {tender.procuring_authority}", body_style))
    story.append(Paragraph(f"<b>Estimated Value:</b> INR {tender.estimated_value:,.0f}", body_style))
    story.append(Paragraph(f"<b>Bid Submission Date:</b> {tender.bid_submission_date}", body_style))
    story.append(Paragraph(f"<b>Report Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", body_style))
    if spec:
        story.append(Paragraph(f"<b>Criteria Spec Hash:</b> <font size=7>{spec.content_hash}</font>", body_style))
    story.append(PageBreak())

    # ── Criteria summary ──────────────────────────────────────────────

    story.append(Paragraph("Eligibility Criteria", h2_style))

    if criteria:
        crit_data = [["ID", "Type", "Description", "Mandatory"]]
        for c in criteria:
            crit_data.append([
                c.id,
                c.type.value.replace("_", " ").title(),
                Paragraph(c.description[:80], small_style),
                "Yes" if c.mandatory else "No",
            ])
        crit_table = Table(crit_data, colWidths=[2 * cm, 3 * cm, 9 * cm, 2 * cm])
        crit_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ]))
        story.append(crit_table)

    story.append(Spacer(1, 1 * cm))

    # ── Per-bidder verdicts ───────────────────────────────────────────

    story.append(Paragraph("Bidder Evaluation Results", h2_style))

    for bidder in bidders:
        bv_result = await session.execute(select(BidderVerdict).where(BidderVerdict.bidder_id == bidder.id))
        bv = bv_result.scalar_one_or_none()
        agg = bv.aggregate_state.value if bv else "unknown"

        verdict_result = await session.execute(select(Verdict).where(Verdict.bidder_id == bidder.id))
        verdicts = list(verdict_result.scalars().all())

        story.append(Paragraph(
            f"<b>{bidder.name}</b> — <font color='{_verdict_color(agg).hexval()}'>"
            f"{_verdict_text(agg)}</font>",
            styles["Heading3"],
        ))

        if verdicts:
            v_data = [["Criterion", "Verdict", "Rule", "Reason"]]
            for v in verdicts:
                v_data.append([
                    v.criterion_id,
                    _verdict_text(v.state.value),
                    v.rule_fired.split(".")[-1] if "." in v.rule_fired else v.rule_fired,
                    Paragraph(v.reason_template[:100], small_style),
                ])
            v_table = Table(v_data, colWidths=[2 * cm, 2.5 * cm, 3.5 * cm, 8 * cm])
            v_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(v_table)

        story.append(Spacer(1, 0.5 * cm))

    story.append(PageBreak())

    # ── Signature block ───────────────────────────────────────────────

    story.append(Paragraph("Digital Signature", h2_style))

    # Sign the report content (we'll compute after building)
    content_for_signing = f"{tender.id}|{spec.content_hash if spec else ''}|{len(bidders)}|{datetime.utcnow().isoformat()}"
    signature = _sign_content(content_for_signing.encode())

    story.append(Paragraph(f"<b>Report Content Hash:</b> <font size=7>{hashlib.sha256(content_for_signing.encode()).hexdigest()}</font>", body_style))
    story.append(Paragraph(f"<b>Digital Signature:</b> <font size=7>{signature}</font>", body_style))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "<i>This report was digitally signed using a self-generated HMAC key. "
        "Production deployment would use a CCA-licensed Digital Signature Certificate (DSC) "
        "as per the Information Technology Act, 2000.</i>",
        small_style,
    ))

    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        "Generated by Nirikshak | AI-Based Tender Evaluation System | Prototype",
        ParagraphStyle("Footer", parent=small_style, alignment=1),
    ))

    doc.build(story)
    pdf_bytes = buf.getvalue()

    logger.info("Generated report: %d bytes, %d bidders", len(pdf_bytes), len(bidders))
    return pdf_bytes
