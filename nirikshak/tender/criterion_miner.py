"""Criterion miner — extract eligibility criteria from tender sections (PRD §5.2)."""

import logging
from pathlib import Path

from nirikshak.core.schemas import (
    Criterion,
    CriterionType,
    LabeledSection,
    MinedCriteriaList,
    MinedCriterion,
    Tender,
)
from nirikshak.llm.instructor_helpers import extract_structured

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "llm" / "prompts" / "criterion_miner.md"

# ID prefix per criterion type
_TYPE_PREFIX = {
    CriterionType.financial_threshold: "FIN",
    CriterionType.experience_count: "EXP",
    CriterionType.statutory_registration: "REG",
    CriterionType.quality_certification: "QUA",
    CriterionType.document_checklist: "DOC",
    CriterionType.policy_compliance: "POL",
}


def _assign_ids(criteria: list[MinedCriterion]) -> list[MinedCriterion]:
    """Reassign IDs using the type-prefix convention to ensure consistency."""
    counters: dict[str, int] = {}
    for c in criteria:
        prefix = _TYPE_PREFIX.get(c.type, "UNK")
        counters[prefix] = counters.get(prefix, 0) + 1
        c.suggested_id = f"{prefix}-{counters[prefix]:03d}"
    return criteria


def mine_criteria(sections: list[LabeledSection], tender: Tender) -> list[Criterion]:
    """Extract structured eligibility criteria from labeled sections.

    Only processes sections labeled 'eligibility'.
    Returns Criterion objects ready to be added to a CriteriaSpec.
    """
    eligibility_sections = [s for s in sections if s.label == "eligibility"]

    if not eligibility_sections:
        logger.warning("No eligibility sections found in tender: %s", tender.title)
        return []

    # Combine eligibility text with page references (cap at ~12000 chars to avoid LLM timeouts)
    combined_text = ""
    for section in eligibility_sections:
        for i, page_num in enumerate(section.pages):
            page_text = section.text.split("\n\n")[i] if i < len(section.text.split("\n\n")) else ""
            combined_text += f"\n--- Page {page_num} ---\n{page_text}"
    combined_text = combined_text[:12000]

    prompt_template = _PROMPT_PATH.read_text()
    prompt = (
        f"{prompt_template}\n\n"
        f"---\n"
        f"TENDER: {tender.title}\n"
        f"Procuring Authority: {tender.procuring_authority}\n"
        f"Estimated Value: INR {tender.estimated_value}\n"
        f"Bid Submission Date: {tender.bid_submission_date}\n\n"
        f"ELIGIBILITY SECTION TEXT:\n{combined_text}"
    )

    logger.info("Mining criteria from %d chars of eligibility text", len(combined_text))

    result = extract_structured(
        prompt=prompt,
        response_model=MinedCriteriaList,
        system="You are a government procurement expert analyzing tender eligibility criteria. Be precise and extract only what is stated.",
        max_tokens=8192,
    )

    mined = _assign_ids(result.criteria)

    # Convert MinedCriterion → Criterion (DB model)
    criteria = []
    for m in mined:
        criteria.append(Criterion(
            id=m.suggested_id,
            criteria_spec_id="placeholder",  # set by criteria_spec.py
            type=m.type,
            description=m.description,
            mandatory=m.mandatory,
            parameters=m.parameters,
            source_page=m.source_page,
            source_quote=m.source_quote,
        ))

    logger.info("Mined %d criteria from tender: %s", len(criteria), tender.title)
    return criteria
