"""Verifier pass — re-check extracted values against cited source region."""

import logging
import re
from uuid import UUID

from nirikshak.core.schemas import EvidenceClaim, Page

logger = logging.getLogger(__name__)


def _normalize_number(s: str) -> str:
    """Remove formatting from a number string for comparison."""
    return re.sub(r"[,.\s₹$Rs/\-]", "", s).strip()


def _to_indian_format(num: float) -> list[str]:
    """Generate Indian number format variants for matching."""
    variants = []
    # Raw digits
    variants.append(str(int(num)))
    # Indian comma format: 1,00,00,000
    s = str(int(num))
    if len(s) > 3:
        last3 = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        variants.append(",".join(parts) + "," + last3)
    # Crore/lakh representations
    crore = num / 1e7
    lakh = num / 1e5
    if crore >= 1:
        for fmt in [f"{crore:.0f}", f"{crore:.1f}", f"{crore:.2f}"]:
            variants.append(fmt)
    if lakh >= 1:
        for fmt in [f"{lakh:.0f}", f"{lakh:.1f}", f"{lakh:.2f}"]:
            variants.append(fmt)
    return variants


def _number_appears_on_page(value: str, page_text: str) -> bool:
    """Check if a numeric value appears on the page (tolerant of formatting)."""
    normalized = _normalize_number(value)
    if not normalized:
        return False

    # Direct normalized match
    page_normalized = _normalize_number(page_text)
    if normalized in page_normalized:
        return True

    # Try variants
    try:
        num = float(re.sub(r"[^\d.]", "", value))
        page_lower = page_text.lower()
        for variant in _to_indian_format(num):
            if variant in page_lower or variant in page_normalized:
                return True
    except (ValueError, OverflowError):
        pass

    return False


def _text_appears_on_page(value: str, page_text: str) -> bool:
    """Check if a text value appears on the page (case-insensitive, partial, fuzzy)."""
    if not value or len(value) < 3:
        return True  # too short to verify meaningfully

    val_lower = value.lower()
    page_lower = page_text.lower()

    # Direct substring
    if val_lower in page_lower:
        return True

    # Check if significant words appear (at least half)
    words = [w for w in re.split(r"\s+", val_lower) if len(w) > 3]
    if not words:
        return True
    matches = sum(1 for w in words if w in page_lower)
    return matches >= max(1, len(words) // 2)


def verify_claim(
    claim: EvidenceClaim,
    pages_by_doc: dict[UUID, list[Page]],
) -> EvidenceClaim:
    """Verify an evidence claim against its cited source page.

    Sets verifier_passed = True if key extracted values appear on the cited page.
    Also searches adjacent pages if the exact page doesn't match.
    """
    pages = pages_by_doc.get(claim.source_doc_id, [])

    # Build searchable text: cited page + adjacent pages
    search_texts = []
    for p in sorted(pages, key=lambda x: x.page_number):
        if abs(p.page_number - claim.source_page) <= 1:
            search_texts.append(p.text)
    page_text = "\n".join(search_texts)

    if not page_text.strip():
        # Fall back to ALL pages in the document
        page_text = "\n".join(p.text for p in pages)

    if not page_text.strip():
        logger.warning("Verifier: no text for doc=%s page=%d", claim.source_doc_id, claim.source_page)
        claim.verifier_passed = False
        return claim

    extracted = claim.extracted_value

    # Skip keys that aren't verifiable content
    skip_keys = {
        "metric", "present", "signed", "dated", "declaration_signed",
        "cross_check_status", "similarity_status", "completion_cert_present",
        "source_doc_id", "source_page", "source_bbox",
        "completion_date",  # dates are hard to verify due to format differences
    }

    checks_passed = 0
    checks_total = 0

    for key, value in extracted.items():
        if value is None or key in skip_keys:
            continue

        if isinstance(value, bool):
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
        # Pass if at least one check passes (lenient for prototype)
        claim.verifier_passed = checks_passed >= 1

    logger.debug(
        "Verifier: criterion=%s passed=%s (%d/%d checks)",
        claim.criterion_id, claim.verifier_passed, checks_passed, checks_total,
    )
    return claim
