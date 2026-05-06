"""Quality certification evidence extractor."""

import logging
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from nirikshak.core.schemas import CriterionType, EvidenceClaim
from nirikshak.bidder.extractors.base import BaseExtractor, register_extractor
from nirikshak.llm.instructor_helpers import extract_structured

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "llm" / "prompts" / "quality_extractor.md"


class CertificationExtraction(BaseModel):
    cert_name: str = ""
    cert_version: str | None = None
    cert_id: str | None = None
    issuing_body: str = ""
    scope: str | None = None
    issue_date: str | None = None
    expiry_date: str | None = None
    source_page: int = 0
    source_quote: str = ""


class CertificationExtractionList(BaseModel):
    certifications: list[CertificationExtraction]


class QualityCertificationExtractor(BaseExtractor):
    criterion_type = CriterionType.quality_certification

    def extract(self, criterion, documents, pages_by_doc, doc_categories):
        docs, text = self._get_all_text(documents, pages_by_doc, doc_categories, "quality_certificate")
        if not text.strip():
            return []

        prompt_template = _PROMPT_PATH.read_text()
        params = criterion.parameters
        prompt = (
            f"{prompt_template}\n\n"
            f"CRITERION: {criterion.description}\n"
            f"Required certificate: {params.get('cert_name', 'any')}\n"
            f"Accepted versions: {params.get('accepted_versions', 'any')}\n\n"
            f"BIDDER DOCUMENTS:\n{text}"
        )

        result = extract_structured(
            prompt=prompt,
            response_model=CertificationExtractionList,
            system="You are a quality certification analyst. Return JSON only.",
        )

        claims = []
        doc_id = docs[0].id if docs else documents[0].id

        for cert in result.certifications:
            claims.append(EvidenceClaim(
                id=uuid4(),
                bidder_id=uuid4(),
                criterion_id=criterion.id,
                extracted_value={
                    "cert_name": cert.cert_name,
                    "cert_version": cert.cert_version,
                    "cert_id": cert.cert_id,
                    "issuing_body": cert.issuing_body,
                    "scope": cert.scope,
                    "issue_date": cert.issue_date,
                    "expiry_date": cert.expiry_date,
                },
                source_doc_id=doc_id,
                source_page=cert.source_page,
                confidence=0.0,
                verifier_passed=False,
            ))

        logger.info("Extracted %d certifications for %s", len(claims), criterion.id)
        return claims


register_extractor(QualityCertificationExtractor())
