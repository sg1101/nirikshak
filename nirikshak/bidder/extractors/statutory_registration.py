"""Statutory registration evidence extractor."""

import logging
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel

from nirikshak.core.schemas import Criterion, CriterionType, Document, EvidenceClaim, Page
from nirikshak.bidder.extractors.base import BaseExtractor, register_extractor
from nirikshak.llm.instructor_helpers import extract_structured

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "llm" / "prompts" / "statutory_extractor.md"


class RegistrationExtraction(BaseModel):
    registration_type: str = ""
    registration_number: str = ""
    registered_name: str = ""
    valid_from: str | None = None
    valid_until: str | None = None
    class_category: str | None = None
    source_page: int = 0
    source_quote: str = ""


class RegistrationExtractionList(BaseModel):
    registrations: list[RegistrationExtraction]


class StatutoryRegistrationExtractor(BaseExtractor):
    criterion_type = CriterionType.statutory_registration

    def extract(self, criterion, documents, pages_by_doc, doc_categories):
        docs, text = self._get_all_text(documents, pages_by_doc, doc_categories, "registration_certificate")
        if not text.strip():
            return []

        prompt_template = _PROMPT_PATH.read_text()
        params = criterion.parameters
        prompt = (
            f"{prompt_template}\n\n"
            f"CRITERION: {criterion.description}\n"
            f"Required registration type: {params.get('registration_type', 'any')}\n"
            f"Required class: {params.get('required_class', 'any')}\n\n"
            f"BIDDER DOCUMENTS:\n{text}"
        )

        result = extract_structured(
            prompt=prompt,
            response_model=RegistrationExtractionList,
            system="You are a document analyst specializing in Indian statutory registrations. Return JSON only.",
        )

        claims = []
        doc_id = docs[0].id if docs else documents[0].id

        for reg in result.registrations:
            claims.append(EvidenceClaim(
                id=uuid4(),
                bidder_id=uuid4(),
                criterion_id=criterion.id,
                extracted_value={
                    "registration_type": reg.registration_type,
                    "registration_number": reg.registration_number,
                    "registered_name": reg.registered_name,
                    "valid_from": reg.valid_from,
                    "valid_until": reg.valid_until,
                    "class_category": reg.class_category,
                },
                source_doc_id=doc_id,
                source_page=reg.source_page,
                confidence=0.0,
                verifier_passed=False,
            ))

        logger.info("Extracted %d registrations for %s", len(claims), criterion.id)
        return claims


register_extractor(StatutoryRegistrationExtractor())
