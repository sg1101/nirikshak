"""Verifier pass — re-check extracted values against cited source region."""

import logging
import re
from uuid import UUID

from nirikshak.core.schemas import EvidenceClaim, Page

logger = logging.getLogger(__name__)


def _normalize_number(s: str) -> str:
    """Remove formatting from a number string for comparison."""
    return re.sub(r"[,\s₹$]", "", s).strip()


def _number_appears_on_page(value: str, page_text: str) -> bool:
    """Check if a numeric value appears on the page (tolerant of formatting)."""
    normalized = _normalize_number(value)
    if not normalized:
        return False

    # Direct match
    if normalized in _normalize_number(page_text):
        return True

    # Try Indian number formatting variants
    # e.g., 75000000 could appear as 7,50,00,000 or 75000000 or 7.5 crore
    try:
        num = float(normalized)
        # Check if number appears in crores/lakhs text
        crore = num / 10000000
        lakh = num / 100000
        page_lower = page_text.lower()

        for variant in [
            f"{crore:.1f}",
            f"{crore:.2f}",
            f"{int(crore)}",
            f"{lakh:.1f}",
            f"{int(lakh)}",
        ]:
            if variant in page_lower:
                return True
    except ValueError:
        pass

    return False


def _text_appears_on_page(value: str, page_text: str) -> bool:
    """Check if a text value appears on the page (case-insensitive, partial)."""
    if not value or len(value) < 3:
        return True  # too short to verify meaningfully
    return value.lower() in page_text.lower()


def verify_claim(
    claim: EvidenceClaim,
    pages_by_doc: dict[UUID, list[Page]],
) -> EvidenceClaim:
    """Verify an evidence claim against its cited source page.

    Sets verifier_passed = True if key extracted values appear on the cited page.
    """
    pages = pages_by_doc.get(claim.source_doc_id, [])
    cited_page = None
    for p in pages:
        if p.page_number == claim.source_page:
            cited_page = p
            break

    if cited_page is None or not cited_page.text.strip():
        logger.warning("Verifier: no text for doc=%s page=%d", claim.source_doc_id, claim.source_page)
        claim.verifier_passed = False
        return claim

    page_text = cited_page.text
    extracted = claim.extracted_value

    # Verify based on what's in the extracted value
    checks_passed = 0
    checks_total = 0

    for key, value in extracted.items():
        if value is None or key in ("metric", "present", "signed", "dated", "declaration_signed",
                                     "cross_check_status", "similarity_status", "completion_cert_present"):
            continue

        if isinstance(value, (int, float)):
            checks_total += 1
            if _number_appears_on_page(str(value), page_text):
                checks_passed += 1
        elif isinstance(value, str) and len(value) > 3:
            checks_total += 1
            if _text_appears_on_page(value, page_text):
                checks_passed += 1

    if checks_total == 0:
        claim.verifier_passed = True  # nothing to verify
    else:
        claim.verifier_passed = checks_passed >= max(1, checks_total // 2)

    logger.debug(
        "Verifier: criterion=%s passed=%s (%d/%d checks)",
        claim.criterion_id, claim.verifier_passed, checks_passed, checks_total,
    )
    return claim
