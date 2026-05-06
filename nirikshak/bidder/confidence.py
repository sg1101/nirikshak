"""Per-field confidence scoring for evidence claims."""

import logging

from nirikshak.core.config import get_settings
from nirikshak.core.schemas import EvidenceClaim, RoutingTag

logger = logging.getLogger(__name__)


def score_confidence(
    claim: EvidenceClaim,
    routing_tag: RoutingTag = RoutingTag.native_pdf,
    ocr_confidence: float | None = None,
) -> float:
    """Compute confidence score for an evidence claim.

    Returns 0.0–1.0. Components:
    - Verifier pass: 0.5 (binary)
    - Source quality: 0.0–0.3 (native PDF > scanned > photo)
    - Extraction quality: 0.0–0.2 (heuristics on extracted data)
    """
    score = 0.0

    # Verifier component (0.5)
    if claim.verifier_passed:
        score += 0.5

    # Source quality component (0.3 max)
    if routing_tag == RoutingTag.native_pdf:
        score += 0.3
    elif routing_tag == RoutingTag.scanned_pdf:
        if ocr_confidence is not None:
            score += 0.3 * ocr_confidence
        else:
            score += 0.15
    elif routing_tag == RoutingTag.photo_certificate:
        score += 0.1

    # Extraction quality heuristics (0.2 max)
    ev = claim.extracted_value
    if isinstance(ev, dict):
        has_values = sum(1 for v in ev.values() if v is not None and v != "" and v is not False)
        total_fields = max(len(ev), 1)
        completeness = has_values / total_fields
        score += 0.2 * completeness

    return min(score, 1.0)


def apply_confidence(
    claim: EvidenceClaim,
    routing_tag: RoutingTag = RoutingTag.native_pdf,
    ocr_confidence: float | None = None,
) -> EvidenceClaim:
    """Score and set confidence on a claim."""
    claim.confidence = score_confidence(claim, routing_tag, ocr_confidence)
    return claim


def needs_review(claim: EvidenceClaim) -> bool:
    """Check if a claim's confidence is below the threshold for mandatory criteria."""
    settings = get_settings()
    return claim.confidence < settings.confidence_threshold
