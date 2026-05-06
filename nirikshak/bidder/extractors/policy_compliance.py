"""Policy compliance evidence extractor."""

import logging
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from nirikshak.core.schemas import CriterionType, EvidenceClaim
from nirikshak.bidder.extractors.base import BaseExtractor, register_extractor
from nirikshak.llm.instructor_helpers import extract_structured

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "llm" / "prompts" / "compliance_extractor.md"


class ComplianceExtraction(BaseModel):
    policy_name: str = ""
    declaration_text: str = ""
    declaration_signed: bool = False
    cross_check_status: str = "not_found"
    source_page: int = 0
    source_quote: str = ""


class PolicyComplianceExtractor(BaseExtractor):
    criterion_type = CriterionType.policy_compliance

    def extract(self, criterion, documents, pages_by_doc, doc_categories):
        docs, text = self._get_all_text(documents, pages_by_doc, doc_categories, "compliance_declaration")
        if not text.strip():
            docs = documents
            texts = []
            for doc in docs:
                texts.append(f"=== {doc.filename} ===\n{self._get_text_for_doc(doc, pages_by_doc)}")
            text = "\n\n".join(texts)[:12000]

        prompt_template = _PROMPT_PATH.read_text()
        params = criterion.parameters
        prompt = (
            f"{prompt_template}\n\n"
            f"CRITERION: {criterion.description}\n"
            f"Policy: {params.get('policy_name', criterion.description)}\n"
            f"Declaration type: {params.get('declaration_type', 'self-declaration')}\n\n"
            f"BIDDER DOCUMENTS:\n{text}"
        )

        result = extract_structured(
            prompt=prompt,
            response_model=ComplianceExtraction,
            system="You are a compliance analyst. Return JSON only.",
        )

        doc_id = docs[0].id if docs else documents[0].id

        claim = EvidenceClaim(
            id=uuid4(),
            bidder_id=uuid4(),
            criterion_id=criterion.id,
            extracted_value={
                "policy_name": result.policy_name,
                "declaration_text": result.declaration_text,
                "declaration_signed": result.declaration_signed,
                "cross_check_status": result.cross_check_status,
            },
            source_doc_id=doc_id,
            source_page=result.source_page,
            confidence=0.0,
            verifier_passed=False,
        )

        logger.info("Compliance check for %s: status=%s", criterion.id, result.cross_check_status)
        return [claim]


register_extractor(PolicyComplianceExtractor())
