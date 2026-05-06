"""Experience count evidence extractor with similarity classification."""

import json
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from nirikshak.core.schemas import CompletedWorkClaim, CriterionType, EvidenceClaim
from nirikshak.bidder.extractors.base import BaseExtractor, register_extractor
from nirikshak.llm.client import call_llm
from nirikshak.llm.instructor_helpers import extract_structured

logger = logging.getLogger(__name__)

_EXP_PROMPT_PATH = Path(__file__).parent.parent.parent / "llm" / "prompts" / "experience_extractor.md"
_SIM_PROMPT_PATH = Path(__file__).parent.parent.parent / "llm" / "prompts" / "similarity_classifier.md"


class WorkClaimExtraction(BaseModel):
    work_description: str = ""
    client_name: str = ""
    contract_value: Decimal | None = None
    completion_date: str | None = None
    completion_cert_present: bool = False
    source_page: int = 0
    source_quote: str = ""


class ExperienceExtraction(BaseModel):
    claims: list[WorkClaimExtraction] = Field(default_factory=list)


def _classify_similarity(tender_scope: str, work_description: str) -> str:
    """Classify if a completed work is similar to the tender scope."""
    prompt_template = _SIM_PROMPT_PATH.read_text()
    prompt = prompt_template.replace("{tender_scope}", tender_scope).replace("{work_description}", work_description)

    raw = call_llm(prompt, system="You are a procurement similarity classifier. Return JSON only, no markdown.")
    try:
        data = json.loads(raw)
        similarity = data.get("similarity", "borderline")
        if similarity not in ("similar", "not_similar", "borderline"):
            return "borderline"
        return similarity
    except (json.JSONDecodeError, KeyError):
        return "borderline"


class ExperienceCountExtractor(BaseExtractor):
    criterion_type = CriterionType.experience_count

    def extract(self, criterion, documents, pages_by_doc, doc_categories):
        docs, text = self._get_all_text(documents, pages_by_doc, doc_categories, "experience_certificate")
        if not text.strip():
            return []

        prompt_template = _EXP_PROMPT_PATH.read_text()
        prompt = (
            f"{prompt_template}\n\n"
            f"CRITERION: {criterion.description}\n\n"
            f"BIDDER DOCUMENTS:\n{text}"
        )

        result = extract_structured(
            prompt=prompt,
            response_model=ExperienceExtraction,
            system="You are an experience certificate analyst for government tenders. Return JSON only.",
        )

        # Build page→doc mapping so we can assign correct source_doc_id per claim
        page_to_doc = {}
        for doc in docs:
            for p in pages_by_doc.get(doc.id, []):
                page_to_doc[p.page_number] = doc.id
        default_doc_id = docs[0].id if docs else documents[0].id

        tender_scope = criterion.description
        claims = []

        for wc in result.claims:
            # Map source_page to the correct document
            doc_id = page_to_doc.get(wc.source_page, default_doc_id)
            # Classify similarity
            similarity = "unknown"
            if criterion.parameters.get("similarity_required", True) and wc.work_description:
                similarity = _classify_similarity(tender_scope, wc.work_description)

            # Parse completion date — try multiple formats
            comp_date = None
            if wc.completion_date and wc.completion_date != "null":
                for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%dT%H:%M:%S"):
                    try:
                        from datetime import datetime as dt
                        comp_date = dt.strptime(wc.completion_date, fmt).date()
                        break
                    except ValueError:
                        continue
                if comp_date is None:
                    # Try partial: "March 2023", "2023", "2022-23"
                    import re
                    if re.match(r"^\d{4}$", wc.completion_date):
                        comp_date = date(int(wc.completion_date), 6, 30)
                    elif re.match(r"^\d{4}-\d{2}$", wc.completion_date):
                        # fiscal year like "2022-23"
                        comp_date = date(2000 + int(wc.completion_date[-2:]), 3, 31)

            claim_data = CompletedWorkClaim(
                value=wc.contract_value or Decimal("0"),
                completion_date=comp_date or date.today(),  # default to today, not 1900
                description=wc.work_description,
                similarity_status=similarity,
                source_doc_id=doc_id,
                source_page=wc.source_page,
            )

            claims.append(EvidenceClaim(
                id=uuid4(),
                bidder_id=uuid4(),
                criterion_id=criterion.id,
                extracted_value=claim_data.model_dump(mode="json"),
                source_doc_id=doc_id,
                source_page=wc.source_page,
                confidence=0.0,
                verifier_passed=False,
            ))

        logger.info("Extracted %d experience claims for %s", len(claims), criterion.id)
        return claims


register_extractor(ExperienceCountExtractor())
